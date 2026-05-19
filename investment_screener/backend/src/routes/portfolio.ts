import express from 'express';
import fs from 'fs';
import path from 'path';
import { spawnPythonScript } from '../services/bridge';
import { questradeSyncService } from '../services/QuestradeSyncService';
import { brokerSyncService, mergeIntoPortfolio } from '../services/BrokerSyncService';
import { getLiveUsdCadRate, isTradingViewConnected } from '../utils/helpers';
import { PORTFOLIO_FILE, PORTFOLIO_CONFIG_FILE, THESIS_FILE, PORTFOLIO_SNAPSHOT_FILE } from '../utils/paths';
import { buildPortfolioSnapshot } from '../utils/portfolioSnapshot';

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
 * Single write path: enriches items with market_value, writes portfolio.json,
 * then writes portfolio_snapshot.json with pre-computed totals.
 * All routes that need total USD/CAD read from the snapshot — never recompute.
 */
async function persistPortfolioWithSnapshot(items: any[], tvSnapshot?: any): Promise<void> {
    const tvSnap = tvSnapshot ?? (() => {
        const tvFile = path.join(path.dirname(PORTFOLIO_FILE), 'portfolio_tv.json');
        return fs.existsSync(tvFile) ? JSON.parse(fs.readFileSync(tvFile, 'utf-8')) : { snapshots: [] };
    })();
    const exchangeRate = await getLiveUsdCadRate(JAN1_USD_CAD_RATE);
    const { holdings: enriched, totals } = buildPortfolioSnapshot(items, tvSnap, exchangeRate);
    fs.writeFileSync(PORTFOLIO_FILE, JSON.stringify(enriched, null, 2));
    fs.writeFileSync(PORTFOLIO_SNAPSHOT_FILE, JSON.stringify({ totals }, null, 2));
    console.log(`[Snapshot] Wrote totals — totalUSD=$${totals.totalUSD.toFixed(2)} totalCAD=$${totals.totalCAD.toFixed(2)} rate=${totals.exchangeRate}`);
}

// ── Portfolio CRUD ────────────────────────────────────────────────────────────

