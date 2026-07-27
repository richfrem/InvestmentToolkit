/**
 * portfolio.ts - Express routing for user portfolio positions, balances, and sync.
 * 
 * Purpose:
 *   Handles backend Express routes for user portfolio data management,
 *   rebalancing updates, live snapshot sync, and performance tracking.
 * 
 * Layer:
 *   Backend / Routes / Portfolio
 * 
 * Key Functions (Index):
 *   - backupPortfolio() - Creates a backup copy of portfolio.json
 *   - loadYtdPerformanceReport() - Executes time-weighted returns script and reads generated report
 *   - readPortfolio() - Parses portfolio JSON structure resolving array/object schemas
 *   - verifyPortfolioTotals(holdings, tvSnapshot) - Reconciliation gate comparing computed vs broker total
 *   - getHoldingsForDisplayFromDb() - SQLite-sourced enriched holdings for GET /
 *   - persistRefreshedPricesToDb(items) - Persist fresh prices + sector/industry into SQLite
 *
 * Routes Index:
 *   - GET / - Reads and returns aggregate portfolio holdings and active sync source
 *   - POST / - Core saving/restructuring of the user portfolio
 *   - GET /summary - Aggregates YTD/TWR returns and portfolio USD/CAD totals
 *   - GET /performance - Triggers and returns period performance details
 *   - GET /weights - Computes weight allocation ratios for each holding
 *   - GET /status - Returns latest sync timestamp from portfolio cache
 *   - GET /position/:ticker - Returns price, shares, and per-account breakdown for a ticker
 *   - GET /holdings/:ticker - Retrieves per-account position counts from TV snapshot
 *   - POST /refresh-prices - Forces yfinance quote refresh
 *   - POST /sync-tv - Gated TradingView CDP sync returning HITL preview diff
 *   - POST /sync-tv/promote - Finalizes and writes HITL TradingView snapshot promote
 *   - POST /sync-tv/apply - One-shot automated sync applying TV data immediately
 *   - POST /sync - Auto-priority sync selecting reachable sources
 *   - GET /strategy-allocation - Aggregates cash and holdings by sub-strategy and pillar
 * 
 * Key Input Dependencies:
 *   - investment_screener/backend/data/portfolio.json (Live portfolio state)
 *   - investment_screener/backend/data/domain_model.sqlite's cash_flow / cash_flow_baseline
 *     tables (Wave 4 cutover; formerly cash_flows.json, now archived)
 *   - investment_screener/backend/data/portfolio-config.json (YTD starting configuration overrides)
 *   - investment_screener/backend/data/ytd_performance_report.json (Output TWR data)
 * 
 * Key Output Dependencies:
 *   - investment_screener/backend/data/portfolio.json
 *   - investment_screener/backend/data/portfolio.json.bak
 */

import express from 'express';
import fs from 'fs';
import path from 'path';
import { spawnPythonScript } from '../services/bridge';
import { brokerSyncService, mergeIntoPortfolio, persistSnapshotToDb } from '../services/BrokerSyncService';
import { getLiveUsdCadRate, isTradingViewConnected } from '../utils/helpers';
import { PORTFOLIO_FILE, PORTFOLIO_CONFIG_FILE, DOMAIN_MODEL_DB_FILE } from '../utils/paths';
import { computeWeightsMap, PortfolioTotals } from '../utils/portfolioSnapshot';
import { computeStrategyAllocation } from '../utils/strategyAllocation';
import { PortfolioRepository } from '../services/PortfolioRepository';
import { InvestmentRepository } from '../services/InvestmentRepository';
import { normalizeTicker } from '../utils/tickerAliases';

const router = express.Router();

// YTD constants — defaults overridden by portfolio-config.json (gitignored, personal)
let YTD_START_VALUE_CAD = 34126.27;
let JAN1_USD_CAD_RATE = 1.3723;
try {
    if (fs.existsSync(PORTFOLIO_CONFIG_FILE)) {
        const cfg = JSON.parse(fs.readFileSync(PORTFOLIO_CONFIG_FILE, 'utf-8'));
        if (typeof cfg.ytdStartValueCAD === 'number') YTD_START_VALUE_CAD = cfg.ytdStartValueCAD;
        if (typeof cfg.jan1UsdCadRate === 'number') JAN1_USD_CAD_RATE = cfg.jan1UsdCadRate;
    }
} catch { /* use compile-time defaults */ }

function backupPortfolio(): void {
    if (fs.existsSync(PORTFOLIO_FILE)) fs.copyFileSync(PORTFOLIO_FILE, PORTFOLIO_FILE + '.bak');
}

/**
 * Executes the Python TWR calculation script and reads the generated report.
 */
async function loadYtdPerformanceReport(): Promise<any> {
    /*
      Wave 4 cutover: cash-flow data now lives in domain_model.sqlite's cash_flow /
      cash_flow_baseline tables, not cash_flows.json (retired/archived) — there is no
      cheap file-existence check left to gate on. ytd_return.py itself now performs
      this gate: load_cash_flows() returns {} when the DB has no baseline row yet
      (fresh install / no cash flows recorded), calculate_twr() detects that and exits
      non-zero with a JSON {"error": ...} on stdout, which spawnPythonScript's
      _spawnRaw() turns into a rejected promise on any non-zero exit code — caught
      below and returned as null, same external behavior as the old existsSync() gate.
     */
    const reportFile = path.join(path.dirname(PORTFOLIO_FILE), 'ytd_performance_report.json');

    try {
        await spawnPythonScript('ytd_return.py', ['--json']);
        if (fs.existsSync(reportFile)) {
            return JSON.parse(fs.readFileSync(reportFile, 'utf-8'));
        }
    } catch (err) {
        console.error(`[loadYtdPerformanceReport] Failed to run ytd_return.py:`, err);
    }
    return null;
}

/** Read portfolio.json — handles both legacy array format and new { holdings, totals, tvSnapshot } format. */
function readPortfolio(): { holdings: any[]; totals: PortfolioTotals | null; tvSnapshot: any | null } {
    if (!fs.existsSync(PORTFOLIO_FILE)) return { holdings: [], totals: null, tvSnapshot: null };
    const raw = JSON.parse(fs.readFileSync(PORTFOLIO_FILE, 'utf-8'));
    if (Array.isArray(raw)) return { holdings: raw, totals: null, tvSnapshot: null };
    return { holdings: raw.holdings ?? [], totals: raw.totals ?? null, tvSnapshot: raw.tvSnapshot ?? null };
}

