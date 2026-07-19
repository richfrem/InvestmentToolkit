/**
 * docs.ts - Express routing for qualitative reports and markdown documentation.
 * 
 * Purpose:
 *   Handles Express API routes for reading investment thesis, portfolio reviews,
 *   agent guides, and qualitative research reports.
 * 
 * Layer:
 *   Backend / Routes / Docs
 * 
 * Routes Index:
 *   - GET /research/:filename - Fetches a specific research report
 *   - GET /research - Lists all available research files
 *   - GET /docs/investment-thesis - Reads the main markdown thesis documentation
 *   - GET /docs/latest-review - Loads the latest markdown portfolio review
 *   - GET /docs/latest-review-data - Generates structured JSON portfolio review statistics
 *   - GET /docs/agent-guide - Serves the agent reference documentation
 * 
 * Key Input Dependencies:
 *   - investment_screener/backend/data/research/ (folder containing research MD files)
 *   - investment_screener/backend/data/portfolio-reviews/ (folder containing review MD files)
 *   - investment_screener/backend/data/theses/target-portfolio.json
 *   - investment_screener/backend/src/utils/paths (RESEARCH_DIR, etc.)
 * 
 * Key Output Dependencies:
 *   None
 */

import express from 'express';
import fs from 'fs';
import path from 'path';
import { thesisService } from '../services/ThesisService';
import { RESEARCH_DIR, PORTFOLIO_REVIEWS_DIR, THESIS_DOC_PATH, AGENT_GUIDE_PATH } from '../utils/paths';
import { spawnPythonScript } from '../services/bridge';

const router = express.Router();

// ── Research reports ──────────────────────────────────────────────────────────

export const DATED_FILENAME_RE = /^[A-Z0-9.-]{1,10}_\d{4}-\d{2}-\d{2}\.md$/;
export const CANONICAL_FILENAME_RE = /^[A-Z0-9.-]{1,10}\.(summary|timeline)\.md$/;

export function parseResearchFilename(filename: string): { ticker: string; date: string | null } {
    const datedMatch = filename.match(/^([A-Z0-9.-]{1,10})_(\d{4}-\d{2}-\d{2})\.md$/);
    if (datedMatch) return { ticker: datedMatch[1], date: datedMatch[2] };
    const canonicalMatch = filename.match(/^([A-Z0-9.-]{1,10})\.(summary|timeline)\.md$/);
    if (canonicalMatch) return { ticker: canonicalMatch[1], date: null };
    return { ticker: filename, date: null };
}

router.get('/research/:filename', async (req, res) => {
    try {
        const { filename } = req.params;
        if (!DATED_FILENAME_RE.test(filename) && !CANONICAL_FILENAME_RE.test(filename)) {
            res.status(400).json({ error: 'Invalid filename format. Expected: TICKER_YYYY-MM-DD.md' });
            return;
        }

        // Try ledger database query first if it is a dated file
        if (DATED_FILENAME_RE.test(filename)) {
            const report = await queryLatestResearchFromLedger(filename);
            if (report) {
                res.json(report);
                return;
            }
        }

        // Fallback to legacy filesystem read
        const filepath = path.join(RESEARCH_DIR, filename);
        if (!path.resolve(filepath).startsWith(path.resolve(RESEARCH_DIR))) {
            res.status(403).json({ error: 'Access denied' });
            return;
        }
        const content = await fs.promises.readFile(filepath, 'utf-8');
        const { ticker, date } = parseResearchFilename(filename);
        res.json({ filename, content, ticker, date });
    } catch (err: any) {
        if (err.code === 'ENOENT') { res.status(404).json({ error: 'Research report not found' }); return; }
        console.error(`[API] Error reading research report:`, err);
        res.status(500).json({ error: 'Failed to read research report' });
    }
});

