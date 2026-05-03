import { geminiService } from './GeminiService';
import { analysisContextBuilder } from './AnalysisContextBuilder';
import { projectionService } from './ProjectionService';

interface ValuationResult {
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

/**
 * Tool A: The "Hybrid" Analyst.
 * Orchestrates the Valuation Logic using Gemini 3.0 Pro.
 */
export class ValuationService {

    /**
     * Conducts a valuation analysis for a given ticker.
     * @param ticker The stock symbol (e.g., NVDA).
     * @param userMessage Optional override from the user (e.g., "Assume 5% growth").
     */
    async analyzeStock(ticker: string, userMessage?: string): Promise<ValuationResult> {

        // 0. Step 0: Freshness Check (30-day skip logic)
        // This ensures we don't burn tokens if a deep analysis was recently done (e.g. via CLI agent)
        console.log(`[ValuationService] Checking freshness for ${ticker}...`);
        const existingProjections = await projectionService.getProjections(ticker);
        const latestAI = existingProjections
            .filter(p => p.source === 'AI_AGENT')
            .sort((a, b) => new Date(b.savedAt).getTime() - new Date(a.savedAt).getTime())[0];

        if (latestAI && latestAI.aiThesis) {
            const savedDate = new Date(latestAI.savedAt);
            const now = new Date();
            const ageInDays = (now.getTime() - savedDate.getTime()) / (1000 * 60 * 60 * 24);

            if (ageInDays < 30) {
                console.log(`[ValuationService] CACHED — Analysis for ${ticker} is only ${Math.floor(ageInDays)}d old. Skipping Gemini call.`);
                const thesis = latestAI.aiThesis;
                const base = latestAI.scenarios.base;
                return {
                    fair_value: thesis.fairValue,
                    growth_assumption: base.growthRate / 100,
                    suggested_growth: base.growthRate / 100,
                    suggested_margin: base.netMargin / 100,
                    exit_pe: base.exitPE,
                    quality_multiplier: base.qualityMultiplier,
                    rationale: latestAI.rationale || thesis.rationale,
                    action: thesis.action as any,
                    model_name: `CACHED: ${thesis.model} (${Math.floor(ageInDays)}d ago)`
                };
            }
        }

        // 1. Get Live Data
        const context = await analysisContextBuilder.buildStockContext(ticker);

        // 2. Build the System Prompt
        const prompt = this.buildPrompt(context, userMessage);

        // 3. Call Gemini
        console.log(`[ValuationService] Asking Gemini about ${ticker}...`);
        const llmResponse = await geminiService.generateContent(prompt);

        // 4. Parse JSON
        const result = parseResponse(llmResponse);

        // 5. Inject Model Name
        result.model_name = geminiService.getModelName();

        return result;
    }

    private buildPrompt(context: any, userMessage?: string): string {
        const metrics = JSON.stringify(context.metrics, null, 2);

        return `
        SYSTEM: You are an elite equities analyst using the active investment thesis framework.
        Your goal is to determine a FAIR VALUE for ${context.ticker}.
        
        DATA CONTEXT:
        Current Price: $${context.price}
        Metrics: ${metrics}
        
        USER INPUT: "${userMessage || 'Provide base case analysis based on current metrics.'}"
        
        INSTRUCTIONS:
        1. Analyze the Revenue Growth, Rule of 40 score, and PE ratio.
        2. Determine a "Quality Multiplier" (0.5x to 2.0x) based on moat, market dominance, and Rule of 40. NVDA typically gets 1.5x.
        3. Determine suggested Growth Rate and Net Margin for the next 5 years.
        4. Calculate Fair Value = (Revenue * Suggested Margin * Exit PE * Quality Multiplier) / Shares (Discounted to PV).
        5. Return ONLY valid JSON in this format:
        {
            "fair_value": <number>,
            "growth_assumption": <number_as_decimal>,
            "suggested_growth": <number_as_decimal>,
            "suggested_margin": <number_as_decimal>,
            "exit_pe": <number>,
            "quality_multiplier": <number_between_0.5_and_2.0>,
            "rationale": "<concise_explanation_max_50_words>",
            "action": "BUY" | "SELL" | "HOLD"
        }
        NO markdown, NO explanations outside the JSON.
        `;
    }
}

function parseResponse(text: string): ValuationResult {
    try {
        // Clean markdown code blocks if present
        const cleanText = text.replace(/```json/g, '').replace(/```/g, '').trim();
        return JSON.parse(cleanText);
    } catch (error) {
        console.error("[ValuationService] Failed to parse LLM response:", text);
        throw new Error("Invalid format from AI Analyst.");
    }
}

export const valuationService = new ValuationService();
