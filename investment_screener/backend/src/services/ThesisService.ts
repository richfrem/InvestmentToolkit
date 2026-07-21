/**
 * ThesisService.ts - Core engine for managing investment theses, strategy pillars, and portfolio drift.
 * 
 * Purpose:
 *   The core engine for managing investment theses, strategy pillars, and portfolio drift analysis.
 *   Orchestrates health checks, strategic reviews via AI, and trade optimization logic.
 * 
 * Layer:
 *   Backend / Services / Strategy
 * 
 * Usage Examples:
 *   const health = await thesisService.computeHealthCheck(thesisId);
 *   const review = await thesisService.performStrategicReview(thesisId);
 * 
 * Key Functions (Index):
 *   - getFilePath(id: string) - Resolves file path for thesis JSON data
 *   - normalizeTicker(ticker: string) - Substitute Questrade formats with canonical ones
 *   - getProjectionPath(ticker: string) - Resolves file path for stock projection JSON data
 *   - getLatestAIProjection(ticker: string) - Retrieve the latest versioned AI projection for a ticker
 *   - getPortfolioItems() - Retrieves all items in the portfolio
 *   - getAccountPolicy() - Returns the parsed account policy configuration
 *   - computeBandPct(targetPct, bandConfig) - Computes absolute percentage bands
 *   - computeHealthCheck(thesisId: string) - Calculates portfolio drift at both holding and pillar levels, generating alerts
 *   - getThesis(id: string) - Fetches a thesis configuration by its ID
 *   - listTheses() - Retrieves a list of all theses
 *   - saveThesis(thesis: Thesis) - Saves a thesis with version verification and lock protection
 *   - updateHolding(thesisId, ticker, updates) - Updates a single holding's details in a thesis
 *   - addHolding(thesisId, holding) - Adds a new holding to a thesis
 *   - removeHolding(thesisId, ticker) - Removes a holding from a thesis
 *   - replaceHoldings(thesisId, newHoldings) - Replaces the entire holding list in a thesis
 *   - performStrategicReview(thesisId: string) - Combines thesis targets with AI valuation data to produce a qualitative adversarial report
 *   - deleteThesis(id: string) - Deletes a thesis file
 *   - optimizePortfolio(thesisId: string) - Generates specific trade recommendations to restore thesis alignment
 *   - parseResponse(text: string) - Helper to clean and parse JSON blocks from LLM responses
 * 
 * Key Input Dependencies:
 *   - investment_screener/backend/data/theses/ (stores theses JSON)
 *   - ./ProjectionService (reads AI projections from data/domain_model.sqlite, ADR-029 —
 *     migrated off data/projections/*.json in Task 7C; see getLatestAIProjection)
 *   - ./PortfolioRepository (reads portfolio holdings from data/domain_model.sqlite's
 *     account_investment/investment_price tables, Wave 3 Task 6 — see getPortfolioItems.
 *     Falls back to investment_screener/backend/data/portfolio.json only when SQLite
 *     has no priced position data yet.)
 *   - investment_screener/backend/data/account_policy.json (reads drift config)
 *
 * Key Output Dependencies:
 *   - investment_screener/backend/data/theses/ (writes theses JSON)
 *
 * Wave 2 Task 10/11 investigation (NOT rewired — documented stop, not an oversight):
 *   getThesis()/listTheses()/saveThesis()/updateHolding()/addHolding()/removeHolding()/
 *   replaceHoldings() read and write the FULL target-portfolio.json Thesis document
 *   (and any other file under data/theses/*.json addressed by id). This is a lossy,
 *   non-mechanical rewire target: the JSON document carries fields with no SQLite
 *   column anywhere in domain_model.sqlite today — `globalSettings`, `changeLog`,
 *   `schemaVersion`, per-pillar `bandConfig`, per-holding `shares`, and the full
 *   structured `thesisBreakers`/`standingDecision` sub-objects (SQLite only stores
 *   4 flat `standing_decision_*` scalar columns on `investment`, consumed
 *   read-only elsewhere — see InvestmentRepository.ts's `getInvestment()` and its
 *   dedicated standingDecision byte-for-byte test in
 *   tests/InvestmentRepository.spec.ts). Reconstructing the full Thesis document
 *   from SQLite would either drop these fields (breaking the frontend + other
 *   consumers of GET /api/theses/:id) or require new schema columns, which is out
 *   of scope for this wave (no schema changes permitted). computeHealthCheck()
 *   itself never reads `standingDecision` or `thesisBreakers` today — verified via
 *   `grep -rn "standingDecision" src/`, zero hits outside this note — so there is
 *   no active standingDecision *read* path in this class to cut over; the narrower
 *   partial-field reads (pillars, holdings summary for stock-lookup/all-holdings)
 *   were cut over instead, in theses.ts's GET /pillars route and
 *   InvestmentRepository.listThesisHoldings() (consumed by stock.ts and
 *   screener.ts), not here.
 */