// ── Wave 3 Task 6: SQLite-backed reads (account_investment / investment_price) ──
// Each helper returns null/[] (never throws, never fabricates) when the SQLite
// side has no usable data yet, so every route below falls back to the existing
// portfolio.json-based computation. This is the read-side cutover that lets
// Task 5's dual-write producers eventually drop their JSON writes (see that
// task's report "Scope deviation" section) -- once these are load-bearing,
// portfolio.json is no longer the only source these 5 endpoints can serve from.

/** Per ADR-030 / portfolio_repository.py::get_portfolio_total_value: the
 * portfolio-wide USD total, computed live as the sum of per-account totals
 * (never a stored value, never an independent flat query). Returns null
 * (not 0) when there's no priced position data yet, so /summary can fall
 * back to its existing portfolio.json-based computation. */
export function getPortfolioTotalUsdFromDb(dbPath: string = DOMAIN_MODEL_DB_FILE): number | null {
    const repo = new PortfolioRepository(dbPath);
    try {
        const total = repo.getPortfolioTotalValue();
        return total > 0 ? total : null;
    } finally {
        repo.close();
    }
}

/** The real, current "last synced" timestamp — `MAX(account_investment.last_synced_at)`,
 * which updates on every real sync. Replaces `/summary`'s prior reliance on
 * portfolio.json's `totals.timestamp`/`positions[].last_updated`, which Wave 3
 * stopped writing entirely once sync cut over to SQLite-only writes (so that
 * field was permanently frozen at whatever it held before the cutover). */
export function getLastSyncedAtFromDb(dbPath: string = DOMAIN_MODEL_DB_FILE): string | null {
    const repo = new PortfolioRepository(dbPath);
    try {
        return repo.getLastSyncedAt();
    } finally {
        repo.close();
    }
}

/** Builds the {holdings, totals}-shaped input `computeWeightsMap` expects,
 * sourced from account_investment/investment_price instead of portfolio.json's
 * `holdings`/`totals`. Returns null when there's no priced position data. */
export function getWeightsFromDb(dbPath: string = DOMAIN_MODEL_DB_FILE): Record<string, number> | null {
    const repo = new PortfolioRepository(dbPath);
    try {
        const positions = repo.listPositionsBySymbol();
        const totalUSD = repo.getPortfolioTotalValue();
        if (positions.length === 0 || totalUSD <= 0) return null;
        const holdings = positions.map(p => ({
            symbol: p.symbol === 'CASH_USD' ? 'USD_CASH' : p.symbol,
            shares: p.quantity,
            price: p.price ?? p.averageCost ?? 0,
        }));
        const totals: PortfolioTotals = {
            holdingsUSD: totalUSD, cashUSD: 0, totalUSD, totalCAD: 0, exchangeRate: 1,
            timestamp: new Date().toISOString(), totalSource: 'tv_authoritative',
        };
        return computeWeightsMap(holdings, totals);
    } finally {
        repo.close();
    }
}

/** Builds `positions`/`totals` input for `computeStrategyAllocation`, sourced
 * from SQLite. Returns null when there's no priced position data so the
 * caller falls back to portfolio.json's `holdings`/`totals`. */
export function getStrategyAllocationInputFromDb(dbPath: string = DOMAIN_MODEL_DB_FILE): { positions: any[]; totals: { totalUSD: number } } | null {
    const repo = new PortfolioRepository(dbPath);
    try {
        const positions = repo.listPositionsBySymbol();
        const totalUSD = repo.getPortfolioTotalValue();
        if (positions.length === 0 || totalUSD <= 0) return null;
        const mapped = positions.map(p => {
            const symbol = p.symbol === 'CASH_USD' ? 'USD_CASH' : p.symbol;
            return {
                symbol,
                shares: p.quantity,
                price: p.price ?? p.averageCost ?? 0,
                book_price: p.averageCost ?? 0,
                sector: symbol === 'USD_CASH' ? 'CASH' : undefined,
            };
        });
        return { positions: mapped, totals: { totalUSD } };
    } finally {
        repo.close();
    }
}

/** Per-account quantity/average_cost for one ticker, replacing
 * `tvSnapshot.positions[]` reads in /position/:ticker and /holdings/:ticker.
 * Returns [] when the symbol has no `account_investment` rows -- an empty
 * per-account breakdown is a legitimate "not currently held per-account"
 * answer, not a fallback trigger (each route still has its own portfolio.json
 * `shares`/`price` fallback for the aggregate-level fields). */
export function getAccountPositionsFromDb(
    ticker: string,
    dbPath: string = DOMAIN_MODEL_DB_FILE
): Array<{ accountId: string; quantity: number; averageCost: number | null }> {
    const repo = new PortfolioRepository(dbPath);
    try {
        return repo.getPerAccountPositions(ticker);
    } finally {
        repo.close();
    }
}

/** Wave 3 (completion): the enriched holdings array GET /api/portfolio serves,
 * sourced from SQLite instead of portfolio.json's flat `holdings`. Per held
 * symbol: shares (quantity summed across accounts), price, book_price
 * (average_cost) from account_investment/investment_price, plus
 * name/sector/industry/pillar_id from the `investment` row. sector/industry fall
 * back to "Unknown" (matching fetch_portfolio_heatmap.py) when not yet resolved —
 * e.g. right after a fresh TV sync, before the first /refresh-prices run.
 * Returns null when there are no priced/held positions in SQLite yet, so GET /
 * falls back to the existing portfolio.json read. */
