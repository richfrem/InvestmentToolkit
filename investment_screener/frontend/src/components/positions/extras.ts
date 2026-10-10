/**
 * extras.ts - The per-ticker facts the table shows that are not in the position row.
 *
 * Purpose:
 *     A position row (database read model) has shares, weights, targets and the stance. The live
 *     price, sector, % price changes and earnings date come from the portfolio-heatmap stock
 *     row; growth, rule of 40, bear/base/bull and the model come from the saved projection.
 *     buildExtras merges those two sources into one flat record with null for anything
 *     unknown (never a made-up 0), so every column reads the same fields on every screen.
 *
 * Layer: Frontend / Components / Positions
 *
 * Usage Examples:
 *     const extras = buildExtras(heatmapByTicker[t], latestProjectionByTicker(projections)[t]);
 *
 * Key Functions (Index):
 *     - latestProjectionByTicker(): newest saved projection per ticker
 *     - buildExtras(): one flat PositionExtras from a heatmap stock and a projection
 *
 * Key Input Dependencies:
 *     - POST /api/portfolio-heatmap stock rows; GET /api/projections
 *     - utils/heatmapPrice (price must be positive to count)
 *
 * Key Output Dependencies:
 *     - columns.ts, PortfolioPage
 */
import { heatmapPrice } from '../../utils/heatmapPrice';

export interface HeatmapStock {
    symbol: string;
    price?: number;
    sector?: string | null;
    industry?: string | null;
    analyst_target_mean?: number | null;
    change_1d?: number | null;
    change_1w?: number | null;
    change_1m?: number | null;
    change_3m?: number | null;
    change_ytd?: number | null;
    change_1y?: number | null;
    change_overall?: number | null;
    earnings_date?: string | null;
    days_to_earnings?: number | null;
}

interface ScenarioLite {
    growthRate?: number;
    netMargin?: number;
    qualityMultiplier?: number;
    scenarioPrice?: number;
}

export interface ProjectionLite {
    ticker: string;
    savedAt: string;
    aiThesis?: { model?: string; fairValue?: number } | null;
    scenarios?: { base?: ScenarioLite; bear?: ScenarioLite; bull?: ScenarioLite } | null;
}

export interface PositionExtras {
    livePrice: number | null;
    sector: string | null;
    industry: string | null;
    analystTarget: number | null;
    change_1d: number | null;
    change_1w: number | null;
    change_1m: number | null;
    change_3m: number | null;
    change_ytd: number | null;
    change_1y: number | null;
    change_overall: number | null;
    earningsDate: string | null;
    daysToEarnings: number | null;
    growth: number | null;
    ruleOf40: number | null;
    bear: number | null;
    base: number | null;
    bull: number | null;
    model: string | null;
    qualityMultiplier: number | null;
    lastAnalyzed: string | null;
}

const num = (v: unknown): number | null => (typeof v === 'number' && Number.isFinite(v) ? v : null);
const text = (v: unknown): string | null => (typeof v === 'string' && v.length > 0 ? v : null);

/** The newest saved projection per ticker; projections without a thesis are skipped. */
export function latestProjectionByTicker(projections: ProjectionLite[]): Record<string, ProjectionLite> {
    const out: Record<string, ProjectionLite> = {};
    for (const p of projections) {
        if (!p?.ticker || !p.aiThesis) continue;
        const current = out[p.ticker];
        if (!current || new Date(p.savedAt) > new Date(current.savedAt)) out[p.ticker] = p;
    }
    return out;
}

/** One flat record from a heatmap stock and a saved projection; null where a source is silent. */
export function buildExtras(heatmap?: HeatmapStock | null, projection?: ProjectionLite | null): PositionExtras {
    const base = projection?.scenarios?.base;
    const growth = num(base?.growthRate);
    const margin = num(base?.netMargin);
    return {
        livePrice: heatmapPrice(heatmap),
        sector: text(heatmap?.sector),
        industry: text(heatmap?.industry),
        analystTarget: num(heatmap?.analyst_target_mean),
        change_1d: num(heatmap?.change_1d),
        change_1w: num(heatmap?.change_1w),
        change_1m: num(heatmap?.change_1m),
        change_3m: num(heatmap?.change_3m),
        change_ytd: num(heatmap?.change_ytd),
        change_1y: num(heatmap?.change_1y),
        change_overall: num(heatmap?.change_overall),
        earningsDate: text(heatmap?.earnings_date),
        daysToEarnings: num(heatmap?.days_to_earnings),
        growth,
        ruleOf40: growth != null && margin != null ? growth + margin : null,
        bear: num(projection?.scenarios?.bear?.scenarioPrice),
        base: num(base?.scenarioPrice),
        bull: num(projection?.scenarios?.bull?.scenarioPrice),
        model: text(projection?.aiThesis?.model),
        qualityMultiplier: num(base?.qualityMultiplier),
        lastAnalyzed: text(projection?.savedAt),
    };
}
