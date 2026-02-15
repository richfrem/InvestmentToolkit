import fs from 'fs';
import path from 'path';
import { lock } from 'proper-lockfile';
import {
    Thesis, ThesisSchema,
    HealthCheck, HealthCheckSchema,
    DriftEntry, HoldingHealth, Projection
} from '../utils/zod-schemas';
import { geminiService } from './GeminiService';

const THESES_DIR = path.resolve(__dirname, '../../data/theses');
const PROJECTIONS_DIR = path.resolve(__dirname, '../../data/projections');
const PORTFOLIO_FILE = path.resolve(__dirname, '../../../frontend/src/data/portfolio.json');
const REBALANCE_PROMPT_PATH = path.resolve(__dirname, '../../../.agent/skills/thesis-balancer/references/rebalance_prompt.md');

// Ensure directory exists
if (!fs.existsSync(THESES_DIR)) {
    fs.mkdirSync(THESES_DIR, { recursive: true });
}

export class ThesisService {

    private getFilePath(id: string): string {
        // Sanitize ID to prevent path traversal (UUIDs should be safe, but good practice)
        const safeId = id.replace(/[^a-z0-9\-]/g, '');
        return path.join(THESES_DIR, `${safeId}.json`);
    }

    private normalizeTicker(ticker: string): string {
        // Hand-coded substitutions for known Questrade vs Yahoo/Thesis mismatches
        const mapping: Record<string, string> = {
            'PSU.U': 'PSU-U.TO',
            'ETH.U': 'ETH-U.TO',
            // Add more as discovered
        };
        return mapping[ticker] || ticker;
    }

    private getProjectionPath(ticker: string): string {
        const safeTicker = ticker.replace(/[^A-Z0-9.\-]/g, '');
        return path.join(PROJECTIONS_DIR, `${safeTicker}.json`);
    }

    async getLatestAIProjection(ticker: string): Promise<Projection | null> {
        const filePath = this.getProjectionPath(ticker);
        if (!fs.existsSync(filePath)) return null;

        try {
            const content = fs.readFileSync(filePath, 'utf-8');
            const projections: Projection[] = JSON.parse(content);

            // Find latest AI execution
            const aiProjections = projections.filter(p => p.source === 'AI_AGENT');
            if (aiProjections.length === 0) return null;

            // Sort descending by version
            aiProjections.sort((a, b) => b.version - a.version);
            return aiProjections[0];
        } catch (e) {
            console.error(`[ThesisService] Error reading projection for ${ticker}:`, e);
            return null;
        }
    }

    async getPortfolioItems(): Promise<any[]> {
        if (!fs.existsSync(PORTFOLIO_FILE)) return [];
        try {
            const content = fs.readFileSync(PORTFOLIO_FILE, 'utf-8');
            return JSON.parse(content) || [];
        } catch (e) {
            console.error(`[ThesisService] Error reading portfolio file:`, e);
            return [];
        }
    }