export function getHoldingsForDisplayFromDb(dbPath: string = DOMAIN_MODEL_DB_FILE): any[] | null {
    // InvestmentRepository first: it owns and fully creates the `investment` table
    // (all columns + indexes). Opening PortfolioRepository first on a brand-new
    // file would create a narrower `investment` table, making InvestmentRepository's
    // later index-on-lifecycle_status/pillar_id creation fail.
    const investmentRepo = new InvestmentRepository(dbPath);
    const portfolioRepo = new PortfolioRepository(dbPath);
    try {
        const positions = portfolioRepo.listPositionsBySymbol();
        if (positions.length === 0) return null;
        return positions.map(p => {
            const displaySymbol = p.symbol === 'CASH_USD' ? 'USD_CASH' : p.symbol;
            const inv = investmentRepo.getInvestment(p.symbol);
            return {
                symbol: displaySymbol,
                shares: p.quantity,
                price: p.price ?? undefined,
                book_price: p.averageCost ?? undefined,
                name: inv?.name ?? displaySymbol,
                sector: displaySymbol === 'USD_CASH' ? 'CASH' : (inv?.sector ?? 'Unknown'),
                industry: displaySymbol === 'USD_CASH' ? 'CASH' : (inv?.industry ?? 'Unknown'),
                pillarId: inv?.pillar_id ?? null,
            };
        });
    } finally {
        investmentRepo.close();
        portfolioRepo.close();
    }
}

/** Book value (sum of quantity * average_cost across held positions) and
 * position count, sourced from account_investment instead of portfolio.json's
 * `positions[].book_price`/`.length` — Wave 7, replacing /summary's prior
 * unconditional reliance on the (frozen since Wave 3) file for these two
 * fields even though totalMarketValueUSD already read SQLite. Returns null
 * when there are no priced/held positions in SQLite yet. */
export function getBookValueAndCountFromDb(dbPath: string = DOMAIN_MODEL_DB_FILE): { totalBookValueUSD: number; positionCount: number } | null {
    const portfolioRepo = new PortfolioRepository(dbPath);
    try {
        const positions = portfolioRepo.listPositionsBySymbol();
        if (positions.length === 0) return null;
        const totalBookValueUSD = positions.reduce((sum, p) => sum + p.quantity * (p.averageCost ?? 0), 0);
        return { totalBookValueUSD, positionCount: positions.length };
    } finally {
        portfolioRepo.close();
    }
}

/** Single-ticker price + book_price (weighted average cost across accounts),
 * sourced from investment_price/account_investment — Wave 7, replacing
 * /position/:ticker's prior unconditional reliance on portfolio.json for
 * these two fields (only per-account share counts had already been cut over
 * to SQLite in Wave 3). Returns null when the ticker has no investment_price
 * row (never synced/priced yet). */
export function getPositionPriceFromDb(ticker: string, dbPath: string = DOMAIN_MODEL_DB_FILE): { price: number | null; book_price: number | null } | null {
    const investmentRepo = new InvestmentRepository(dbPath);
    const portfolioRepo = new PortfolioRepository(dbPath);
    try {
        const investmentId = investmentRepo.resolveInvestmentId(ticker, 'EQUITY', 'USD');
        const priceRow = portfolioRepo.getInvestmentPrice(investmentId);
        if (priceRow == null) return null;
        const accountRows = portfolioRepo.getPerAccountPositions(ticker);
        const totalQty = accountRows.reduce((s, r) => s + r.quantity, 0);
        const totalCost = accountRows.reduce((s, r) => s + r.quantity * (r.averageCost ?? 0), 0);
        const book_price = totalQty > 0 ? totalCost / totalQty : null;
        return { price: priceRow.price, book_price };
    } finally {
        investmentRepo.close();
        portfolioRepo.close();
    }
}

/**
 * Watchlist-only tickers (`investment.is_watchlisted = 1`, no shares in
 * `account_investment`) as shares:0 refresh items — shaped so they slot into
 * the same `itemsForFetch`/`persistRefreshedPricesToDb` pipeline as held
 * positions. Closes a 2026-07-27 gap: `/refresh-prices` sourced its ticker
 * list from held positions only, so watchlist tickers (fed to the watchlist
 * heatmap, thesis review, etc.) never got refreshed and went stale
 * indefinitely with no visible signal.
 */
export function getWatchlistTickersForRefresh(dbPath: string = DOMAIN_MODEL_DB_FILE): Array<{ symbol: string; shares: number }> {
    const investmentRepo = new InvestmentRepository(dbPath);
    try {
        return investmentRepo.listWatchlisted().map(w => ({ symbol: w.ticker, shares: 0 }));
    } finally {
        investmentRepo.close();
    }
}

/**
 * Delete each symbol's `investment_price` row before a refresh fetch runs, so
 * a symbol whose fetch fails or is skipped reads as missing (0/unknown)
 * afterward instead of silently continuing to serve a stale price. Found
 * 2026-07-27: several held/watchlisted symbols sat a full day stale, frozen
 * at the exact regular-session price with no signal anything was wrong.
 */
export function clearPricesBeforeRefresh(symbols: string[], dbPath: string = DOMAIN_MODEL_DB_FILE): void {
    const investmentRepo = new InvestmentRepository(dbPath);
    const portfolioRepo = new PortfolioRepository(dbPath);
    try {
        for (const rawSymbol of symbols) {
            if (!rawSymbol || rawSymbol === 'USD_CASH') continue;
            const symbol = normalizeTicker(rawSymbol);
            const investmentId = investmentRepo.resolveInvestmentId(symbol, 'EQUITY', 'USD');
            portfolioRepo.clearInvestmentPrice(investmentId);
        }
    } finally {
        investmentRepo.close();
        portfolioRepo.close();
    }
}

/**
 * Wave 3 (completion): persist freshly-refreshed live prices into
 * `investment_price`, closing the gap that previously left SQLite prices
 * permanently stale after the one-time migrate_portfolio_to_sqlite.py run.
 *
 * `/refresh-prices` builds a FLAT, cross-account-aggregated `items` array (fresh
 * yfinance/TV price per symbol, no per-account attribution). `investment_price`
 * is keyed per-investment (not per-account), so it is the one table this flat
 * shape can safely write — `account_investment` quantities are deliberately NOT
 * touched here (they carry per-account attribution this array lacks and are
 * maintained only by the sync-tv → persistSnapshotToDb path). Symbols are
 * normalized through the same broker alias map persistSnapshotToDb uses so the
 * `investment_id` resolved here matches the account_investment rows those prices
 * are joined against.
 *
 * Also persists the sector/industry each `item` carries (resolved by
 * fetch_portfolio_heatmap.py's yfinance/SECTOR_OVERRIDES lookup — the SAME real
 * code path, no duplicated logic) into investment.sector/investment.industry via
 * InvestmentRepository.updateSectorIndustry, so GET /api/portfolio can serve
 * enriched holding metadata from SQLite. A "Unknown"/absent sector is written
 * through as-is (never fabricated); readers fall back to "Unknown".
 *
 * Returns the number of prices written. Exported for tmp_path-scoped tests.
 */
