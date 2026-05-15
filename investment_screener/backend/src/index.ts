/**
 * index.ts (Express Server Entry Point)
 * =====================================
 *
 * Purpose:
 *     The primary backend orchestrator for the InvestmentToolkit. Handles API routing, Python process bridging,
 *     data persistence for portfolios and projections, and secure integration with external financial services (Questrade, Exchange Rates).
 *
 * Layer: Backend / Core
 *
 * Usage Examples:
 *     node dist/index.js (Production)
 *     npm run dev (Development via ts-node-dev)
 *
 * Key Functions:
 *     - spawnPythonScript() - Bridges Node.js requests to the Python financial data engine (fetch_financials.py, etc.)
 *     - questradeSyncService.runSync() - Coordinates the automated brokerage data synchronization lifecycle
 *     - projectionService.saveProjection() - Manages the validation and archival of AI-generated stock valuation models
 */
import express from 'express';
import dotenv from 'dotenv';
import path from 'path';
import net from 'net';

// Initialize environment variables from the project root .env
dotenv.config({ path: path.resolve(__dirname, '../../../.env') });

import cors from 'cors';
import fs from 'fs';
import { spawnPythonScript } from './services/bridge';
import { questradeSyncService } from './services/QuestradeSyncService';
import { projectionService } from './services/ProjectionService';

const app = express();
const port = process.env.PORT || 3001;

app.use(cors());
app.use(express.json({ limit: '1mb' })); // raised from 50kb — v1.2 projections with analyticsLog can be 50-200kb

const PORTFOLIO_FILE = path.join(__dirname, '../data/portfolio.json');
const PORTFOLIO_EXAMPLE = PORTFOLIO_FILE + '.example';
const ETF_ANALYSIS_DIR = path.join(__dirname, '../data/etf_analysis');

// On startup, seed portfolio.json from .example if it doesn't exist (clean clone)
if (!fs.existsSync(PORTFOLIO_FILE) && fs.existsSync(PORTFOLIO_EXAMPLE)) {
    fs.copyFileSync(PORTFOLIO_EXAMPLE, PORTFOLIO_FILE);
    console.log('[Init] Created portfolio.json from .example');
}

function isTradingViewConnected(tvPort = 9222): Promise<boolean> {
    return new Promise((resolve) => {
        const socket = new net.Socket();
        socket.setTimeout(300);
        socket.on('connect', () => { socket.destroy(); resolve(true); });
        socket.on('timeout', () => { socket.destroy(); resolve(false); });
        socket.on('error', () => resolve(false));
        socket.connect(tvPort, 'localhost');
    });
}

// Validates ticker symbols: 1-10 uppercase alphanumeric chars, dots, hyphens (e.g. BRK-B, BTC-USD)
const isValidTicker = (ticker: string): boolean => /^[A-Z0-9.\-_]{1,10}$/.test(ticker);