router.get('/research', async (_req, res) => {
    try {
        // 1. Get ledger research reports
        const ledgerReports = await queryResearchListFromLedger() || [];

        // 2. Get local filesystem files
        await fs.promises.mkdir(RESEARCH_DIR, { recursive: true });
        const files = await fs.promises.readdir(RESEARCH_DIR);
        const diskReports = files
            .filter(f => f.endsWith('.md'))
            .map(f => ({ filename: f, ...parseResearchFilename(f) }));

        // 3. Combine and deduplicate by filename
        const combinedMap = new Map<string, any>();
        for (const r of diskReports) {
            combinedMap.set(r.filename, r);
        }
        for (const r of ledgerReports) {
            combinedMap.set(r.filename, r);
        }

        const reports = Array.from(combinedMap.values())
            .sort((a, b) => (b.date ?? '').localeCompare(a.date ?? ''));

        res.json({ reports });
    } catch (err: any) {
        console.error(`[API] Error listing research reports:`, err);
        res.json({ reports: [] });
    }
});

// ── Docs ──────────────────────────────────────────────────────────────────────

router.get('/docs/investment-thesis', async (_req, res) => {
    try {
        const content = await fs.promises.readFile( THESIS_DOC_PATH, 'utf-8');
        let thesisName = 'Investment Thesis';
        let thesisDescription = '';
        try {
            const thesisData = await thesisService.getThesis('target-portfolio');
            if (thesisData) { thesisName = thesisData.name; thesisDescription = thesisData.description ?? ''; }
        } catch { /* fall back to generic label */ }
        res.json({ content, filename: 'investment_thesis.md', thesisName, thesisDescription });
    } catch { res.status(404).json({ error: 'Investment thesis document not found' }); }
});

router.get('/docs/latest-review', async (_req, res) => {
    try {
        await fs.promises.mkdir(PORTFOLIO_REVIEWS_DIR, { recursive: true });
        const files = (await fs.promises.readdir(PORTFOLIO_REVIEWS_DIR))
            .filter(f => f.endsWith('.md') && f.match(/^\d{4}-\d{2}-\d{2}/))
            .sort().reverse();
        if (!files.length) { res.status(404).json({ error: 'No reviews found' }); return; }
        const latest = files[0];
        const content = await fs.promises.readFile(path.join(PORTFOLIO_REVIEWS_DIR, latest), 'utf-8');
        res.json({ content, filename: latest, date: latest.substring(0, 10) });
    } catch { res.status(500).json({ error: 'Failed to load review' }); }
});

router.get('/docs/latest-review-data', async (_req, res) => {
    try {
        const review = await spawnPythonScript('generate_review_json.py', ['--dry-run']);
        res.json(review);
    } catch (err: any) {
        console.error('[API] latest-review-data error:', err.message);
        res.status(500).json({ error: 'Failed to generate review data' });
    }
});

router.get('/docs/agent-guide', async (_req, res) => {
    try {
        const content = await fs.promises.readFile(AGENT_GUIDE_PATH, 'utf-8');
        res.json({ content, filename: 'agent-quick-reference.md' });
    } catch { res.status(404).json({ error: 'Agent guide not found' }); }
});

export async function queryLatestResearchFromLedger(filename: string, dbPath?: string): Promise<any> {
    try {
        const args = ['--get', filename];
        if (dbPath) {
            args.push('--db-path', dbPath);
        }
        const data = await spawnPythonScript('query_ledger_research.py', args);
        return data || null;
    } catch (e) {
        console.warn('Ledger query latest research failed, falling back:', e);
        return null;
    }
}

export async function queryResearchListFromLedger(dbPath?: string): Promise<any[] | null> {
    try {
        const args = ['--list'];
        if (dbPath) {
            args.push('--db-path', dbPath);
        }
        const data = await spawnPythonScript('query_ledger_research.py', args);
        return Array.isArray(data) ? data : null;
    } catch (e) {
        console.warn('Ledger query research list failed, falling back:', e);
        return null;
    }
}

export default router;

