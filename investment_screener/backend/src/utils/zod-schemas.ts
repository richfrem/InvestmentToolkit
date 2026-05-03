import { z } from 'zod';

// Helper for validating ticker symbols (Unified Regex: 1-5 letters, optional dot + 1-3 letters, OR simple 1-10 alphanumeric for broader compatibility if needed, but keeping strict for now based on previous valid file)
// Red Team D3: Unify with index.ts which uses /^[A-Z0-9.\-]{1,10}$/
// Let's use the broader one from index.ts to allow BRK-B, BTC-USD, etc.
const tickerRegex = /^[A-Z0-9.\-]{1,10}$/;

// Scenario Schema — .passthrough() preserves v1.2 fields (year5Revenue, year5NetIncome,
// year5EPS, scenarioPrice, risks) without stripping them on save.
export const ScenarioSchema = z.object({
    weight: z.number().min(0).max(1),
    growthRate: z.number().min(-100).max(1000),
    netMargin: z.number().min(-100).max(100),
    exitPE: z.number().min(0).max(1000),
    qualityMultiplier: z.number().min(0.1).max(10),
    shareChange: z.number().min(-100).max(1000),
    rationale: z.string().max(10000).optional(),  // raised from 2000 — detailed AI rationales are long
    moatScore: z.number().min(0).max(5).optional(),
    managementScore: z.number().min(0).max(5).optional(),
    // v1.2 output fields
    year5Revenue: z.number().optional(),
    year5NetIncome: z.number().optional(),
    year5EPS: z.number().optional(),
    scenarioPrice: z.number().optional(),
    risks: z.array(z.string()).optional(),
}).passthrough(); // preserve any future extension fields

// Snapshot Schema
export const SnapshotSchema = z.object({
    price: z.number().nonnegative(),
    currency: z.string().length(3),
    shares: z.number().nonnegative(),
    revenue: z.number().nonnegative(),
    lastActualPS: z.number().nonnegative().nullable().transform(v => v ?? 0),
    fiscalPeriod: z.string().optional(),
    analystGrowthEstimate: z.number().nullable().optional(),
    analystMarginEstimate: z.number().nullable().optional(),
});

// Full Projection Schema — .passthrough() ensures analyticsLog and any future v1.x
// extension fields are preserved in parseResult.data (not just the original object).
export const ProjectionSchema = z.object({
    ticker: z.string().regex(tickerRegex),
    id: z.string().uuid(),
    source: z.enum(['USER', 'SYSTEM', 'AI_AGENT']).default('USER'),
    schemaVersion: z.union([z.literal('1.1'), z.literal('1.2')]),
    version: z.number().int().nonnegative(),
    savedAt: z.string().datetime(),
    updatedAt: z.string().datetime(),
    name: z.string().min(1).max(200),  // raised from 100 — AI names include ticker + date
    rationale: z.string().max(10000).optional(),  // raised from 5000
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
        const sum = data.bear.weight + data.base.weight + data.bull.weight;
        return Math.abs(sum - 1.0) < 0.01;
    }, {
        message: "Scenario weights must sum to 1.0",
        path: ["base"],
    }),
    aiThesis: z.object({
        model: z.string(),
        rationale: z.string(),
        fairValue: z.number(),
        // BUY/HOLD/SELL = pure DCF valuation signal.
        // INITIATE/ACCUMULATE/MAINTAIN/TRIM/EXIT/WATCHLIST = portfolio-level action recommendation.
        // Both live in this one field; the most recent version of a projection carries the portfolio action.
        action: z.enum(['BUY', 'HOLD', 'SELL', 'INITIATE', 'ACCUMULATE', 'MAINTAIN', 'TRIM', 'EXIT', 'WATCHLIST']),
        analyzedAt: z.string().datetime(),
        researchReport: z.string().max(200).optional(),
    }).optional(),
    globalSettings: z.object({
        discountRate: z.number().min(0).max(100),
        timeHorizon: z.number().int().min(1).max(50),
    }),
    // v1.2: full analytical decision log — preserved but not rigidly typed so schema
    // changes to analyticsLog don't require backend deploys.
    analyticsLog: z.record(z.unknown()).optional(),
}).passthrough();

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
    // slug-style id (e.g. "target-portfolio", "thesis") — no longer requires UUID format
    id: z.string().min(1).max(100).regex(/^[a-z0-9-]+$/, 'id must be lowercase letters, digits or hyphens'),
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
    hasValuation: z.boolean(),
    latestAction: z.enum(['BUY', 'HOLD', 'SELL', 'INITIATE', 'ACCUMULATE', 'MAINTAIN', 'TRIM', 'EXIT', 'WATCHLIST']).optional(),
    latestFairValue: z.number().optional(),
});

export const HealthCheckSchema = z.object({
    thesisId: z.string().min(1).max(100),
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
