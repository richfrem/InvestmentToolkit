import express from 'express';
import fs from 'fs';
import path from 'path';
import { spawn } from 'child_process';
import { thesisService } from '../services/ThesisService';
import { RESEARCH_DIR, PORTFOLIO_REVIEWS_DIR, THESIS_DOC_PATH, AGENT_GUIDE_PATH } from '../utils/paths';

const router = express.Router();

// ── Research reports ──────────────────────────────────────────────────────────

router.get('/research/:filename', async (req, res) => {
    try {
        const { filename } = req.params;
        if (!/^[A-Z0-9.-]{1,10}_\d{4}-\d{2}-\d{2}\.md$/.test(filename)) {
            res.status(400).json({ error: 'Invalid filename format. Expected: TICKER_YYYY-MM-DD.md' });
            return;
        }
        const filepath = path.join(RESEARCH_DIR, filename);
        if (!path.resolve(filepath).startsWith(path.resolve(RESEARCH_DIR))) {
            res.status(403).json({ error: 'Access denied' });
            return;
        }
        const content = await fs.promises.readFile(filepath, 'utf-8');
        res.json({ filename, content, ticker: filename.split('_')[0], date: filename.split('_')[1].replace('.md', '') });
    } catch (err: any) {
        if (err.code === 'ENOENT') { res.status(404).json({ error: 'Research report not found' }); return; }
        console.error(`[API] Error reading research report:`, err);
        res.status(500).json({ error: 'Failed to read research report' });
    }
});

router.get('/research', async (_req, res) => {
    try {
        await fs.promises.mkdir(RESEARCH_DIR, { recursive: true });
        const files = await fs.promises.readdir(RESEARCH_DIR);
        const reports = files
            .filter(f => f.endsWith('.md'))
            .map(f => ({ filename: f, ticker: f.split('_')[0], date: f.split('_')[1].replace('.md', '') }))
            .sort((a, b) => b.date.localeCompare(a.date));
        res.json({ reports });
    } catch (err: any) {
        console.error(`[API] Error listing research reports:`, err);
        res.json({ reports: [] });
    }
});

// ── Docs ──────────────────────────────────────────────────────────────────────

router.get('/docs/investment-thesis', async (_req, res) => {
    try {
        const content = await fs.promises.readFile(THESIS_DOC_PATH, 'utf-8');
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
    const scriptPath = path.resolve(__dirname, '../../../../../plugins/portfolio-advisor/scripts/generate_review_json.py');
    const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';
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

router.get('/docs/agent-guide', async (_req, res) => {
    try {
        const content = await fs.promises.readFile(AGENT_GUIDE_PATH, 'utf-8');
        res.json({ content, filename: 'agent-quick-reference.md' });
    } catch { res.status(404).json({ error: 'Agent guide not found' }); }
});

export default router;
