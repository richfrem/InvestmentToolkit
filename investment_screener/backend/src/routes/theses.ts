import express from 'express';
import fs from 'fs';
import path from 'path';
import { thesisService } from '../services/ThesisService';
import { THESIS_FILE } from '../utils/paths';

const router = express.Router();
const SUB_STRATEGIES_DIR = path.resolve(__dirname, '../../data/theses/sub_strategies');

interface SubStrategySummary {
    id: string;
    title: string;
    status: string;
    date: string;
    targetWeight: string;
}

// Helper to parse basic metadata from the markdown file
function parseMetadata(content: string, filename: string): SubStrategySummary {
    const titleMatch = content.match(/^# Investment Thesis Proposal:\s*(.+)$/m) || content.match(/^#\s*(.+)$/m);
    const statusMatch = content.match(/\*\*Status\*\*:\s*(.+)$/m);
    const dateMatch = content.match(/\*\*Date\*\*:\s*(.+)$/m);
    const weightMatch = content.match(/\*\*Target Weight\*\*:\s*(.+)$/m);

    return {
        id: filename.replace('.md', ''),
        title: titleMatch ? titleMatch[1].trim() : filename,
        status: statusMatch ? statusMatch[1].trim() : 'UNKNOWN',
        date: dateMatch ? dateMatch[1].trim() : '',
        targetWeight: weightMatch ? weightMatch[1].trim() : 'N/A'
    };
}

// GET /api/theses/sub-strategies
router.get('/sub-strategies', (req, res) => {
    try {
        if (!fs.existsSync(SUB_STRATEGIES_DIR)) {
            return res.json([]);
        }

        const files = fs.readdirSync(SUB_STRATEGIES_DIR).filter(f => f.endsWith('.md'));
        const strategies: SubStrategySummary[] = files.map(file => {
            const content = fs.readFileSync(path.join(SUB_STRATEGIES_DIR, file), 'utf-8');
            return parseMetadata(content, file);
        });

        // Sort by id for consistency
        strategies.sort((a, b) => a.id.localeCompare(b.id));

        res.json(strategies);
    } catch (error) {
        console.error('Error reading sub-strategies:', error);
        res.status(500).json({ error: 'Failed to read sub-strategies' });
    }
});

// GET /api/theses/sub-strategies/:id
router.get('/sub-strategies/:id', (req, res) => {
    try {
        const id = req.params.id;
        const filePath = path.join(SUB_STRATEGIES_DIR, `${id}.md`);
        
        if (!fs.existsSync(filePath)) {
            return res.status(404).json({ error: 'Sub-strategy not found' });
        }

        const content = fs.readFileSync(filePath, 'utf-8');
        res.json({ id, content });
    } catch (error) {
        console.error('Error reading sub-strategy detail:', error);
        res.status(500).json({ error: 'Failed to read sub-strategy' });
    }
});

router.get('/', async (_req, res) => {
    const theses = await thesisService.listTheses();
    res.json(theses);
});

router.get('/pillars', async (_req, res) => {
    try {
        if (!fs.existsSync(THESIS_FILE)) { res.json([]); return; }
        const thesis = JSON.parse(fs.readFileSync(THESIS_FILE, 'utf-8'));
        res.json(thesis.pillars ?? []);
    } catch (err: any) { res.status(500).json({ error: err.message }); }
});

router.get('/:id', async (req, res) => {
    const thesis = await thesisService.getThesis(req.params.id);
    if (thesis) res.json(thesis);
    else res.status(404).json({ error: 'Thesis not found' });
});

router.get('/:id/health', async (req, res) => {
    try {
        const health = await thesisService.computeHealthCheck(req.params.id);
        res.json(health);
    } catch (error: any) {
        console.error(`[API] Error computing health check for ${req.params.id}:`, error);
        res.status(500).json({ error: error.message || 'Failed to compute health check' });
    }
});

router.post('/:id/strategic-review', async (req, res) => {
    try {
        const result = await thesisService.performStrategicReview(req.params.id);
        res.json(result);
    } catch (error: any) {
        console.error(`[API] Error performing strategic review for ${req.params.id}:`, error);
        res.status(500).json({ error: error.message });
    }
});

router.post('/:id/optimize', async (req, res) => {
    try {
        const result = await thesisService.optimizePortfolio(req.params.id);
        res.json(result);
    } catch (error: any) {
        console.error(`[API] Error optimizing thesis ${req.params.id}:`, error);
        res.status(500).json({ error: error.message || 'Failed to optimize portfolio' });
    }
});

router.post('/', async (req, res) => {
    try {
        const thesis = req.body;
        await thesisService.saveThesis(thesis);
        res.json({ success: true, message: 'Thesis saved successfully', id: thesis.id });
    } catch (error: any) {
        console.error(`[API] Error saving thesis:`, error);
        if (error.message.includes('Validation Failed')) res.status(400).json({ error: error.message });
        else if (error.message.includes('Conflict')) res.status(409).json({ error: error.message });
        else res.status(500).json({ error: 'Failed to save thesis' });
    }
});

router.patch('/:id/holdings/:ticker', async (req, res) => {
    try {
        const updatedThesis = await thesisService.updateHolding(req.params.id, req.params.ticker, req.body);
        res.json(updatedThesis);
    } catch (error: any) {
        console.error(`[API] Error updating holding ${req.params.ticker}:`, error);
        res.status(500).json({ error: error.message });
    }
});

router.post('/:id/holdings', async (req, res) => {
    try {
        const updatedThesis = await thesisService.addHolding(req.params.id, req.body);
        res.json(updatedThesis);
    } catch (error: any) {
        console.error(`[API] Error adding holding to ${req.params.id}:`, error);
        res.status(500).json({ error: error.message });
    }
});

router.delete('/:id/holdings/:ticker', async (req, res) => {
    try {
        const updatedThesis = await thesisService.removeHolding(req.params.id, req.params.ticker);
        res.json(updatedThesis);
    } catch (error: any) {
        console.error(`[API] Error removing holding ${req.params.ticker} from ${req.params.id}:`, error);
        res.status(500).json({ error: error.message });
    }
});

router.put('/:id/holdings', async (req, res) => {
    try {
        const updatedThesis = await thesisService.replaceHoldings(req.params.id, req.body);
        res.json(updatedThesis);
    } catch (error: any) {
        console.error(`[API] Error replacing holdings for ${req.params.id}:`, error);
        res.status(500).json({ error: error.message });
    }
});

router.delete('/:id', async (req, res) => {
    try {
        const result = await thesisService.deleteThesis(req.params.id);
        if (result) res.json({ success: true, message: 'Thesis deleted' });
        else res.status(404).json({ error: 'Thesis not found' });
    } catch (error: any) {
        console.error(`[API] Error deleting thesis:`, error);
        res.status(500).json({ error: 'Failed to delete thesis' });
    }
});

export default router;
