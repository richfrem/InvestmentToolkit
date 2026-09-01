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

router.get('/stock/:ticker/technical-analysis', async (req, res) => {
    const { ticker } = req.params;
    if (!isValidTicker(ticker)) {
        res.status(400).json({ error: 'Invalid ticker symbol' });
        return;
    }
    const cleanSym = ticker.toUpperCase();

    try {
        // 1. Query latest TECHNICAL_SWEEP event for this ticker from intelligence.sqlite
        const intelligenceDbPath = path.resolve(__dirname, '../../data/intelligence.sqlite');
        let sweepData: any = null;

        if (fs.existsSync(intelligenceDbPath)) {
            const Database = (await import('better-sqlite3')).default;
            const db = new Database(intelligenceDbPath, { readonly: true });
            try {
                const row = db.prepare(`
                    SELECT payload_json, effective_at 
                    FROM intelligence_event 
                    WHERE event_type = 'TECHNICAL_SWEEP' 
                      AND (instrument_id = ? OR instrument_id = ? OR payload_json LIKE ?)
                    ORDER BY effective_at DESC, event_sequence DESC 
                    LIMIT 1
                `).get(cleanSym, `na-${cleanSym.toLowerCase()}`, `%"ticker": "${cleanSym}"%`) as { payload_json: string; effective_at: string } | undefined;

                if (row && row.payload_json) {
                    sweepData = JSON.parse(row.payload_json);
                    sweepData.effectiveAt = row.effective_at;
                }
            } catch (dbErr) {
                console.warn(`[API] Failed to query intelligence.sqlite for ${cleanSym}:`, dbErr);
            } finally {
                db.close();
            }
        }

        // 2. Query holding info and projection revisions from domain_model.sqlite
        let holdingInfo: { isHolding: boolean; targetWeight: number | null; actualWeight: number | null; role: string | null } = {
            isHolding: false,
            targetWeight: null,
            actualWeight: null,
            role: null,
        };
        let dcfFV: number | null = sweepData?.dcf?.fairValue ?? null;
        let dcfBaseTarget: number | null = sweepData?.dcf?.base ?? null;
        let revisionHistory: Array<{ date: string; fairValue: number; action: string; model: string }> = [];

        if (fs.existsSync(DOMAIN_MODEL_DB_FILE)) {
            const repo = new InvestmentRepository(DOMAIN_MODEL_DB_FILE);
            const projRepo = new (await import('../services/ProjectionRepository')).ProjectionRepository(DOMAIN_MODEL_DB_FILE);
            try {
                const inv = repo.getInvestment(cleanSym);
                const sharesHeld = repo.getSharesHeld(cleanSym);
                if (inv) {
                    holdingInfo.isHolding = sharesHeld > 0;
                    holdingInfo.targetWeight = inv.target_weight ?? null;
                    holdingInfo.actualWeight = null;
                    holdingInfo.role = inv.lifecycle_status ?? null;
                }
                const savedProjections = projRepo.findByTicker(cleanSym);
                if (savedProjections.length > 0) {
                    const latest = savedProjections.sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime())[0];
                    if (latest.aiThesis?.fairValue) {
                        dcfFV = latest.aiThesis.fairValue;
                    }
                    if (latest.scenarios?.base?.scenarioPrice) {
                        dcfBaseTarget = latest.scenarios.base.scenarioPrice;
                    }
                    revisionHistory = savedProjections
                        .filter(p => p.aiThesis?.fairValue)
                        .map(p => ({
                            date: p.savedAt?.split('T')[0] || p.updatedAt?.split('T')[0],
                            fairValue: p.aiThesis!.fairValue,
                            action: p.aiThesis?.action || 'HOLD',
                            model: p.aiThesis?.model || 'AI Model',
                        }))
                        .sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime())
                        .slice(0, 4);
                }
            } catch (tErr) {
                console.warn(`[API] Error reading thesis/projections for ${cleanSym}:`, tErr);
            } finally {
                repo.close();
                projRepo.close();
            }
        }

        // 3. Synthesize TA metrics and Plain-English Advice
        const price = sweepData?.close ?? 0;
        const ema21 = sweepData?.emaFast ?? sweepData?.ema21 ?? (price > 0 ? price * 0.985 : 0);
        const ema50 = sweepData?.emaMid ?? sweepData?.ema50 ?? (price > 0 ? price * 0.95 : 0);
        const ema200 = sweepData?.emaSlow ?? sweepData?.ema200 ?? (price > 0 ? price * 0.88 : 0);
        const adx = sweepData?.adx ?? 20.0;
        const volBias = sweepData?.volBias ?? 0.0;
        const atr = sweepData?.atr ?? (price > 0 ? price * 0.03 : 0);
        const rsi = sweepData?.rsi ?? 50.0;
        const isSqueeze = Boolean(sweepData?.squeezeOn);

        // Derive technical regime
        let regime: 'BULLISH_TREND' | 'BULLISH_CONSOLIDATION' | 'BEARISH_TREND' | 'DISTRIBUTION' | 'COMPRESSION' = 'BULLISH_CONSOLIDATION';
        if (isSqueeze) {
            regime = 'COMPRESSION';
        } else if (price >= ema21 && ema21 >= ema50 && adx >= 25) {
            regime = 'BULLISH_TREND';
        } else if (price >= ema50 && adx < 25) {
            regime = 'BULLISH_CONSOLIDATION';
        } else if (volBias <= -25 && price < ema21) {
            regime = 'DISTRIBUTION';
        } else if (price < ema50 && ema50 < ema200) {
            regime = 'BEARISH_TREND';
        }

        // Derive Technical Action Recommendation
        let technicalAction: 'ACCUMULATE' | 'MAINTAIN' | 'TRIM' | 'EXIT' | 'INITIATE' | 'WATCHLIST' | 'AVOID';
        let actionRationale = '';

        if (holdingInfo.isHolding) {
            if (regime === 'BULLISH_TREND' || (price <= ema21 * 1.02 && price >= ema50 && volBias > -15)) {
                technicalAction = 'ACCUMULATE';
                actionRationale = `${cleanSym} is in a confirmed Bullish Trend trading above its key moving averages (21 EMA: $${ema21.toFixed(2)}). Pullbacks toward support represent high-probability accumulation zones.`;
            } else if (regime === 'DISTRIBUTION' || (dcfFV && price > dcfFV * 1.25) || rsi > 72) {
                technicalAction = 'TRIM';
                actionRationale = `${cleanSym} is showing technical distribution pressure (Vol Bias: ${volBias.toFixed(1)}%) or extended valuation. Consider taking partial profits into strength.`;
            } else if (price < ema50 && volBias < -30) {
                technicalAction = 'EXIT';
                actionRationale = `${cleanSym} has breached key structural support (50 EMA: $${ema50.toFixed(2)}) with elevated selling volume. Risk-reward favors capital preservation.`;
            } else {
                technicalAction = 'MAINTAIN';
                actionRationale = `${cleanSym} is consolidating within a normal statistical volatility band (ATR: $${atr.toFixed(2)}). Maintain current position size and monitor support at $${ema50.toFixed(2)}.`;
            }
        } else {
            // Non-holding / Watchlist
            if ((regime === 'BULLISH_TREND' || regime === 'COMPRESSION') && (dcfFV ? price <= dcfFV * 1.1 : true) && price >= ema50) {
                technicalAction = 'INITIATE';
                actionRationale = `${cleanSym} presents an attractive technical entry shelf near the 21 EMA ($${ema21.toFixed(2)}) with favorable trend momentum (ADX: ${adx.toFixed(1)}).`;
            } else if (price < ema200 || (dcfFV && price > dcfFV * 1.4)) {
                technicalAction = 'AVOID';
                actionRationale = `${cleanSym} is trading in a long-term downtrend beneath its 200 EMA ($${ema200.toFixed(2)}) or is excessively extended. Avoid new exposure until a structural base forms.`;
            } else {
                technicalAction = 'WATCHLIST';
                actionRationale = `${cleanSym} is in a consolidation regime. Keep on active watchlist and wait for a volume-backed breakout or pullback to structural support ($${ema50.toFixed(2)}).`;
            }
        }

        const support1 = ema21 > 0 ? Number(ema21.toFixed(2)) : Number((price * 0.98).toFixed(2));
        const support2 = ema50 > 0 ? Number(ema50.toFixed(2)) : Number((price * 0.95).toFixed(2));
        const macroFloor = ema200 > 0 ? Number(ema200.toFixed(2)) : Number((price * 0.88).toFixed(2));
        const resistance1 = price > 0 ? Number((price * 1.06).toFixed(2)) : 0;
        const baseTarget = dcfBaseTarget ? Number(dcfBaseTarget.toFixed(2)) : (sweepData?.dcf?.base ? Number(sweepData.dcf.base.toFixed(2)) : Number((price * 1.20).toFixed(2)));
        const resistance2 = dcfFV ? Number(dcfFV.toFixed(2)) : Number((price * 1.35).toFixed(2));
        const stopLoss = support2 > 0 ? Number((support2 - atr * 1.5).toFixed(2)) : Number((price * 0.90).toFixed(2));

        // Staged Profit Taking Tiers
        const profitTiers = [
            {
                tier: 1,
                label: 'Tier 1 (Tactical Trim)',
                price: resistance1,
                trimPct: 20,
                gainPct: price > 0 ? Number((((resistance1 - price) / price) * 100).toFixed(1)) : 0,
                basis: 'Resistance / 1.5× ATR Target',
            },
            {
                tier: 2,
                label: 'Tier 2 (Base Case Trim)',
                price: baseTarget,
                trimPct: 30,
                gainPct: price > 0 ? Number((((baseTarget - price) / price) * 100).toFixed(1)) : 0,
                basis: 'DCF Base Target Model',
            },
            {
                tier: 3,
                label: 'Tier 3 (Fair Value / Bull)',
                price: resistance2,
                trimPct: 50,
                gainPct: price > 0 ? Number((((resistance2 - price) / price) * 100).toFixed(1)) : 0,
                basis: 'DCF Fair Value / Expansion Target',
            }
        ];

        res.json({
            ticker: cleanSym,
            price,
            technicalAction,
            regime,
            rationale: actionRationale,
            effectiveAt: sweepData?.effectiveAt ?? new Date().toISOString().split('T')[0],
            keyLevels: {
                support1,
                support2,
                macroFloor,
                resistance1,
                baseTarget,
                resistance2,
                stopLoss,
                atrExpectedSwing: Number(atr.toFixed(2)),
                profitTiers,
            },
            metrics: {
                ema21: Number(ema21.toFixed(2)),
                ema50: Number(ema50.toFixed(2)),
                ema200: Number(ema200.toFixed(2)),
                adx: Number(adx.toFixed(1)),
                volBias: Number(volBias.toFixed(1)),
                atr: Number(atr.toFixed(2)),
                rsi: Number(rsi.toFixed(1)),
                isSqueeze,
            },
            holdingStatus: holdingInfo,
            revisionHistory,
        });
    } catch (err: any) {
        console.error(`[API] Error generating TA summary for ${cleanSym}:`, err);
        res.status(500).json({ error: 'Failed to generate technical analysis summary' });
    }
});

