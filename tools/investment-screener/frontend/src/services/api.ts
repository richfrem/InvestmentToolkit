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
