/**
 * Purpose: explain why a saved valuation rate was chosen, wherever that rate is shown.
 * Layer: Frontend / UI. Usage: <SavedRateRationale rate={savedValuationRate(projection)} />.
 * Key Functions: SavedRateRationale — saved formula and written reason, or nothing when unaudited.
 * Key Input Dependencies: savedValuationRate presentation of the persisted rate audit.
 */
import type { savedValuationRate } from '../utils/valuationPresentation';

/** Render saved audit text only; an unaudited rate gets no invented explanation. */
export function SavedRateRationale({ rate }: { rate: ReturnType<typeof savedValuationRate> }) {
    if (!rate.formula && !rate.rationale) return null;
    return (
        <div role="group" aria-label="Why this rate" className="mt-3 pt-3 border-t border-slate-800 text-xs text-slate-400 space-y-1 text-left">
            <div className="font-semibold uppercase tracking-wider text-slate-500">Why this rate</div>
            {rate.formula && <div className="font-mono text-indigo-200">{rate.formula}</div>}
            {rate.rationale && <p className="leading-relaxed">{rate.rationale}</p>}
        </div>
    );
}
