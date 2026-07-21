/**
 * stock.ts - Express routing for individual stock/ETF metrics and search.
 * 
 * Purpose:
 *   Handles Express API routes for looking up stocks, fetching real-time financial metrics,
 *   running valuations, and obtaining ETF allocation details.
 * 
 * Layer:
 *   Backend / Routes / Stock
 * 
 * Routes Index:
 *   - GET /stock/lookup - Builds search dictionaries for tickers
 *   - GET /stock/:ticker - Fetches financial metrics or ETF profile details
 *   - POST /portfolio-heatmap - Fetches aggregated heatmap data for portfolio positions
 *   - GET /market/quotes - Batch quote (bid/ask/price/change) for a comma-separated list of tickers
 * 
 * Key Input Dependencies:
 *   - investment_screener/backend/data/domain_model.sqlite (thesis holdings,
 *     via InvestmentRepository.listThesisHoldings() — rewired off
 *     target-portfolio.json in Wave 2 Task 10/11)
 *   - investment_screener/backend/data/etf_analysis/ (contains processed ETF JSON results)
 *   - investment_screener/backend/data/domain_model.sqlite (portfolio-wide USD
 *     total, via PortfolioRepository.getPortfolioTotalValue() — rewired off
 *     portfolio.json's `totals` block in Wave 3 Task 6, see
 *     getStockTotalsFromDb; falls back to portfolio.json only when SQLite has
 *     no priced position data yet)
 *   - ../services/bridge (for fetch_financials.py, fetch_portfolio_heatmap.py, and fetch_quotes.py)
 *
 * Key Output Dependencies:
 *   None
 */

import express from 'express';
import fs from 'fs';
import path from 'path';
import { spawnPythonScript } from '../services/bridge';
import { getLiveUsdCadRate } from '../utils/helpers';
import { isValidTicker } from '../utils/helpers';
import { ETF_ANALYSIS_DIR, PORTFOLIO_FILE, DOMAIN_MODEL_DB_FILE } from '../utils/paths';
import { buildLookupDictionary } from '../utils/stockLookup';
import { InvestmentRepository } from '../services/InvestmentRepository';
import { PortfolioRepository } from '../services/PortfolioRepository';

const router = express.Router();

/** Wave 3 Task 6: portfolio-wide USD total computed live from
 * domain_model.sqlite (account_investment JOIN investment_price, GROUP BY
 * account_id then summed), reusing PortfolioRepository.getPortfolioTotalValue()
 * — the same function routes/portfolio.ts's /summary calls (per ADR-030 /
 * portfolio_repository.py::get_portfolio_total_value: never a stored `totals`
 * value). Returns null (not 0) when there's no priced position data yet, so
 * POST /portfolio-heatmap falls back to portfolio.json's `totals` block. */
export function getStockTotalsFromDb(dbPath: string = DOMAIN_MODEL_DB_FILE): number | null {
    const repo = new PortfolioRepository(dbPath);
    try {
        const total = repo.getPortfolioTotalValue();
        return total > 0 ? total : null;
    } finally {
        repo.close();
    }
}

router.get('/stock/lookup', async (req, res) => {
    try {
        const repo = new InvestmentRepository(DOMAIN_MODEL_DB_FILE);
        let holdings;
        try {
            holdings = repo.listThesisHoldings();
        } finally {
            repo.close();
        }
        const dict = buildLookupDictionary(holdings);
        res.json(dict);
    } catch (e: any) {
        console.error(`[API] Error building stock lookup: `, e);
        res.status(500).json({ error: 'Failed to build stock lookup' });
    }
});

router.get('/stock/:ticker', async (req, res) => {
    const { ticker } = req.params;
    if (!isValidTicker(ticker)) { res.status(400).json({ error: 'Invalid ticker symbol' }); return; }

    // ETF fast-path
    const etfFile = path.join(ETF_ANALYSIS_DIR, `${ticker}.json`);
    if (fs.existsSync(etfFile)) {
        console.log(`[API] ETF analysis found for ${ticker} — returning ETF profile`);
        try {
            const parsed = JSON.parse(fs.readFileSync(etfFile, 'utf-8'));
            const etf = Array.isArray(parsed) ? parsed[parsed.length - 1] : parsed;
            const snap = etf.snapshot ?? {};
            const holdings = etf.holdingsAnalysis?.topHoldings ?? [];
            res.json({
                symbol: ticker, price: snap.price ?? 0, currency: snap.currency ?? 'USD',
                profile: {
                    type: 'ETF', assetType: 'ETF', sector: 'ETF', industry: etf.fundType ?? 'THEMATIC_ETF',
                    description: etf.rationale ?? '', longName: etf.name ?? ticker, fundFamily: '',
                    expenseRatio: snap.expenseRatio ?? null, aum: snap.aum ?? null,
                    fiftyTwoWeekHigh: snap.fiftyTwoWeekHigh ?? null, fiftyTwoWeekLow: snap.fiftyTwoWeekLow ?? null,
                    topHoldings: holdings, thesisAlignmentScore: etf.holdingsAnalysis?.thesisAlignmentScore ?? null,
                    action: etf.action ?? null, actionRationale: etf.actionRationale ?? null,
                    upsideCatalysts: etf.upsideCatalysts ?? [], risks: etf.risks ?? [],
                    entryNote: etf.entryNote ?? null, analyzedAt: etf.savedAt ?? null,
                },
                metrics: { pe_ratio: 0, forward_pe: 0, market_cap: snap.aum ?? 0, beta: 0, revenue: 0, shares_outstanding: 0 },
                expert_metrics: {
                    rule_of_40: { score: 0, revenue_growth: 0, ebitda_margin: 0, is_saas: false },
                    piotroski_f_score: { score: 0, max: 9, details: {} },
                },
                financials: {
                    historical_revenue: [], historical_net_income: [], historical_fcf: [],
                    historical_gross_margin: [], historical_operating_margin: [],
                    historical_net_margin: [], historical_eps: [],
                },
            });
            return;
        } catch (err) { console.warn(`[API] ETF parse error for ${ticker}:`, err); }
    }

    const fresh = req.query.fresh === 'true';
    console.log(`[API] Fetching data for ${ticker}${fresh ? ' (fresh)' : ''}...`);
    try {
        const data = await spawnPythonScript('fetch_financials.py', fresh ? [ticker, '--no-cache'] : [ticker]);
        if (data.error) { res.status(400).json({ error: data.error }); return; }
        res.json(data);
    } catch (error) {
        console.error(`[API] Error fetching ${ticker}: `, error);
        res.status(500).json({ error: 'Failed to fetch financial data' });
    }
});

