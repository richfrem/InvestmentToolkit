/**
 * recommendationPresentation.ts
 *
 * Purpose:
 *     Pure presentation mapping for Daily Brief recommendation cards —
 *     translates the engine's recommendation strings (brief_recommendations.py)
 *     into trade-button intents and chip styling. Keeps DailyBriefPage purely
 *     presentational.
 *
 * Layer: Frontend / Utils
 */

export interface TradeIntent {
    side: 'buy' | 'sell';
    rating: 'BUY' | 'SELL';
}

/**
 * Map a recommendation kind to its trade-button intent.
 * HOLD / QUEUED (and anything unknown) render no button.
 */
export function tradeIntent(recommendation: string): TradeIntent | null {
    switch (recommendation) {
        case 'SELL':
        case 'TRIM':
            return { side: 'sell', rating: 'SELL' };
        case 'BUY':
        case 'BUY_LIMIT':
            return { side: 'buy', rating: 'BUY' };
        default:
            return null;
    }
}

/** Chip styling per recommendation kind (Luxury Dark Mode palette). */
export const REC_CHIP_STYLES: Record<string, { bg: string; text: string; border: string }> = {
    SELL:      { bg: 'bg-red-500/10',     text: 'text-red-400',     border: 'border-red-500/30' },
    TRIM:      { bg: 'bg-orange-500/10',  text: 'text-orange-400',  border: 'border-orange-500/30' },
    BUY:       { bg: 'bg-emerald-500/10', text: 'text-emerald-400', border: 'border-emerald-500/30' },
    BUY_LIMIT: { bg: 'bg-emerald-500/10', text: 'text-emerald-400', border: 'border-emerald-500/30' },
    HOLD:      { bg: 'bg-sky-500/10',     text: 'text-sky-400',     border: 'border-sky-500/30' },
    QUEUED:    { bg: 'bg-zinc-500/10',    text: 'text-zinc-400',    border: 'border-zinc-500/30' },
};
