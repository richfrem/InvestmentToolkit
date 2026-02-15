import { spawnPythonScript } from './bridge';

interface StockContext {
    ticker: string;
    metrics: any;
    price: number;
    timestamp: string;
}

/**
 * Builds the context required for AI Analysis prompts.
 * Aggregates data from Python scripts (yfinance) and internal portfolio state.
 */
class AnalysisContextBuilder {

    /**
     * Fetches live financial data and valuation metrics from Python.
     * Used for Tool A (Valuation Assistant).
     */
    async buildStockContext(ticker: string): Promise<StockContext> {
        console.log(`[ContextBuilder] Fetching context for ${ticker}...`);

        try {
            // Re-use the existing bridge to call fetch_financials.py
            const data = await spawnPythonScript('fetch_financials.py', [ticker]);

            if (data.error) {
                throw new Error(data.error);
            }

            return {
                ticker: ticker,
                metrics: data, // Includes PE, RuleOf40, Revenue Growth, etc.
                price: data.price,
                timestamp: new Date().toISOString()
            };
        } catch (error: any) {
            console.error(`[ContextBuilder] Error building context for ${ticker}:`, error);
            throw error;
        }
    }

    /**
     * Placeholder for Tool B (Thesis Balancer).
     * Will aggregate portfolio + thesis targets later.
     */
    async buildPortfolioContext(): Promise<any> {
        return { message: "Not implemented yet (Tool B Scope)" };
    }
}

export const analysisContextBuilder = new AnalysisContextBuilder();
