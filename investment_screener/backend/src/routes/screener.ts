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
 *     positions, via PortfolioRepository.listPositionsBySymbol(), see
 *     getScreenerPositionsFromDb; no priced positions gives an empty list)
 *   - investment_screener/backend/data/domain_model.sqlite (Conviction targets,
 *     via InvestmentRepository.listThesisHoldings())
 *   - investment_screener/backend/data/portfolio-reviews/ (Review logs)
 *   - ../services/WatchlistService (watchlistService operations)
 *
 * Key Output Dependencies:
 *   None
 */

import express from 'express';
import fs from 'fs';
import path from 'path';
import { getRecommendations } from '../utils/helpers';
import { DATA_DIR, PORTFOLIO_REVIEWS_DIR, DOMAIN_MODEL_DB_FILE } from '../utils/paths';
import { watchlistService } from '../services/WatchlistService';
import { InvestmentRepository } from '../services/InvestmentRepository';
import { PortfolioRepository } from '../services/PortfolioRepository';
import { getWeightsFromDb } from './portfolio';

const router = express.Router();

/** One current recommendation record per ticker for all web surfaces. */
router.get('/recommendations', async (_req, res) => {
    try {
        res.json(await getRecommendations());
    } catch (error: any) {
        res.status(503).json({ error: error.message });
    }
});

/** Per-symbol {symbol, shares, price} aggregated across accounts from
 * account_investment/investment_price, for GET /all-holdings. Mirrors
 * routes/portfolio.ts's getWeightsFromDb/getStrategyAllocationInputFromDb pattern: reuses
 * PortfolioRepository.listPositionsBySymbol() rather than new raw SQL, and returns
 * null (not []) when SQLite has no priced position data yet. */
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

/**
 * Builds the `{ ticker: { pct, price } }` map `/all-holdings` exposes as
 * `actualPct`/`currentPrice`. Prefers `dbWeights` (getWeightsFromDb() —
 * routes/portfolio.ts's canonical weight computation, the same one
 * `/api/portfolio/weights` serves) for `pct` whenever a ticker is present
 * there, falling back to an independent shares*price/totalValue computation
 * only for tickers `dbWeights` doesn't cover (e.g. no priced positions yet).
 *
 * Before this fix, `/all-holdings` always reimplemented its own pct math
 * from `positions` directly, completely independent of `getWeightsFromDb()`.
 * Both were individually self-consistent (each summed to 100% in isolation),
 * but the frontend's per-row fallback chains (ScreenerTable.tsx) could pick
 * up either source depending on row type, and any symbol-normalization
 * difference between the two (e.g. CASH_USD vs USD_CASH) meant the two
 * sources didn't always agree ticker-for-ticker — surfacing as the
 * portfolio-wide current-weight total not summing to 100% in the UI even
 * though each backend endpoint's own total did. Exported for testing.
 */
export function buildActualPctMap(
    positions: Array<{ symbol?: string; ticker?: string; shares?: number; price?: number }>,
    dbWeights: Record<string, number> | null
): Record<string, { pct: number; price: number }> {
    const totalValue = positions.reduce((s, p) => s + (p.shares || 0) * (p.price || 0), 0);
    const actualMap: Record<string, { pct: number; price: number }> = {};
    for (const p of positions) {
        const ticker = (p.symbol ?? p.ticker) as string;
        if (!ticker) continue;
        const fallbackPct = totalValue > 0 ? ((p.shares || 0) * (p.price || 0) / totalValue) * 100 : 0;
        const pct = dbWeights?.[ticker] ?? fallbackPct;
        actualMap[ticker] = { pct, price: p.price || 0 };
    }
    return actualMap;
}

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

        // Positions come live from domain_model.sqlite (account_investment JOIN investment_price
        // via PortfolioRepository); no priced positions gives an empty list.
        const positions: any[] = getScreenerPositionsFromDb() ?? [];

        const dbWeights = getWeightsFromDb();
        const actualMap = buildActualPctMap(positions, dbWeights);

        const recommendations = await getRecommendations();

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
        const projectionsDir = path.join(DATA_DIR, 'projections');
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

            // The action is the canonical recommendation verbatim (no fallbacks here).
            const rec = recommendations[ticker] ?? null;
            const action: string | null = rec?.action ?? null;

            return {
                ticker,
                name: h?.name ?? (ticker === 'USD_CASH' ? 'US Dollar Cash' : ticker),
                assetClass: h?.assetClass ?? (ticker.includes('CASH') ? 'CASH' : 'EQUITY'),
                pillarId: h?.pillarId ?? (isCash ? 'cash' : 'other'),
                subStrategyId: h?.subStrategyId ?? (isCash ? 'cash' : 'other'),
                role: h?.role ?? (live ? 'untracked' : 'watchlist'),
                targetPct: h?.targetWeight ?? null,
                actualPct: live?.pct ?? null,
                currentPrice: live?.price ?? null,
                action,
                recommendation: rec,
                rationale: rev?.rationale ?? h?.agentRationale ?? h?.thesisForInclusion ?? (isWatched ? 'Monitored via Watchlist' : null),
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

