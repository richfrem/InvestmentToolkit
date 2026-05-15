/**
 * api.ts (TypeScript Service)
 * =====================================
 *
 * Purpose:
 *     Central API client for interacting with the Node.js backend. Handles data fetching for stocks, portfolio summaries,
 *     Questrade synchronization, and DCF projections.
 *
 * Layer: Frontend / Services / API
 *
 * Usage Examples:
 *     import { fetchStockData } from './services/api';
 *     const data = await fetchStockData('AAPL');
 *
 * Key Functions:
 *     - fetchStockData() - Retrieves comprehensive financial and profile data for a specific ticker
 *     - fetchPortfolioSummary() - Fetches account-level valuation metrics (USD/CAD) and YTD performance
 *     - saveProjection() - Persists a versioned DCF projection object to the backend
 *     - syncQuestrade() - Triggers the background brokerage sync process via the QuestradeDataEngine
 */
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

// --- Portfolio Summary ---

export interface PortfolioSummary {
    positionCount: number;
    totalMarketValueUSD: number;
    totalMarketValueCAD: number;
    totalBookValueUSD: number;
    totalBookValueCAD: number;
    ytdStartValueCAD: number;
    ytdStartValueUSD: number;
    ytdChangeCAD: number;
    ytdChangePctCAD: number;
    ytdChangeUSD: number;
    ytdChangePctUSD: number;
    unrealizedGainUSD: number;
    unrealizedGainPctUSD: number;
    unrealizedGainCAD: number;
    unrealizedGainPctCAD: number;
    liveUsdCadRate: number;
    jan1UsdCadRate: number;
    lastUpdated: string;
    price_source?: string;
}

export const fetchPortfolioSummary = async (): Promise<PortfolioSummary> => {
    const response = await fetch('/api/portfolio/summary');
    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || 'Failed to fetch portfolio summary');
    }
    return await response.json();
};

// --- Portfolio Period Performance ---

export interface PeriodPerformance {
    change: number;
    changePct: number;
    historicalValue: number;
    currentValue: number;
}

export interface PortfolioPerformance {
    '1d': PeriodPerformance | null;
    '1w': PeriodPerformance | null;
    '1m': PeriodPerformance | null;
}

export const fetchPortfolioPerformance = async (): Promise<PortfolioPerformance> => {
    const response = await fetch('/api/portfolio/performance');
    if (!response.ok) throw new Error('Failed to fetch portfolio performance');
    return await response.json();
};

// --- Strategy Allocation ---

export interface StrategyHolding {
    symbol: string;
    name: string;
    sector: string;
    subStrategyId: string | null;
    shares: number;
    price: number;
    valueUSD: number;
    pct: number;
}

export interface StrategyAllocationItem {
    id: string;
    name: string;
    valueUSD: number;
    pct: number;
    holdings: StrategyHolding[];
}

export interface StrategyAllocation {
    allocation: StrategyAllocationItem[];
    totalUSD: number;
}

export const fetchStrategyAllocation = async (): Promise<StrategyAllocation> => {
    const response = await fetch('/api/portfolio/strategy-allocation');
    if (!response.ok) throw new Error('Failed to fetch strategy allocation');
    return await response.json();
};

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

// Auto-pick source: TradingView CDP (primary) → Questrade → cache
export const syncPortfolio = async (): Promise<{ success: boolean; dataSource: string; message: string }> => {
    const response = await fetch('/api/portfolio/sync', {
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
    moatScore?: number; // 0-5
    managementScore?: number; // 0-5
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
    isDefault?: boolean; // If true, this loads automatically
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
        action: 'BUY' | 'HOLD' | 'SELL' | 'INITIATE' | 'ACCUMULATE' | 'MAINTAIN' | 'TRIM' | 'EXIT' | 'WATCHLIST';
        analyzedAt: string;
        researchReport?: string;
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

export const fetchAllProjections = async (): Promise<Projection[]> => {
    const response = await fetch('/api/projections');
    if (!response.ok) {
        throw new Error('Failed to fetch projections');
    }
    return await response.json();
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

// ─── Docs API ─────────────────────────────────────────────────────────────────

export const fetchInvestmentThesis = async (): Promise<{ content: string; filename: string; thesisName: string; thesisDescription: string }> => {
    const res = await fetch('/api/docs/investment-thesis');
    if (!res.ok) throw new Error('Failed to load investment thesis');
    return res.json();
};

export const fetchLatestReviewData = async (): Promise<any> => {
    const res = await fetch('/api/docs/latest-review-data');
    if (!res.ok) throw new Error('Failed to load review data');
    return res.json();
};

// ─── Portfolio Health API ──────────────────────────────────────────────────────

export interface HoldingWeight {
    ticker: string;
    actualPct: number;
    targetPct: number;
}

export const fetchPortfolioWeights = async (): Promise<Record<string, HoldingWeight>> => {
    try {
        const res = await fetch('/api/theses/target-portfolio/health');
        if (!res.ok) return {};
        const data = await res.json();
        const map: Record<string, HoldingWeight> = {};
        for (const h of data.holdingHealth ?? []) {
            map[h.ticker] = { ticker: h.ticker, actualPct: h.actualPct ?? 0, targetPct: h.targetPct ?? 0 };
        }
        return map;
    } catch { return {}; }
};

export const fetchAgentGuide = async (): Promise<{ content: string; filename: string }> => {
    const res = await fetch('/api/docs/agent-guide');
    if (!res.ok) throw new Error('Failed to load agent guide');
    return res.json();
};
