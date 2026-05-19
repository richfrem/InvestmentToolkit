/**
 * valuationMath.ts
 * =====================================
 * Canonical DCF calculation engine for the frontend.
 * MIRRORS investment_screener/backend/py_services/dcf_scenarios.py exactly.
 */

export interface ScenarioParams {
    weight: number;
    growthRate: number;
    netMargin: number;
    exitPE: number;
    qualityMultiplier: number;
    shareChange: number;
    optionalityAdjustment?: number;
}

export interface ComputedScenario extends ScenarioParams {
    year5Revenue: number;
    year5NetIncome: number;
    year5Shares: number;
    year5EPS: number;
    year5PriceUndiscounted: number;
    presentValue: number;
}

/**
 * Computes a 5-year DCF scenario.
 * logic mirrored from dcf_scenarios.py
 */
export function computeScenario(
    baseRevenue: number,
    baseShares: number,
    discountRate: number,
    horizon: number,
    params: ScenarioParams
): ComputedScenario {
    const growth = params.growthRate / 100.0;
    const margin = params.netMargin / 100.0;
    const sc = params.shareChange / 100.0;
    const pe = params.exitPE;
    const qm = params.qualityMultiplier;
    const optionality = params.optionalityAdjustment || 0;

    const divisor = Math.pow(1 + discountRate, horizon);

    // logic mirrored from dcf_scenarios.py: calculate all, then round for output
    const y5Revenue = baseRevenue * Math.pow(1 + growth, horizon);
    const y5NetIncome = y5Revenue * margin;
    const y5Shares = baseShares * Math.pow(1 + sc, horizon);
    
    const rawEPS = y5Shares > 0 ? y5NetIncome / y5Shares : 0;
    
    // logic mirrored from dcf_scenarios.py: calculate all, then round for output
    // Note: optionalityAdjustment is an absolute dollar value ($ in dollars) 
    // for future projects (e.g. data centers) added to terminal value.
    const perShareOptionality = y5Shares > 0 ? optionality / y5Shares : 0;
    const rawPriceUndiscounted = (rawEPS * pe * qm) + perShareOptionality;
    const rawPresentValue = rawPriceUndiscounted / divisor;

    return {
        ...params,
        year5Revenue: Math.round((y5Revenue / 1_000_000) * 10) / 10,
        year5NetIncome: Math.round((y5NetIncome / 1_000_000) * 10) / 10,
        year5Shares: Math.round((y5Shares / 1_000_000) * 10) / 10,
        year5EPS: Math.round(rawEPS * 100) / 100,
        year5PriceUndiscounted: Math.round(rawPriceUndiscounted * 100) / 100,
        presentValue: Math.round(rawPresentValue * 100) / 100,
    };
}
