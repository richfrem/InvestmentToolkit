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
 *   - syncThesisShares(positions) - Keep thesis holdings[].shares in sync with actual portfolio positions
 *   - verifyPortfolioTotals(holdings, tvSnapshot) - Reconciliation gate comparing computed vs broker total
 *   - persistPortfolioWithSnapshot(items, tvSnapshot) - Writes to portfolio.json with totals and snaps
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
 *   - investment_screener/backend/data/cash_flows.json (Deposit & withdrawal logs)
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
import { PORTFOLIO_FILE, PORTFOLIO_CONFIG_FILE, THESIS_FILE, DOMAIN_MODEL_DB_FILE } from '../utils/paths';
import { buildPortfolioSnapshot, preserveAuthoritativeTotal, computeWeightsMap, PortfolioTotals } from '../utils/portfolioSnapshot';
import { computeStrategyAllocation } from '../utils/strategyAllocation';
import { PortfolioRepository } from '../services/PortfolioRepository';

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
      Checks if cash_flows.json is present, executes ytd_return.py via the Python bridge,
      and loads ytd_performance_report.json. Returns null on failure or if missing.
     */
    const cashFlowsFile = path.join(path.dirname(PORTFOLIO_FILE), 'cash_flows.json');
    const reportFile = path.join(path.dirname(PORTFOLIO_FILE), 'ytd_performance_report.json');
    
    if (!fs.existsSync(cashFlowsFile)) {
        return null;
    }
    
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

/**
 * Keep thesis holdings[].shares in sync with actual portfolio positions.
 * Called after any write to portfolio.json that may change share quantities.
 * - Updates shares on existing thesis holdings.
 * - Removes the shares field when a position is closed.
 * - Adds a stub holding for new tickers not yet in the thesis.
 */
