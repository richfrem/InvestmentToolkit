/**
 * zod-schemas.ts - Shared Zod validation schemas and type inferences.
 * 
 * Purpose:
 *   Validates and parses JSON files (e.g. portfolio.json, target-portfolio.json,
 *   projections, account policy, health checks) to ensure structure integrity
 *   across frontend, backend, and agent plugins.
 * 
 * Key Input Dependencies:
 *   None
 * 
 * Key Output Dependencies:
 *   None
 * 
 * Schema & Type Index:
 *   - PriceTierSchema / PriceTier
 *   - StopLossSchema / StopLoss
 *   - PriceLevelsSchema / PriceLevels
 *   - PriceLevelSnapshotSchema / PriceLevelSnapshot
 *   - ScenarioSchema
 *   - SnapshotSchema
 *   - ProjectionSchema / Projection
 *   - ThesisHoldingSchema / ThesisHolding
 *   - PortfolioHoldingSchema / PortfolioHolding
 *   - ThesisPillarSchema / ThesisPillar
 *   - ThesisSchema / Thesis
 *   - AccountPolicySchema / AccountPolicy
 *   - DriftEntrySchema / DriftEntry
 *   - HoldingHealthSchema / HoldingHealth
 *   - HealthCheckSchema / HealthCheck
 */

import { z } from 'zod';

// === PRICE LEVEL SCHEMAS ===
// Structured tiered buy/sell price levels derived from DCF, TA, news, earnings, 13F.
// Written by update_price_levels.py — consumed by tv-alert-sync, ta-daily-sweep,
// rebalance-portfolio, and the daily-loop triage cards.

export const PriceTierSchema = z.object({
    tier: z.number().int().min(1),
    price: z.number().positive(),
    action: z.enum(['accumulate', 'accumulate_aggressive', 'trim', 'exit']),
    trimPct: z.number().min(1).max(100).nullable().optional(),
    orderType: z.enum(['limit', 'market', 'stop_limit']).default('limit'),
    basis: z.string().max(300),
    source: z.enum(['dcf', 'ta', 'news', 'earnings', '13f', 'manual']),
    sourceDate: z.string(),
    condition: z.string().nullable().optional(),
    status: z.enum(['active', 'triggered', 'cancelled', 'expired']).default('active'),
    triggeredAt: z.string().datetime().optional(),
});

export const StopLossSchema = z.object({
    price: z.number().positive(),
    basis: z.string().max(300),
    source: z.enum(['dcf', 'ta', 'news', 'earnings', '13f', 'manual']),
    sourceDate: z.string(),
    type: z.enum(['thesis_breaker', 'trailing', 'manual']),
    status: z.enum(['active', 'triggered', 'cancelled']).default('active'),
    triggeredAt: z.string().datetime().optional(),
});

export const PriceLevelsSchema = z.object({
    schemaVersion: z.string().default('1.0'),
    lastUpdated: z.string(),
    lastUpdatedBy: z.string(),
    buyTiers: z.array(PriceTierSchema).max(5).optional(),
    sellTiers: z.array(PriceTierSchema).max(5).optional(),
    stopLoss: StopLossSchema.optional(),
}).optional();

// Denormalized snapshot written into portfolio.json by update_price_levels.py.
// Refreshed on every /tv-portfolio-sync. Read-only — always derived from priceLevels.
export const PriceLevelSnapshotSchema = z.object({
    nextBuyTier: PriceTierSchema.nullable().optional(),
    nextSellTier: PriceTierSchema.nullable().optional(),
    stopLoss: StopLossSchema.nullable().optional(),
    proximityFlags: z.array(z.string()).optional(),
}).optional();

export type PriceTier = z.infer<typeof PriceTierSchema>;
export type StopLoss = z.infer<typeof StopLossSchema>;
export type PriceLevels = z.infer<typeof PriceLevelsSchema>;
export type PriceLevelSnapshot = z.infer<typeof PriceLevelSnapshotSchema>;

const tickerRegex = /^[A-Z0-9.\-_]{1,10}$/;

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
    schemaVersion: z.string().regex(/^1\.\d+$/),
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
    ticker: z.string().regex(tickerRegex),
    name: z.string().max(100),
    pillarId: z.string().optional().default('other'),
    targetWeight: z.number().min(0).max(100),
    targetEntryPrice: z.number().positive().nullable().optional(),
    thesisForInclusion: z.string().max(2000).optional(),
    thesisBreakers: z.array(z.string().max(500)).max(5).optional(),
    role: z.enum(['accumulate', 'avoid', 'watchlist', 'trim', 'initiate', 'exit']).default('watchlist'),
    // Structured tiered price levels — written by update_price_levels.py
    priceLevels: PriceLevelsSchema,
}).passthrough(); // allow agentRationale, shares, subStrategyId and other free fields

// Live portfolio holding schema (portfolio.json) — broker-synced snapshot.
// priceLevelSnapshot is denormalized from target-portfolio.json on every sync.
export const PortfolioHoldingSchema = z.object({
    symbol: z.string().regex(tickerRegex),
    shares: z.number().nonnegative(),
    book_price: z.number().nonnegative().optional(),
    market_value: z.number().optional(),
    price: z.number().nonnegative(),
    last_updated: z.string().optional(),
    // Denormalized tier snapshot — read-only, derived from priceLevels
    priceLevelSnapshot: PriceLevelSnapshotSchema,
}).passthrough();

export type PortfolioHolding = z.infer<typeof PortfolioHoldingSchema>;

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
    version: z.union([z.number(), z.string()]),
    createdAt: z.string().datetime(),
    updatedAt: z.string().datetime(),
    description: z.string().max(5000).optional(),
    pillars: z.array(ThesisPillarSchema).min(1).max(20),
    holdings: z.array(ThesisHoldingSchema).min(1).max(100)
        .refine((holdings) => {
            const sum = holdings.reduce((s, h) => s + h.targetWeight, 0);
            return Math.abs(sum - 100) < 0.5;
        }, { message: "Holding target weights must sum to 100%" }),
    globalSettings: z.object({
        rebalanceFrequency: z.enum(['weekly', 'monthly', 'quarterly']).default('quarterly'),
        portfolioValueUSD: z.number().nonnegative().optional(),
    }),
});

// === ACCOUNT POLICY SCHEMA (E2 — Rebalancer v2) ===
// account_policy.json — drift-band config, risk-budget caps, account/tax
// placement rules. Read by both rebalancer.py (Python) and this service
// (TypeScript, independently re-implemented, not shelled out to Python).

export const AccountPolicySchema = z.object({
    accountPreferenceRules: z.array(z.object({
        match: z.string(),
        prefer: z.enum(['TFSA', 'RRSP', 'Cash']),
        reason: z.string().optional(),
    })),
    psuFundingRule: z.object({
        ticker: z.string(),
        sameAccountOnly: z.boolean(),
        sharesFormula: z.string(),
    }),
    riskBudgetCaps: z.object({
        maxMarginalRiskContributionPct: z.number().positive(),
        maxClusterVarianceContributionPct: z.number().positive(),
    }),
    bandConfig: z.object({
        relativePct: z.number().positive(),
        absolutePct: z.number().positive(),
        criticalMultiplier: z.number().positive().default(2.0),
    }),
});

export type AccountPolicy = z.infer<typeof AccountPolicySchema>;

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
    role: z.enum(['accumulate', 'avoid', 'watchlist', 'trim', 'initiate', 'exit']),
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
