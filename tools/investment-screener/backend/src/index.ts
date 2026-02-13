import express from 'express';
import cors from 'cors';
import fs from 'fs';
import path from 'path';
import { spawnPythonScript } from './services/bridge';
import { questradeSyncService } from './services/QuestradeSyncService';

const app = express();
const port = process.env.PORT || 3001;

app.use(cors());
app.use(express.json());

const PORTFOLIO_FILE = path.join(__dirname, '../../frontend/src/data/portfolio.json');
const PORTFOLIO_EXAMPLE = PORTFOLIO_FILE + '.example';

// On startup, seed portfolio.json from .example if it doesn't exist (clean clone)
if (!fs.existsSync(PORTFOLIO_FILE) && fs.existsSync(PORTFOLIO_EXAMPLE)) {
    fs.copyFileSync(PORTFOLIO_EXAMPLE, PORTFOLIO_FILE);
    console.log('[Init] Created portfolio.json from .example');
}

// Validates ticker symbols: 1-10 uppercase alphanumeric chars, dots, hyphens (e.g. BRK-B, BTC-USD)
const isValidTicker = (ticker: string): boolean => /^[A-Z0-9.\-]{1,10}$/.test(ticker);

app.get('/health', (_req, res) => {
    res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

app.get('/api/stock/:ticker', async (req, res) => {
    const { ticker } = req.params;
    if (!isValidTicker(ticker)) {
        res.status(400).json({ error: 'Invalid ticker symbol' });
        return;
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
        console.error(`[API] Error fetching ${ticker}:`, error);
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
            res.status(400).json({ error: `Invalid ticker symbols: ${invalidTickers.map((i: any) => i.symbol).join(', ')}` });
            return;
        }
        const data = await spawnPythonScript('fetch_portfolio_heatmap.py', [JSON.stringify(items)]);
        if (data.error) {
            res.status(400).json({ error: data.error });
            return;
        }
        res.json(data);
    } catch (error) {
        console.error(`[API] Error fetching heatmap:`, error);
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
        console.error(`[API] Error reading portfolio:`, error);
        res.status(500).json({ error: 'Failed to read portfolio' });
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
        console.error(`[API] Error saving portfolio:`, error);
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
        console.error(`[API] Error refreshing prices:`, error);
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
        console.error(`[API] Questrade Sync Error:`, error);
        res.status(500).json({
            error: 'Questrade sync failed',
            details: error.message
        });
    }
});

app.listen(port, () => {
    console.log(`Backend server running on http://localhost:${port}`);
});