function syncThesisShares(positions: any[]): void {
    if (!fs.existsSync(THESIS_FILE)) return;
    try {
        const thesis = JSON.parse(fs.readFileSync(THESIS_FILE, 'utf-8'));
        const holdings: any[] = thesis.holdings ?? [];

        // ticker → total shares from portfolio.json (skip virtual cash)
        const portfolioMap = new Map<string, number>();
        for (const pos of positions) {
            const sym: string = pos.symbol || pos.ticker;
            if (sym && sym !== 'USD_CASH') portfolioMap.set(sym, pos.shares ?? 0);
        }

        let dirty = false;

        for (const h of holdings) {
            const ticker: string = h.ticker;
            if (!ticker || ticker === 'USD_CASH') continue;

            if (portfolioMap.has(ticker)) {
                const newShares = portfolioMap.get(ticker)!;
                if (h.shares !== newShares) { h.shares = newShares; dirty = true; }
                portfolioMap.delete(ticker);
            } else if (h.shares !== undefined) {
                // Position closed — drop the field so the holding stays as a thesis target
                delete h.shares;
                dirty = true;
            }
        }

        // New tickers not yet tracked in thesis — add minimal stub
        for (const [ticker, shares] of portfolioMap) {
            holdings.push({
                ticker,
                name: ticker,
                pillarId: 'other',
                targetWeight: 0,
                role: 'watchlist',
                thesisForInclusion: '',
                agentRationale: `Added automatically on ${new Date().toISOString().slice(0, 10)}.`,
                shares,
            });
            dirty = true;
            console.log(`[Thesis] New position ${ticker} (${shares} shares) — added stub holding.`);
        }

        if (dirty) {
            thesis.holdings = holdings;
            thesis.updatedAt = new Date().toISOString();
            fs.writeFileSync(THESIS_FILE, JSON.stringify(thesis, null, 2));
            console.log(`[Thesis] Synced shares across ${holdings.length} holdings.`);
        }
    } catch (err: any) {
        console.error('[Thesis] Failed to sync shares:', err.message);
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

/**
 * Single write path — everything goes to portfolio.json as { holdings, totals }.
 * No other file is written. All routes read from this one file.
 */
async function persistPortfolioWithSnapshot(items: any[], tvSnapshot?: any): Promise<void> {
    const tvSnap = tvSnapshot ?? (() => {
        if (fs.existsSync(PORTFOLIO_FILE)) {
            try {
                const raw = JSON.parse(fs.readFileSync(PORTFOLIO_FILE, 'utf-8'));
                if (raw && !Array.isArray(raw) && raw.tvSnapshot) {
                    return raw.tvSnapshot;
                }
            } catch (err: any) {
                console.warn(`[Portfolio] Failed to load cached tvSnapshot:`, err.message);
            }
        }
        return { snapshots: [] };
    })();
    const exchangeRate = await getLiveUsdCadRate(JAN1_USD_CAD_RATE);

    // Sum holdings USD value: sum(shares * price)
    const holdingsUSD = items
        .filter(h => (h.symbol || h.ticker) !== 'USD_CASH')
        .reduce((sum, h) => sum + (h.shares ?? 0) * (h.price ?? h.book_price ?? 0), 0);

    // Sum cash USD value across accounts
    const cashUSD = (tvSnap?.snapshots ?? []).reduce(
        (sum: number, snap: any) => sum + (snap?.balances?.cashUSD ?? 0),
        0
    );

    // Sum cash CAD value across accounts
    const cashCAD = (tvSnap?.snapshots ?? []).reduce(
        (sum: number, snap: any) => sum + (snap?.balances?.cashCAD ?? 0),
        0
    );

    // Calculate total USD from calculated values
    const calculatedTotalUSD = holdingsUSD + cashUSD;

    // Calculate total CAD using calculated USD value converted by TV inferred exchange rate
    // TV inferred exchange rate = totalCAD / totalUSD from snapshot balances
    let inferredRate = exchangeRate;
    let tvTotalUSD = 0;
    let tvTotalCAD = 0;
    for (const snap of (tvSnap?.snapshots ?? [])) {
        const b = snap?.balances;
        if (b) {
            tvTotalUSD += b.totalEquityUSDCombined ?? b.totalEquityUSD ?? 0;
            tvTotalCAD += b.totalEquityCADCombined ?? b.totalEquityCAD ?? 0;
        }
    }
    if (tvTotalUSD > 0 && tvTotalCAD > 0) {
        inferredRate = tvTotalCAD / tvTotalUSD;
    }

    const calculatedTotalCAD = (holdingsUSD * inferredRate) + cashCAD;

    const { holdings: enriched, totals } = buildPortfolioSnapshot(
        items, tvSnap, inferredRate, calculatedTotalUSD
    );

    totals.totalCAD = calculatedTotalCAD;
    totals.totalSource = 'tv_authoritative'; // Derived directly from live TV holdings + cash

    fs.writeFileSync(PORTFOLIO_FILE, JSON.stringify({ holdings: enriched, totals, tvSnapshot: tvSnap }, null, 2));
    console.log(`[Portfolio] Wrote portfolio.json — totalUSD=$${totals.totalUSD.toFixed(2)} totalCAD=$${totals.totalCAD.toFixed(2)}`);

    // Wave 3 Task 5.5: additionally persist tvSnap's real per-account positions/cash
    // into account_investment via BrokerSyncService.persistSnapshotToDb (same helper
    // used by BrokerSyncService.ts's own sync write, per this task's DRY constraint —
    // one upsert-per-holding path, not duplicated here). `totals` (computed USD/CAD
    // aggregates, exchange rates, reconciliation) has no SQLite equivalent per
    // portfolio_repository.py's ADR-030 design (read-time-only, never stored) and is
    // NOT migrated by this call -- only real per-position/cash facts are. This is
    // additive, not a replacement of the JSON write: /summary, /weights,
    // /strategy-allocation, and the totals fields above all still read from
    // portfolio.json and were not part of this wave's read-side cutover.
    if (tvSnap?.snapshots?.length) {
        try {
            persistSnapshotToDb(tvSnap);
        } catch (dbErr: any) {
            console.warn(`[Portfolio] Failed to persist tvSnapshot to domain_model.sqlite:`, dbErr.message);
        }
    }
}


// ── Portfolio CRUD ────────────────────────────────────────────────────────────

router.get('/', async (_req, res) => {
    try {
        const { holdings, tvSnapshot } = readPortfolio();
        const dataSource = tvSnapshot?.dataSource ?? 'cache';
        res.json({ items: holdings, dataSource });
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
        // Wave 3 Task 5.5 gap (documented, not silently dropped): this route accepts
        // `items`, a flat cross-account-aggregated array (a manual/UI-triggered edit
        // path) with no per-account attribution -- unlike persistPortfolioWithSnapshot
        // above, there is no real tvSnapshot.snapshots[].positions[] data for THIS
        // specific edit to attribute to TFSA vs RRSP vs CASH. Writing a fabricated
        // single-account split would corrupt real account_investment data, which is
        // worse than not writing here. The cached tvSnapshot (unchanged by this route)
        // still reflects the last real broker sync and is what
        // persistSnapshotToDb/persistPortfolioWithSnapshot's own call sites persist.
        syncThesisShares(items);
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
        if (!fs.existsSync(PORTFOLIO_FILE)) { res.status(404).json({ error: 'No portfolio data found' }); return; }
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
            liveUsdCadRate = totals?.exchangeRate ?? await getLiveUsdCadRate(JAN1_USD_CAD_RATE);
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

        // Book value from fill prices — never changes on price refresh
        let totalBookValueUSD = 0;
        for (const pos of positions) {
            totalBookValueUSD += (pos.shares || 0) * (pos.book_price || 0);
        }
        const totalBookValueCAD = totalBookValueUSD * liveUsdCadRate;

        // Derive the actual server-side sync timestamp matching `/status` logic
        const fromTotals = totals?.timestamp ?? null;
        const fromHoldings = positions.reduce((latest: string, item: any) => {
            if (!item.last_updated) return latest;
            return !latest || new Date(item.last_updated) > new Date(latest) ? item.last_updated : latest;
        }, '');
        const lastUpdated = fromTotals ?? fromHoldings ?? new Date().toISOString();

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
            positionCount: positions.length,
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
        const { holdings, totals } = readPortfolio();
        // totals.timestamp is written on every sync — prefer it over per-holding last_updated
        const fromTotals = totals?.timestamp ?? null;
        const fromHoldings = holdings.reduce((latest: string, item: any) => {
            if (!item.last_updated) return latest;
            return !latest || new Date(item.last_updated) > new Date(latest) ? item.last_updated : latest;
        }, '');
        const lastSync = fromTotals ?? fromHoldings ?? null;
        res.json({ lastSync });
    } catch { res.status(500).json({ error: 'Failed to get status' }); }
});

// ── Position (price + book + per-account holdings) ───────────────────────────

router.get('/position/:ticker', (req, res) => {
    const ticker = req.params.ticker.toUpperCase();
    try {
        // From portfolio.json: price and book_price
        let price: number | null = null;
        let book_price: number | null = null;
        let portfolioShares: number = 0;
        const { holdings: portfolio, tvSnapshot } = readPortfolio();
        const entry = portfolio.find((p: any) => (p.symbol ?? '').toUpperCase() === ticker);
        if (entry) {
            price = typeof entry.price === 'number' ? entry.price : null;
            book_price = typeof entry.book_price === 'number' ? entry.book_price : null;
            portfolioShares = typeof entry.shares === 'number' ? entry.shares : 0;
        }
        // Wave 3 Task 6: per-account quantities from domain_model.sqlite
        // (account_investment), replacing tvSnapshot.positions[]. Falls back to
        // the tvSnapshot read when SQLite has no rows for this ticker yet.
        const byAccount: Record<string, number> = {};
        const dbRows = getAccountPositionsFromDb(ticker);
        if (dbRows.length > 0) {
            for (const r of dbRows) byAccount[r.accountId] = (byAccount[r.accountId] ?? 0) + r.quantity;
        } else if (tvSnapshot) {
            for (const p of (tvSnapshot.positions ?? [])) {
                if ((p.symbol ?? '').toUpperCase() === ticker) {
                    const acct = (p.accountType ?? 'UNKNOWN').toUpperCase();
                    byAccount[acct] = (byAccount[acct] ?? 0) + (p.quantity ?? 0);
                }
            }
        }
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
        const { holdings: portfolioData } = readPortfolio();
        // Strip stored price so fetch_portfolio_heatmap.py uses live yfinance prices
        const itemsForFetch = portfolioData.map((item: any) => { const { price, ...rest } = item; return rest; });
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
        const updatedItems = portfolioData.map((item: any) => {
            const stockData = data.stocks.find((s: any) => s.symbol === item.symbol);
            return stockData ? { ...item, price: stockData.price, last_updated: new Date().toISOString() } : item;
        });
        backupPortfolio();
        await persistPortfolioWithSnapshot(updatedItems);
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
        const { holdings: existing } = readPortfolio();
        const { merged, added, removed, changed } = mergeIntoPortfolio(snapshot, existing);
        res.json({
            success: true, dataSource: 'tradingview-cdp', positionCount: posCount,
            diff: { added, removed, changed }, snapshot, merged,
            message: `TV sync: ${posCount} positions. ${added.length} added, ${removed.length} removed, ${changed.length} changed. Call POST /api/portfolio/sync-tv/promote to write to portfolio.json.`,
        });
    } catch (error: any) {
        console.error('[API] TV Sync Error:', error);
        res.status(500).json({ error: 'TradingView sync failed', details: error.message });
    }
});

router.post('/sync-tv/promote', async (req, res) => {
    const { merged } = req.body;
    if (!Array.isArray(merged) || merged.length === 0) {
        res.status(400).json({ error: 'merged array is required in request body. Call /api/portfolio/sync-tv first.' });
        return;
    }
    backupPortfolio();
    await persistPortfolioWithSnapshot(merged);
    syncThesisShares(merged);
    console.log(`[API] portfolio.json promoted from TV snapshot (${merged.length} positions).`);
    res.json({ success: true, positionCount: merged.length, message: 'portfolio.json updated from TradingView data.' });
});

// One-shot: fetch TV snapshot → merge → write portfolio.json immediately (no HITL gate)
router.post('/sync-tv/apply', async (_req, res) => {
    console.log('[API] TV sync + auto-apply to portfolio.json...');
    try {
        const snapshot = await brokerSyncService.syncFromTV();
        const posCount = snapshot.positions?.length ?? 0;
        if (posCount === 0) {
            console.warn('[API] TradingView returned 0 positions — portfolio.json unchanged.');
            res.json({ success: true, positionCount: 0, tvAvailable: false, message: 'TradingView not available or returned 0 positions — portfolio unchanged.' });
            return;
        }
        const { holdings: existing } = readPortfolio();
        const { merged, added, removed, changed } = mergeIntoPortfolio(snapshot, existing);
        backupPortfolio();
        await persistPortfolioWithSnapshot(merged, snapshot);
        syncThesisShares(merged);

        // Reconciliation gate — compare stored prices vs TV broker total
        const recon = verifyPortfolioTotals(merged, snapshot);
        if (recon.isValid) {
            console.log(`[Recon] ✅ PASS  computed=$${recon.computedTotal.toFixed(2)} broker=$${recon.brokerTotal.toFixed(2)} diff=$${recon.diff.toFixed(2)} (${recon.pct.toFixed(2)}%)`);
        } else {
            console.error(`[Recon] ❌ MISMATCH  computed=$${recon.computedTotal.toFixed(2)} broker=$${recon.brokerTotal.toFixed(2)} diff=$${recon.diff.toFixed(2)} (${recon.pct.toFixed(2)}%)  — run ↻ Refresh to update stored prices`);
        }

        console.log(`[API] portfolio.json auto-applied from TV (${merged.length} positions).`);
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
        if (!fs.existsSync(PORTFOLIO_FILE)) { res.status(404).json({ error: 'No portfolio data found' }); return; }
        let thesis: any = null;
        if (fs.existsSync(THESIS_FILE)) {
            thesis = JSON.parse(fs.readFileSync(THESIS_FILE, 'utf-8'));
        }
        // Wave 3 Task 6: prefer domain_model.sqlite for positions/totals; fall back
        // to portfolio.json when SQLite has no priced position data yet. `thesis`
        // (pillar/sub-strategy mapping) stays JSON-sourced — out of this task's scope.
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
