/**
 * BrokerSyncService.ts (TypeScript Service)
 * ==========================================
 *
 * Purpose:
 *     Broker-agnostic portfolio sync. Resolves the data source in priority order:
 *     TradingView CDP (primary) → portfolio.json cache.
 *     TV CDP is the default and works for any TradingView-connected broker.
 *
 * Layer: Backend / Services / Data Sync
 *
 * Key Input Dependencies:
 *     - investment_screener/backend/data/portfolio.json (Maintains aggregate holdings and TV snapshots)
 *     - investment_screener/backend/data/theses/target-portfolio.json (Maintains active conviction weight mappings)
 *
 * Key Functions:
 *     - syncFromTV()      — Fetches all accounts from TradingView broker panel via CDP
 *     - syncAuto()        — Auto-picks source (TV if reachable, else cache)
 *     - mergeIntoPortfolio() — Merges TV positions into portfolio.json format (preserves thesis/pillar/price)
 */

import { spawn } from 'child_process';
import path from 'path';
import net from 'net';
import fs from 'fs';
import { normalizeTicker } from '../utils/tickerAliases';
import { InvestmentRepository } from './InvestmentRepository';
import { PortfolioRepository } from './PortfolioRepository';
import { DOMAIN_MODEL_DB_FILE } from '../utils/paths';

const PORTFOLIO_FILE    = path.resolve(__dirname, '../../data/portfolio.json');
const PY_SERVICES_DIR   = path.resolve(__dirname, '../../py_services');
const FETCH_BROKER_PY   = path.join(PY_SERVICES_DIR, 'fetch_broker_data.py');

const REAL_ACCOUNTS = new Set(['TFSA', 'RRSP', 'CASH']);

function isTVReachable(port = 9222): Promise<boolean> {
    return new Promise((resolve) => {
        const socket = new net.Socket();
        socket.setTimeout(400);
        socket.on('connect', () => { socket.destroy(); resolve(true); });
        socket.on('timeout', () => { socket.destroy(); resolve(false); });
        socket.on('error', () => resolve(false));
        socket.connect(port, 'localhost');
    });
}

/**
 * Parse the snapshot JSON out of fetch_broker_data.py --snapshot's stdout.
 *
 * Wave 3 completion: the Python script now emits the snapshot as a single-line
 * JSON blob on stdout (all progress on stderr — see emit_snapshot_json). This
 * replaced the former IPC channel where BrokerSyncService re-read
 * portfolio.json.tvSnapshot off disk after the subprocess exited. We parse the
 * LAST non-empty line as JSON so any stray earlier stdout output (e.g. a child
 * process that leaked to stdout) cannot corrupt the parse — the emitted JSON is
 * always the final line.
 */
export function parseSnapshotStdout(stdout: string): any {
    const lines = stdout.split('\n').map((l) => l.trim()).filter((l) => l.length > 0);
    if (lines.length === 0) {
        throw new Error('fetch_broker_data.py produced no stdout — expected a JSON snapshot line');
    }
    const lastLine = lines[lines.length - 1];
    try {
        return JSON.parse(lastLine);
    } catch {
        throw new Error(`fetch_broker_data.py stdout did not end with parseable JSON: ${lastLine.slice(0, 200)}`);
    }
}

export function spawnFetchBroker(
    args: string[],
    timeoutMs = 120_000,
    opts: { command?: string; scriptPath?: string } = {},
): Promise<any> {
    const command = opts.command ?? 'python3';
    const scriptPath = opts.scriptPath ?? FETCH_BROKER_PY;
    return new Promise((resolve, reject) => {
        const proc = spawn(command, [scriptPath, ...args]);
        let stdout = '';
        let stderr = '';
        let killed = false;

        const timer = setTimeout(() => {
            killed = true;
            proc.kill('SIGTERM');
            reject(new Error(`fetch_broker_data.py timed out after ${timeoutMs / 1000}s`));
        }, timeoutMs);

        proc.stdout.on('data', (d) => { stdout += d.toString(); });
        proc.stderr.on('data', (d) => { stderr += d.toString(); });

        proc.on('close', (code) => {
            clearTimeout(timer);
            if (killed) return;
            if (code !== 0) {
                reject(new Error(`fetch_broker_data.py failed (exit ${code}): ${stderr.trim().slice(0, 400)}`));
                return;
            }
            // stdout IPC channel: parse the snapshot straight from stdout — no
            // portfolio.json re-read. Works even when portfolio.json is absent.
            try {
                resolve(parseSnapshotStdout(stdout));
            } catch (err: any) {
                reject(err);
            }
        });

        proc.on('error', (err) => {
            clearTimeout(timer);
            reject(err);
        });
    });
}

export interface TVPosition {
    symbol:       string;
    quantity:     number;
    avgFillPrice: number;
    accountType:  string;
    accountId:    string;
}

