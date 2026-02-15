import { GoogleGenerativeAI } from "@google/generative-ai";

/**
 * Service to interact with Google's Gemini Models.
 * Centralizes API key management and model configuration.
 */
class GeminiService {
    private genAI: GoogleGenerativeAI | null = null;
    private model: any | null = null;

    constructor() {
        // Constructor is now empty, initialization is lazy
    }

    public getModelName(): string {
        return process.env.INVESTMENT_TOOLKIT_GEMINI_MODEL || "NOT_SET";
    }

    private getModel() {
        if (!this.model) {
            const apiKey = process.env.INVESTMENT_TOOLKIT_GEMINI_API_KEY;
            const modelName = process.env.INVESTMENT_TOOLKIT_GEMINI_MODEL;

            console.log(`[GeminiService] Initializing... Model: ${modelName || "NOT SET"}`);

            if (!apiKey) {
                throw new Error("INVESTMENT_TOOLKIT_GEMINI_API_KEY is not set in environment.");
            }
            if (!modelName) {
                throw new Error("INVESTMENT_TOOLKIT_GEMINI_MODEL is not set in environment.");
            }

            this.genAI = new GoogleGenerativeAI(apiKey);
            this.model = this.genAI.getGenerativeModel({ model: modelName });
        }
        return this.model;
    }

    /**
     * Generates content from a text prompt.
     * @param prompt The prompt string (system instructions + user input)
     * @returns The generated text response
     */
    async generateContent(prompt: string): Promise<string> {
        try {
            const model = this.getModel();
            const result = await model.generateContent(prompt);
            const response = await result.response;
            return response.text();
        } catch (error: any) {
            console.error("[GeminiService] Error generating content:", error);
            throw new Error(`Gemini API Error: ${error.message}`);
        }
    }
}

export const geminiService = new GeminiService();
