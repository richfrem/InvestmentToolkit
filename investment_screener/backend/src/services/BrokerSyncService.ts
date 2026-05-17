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
const PY_SERVICES_DIR   = path.resolve(process.cwd(), 'py_services');
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
            // stderr has informational progress lines — only fail on non-zero exit with no stdout
            if (code !== 0 && !stdout.trim()) {
                reject(new Error(`fetch_broker_data.py failed (exit ${code}): ${stderr.trim().slice(0, 400)}`));
                return;
            }
            try {
                // stdout may have progress lines before the final JSON — find last JSON block
                const lines = stdout.trim().split('\n');
                let json: any = null;
                for (let i = lines.length - 1; i >= 0; i--) {
                    const line = lines[i].trim();
                    if (line.startsWith('{') || line.startsWith('[')) {
                        json = JSON.parse(line);
                        break;
                    }
                }
                if (json === null) json = JSON.parse(stdout.trim());
                resolve(json);
            } catch {
                reject(new Error(`Failed to parse fetch_broker_data.py output: ${stdout.trim().slice(0, 200)}`));
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
    const existingMap = new Map<string, any>();
    for (const item of existing) {
        const sym = item.symbol || item.ticker;
        if (sym && sym !== 'USD_CASH') existingMap.set(sym, item);
    }

    // Aggregate TV positions by symbol (sum quantities across accounts)
    const tvMap = new Map<string, { quantity: number; avgFillPrice: number; accountType: string }>();
    for (const pos of tvSnapshot.positions) {
        if (!pos.symbol) continue;
        if (tvMap.has(pos.symbol)) {
            tvMap.get(pos.symbol)!.quantity += pos.quantity;
        } else {
            tvMap.set(pos.symbol, { quantity: pos.quantity, avgFillPrice: pos.avgFillPrice, accountType: pos.accountType });
        }
    }

    const merged: any[] = [];
    const added: string[] = [];
    const removed: string[] = [];
    const changed: Array<{ symbol: string; field: string; from: any; to: any }> = [];

    // Process TV positions
    for (const [symbol, tv] of tvMap) {
        const ex = existingMap.get(symbol);
        if (!ex) {
            // New position — add with TV data only (no thesis/price yet)
            added.push(symbol);
            merged.push({
                symbol,
                shares:     tv.quantity,
                book_price: tv.avgFillPrice,
                accountType: tv.accountType,
            });
        } else {
            // Existing — update shares and book_price, preserve everything else
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
    // Keep USD_CASH if present (TV tracks it as a balance, not a position)
    for (const [symbol, item] of existingMap) {
        if (symbol === 'USD_CASH') {
            merged.push(item);
        } else {
            removed.push(symbol);
        }
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

    const existing = fs.existsSync(PORTFOLIO_FILE)
        ? JSON.parse(fs.readFileSync(PORTFOLIO_FILE, 'utf-8'))
        : [];
    return {
        dataSource:    'cache',
        positionCount: Array.isArray(existing) ? existing.length : 0,
        message:       tvReachable 
            ? 'TradingView connected but returned no positions — returning cached portfolio.'
            : 'TradingView not reachable — returning cached portfolio.',
    };
}

export const brokerSyncService = { syncFromTV, syncAuto, mergeIntoPortfolio };
