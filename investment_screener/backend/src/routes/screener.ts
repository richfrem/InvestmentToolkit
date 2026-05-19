import express from 'express';
import fs from 'fs';
import path from 'path';
import { getPythonActions } from '../utils/helpers';
import { PORTFOLIO_FILE, TARGET_PORTFOLIO_FILE, PORTFOLIO_REVIEWS_DIR } from '../utils/paths';

const router = express.Router();

// GET /api/screener/all-holdings
router.get('/all-holdings', async (_req, res) => {
    try {
        const targetPortfolio = JSON.parse(await fs.promises.readFile(TARGET_PORTFOLIO_FILE, 'utf-8'));
        const thesisHoldings: any[] = targetPortfolio.holdings ?? [];
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
        const result = thesisHoldings.map((h: any) => {
            const rev = reviewMap[h.ticker];
            const live = actualMap[h.ticker];
            return {
                ticker: h.ticker, name: h.name ?? h.ticker, pillarId: h.pillarId ?? 'other',
                subStrategyId: h.subStrategyId ?? null, role: h.role ?? null,
                targetPct: h.targetWeight ?? null, actualPct: live?.pct ?? null,
                currentPrice: live?.price ?? null, action: actionsMap[h.ticker] ?? 'WATCHLIST',
                rationale: rev?.rationale ?? h.thesisForInclusion ?? null, hasValuation: false,
            };
        });
        const thesisTickers = new Set(thesisHoldings.map((h: any) => h.ticker));
        for (const [ticker, data] of Object.entries(actualMap) as [string, { pct: number; price: number }][]) {
            if (!thesisTickers.has(ticker)) {
                const isCash = ticker === 'USD_CASH' || (ticker as string).includes('CASH');
                result.push({
                    ticker, name: ticker === 'USD_CASH' ? 'US Dollar Cash' : ticker,
                    pillarId: isCash ? 'cash' : 'other', subStrategyId: isCash ? 'cash' : 'other',
                    role: 'untracked', targetPct: null, actualPct: data.pct, currentPrice: data.price,
                    action: actionsMap[ticker] ?? 'EXIT',
                    rationale: 'Cash position — not mapped to a thesis holding', hasValuation: false,
                } as any);
            }
        }
        res.json(result);
    } catch (err: any) { res.status(500).json({ error: err.message }); }
});

export default router;
