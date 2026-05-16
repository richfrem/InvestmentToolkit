import express from 'express';
import { projectionService } from '../services/ProjectionService';
import { isValidTicker } from '../utils/helpers';

const router = express.Router();

router.get('/', async (_req, res) => {
    try {
        const projections = await projectionService.getAllProjections();
        res.json(projections);
    } catch (error) {
        console.error(`[API] Error getting all projections:`, error);
        res.status(500).json({ error: 'Failed to fetch projections' });
    }
});

router.get('/:ticker', async (req, res) => {
    const { ticker } = req.params;
    if (!isValidTicker(ticker)) { res.status(400).json({ error: 'Invalid ticker symbol' }); return; }
    try {
        const projections = await projectionService.getProjections(ticker);
        res.json(projections);
    } catch (error) {
        console.error(`[API] Error fetching projections for ${ticker}:`, error);
        res.status(500).json({ error: 'Failed to fetch projections' });
    }
});

router.post('/', async (req, res) => {
    try {
        await projectionService.saveProjection(req.body);
        res.json({ success: true, message: 'Projection saved successfully' });
    } catch (error: any) {
        console.error(`[API] Error saving projection:`, error);
        if (error.message.includes('Validation Failed')) res.status(400).json({ error: error.message });
        else if (error.message.includes('Conflict')) res.status(409).json({ error: error.message });
        else res.status(500).json({ error: 'Failed to save projection' });
    }
});

router.delete('/:ticker/:id', async (req, res) => {
    const { ticker, id } = req.params;
    if (!isValidTicker(ticker)) { res.status(400).json({ error: 'Invalid ticker symbol' }); return; }
    try {
        const result = await projectionService.deleteProjection(ticker, id);
        if (result) res.json({ success: true, message: 'Projection deleted' });
        else res.status(404).json({ error: 'Projection not found' });
    } catch (error: any) {
        console.error(`[API] Error deleting projection:`, error);
        res.status(500).json({ error: 'Failed to delete projection' });
    }
});

export default router;
