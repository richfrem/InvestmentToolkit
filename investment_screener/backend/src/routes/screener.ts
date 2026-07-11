/**
 * src/routes/screener.ts
 * =====================
 *
 * Purpose:
 *   Handles Express API routes for watchlist management, screener calculations,
 *   and fetching python-based actionable opportunities.
 *
 * Key Functions:
 *   - GET /watchlist - Retrieves user watchlist
 *   - POST /watchlist - Adds a ticker to the watchlist
 */

import express from 'express';
import fs from 'fs';
import path from 'path';
import { getPythonActions } from '../utils/helpers';
import { PORTFOLIO_FILE, TARGET_PORTFOLIO_FILE, PORTFOLIO_REVIEWS_DIR } from '../utils/paths';
import { watchlistService } from '../services/WatchlistService';

const router = express.Router();

// GET /api/screener/watchlist
router.get('/watchlist', async (_req, res) => {
    try {
        const watchlist = await watchlistService.getWatchlist();
        res.json(watchlist);
    } catch (err: any) {
        res.status(500).json({ error: err.message });
    }
});

// POST /api/screener/watchlist/add
router.post('/watchlist/add', async (req, res) => {
    const { ticker } = req.body;
    if (!ticker) {
        res.status(400).json({ error: 'Ticker is required' });
        return;
    }
    try {
        await watchlistService.addToWatchlist(ticker);
        res.json({ success: true, message: `${ticker.toUpperCase()} added to watchlist` });
    } catch (err: any) {
        res.status(500).json({ error: err.message });
    }
});

// POST /api/screener/watchlist/remove
router.post('/watchlist/remove', async (req, res) => {
    const { ticker } = req.body;
    if (!ticker) {
        res.status(400).json({ error: 'Ticker is required' });
        return;
    }
    try {
        await watchlistService.removeFromWatchlist(ticker);
        res.json({ success: true, message: `${ticker.toUpperCase()} removed from watchlist` });
    } catch (err: any) {
        res.status(500).json({ error: err.message });
    }
});

// GET /api/screener/all-holdings
router.get('/all-holdings', async (_req, res) => {
    try {
        // 1. Fetch data from all sources
        const watchlistItems = await watchlistService.getWatchlist();
        const watchedTickers = new Set(watchlistItems.map(item => item.ticker));

        const targetPortfolio = JSON.parse(await fs.promises.readFile(TARGET_PORTFOLIO_FILE, 'utf-8'));
        const thesisHoldings: any[] = targetPortfolio.holdings ?? [];
        const thesisMap = new Map(thesisHoldings.map(h => [h.ticker, h]));

        const rawPortfolio = fs.existsSync(PORTFOLIO_FILE)
            ? JSON.parse(fs.readFileSync(PORTFOLIO_FILE, 'utf-8')) : [];
        const positions: any[] = Array.isArray(rawPortfolio) ? rawPortfolio : (rawPortfolio.holdings ?? []);
        
        const totalValue = positions.reduce((s, p) => s + (p.shares || 0) * (p.price || 0), 0);
        const actualMap: Record<string, { pct: number; price: number }> = {};
        for (const p of positions) {
            const ticker = (p.symbol ?? p.ticker) as string;
            if (ticker && totalValue > 0)
                actualMap[ticker] = { pct: ((p.shares || 0) * (p.price || 0) / totalValue) * 100, price: p.price || 0 };
        }

        const actionsMap = await getPythonActions();

        let reviewMap: Record<string, any> = {};
        try {
            await fs.promises.mkdir(PORTFOLIO_REVIEWS_DIR, { recursive: true });
            const files = (await fs.promises.readdir(PORTFOLIO_REVIEWS_DIR))
                .filter(f => f.endsWith('.json') && f.match(/^\d{4}-\d{2}-\d{2}/) && !f.includes('patch'))
                .sort().reverse();
            if (files.length) {
                const raw = JSON.parse(await fs.promises.readFile(path.join(PORTFOLIO_REVIEWS_DIR, files[0]), 'utf-8'));
                for (const h of [...(raw.holdings ?? []), ...(raw.holdingsUnchanged ?? [])]) reviewMap[h.ticker] = h;
            }
        } catch { /* no review file — proceed without */ }

        // Find existing projections (hasValuation)
        const projectionsDir = path.join(path.dirname(PORTFOLIO_FILE), 'projections');
        const projectionTickers = new Set<string>();
        if (fs.existsSync(projectionsDir)) {
            const projFiles = (await fs.promises.readdir(projectionsDir)).filter(f => f.endsWith('.json'));
            for (const f of projFiles) {
                projectionTickers.add(f.replace('.json', '').toUpperCase());
            }
        }

        // 2. Build the union of all tickers
        const allTickers = new Set<string>([
            ...watchedTickers,
            ...thesisMap.keys(),
            ...Object.keys(actualMap),
            ...projectionTickers
        ]);

        // 3. Map each ticker in the union
        const result = Array.from(allTickers).map(ticker => {
            const isCash = ticker === 'USD_CASH' || ticker.includes('CASH');
            const h = thesisMap.get(ticker);
            const live = actualMap[ticker];
            const rev = reviewMap[ticker];
            const hasValuation = projectionTickers.has(ticker);
            const isWatched = watchedTickers.has(ticker);

            // Compute default/fallback actions
            let action = actionsMap[ticker];
            if (!action) {
                if (isWatched) {
                    action = 'WATCHLIST';
                } else if (live && !h) {
                    action = 'EXIT';
                } else {
                    action = 'WATCHLIST';
                }
            }

            return {
                ticker,
                name: h?.name ?? (ticker === 'USD_CASH' ? 'US Dollar Cash' : ticker),
                pillarId: h?.pillarId ?? (isCash ? 'cash' : 'other'),
                subStrategyId: h?.subStrategyId ?? (isCash ? 'cash' : 'other'),
                role: h?.role ?? (live ? 'untracked' : 'watchlist'),
                targetPct: h?.targetWeight ?? null,
                actualPct: live?.pct ?? null,
                currentPrice: live?.price ?? null,
                action,
                rationale: rev?.rationale ?? h?.thesisForInclusion ?? (isWatched ? 'Monitored via Watchlist' : null),
                hasValuation,
                isWatched
            };
        });

        res.json(result);
    } catch (err: any) {
        res.status(500).json({ error: err.message });
    }
});

export default router;