export function persistRefreshedPricesToDb(items: any[], dbPath: string = DOMAIN_MODEL_DB_FILE): number {
    const investmentRepo = new InvestmentRepository(dbPath);
    const portfolioRepo = new PortfolioRepository(dbPath);
    try {
        const now = new Date().toISOString();
        let count = 0;
        for (const item of items) {
            const rawSymbol: string = item?.symbol ?? item?.ticker;
            if (!rawSymbol || rawSymbol === 'USD_CASH') continue;
            const price = item?.price;
            if (typeof price !== 'number' || !Number.isFinite(price) || price <= 0) continue;
            const symbol = normalizeTicker(rawSymbol);
            const investmentId = investmentRepo.resolveInvestmentId(symbol, 'EQUITY', 'USD');
            portfolioRepo.upsertInvestmentPrice(investmentId, price, 'USD', now);
            // Persist sector/industry when the heatmap payload resolved them
            // (present on every fetch_portfolio_heatmap.py stock row). Skip only
            // when neither field is present at all, so a plain price-only item
            // (e.g. a test) never blanks an already-resolved sector.
            const sector = item?.sector;
            const industry = item?.industry;
            if (sector != null || industry != null) {
                investmentRepo.updateSectorIndustry(symbol, sector ?? null, industry ?? null);
            }
            count++;
        }
        return count;
    } finally {
        investmentRepo.close();
        portfolioRepo.close();
    }
}

/**
 * Reconciliation gate: compare our computed portfolio value vs TV broker total.
 * holdings = portfolio.json positions (with stored prices)
 * tvSnapshot = raw TV snapshot object (has snapshots[].balances)
 */
function verifyPortfolioTotals(holdings: any[], tvSnapshot: any): {
    holdingsTotal: number; totalCash: number; computedTotal: number;
    brokerTotal: number; diff: number; pct: number; isValid: boolean;
} {
    const holdingsTotal = holdings
        .filter(p => (p.symbol || p.ticker) !== 'USD_CASH')
        .reduce((sum, p) => sum + (p.shares || 0) * (p.price ?? p.book_price ?? 0), 0);
    const totalCash = (tvSnapshot.snapshots ?? []).reduce((sum: number, snap: any) => {
        return sum + (snap?.balances?.cashUSD ?? 0);
    }, 0);
    const computedTotal = holdingsTotal + totalCash;
    const brokerTotal = (tvSnapshot.snapshots ?? []).reduce((sum: number, snap: any) => {
        const equity = snap?.balances?.totalEquityUSDCombined ?? snap?.balances?.totalEquityUSD ?? 0;
        return sum + (typeof equity === 'number' && equity > 0 ? equity : 0);
    }, 0);
    const diff = computedTotal - brokerTotal;
    const pct = brokerTotal > 0 ? (diff / brokerTotal) * 100 : 0;
    const isValid = Math.abs(diff) <= 200 || Math.abs(pct) <= 0.5;
    return { holdingsTotal, totalCash, computedTotal, brokerTotal, diff, pct, isValid };
}

// ── Portfolio CRUD ────────────────────────────────────────────────────────────

router.get('/', async (_req, res) => {
    try {
        // Wave 3 (completion): prefer SQLite-sourced enriched holdings
        // (account_investment/investment_price + investment.name/sector/industry/
        // pillar_id). Falls back to portfolio.json when SQLite has no held
        // positions yet (e.g. before the first sync/migration).
        const dbHoldings = getHoldingsForDisplayFromDb();
        const { holdings, tvSnapshot } = readPortfolio();
        const dataSource = dbHoldings != null ? 'domain_model_sqlite' : (tvSnapshot?.dataSource ?? 'cache');
        res.json({ items: dbHoldings ?? holdings, dataSource });
    } catch (error) {
        console.error(`[API] Error reading portfolio: `, error);
        res.status(500).json({ error: 'Failed to read portfolio' });
    }
});

router.post('/', async (req, res) => {
    const { items } = req.body;
    console.log(`[API] Saving portfolio with ${items?.length || 0} positions...`);
    try {
        if (!items || !Array.isArray(items)) { res.status(400).json({ error: 'items array required' }); return; }
        backupPortfolio();
        const { totals, tvSnapshot } = readPortfolio();
        fs.writeFileSync(PORTFOLIO_FILE, JSON.stringify({ holdings: items, totals, tvSnapshot }, null, 2));
        // Wave 3 gap (documented, not silently dropped): this route is the
        // manual/UI-triggered position editor (PortfolioModal). It accepts `items`,
        // a flat cross-account-aggregated array with no per-account attribution, so
        // there is no real tvSnapshot.snapshots[].positions[] data for THIS specific
        // edit to attribute to TFSA vs RRSP vs CASH. Writing a fabricated
        // single-account split would corrupt real account_investment data, which is
        // worse than not writing to SQLite here. This portfolio.json write is
        // therefore intentionally retained for the manual-edit path ONLY — it is NOT
        // a sync/promote/apply write (those are now SQLite-only). GET / still prefers
        // SQLite and only falls back to this file when SQLite has no positions.
        res.json({ success: true, count: items.length });
    } catch (error) {
        console.error(`[API] Error saving portfolio: `, error);
        res.status(500).json({ error: 'Failed to save portfolio' });
    }
});

// ── Summary & Performance ─────────────────────────────────────────────────────

