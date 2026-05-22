import express from 'express';
import fs from 'fs';
import path from 'path';
import { spawnPythonScript } from '../services/bridge';
import { getLiveUsdCadRate } from '../utils/helpers';
import { isValidTicker } from '../utils/helpers';
import { ETF_ANALYSIS_DIR, PORTFOLIO_FILE, TARGET_PORTFOLIO_FILE } from '../utils/paths';
import { buildLookupDictionary } from '../utils/stockLookup';

const router = express.Router();

router.get('/stock/lookup', async (req, res) => {
    try {
        if (!fs.existsSync(TARGET_PORTFOLIO_FILE)) {
            res.json({});
            return;
        }
        const raw = fs.readFileSync(TARGET_PORTFOLIO_FILE, 'utf-8');
        const target = JSON.parse(raw);
        const dict = buildLookupDictionary(target.holdings ?? []);
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
        // Read totals from portfolio.json — same source as /summary so all pages agree.
        let exchangeRate = 1.38;
        let snapshotTotalUSD = 0;
        let snapshotTotalCAD = 0;
        try {
            if (fs.existsSync(PORTFOLIO_FILE)) {
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