export interface TVSnapshot {
    dataSource:  string;
    timestamp:   string;
    accounts:    Array<{ accountType: string; accountId: string; displayText: string }>;
    snapshots:   Array<any>;
    positions:   TVPosition[];
}

export interface SyncResult {
    dataSource:    'tradingview-cdp' | 'cache';
    positionCount: number;
    message:       string;
    tvSnapshot?:   TVSnapshot;
}

/**
 * Fetch full portfolio snapshot from TradingView (all accounts).
 * Returns raw TVSnapshot — caller decides what to do with it.
 */
export async function syncFromTV(): Promise<TVSnapshot> {
    const snapshot = await spawnFetchBroker(['--snapshot']);
    if (snapshot?.error) throw new Error(`TradingView sync error: ${snapshot.error}`);
    return snapshot as TVSnapshot;
}

/**
 * Merge TV positions into existing portfolio.json format.
 * Preserves fields that TV doesn't provide (thesis, pillar, price, sector, etc.)
 * by overlaying TV's symbol/shares/book_price onto the existing records.
 *
 * Positions present in TV but not in portfolio.json are added as new entries.
 * Positions present in portfolio.json but not in TV are removed (closed positions).
 *
 * Returns { merged, added, removed, changed } for HITL diff display.
 */
export function mergeIntoPortfolio(tvSnapshot: TVSnapshot, existing: any[]): {
    merged:   any[];
    added:    string[];
    removed:  string[];
    changed:  Array<{ symbol: string; field: string; from: any; to: any }>;
} {
    // Capture USD_CASH before building existingMap (TV tracks cash as balance, not position)
    const existingCash = existing.find(item => (item.symbol || item.ticker) === 'USD_CASH') ?? null;

    const existingMap = new Map<string, any>();
    for (const item of existing) {
        const sym = item.symbol || item.ticker;
        if (sym && sym !== 'USD_CASH') existingMap.set(sym, item);
    }

    // Aggregate TV positions by symbol (sum quantities across accounts, weighted avg fill price).
    // Symbols are normalized through the broker alias map (PSU.U.TO → PSU-U.TO) —
    // skipping this re-creates the duplicate PSU row in portfolio.json and the thesis.
    const tvMap = new Map<string, { quantity: number; avgFillPrice: number; accountType: string; costBasis: number }>();
    for (const pos of tvSnapshot.positions) {
        if (!pos.symbol) continue;
        const symbol = normalizeTicker(pos.symbol);
        const qty = pos.quantity ?? 0;
        const fill = pos.avgFillPrice ?? 0;
        if (tvMap.has(symbol)) {
            const existing = tvMap.get(symbol)!;
            existing.costBasis += qty * fill;
            existing.quantity += qty;
            existing.avgFillPrice = existing.quantity > 0 ? existing.costBasis / existing.quantity : fill;
        } else {
            tvMap.set(symbol, { quantity: qty, avgFillPrice: fill, accountType: pos.accountType, costBasis: qty * fill });
        }
    }

    // Derive cash balance from TV account snapshots
    let tvCashUSD = 0;
    for (const snap of (tvSnapshot as any).snapshots ?? []) {
        const b = snap.balances ?? {};
        if (b.cashUSD) tvCashUSD += b.cashUSD;
    }

    const merged: any[] = [];
    const added: string[] = [];
    const removed: string[] = [];
    const changed: Array<{ symbol: string; field: string; from: any; to: any }> = [];

    // Process TV positions
    for (const [symbol, tv] of tvMap) {
        const ex = existingMap.get(symbol);
        if (!ex) {
            added.push(symbol);
            merged.push({
                symbol,
                shares:      tv.quantity,
                book_price:  tv.avgFillPrice,
                price:       null,  // no live price yet — heatmap/quotes will fetch from yfinance
                accountType: tv.accountType,
            });
        } else {
            const updated = { ...ex };
            if (Math.abs((ex.shares ?? 0) - tv.quantity) > 0.001) {
                changed.push({ symbol, field: 'shares', from: ex.shares, to: tv.quantity });
                updated.shares = tv.quantity;
            }
            if (Math.abs((ex.book_price ?? 0) - tv.avgFillPrice) > 0.001) {
                changed.push({ symbol, field: 'book_price', from: ex.book_price, to: tv.avgFillPrice });
                updated.book_price = tv.avgFillPrice;
            }
            merged.push(updated);
            existingMap.delete(symbol);
        }
    }

    // Positions in portfolio.json but not in TV → closed/removed
    for (const [symbol, item] of existingMap) {
        removed.push(symbol);
        void item;
    }

    // Always preserve USD_CASH — update from TV balance if available, else keep existing
    if (tvCashUSD > 0) {
        merged.push({
            ...(existingCash ?? { symbol: 'USD_CASH', book_price: 1.0, price: 1.0, name: 'USD Cash', sector: 'Cash', industry: 'Cash' }),
            symbol: 'USD_CASH',
            shares: Math.round(tvCashUSD * 100) / 100,
        });
    } else if (existingCash) {
        merged.push(existingCash);
    }

    return { merged, added, removed, changed };
}

