/**
 * src/routes/dailybrief.ts
 * =======================
 *
 * Purpose:
 *   Serves today's conviction scores, macro regime, pillar health, and earnings
 *   flags from the daily-briefs/ snapshot directory.
 *
 * Key Functions:
 *   - todayStr() - Formats current date
 *   - latestBriefPath() - Resolves path to the most recent brief
 */
import { Router } from 'express';
import fs from 'fs';
import path from 'path';

const router = Router();

const BRIEFS_DIR = path.resolve(__dirname, '../../data/daily-briefs');

function todayStr(): string {
    return new Date().toISOString().slice(0, 10);
}

function latestBriefPath(): string | null {
    if (!fs.existsSync(BRIEFS_DIR)) return null;
    const files = fs.readdirSync(BRIEFS_DIR)
        .filter(f => f.endsWith('.json'))
        .sort()
        .reverse();
    return files.length ? path.join(BRIEFS_DIR, files[0]) : null;
}

/** GET /api/daily-brief/latest — returns today's brief or the most recent available. */
router.get('/latest', (_req, res) => {
    try {
        const briefPath = latestBriefPath();
        if (!briefPath) {
            res.status(404).json({ error: 'No daily brief found. Run: python3 plugins/portfolio-advisor/scripts/daily_brief.py' });
            return;
        }
        const brief = JSON.parse(fs.readFileSync(briefPath, 'utf-8'));
        res.json(brief);
    } catch (e: any) {
        res.status(500).json({ error: e.message });
    }
});

/** GET /api/daily-brief/history — returns metadata for all available snapshots. */
router.get('/history', (_req, res) => {
    try {
        if (!fs.existsSync(BRIEFS_DIR)) { res.json([]); return; }
        const files = fs.readdirSync(BRIEFS_DIR)
            .filter(f => f.endsWith('.json'))
            .sort()
            .reverse();
        const history = files.map(f => {
            const d = JSON.parse(fs.readFileSync(path.join(BRIEFS_DIR, f), 'utf-8'));
            return {
                date: d.date,
                regime: d.macro_regime?.regime,
                reduce_count: (d.conviction_scores ?? []).filter((s: any) => s.band === 'REDUCE' || s.band === 'EXIT').length,
                accum_count:  (d.conviction_scores ?? []).filter((s: any) => s.band === 'ACCUMULATE').length,
                ta_refreshed: d.ta_refreshed,
            };
        });
        res.json(history);
    } catch (e: any) {
        res.status(500).json({ error: e.message });
    }
});

/** GET /api/daily-brief/conviction/:ticker — historical conviction score for one ticker. */
router.get('/conviction/:ticker', (req, res) => {
    try {
        const ticker = req.params.ticker.toUpperCase();
        if (!fs.existsSync(BRIEFS_DIR)) { res.json([]); return; }
        const files = fs.readdirSync(BRIEFS_DIR)
            .filter(f => f.endsWith('.json'))
            .sort();
        const history = files.flatMap(f => {
            const d = JSON.parse(fs.readFileSync(path.join(BRIEFS_DIR, f), 'utf-8'));
            const score = (d.conviction_scores ?? []).find((s: any) => s.ticker === ticker);
            return score ? [{ date: d.date, ...score }] : [];
        });
        res.json(history);
    } catch (e: any) {
        res.status(500).json({ error: e.message });
    }
});

export default router;
