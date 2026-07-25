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
 *   - normalizeTicker(ticker: string) - Substitute Questrade formats with canonical ones
 *   - getProjectionPath(ticker: string) - Resolves file path for stock projection JSON data
 *   - getLatestAIProjection(ticker: string) - Retrieve the latest versioned AI projection for a ticker
 *   - getPortfolioItems() - Retrieves all items in the portfolio
 *   - getAccountPolicy() - Returns the parsed account policy configuration
 *   - computeBandPct(targetPct, bandConfig) - Computes absolute percentage bands
 *   - computeHealthCheck(thesisId: string) - Calculates portfolio drift at both holding and pillar levels, generating alerts
 *   - getThesis(id: string) - Assembles the thesis document from SQLite
 *   - listTheses() - Returns the single canonical thesis entry
 *   - saveThesis(thesis: Thesis) - Validates and writes every field to SQLite
 *   - updateHolding(thesisId, ticker, updates) - Updates a single holding's details
 *   - addHolding(thesisId, holding) - Adds a new holding
 *   - removeHolding(thesisId, ticker) - Clears a holding's thesis fields (zeroes target_weight)
 *   - replaceHoldings(thesisId, newHoldings) - Replaces the entire holding list
 *   - performStrategicReview(thesisId: string) - Combines thesis targets with AI valuation data to produce a qualitative adversarial report
 *   - deleteThesis(id: string) - No-op for the canonical id (nothing to delete; single-document architecture)
 *   - optimizePortfolio(thesisId: string) - Generates specific trade recommendations to restore thesis alignment
 *   - parseResponse(text: string) - Helper to clean and parse JSON blocks from LLM responses
 *
 * Key Input Dependencies:
 *   - domain_model.sqlite: investment, strategy_pillar, price_level_set/tier,
 *     portfolio_change_log, portfolio_policy tables (sole source of truth for
 *     the thesis document — Wave 8)
 *   - ./ProjectionService (reads AI projections from domain_model.sqlite)
 *   - ./PortfolioRepository, ./InvestmentRepository, ./PriceLevelRepository,
 *     ./PortfolioChangeLogRepository
 *
 * Key Output Dependencies:
 *   - domain_model.sqlite (writes via the repositories above)
 */
import fs from 'fs';
import path from 'path';
import {
    Thesis, ThesisSchema,
    HealthCheck, HealthCheckSchema,
    DriftEntry, HoldingHealth, Projection,
    AccountPolicy, AccountPolicySchema
} from '../utils/zod-schemas';
import { geminiService } from './GeminiService';
import { projectionService, ProjectionService } from './ProjectionService';
import { PortfolioRepository } from './PortfolioRepository';
import { InvestmentRepository } from './InvestmentRepository';
import { PriceLevelRepository, PriceTierRow, StopLossRow } from './PriceLevelRepository';
import { PortfolioChangeLogRepository } from './PortfolioChangeLogRepository';
import { DOMAIN_MODEL_DB_FILE } from '../utils/paths';

const PORTFOLIO_FILE = path.resolve(__dirname, '../../data/portfolio.json');
const REBALANCE_PROMPT_PATH = path.resolve(__dirname, '../../../.agent/skills/portfolio-advisor/references/rebalance_prompt.md');