/**
 * Persist a raw TV snapshot's real per-account facts (positions + cash balances)
 * into `account_investment`/`investment` rows, mirroring
 * `migrate_portfolio_to_sqlite.py::run_real_migration`'s per-holding write shape:
 * one `upsertAccountInvestment` call per real position, cash written via the
 * same path as a CASH_USD investment row (not a special-cased column). Only
 * the three real, seeded broker sub-accounts (TFSA/RRSP/CASH) are in scope —
 * anything else is unrecognized and intentionally skipped, matching the
 * migration script's own account allowlist.
 *
 * Wave 3 Task 8 (final dual-write reduction): this is now the SOLE write in
 * `syncAuto()` below — the former `portfolio.json` `tvSnapshot` cache write there
 * was removed. It was safe to drop because `routes/portfolio.ts`'s
 * `/position/:ticker` and `/holdings/:ticker` routes were migrated to read
 * per-account quantities from SQLite (`account_investment`) in Task 6.
 *
 * Wave 3 completion: `fetch_broker_data.py` no longer writes `portfolio.json` at
 * all either — its `--snapshot` mode is now SQLite-only and returns the raw
 * snapshot to us over stdout (parsed by `spawnFetchBroker` via
 * `parseSnapshotStdout`), so the entire live TV sync pipeline is JSON-write-free.
 */
/**
 * Infer the live USD->CAD rate from TV's own native equity totals — replicates
 * helpers.ts::getLiveUsdCadRate()'s exact math: sum totalEquityCADCombined
 * (fallback totalEquityCAD) and totalEquityUSDCombined (fallback totalEquityUSD)
 * across every snapshot, then rate = totalCAD / totalUSD. Returns null when
 * either sum is non-positive. Per CLAUDE.md pitfall #27 the rate is always
 * inferred from these native broker values, never an external FX API.
 */
export function computeExchangeRateFromSnapshot(snapshot: TVSnapshot): number | null {
    let totalCAD = 0;
    let totalUSD = 0;
    for (const snap of (snapshot as any).snapshots ?? []) {
        const b = snap?.balances;
        if (b) {
            totalCAD += Number(b.totalEquityCADCombined ?? b.totalEquityCAD ?? 0);
            totalUSD += Number(b.totalEquityUSDCombined ?? b.totalEquityUSD ?? 0);
        }
    }
    if (totalUSD > 0 && totalCAD > 0) return totalCAD / totalUSD;
    return null;
}

/**
 * Sum the broker's OWN reported equity totals across snapshots —
 * totalEquityUSDCombined (fallback totalEquityUSD) and totalEquityCADCombined
 * (fallback totalEquityCAD). Returns the broker's last-reported portfolio total
 * ({totalUsd, totalCad}), the figure verify_portfolio_total.py reconciles the
 * computed total against, or null when no USD equity total is present. Mirrors
 * routes/portfolio.ts::persistPortfolioWithSnapshot's tvTotalUSD/tvTotalCAD sum.
 */
export function computeBrokerReportedTotalFromSnapshot(snapshot: TVSnapshot): { totalUsd: number; totalCad: number } | null {
    let totalUsd = 0;
    let totalCad = 0;
    for (const snap of (snapshot as any).snapshots ?? []) {
        const b = snap?.balances;
        if (b) {
            totalUsd += Number(b.totalEquityUSDCombined ?? b.totalEquityUSD ?? 0);
            totalCad += Number(b.totalEquityCADCombined ?? b.totalEquityCAD ?? 0);
        }
    }
    if (totalUsd > 0) return { totalUsd, totalCad };
    return null;
}

