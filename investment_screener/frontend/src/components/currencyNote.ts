/**
 * currencyNote.ts - Wording for the "current developments" note on a thesis page.
 *
 * Purpose:
 *     The daily, weekly and review skills keep one short note per thesis document current
 *     (thesis_document_currency). This holds the pure wording for how old that note is, so the
 *     panel and its tests share one rule.
 *
 * Layer: Frontend / Components
 *
 * Usage Examples:
 *     currencyAgeLabel(5)   // "5 days ago"
 *
 * Key Functions (Index):
 *     - CurrencyNote: the note as the thesis route returns it
 *     - currencyAgeLabel(): "today", "yesterday" or "N days ago"
 *
 * Key Input Dependencies:
 *     - GET /api/theses/sub-strategies/:id (currency)
 *
 * Key Output Dependencies:
 *     - ThesisCurrency panel, ThesisViewModal
 */

export interface CurrencyNote {
    asOf: string;
    markdown: string;
    updatedAt: string;
    updatedBy: string | null;
    ageDays: number;
    stale: boolean;
}

/** How old the note is in words; a negative age reads as today. */
export function currencyAgeLabel(ageDays: number): string {
    if (ageDays <= 0) return 'today';
    if (ageDays === 1) return 'yesterday';
    return `${ageDays} days ago`;
}
