import express from 'express';
import cors from 'cors';
import { spawnPythonScript } from './services/bridge';

const app = express();
const port = process.env.PORT || 3001;

app.use(cors());
app.use(express.json());

app.get('/health', (req, res) => {
    res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

app.get('/api/stock/:ticker', async (req, res) => {
    const { ticker } = req.params;
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

app.listen(port, () => {
    console.log(`Backend server running on http://localhost:${port}`);
});