router.get('/summary', async (_req, res) => {
    console.log(`[API] Computing portfolio summary...`);
    try {
        const { holdings: positions, totals } = readPortfolio();

        // ── Market value: Wave 3 Task 6 — computed live from domain_model.sqlite
        // (account_investment JOIN investment_price, GROUP BY account_id then summed,
        // per ADR-030 / portfolio_repository.py::get_portfolio_total_value), never read
        // from a stored `totals` block. Falls back to portfolio.json's `totals` (and
        // then to the raw shares*price computation) when SQLite has no priced position
        // data yet — e.g. before the first migrate_portfolio_to_sqlite.py run.
        let totalMarketValueUSD = 0;
        let totalMarketValueCAD = 0;
        let liveUsdCadRate = JAN1_USD_CAD_RATE;
        let priceSource = 'yfinance';

        const dbTotalUSD = getPortfolioTotalUsdFromDb();
        if (dbTotalUSD != null) {
            // Always the live, SQLite-sourced broker_exchange_rate (never the stale
            // portfolio.json totals.exchangeRate — that field is frozen since Wave 3
            // stopped writing portfolio.json; using it here caused Portfolio Summary
            // and Portfolio Table to show two different CAD totals for the same
            // portfolio at the same instant, since stock.ts already always uses
            // getLiveUsdCadRate() unconditionally).
            liveUsdCadRate = await getLiveUsdCadRate(JAN1_USD_CAD_RATE);
            totalMarketValueUSD = dbTotalUSD;
            totalMarketValueCAD = dbTotalUSD * liveUsdCadRate;
            priceSource = 'domain_model_sqlite';
            console.log(`[Summary] totalUSD=$${totalMarketValueUSD.toFixed(2)} (from domain_model.sqlite)`);
        } else if (totals != null && (totals.totalUSD ?? 0) > 0) {
            totalMarketValueUSD = totals.totalUSD!;
            totalMarketValueCAD = totals.totalCAD!;
            liveUsdCadRate = totals.exchangeRate ?? JAN1_USD_CAD_RATE;
            priceSource = 'tradingview';
            console.log(`[Summary] totalUSD=$${totalMarketValueUSD.toFixed(2)} totalCAD=$${totalMarketValueCAD.toFixed(2)}`);
        } else {
            // Fallback: compute from stored prices (before first sync)
            liveUsdCadRate = await getLiveUsdCadRate(JAN1_USD_CAD_RATE);
            for (const pos of positions) {
                totalMarketValueUSD += (pos.shares || 0) * (pos.price ?? pos.book_price ?? 0);
            }
            totalMarketValueCAD = totalMarketValueUSD * liveUsdCadRate;
            console.log(`[Summary] No totals in portfolio.json — computed $${totalMarketValueUSD.toFixed(2)} (fallback)`);
        }

        // Book value + position count: Wave 7 — computed live from
        // account_investment (SUM(quantity * average_cost), COUNT(*)), replacing
        // the prior unconditional read of portfolio.json's `positions[].book_price`/
        // `.length` (frozen since Wave 3 stopped writing that file) even though
        // totalMarketValueUSD above already read SQLite. Falls back to the
        // portfolio.json-derived `positions` only when SQLite has no priced
        // position data yet.
        const dbBookValue = getBookValueAndCountFromDb();
        let totalBookValueUSD: number;
        let positionCount: number;
        if (dbBookValue != null) {
            totalBookValueUSD = dbBookValue.totalBookValueUSD;
            positionCount = dbBookValue.positionCount;
        } else {
            totalBookValueUSD = 0;
            for (const pos of positions) {
                totalBookValueUSD += (pos.shares || 0) * (pos.book_price || 0);
            }
            positionCount = positions.length;
        }
        const totalBookValueCAD = totalBookValueUSD * liveUsdCadRate;

        // Derive the actual "last synced" timestamp. Prefer the real, current
        // SQLite value (MAX(account_investment.last_synced_at), updated on every
        // real sync) over portfolio.json's totals.timestamp/positions[].last_updated
        // — those fields are frozen since Wave 3 stopped writing portfolio.json on
        // every sync path, which is why the UI's "SQLite · <time>" badge never
        // advanced on refresh even though the totals above were already live.
        const dbLastSyncedAt = getLastSyncedAtFromDb();
        const fromTotals = totals?.timestamp ?? null;
        const fromHoldings = positions.reduce((latest: string, item: any) => {
            if (!item.last_updated) return latest;
            return !latest || new Date(item.last_updated) > new Date(latest) ? item.last_updated : latest;
        }, '');
        const lastUpdated = dbLastSyncedAt ?? fromTotals ?? fromHoldings ?? new Date().toISOString();

        // Fetch time-weighted performance metrics from report
        const twrReport = await loadYtdPerformanceReport();

        let ytdStartValueCAD_toUse = twrReport?.starting_balance_cad ?? YTD_START_VALUE_CAD;
        let ytdChangeCAD_toUse = twrReport?.dollar_gain_cad ?? (totalMarketValueCAD - YTD_START_VALUE_CAD);
        let ytdChangePctCAD_toUse = twrReport?.time_weighted_return_pct ?? ((totalMarketValueCAD - YTD_START_VALUE_CAD) / YTD_START_VALUE_CAD) * 100;
        let ytdSimpleReturnPctCAD = twrReport?.simple_return_pct ?? ((totalMarketValueCAD - YTD_START_VALUE_CAD) / YTD_START_VALUE_CAD) * 100;

        const ytdStartValueUSD = ytdStartValueCAD_toUse / JAN1_USD_CAD_RATE;
        const ytdChangeUSD = ytdChangeCAD_toUse / liveUsdCadRate;
        const ytdChangePctUSD = ytdChangePctCAD_toUse;

        res.json({
            positionCount,
            totalMarketValueUSD, totalMarketValueCAD,
            totalBookValueUSD, totalBookValueCAD,
            ytdStartValueCAD: ytdStartValueCAD_toUse,
            ytdStartValueUSD,
            ytdChangeCAD: ytdChangeCAD_toUse,
            ytdChangePctCAD: ytdChangePctCAD_toUse,
            ytdSimpleReturnPctCAD,
            ytdChangeUSD,
            ytdChangePctUSD,
            unrealizedGainUSD: totalMarketValueUSD - totalBookValueUSD,
            unrealizedGainPctUSD: totalBookValueUSD > 0 ? ((totalMarketValueUSD - totalBookValueUSD) / totalBookValueUSD) * 100 : 0,
            unrealizedGainCAD: totalMarketValueCAD - totalBookValueCAD,
            unrealizedGainPctCAD: totalBookValueUSD > 0 ? ((totalMarketValueUSD - totalBookValueUSD) / totalBookValueUSD) * 100 : 0,
            liveUsdCadRate, jan1UsdCadRate: JAN1_USD_CAD_RATE,
            lastUpdated,
            price_source: priceSource,
        });
    } catch (error) {
        console.error(`[API] Error computing portfolio summary: `, error);
        res.status(500).json({ error: 'Failed to compute portfolio summary' });
    }
});