router.post('/portfolio-heatmap', async (req, res) => {
    const { items } = req.body;
    console.log(`[API] Fetching heatmap data for ${items?.length || 0} positions...`);
    try {
        if (!items || !Array.isArray(items)) { res.status(400).json({ error: 'items array required' }); return; }
        const invalidTickers = items.filter((item: any) => !isValidTicker(item.symbol));
        if (invalidTickers.length > 0) {
            res.status(400).json({ error: `Invalid ticker symbols: ${invalidTickers.map((i: any) => i.symbol).join(', ')}` });
            return;
        }
        // Wave 3 Task 6: totalUSD computed live from domain_model.sqlite (same
        // getPortfolioTotalValue() source as /summary, so all pages agree),
        // falling back to portfolio.json's `totals` block only when SQLite has
        // no priced position data yet. exchangeRate has no SQLite equivalent
        // (TV broker per-currency balance totals are not a stored table —
        // documented gap, see portfolio_repository.py's load_portfolio_state_from_db
        // and helpers.ts's getLiveUsdCadRate), so it is still inferred/fetched
        // via getLiveUsdCadRate() regardless of totals source.
        let exchangeRate = 1.38;
        let snapshotTotalUSD = 0;
        let snapshotTotalCAD = 0;
        try {
            const dbTotalUSD = getStockTotalsFromDb();
            if (dbTotalUSD != null) {
                exchangeRate = await getLiveUsdCadRate(1.38);
                snapshotTotalUSD = dbTotalUSD;
                snapshotTotalCAD = Math.round(dbTotalUSD * exchangeRate);
            } else if (fs.existsSync(PORTFOLIO_FILE)) {
                const raw = JSON.parse(fs.readFileSync(PORTFOLIO_FILE, 'utf-8'));
                const totals = Array.isArray(raw) ? null : raw.totals;
                if (totals?.exchangeRate > 0) exchangeRate = totals.exchangeRate;
                if (totals?.totalUSD > 0) snapshotTotalUSD = totals.totalUSD;
                if (totals?.totalCAD > 0) snapshotTotalCAD = totals.totalCAD;
            } else {
                exchangeRate = await getLiveUsdCadRate(1.38);
            }
        } catch {
            exchangeRate = await getLiveUsdCadRate(1.38);
        }
        const data = await spawnPythonScript('fetch_portfolio_heatmap.py', [JSON.stringify(items)]);
        if (data.error) { res.status(400).json({ error: data.error }); return; }
        // Use snapshot total (TV broker equity) for header display; heatmap's computed total for % math
        const total_value_usd = snapshotTotalUSD > 0 ? snapshotTotalUSD : data.total_value;
        const total_value_cad = snapshotTotalCAD > 0 ? snapshotTotalCAD : Math.round((data.total_value ?? 0) * exchangeRate);
        res.json({ ...data, exchange_rate: exchangeRate, total_value_usd, total_value_cad });
    } catch (error) {
        console.error(`[API] Error fetching heatmap: `, error);
        res.status(500).json({ error: 'Failed to fetch heatmap data' });
    }
});

// Batch quote: bid/ask/price/change for a comma-separated list of tickers
router.get('/market/quotes', async (req, res) => {
    const raw = String(req.query.tickers ?? '').trim();
    if (!raw) { res.json({}); return; }
    const tickers = raw.split(',').map(t => t.trim().toUpperCase()).filter(Boolean).slice(0, 30);
    try {
        const data = await spawnPythonScript('fetch_quotes.py', [tickers.join(',')]);
        res.json(data);
    } catch (e: any) {
        res.status(500).json({ error: e.message });
    }
});

export default router;
