import { z } from 'zod';

// Helper for validating ticker symbols (Unified Regex: 1-5 letters, optional dot + 1-3 letters, OR simple 1-10 alphanumeric for broader compatibility if needed, but keeping strict for now based on previous valid file)
// Red Team D3: Unify with index.ts which uses /^[A-Z0-9.\-]{1,10}$/
// Let's use the broader one from index.ts to allow BRK-B, BTC-USD, etc.
const tickerRegex = /^[A-Z0-9.\-]{1,10}$/;

// Scenario Schema
export const ScenarioSchema = z.object({
    weight: z.number().min(0).max(1),
    growthRate: z.number().min(-100).max(1000), // Reasonable bounds for growth
    netMargin: z.number().min(-100).max(100),
    exitPE: z.number().min(0).max(1000),
    qualityMultiplier: z.number().min(0.1).max(10), // Quality multiplier range
    shareChange: z.number().min(-100).max(1000), // Share dilution/buyback %
    rationale: z.string().max(2000).optional(), // Limit rationale length
    moatScore: z.number().min(0).max(5).optional(), // 0-5
    managementScore: z.number().min(0).max(5).optional(), // 0-5
});

// Snapshot Schema
export const SnapshotSchema = z.object({
    price: z.number().nonnegative(),
    currency: z.string().length(3),
    shares: z.number().nonnegative(),
    revenue: z.number().nonnegative(),
    lastActualPS: z.number().nonnegative(),
    fiscalPeriod: z.string().optional(),
    analystGrowthEstimate: z.number().optional(),
    analystMarginEstimate: z.number().optional(),
});

// Full Projection Schema
export const ProjectionSchema = z.object({
    ticker: z.string().regex(tickerRegex),
    id: z.string().uuid(),
    source: z.enum(['USER', 'SYSTEM', 'AI_AGENT']).default('USER'), // Red Team C2: Source Isolation
    schemaVersion: z.literal('1.1'),
    version: z.number().int().nonnegative(),
    savedAt: z.string().datetime(),
    updatedAt: z.string().datetime(),
    name: z.string().min(1).max(100),
    rationale: z.string().max(5000).optional(),
    snapshot: SnapshotSchema,
    dataPreferences: z.object({
        growthBasis: z.enum(['ttm', 'next', 'current']),
        marginBasis: z.enum(['ttm', 'next', 'quarterly']),
    }),
    scenarios: z.object({
        bear: ScenarioSchema,
        base: ScenarioSchema,
        bull: ScenarioSchema,
    }).refine((data) => {
        // Validate strict weight sum = 1.0 (with small float tolerance)
        const sum = data.bear.weight + data.base.weight + data.bull.weight;
        return Math.abs(sum - 1.0) < 0.01;
    }, {
        message: "Scenario weights must sum to 1.0",
        path: ["base"], // Attach error to base scenario for UI simplicity
    }),
    aiThesis: z.object({
        model: z.string(),
        rationale: z.string(),
        fairValue: z.number(),
        action: z.enum(['BUY', 'HOLD', 'SELL']),
        analyzedAt: z.string().datetime(),
        researchReport: z.string().max(200).optional(), // Link to markdown report
    }).optional(), // Optional because user might save manual projection without AI
    globalSettings: z.object({
        discountRate: z.number().min(0).max(100),
        timeHorizon: z.number().int().min(1).max(50),
    }),
});

export type Projection = z.infer<typeof ProjectionSchema>;

// === THESIS SCHEMAS ===

export const ThesisHoldingSchema = z.object({
    ticker: z.string().regex(/^[A-Z0-9.\-]{1,10}$/),
    name: z.string().max(100),
    pillarId: z.string(),
    targetWeight: z.number().min(0).max(100),
    thesisForInclusion: z.string().max(2000).optional(),
    thesisBreakers: z.array(z.string().max(500)).max(5).optional(),
    role: z.enum(['core', 'hedge', 'speculative', 'reserve']).default('core'),
});