    async computeHealthCheck(thesisId: string): Promise<HealthCheck> {
        const thesis = await this.getThesis(thesisId);
        if (!thesis) throw new Error('Thesis not found');

        const portfolioItems = await this.getPortfolioItems();

        // Calculate Total Portfolio Value (sum of market values)
        let totalPortfolioValue = 0;
        const positions = new Map<string, { marketValue: number, price: number }>();

        for (const item of portfolioItems) {
            const price = parseFloat(item.price) || 0;
            const quantity = parseFloat(item.quantity || item.shares) || 0;
            const marketValue = item.marketValue ? parseFloat(item.marketValue) : (price * quantity);

            if (!isNaN(marketValue)) {
                totalPortfolioValue += marketValue;
                const normalizedTicker = this.normalizeTicker(item.symbol);
                // If duplicates exist after normalization, sum them up (e.g. multiple lots)
                const existing = positions.get(normalizedTicker);
                if (existing) {
                    positions.set(normalizedTicker, {
                        marketValue: existing.marketValue + marketValue,
                        price: price // Use latest price
                    });
                } else {
                    positions.set(normalizedTicker, { marketValue, price });
                }
            }
        }

        // --- 1. Holding Level Drift ---
        const holdingHealth: HoldingHealth[] = [];
        const alerts: HealthCheck['alerts'] = [];

        // Batch read all projections in parallel
        const projectionPromises = thesis.holdings.map(h => this.getLatestAIProjection(h.ticker));
        const projections = await Promise.all(projectionPromises);
        const projectionMap = new Map<string, Projection | null>();
        thesis.holdings.forEach((h, i) => projectionMap.set(h.ticker, projections[i]));

        for (const holding of thesis.holdings) {
            const position = positions.get(holding.ticker);
            const actualValue = position ? position.marketValue : 0;
            const actualPct = totalPortfolioValue > 0 ? (actualValue / totalPortfolioValue) * 100 : 0;
            const driftPct = actualPct - holding.targetWeight;

            let status: 'ON_TARGET' | 'DRIFT' | 'CRITICAL' = 'ON_TARGET';
            if (Math.abs(driftPct) >= thesis.globalSettings.criticalDriftPct) status = 'CRITICAL';
            else if (Math.abs(driftPct) >= thesis.globalSettings.driftThresholdPct) status = 'DRIFT';

            // Cross-reference Tool A (from cache)
            const aiProj = projectionMap.get(holding.ticker);

            holdingHealth.push({
                id: holding.ticker, // using ticker as ID for holding entry
                name: holding.name,
                ticker: holding.ticker,
                pillarId: holding.pillarId,
                role: holding.role,
                targetPct: holding.targetWeight,
                actualPct: parseFloat(actualPct.toFixed(2)),
                driftPct: parseFloat(driftPct.toFixed(2)),
                status,
                currentPrice: position?.price,
                marketValue: actualValue,
                hasValuation: !!aiProj,
                latestAction: aiProj?.aiThesis?.action,
                latestFairValue: aiProj?.aiThesis?.fairValue
            });

            // Generate Alerts
            if (status === 'CRITICAL') {
                alerts.push({
                    severity: 'CRITICAL',
                    message: `${holding.ticker} is ${driftPct.toFixed(1)}% off target (Actual: ${actualPct.toFixed(1)}%, Target: ${holding.targetWeight}%)`,
                    ticker: holding.ticker,
                    pillarId: holding.pillarId,
                    action: driftPct < 0 ? 'BUY' : 'SELL'
                });
            } else if (status === 'DRIFT' && holding.role === 'core') {
                alerts.push({
                    severity: 'WARNING',
                    message: `${holding.ticker} is drifting ${driftPct.toFixed(1)}% (Threshold: ${thesis.globalSettings.driftThresholdPct}%)`,
                    ticker: holding.ticker,
                    pillarId: holding.pillarId,
                    action: driftPct < 0 ? 'BUY' : 'SELL'
                });
            }

            if (!aiProj && holding.role === 'core') {
                alerts.push({
                    severity: 'INFO',
                    message: `${holding.ticker} (Core) has no AI valuation. Recommend running Tool A.`,
                    ticker: holding.ticker,
                    action: 'NONE'
                });
            }
        }

        // --- 2. Pillar Level Drift ---
        const pillarHealth: DriftEntry[] = [];
        for (const pillar of thesis.pillars) {
            // Sum actual weight of all holdings in this pillar
            const pillarHoldings = holdingHealth.filter(h => h.pillarId === pillar.id);
            const actualPct = pillarHoldings.reduce((sum, h) => sum + h.actualPct, 0);
            const driftPct = actualPct - pillar.targetWeight;

            let status: 'ON_TARGET' | 'DRIFT' | 'CRITICAL' = 'ON_TARGET';
            if (Math.abs(driftPct) >= thesis.globalSettings.criticalDriftPct) status = 'CRITICAL';
            else if (Math.abs(driftPct) >= thesis.globalSettings.driftThresholdPct) status = 'DRIFT';

            pillarHealth.push({
                id: pillar.id,
                name: pillar.name,
                targetPct: pillar.targetWeight,
                actualPct: parseFloat(actualPct.toFixed(2)),
                driftPct: parseFloat(driftPct.toFixed(2)),
                status
            });

            if (status === 'CRITICAL') {
                alerts.push({
                    severity: 'CRITICAL',
                    message: `Pillar '${pillar.name}' is ${driftPct.toFixed(1)}% off target`,
                    pillarId: pillar.id,
                    action: driftPct < 0 ? 'BUY' : 'SELL'
                });
            }
        }

        // --- 3. Summary ---
        const totalDriftScore = pillarHealth.reduce((sum, p) => sum + Math.abs(p.driftPct), 0);

        // Find worst
        const worstPillar = [...pillarHealth].sort((a, b) => Math.abs(b.driftPct) - Math.abs(a.driftPct))[0];
        const worstHolding = [...holdingHealth].sort((a, b) => Math.abs(b.driftPct) - Math.abs(a.driftPct))[0];

        let overallStatus: 'ALIGNED' | 'DRIFTING' | 'CRITICAL' = 'ALIGNED';
        if (pillarHealth.some(p => p.status === 'CRITICAL')) overallStatus = 'CRITICAL';
        else if (pillarHealth.some(p => p.status === 'DRIFT')) overallStatus = 'DRIFTING';

        return {
            thesisId: thesis.id,
            thesisName: thesis.name,
            analyzedAt: new Date().toISOString(),
            portfolioValueUSD: totalPortfolioValue,
            pillarHealth,
            holdingHealth,
            alerts,
            summary: {
                totalDriftScore: parseFloat(totalDriftScore.toFixed(2)),
                worstPillar: worstPillar ? `${worstPillar.name} (${worstPillar.driftPct}%)` : undefined,
                worstHolding: worstHolding ? `${worstHolding.ticker} (${worstHolding.driftPct}%)` : undefined,
                overallStatus
            }
        };
    }

