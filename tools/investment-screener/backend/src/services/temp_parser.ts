function parseResponse(text: string): ValuationResult {
    try {
        console.log("[ValuationService] Raw LLM Response:", text);
        // Clean markdown code blocks if present
        const cleanText = text.replace(/```json/g, '').replace(/```/g, '').trim();
        return JSON.parse(cleanText);
    } catch (error) {
        console.error("[ValuationService] Failed to parse LLM response:", text);
        throw new Error("Invalid format from AI Analyst.");
    }
}
