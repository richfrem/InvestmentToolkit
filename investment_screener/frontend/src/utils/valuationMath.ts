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

    const y5Revenue = baseRevenue * Math.pow(1 + growth, horizon);
    const y5NetIncome = y5Revenue * margin;
    const y5Shares = baseShares * Math.pow(1 + sc, horizon);
    
    // dcf_scenarios.py logic:
    // y5_eps = y5_net_income / y5_shares if y5_shares > 0 else 0.0
    // y5_eps = round(y5_eps, 2)
    const rawEPS = y5Shares > 0 ? y5NetIncome / y5Shares : 0;
    const y5EPS = Math.round(rawEPS * 100) / 100;
    
    // y5_price_undiscounted = y5_eps * pe * qm
    // y5_price_undiscounted = round(y5_price_undiscounted, 2)
    const y5PriceUndiscounted = Math.round((y5EPS * pe * qm + optionality) * 100) / 100;
    
    // present_value = y5_price_undiscounted / divisor
    // present_value = round(present_value, 2)
    const presentValue = Math.round((y5PriceUndiscounted / divisor) * 100) / 100;

    return {
        ...params,
        year5Revenue: Math.round((y5Revenue / 1_000_000) * 10) / 10,
        year5NetIncome: Math.round((y5NetIncome / 1_000_000) * 10) / 10,
        year5Shares: Math.round((y5Shares / 1_000_000) * 10) / 10,
        year5EPS: y5EPS,
        year5PriceUndiscounted: y5PriceUndiscounted,
        presentValue: presentValue,
    };
}
