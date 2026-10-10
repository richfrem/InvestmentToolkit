/**
 * positionMath.ts - Pure helpers for the shared positions table: row type, formatting, scope
 * filtering, sorting and totals.
 *
 * Purpose:
 *     Everything about a position row that does not need React: the row shape served by
 *     GET /api/screener/all-holdings, weight and gap formatting (a dash for unknown, never a
 *     made-up 0), the per-thesis row filter, a sort that keeps unknown values last, and the
 *     totals row. Kept pure so it is covered by plain unit tests.
 *
 * Layer: Frontend / Components / Positions
 *
 * Usage Examples:
 *     rowsForDocument(rows, 'asi_race', 'held')   // the held stocks one thesis document lists
 *     totalsFor(rows)                              // { actualPct, targetPct, gapPct, heldCount }
 *
 * Key Functions (Index):
 *     - formatWeight(), formatGap(): display text for weights and the weight gap
 *     - moneyText(): dollar text that honours privacy mode, a dash when unknown
 *     - rowsForDocument(): the rows a thesis document lists, optionally only held ones
 *     - totalsFor(): summed weights, gap and number of positions
 *     - sortRows(): stable sort by an accessor, unknown values last in both directions
 *
 * Key Input Dependencies:
 *     - PositionRow mirrors backend/src/services/positionRows.ts
 *
 * Key Output Dependencies:
 *     - PositionsTable, ThesisPositions
 */

export interface PositionRow {
    ticker: string;
    name: string;
    assetClass: string;
    pillarId: string;
    subStrategyId: string;
    role: string;
    held: boolean;
    shares: number;
    averageCost: number | null;
    bookValue: number | null;
    marketValue: number | null;
    currentPrice: number | null;
    /** 0 when not held; null only when held and the weight is not known. */
    actualPct: number | null;
    targetPct: number | null;
    gapPct: number | null;
    action: string | null;
    rationale: string | null;
    hasValuation: boolean;
    isWatched: boolean;
    documents: string[];
}

export type DocumentScope = 'held' | 'all';

export interface PositionTotals {
    actualPct: number;
    targetPct: number;
    gapPct: number;
    heldCount: number;
}

/** A weight as text with one decimal; a dash when unknown (null is not 0). */
export function formatWeight(value: number | null | undefined): string {
    return value == null ? '—' : `${value.toFixed(1)}%`;
}

/** Dollar text via ``format``, masked in privacy mode, a dash when the value is unknown. */
export function moneyText(value: number | null | undefined, hidden: boolean, format: (v: number) => string): string {
    if (value == null) return '—';
    return hidden ? '$••••' : format(value);
}

/** The actual-minus-target gap in percentage points, signed (plain 0.0pp when it rounds to zero); a dash when unknown. */
export function formatGap(value: number | null | undefined): string {
    if (value == null) return '—';
    const text = Math.abs(value).toFixed(1);
    if (text === '0.0') return '0.0pp';
    return `${value > 0 ? '+' : '-'}${text}pp`;
}

/** The rows a thesis document lists; with scope 'held', only the stocks currently owned. */
export function rowsForDocument(rows: PositionRow[], documentId: string, scope: DocumentScope): PositionRow[] {
    return rows.filter(r => r.documents.includes(documentId) && (scope === 'all' || r.held));
}

/** Summed actual and target weight (unknown weights skipped), their gap, and the position count. */
export function totalsFor(rows: PositionRow[]): PositionTotals {
    const actualPct = rows.reduce((s, r) => s + (r.actualPct ?? 0), 0);
    const targetPct = rows.reduce((s, r) => s + (r.targetPct ?? 0), 0);
    return { actualPct, targetPct, gapPct: actualPct - targetPct, heldCount: rows.filter(r => r.held).length };
}

/** A copy of ``rows`` ordered by ``get``; null and undefined always sort last. */
export function sortRows<T>(rows: T[], get: (row: T) => number | string | null | undefined, dir: 'asc' | 'desc'): T[] {
    const sign = dir === 'asc' ? 1 : -1;
    return [...rows].sort((a, b) => {
        const x = get(a), y = get(b);
        if (x == null && y == null) return 0;
        if (x == null) return 1;
        if (y == null) return -1;
        if (typeof x === 'number' && typeof y === 'number') return (x - y) * sign;
        return String(x).localeCompare(String(y), undefined, { sensitivity: 'base' }) * sign;
    });
}
