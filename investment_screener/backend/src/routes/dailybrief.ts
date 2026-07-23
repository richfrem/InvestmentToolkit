/**
 * dailybrief.ts - Express routing for daily-brief snapshot metrics.
 *
 * Purpose:
 *   Serves today's conviction scores, macro regime, pillar health, and earnings
 *   flags from the intelligence_event ledger (event_type REVIEW_DAILY).
 *
 * Layer:
 *   Backend / Routes / Daily Brief
 *
 * Routes Index:
 *   - GET /latest - Returns today's brief or the most recent available
 *   - GET /history - Returns metadata for all available snapshots
 *   - GET /conviction/:ticker - Historical conviction score for one ticker
 *
 * Key Input Dependencies:
 *   - investment_screener/backend/data/intelligence.sqlite (intelligence_event ledger)
 *
 * Key Output Dependencies:
 *   None
 */
import { Router } from 'express';
import { spawnPythonScript } from '../services/bridge';

const router = Router();

export async function queryLatestBriefFromLedger(dbPath?: string): Promise<any> {
    try {
        const args = ['--latest'];
        if (dbPath) {
            args.push('--db-path', dbPath);
        }
        const data = await spawnPythonScript('query_ledger_brief.py', args);
        return data || null;
    } catch (e) {
        console.warn('Ledger query latest brief failed:', e);
        return null;
    }
}

export async function queryBriefHistoryFromLedger(dbPath?: string): Promise<any[] | null> {
    try {
        const args = ['--history'];
        if (dbPath) {
            args.push('--db-path', dbPath);
        }
        const data = await spawnPythonScript('query_ledger_brief.py', args);
        return Array.isArray(data) ? data : null;
    } catch (e) {
        console.warn('Ledger query history failed:', e);
        return null;
    }
}

export async function queryTickerConvictionFromLedger(ticker: string, dbPath?: string): Promise<any[] | null> {
    try {
        const args = ['--conviction', ticker];
        if (dbPath) {
            args.push('--db-path', dbPath);
        }
        const data = await spawnPythonScript('query_ledger_brief.py', args);
        return Array.isArray(data) ? data : null;
    } catch (e) {
        console.warn('Ledger query ticker conviction failed:', e);
        return null;
    }
}

/** GET /api/daily-brief/latest — returns today's brief or the most recent available. */
router.get('/latest', async (_req, res) => {
    try {
        const brief = await queryLatestBriefFromLedger();
        if (!brief) {
            res.status(404).json({ error: 'No daily brief found. Run: python3 plugins/portfolio-advisor/scripts/daily_brief.py' });
            return;
        }
        res.json(brief);
    } catch (e: any) {
        res.status(500).json({ error: e.message });
    }
});

/** GET /api/daily-brief/history — returns metadata for all available snapshots. */
router.get('/history', async (_req, res) => {
    try {
        const history = await queryBriefHistoryFromLedger();
        res.json(history ?? []);
    } catch (e: any) {
        res.status(500).json({ error: e.message });
    }
});

/** GET /api/daily-brief/conviction/:ticker — historical conviction score for one ticker. */
router.get('/conviction/:ticker', async (req, res) => {
    try {
        const ticker = req.params.ticker.toUpperCase();
        const convictionHistory = await queryTickerConvictionFromLedger(ticker);
        res.json(convictionHistory ?? []);
    } catch (e: any) {
        res.status(500).json({ error: e.message });
    }
});

export default router;