export const ThesisPillarSchema = z.object({
    id: z.string(),
    name: z.string().max(100),
    targetWeight: z.number().min(0).max(100),
    description: z.string().max(2000).optional(),
    thesisBreakers: z.array(z.string().max(500)).max(5).optional(),
});

export const ThesisSchema = z.object({
    id: z.string().uuid(),
    name: z.string().min(1).max(100),
    schemaVersion: z.literal('1.0'),
    version: z.number().int().nonnegative(),
    createdAt: z.string().datetime(),
    updatedAt: z.string().datetime(),
    description: z.string().max(5000).optional(),
    pillars: z.array(ThesisPillarSchema).min(1).max(20)
        .refine((pillars) => {
            const sum = pillars.reduce((s, p) => s + p.targetWeight, 0);
            return Math.abs(sum - 100) < 0.5;
        }, { message: "Pillar target weights must sum to 100%" }),
    holdings: z.array(ThesisHoldingSchema).min(1).max(100)
        .refine((holdings) => {
            const sum = holdings.reduce((s, h) => s + h.targetWeight, 0);
            return Math.abs(sum - 100) < 0.5;
        }, { message: "Holding target weights must sum to 100%" }),
    globalSettings: z.object({
        driftThresholdPct: z.number().min(0.5).max(20).default(3.0),
        criticalDriftPct: z.number().min(1).max(30).default(5.0),
        rebalanceFrequency: z.enum(['weekly', 'monthly', 'quarterly']).default('quarterly'),
        portfolioValueUSD: z.number().nonnegative().optional(),
    }),
});

export type Thesis = z.infer<typeof ThesisSchema>;
export type ThesisHolding = z.infer<typeof ThesisHoldingSchema>;
export type ThesisPillar = z.infer<typeof ThesisPillarSchema>;

// === HEALTH CHECK SCHEMAS (Tool B) ===

export const DriftEntrySchema = z.object({
    id: z.string(),
    name: z.string(),
    targetPct: z.number(),
    actualPct: z.number(),
    driftPct: z.number(),           // actual - target (negative = underweight)
    status: z.enum(['ON_TARGET', 'DRIFT', 'CRITICAL']),
});

export const HoldingHealthSchema = DriftEntrySchema.extend({
    ticker: z.string(),
    pillarId: z.string(),
    currentPrice: z.number().optional(),
    marketValue: z.number().optional(),
    role: z.enum(['core', 'hedge', 'speculative', 'reserve']),
    // Cross-reference with Tool A
    hasValuation: z.boolean(),       // Does a projection exist in projections/{TICKER}.json?
    latestAction: z.enum(['BUY', 'HOLD', 'SELL']).optional(),  // From Tool A's aiThesis
    latestFairValue: z.number().optional(),
});

export const HealthCheckSchema = z.object({
    thesisId: z.string().uuid(),
    thesisName: z.string(),
    analyzedAt: z.string().datetime(),
    portfolioValueUSD: z.number(),
    pillarHealth: z.array(DriftEntrySchema),
    holdingHealth: z.array(HoldingHealthSchema),
    alerts: z.array(z.object({
        severity: z.enum(['INFO', 'WARNING', 'CRITICAL']),
        message: z.string(),
        pillarId: z.string().optional(),
        ticker: z.string().optional(),
        action: z.enum(['BUY', 'SELL', 'HOLD', 'NONE']).optional() // Added for clarity in alerts
    })),
    summary: z.object({
        totalDriftScore: z.number(),    // Sum of |drift| across all pillars
        worstPillar: z.string().optional(),
        worstHolding: z.string().optional(),
        overallStatus: z.enum(['ALIGNED', 'DRIFTING', 'CRITICAL']),
    }),
});

export type DriftEntry = z.infer<typeof DriftEntrySchema>;
export type HoldingHealth = z.infer<typeof HoldingHealthSchema>;
export type HealthCheck = z.infer<typeof HealthCheckSchema>;
