/**
 * screener.ts - Express routing for investment screener operations.
 * 
 * Purpose:
 *   Handles Express API routes for watchlist management, screener calculations,
 *   and fetching python-based actionable opportunities.
 * 
 * Layer:
 *   Backend / Routes / Screener
 * 
 * Routes Index:
 *   - GET /watchlist - Retrieves user watchlist
 *   - POST /watchlist/add - Adds a ticker to the watchlist
 *   - POST /watchlist/remove - Removes a ticker from the watchlist
 *   - GET /all-holdings - Aggregates data from watchlist, thesis, actual portfolio, and reviews into a unified map
 * 
 * Key Input Dependencies:
 *   - investment_screener/backend/data/domain_model.sqlite (Live portfolio
 *     positions, via PortfolioRepository.listPositionsBySymbol() — rewired off
 *     portfolio.json in Wave 3 Task 6, see getScreenerPositionsFromDb; falls
 *     back to investment_screener/backend/data/portfolio.json only when
 *     SQLite has no priced position data yet)
 *   - investment_screener/backend/data/domain_model.sqlite (Conviction targets,
 *     via InvestmentRepository.listThesisHoldings() — rewired off
 *     target-portfolio.json in Wave 2 Task 10/11)
 *   - investment_screener/backend/data/portfolio-reviews/ (Review logs)
 *   - ../services/WatchlistService (watchlistService operations)
 *
 * Key Output Dependencies:
 *   None
 */

import express from 'express';
import fs from 'fs';
import path from 'path';
import { getPythonActions } from '../utils/helpers';
import { PORTFOLIO_FILE, PORTFOLIO_REVIEWS_DIR, DOMAIN_MODEL_DB_FILE } from '../utils/paths';
import { watchlistService } from '../services/WatchlistService';
import { InvestmentRepository } from '../services/InvestmentRepository';
import { PortfolioRepository } from '../services/PortfolioRepository';

const router = express.Router();

/** Resolves a ticker's display action when the Python-computed action is
 * absent. Must never default an unwatched ticker to 'WATCHLIST' — that
 * previously mislabeled any researched-but-untracked ticker, and kept
 * showing 'WATCHLIST' even after a ticker was explicitly removed from the
 * watchlist. Returns null (not a placeholder string) when no real action
 * category applies. */
export function resolveFallbackAction(
    isWatched: boolean,
    hasLiveHolding: boolean,
    hasThesis: boolean
): 'WATCHLIST' | 'EXIT' | null {
    if (isWatched) return 'WATCHLIST';
    if (hasLiveHolding && !hasThesis) return 'EXIT';
    return null;
}

/** Wave 3 Task 6: per-symbol {symbol, shares, price} aggregated across accounts
 * from account_investment/investment_price, replacing GET /all-holdings' direct
 * portfolio.json `holdings`/flat-array read. Mirrors routes/portfolio.ts's
 * getWeightsFromDb/getStrategyAllocationInputFromDb pattern: reuses
 * PortfolioRepository.listPositionsBySymbol() rather than new raw SQL, returns
 * null (not []) when SQLite has no priced position data yet so the caller falls
 * back to portfolio.json. */
export function getScreenerPositionsFromDb(
    dbPath: string = DOMAIN_MODEL_DB_FILE
): Array<{ symbol: string; shares: number; price: number }> | null {
    const repo = new PortfolioRepository(dbPath);
    try {
        const positions = repo.listPositionsBySymbol();
        if (positions.length === 0) return null;
        return positions.map(p => ({
            symbol: p.symbol,
            shares: p.quantity,
            price: p.price ?? p.averageCost ?? 0,
        }));
    } finally {
        repo.close();
    }
}

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

        const repo = new InvestmentRepository(DOMAIN_MODEL_DB_FILE);
        let thesisHoldings;
        try {
            thesisHoldings = repo.listThesisHoldings();
        } finally {
            repo.close();
        }
        const thesisMap = new Map(thesisHoldings.map(h => [h.ticker, h]));

        // Wave 3 Task 6: positions sourced live from domain_model.sqlite
        // (account_investment JOIN investment_price via PortfolioRepository),
        // falling back to portfolio.json only when SQLite has no priced
        // position data yet.
        const dbPositions = getScreenerPositionsFromDb();
        const positions: any[] = dbPositions ?? (fs.existsSync(PORTFOLIO_FILE)
            ? (() => {
                const rawPortfolio = JSON.parse(fs.readFileSync(PORTFOLIO_FILE, 'utf-8'));
                return Array.isArray(rawPortfolio) ? rawPortfolio : (rawPortfolio.holdings ?? []);
            })()
            : []);

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
            let action: string | null = actionsMap[ticker];
            if (!action) {
                action = resolveFallbackAction(isWatched, Boolean(live), Boolean(h));
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