// The single, real thesis document this app has ever had one of. Wave 8 fully
// cut this over to domain_model.sqlite (investment/strategy_pillar/
// price_level_set/price_level_tier/portfolio_change_log tables) -- no
// multi-thesis-by-id scheme is actually in use, so getThesis()/listTheses()
// only ever resolve this one id.
const CANONICAL_THESIS_ID = 'target-portfolio';

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

    /** Wave 5E cutover: sourced from domain_model.sqlite's portfolio_policy singleton
     * row (via PortfolioRepository.getPortfolioPolicy()) rather than account_policy.json.
     * Reshapes the flat SQLite row back into AccountPolicySchema's nested shape so
     * every caller (computeBandPct, computeHealthCheck) needs no changes. */
    private getAccountPolicy(): AccountPolicy | null {
        try {
            const repo = new PortfolioRepository(this.dbPath);
            let row: Record<string, unknown> | null;
            try {
                row = repo.getPortfolioPolicy();
            } finally {
                repo.close();
            }
            if (!row) return null;
            const data = {
                accountPreferenceRules: JSON.parse((row.account_preference_rules_json as string) ?? '[]'),
                psuFundingRule: JSON.parse((row.psu_funding_rule_json as string) ?? '{}'),
                riskBudgetCaps: {
                    maxMarginalRiskContributionPct: row.max_marginal_risk_contribution_pct,
                    maxClusterVarianceContributionPct: row.max_cluster_variance_contribution_pct,
                },
                bandConfig: {
                    relativePct: row.rebalance_band_relative_pct,
                    absolutePct: row.rebalance_band_absolute_pct,
                    criticalMultiplier: row.rebalance_band_critical_multiplier,
                },
            };
            return AccountPolicySchema.parse(data);
        } catch (e) {
            console.error('[ThesisService] Error reading portfolio_policy from SQLite:', e);
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
            } else if (status === 'DRIFT' && holding.role !== 'watchlist') {
                // Wave 8: role's real enum ('accumulate'/'avoid'/'watchlist'/'trim'/
                // 'initiate'/'exit') has no 'core' value -- this check previously
                // never fired in production (confirmed zero real holdings ever had
                // role='core'). Closest defensible equivalent: alert on any holding
                // that's an actual thesis target, not merely watchlisted.
                alerts.push({
                    severity: 'WARNING',
                    message: `${holding.ticker} is drifting ${driftPct.toFixed(1)}% (Band: ${bandPct.toFixed(1)}pp)`,
                    ticker: holding.ticker,
                    pillarId: holding.pillarId,
                    action: driftPct < 0 ? 'BUY' : 'SELL'
                });
            }

            if (!aiProj && holding.role !== 'watchlist') {
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

    /** Assembles the one real thesis document from SQLite: strategy_pillar
     * (pillars), investment + price_level_set/tier (holdings), portfolio_policy
     * (globalSettings). Returns null for any id other than the canonical one --
     * no multi-thesis-by-id scheme is actually in use. */
    private buildThesisFromDb(): Thesis | null {
        const investmentRepo = new InvestmentRepository(this.dbPath);
        const priceLevelRepo = new PriceLevelRepository(this.dbPath);
        const portfolioRepo = new PortfolioRepository(this.dbPath);
        try {
            const holdingRows = investmentRepo.listThesisHoldings();
            if (holdingRows.length === 0) return null;

            const pillars = investmentRepo.listPillars().map(p => ({
                id: p.id, name: p.name, targetWeight: p.targetWeight ?? 0,
            }));

            const holdings = holdingRows.map(h => {
                const pl = priceLevelRepo.getPriceLevels(h.ticker);
                const priceLevels = pl ? {
                    schemaVersion: pl.schemaVersion ?? '1.0',
                    lastUpdated: pl.lastUpdated ?? new Date().toISOString(),
                    lastUpdatedBy: pl.lastUpdatedBy ?? 'system',
                    buyTiers: pl.buyTiers as any,
                    sellTiers: pl.sellTiers as any,
                    stopLoss: (pl.stopLoss ?? undefined) as any,
                } : undefined;
                return {
                    ticker: h.ticker,
                    name: h.name ?? h.ticker,
                    pillarId: h.pillarId ?? 'other',
                    targetWeight: h.targetWeight ?? 0,
                    targetEntryPrice: pl?.targetEntryPrice ?? undefined,
                    thesisForInclusion: h.thesisForInclusion ?? '',
                    role: (h.role as any) ?? 'core',
                    priceLevels,
                    subStrategyId: h.subStrategyId ?? undefined,
                    agentRationale: h.agentRationale ?? undefined,
                } as Thesis['holdings'][0];
            });

            const policy = portfolioRepo.getPortfolioPolicy();
            const globalSettings = {
                rebalanceFrequency: (policy?.rebalance_frequency as any) ?? 'quarterly',
                portfolioValueUSD: (policy?.portfolio_value_usd_target as number) ?? undefined,
            };

            const changeLogRepo = new PortfolioChangeLogRepository(this.dbPath);
            let changeLog: Array<{ version: string; date: string; note: string }>;
            try {
                changeLog = changeLogRepo.listEntries().map(e => ({ version: e.version, date: e.entryDate, note: e.note }));
            } finally {
                changeLogRepo.close();
            }

            const updatedAt = holdingRows.reduce((latest, h: any) => {
                const t = h.updatedAt ?? h.updated_at;
                return t && (!latest || t > latest) ? t : latest;
            }, '') || new Date().toISOString();

            const latestVersion = changeLog.length > 0 ? changeLog[changeLog.length - 1].version : '1';

            return {
                id: CANONICAL_THESIS_ID,
                name: 'Investment Thesis',
                schemaVersion: '1.0',
                version: latestVersion,
                createdAt: '2026-02-14T12:00:00Z',
                updatedAt,
                description: 'Investment thesis (SQLite-backed, Wave 8).',
                pillars,
                holdings,
                globalSettings,
                ...( { changeLog } as any ),
            } as Thesis;
        } finally {
            investmentRepo.close();
            priceLevelRepo.close();
            portfolioRepo.close();
        }
    }

    async getThesis(id: string): Promise<Thesis | null> {
        if (id !== CANONICAL_THESIS_ID) return null;
        try {
            return this.buildThesisFromDb();
        } catch (error) {
            console.error(`[ThesisService] Error building thesis ${id} from SQLite:`, error);
            return null;
        }
    }

    async listTheses(): Promise<{ id: string; name: string; updatedAt: string }[]> {
        const thesis = await this.getThesis(CANONICAL_THESIS_ID);
        if (!thesis) return [];
        return [{ id: thesis.id, name: thesis.name, updatedAt: thesis.updatedAt }];
    }

    /** Writes every holding's thesis fields + price levels into SQLite.
     * Pillars are NOT written here -- strategy_pillar has no TS writer yet
     * (matches portfolio_policy's established "TS read-only" pattern); pillar
     * definitions change rarely and are out of this wave's scope. */
    async saveThesis(thesis: Thesis): Promise<void> {
        const parseResult = ThesisSchema.safeParse(thesis);
        if (!parseResult.success) {
            throw new Error(`Validation Failed: ${parseResult.error.message}`);
        }

        const investmentRepo = new InvestmentRepository(this.dbPath);
        const priceLevelRepo = new PriceLevelRepository(this.dbPath);
        try {
            for (const h of thesis.holdings) {
                this.writeHoldingToDb(h, investmentRepo, priceLevelRepo);
            }
        } finally {
            investmentRepo.close();
            priceLevelRepo.close();
        }
    }

    /** Shared write helper used by saveThesis/updateHolding/addHolding/replaceHoldings. */
    private writeHoldingToDb(
        holding: Thesis['holdings'][0],
        investmentRepo: InvestmentRepository,
        priceLevelRepo: PriceLevelRepository
    ): void {
        investmentRepo.updateThesisFields(holding.ticker, {
            name: holding.name,
            pillarId: (holding as any).pillarId,
            subStrategyId: (holding as any).subStrategyId,
            targetWeight: holding.targetWeight,
            thesisForInclusion: (holding as any).thesisForInclusion,
            agentRationale: (holding as any).agentRationale,
            role: (holding as any).role,
        });

        const pl = (holding as any).priceLevels;
        if (pl) {
            priceLevelRepo.replacePriceLevels(
                holding.ticker,
                pl.schemaVersion ?? '1.0', pl.lastUpdated ?? new Date().toISOString(),
                pl.lastUpdatedBy ?? 'system', null,
                (pl.buyTiers ?? []) as PriceTierRow[], (pl.sellTiers ?? []) as PriceTierRow[],
                (pl.stopLoss ?? null) as StopLossRow | null,
                (holding as any).targetEntryPrice ?? null
            );
        }
    }

    async updateHolding(thesisId: string, ticker: string, updates: Partial<Thesis['holdings'][0]>): Promise<Thesis> {
        if (thesisId !== CANONICAL_THESIS_ID) throw new Error(`Thesis ${thesisId} not found`);
        const thesis = await this.getThesis(thesisId);
        if (!thesis) throw new Error('Thesis not found');
        const index = thesis.holdings.findIndex(h => h.ticker === ticker);
        if (index === -1) throw new Error(`Holding ${ticker} not found`);

        const updatedHolding = { ...thesis.holdings[index], ...updates };
        thesis.holdings[index] = updatedHolding;

        const parseResult = ThesisSchema.safeParse(thesis);
        if (!parseResult.success) {
            throw new Error(`Validation Failed: ${parseResult.error.message}`);
        }

        const investmentRepo = new InvestmentRepository(this.dbPath);
        const priceLevelRepo = new PriceLevelRepository(this.dbPath);
        try {
            this.writeHoldingToDb(updatedHolding, investmentRepo, priceLevelRepo);
        } finally {
            investmentRepo.close();
            priceLevelRepo.close();
        }
        return (await this.getThesis(thesisId))!;
    }

    async addHolding(thesisId: string, holding: Thesis['holdings'][0]): Promise<Thesis> {
        if (thesisId !== CANONICAL_THESIS_ID) throw new Error(`Thesis ${thesisId} not found`);
        const thesis = await this.getThesis(thesisId);
        if (!thesis) throw new Error('Thesis not found');
        if (thesis.holdings.some(h => h.ticker === holding.ticker)) {
            throw new Error(`Holding ${holding.ticker} already exists`);
        }
        thesis.holdings.push(holding);

        const parseResult = ThesisSchema.safeParse(thesis);
        if (!parseResult.success) {
            throw new Error(`Validation Failed: ${parseResult.error.message}`);
        }

        const investmentRepo = new InvestmentRepository(this.dbPath);
        const priceLevelRepo = new PriceLevelRepository(this.dbPath);
        try {
            this.writeHoldingToDb(holding, investmentRepo, priceLevelRepo);
        } finally {
            investmentRepo.close();
            priceLevelRepo.close();
        }
        return (await this.getThesis(thesisId))!;
    }

    /** Clears a holding's thesis fields (zeroes target_weight, clears pillar/
     * rationale) rather than deleting the investment row -- SQLite has no
     * per-holding "delete" concept here; the row still legitimately exists
     * for held-position tracking even once it's no longer a thesis target. */
    async removeHolding(thesisId: string, ticker: string): Promise<Thesis> {
        if (thesisId !== CANONICAL_THESIS_ID) throw new Error(`Thesis ${thesisId} not found`);
        const thesis = await this.getThesis(thesisId);
        if (!thesis) throw new Error('Thesis not found');
        const index = thesis.holdings.findIndex(h => h.ticker === ticker);
        if (index === -1) throw new Error(`Holding ${ticker} not found`);
        thesis.holdings.splice(index, 1);

        const investmentRepo = new InvestmentRepository(this.dbPath);
        try {
            investmentRepo.updateThesisFields(ticker, { targetWeight: 0 });
        } finally {
            investmentRepo.close();
        }
        return (await this.getThesis(thesisId))!;
    }

    async replaceHoldings(thesisId: string, newHoldings: Thesis['holdings']): Promise<Thesis> {
        if (thesisId !== CANONICAL_THESIS_ID) throw new Error(`Thesis ${thesisId} not found`);
        const thesis = await this.getThesis(thesisId);
        if (!thesis) throw new Error('Thesis not found');
        thesis.holdings = newHoldings;

        const parseResult = ThesisSchema.safeParse(thesis);
        if (!parseResult.success) {
            throw new Error(`Validation Failed: ${parseResult.error.message}`);
        }

        const investmentRepo = new InvestmentRepository(this.dbPath);
        const priceLevelRepo = new PriceLevelRepository(this.dbPath);
        try {
            for (const h of newHoldings) {
                this.writeHoldingToDb(h, investmentRepo, priceLevelRepo);
            }
        } finally {
            investmentRepo.close();
            priceLevelRepo.close();
        }
        return (await this.getThesis(thesisId))!;
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

    /** No-op for the canonical id: this is a single-document architecture --
     * "deleting the thesis" has no SQLite analogy (it would mean wiping every
     * investment's thesis fields, a much more destructive and different
     * operation than the original file-delete). Returns false for any id,
     * matching the original "nothing found to delete" contract. */
    async deleteThesis(_id: string): Promise<boolean> {
        return false;
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