app.get('/health', (_req, res) => {
    res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

app.get('/api/stock/:ticker', async (req, res) => {
    const { ticker } = req.params;
    if (!isValidTicker(ticker)) {
        res.status(400).json({ error: 'Invalid ticker symbol' });
        return;
    }

    // ETF fast-path: if we have a saved ETF analysis, return it shaped as StockData
    const etfFile = path.join(ETF_ANALYSIS_DIR, `${ticker}.json`);
    if (fs.existsSync(etfFile)) {
        console.log(`[API] ETF analysis found for ${ticker} — returning ETF profile`);
        try {
            const parsed = JSON.parse(fs.readFileSync(etfFile, 'utf-8'));
            // persist_etf_analysis.py stores as an array of versions; take the latest
            const etf = Array.isArray(parsed) ? parsed[parsed.length - 1] : parsed;
            const snap = etf.snapshot ?? {};
            const holdings = etf.holdingsAnalysis?.topHoldings ?? [];
            const etfResponse = {
                symbol: ticker,
                price: snap.price ?? 0,
                currency: snap.currency ?? 'USD',
                profile: {
                    type: 'ETF',
                    assetType: 'ETF',
                    sector: 'ETF',
                    industry: etf.fundType ?? 'THEMATIC_ETF',
                    description: etf.rationale ?? '',
                    longName: etf.name ?? ticker,
                    fundFamily: '',
                    expenseRatio: snap.expenseRatio ?? null,
                    aum: snap.aum ?? null,
                    fiftyTwoWeekHigh: snap.fiftyTwoWeekHigh ?? null,
                    fiftyTwoWeekLow: snap.fiftyTwoWeekLow ?? null,
                    topHoldings: holdings,
                    thesisAlignmentScore: etf.holdingsAnalysis?.thesisAlignmentScore ?? null,
                    action: etf.action ?? null,
                    actionRationale: etf.actionRationale ?? null,
                    upsideCatalysts: etf.upsideCatalysts ?? [],
                    risks: etf.risks ?? [],
                    entryNote: etf.entryNote ?? null,
                    analyzedAt: etf.savedAt ?? null,
                },
                metrics: {
                    pe_ratio: 0, forward_pe: 0, market_cap: snap.aum ?? 0,
                    beta: 0, revenue: 0, shares_outstanding: 0,
                },
                expert_metrics: {
                    rule_of_40: { score: 0, revenue_growth: 0, ebitda_margin: 0, is_saas: false },
                    piotroski_f_score: { score: 0, max: 9, details: {} },
                },
                financials: {
                    historical_revenue: [], historical_net_income: [], historical_fcf: [],
                    historical_gross_margin: [], historical_operating_margin: [],
                    historical_net_margin: [], historical_eps: [],
                },
            };
            res.json(etfResponse);
            return;
        } catch (err) {
            console.warn(`[API] ETF analysis parse error for ${ticker}:`, err);
            // fall through to normal fetch
        }
    }

    console.log(`[API] Fetching data for ${ticker}...`);
    try {
        const data = await spawnPythonScript('fetch_financials.py', [ticker]);
        if (data.error) {
            res.status(400).json({ error: data.error });
            return;
        }
        res.json(data);
    } catch (error) {
        console.error(`[API] Error fetching ${ticker}: `, error);
        res.status(500).json({ error: 'Failed to fetch financial data' });
    }
});

app.post('/api/portfolio-heatmap', async (req, res) => {
    const { items } = req.body;
    console.log(`[API] Fetching heatmap data for ${items?.length || 0} positions...`);
    try {
        if (!items || !Array.isArray(items)) {
            res.status(400).json({ error: 'items array required' });
            return;
        }
        const invalidTickers = items.filter((item: any) => !isValidTicker(item.symbol));
        if (invalidTickers.length > 0) {
            res.status(400).json({ error: `Invalid ticker symbols: ${invalidTickers.map((i: any) => i.symbol).join(', ')} ` });
            return;
        }
        const data = await spawnPythonScript('fetch_portfolio_heatmap.py', [JSON.stringify(items)]);
        if (data.error) {
            res.status(400).json({ error: data.error });
            return;
        }
        res.json(data);
    } catch (error) {
        console.error(`[API] Error fetching heatmap: `, error);
        res.status(500).json({ error: 'Failed to fetch heatmap data' });
    }
});

app.get('/api/portfolio', async (_req, res) => {
    try {
        if (!fs.existsSync(PORTFOLIO_FILE)) {
            res.json({ items: [] });
            return;
        }
        const data = JSON.parse(fs.readFileSync(PORTFOLIO_FILE, 'utf-8'));
        res.json({ items: data });
    } catch (error) {
        console.error(`[API] Error reading portfolio: `, error);
        res.status(500).json({ error: 'Failed to read portfolio' });
    }
});

// --- Portfolio Summary (YTD Performance & Total Value) ---

const YTD_START_VALUE_CAD = 34126.27;
const JAN1_USD_CAD_RATE = 1.3723;

app.get('/api/portfolio/summary', async (_req, res) => {
    console.log(`[API] Computing portfolio summary...`);
    try {
        if (!fs.existsSync(PORTFOLIO_FILE)) {
            res.status(404).json({ error: 'No portfolio data found' });
            return;
        }

        const positions = JSON.parse(fs.readFileSync(PORTFOLIO_FILE, 'utf-8'));

        // Compute totals in USD (all holdings are US stocks)
        let totalMarketValueUSD = 0;
        let totalBookValueUSD = 0;

        for (const pos of positions) {
            const marketVal = (pos.shares || 0) * (pos.price || 0);
            const bookVal = (pos.shares || 0) * (pos.book_price || 0);
            totalMarketValueUSD += marketVal;
            totalBookValueUSD += bookVal;
        }

        // Fetch live USD/CAD exchange rate
        const apiKey = process.env.EXCHANGE_RATE_API_KEY;
        let liveUsdCadRate = JAN1_USD_CAD_RATE; // fallback

        if (apiKey) {
            try {
                const rateResponse = await fetch(
                    `https://v6.exchangerate-api.com/v6/${apiKey}/pair/USD/CAD`
                );
                const rateData = await rateResponse.json();
                if (rateData.result === 'success') {
                    liveUsdCadRate = rateData.conversion_rate;
                }
            } catch (err) {
                console.warn('[API] Exchange rate fetch failed, using fallback rate');
            }
        }

        // Convert to CAD using live rate
        const totalMarketValueCAD = totalMarketValueUSD * liveUsdCadRate;
        const totalBookValueCAD = totalBookValueUSD * liveUsdCadRate;

        // YTD calculations (starting value is in CAD)
        const ytdStartValueCAD = YTD_START_VALUE_CAD;
        const ytdStartValueUSD = ytdStartValueCAD / JAN1_USD_CAD_RATE;
        const ytdChangeCAD = totalMarketValueCAD - ytdStartValueCAD;
        const ytdChangePctCAD = ((totalMarketValueCAD - ytdStartValueCAD) / ytdStartValueCAD) * 100;
        const ytdChangeUSD = totalMarketValueUSD - ytdStartValueUSD;
        const ytdChangePctUSD = ((totalMarketValueUSD - ytdStartValueUSD) / ytdStartValueUSD) * 100;

        // Book vs Market (unrealized gain/loss)
        const unrealizedGainUSD = totalMarketValueUSD - totalBookValueUSD;
        const unrealizedGainPctUSD = totalBookValueUSD > 0
            ? ((totalMarketValueUSD - totalBookValueUSD) / totalBookValueUSD) * 100
            : 0;
        const unrealizedGainCAD = totalMarketValueCAD - totalBookValueCAD;
        const unrealizedGainPctCAD = unrealizedGainPctUSD; // same % regardless of currency

        const tvConnected = await isTradingViewConnected();

        res.json({
            positionCount: positions.length,
            // Market value
            totalMarketValueUSD,
            totalMarketValueCAD,
            // Book value
            totalBookValueUSD,
            totalBookValueCAD,
            // YTD
            ytdStartValueCAD,
            ytdStartValueUSD,
            ytdChangeCAD,
            ytdChangePctCAD,
            ytdChangeUSD,
            ytdChangePctUSD,
            // Unrealized gain/loss
            unrealizedGainUSD,
            unrealizedGainPctUSD,
            unrealizedGainCAD,
            unrealizedGainPctCAD,
            // Exchange rates
            liveUsdCadRate,
            jan1UsdCadRate: JAN1_USD_CAD_RATE,
            lastUpdated: new Date().toISOString(),
            price_source: tvConnected ? 'tradingview' : 'yfinance',
        });
    } catch (error) {
        console.error(`[API] Error computing portfolio summary: `, error);
        res.status(500).json({ error: 'Failed to compute portfolio summary' });
    }
});

// --- Portfolio Period Performance (1d / 1w / 1m changes via yfinance) ---

app.get('/api/portfolio/performance', async (_req, res) => {
    console.log(`[API] Computing portfolio period performance...`);
    try {
        if (!fs.existsSync(PORTFOLIO_FILE)) {
            res.status(404).json({ error: 'No portfolio data found' });
            return;
        }
        const data = await spawnPythonScript('portfolio_performance.py', [PORTFOLIO_FILE]);
        res.json(data);
    } catch (error) {
        console.error(`[API] Error computing performance: `, error);
        res.status(500).json({ error: 'Failed to compute portfolio performance' });
    }
});

// --- Portfolio Strategy Allocation (actual value by thesis pillar) ---

const THESIS_FILE = path.join(__dirname, '../data/theses/target-portfolio.json');

app.get('/api/portfolio/strategy-allocation', async (_req, res) => {
    console.log(`[API] Computing strategy allocation...`);
    try {
        if (!fs.existsSync(PORTFOLIO_FILE)) {
            res.status(404).json({ error: 'No portfolio data found' });
            return;
        }

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
            const pillarId = (pos.symbol === 'USD_CASH' || pos.sector === 'CASH')
                ? 'cash'
                : (pillarMap[pos.symbol] ?? 'other');
            pillarValues[pillarId] = (pillarValues[pillarId] ?? 0) + value;
            (pillarPositions[pillarId] ??= []).push(pos);
        }

        const totalUSD = Object.values(pillarValues).reduce((a, b) => a + b, 0);

        const pillarNameMap: Record<string, string> = { other: 'Other' };
        for (const p of pillars) pillarNameMap[p.id] = p.name;

        const allocation = Object.entries(pillarValues)
            .map(([id, value]) => ({
                id,
                name: pillarNameMap[id] ?? id,
                valueUSD: Math.round(value * 100) / 100,
                pct: totalUSD > 0 ? Math.round((value / totalUSD) * 10000) / 100 : 0,
                holdings: (pillarPositions[id] ?? [])
                    .map((pos: any) => ({
                        symbol: pos.symbol as string,
                        name: (pos.name ?? pos.symbol) as string,
                        sector: (pos.sector ?? 'Other') as string,
                        subStrategyId: (subStrategyMap[pos.symbol] ?? (pos.symbol === 'USD_CASH' ? 'cash' : null)) as string | null,
                        shares: (pos.shares ?? 0) as number,
                        price: (pos.price ?? 0) as number,
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

app.post('/api/portfolio', async (req, res) => {
    const { items } = req.body;
    console.log(`[API] Saving portfolio with ${items?.length || 0} positions...`);
    try {
        if (!items || !Array.isArray(items)) {
            res.status(400).json({ error: 'items array required' });
            return;
        }
        fs.writeFileSync(PORTFOLIO_FILE, JSON.stringify(items, null, 2));
        res.json({ success: true, count: items.length });
    } catch (error) {
        console.error(`[API] Error saving portfolio: `, error);
        res.status(500).json({ error: 'Failed to save portfolio' });
    }
});

app.post('/api/portfolio/refresh-prices', async (_req, res) => {
    console.log(`[API] Refreshing portfolio prices from Yahoo...`);
    try {
        // Read current portfolio from disk (gitignored local file)
        const portfolioData = JSON.parse(fs.readFileSync(PORTFOLIO_FILE, 'utf-8'));

        // Fetch updated prices
        const data = await spawnPythonScript('fetch_portfolio_heatmap.py', [JSON.stringify(portfolioData)]);

        if (data.error) {
            res.status(400).json({ error: data.error });
            return;
        }

        // Update portfolio with current prices
        const updatedItems = portfolioData.map((item: any) => {
            const stockData = data.stocks.find((s: any) => s.symbol === item.symbol);
            if (stockData) {
                return {
                    ...item,
                    price: stockData.price,
                    last_updated: new Date().toISOString()
                };
            }
            return item;
        });

        // Save updated portfolio
        fs.writeFileSync(PORTFOLIO_FILE, JSON.stringify(updatedItems, null, 2));

        res.json({
            success: true,
            updated: updatedItems.length,
            heatmap: data
        });
    } catch (error) {
        console.error(`[API] Error refreshing prices: `, error);
        res.status(500).json({ error: 'Failed to refresh prices' });
    }
});

app.post('/api/portfolio/sync-questrade', async (_req, res) => {
    console.log(`[API] Triggering Questrade Portfolio Sync...`);
    try {
        await questradeSyncService.runSync();
        res.json({
            success: true,
            message: 'Questrade portfolio sync completed successfully.'
        });
    } catch (error: any) {
        console.error(`[API] Questrade Sync Error: `, error);
        res.status(500).json({
            error: 'Questrade sync failed',
            details: error.message
        });
    }
});

app.post('/api/questrade/seed', async (req, res) => {
    const { refreshToken } = req.body;
    if (!refreshToken) {
        res.status(400).json({ error: 'refreshToken is required' });
        return;
    }

    console.log(`[API] Seeding Questrade refresh token...`);
    try {
        // Exchange the one-week app token for a proper OAuth2 refresh token.
        // Questrade portal tokens are single-use; the exchange produces the long-lived token.
        const exchangeUrl = `https://login.questrade.com/oauth2/token?grant_type=refresh_token&refresh_token=${encodeURIComponent(refreshToken)}`;
        const exchangeRes = await fetch(exchangeUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: '',
        });
        if (!exchangeRes.ok) {
            const errText = await exchangeRes.text();
            console.error(`[API][Seed] Token exchange failed: ${errText}`);
            res.status(400).json({ error: 'Token exchange failed. Ensure you are using a fresh one-week token from the Questrade portal.', details: errText });
            return;
        }
        const exchangeData: any = await exchangeRes.json();
        const seedToken: string = exchangeData.refresh_token;
        if (!seedToken) {
            res.status(400).json({ error: 'Token exchange did not return a refresh_token.' });
            return;
        }
        console.log(`[API][Seed] Token exchanged successfully.`);

        const { spawn } = require('child_process');
        // __dirname is dist/ at runtime; Python scripts live in src/
        const enginePath = path.resolve(__dirname, '../src/QuestradeDataEngine.py');
        const args = ['--cache-dir', path.resolve(__dirname, '../'), '--seed', seedToken];

        console.log(`[API][Seed] Spawning: python3 ${enginePath} ${args.join(' ')} `);
        const pythonProcess = spawn('python3', [enginePath, ...args]);

        let output = '';
        let errorOutput = '';

        pythonProcess.stdout.on('data', (data: any) => {
            output += data.toString();
            console.log(`[API][Seed][Python] ${data.toString().trim()} `);
        });

        pythonProcess.stderr.on('data', (data: any) => {
            errorOutput += data.toString();
            console.error(`[API][Seed][Error] ${data.toString().trim()} `);
        });

        pythonProcess.on('close', (code: number) => {
            if (code === 0) {
                console.log(`[API][Seed] Success.`);
                res.json({ success: true, message: 'Refresh token seeded successfully.' });
            } else {
                console.error(`[API][Seed] Failed with code ${code}.Error: ${errorOutput} `);
                res.status(500).json({
                    error: `Seeding failed with code ${code} `,
                    details: errorOutput || 'Unknown error'
                });
            }
        });
    } catch (error: any) {
        console.error(`[API] Seeding Error: `, error);
        res.status(500).json({ error: error.message });
    }
});


// --- AI Analyst Routes (Tool A) ---

import { valuationService } from './services/ValuationService';

app.post('/api/analysis/valuation', async (req, res) => {
    const { ticker, userMessage } = req.body;
    console.log(`[API] AI Valuation Request for ${ticker}...`);

    try {
        if (!ticker) {
            res.status(400).json({ error: 'Ticker is required' });
            return;
        }

        const result = await valuationService.analyzeStock(ticker, userMessage);
        res.json(result);

    } catch (error: any) {
        console.error(`[API] Valuation Error: `, error);
        res.status(500).json({
            error: 'AI Analysis Failed',
            details: error.message
        });
    }
});

// GET /api/portfolio/weights — percentage weight of every live holding (shares * price / total)
app.get('/api/portfolio/weights', (_req, res) => {
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
    } catch (err: any) {
        res.status(500).json({ error: err.message });
    }
});

app.get('/api/portfolio/status', (req, res) => {
    try {
        if (!fs.existsSync(PORTFOLIO_FILE)) {
            res.json({ lastSync: null });
            return;
        }
        const data = JSON.parse(fs.readFileSync(PORTFOLIO_FILE, 'utf-8'));
        if (Array.isArray(data) && data.length > 0) {
            // Find the most recent last_updated timestamp
            const lastSync = data.reduce((latest: string, item: any) => {
                if (!item.last_updated) return latest;
                return !latest || new Date(item.last_updated) > new Date(latest) ? item.last_updated : latest;
            }, '');
            res.json({ lastSync: lastSync || null });
        } else {
            res.json({ lastSync: null });
        }
    } catch (error) {
        res.status(500).json({ error: 'Failed to get status' });
    }
});

// --- Valuation Persistence Routes ---

const RESEARCH_DIR = path.join(__dirname, '..', 'data', 'research');

// GET /api/research/:filename — returns markdown content for a research report
app.get('/api/research/:filename', async (req, res) => {
    try {
        const { filename } = req.params;

        // Sanitize: only allow TICKER_DATE.md pattern
        if (!/^[A-Z0-9.-]{1,10}_\d{4}-\d{2}-\d{2}\.md$/.test(filename)) {
            res.status(400).json({ error: 'Invalid filename format. Expected: TICKER_YYYY-MM-DD.md' });
            return;
        }

        const filepath = path.join(RESEARCH_DIR, filename);
        // Security check: ensure path resolves to RESEARCH_DIR
        if (!path.resolve(filepath).startsWith(path.resolve(RESEARCH_DIR))) {
            res.status(403).json({ error: 'Access denied' });
            return;
        }

        const content = await fs.promises.readFile(filepath, 'utf-8');

        res.json({
            filename,
            content,
            ticker: filename.split('_')[0],
            date: filename.split('_')[1].replace('.md', ''),
        });
    } catch (err: any) {
        if (err.code === 'ENOENT') {
            res.status(404).json({ error: 'Research report not found' });
            return;
        }
        console.error(`[API] Error reading research report:`, err);
        res.status(500).json({ error: 'Failed to read research report' });
    }
});

// GET /api/research — list all available research reports
app.get('/api/research', async (_req, res) => {
    try {
        await fs.promises.mkdir(RESEARCH_DIR, { recursive: true });
        const files = await fs.promises.readdir(RESEARCH_DIR);
        const reports = files
            .filter(f => f.endsWith('.md'))
            .map(f => ({
                filename: f,
                ticker: f.split('_')[0],
                date: f.split('_')[1].replace('.md', ''),
            }))
            .sort((a, b) => b.date.localeCompare(a.date)); // newest first
        res.json({ reports });
    } catch (err: any) {
        console.error(`[API] Error listing research reports:`, err);
        res.json({ reports: [] });
    }
});

// Projections API
app.get('/api/projections', async (req, res) => {
    try {
        const projections = await projectionService.getAllProjections();
        res.json(projections);
    } catch (error) {
        console.error(`[API] Error getting all projections:`, error);
        res.status(500).json({ error: 'Failed to fetch projections' });
    }
});

app.get('/api/projections/:ticker', async (req, res) => {
    const { ticker } = req.params;
    if (!isValidTicker(ticker)) {
        res.status(400).json({ error: 'Invalid ticker symbol' });
        return;
    }
    try {
        const projections = await projectionService.getProjections(ticker);
        res.json(projections);
    } catch (error: any) {
        console.error(`[API] Error fetching projections for ${ticker}:`, error);
        res.status(500).json({ error: 'Failed to fetch projections' });
    }
});

app.post('/api/projections', async (req, res) => {
    try {
        const projection = req.body;
        // Limit payload size check if needed, but express.json limit is global.
        // We could check content-length header here but let's rely on global or add middleware if needed.
        // Red Team mentioned adding payload limit. 
        // We didn't change specific limit in `app.use(express.json())` yet.
        await projectionService.saveProjection(projection);
        res.json({ success: true, message: 'Projection saved successfully' });
    } catch (error: any) {
        console.error(`[API] Error saving projection:`, error);
        if (error.message.includes('Validation Failed')) {
            res.status(400).json({ error: error.message });
        } else if (error.message.includes('Conflict')) {
            res.status(409).json({ error: error.message });
        } else {
            res.status(500).json({ error: 'Failed to save projection' });
        }
    }
});

app.delete('/api/projections/:ticker/:id', async (req, res) => {
    const { ticker, id } = req.params;
    if (!isValidTicker(ticker)) {
        res.status(400).json({ error: 'Invalid ticker symbol' });
        return;
    }
    try {
        const result = await projectionService.deleteProjection(ticker, id);
        if (result) {
            res.json({ success: true, message: 'Projection deleted' });
        } else {
            res.status(404).json({ error: 'Projection not found' });
        }
    } catch (error: any) {
        console.error(`[API] Error deleting projection:`, error);
        res.status(500).json({ error: 'Failed to delete projection' });
    }
});

// --- Thesis Routes (Tool B) ---

import { thesisService } from './services/ThesisService';

app.get('/api/theses', async (_req, res) => {
    const theses = await thesisService.listTheses();
    res.json(theses);
});

app.get('/api/theses/pillars', async (_req, res) => {
    try {
        if (!fs.existsSync(THESIS_FILE)) {
            res.json([]);
            return;
        }
        const thesis = JSON.parse(fs.readFileSync(THESIS_FILE, 'utf-8'));
        res.json(thesis.pillars ?? []);
    } catch (err: any) {
        res.status(500).json({ error: err.message });
    }
});

app.get('/api/theses/:id', async (req, res) => {
    const { id } = req.params;
    const thesis = await thesisService.getThesis(id);
    if (thesis) {
        res.json(thesis);
    } else {
        res.status(404).json({ error: 'Thesis not found' });
    }
});

app.get('/api/theses/:id/health', async (req, res) => {
    const { id } = req.params;
    try {
        const health = await thesisService.computeHealthCheck(id);
        res.json(health);
    } catch (error: any) {
        console.error(`[API] Error computing health check for ${id}:`, error);
        res.status(500).json({ error: error.message || 'Failed to compute health check' });
    }
});

app.post('/api/theses/:id/strategic-review', async (req, res) => {
    const { id } = req.params;
    try {
        const result = await thesisService.performStrategicReview(id);
        res.json(result);
    } catch (error: any) {
        console.error(`[API] Error performing strategic review for ${id}:`, error);
        res.status(500).json({ error: error.message });
    }
});

app.post('/api/theses/:id/optimize', async (req, res) => {
    const { id } = req.params;
    try {
        const result = await thesisService.optimizePortfolio(id);
        res.json(result);
    } catch (error: any) {
        console.error(`[API] Error optimizing thesis ${id}:`, error);
        res.status(500).json({ error: error.message || 'Failed to optimize portfolio' });
    }
});

app.post('/api/theses', async (req, res) => {
    try {
        const thesis = req.body;
        await thesisService.saveThesis(thesis);
        res.json({ success: true, message: 'Thesis saved successfully', id: thesis.id });
    } catch (error: any) {
        console.error(`[API] Error saving thesis:`, error);
        if (error.message.includes('Validation Failed')) {
            res.status(400).json({ error: error.message });
        } else if (error.message.includes('Conflict')) {
            res.status(409).json({ error: error.message });
        } else {
            res.status(500).json({ error: 'Failed to save thesis' });
        }
    }
});

app.patch('/api/theses/:id/holdings/:ticker', async (req, res) => {
    const { id, ticker } = req.params;
    const updates = req.body;
    try {
        const updatedThesis = await thesisService.updateHolding(id, ticker, updates);
        res.json(updatedThesis);
    } catch (error: any) {
        console.error(`[API] Error updating holding ${ticker}:`, error);
        res.status(500).json({ error: error.message });
    }
});

app.post('/api/theses/:id/holdings', async (req, res) => {
    const { id } = req.params;
    const holding = req.body;
    try {
        const updatedThesis = await thesisService.addHolding(id, holding);
        res.json(updatedThesis);
    } catch (error: any) {
        console.error(`[API] Error adding holding to ${id}:`, error);
        res.status(500).json({ error: error.message });
    }
});

app.delete('/api/theses/:id/holdings/:ticker', async (req, res) => {
    const { id, ticker } = req.params;
    try {
        const updatedThesis = await thesisService.removeHolding(id, ticker);
        res.json(updatedThesis);
    } catch (error: any) {
        console.error(`[API] Error removing holding ${ticker} from ${id}:`, error);
        res.status(500).json({ error: error.message });
    }
});

app.put('/api/theses/:id/holdings', async (req, res) => {
    const { id } = req.params;
    const newHoldings = req.body;
    try {
        const updatedThesis = await thesisService.replaceHoldings(id, newHoldings);
        res.json(updatedThesis);
    } catch (error: any) {
        console.error(`[API] Error replacing holdings for ${id}:`, error);
        res.status(500).json({ error: error.message });
    }
});

app.delete('/api/theses/:id', async (req, res) => {
    const { id } = req.params;
    try {
        const result = await thesisService.deleteThesis(id);
        if (result) {
            res.json({ success: true, message: 'Thesis deleted' });
        } else {
            res.status(404).json({ error: 'Thesis not found' });
        }
    } catch (error: any) {
        console.error(`[API] Error deleting thesis:`, error);
        res.status(500).json({ error: 'Failed to delete thesis' });
    }
});

// ─── Docs API ─────────────────────────────────────────────────────────────────
const THESIS_DOC_PATH = path.resolve(__dirname, '../../../plugins/portfolio-advisor/references/investment_thesis.md');
const TARGET_PORTFOLIO_FILE = path.resolve(__dirname, '../data/theses/target-portfolio.json');

// Calls portfolio_action.py (canonical Python) and returns { ticker → action } map.
// This is the single source of truth — no TypeScript mirrors of action logic.
async function getPythonActions(): Promise<Record<string, string>> {
    const { spawn } = require('child_process');
    const scriptPath = path.resolve(__dirname, '../../../plugins/portfolio-advisor/scripts/portfolio_action.py');
    const portfolioPath = path.resolve(__dirname, '../data/portfolio.json');
    const targetPath = path.resolve(__dirname, '../data/theses/target-portfolio.json');
    const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';
    return new Promise((resolve) => {
        const proc = spawn(pythonCmd, [scriptPath, '--all', '--portfolio', portfolioPath, '--target', targetPath]);
        let out = '';
        let err = '';
        proc.stdout.on('data', (d: Buffer) => out += d.toString());
        proc.stderr.on('data', (d: Buffer) => err += d.toString());
        proc.on('close', (code: number) => {
            if (code !== 0) {
                console.error('[Actions] portfolio_action.py failed:', err);
                resolve({});
            } else {
                try { resolve(JSON.parse(out)); } catch { resolve({}); }
            }
        });
    });
}

// GET /api/screener/all-holdings — all thesis holdings enriched with actual %, review action, and rationale.
// Used by the screener to show ETFs and other non-projection holdings alongside DCF rows.
app.get('/api/screener/all-holdings', async (_req, res) => {
    try {
        // 1. Target portfolio (thesis targets + names + subStrategyId + thesisForInclusion)
        const targetPortfolio = JSON.parse(await fs.promises.readFile(TARGET_PORTFOLIO_FILE, 'utf-8'));
        const thesisHoldings: any[] = targetPortfolio.holdings ?? [];

        // 2. Live portfolio weights (symbol → { pct, price })
        const positions: any[] = fs.existsSync(PORTFOLIO_FILE)
            ? JSON.parse(fs.readFileSync(PORTFOLIO_FILE, 'utf-8')) : [];
        const totalValue = positions.reduce((s, p) => s + (p.shares || 0) * (p.price || 0), 0);
        const actualMap: Record<string, { pct: number; price: number }> = {};
        for (const p of positions) {
            const ticker = (p.symbol ?? p.ticker) as string;
            if (ticker && totalValue > 0)
                actualMap[ticker] = { pct: ((p.shares || 0) * (p.price || 0) / totalValue) * 100, price: p.price || 0 };
        }
        // 3. Canonical actions from Python — single source of truth
        const actionsMap = await getPythonActions();

        // 4. Rationale from latest review (never overrides weights or actions)
        let reviewMap: Record<string, any> = {};
        try {
            await fs.promises.mkdir(PORTFOLIO_REVIEWS_DIR, { recursive: true });
            const files = (await fs.promises.readdir(PORTFOLIO_REVIEWS_DIR))
                .filter(f => f.endsWith('.json') && f.match(/^\d{4}-\d{2}-\d{2}/) && !f.includes('patch'))
                .sort().reverse();
            if (files.length) {
                const raw = JSON.parse(await fs.promises.readFile(path.join(PORTFOLIO_REVIEWS_DIR, files[0]), 'utf-8'));
                for (const h of [...(raw.holdings ?? []), ...(raw.holdingsUnchanged ?? [])]) {
                    reviewMap[h.ticker] = h;
                }
            }
        } catch { /* no review file — proceed without */ }

        // 5. Merge: weights from JSON files, action from Python, rationale from review
        const result = thesisHoldings.map((h: any) => {
            const rev = reviewMap[h.ticker];
            const live = actualMap[h.ticker];
            return {
                ticker: h.ticker,
                name: h.name ?? h.ticker,
                pillarId: h.pillarId ?? 'other',
                subStrategyId: h.subStrategyId ?? null,
                role: h.role ?? null,
                targetPct: h.targetWeight ?? null,
                actualPct: live?.pct ?? null,
                currentPrice: live?.price ?? null,
                action: actionsMap[h.ticker] ?? 'WATCHLIST',
                rationale: rev?.rationale ?? h.thesisForInclusion ?? null,
                hasValuation: false,
            };
        });

        // Append any positions in portfolio.json with no thesis row (e.g. USD_CASH)
        const thesisTickers = new Set(thesisHoldings.map((h: any) => h.ticker));
        for (const [ticker, data] of Object.entries(actualMap) as [string, { pct: number; price: number }][]) {
            if (!thesisTickers.has(ticker)) {
                const isCash = ticker === 'USD_CASH' || (ticker as string).includes('CASH');
                result.push({
                    ticker,
                    name: ticker === 'USD_CASH' ? 'US Dollar Cash' : ticker,
                    pillarId: isCash ? 'cash' : 'other',
                    subStrategyId: isCash ? 'cash' : 'other',
                    role: 'untracked',
                    targetPct: null,
                    actualPct: data.pct,
                    currentPrice: data.price,
                    action: actionsMap[ticker] ?? 'EXIT',
                    rationale: 'Cash position — not mapped to a thesis holding',
                    hasValuation: false,
                } as any);
            }
        }

        res.json(result);
    } catch (err: any) {
        res.status(500).json({ error: err.message });
    }
});



// GET /api/docs/investment-thesis — serves the investment thesis markdown + live metadata from target_portfolio.json
app.get('/api/docs/investment-thesis', async (_req, res) => {
    try {
        const content = await fs.promises.readFile(THESIS_DOC_PATH, 'utf-8');
        // Pull live name/description from the active thesis JSON so the UI never hardcodes the strategy name
        let thesisName = 'Investment Thesis';
        let thesisDescription = '';
        try {
            const thesisData = await thesisService.getThesis('target-portfolio');
            if (thesisData) {
                thesisName = thesisData.name;
                thesisDescription = thesisData.description ?? '';
            }
        } catch { /* thesis JSON unavailable — fall back to generic label */ }
        res.json({ content, filename: 'investment_thesis.md', thesisName, thesisDescription });
    } catch (err: any) {
        res.status(404).json({ error: 'Investment thesis document not found' });
    }
});

const PORTFOLIO_REVIEWS_DIR = path.resolve(__dirname, '../../../PortfolioAnalysis/strategic-reviews');
app.get('/api/docs/latest-review', async (_req, res) => {
    try {
        await fs.promises.mkdir(PORTFOLIO_REVIEWS_DIR, { recursive: true });
        const files = (await fs.promises.readdir(PORTFOLIO_REVIEWS_DIR))
            .filter(f => f.endsWith('.md') && f.match(/^\d{4}-\d{2}-\d{2}/))
            .sort().reverse();
        if (!files.length) { res.status(404).json({ error: 'No reviews found' }); return; }
        const latest = files[0];
        const content = await fs.promises.readFile(path.join(PORTFOLIO_REVIEWS_DIR, latest), 'utf-8');
        res.json({ content, filename: latest, date: latest.substring(0, 10) });
    } catch (err: any) {
        res.status(500).json({ error: 'Failed to load review' });
    }
});

// GET /api/docs/latest-review-data — generates live review from current portfolio + thesis
// Runs generate_review_json.py --dry-run so data always reflects the latest portfolio sync.
app.get('/api/docs/latest-review-data', async (_req, res) => {
    const { spawn } = require('child_process');
    const scriptPath = path.resolve(__dirname, '../../../plugins/portfolio-advisor/scripts/generate_review_json.py');
    const pythonCmd  = process.platform === 'win32' ? 'python' : 'python3';
    try {
        const review = await new Promise<any>((resolve, reject) => {
            const proc = spawn(pythonCmd, [scriptPath, '--dry-run']);
            let out = '';
            let err = '';
            const timer = setTimeout(() => { proc.kill(); reject(new Error('Review generation timed out')); }, 20_000);
            proc.stdout.on('data', (d: Buffer) => { out += d.toString(); });
            proc.stderr.on('data', (d: Buffer) => { err += d.toString(); });
            proc.on('close', (code: number) => {
                clearTimeout(timer);
                if (code !== 0) return reject(new Error(`generate_review_json exited ${code}: ${err}`));
                try { resolve(JSON.parse(out)); } catch { reject(new Error('Failed to parse review JSON')); }
            });
            proc.on('error', (e: Error) => { clearTimeout(timer); reject(e); });
        });
        res.json(review);
    } catch (err: any) {
        console.error('[API] latest-review-data error:', err.message);
        res.status(500).json({ error: 'Failed to generate review data' });
    }
});

// GET /api/docs/agent-guide — serves the agent quick reference markdown
const AGENT_GUIDE_PATH = path.resolve(__dirname, '../../../plugins/toolkit-manager/references/agent-quick-reference.md');
app.get('/api/docs/agent-guide', async (_req, res) => {
    try {
        const content = await fs.promises.readFile(AGENT_GUIDE_PATH, 'utf-8');
        res.json({ content, filename: 'agent-quick-reference.md' });
    } catch (err: any) {
        res.status(404).json({ error: 'Agent guide not found' });
    }
});

app.listen(port, () => {
    console.log(`Backend server running on http://localhost:${port}`);
});