router.get('/performance', async (_req, res) => {
    console.log(`[API] Computing portfolio period performance...`);
    try {
        if (!fs.existsSync(PORTFOLIO_FILE)) { res.status(404).json({ error: 'No portfolio data found' }); return; }
        const data = await spawnPythonScript('portfolio_performance.py', [PORTFOLIO_FILE]);
        res.json(data);
    } catch (error) {
        console.error(`[API] Error computing performance: `, error);
        res.status(500).json({ error: 'Failed to compute portfolio performance' });
    }
});

router.get('/weights', (_req, res) => {
    try {
        // Wave 3 Task 6: prefer domain_model.sqlite; fall back to portfolio.json
        // when SQLite has no priced position data yet.
        const dbWeights = getWeightsFromDb();
        if (dbWeights != null) { res.json(dbWeights); return; }
        const { holdings, totals } = readPortfolio();
        res.json(computeWeightsMap(holdings, totals));
    } catch (err: any) { res.status(500).json({ error: err.message }); }
});

router.get('/status', (_req, res) => {
    try {
        // Wave 7: MAX(account_investment.last_synced_at), the real, current sync
        // timestamp — replaces the prior unconditional read of portfolio.json's
        // totals.timestamp/positions[].last_updated, which was frozen at whatever
        // it held before Wave 3 stopped writing that file. This is why the UI's
        // "SQLite · <time>" badge never advanced on refresh even though the data
        // underneath it was live.
        const lastSync = getLastSyncedAtFromDb();
        res.json({ lastSync });
    } catch { res.status(500).json({ error: 'Failed to get status' }); }
});

// ── Position (price + book + per-account holdings) ───────────────────────────

router.get('/position/:ticker', (req, res) => {
    const ticker = req.params.ticker.toUpperCase();
    try {
        // Wave 7: price/book_price sourced live from investment_price/
        // account_investment (getPositionPriceFromDb), replacing the prior
        // unconditional read of portfolio.json for these two fields (only
        // per-account share counts had already been cut over to SQLite in
        // Wave 3). Falls back to portfolio.json only when this ticker has no
        // investment_price row yet (never synced/priced).
        let price: number | null = null;
        let book_price: number | null = null;
        let portfolioShares: number = 0;
        const dbPrice = getPositionPriceFromDb(ticker);
        if (dbPrice != null) {
            price = dbPrice.price;
            book_price = dbPrice.book_price;
        } else {
            const { holdings: portfolio } = readPortfolio();
            const entry = portfolio.find((p: any) => (p.symbol ?? '').toUpperCase() === ticker);
            if (entry) {
                price = typeof entry.price === 'number' ? entry.price : null;
                book_price = typeof entry.book_price === 'number' ? entry.book_price : null;
                portfolioShares = typeof entry.shares === 'number' ? entry.shares : 0;
            }
        }
        // Per-account quantities from domain_model.sqlite (account_investment).
        const byAccount: Record<string, number> = {};
        const dbRows = getAccountPositionsFromDb(ticker);
        for (const r of dbRows) byAccount[r.accountId] = (byAccount[r.accountId] ?? 0) + r.quantity;
        const accounts = Object.entries(byAccount).map(([account, shares]) => ({ account, shares }));
        const accountTotal = accounts.reduce((s, a) => s + a.shares, 0);
        const totalShares = accountTotal || portfolioShares;
        const unrealizedGain = (price !== null && book_price !== null && totalShares > 0)
            ? (price - book_price) * totalShares : null;
        const unrealizedGainPct = (price !== null && book_price !== null && book_price > 0)
            ? ((price - book_price) / book_price) * 100 : null;
        res.json({ ticker, price, book_price, shares: totalShares, unrealizedGain, unrealizedGainPct, accounts, accountTotal });
    } catch { res.json({ ticker, price: null, book_price: null, shares: 0, unrealizedGain: null, unrealizedGainPct: null, accounts: [], accountTotal: 0 }); }
});

// ── Holdings by Account ───────────────────────────────────────────────────────

router.get('/holdings/:ticker', (req, res) => {
    const ticker = req.params.ticker.toUpperCase();
    try {
        // Wave 3 Task 6: per-account quantity/average_cost from domain_model.sqlite
        // (account_investment), replacing tvSnapshot.positions[]. average_cost maps
        // 1:1 to this route's existing `avgFillPrice` field name.
        const dbRows = getAccountPositionsFromDb(ticker);
        if (dbRows.length > 0) {
            const accounts = dbRows.map(r => ({
                account: r.accountId,
                shares: r.quantity,
                avgFillPrice: r.averageCost != null ? Math.round(r.averageCost * 100) / 100 : null,
            }));
            const total = accounts.reduce((s, a) => s + a.shares, 0);
            const totalCost = accounts.reduce((s, a) => s + (a.avgFillPrice ?? 0) * a.shares, 0);
            const avgFillPrice = total > 0 ? Math.round((totalCost / total) * 100) / 100 : null;
            res.json({ ticker, accounts, total, avgFillPrice, dataSource: 'domain_model_sqlite', timestamp: null });
            return;
        }

        // Fallback: tvSnapshot.positions[] (pre-SQLite-sync data)
        const { tvSnapshot } = readPortfolio();
        if (!tvSnapshot) { res.json({ ticker, accounts: [], total: 0, avgFillPrice: null, dataSource: 'none' }); return; }
        const positions: any[] = tvSnapshot.positions ?? [];
        const matches = positions.filter((p: any) => (p.symbol ?? '').toUpperCase() === ticker);

        // Aggregate per-account: weighted average fill price
        const byAccount: Record<string, { shares: number; costBasis: number }> = {};
        for (const p of matches) {
            const acct = (p.accountType ?? 'UNKNOWN').toUpperCase();
            const qty = p.quantity ?? 0;
            const fill = p.avgFillPrice ?? 0;
            if (!byAccount[acct]) byAccount[acct] = { shares: 0, costBasis: 0 };
            byAccount[acct].shares += qty;
            byAccount[acct].costBasis += qty * fill;
        }
        const accounts = Object.entries(byAccount).map(([account, { shares, costBasis }]) => ({
            account,
            shares,
            avgFillPrice: shares > 0 ? Math.round((costBasis / shares) * 100) / 100 : null,
        }));
        const total = accounts.reduce((s, a) => s + a.shares, 0);
        const totalCost = accounts.reduce((s, a) => s + (a.avgFillPrice ?? 0) * a.shares, 0);
        const avgFillPrice = total > 0 ? Math.round((totalCost / total) * 100) / 100 : null;
        res.json({ ticker, accounts, total, avgFillPrice, dataSource: tvSnapshot.dataSource ?? 'tradingview-cdp', timestamp: tvSnapshot.timestamp ?? null });
    } catch { res.json({ ticker, accounts: [], total: 0, avgFillPrice: null, dataSource: 'error' }); }
});