    async getThesis(id: string): Promise<Thesis | null> {
        const filePath = this.getFilePath(id);
        if (!fs.existsSync(filePath)) {
            return null;
        }
        try {
            const data = fs.readFileSync(filePath, 'utf-8');
            return JSON.parse(data);
        } catch (error) {
            console.error(`[ThesisService] Error reading thesis ${id}:`, error);
            return null;
        }
    }

    async listTheses(): Promise<{ id: string; name: string; updatedAt: string }[]> {
        try {
            const files = fs.readdirSync(THESES_DIR).filter(f => f.endsWith('.json'));
            const theses = [];

            for (const file of files) {
                try {
                    const content = fs.readFileSync(path.join(THESES_DIR, file), 'utf-8');
                    const thesis = JSON.parse(content);
                    theses.push({
                        id: thesis.id,
                        name: thesis.name,
                        updatedAt: thesis.updatedAt
                    });
                } catch (e) {
                    console.warn(`[ThesisService] Failed to parse ${file}, skipping.`);
                }
            }

            // Sort by most recently updated
            return theses.sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime());

        } catch (error) {
            console.error('[ThesisService] Error listing theses:', error);
            return [];
        }
    }

    async saveThesis(thesis: Thesis): Promise<void> {
        // 1. Zod Validation
        const parseResult = ThesisSchema.safeParse(thesis);
        if (!parseResult.success) {
            throw new Error(`Validation Failed: ${parseResult.error.message}`);
        }

        const filePath = this.getFilePath(thesis.id);

        // If file exists, check versioning
        if (fs.existsSync(filePath)) {
            let release: () => Promise<void>;
            try {
                release = await lock(filePath, { retries: { retries: 5, maxTimeout: 2000 } });
            } catch (e) {
                throw new Error('Could not acquire file lock for saving thesis.');
            }

            try {
                const existingContent = fs.readFileSync(filePath, 'utf-8');
                const existingThesis = JSON.parse(existingContent);

                if (existingThesis.version > thesis.version) {
                    throw new Error(
                        `Conflict: Server has version ${existingThesis.version}, incoming is ${thesis.version}`
                    );
                }

                // Server-side increment
                thesis.version = existingThesis.version + 1;
                thesis.updatedAt = new Date().toISOString();

                // Atomic write (MOVED INSIDE LOCK)
                const tempPath = `${filePath}.tmp`;
                fs.writeFileSync(tempPath, JSON.stringify(thesis, null, 2));
                fs.renameSync(tempPath, filePath);

            } finally {
                await release();
            }
        } else {
            // New thesis
            thesis.version = 1;
            // Ensure created/updated match if not set (though schema validates datetime)
            if (!thesis.createdAt) thesis.createdAt = new Date().toISOString();
            if (!thesis.updatedAt) thesis.updatedAt = new Date().toISOString();

            // Write new file
            const tempPath = `${filePath}.tmp`;
            fs.writeFileSync(tempPath, JSON.stringify(thesis, null, 2));
            fs.renameSync(tempPath, filePath);
        }
    }

    async updateHolding(thesisId: string, ticker: string, updates: Partial<Thesis['holdings'][0]>): Promise<Thesis> {
        let release: () => Promise<void>;
        const filePath = this.getFilePath(thesisId);

        try {
            release = await lock(filePath, { retries: { retries: 5, maxTimeout: 2000 } });
        } catch (e) {
            throw new Error('Could not acquire file lock.');
        }

        try {
            const content = fs.readFileSync(filePath, 'utf-8');
            const thesis: Thesis = JSON.parse(content);

            const index = thesis.holdings.findIndex(h => h.ticker === ticker);
            if (index === -1) throw new Error(`Holding ${ticker} not found`);

            // Apply updates
            const updatedHolding = { ...thesis.holdings[index], ...updates };
            thesis.holdings[index] = updatedHolding;

            // Validate Schema (Zod)
            const parseResult = ThesisSchema.safeParse(thesis);
            if (!parseResult.success) {
                throw new Error(`Validation Failed: ${parseResult.error.message}`);
            }

            // Save
            thesis.version++;
            thesis.updatedAt = new Date().toISOString();
            const tempPath = `${filePath}.tmp`;
            fs.writeFileSync(tempPath, JSON.stringify(thesis, null, 2));
            fs.renameSync(tempPath, filePath);

            return thesis;
        } finally {
            if (release!) await release();
        }
    }

    async addHolding(thesisId: string, holding: Thesis['holdings'][0]): Promise<Thesis> {
        let release: () => Promise<void>;
        const filePath = this.getFilePath(thesisId);

        try {
            release = await lock(filePath, { retries: { retries: 5, maxTimeout: 2000 } });
        } catch (e) {
            throw new Error('Could not acquire file lock.');
        }

        try {
            const content = fs.readFileSync(filePath, 'utf-8');
            const thesis: Thesis = JSON.parse(content);

            if (thesis.holdings.some(h => h.ticker === holding.ticker)) {
                throw new Error(`Holding ${holding.ticker} already exists`);
            }

            thesis.holdings.push(holding);

            // Validate
            const parseResult = ThesisSchema.safeParse(thesis);
            if (!parseResult.success) {
                throw new Error(`Validation Failed: ${parseResult.error.message}`);
            }

            // Save
            thesis.version++;
            thesis.updatedAt = new Date().toISOString();
            const tempPath = `${filePath}.tmp`;
            fs.writeFileSync(tempPath, JSON.stringify(thesis, null, 2));
            fs.renameSync(tempPath, filePath);

            return thesis;
        } finally {
            if (release!) await release();
        }
    }

    async removeHolding(thesisId: string, ticker: string): Promise<Thesis> {
        let release: () => Promise<void>;
        const filePath = this.getFilePath(thesisId);

        try {
            release = await lock(filePath, { retries: { retries: 5, maxTimeout: 2000 } });
        } catch (e) {
            throw new Error('Could not acquire file lock.');
        }

        try {
            const content = fs.readFileSync(filePath, 'utf-8');
            const thesis: Thesis = JSON.parse(content);

            const index = thesis.holdings.findIndex(h => h.ticker === ticker);
            if (index === -1) throw new Error(`Holding ${ticker} not found`);

            thesis.holdings.splice(index, 1);

            // Validate
            const parseResult = ThesisSchema.safeParse(thesis);
            if (!parseResult.success) {
                throw new Error(`Validation Failed: ${parseResult.error.message}`);
            }

            // Save
            thesis.version++;
            thesis.updatedAt = new Date().toISOString();
            const tempPath = `${filePath}.tmp`;
            fs.writeFileSync(tempPath, JSON.stringify(thesis, null, 2));
            fs.renameSync(tempPath, filePath);

            return thesis;
        } finally {
            if (release!) await release();
        }
    }

    async replaceHoldings(thesisId: string, newHoldings: Thesis['holdings']): Promise<Thesis> {
        let release: () => Promise<void>;
        const filePath = this.getFilePath(thesisId);

        try {
            release = await lock(filePath, { retries: { retries: 5, maxTimeout: 2000 } });
        } catch (e) {
            throw new Error('Could not acquire file lock.');
        }

        try {
            const content = fs.readFileSync(filePath, 'utf-8');
            const thesis: Thesis = JSON.parse(content);

            // Replace all holdings
            thesis.holdings = newHoldings;

            // Validate Schema (Zod) - This checks the 100% sum
            const parseResult = ThesisSchema.safeParse(thesis);
            if (!parseResult.success) {
                // If Zod error is confusing, we might want to wrap it, but raw is fine for now
                throw new Error(`Validation Failed: ${parseResult.error.message}`);
            }

            // Save
            thesis.version++;
            thesis.updatedAt = new Date().toISOString();
            const tempPath = `${filePath}.tmp`;
            fs.writeFileSync(tempPath, JSON.stringify(thesis, null, 2));
            fs.renameSync(tempPath, filePath);

            return thesis;
        } finally {
            if (release!) await release();
        }
    }

    async deleteThesis(id: string): Promise<boolean> {
        const filePath = this.getFilePath(id);
        if (!fs.existsSync(filePath)) return false;

        let release: () => Promise<void>;
        try {
            release = await lock(filePath, { retries: { retries: 5, maxTimeout: 2000 } });
        } catch (e) {
            throw new Error('Could not acquire lock for deletion.');
        }

        try {
            fs.unlinkSync(filePath);
            return true;
        } finally {
            await release();
        }
    }

    async optimizePortfolio(thesisId: string): Promise<any> {
        const healthCheck = await this.computeHealthCheck(thesisId);

        // Read Prompt
        if (!fs.existsSync(REBALANCE_PROMPT_PATH)) {
            throw new Error(`Rebalance prompt not found at ${REBALANCE_PROMPT_PATH}`);
        }
        const promptTemplate = fs.readFileSync(REBALANCE_PROMPT_PATH, 'utf-8');

        // Construct Final Prompt
        const prompt = `
        ${promptTemplate}

        DATA INPUT:
        ${JSON.stringify(healthCheck, null, 2)}
        `;

        console.log(`[ThesisService] Asking Gemini to optimize thesis ${thesisId}...`);

        try {
            const llmResponse = await geminiService.generateContent(prompt);
            return this.parseResponse(llmResponse);
        } catch (error: any) {
            console.error("[ThesisService] Optimization failed:", error);
            throw new Error(`Optimization failed: ${error.message}`);
        }
    }

    private parseResponse(text: string): any {
        try {
            // Clean markdown code blocks if present
            const cleanText = text.replace(/```json/g, '').replace(/```/g, '').trim();
            return JSON.parse(cleanText);
        } catch (error) {
            console.error("[ThesisService] Failed to parse LLM response:", text);
            throw new Error("Invalid format from Thesis Optimizer.");
        }
    }
}

export const thesisService = new ThesisService();