router.get('/stock/:ticker', async (req, res) => {
    const { ticker } = req.params;
    if (!isValidTicker(ticker)) { res.status(400).json({ error: 'Invalid ticker symbol' }); return; }
    const cleanSym = ticker.toUpperCase();

    // ETF fast-path
    const etfFile = path.join(ETF_ANALYSIS_DIR, `${cleanSym}.json`);
    if (fs.existsSync(etfFile)) {
        console.log(`[API] ETF analysis found for ${cleanSym} — returning ETF profile`);
        try {
            const parsed = JSON.parse(fs.readFileSync(etfFile, 'utf-8'));
            const etf = Array.isArray(parsed) ? parsed[parsed.length - 1] : parsed;
            const snap = etf.snapshot ?? {};
            const holdings = etf.holdingsAnalysis?.topHoldings ?? [];
            res.json({
                symbol: cleanSym, price: snap.price ?? 0, currency: snap.currency ?? 'USD',
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
    console.log(`[API] Fetching data for ${cleanSym}${fresh ? ' (fresh)' : ''}...`);
    try {
        const data = await spawnPythonScript('fetch_financials.py', fresh ? [cleanSym, '--no-cache'] : [cleanSym]);
        if (data.error) {
            const isNotFound = /Quote not found|possibly delisted|No data found|Insufficient financial data|404/i.test(data.error);
            res.status(isNotFound ? 404 : 400).json({ error: isNotFound ? `Symbol ${cleanSym} not found` : data.error });
            return;
        }
        res.json(data);
    } catch (error: any) {
        const errorMsg = error?.message || '';
        const isNotFound = /Quote not found|possibly delisted|No data found|Insufficient financial data|404/i.test(errorMsg);
        if (isNotFound) {
            console.warn(`[API] Symbol ${cleanSym} not found: ${errorMsg}`);
            res.status(404).json({ error: `Symbol ${cleanSym} not found` });
            return;
        }
        console.error(`[API] Error fetching ${cleanSym}: `, error);
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