// ── Refresh & Sync ────────────────────────────────────────────────────────────

router.post('/refresh-prices', async (_req, res) => {
    console.log(`[API] Refreshing portfolio prices from Yahoo...`);
    try {
        // Wave 7: the ticker list to refresh comes live from account_investment,
        // replacing the prior unconditional read of portfolio.json — that file
        // (frozen since Wave 3) meant newly-synced positions never got their
        // prices refreshed here, and closed positions kept getting "refreshed"
        // needlessly. Falls back to portfolio.json only when SQLite has no
        // held positions yet.
        const portfolioData = getHoldingsForDisplayFromDb() ?? readPortfolio().holdings;
        // Refresh scope = held positions PLUS watchlist-only tickers (is_watchlisted=1,
        // no shares). Previously this only covered held positions, so watchlist tickers
        // (fed to the watchlist heatmap, thesis review, etc.) went stale indefinitely —
        // found via a direct investment_price.fetched_at audit on 2026-07-27. Watchlist
        // items carry shares:0 so fetch_portfolio_heatmap.py's math (position_value =
        // shares*price) is a harmless 0, and persistRefreshedPricesToDb still writes
        // their price (it doesn't gate on shares).
        const watchlistData = getWatchlistTickersForRefresh();
        const portfolioDataForRefresh = [...portfolioData, ...watchlistData];
        // Strip stored price so fetch_portfolio_heatmap.py uses live yfinance prices
        const itemsForFetch = portfolioDataForRefresh.map((item: any) => { const { price, ...rest } = item; return rest; });
        // Clear each symbol's stored price BEFORE fetching fresh ones, so a symbol whose
        // fetch fails/times out reads as missing (0/unknown) afterward instead of quietly
        // continuing to serve a stale price forever — the exact failure mode found
        // 2026-07-27 (prices frozen a full day stale with no visible signal).
        clearPricesBeforeRefresh(itemsForFetch.map((item: any) => item.symbol));
        // Wave 3 Task 8: a price-only refresh never triggers a full broker sync, so the
        // stored USD->CAD rate could go stale relative to freshly-refreshed USD prices.
        // fetch_broker_data.py --refresh-exchange-rate does a lightweight balances-only
        // CDP fetch (no full position sync) and persists the rate directly, run here in
        // parallel with the price fetch so the two numbers never drift apart. Best-effort:
        // its failure must not block the price refresh this endpoint exists to perform.
        const [data, exchangeRate] = await Promise.all([
            spawnPythonScript('fetch_portfolio_heatmap.py', [JSON.stringify(itemsForFetch), '--bust-cache']),
            getLiveUsdCadRate(JAN1_USD_CAD_RATE),
            spawnPythonScript('fetch_broker_data.py', ['--refresh-exchange-rate']).catch((err: Error) => {
                console.warn(`[API] Exchange rate refresh during price refresh failed: `, err.message);
                return null;
            }),
        ]);
        if (data.error) { res.status(400).json({ error: data.error }); return; }
        const updatedItems = portfolioDataForRefresh.map((item: any) => {
            const stockData = data.stocks.find((s: any) => s.symbol === item.symbol);
            // Carry the heatmap-resolved sector/industry through so
            // persistRefreshedPricesToDb can persist them into investment.* (the
            // enriched metadata GET /api/portfolio now serves from SQLite).
            return stockData
                ? { ...item, price: stockData.price, sector: stockData.sector, industry: stockData.industry, last_updated: new Date().toISOString() }
                : item;
        });
        // Wave 3 (completion): SQLite-only persistence — this path no longer writes
        // portfolio.json. The freshly-fetched live prices are persisted into
        // `investment_price` (the gap that previously left SQLite prices permanently
        // stale after the one-time migration), which is what /summary, /weights, and
        // /strategy-allocation now read their market values from (Task 6). The flat
        // `updatedItems` array carries no per-account attribution, so account_investment
        // quantities are intentionally left untouched (owned by the sync-tv path). The
        // fresh heatmap prices are still returned inline in this response for the caller.
        const pricesWritten = persistRefreshedPricesToDb(updatedItems);
        console.log(`[Portfolio] refresh-prices: wrote ${pricesWritten} fresh prices to investment_price (SQLite-only, no portfolio.json write).`);
        res.json({ success: true, updated: updatedItems.length, heatmap: { ...data, exchange_rate: exchangeRate } });
    } catch (error) {
        console.error(`[API] Error refreshing prices: `, error);
        res.status(500).json({ error: 'Failed to refresh prices' });
    }
});

router.post('/sync-tv', async (_req, res) => {
    console.log('[API] Triggering TradingView portfolio sync...');
    try {
        const snapshot = await brokerSyncService.syncFromTV();
        const posCount = snapshot.positions?.length ?? 0;
        if (posCount === 0) {
            res.status(503).json({ error: 'TradingView returned 0 positions. Is TradingView Desktop running with a broker connected?' });
            return;
        }
        // Wave 7: diff baseline sourced live from account_investment, replacing
        // the prior unconditional read of portfolio.json — a diff against a
        // frozen 3-day-old file was comparing against the wrong "existing"
        // state, producing wrong added/removed/changed counts.
        const existing = getHoldingsForDisplayFromDb() ?? readPortfolio().holdings;
        const { merged, added, removed, changed } = mergeIntoPortfolio(snapshot, existing);
        res.json({
            success: true, dataSource: 'tradingview-cdp', positionCount: posCount,
            diff: { added, removed, changed }, snapshot, merged,
            message: `TV sync: ${posCount} positions. ${added.length} added, ${removed.length} removed, ${changed.length} changed. Call POST /api/portfolio/sync-tv/promote to persist to domain_model.sqlite.`,
        });
    } catch (error: any) {
        console.error('[API] TV Sync Error:', error);
        res.status(500).json({ error: 'TradingView sync failed', details: error.message });
    }
});