router.get('/', async (_req, res) => {
    try {
        if (!fs.existsSync(PORTFOLIO_FILE)) { res.json({ items: [], dataSource: 'cache' }); return; }
        const data = JSON.parse(fs.readFileSync(PORTFOLIO_FILE, 'utf-8'));
        const tvFile = path.join(path.dirname(PORTFOLIO_FILE), 'portfolio_tv.json');
        let dataSource = 'cache';
        if (fs.existsSync(tvFile)) {
            dataSource = fs.statSync(tvFile).mtimeMs >= fs.statSync(PORTFOLIO_FILE).mtimeMs
                ? 'tradingview-cdp' : 'questrade';
        }
        res.json({ items: data, dataSource });
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
        fs.writeFileSync(PORTFOLIO_FILE, JSON.stringify(items, null, 2));
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
        const positions: any[] = JSON.parse(fs.readFileSync(PORTFOLIO_FILE, 'utf-8'));

        // ── Market value: read from pre-computed snapshot (single source of truth) ──
        let totalMarketValueUSD = 0;
        let totalMarketValueCAD = 0;
        let liveUsdCadRate = JAN1_USD_CAD_RATE;
        let priceSource = 'yfinance';

        if (fs.existsSync(PORTFOLIO_SNAPSHOT_FILE)) {
            try {
                const snap = JSON.parse(fs.readFileSync(PORTFOLIO_SNAPSHOT_FILE, 'utf-8'));
                if (snap?.totals?.totalUSD > 0) {
                    totalMarketValueUSD = snap.totals.totalUSD;
                    totalMarketValueCAD = snap.totals.totalCAD;
                    liveUsdCadRate = snap.totals.exchangeRate ?? JAN1_USD_CAD_RATE;
                    priceSource = 'tradingview';
                    console.log(`[Summary] Read from snapshot — $${totalMarketValueUSD.toFixed(2)} USD`);
                }
            } catch { /* fall through to fallback */ }
        }

        // Fallback: compute from stored prices when no snapshot exists yet
        if (totalMarketValueUSD === 0) {
            liveUsdCadRate = await getLiveUsdCadRate(JAN1_USD_CAD_RATE);
            for (const pos of positions) {
                totalMarketValueUSD += (pos.shares || 0) * (pos.price ?? pos.book_price ?? 0);
            }
            totalMarketValueCAD = totalMarketValueUSD * liveUsdCadRate;
            console.log(`[Summary] Snapshot absent — computed $${totalMarketValueUSD.toFixed(2)} USD (fallback)`);
        }

        // Book value always from portfolio.json fill prices (never changes on price refresh)
        let totalBookValueUSD = 0;
        for (const pos of positions) {
            totalBookValueUSD += (pos.shares || 0) * (pos.book_price || 0);
        }
        const totalBookValueCAD = totalBookValueUSD * liveUsdCadRate;

        const ytdStartValueUSD = YTD_START_VALUE_CAD / JAN1_USD_CAD_RATE;
        res.json({
            positionCount: positions.length,
            totalMarketValueUSD, totalMarketValueCAD,
            totalBookValueUSD, totalBookValueCAD,
            ytdStartValueCAD: YTD_START_VALUE_CAD,
            ytdStartValueUSD,
            ytdChangeCAD: totalMarketValueCAD - YTD_START_VALUE_CAD,
            ytdChangePctCAD: ((totalMarketValueCAD - YTD_START_VALUE_CAD) / YTD_START_VALUE_CAD) * 100,
            ytdChangeUSD: totalMarketValueUSD - ytdStartValueUSD,
            ytdChangePctUSD: ((totalMarketValueUSD - ytdStartValueUSD) / ytdStartValueUSD) * 100,
            unrealizedGainUSD: totalMarketValueUSD - totalBookValueUSD,
            unrealizedGainPctUSD: totalBookValueUSD > 0 ? ((totalMarketValueUSD - totalBookValueUSD) / totalBookValueUSD) * 100 : 0,
            unrealizedGainCAD: totalMarketValueCAD - totalBookValueCAD,
            unrealizedGainPctCAD: totalBookValueUSD > 0 ? ((totalMarketValueUSD - totalBookValueUSD) / totalBookValueUSD) * 100 : 0,
            liveUsdCadRate, jan1UsdCadRate: JAN1_USD_CAD_RATE,
            lastUpdated: new Date().toISOString(),
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
        if (!fs.existsSync(PORTFOLIO_FILE)) { res.json({}); return; }
        const positions: any[] = JSON.parse(fs.readFileSync(PORTFOLIO_FILE, 'utf-8'));
        const marketPrice = (p: any) => p.price ?? p.book_price ?? 0;
        const total = positions.reduce((s, p) => s + (p.shares || 0) * marketPrice(p), 0);
        const map: Record<string, number> = {};
        for (const p of positions) {
            const ticker = p.symbol ?? p.ticker;
            if (ticker && total > 0) map[ticker] = ((p.shares || 0) * marketPrice(p) / total) * 100;
        }
        res.json(map);
    } catch (err: any) { res.status(500).json({ error: err.message }); }
});

router.get('/status', (_req, res) => {
    try {
        if (!fs.existsSync(PORTFOLIO_FILE)) { res.json({ lastSync: null }); return; }
        const data = JSON.parse(fs.readFileSync(PORTFOLIO_FILE, 'utf-8'));
        if (Array.isArray(data) && data.length > 0) {
            const lastSync = data.reduce((latest: string, item: any) => {
                if (!item.last_updated) return latest;
                return !latest || new Date(item.last_updated) > new Date(latest) ? item.last_updated : latest;
            }, '');
            res.json({ lastSync: lastSync || null });
        } else { res.json({ lastSync: null }); }
    } catch { res.status(500).json({ error: 'Failed to get status' }); }
});

// ── Position (price + book + per-account holdings) ───────────────────────────

router.get('/position/:ticker', (req, res) => {
    const ticker = req.params.ticker.toUpperCase();
    const tvFile = path.join(path.dirname(PORTFOLIO_FILE), 'portfolio_tv.json');
    try {
        // From portfolio.json: price and book_price
        let price: number | null = null;
        let book_price: number | null = null;
        let portfolioShares: number = 0;
        if (fs.existsSync(PORTFOLIO_FILE)) {
            const portfolio: any[] = JSON.parse(fs.readFileSync(PORTFOLIO_FILE, 'utf-8'));
            const entry = portfolio.find((p: any) => (p.symbol ?? '').toUpperCase() === ticker);
            if (entry) {
                price = typeof entry.price === 'number' ? entry.price : null;
                book_price = typeof entry.book_price === 'number' ? entry.book_price : null;
                portfolioShares = typeof entry.shares === 'number' ? entry.shares : 0;
            }
        }
        // From portfolio_tv.json: per-account quantities
        const byAccount: Record<string, number> = {};
        if (fs.existsSync(tvFile)) {
            const tv = JSON.parse(fs.readFileSync(tvFile, 'utf-8'));
            for (const p of (tv.positions ?? [])) {
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
    const tvFile = path.join(path.dirname(PORTFOLIO_FILE), 'portfolio_tv.json');
    try {
        if (!fs.existsSync(tvFile)) { res.json({ ticker, accounts: [], total: 0, avgFillPrice: null, dataSource: 'none' }); return; }
        const tv = JSON.parse(fs.readFileSync(tvFile, 'utf-8'));
        const positions: any[] = tv.positions ?? [];
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
        res.json({ ticker, accounts, total, avgFillPrice, dataSource: 'tradingview-cdp', timestamp: tv.timestamp ?? null });
    } catch { res.json({ ticker, accounts: [], total: 0, avgFillPrice: null, dataSource: 'error' }); }
});

// ── Refresh & Sync ────────────────────────────────────────────────────────────

router.post('/refresh-prices', async (_req, res) => {
    console.log(`[API] Refreshing portfolio prices from Yahoo...`);
    try {
        const portfolioData = JSON.parse(fs.readFileSync(PORTFOLIO_FILE, 'utf-8'));
        // Strip stored price so fetch_portfolio_heatmap.py uses live yfinance prices
        const itemsForFetch = portfolioData.map((item: any) => { const { price, ...rest } = item; return rest; });
        const [data, exchangeRate] = await Promise.all([
            spawnPythonScript('fetch_portfolio_heatmap.py', [JSON.stringify(itemsForFetch)]),
            getLiveUsdCadRate(JAN1_USD_CAD_RATE),
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

router.post('/sync-questrade', async (_req, res) => {
    console.log(`[API] Triggering Questrade Portfolio Sync...`);
    try {
        await questradeSyncService.runSync();
        res.json({ success: true, message: 'Questrade portfolio sync completed successfully.' });
    } catch (error: any) {
        console.error(`[API] Questrade Sync Error: `, error);
        res.status(500).json({ error: 'Questrade sync failed', details: error.message });
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
        const existing = fs.existsSync(PORTFOLIO_FILE) ? JSON.parse(fs.readFileSync(PORTFOLIO_FILE, 'utf-8')) : [];
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
        const existing = fs.existsSync(PORTFOLIO_FILE) ? JSON.parse(fs.readFileSync(PORTFOLIO_FILE, 'utf-8')) : [];
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
    console.log('[API] Auto portfolio sync (TV → Questrade → cache)...');
    try {
        const result = await brokerSyncService.syncAuto(() => questradeSyncService.runSync());
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
        const positions: any[] = JSON.parse(fs.readFileSync(PORTFOLIO_FILE, 'utf-8'));
        let pillarMap: Record<string, string> = {};
        let subStrategyMap: Record<string, string> = {};
        let pillars: Array<{ id: string; name: string }> = [];
        if (fs.existsSync(THESIS_FILE)) {
            const thesis = JSON.parse(fs.readFileSync(THESIS_FILE, 'utf-8'));
            pillars = thesis.pillars ?? [];
            for (const h of (thesis.holdings ?? [])) {
                if (h.ticker && h.pillarId) pillarMap[h.ticker] = h.pillarId;
                if (h.ticker && h.subStrategyId) subStrategyMap[h.ticker] = h.subStrategyId;
            }
        }
        const pillarValues: Record<string, number> = {};
        const pillarPositions: Record<string, any[]> = {};
        for (const pos of positions) {
            const value = (pos.shares ?? 0) * (pos.price ?? 0);
            const pillarId = (pos.symbol === 'USD_CASH' || pos.sector === 'CASH') ? 'cash' : (pillarMap[pos.symbol] ?? 'other');
            pillarValues[pillarId] = (pillarValues[pillarId] ?? 0) + value;
            (pillarPositions[pillarId] ??= []).push(pos);
        }
        const totalUSD = Object.values(pillarValues).reduce((a, b) => a + b, 0);
        const pillarNameMap: Record<string, string> = { other: 'Other' };
        for (const p of pillars) pillarNameMap[p.id] = p.name;
        const allocation = Object.entries(pillarValues)
            .map(([id, value]) => ({
                id, name: pillarNameMap[id] ?? id,
                valueUSD: Math.round(value * 100) / 100,
                pct: totalUSD > 0 ? Math.round((value / totalUSD) * 10000) / 100 : 0,
                holdings: (pillarPositions[id] ?? [])
                    .map((pos: any) => ({
                        symbol: pos.symbol as string, name: (pos.name ?? pos.symbol) as string,
                        sector: (pos.sector ?? 'Other') as string,
                        subStrategyId: (subStrategyMap[pos.symbol] ?? (pos.symbol === 'USD_CASH' ? 'cash' : null)) as string | null,
                        shares: (pos.shares ?? 0) as number, price: (pos.price ?? 0) as number,
                        valueUSD: Math.round((pos.shares ?? 0) * (pos.price ?? 0) * 100) / 100,
                        pct: totalUSD > 0 ? Math.round(((pos.shares ?? 0) * (pos.price ?? 0) / totalUSD) * 10000) / 100 : 0,
                    }))
                    .sort((a: any, b: any) => b.valueUSD - a.valueUSD),
            }))
            .filter(a => a.valueUSD > 0)
            .sort((a, b) => b.valueUSD - a.valueUSD);
        res.json({ allocation, totalUSD: Math.round(totalUSD * 100) / 100 });
    } catch (error) {
        console.error(`[API] Error computing strategy allocation: `, error);
        res.status(500).json({ error: 'Failed to compute strategy allocation' });
    }
});

export default router;
