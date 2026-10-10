/**
 * presets.ts - Which columns, order and sort each screen shows from the one registry.
 *
 * Purpose:
 *     A preset is only a list of registry column ids plus a default sort. Screens do not define
 *     columns; they pick a preset. Row filtering (held positions, one thesis) lives in
 *     positionMath.ts and the screen that renders the table.
 *
 * Layer: Frontend / Components / Positions
 *
 * Usage Examples:
 *     <PositionsTable rows={rows} preset={THESIS_PRESET} />
 *
 * Key Functions (Index):
 *     - THESIS_PRESET: the compact set used inside a thesis page
 *
 * Key Input Dependencies:
 *     - columns.tsx (column ids)
 *
 * Key Output Dependencies:
 *     - PositionsTable, ThesisPositions
 */
export interface PositionPreset {
    columns: string[];
    sort: { id: string; dir: 'asc' | 'desc' };
    totals: boolean;
}

/** A thesis page: stance, valuation range, and how the weight compares with the target. */
export const THESIS_PRESET: PositionPreset = {
    columns: ['symbol', 'action', 'rr_range', 'rr_premium', 'rr_ratio', 'shares', 'actualPct', 'targetPct', 'gapPct'],
    sort: { id: 'actualPct', dir: 'desc' },
    totals: true,
};
