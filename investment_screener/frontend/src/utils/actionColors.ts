// Canonical action badge colors for the full portfolio action vocabulary.
// Used by ScreenerTable, AIAnalysisModal, LatestReviewModal, and any future consumers.

export type PortfolioAction = 'INITIATE' | 'ACCUMULATE' | 'MAINTAIN' | 'TRIM' | 'EXIT' | 'WATCHLIST' | 'HOLD' | 'REVIEW';

// Full combined class string (text + border + bg) — use for pills/badges
const ACTION_BADGE: Record<string, string> = {
    INITIATE:   'text-cyan-400 border-cyan-500/40 bg-cyan-500/10',
    ACCUMULATE: 'text-green-400 border-green-500/40 bg-green-500/10',
    MAINTAIN:   'text-slate-300 border-slate-500/40 bg-slate-500/10',
    HOLD:       'text-slate-300 border-slate-500/40 bg-slate-500/10',
    TRIM:       'text-amber-400 border-amber-500/40 bg-amber-500/10',
    EXIT:       'text-red-400 border-red-500/40 bg-red-500/10',
    WATCHLIST:  'text-purple-400 border-purple-500/40 bg-purple-500/10',
    REVIEW:     'text-yellow-400 border-yellow-500/40 bg-yellow-500/10',
};

// Text-only color — use for inline labels, small tags
const ACTION_TEXT: Record<string, string> = {
    INITIATE:   'text-cyan-400',
    ACCUMULATE: 'text-green-400',
    MAINTAIN:   'text-slate-300',
    HOLD:       'text-slate-300',
    TRIM:       'text-amber-400',
    EXIT:       'text-red-400',
    WATCHLIST:  'text-purple-400',
    REVIEW:     'text-yellow-400',
};

const FALLBACK_BADGE = 'text-slate-400 border-slate-600/40 bg-transparent';
const FALLBACK_TEXT  = 'text-slate-400';

export function getActionBadgeClass(action: string): string {
    return ACTION_BADGE[action?.toUpperCase()] ?? FALLBACK_BADGE;
}

export function getActionTextClass(action: string): string {
    return ACTION_TEXT[action?.toUpperCase()] ?? FALLBACK_TEXT;
}
