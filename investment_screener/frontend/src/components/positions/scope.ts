/**
 * scope.ts - Which rows the portfolio table shows: scope, action chips, sector, strategy, text.
 *
 * Purpose:
 *     The one place that decides which position rows a filter state keeps and how many each chip
 *     counts. Scope is Holdings (funded or with a target weight), Watchlist or All; the action
 *     chips match on the one stance every page shows (stanceOf); gaps are funded or targeted
 *     tickers with no saved valuation. Pure, so it is covered by plain unit tests and the chips
 *     and the table can never disagree.
 *
 * Layer: Frontend / Components / Positions
 *
 * Usage Examples:
 *     const kept = filterRows(rows, state, recommendations, r => sectors[r.ticker]);
 *     const counts = countsFor(rows, recommendations);
 *
 * Key Functions (Index):
 *     - isCashRow(), isHoldingRow(): row classification
 *     - filterRows(): the rows a filter state keeps
 *     - countsFor(): the number each scope and action chip shows
 *     - sectorOptions(), strategyOptions(): values for the dropdowns
 *
 * Key Input Dependencies:
 *     - utils/riskReward (stanceOf, isReduceCandidate), positionMath (PositionRow)
 *
 * Key Output Dependencies:
 *     - the portfolio page toolbar and table
 */
import type { RecommendationRecord } from '../../services/api';
import { isReduceCandidate, stanceOf } from '../../utils/riskReward';
import type { PositionRow } from './positionMath';

export type Scope = 'holdings' | 'watchlist' | 'all';
export type StatusFilter = 'all' | 'actionable' | 'initiate' | 'accumulate' | 'trim' | 'exit' | 'reduce' | 'gaps';

export interface FilterState {
    scope: Scope;
    status: StatusFilter;
    /** A sector name, or 'all'. */
    sector: string;
    /** A sub-strategy id, or 'all'. */
    strategy: string;
    /** Case-insensitive substring filters keyed by column id. */
    text: Record<string, string>;
}

export interface Counts {
    all: number;
    actionable: number;
    initiate: number;
    accumulate: number;
    trim: number;
    exit: number;
    reduce: number;
    holdings: number;
    watchlist: number;
    gaps: number;
}

type Recs = Record<string, RecommendationRecord>;
type SectorOf = (row: PositionRow) => string | null | undefined;

const ACTIONABLE = ['INITIATE', 'ACCUMULATE', 'TRIM', 'EXIT', 'REVIEW', 'BUY', 'SELL'];

export const isCashRow = (row: PositionRow): boolean =>
    row.assetClass === 'CASH' || row.ticker.includes('CASH');

/** Funded, or with a target weight: what the Holdings scope shows (cash included). */
export const isHoldingRow = (row: PositionRow): boolean =>
    (row.actualPct ?? 0) > 0 || (row.targetPct ?? 0) > 0;

const stance = (row: PositionRow, recs: Recs): string =>
    (stanceOf(recs[row.ticker]) ?? row.action ?? '').toUpperCase();

const missingValuation = (row: PositionRow, recs: Recs): boolean =>
    !row.hasValuation || recs[row.ticker]?.fair_value == null;

function inScope(row: PositionRow, scope: Scope): boolean {
    if (scope === 'holdings') return isHoldingRow(row);
    if (scope === 'watchlist') return row.isWatched;
    return true;
}

function matchesStatus(row: PositionRow, status: StatusFilter, recs: Recs): boolean {
    if (status === 'all') return true;
    if (isCashRow(row)) return false;
    const act = stance(row, recs);
    switch (status) {
        case 'actionable': return ACTIONABLE.includes(act);
        case 'initiate': return act === 'INITIATE';
        case 'accumulate': return act === 'ACCUMULATE';
        case 'trim': return act === 'TRIM';
        case 'exit': return act === 'EXIT';
        case 'reduce': return isReduceCandidate(recs[row.ticker]);
        case 'gaps': return isHoldingRow(row) && missingValuation(row, recs);
    }
}

const TEXT_FIELD: Record<string, (row: PositionRow) => unknown> = {
    ticker: row => row.ticker,
    symbol: row => row.ticker,
    name: row => row.name,
    action: row => row.action,
    subStrategyId: row => row.subStrategyId,
};

/** The rows ``state`` keeps, in their incoming order. */
export function filterRows(rows: PositionRow[], state: FilterState, recs: Recs, sectorOf: SectorOf): PositionRow[] {
    return rows.filter(row => {
        if (!inScope(row, state.scope)) return false;
        if (!matchesStatus(row, state.status, recs)) return false;
        if (state.sector !== 'all' && sectorOf(row) !== state.sector) return false;
        if (state.strategy !== 'all' && row.subStrategyId !== state.strategy) return false;
        return Object.entries(state.text).every(([id, needle]) => {
            if (!needle) return true;
            const get = TEXT_FIELD[id];
            if (!get) return true;
            const value = get(row);
            return value != null && String(value).toLowerCase().includes(needle.toLowerCase());
        });
    });
}

/** The count each scope and action chip shows, from the same rules the filter uses. */
export function countsFor(rows: PositionRow[], recs: Recs): Counts {
    const c: Counts = { all: rows.length, actionable: 0, initiate: 0, accumulate: 0, trim: 0, exit: 0, reduce: 0, holdings: 0, watchlist: 0, gaps: 0 };
    for (const row of rows) {
        if (isHoldingRow(row)) c.holdings++;
        if (row.isWatched) c.watchlist++;
        if (matchesStatus(row, 'actionable', recs)) c.actionable++;
        if (matchesStatus(row, 'initiate', recs)) c.initiate++;
        if (matchesStatus(row, 'accumulate', recs)) c.accumulate++;
        if (matchesStatus(row, 'trim', recs)) c.trim++;
        if (matchesStatus(row, 'exit', recs)) c.exit++;
        if (matchesStatus(row, 'reduce', recs)) c.reduce++;
        if (matchesStatus(row, 'gaps', recs)) c.gaps++;
    }
    return c;
}

const distinctSorted = (values: Array<string | null | undefined>): string[] =>
    [...new Set(values.filter((v): v is string => !!v))].sort((a, b) => a.localeCompare(b));

export const sectorOptions = (rows: PositionRow[], sectorOf: SectorOf): string[] =>
    distinctSorted(rows.map(sectorOf));

export const strategyOptions = (rows: PositionRow[]): string[] =>
    distinctSorted(rows.map(r => r.subStrategyId));
