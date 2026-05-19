/**
 * BrokerSyncService.ts (TypeScript Service)
 * ==========================================
 *
 * Purpose:
 *     Broker-agnostic portfolio sync. Resolves the data source in priority order:
 *     TradingView CDP (primary) → Questrade REST API (optional fallback) → portfolio.json cache.
 *     TV CDP is the default and works for any TradingView-connected broker.
 *
 * Layer: Backend / Services / Data Sync
 *
 * Key Functions:
 *     - syncFromTV()      — Fetches all accounts from TradingView broker panel via CDP
 *     - syncAuto()        — Auto-picks source (TV if reachable, else Questrade, else cache)
 *     - mergeIntoPortfolio() — Merges TV positions into portfolio.json format (preserves thesis/pillar/price)
 */

import { spawn } from 'child_process';
import path from 'path';
import net from 'net';
import fs from 'fs';

const PORTFOLIO_FILE    = path.resolve(__dirname, '../../data/portfolio.json');
const PORTFOLIO_TV_FILE = path.resolve(__dirname, '../../data/portfolio_tv.json');
const PY_SERVICES_DIR   = path.resolve(__dirname, '../../py_services');
const FETCH_BROKER_PY   = path.join(PY_SERVICES_DIR, 'fetch_broker_data.py');

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

function spawnFetchBroker(args: string[], timeoutMs = 120_000): Promise<any> {
    return new Promise((resolve, reject) => {
        const proc = spawn('python3', [FETCH_BROKER_PY, ...args]);
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
            // The script writes portfolio_tv.json — read from there (stdout has progress messages mixed in)
            try {
                const data = JSON.parse(fs.readFileSync(PORTFOLIO_TV_FILE, 'utf-8'));
                resolve(data);
            } catch {
                reject(new Error(`fetch_broker_data.py ran but portfolio_tv.json is missing or invalid`));
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
    dataSource:    'tradingview-cdp' | 'questrade' | 'cache';
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

    // Aggregate TV positions by symbol (sum quantities across accounts, weighted avg fill price)
    const tvMap = new Map<string, { quantity: number; avgFillPrice: number; accountType: string; costBasis: number }>();
    for (const pos of tvSnapshot.positions) {
        if (!pos.symbol) continue;
        const qty = pos.quantity ?? 0;
        const fill = pos.avgFillPrice ?? 0;
        if (tvMap.has(pos.symbol)) {
            const existing = tvMap.get(pos.symbol)!;
            existing.costBasis += qty * fill;
            existing.quantity += qty;
            existing.avgFillPrice = existing.quantity > 0 ? existing.costBasis / existing.quantity : fill;
        } else {
            tvMap.set(pos.symbol, { quantity: qty, avgFillPrice: fill, accountType: pos.accountType, costBasis: qty * fill });
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
                price:       tv.avgFillPrice,  // seed from fill price until next price refresh
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
 * Auto-pick source and sync portfolio.json.
 * Priority: TV CDP → cache (Questrade fallback disabled for pure TV mode).
 */
export async function syncAuto(_questradeSyncFn?: () => Promise<void>): Promise<SyncResult> {
    const tvReachable = await isTVReachable();

    if (tvReachable) {
        try {
            const snapshot = await syncFromTV();
            const posCount = snapshot.positions?.length ?? 0;
            if (posCount > 0) {
                // Write portfolio_tv.json (safe staging file — never overwrites portfolio.json directly)
                fs.mkdirSync(path.dirname(PORTFOLIO_TV_FILE), { recursive: true });
                fs.writeFileSync(PORTFOLIO_TV_FILE, JSON.stringify(snapshot, null, 2));
                console.log(`[BrokerSync] TV sync complete: ${posCount} positions → portfolio_tv.json`);
                return {
                    dataSource:    'tradingview-cdp',
                    positionCount: posCount,
                    message:       `Synced ${posCount} positions from TradingView CDP. Written to portfolio_tv.json. Use /tv-portfolio-sync to review and promote.`,
                    tvSnapshot:    snapshot,
                };
            }
        } catch (err: any) {
            console.warn(`[BrokerSync] TV sync failed: ${err.message}`);
        }
    }

    // Questrade fallback disabled per user request (pure TradingView mode)
    /*
    if (questradeSyncFn) {
        try {
            await questradeSyncFn();
            ...
        }
    }
    */

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

export const brokerSyncService = { syncFromTV, syncAuto, mergeIntoPortfolio };
