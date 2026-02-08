export interface FinancialData {
    // Historical Arrays (New)
    historical_revenue: number[];
    historical_net_income: number[];
    historical_fcf: number[]; // Free Cash Flow
    historical_gross_margin: number[];
    historical_operating_margin: number[];
    historical_net_margin: number[];
    historical_eps: number[];

    // Analyst Estimates (New)
    analyst_revenue_forecast: {
        year: number;
        high: number;
        low: number;
        avg: number;
    }[];
    analyst_earnings_forecast: {
        year: number;
        high: number;
        low: number;
        avg: number;
    }[];
}

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
    financials: FinancialData;
}