import fs from 'fs';
import path from 'path';
import { lock } from 'proper-lockfile';
import {
    Thesis, ThesisSchema,
    HealthCheck, HealthCheckSchema,
    DriftEntry, HoldingHealth, Projection,
    AccountPolicy, AccountPolicySchema
} from '../utils/zod-schemas';
import { geminiService } from './GeminiService';
import { projectionService, ProjectionService } from './ProjectionService';
import { PortfolioRepository } from './PortfolioRepository';
import { DOMAIN_MODEL_DB_FILE } from '../utils/paths';

const THESES_DIR = path.resolve(__dirname, '../../data/theses');
const PORTFOLIO_FILE = path.resolve(__dirname, '../../data/portfolio.json');
const ACCOUNT_POLICY_FILE = path.resolve(__dirname, '../../data/account_policy.json');
const REBALANCE_PROMPT_PATH = path.resolve(__dirname, '../../../.agent/skills/portfolio-advisor/references/rebalance_prompt.md');
// Ensure directory exists
if (!fs.existsSync(THESES_DIR)) {
    fs.mkdirSync(THESES_DIR, { recursive: true });
}

export class ThesisService {

    /** Defaults to the shared `projectionService` singleton (SQLite-backed, ADR-029).
     * Constructor-injectable so tests can pass a fake/temp-db-backed instance without
     * ThesisService opening its own database connection or reading the filesystem.
     * `dbPath` (Wave 3 Task 6) is separately injectable so tests can point
     * getPortfolioItems() at a tmp-scoped SQLite file instead of the real
     * domain_model.sqlite, matching InvestmentRepository/PortfolioRepository's own
     * constructor-injection pattern rather than a module-level singleton. */
    constructor(
        private projections: Pick<ProjectionService, 'getProjections'> = projectionService,
        private dbPath: string = DOMAIN_MODEL_DB_FILE
    ) {}

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

