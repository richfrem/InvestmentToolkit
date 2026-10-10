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
 *     - formatWeight(), formatGap(), weightHeat(): display text and cell shading for weights and the gap
 *     - moneyText(): dollar text that honours privacy mode, a dash when unknown
 *     - normalizePositionRows(): rows from the API with every field present (older backends omit some)
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
    marketValue: number;
    bookValue: number;
    heldCount: number;
}

/** A weight as text with two decimals (small positions matter); a dash when unknown (null is not 0). */
export function formatWeight(value: number | null | undefined): string {
    return value == null ? '—' : `${value.toFixed(2)}%`;
}

/** Cell background for a weight: emerald for actual, indigo for target; none for 0 or unknown. */
export function weightHeat(pct: number | null | undefined, kind: 'actual' | 'target'): string | undefined {
    if (!pct || pct <= 0) return undefined;
    const intensity = Math.min(pct / 12, 1);
    return kind === 'actual' ? `rgba(16, 185, 129, ${intensity * 0.32})` : `rgba(99, 102, 241, ${intensity * 0.32})`;
}

/** Dollar text via ``format``, masked in privacy mode, a dash when the value is unknown. */
export function moneyText(value: number | null | undefined, hidden: boolean, format: (v: number) => string): string {
    if (value == null) return '—';
    return hidden ? '$••••' : format(value);
}

/** The actual-minus-target gap in percentage points, signed (plain 0.00pp when it rounds to zero); a dash when unknown. */
export function formatGap(value: number | null | undefined): string {
    if (value == null) return '—';
    const text = Math.abs(value).toFixed(2);
    if (text === '0.00') return '0.00pp';
    return `${value > 0 ? '+' : '-'}${text}pp`;
}

const asNumber = (v: unknown): number | null => (typeof v === 'number' && Number.isFinite(v) ? v : null);
const asText = (v: unknown, fallback: string): string => (typeof v === 'string' ? v : fallback);

/**
 * Rows from GET /api/screener/all-holdings with every field present. A backend that has not been
 * restarted since an upgrade omits newer fields (documents, shares, held ...); filling them here
 * keeps one stale field from crashing a whole screen. Entries without a ticker are dropped and a
 * non-list gives no rows.
 */
export function normalizePositionRows(raw: unknown): PositionRow[] {
    if (!Array.isArray(raw)) return [];
    const rows: PositionRow[] = [];
    for (const item of raw) {
        if (!item || typeof item !== 'object') continue;
        const r = item as Record<string, unknown>;
        if (typeof r.ticker !== 'string' || !r.ticker) continue;
        const shares = asNumber(r.shares) ?? 0;
        rows.push({
            ticker: r.ticker,
            name: asText(r.name, r.ticker),
            assetClass: asText(r.assetClass, 'EQUITY'),
            pillarId: asText(r.pillarId, 'other'),
            subStrategyId: asText(r.subStrategyId, 'other'),
            role: asText(r.role, 'watchlist'),
            held: typeof r.held === 'boolean' ? r.held : shares > 0,
            shares,
            averageCost: asNumber(r.averageCost),
            bookValue: asNumber(r.bookValue),
            marketValue: asNumber(r.marketValue),
            currentPrice: asNumber(r.currentPrice),
            actualPct: asNumber(r.actualPct),
            targetPct: asNumber(r.targetPct),
            gapPct: asNumber(r.gapPct),
            action: typeof r.action === 'string' ? r.action : null,
            rationale: typeof r.rationale === 'string' ? r.rationale : null,
            hasValuation: r.hasValuation === true,
            isWatched: r.isWatched === true,
            documents: Array.isArray(r.documents) ? r.documents.filter((d): d is string => typeof d === 'string') : [],
        });
    }
    return rows;
}

/** The rows a thesis document lists; with scope 'held', only the stocks currently owned. */
export function rowsForDocument(rows: PositionRow[], documentId: string, scope: DocumentScope): PositionRow[] {
    return rows.filter(r => (r.documents ?? []).includes(documentId) && (scope === 'all' || r.held));
}

/** Summed weights (unknown skipped), their gap, summed market and book value, and the position count. */
export function totalsFor(rows: PositionRow[]): PositionTotals {
    const actualPct = rows.reduce((s, r) => s + (r.actualPct ?? 0), 0);
    const targetPct = rows.reduce((s, r) => s + (r.targetPct ?? 0), 0);
    const marketValue = rows.reduce((s, r) => s + (r.marketValue ?? 0), 0);
    const bookValue = rows.reduce((s, r) => s + (r.bookValue ?? 0), 0);
    return { actualPct, targetPct, gapPct: actualPct - targetPct, marketValue, bookValue, heldCount: rows.filter(r => r.held).length };
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
