/**
 * index.ts (Express Server Entry Point)
 * =====================================
 *
 * Purpose:
 *     Application bootstrap: middleware setup, route registration, server startup.
 *     Business logic lives in src/routes/ and src/services/.
 *
 * Layer: Backend / Core
 *
 * Usage:
 *     node dist/index.js        (Production)
 *     npm run dev               (Development via ts-node-dev)
 */
import express from 'express';
import dotenv from 'dotenv';
import path from 'path';
import fs from 'fs';

dotenv.config({ path: path.resolve(__dirname, '../../../.env') });

import cors from 'cors';
import { valuationService } from './services/ValuationService';
import { PORTFOLIO_FILE, PORTFOLIO_EXAMPLE } from './utils/paths';
import { isTradingViewConnected } from './utils/helpers';

import portfolioRouter from './routes/portfolio';
import projectionsRouter from './routes/projections';
import thesesRouter from './routes/theses';
import docsRouter from './routes/docs';
import screenerRouter from './routes/screener';
import stockRouter from './routes/stock';

const app = express();
const port = process.env.PORT || 3001;

// Bind to loopback only — prevents other machines on the network from reaching the API.
// All clients (Vite dev proxy, CLI agents) connect via localhost, so this is safe.
const HOST = '127.0.0.1';

app.use(cors());
app.use(express.json({ limit: '1mb' }));

// On startup, seed portfolio.json from .example if it doesn't exist (clean clone)
if (!fs.existsSync(PORTFOLIO_FILE) && fs.existsSync(PORTFOLIO_EXAMPLE)) {
    fs.copyFileSync(PORTFOLIO_EXAMPLE, PORTFOLIO_FILE);
    console.log('[Init] Created portfolio.json from .example');
}

// ── Utility routes ─────────────────────────────────────────────────────────────

app.get('/health', (_req, res) => {
    res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

app.get('/api/tv-status', async (_req, res) => {
    const connected = await isTradingViewConnected();
    res.json({ price_source: connected ? 'tradingview' : 'yfinance' });
});

// ── AI Valuation (standalone — not grouped with screener routes) ───────────────

app.post('/api/analysis/valuation', async (req, res) => {
    const { ticker, userMessage } = req.body;
    console.log(`[API] AI Valuation Request for ${ticker}...`);
    try {
        if (!ticker) { res.status(400).json({ error: 'Ticker is required' }); return; }
        const result = await valuationService.analyzeStock(ticker, userMessage);
        res.json(result);
    } catch (error: any) {
        console.error(`[API] Valuation Error: `, error);
        res.status(500).json({ error: 'AI Analysis Failed', details: error.message });
    }
});

// ── Questrade seed ────────────────────────────────────────────────────────────

app.post('/api/questrade/seed', async (req, res) => {
    const { refreshToken } = req.body;
    if (!refreshToken) { res.status(400).json({ error: 'refreshToken is required' }); return; }
    console.log(`[API] Seeding Questrade refresh token...`);
    try {
        const exchangeUrl = `https://login.questrade.com/oauth2/token?grant_type=refresh_token&refresh_token=${encodeURIComponent(refreshToken)}`;
        const exchangeRes = await fetch(exchangeUrl, {
            method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: '',
        });
        if (!exchangeRes.ok) {
            const errText = await exchangeRes.text();
            console.error(`[API][Seed] Token exchange failed: ${errText}`);
            res.status(400).json({ error: 'Token exchange failed. Ensure you are using a fresh one-week token from the Questrade portal.', details: errText });
            return;
        }
        const exchangeData: any = await exchangeRes.json();
        const seedToken: string = exchangeData.refresh_token;
        if (!seedToken) { res.status(400).json({ error: 'Token exchange did not return a refresh_token.' }); return; }
        console.log(`[API][Seed] Token exchanged successfully.`);

        const { spawn } = require('child_process');
        const enginePath = path.resolve(__dirname, '../src/QuestradeDataEngine.py');
        const args = ['--cache-dir', path.resolve(__dirname, '../'), '--seed', seedToken];
        const pythonProcess = spawn('python3', [enginePath, ...args]);
        let output = '';
        let errorOutput = '';
        pythonProcess.stdout.on('data', (data: any) => { output += data.toString(); console.log(`[API][Seed][Python] ${data.toString().trim()}`); });
        pythonProcess.stderr.on('data', (data: any) => { errorOutput += data.toString(); console.error(`[API][Seed][Error] ${data.toString().trim()}`); });
        pythonProcess.on('close', (code: number) => {
            if (code === 0) { res.json({ success: true, message: 'Refresh token seeded successfully.' }); }
            else { res.status(500).json({ error: `Seeding failed with code ${code}`, details: errorOutput || 'Unknown error' }); }
        });
    } catch (error: any) {
        console.error(`[API] Seeding Error: `, error);
        res.status(500).json({ error: error.message });
    }
});

// ── Route registration ────────────────────────────────────────────────────────

app.use('/api/portfolio', portfolioRouter);   // /api/portfolio/** (CRUD, sync, summary, strategy-allocation)
app.use('/api/projections', projectionsRouter);
app.use('/api/theses', thesesRouter);
app.use('/api', docsRouter);                 // /api/docs/**, /api/research/**
app.use('/api', stockRouter);               // /api/stock/:ticker, /api/portfolio-heatmap
app.use('/api/screener', screenerRouter);   // /api/screener/all-holdings

app.listen(Number(port), HOST, () => {
    console.log(`Backend server running on http://${HOST}:${port}`);
});