    async getLatestAIProjection(ticker: string): Promise<Projection | null> {
        try {
            const projections = await this.projections.getProjections(ticker);

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

    /** Wave 3 Task 6: sourced from domain_model.sqlite (account_investment JOIN
     * investment_price, aggregated per-symbol via PortfolioRepository.listPositionsBySymbol())
     * rather than portfolio.json's `holdings` array. Falls back to the JSON file when
     * SQLite has no priced position data yet (e.g. before the first migration run),
     * matching routes/portfolio.ts's established fallback pattern for this same table. */
    async getPortfolioItems(): Promise<any[]> {
        try {
            const repo = new PortfolioRepository(this.dbPath);
            let positions: ReturnType<PortfolioRepository['listPositionsBySymbol']>;
            try {
                positions = repo.listPositionsBySymbol();
            } finally {
                repo.close();
            }
            if (positions.length > 0) {
                return positions.map(p => ({
                    symbol: p.symbol,
                    quantity: p.quantity,
                    price: p.price ?? p.averageCost ?? 0,
                }));
            }
        } catch (e) {
            console.error(`[ThesisService] Error reading portfolio positions from SQLite:`, e);
        }

        if (!fs.existsSync(PORTFOLIO_FILE)) return [];
        try {
            const raw = JSON.parse(fs.readFileSync(PORTFOLIO_FILE, 'utf-8'));
            return Array.isArray(raw) ? raw : (raw.holdings ?? []);
        } catch (e) {
            console.error(`[ThesisService] Error reading portfolio file:`, e);
            return [];
        }
    }

    private getAccountPolicy(): AccountPolicy | null {
        if (!fs.existsSync(ACCOUNT_POLICY_FILE)) return null;
        try {
            const data = JSON.parse(fs.readFileSync(ACCOUNT_POLICY_FILE, 'utf-8'));
            return AccountPolicySchema.parse(data);
        } catch (e) {
            console.error('[ThesisService] Error reading account_policy.json:', e);
            return null;
        }
    }

    private computeBandPct(targetPct: number, bandConfig: AccountPolicy['bandConfig']): number {
        return Math.max(targetPct * bandConfig.relativePct / 100, bandConfig.absolutePct);
    }

    async computeHealthCheck(thesisId: string): Promise<HealthCheck> {
        const thesis = await this.getThesis(thesisId);
        if (!thesis) throw new Error('Thesis not found');

        const portfolioItems = await this.getPortfolioItems();
        const accountPolicy = this.getAccountPolicy();
        const bandConfig = accountPolicy?.bandConfig ?? { relativePct: 20, absolutePct: 1.5, criticalMultiplier: 2.0 };

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

            const bandPct = this.computeBandPct(holding.targetWeight, bandConfig);
            let status: 'ON_TARGET' | 'DRIFT' | 'CRITICAL' = 'ON_TARGET';
            if (Math.abs(driftPct) >= bandPct * bandConfig.criticalMultiplier) status = 'CRITICAL';
            else if (Math.abs(driftPct) >= bandPct) status = 'DRIFT';

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
                latestFairValue: aiProj?.aiThesis?.fairValue,
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
                    message: `${holding.ticker} is drifting ${driftPct.toFixed(1)}% (Band: ${bandPct.toFixed(1)}pp)`,
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

            const pillarBandPct = this.computeBandPct(pillar.targetWeight, bandConfig);
            let status: 'ON_TARGET' | 'DRIFT' | 'CRITICAL' = 'ON_TARGET';
            if (Math.abs(driftPct) >= pillarBandPct * bandConfig.criticalMultiplier) status = 'CRITICAL';
            else if (Math.abs(driftPct) >= pillarBandPct) status = 'DRIFT';

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
            const files = (await fs.promises.readdir(THESES_DIR)).filter(f => f.endsWith('.json'));
            const results = await Promise.all(
                files.map(async file => {
                    try {
                        const content = await fs.promises.readFile(path.join(THESES_DIR, file), 'utf-8');
                        const thesis = JSON.parse(content);
                        return { id: thesis.id as string, name: thesis.name as string, updatedAt: thesis.updatedAt as string };
                    } catch {
                        console.warn(`[ThesisService] Failed to parse ${file}, skipping.`);
                        return null;
                    }
                })
            );
            const theses = results.filter((t): t is NonNullable<typeof t> => t !== null);
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
                thesis.version = Number(existingThesis.version || 0) + 1;
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
            thesis.version = Number(thesis.version || 0) + 1;
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
            thesis.version = Number(thesis.version || 0) + 1;
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
            thesis.version = Number(thesis.version || 0) + 1;
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
            thesis.version = Number(thesis.version || 0) + 1;
            thesis.updatedAt = new Date().toISOString();
            const tempPath = `${filePath}.tmp`;
            fs.writeFileSync(tempPath, JSON.stringify(thesis, null, 2));
            fs.renameSync(tempPath, filePath);

            return thesis;
        } finally {
            if (release!) await release();
        }
    }

    async performStrategicReview(thesisId: string): Promise<any> {
        const health = await this.computeHealthCheck(thesisId);
        const thesis = await this.getThesis(thesisId);
        if (!thesis) throw new Error('Thesis not found');

        // strategic_review_prompt.md path
        const promptPath = path.resolve(__dirname, '../../../.agent/skills/portfolio-advisor/references/strategic_review_prompt.md');
        let promptTemplate = '';

        if (fs.existsSync(promptPath)) {
            promptTemplate = fs.readFileSync(promptPath, 'utf-8');
        } else {
            // Fallback prompt if file missing
            promptTemplate = `
You are a Strategic Investment Advisor. Review the portfolio health and thesis alignment.
Identify any "Strategic Conflicts" where market data contradicts the thesis.
Check if any holding's "Thesis Breakers" might be triggered based on available data.
Provide a qualitative assessment before suggesting any trades.
            `;
        }

        const prompt = `
${promptTemplate}

THESIS:
${JSON.stringify({ name: thesis.name, pillars: thesis.pillars, globalSettings: thesis.globalSettings }, null, 2)}

HOLDINGS & BREAKERS:
${JSON.stringify(thesis.holdings.map(h => ({ ticker: h.ticker, role: h.role, breakers: h.thesisBreakers })), null, 2)}

HEALTH CHECK DATA:
${JSON.stringify(health, null, 2)}
        `;

        console.log(`[ThesisService] Asking Gemini for Strategic Review of ${thesisId}...`);

        try {
            const llmResponse = await geminiService.generateContent(prompt);
            return {
                timestamp: new Date().toISOString(),
                analysis: llmResponse
            };
        } catch (error: any) {
            console.error("[ThesisService] Strategic Review failed:", error);
            throw new Error(`Strategic Review failed: ${error.message}`);
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
