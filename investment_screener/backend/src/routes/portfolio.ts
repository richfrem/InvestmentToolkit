import express from 'express';
import fs from 'fs';
import path from 'path';
import { spawnPythonScript } from '../services/bridge';
import { questradeSyncService } from '../services/QuestradeSyncService';
import { brokerSyncService, mergeIntoPortfolio } from '../services/BrokerSyncService';
import { getLiveUsdCadRate, isTradingViewConnected } from '../utils/helpers';
import { PORTFOLIO_FILE, PORTFOLIO_CONFIG_FILE, THESIS_FILE } from '../utils/paths';

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
        const positions = JSON.parse(fs.readFileSync(PORTFOLIO_FILE, 'utf-8'));
        let totalMarketValueUSD = 0;
        let totalBookValueUSD = 0;
        for (const pos of positions) {
            totalMarketValueUSD += (pos.shares || 0) * (pos.price || 0);
            totalBookValueUSD += (pos.shares || 0) * (pos.book_price || 0);
        }
        const liveUsdCadRate = await getLiveUsdCadRate(JAN1_USD_CAD_RATE);
        const totalMarketValueCAD = totalMarketValueUSD * liveUsdCadRate;
        const totalBookValueCAD = totalBookValueUSD * liveUsdCadRate;
        const ytdStartValueUSD = YTD_START_VALUE_CAD / JAN1_USD_CAD_RATE;
        const tvConnected = await isTradingViewConnected();
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
            price_source: tvConnected ? 'tradingview' : 'yfinance',
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
        const total = positions.reduce((s, p) => s + (p.shares || 0) * (p.price || 0), 0);
        const map: Record<string, number> = {};
        for (const p of positions) {
            const ticker = p.symbol ?? p.ticker;
            if (ticker && total > 0) map[ticker] = ((p.shares || 0) * (p.price || 0) / total) * 100;
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

// ── Refresh & Sync ────────────────────────────────────────────────────────────

router.post('/refresh-prices', async (_req, res) => {
    console.log(`[API] Refreshing portfolio prices from Yahoo...`);
    try {
        const portfolioData = JSON.parse(fs.readFileSync(PORTFOLIO_FILE, 'utf-8'));
        const [data, exchangeRate] = await Promise.all([
            spawnPythonScript('fetch_portfolio_heatmap.py', [JSON.stringify(portfolioData)]),
            getLiveUsdCadRate(JAN1_USD_CAD_RATE),
        ]);
        if (data.error) { res.status(400).json({ error: data.error }); return; }
        const updatedItems = portfolioData.map((item: any) => {
            const stockData = data.stocks.find((s: any) => s.symbol === item.symbol);
            return stockData ? { ...item, price: stockData.price, last_updated: new Date().toISOString() } : item;
        });
        backupPortfolio();
        fs.writeFileSync(PORTFOLIO_FILE, JSON.stringify(updatedItems, null, 2));
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
    fs.writeFileSync(PORTFOLIO_FILE, JSON.stringify(merged, null, 2));
    console.log(`[API] portfolio.json promoted from TV snapshot (${merged.length} positions).`);
    res.json({ success: true, positionCount: merged.length, message: 'portfolio.json updated from TradingView data.' });
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