router.post('/sync-tv/promote', async (req, res) => {
    const { merged, snapshot } = req.body;
    if (!Array.isArray(merged) || merged.length === 0) {
        res.status(400).json({ error: 'merged array is required in request body. Call /api/portfolio/sync-tv first.' });
        return;
    }
    // Wave 3 (completion): SQLite-only — no portfolio.json write. When the caller
    // passes back the raw `snapshot` from the preceding /sync-tv response, its real
    // per-account positions/cash + FX rate are persisted to domain_model.sqlite via
    // persistSnapshotToDb (the single shared writer, no duplicated logic). Without a
    // snapshot there is no per-account attribution to write (the flat `merged` array
    // lacks it), so account_investment is left to the /sync-tv/apply or /sync path;
    // thesis shares are still synced from `merged`.
    if (snapshot?.snapshots?.length) {
        try {
            persistSnapshotToDb(snapshot);
        } catch (dbErr: any) {
            console.warn(`[API] promote: failed to persist snapshot to domain_model.sqlite:`, dbErr.message);
        }
    }
    console.log(`[API] TV snapshot promoted to domain_model.sqlite (${merged.length} positions).`);
    res.json({ success: true, positionCount: merged.length, message: 'Portfolio updated from TradingView data (SQLite).' });
});

// One-shot: fetch TV snapshot → merge → write portfolio.json immediately (no HITL gate)
router.post('/sync-tv/apply', async (_req, res) => {
    console.log('[API] TV sync + auto-apply to domain_model.sqlite...');
    try {
        const snapshot = await brokerSyncService.syncFromTV();
        const posCount = snapshot.positions?.length ?? 0;
        if (posCount === 0) {
            console.warn('[API] TradingView returned 0 positions — SQLite holdings unchanged.');
            res.json({ success: true, positionCount: 0, tvAvailable: false, message: 'TradingView not available or returned 0 positions — portfolio unchanged.' });
            return;
        }
        // Wave 7: diff baseline sourced live from account_investment, replacing
        // the prior unconditional read of portfolio.json — a diff against a
        // frozen 3-day-old file was comparing against the wrong "existing"
        // state, producing wrong added/removed/changed counts.
        const existing = getHoldingsForDisplayFromDb() ?? readPortfolio().holdings;
        const { merged, added, removed, changed } = mergeIntoPortfolio(snapshot, existing);
        // Wave 3 (completion): SQLite-only — no portfolio.json write. The fresh
        // snapshot's real per-account positions/cash + FX rate + broker-reported
        // total are persisted to domain_model.sqlite via persistSnapshotToDb (the
        // single shared writer). /summary, /weights, /strategy-allocation, GET /,
        // /position, /holdings all now read from there.
        try {
            persistSnapshotToDb(snapshot);
        } catch (dbErr: any) {
            console.warn(`[API] apply: failed to persist snapshot to domain_model.sqlite:`, dbErr.message);
        }

        // Reconciliation gate — compare stored prices vs TV broker total
        const recon = verifyPortfolioTotals(merged, snapshot);
        if (recon.isValid) {
            console.log(`[Recon] ✅ PASS  computed=$${recon.computedTotal.toFixed(2)} broker=$${recon.brokerTotal.toFixed(2)} diff=$${recon.diff.toFixed(2)} (${recon.pct.toFixed(2)}%)`);
        } else {
            console.error(`[Recon] ❌ MISMATCH  computed=$${recon.computedTotal.toFixed(2)} broker=$${recon.brokerTotal.toFixed(2)} diff=$${recon.diff.toFixed(2)} (${recon.pct.toFixed(2)}%)  — run ↻ Refresh to update stored prices`);
        }

        console.log(`[API] domain_model.sqlite auto-applied from TV (${merged.length} positions).`);
        res.json({ success: true, positionCount: merged.length, tvAvailable: true, diff: { added, removed, changed }, reconciliation: recon });
    } catch (error: any) {
        console.error('[API] TV sync/apply error:', error);
        res.status(500).json({ error: 'TV sync failed', details: error.message });
    }
});

router.post('/sync', async (_req, res) => {
    console.log('[API] Auto portfolio sync (TV → cache)...');
    try {
        const result = await brokerSyncService.syncAuto();
        res.json({ success: true, ...result });
    } catch (error: any) {
        console.error('[API] Auto sync error:', error);
        res.status(500).json({ error: 'Auto sync failed', details: error.message });
    }
});

// ── Strategy Allocation ───────────────────────────────────────────────────────

router.get('/strategy-allocation', async (_req, res) => {
    console.log(`[API] Computing strategy allocation...`);
    try {
        // Wave 8: pillar/sub-strategy mapping sourced live from
        // strategy_pillar/investment (InvestmentRepository.listPillars()/
        // listThesisHoldings()), replacing the prior unconditional read of
        // target-portfolio.json for this mapping.
        const investmentRepo = new InvestmentRepository(DOMAIN_MODEL_DB_FILE);
        let thesis: any;
        try {
            const pillars = investmentRepo.listPillars().map(p => ({ id: p.id, name: p.name }));
            const holdings = investmentRepo.listThesisHoldings().map(h => ({
                ticker: h.ticker, pillarId: h.pillarId, subStrategyId: h.subStrategyId,
            }));
            thesis = { pillars, holdings };
        } finally {
            investmentRepo.close();
        }

        // Wave 3 Task 6: prefer domain_model.sqlite for positions/totals; fall back
        // to portfolio.json when SQLite has no priced position data yet.
        const dbInput = getStrategyAllocationInputFromDb();
        if (dbInput != null) {
            res.json(computeStrategyAllocation(dbInput.positions, dbInput.totals, thesis));
            return;
        }
        const { holdings: positions, totals } = readPortfolio();
        const result = computeStrategyAllocation(positions, totals, thesis);
        res.json(result);
    } catch (error) {
        console.error(`[API] Error computing strategy allocation: `, error);
        res.status(500).json({ error: 'Failed to compute strategy allocation' });
    }
});

export default router;