export function persistSnapshotToDb(snapshot: TVSnapshot, dbPath: string = DOMAIN_MODEL_DB_FILE): void {
    const investmentRepo = new InvestmentRepository(dbPath);
    const portfolioRepo = new PortfolioRepository(dbPath);
    try {
        const now = new Date().toISOString();
        for (const snap of (snapshot as any).snapshots ?? []) {
            const accountId: string = snap.accountType;
            if (!REAL_ACCOUNTS.has(accountId)) continue;
            portfolioRepo.upsertAccount(accountId, accountId, accountId);

            // A fresh TV snapshot for this account is the complete, authoritative
            // current state, not a partial diff — clear all of this account's
            // existing rows first so a position fully closed/sold since the last
            // sync (and therefore absent from this snapshot) doesn't linger as a
            // stale nonzero-quantity row inflating future computed totals.
            portfolioRepo.clearAccountInvestments(accountId);

            const cashUsd = Number(snap.balances?.cashUSD ?? 0);
            if (cashUsd > 0) {
                const cashInvestmentId = investmentRepo.resolveInvestmentId('CASH_USD', 'CASH', 'USD');
                portfolioRepo.upsertAccountInvestment(accountId, cashInvestmentId, cashUsd, 1.0, cashUsd, 'USD', now);
                // getAccountMarketValues() INNER JOINs against investment_price -- without
                // this, a CASH_USD account_investment row with no matching price row
                // silently contributes $0 to the computed portfolio total (2026-07-23 bug).
                portfolioRepo.upsertInvestmentPrice(cashInvestmentId, 1.0, 'USD', now);
            }

            for (const pos of snap.positions ?? []) {
                const quantity = Number(pos.quantity ?? 0);
                if (quantity <= 0) continue; // closed/flattened position — no noise row
                const symbol = normalizeTicker(pos.symbol);
                const investmentId = investmentRepo.resolveInvestmentId(symbol, 'EQUITY', 'USD');
                portfolioRepo.upsertAccountInvestment(
                    accountId, investmentId, quantity, pos.avgFillPrice ?? null, null, 'USD', now
                );
            }
        }

        // Wave 3 Task 8: store the single broker-reported FX fact (USD->CAD),
        // inferred from the SAME native TV totals helpers.ts::getLiveUsdCadRate()
        // uses. Only the scalar rate is stored (ADR-030 addendum), never a CAD total.
        const rate = computeExchangeRateFromSnapshot(snapshot);
        if (rate !== null) portfolioRepo.upsertExchangeRate(rate, now);

        // Wave 3 Task 8 (tvSnapshot closure): store the broker's own last-reported
        // portfolio total for verify_portfolio_total.py's reconciliation audit.
        // 'tv_authoritative' matches the totalSource fetch_broker_data.py stamps.
        const brokerTotal = computeBrokerReportedTotalFromSnapshot(snapshot);
        if (brokerTotal !== null) {
            portfolioRepo.upsertBrokerReportedTotal(brokerTotal.totalUsd, brokerTotal.totalCad, now, 'tv_authoritative');
        }
    } finally {
        investmentRepo.close();
        portfolioRepo.close();
    }
}

/**
 * Auto-pick source and sync portfolio.json.
 * Priority: TV CDP → cache.
 */
export async function syncAuto(): Promise<SyncResult> {
    const tvReachable = await isTVReachable();

    if (tvReachable) {
        try {
            const snapshot = await syncFromTV();
            const posCount = snapshot.positions?.length ?? 0;
            if (posCount > 0) {
                // Wave 3 Task 8 (final dual-write reduction): the raw tvSnapshot is
                // persisted to the domain model (SQLite) via persistSnapshotToDb —
                // reading the same in-memory `snapshot` object, no portfolio.json
                // read/merge/write. The former portfolio.json tvSnapshot cache write
                // here was redundant (fetch_broker_data.py already wrote it during
                // syncFromTV) and its read-side consumers (/position, /holdings) were
                // migrated to SQLite in Task 6, so this JSON write was removed.
                try {
                    persistSnapshotToDb(snapshot);
                } catch (dbErr: any) {
                    console.warn(`[BrokerSync] Failed to persist snapshot to domain_model.sqlite:`, dbErr.message);
                }
                console.log(`[BrokerSync] TV sync complete: ${posCount} positions → domain_model.sqlite (domain model)`);
                return {
                    dataSource:    'tradingview-cdp',
                    positionCount: posCount,
                    message:       `Synced ${posCount} positions from TradingView CDP. Persisted to the domain model (SQLite). Use /tv-portfolio-sync to review and promote.`,
                    tvSnapshot:    snapshot,
                };
            }
        } catch (err: any) {
            console.warn(`[BrokerSync] TV sync failed: ${err.message}`);
        }
    }

    const rawExisting = fs.existsSync(PORTFOLIO_FILE)
        ? JSON.parse(fs.readFileSync(PORTFOLIO_FILE, 'utf-8'))
        : [];
    const existing = Array.isArray(rawExisting) ? rawExisting : (rawExisting.holdings ?? []);
    return {
        dataSource:    'cache',
        positionCount: existing.length,
        message:       tvReachable 
            ? 'TradingView connected but returned no positions — returning cached portfolio.'
            : 'TradingView not reachable — returning cached portfolio.',
    };
}

export const brokerSyncService = { syncFromTV, syncAuto, mergeIntoPortfolio, persistSnapshotToDb, computeExchangeRateFromSnapshot, computeBrokerReportedTotalFromSnapshot };
