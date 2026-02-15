export interface StockData {
    symbol: string;
    price: number;
    currency: string;
    profile: {
        sector: string;
        industry: string;
        description: string;
    };
    metrics: {
        pe_ratio: number;
        forward_pe: number;
        market_cap: number;
        beta: number;
        revenue: number;
        shares_outstanding: number;
        peg_ratio?: number;
        revenue_growth?: number;
        profit_margin?: number;
    };
    performance?: {
        "1d": number;
        "1w": number;
        "1m": number;
        "3m": number;
        "ytd": number;
        "1y": number;
        "5y": number;
    };
    expert_metrics: {
        rule_of_40: {
            score: number;
            revenue_growth: number;
            ebitda_margin: number;
            is_saas: boolean;
        };
        piotroski_f_score: {
            score: number;
            max: number;
            details: {
                roa_positive: boolean;
                cfo_positive: boolean;
                roa_improving: boolean;
                accruals_ok: boolean;
                leverage_decreasing: boolean;
                current_ratio_improving: boolean;
                no_dilution: boolean;
                gross_margin_improving: boolean;
                asset_turnover_improving: boolean;
            };
        };
    };
    financials: {
        historical_revenue: number[];
        historical_net_income: number[];
        historical_fcf: number[];
        historical_gross_margin: number[];
        historical_operating_margin: number[];
        historical_net_margin: number[];
        historical_eps: number[];
    };
    analyst_revenue_forecast?: Array<{
        year: number;
        avg: number;
        low: number;
        high: number;
        period: string;
    }>;
    analyst_earnings_forecast?: Array<{
        year: number;
        avg: number;
        low: number;
        high: number;
        period: string;
    }>;
    analyst_estimates?: {
        target_high_price: number;
        target_low_price: number;
        target_mean_price: number;
        target_median_price: number;
        recommendation: string;
        number_of_analysts: number;
        revenue_growth?: number;
        profit_margin?: number;
        forward_pe?: number;
    };
    growth_estimates?: {
        stockTrend: {
            "0q": number;
            "+1q": number;
            "0y": number;
            "+1y": number;
        };
    };
    quarterly_margin?: number;
    error?: string;
}

export const fetchStockData = async (ticker: string): Promise<StockData> => {
    try {
        const response = await fetch(`/api/stock/${ticker}`);
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `Error ${response.status}: ${response.statusText}`);
        }
        return await response.json();
    } catch (error) {
        console.error("API Fetch Error:", error);
        throw error;
    }
};

export const syncQuestrade = async (): Promise<{ success: boolean; message: string }> => {
    const response = await fetch('/api/portfolio/sync-questrade', {
        method: 'POST',
    });
    const data = await response.json();
    if (!response.ok) {
        throw new Error(data.details || data.error || 'Sync failed');
    }
    return data;
};

export const seedQuestradeToken = async (refreshToken: string): Promise<{ success: boolean; message: string }> => {
    const response = await fetch('/api/questrade/seed', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refreshToken }),
    });
    const data = await response.json();
    if (!response.ok) {
        throw new Error(data.error || 'Seeding failed');
    }
    return data;
};

export interface ValuationResult {
    fair_value: number;
    growth_assumption: number;
    rationale: string;
    action: "BUY" | "SELL" | "HOLD";
    model_name: string;
    suggested_growth?: number;
    suggested_margin?: number;
    exit_pe?: number;
    quality_multiplier?: number;
}

export const runAIAnalysis = async (ticker: string, userMessage?: string): Promise<ValuationResult> => {
    const response = await fetch('/api/analysis/valuation', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ticker, userMessage }),
    });
    const data = await response.json();
    if (!response.ok) {
        throw new Error(data.details || data.error || 'AI Analysis failed');
    }
    return data;
};

export const fetchSyncStatus = async (): Promise<{ lastSync: string | null }> => {
    const response = await fetch('/api/portfolio/status');
    if (!response.ok) {
        throw new Error('Failed to fetch sync status');
    }
    return await response.json();
};

// --- Valuation Persistence Interfaces & API ---

export interface Scenario {
    weight: number;
    growthRate: number; // 0-100+
    netMargin: number; // 0-100
    exitPE: number;
    qualityMultiplier: number;
    shareChange: number; // % change (negative = buyback)
    rationale?: string;
    scenarioPrice?: number;
    risks?: string[];
}

export interface Snapshot {
    price: number;
    currency: string;
    shares: number;
    revenue: number;
    lastActualPS: number;
    fiscalPeriod?: string;
    analystGrowthEstimate?: number;
    analystMarginEstimate?: number;
}

export interface Projection {
    ticker: string;
    id: string;
    source: 'USER' | 'SYSTEM' | 'AI_AGENT'; // Added for V2
    schemaVersion: '1.1';
    version: number;
    savedAt: string;
    updatedAt: string;
    name: string;
    rationale?: string;
    snapshot: Snapshot;
    dataPreferences: {
        growthBasis: 'ttm' | 'next' | 'current';
        marginBasis: 'ttm' | 'next' | 'quarterly';
    };
    scenarios: {
        bear: Scenario;
        base: Scenario;
        bull: Scenario;
    };
    aiThesis?: {
        model: string;
        rationale: string;
        fairValue: number;
        action: 'BUY' | 'HOLD' | 'SELL';
        analyzedAt: string;
    };
    globalSettings: {
        discountRate: number;
        timeHorizon: number;
    };
}

export const fetchProjections = async (ticker: string): Promise<Projection[] | null> => {
    try {
        const response = await fetch(`/api/projections/${ticker}`);
        if (!response.ok) {
            if (response.status === 404) return [];
            const errorData = await response.json().catch(() => ({}));
            console.warn("Fetch Projections Warning", errorData);
            // Red Team C1 Fix: Return null on error so caller knows it's a failure, not just empty.
            return null;
        }
        return await response.json();
    } catch (e) {
        console.error("Network error fetching projections", e);
        // Red Team C1 Fix: Return null on network error.
        return null;
    }
};

export const saveProjection = async (projection: Projection): Promise<{ success: boolean; message: string }> => {
    const response = await fetch('/api/projections', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(projection),
    });
    const data = await response.json();
    if (!response.ok) {
        throw new Error(data.error || 'Failed to save projection');
    }
    return data;
};

export const deleteProjection = async (ticker: string, id: string): Promise<{ success: boolean; message: string }> => {
    const response = await fetch(`/api/projections/${ticker}/${id}`, {
        method: 'DELETE',
    });
    const data = await response.json();
    if (!response.ok) {
        throw new Error(data.error || 'Failed to delete projection');
    }
    return data;
};
