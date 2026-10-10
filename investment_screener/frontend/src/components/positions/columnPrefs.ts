/**
 * columnPrefs.ts - Pure state rules for the configurable table: which columns show, in what
 * order, how wide.
 *
 * Purpose:
 *     A preset names the default columns; the owner can then show or hide columns, reorder them
 *     and resize them, and the page saves that. These functions resolve saved choices against
 *     the current registry (dropping ids that no longer exist, showing new preset columns) and
 *     apply each edit without mutating state. React and localStorage stay in useColumnPrefs.
 *
 * Layer: Frontend / Components / Positions
 *
 * Usage Examples:
 *     const { visible, order, widths } = resolveColumns(saved, COLUMNS, PORTFOLIO_PRESET.columns);
 *
 * Key Functions (Index):
 *     - resolveColumns(): saved prefs + registry + preset -> { visible, order, widths }
 *     - toggleColumn(): show or hide one column (not the always-on ones)
 *     - moveColumn(): move one column a place up or down
 *     - resizeColumn(): set one width with a minimum
 *
 * Key Input Dependencies:
 *     - utils/riskReward (mergeColumnPrefs)
 *
 * Key Output Dependencies:
 *     - useColumnPrefs, ColumnPicker
 */
import { mergeColumnPrefs } from '../../utils/riskReward';

export interface ColumnPrefs {
    visible: string[];
    columnOrder: string[];
    columnWidths: Record<string, number>;
}

export interface ColumnMeta {
    id: string;
    always?: boolean;
}

export const MIN_COLUMN_WIDTH = 40;

/** Saved prefs resolved against the current columns; ``defaults`` are the preset's column ids. */
export function resolveColumns(prefs: ColumnPrefs | null, columns: ColumnMeta[], defaults: string[]) {
    const defaultSet = new Set(defaults);
    const merged = mergeColumnPrefs(
        prefs,
        columns.map(c => ({ id: c.id, always: c.always, defaultOn: defaultSet.has(c.id) })),
        'action',
    );
    const visible = new Set(merged.visible);
    for (const c of columns) if (c.always) visible.add(c.id);
    const valid = new Set(columns.map(c => c.id));
    const widths = Object.fromEntries(Object.entries(prefs?.columnWidths ?? {}).filter(([id]) => valid.has(id)));
    return { visible, order: merged.order, widths };
}

/** A copy of ``visible`` with ``id`` toggled; always-on columns are left alone. */
export function toggleColumn(visible: Set<string>, id: string, always: Set<string>): Set<string> {
    if (always.has(id)) return new Set(visible);
    const next = new Set(visible);
    if (next.has(id)) next.delete(id); else next.add(id);
    return next;
}

/** A copy of ``order`` with ``id`` moved one place; unchanged at the ends or for an unknown id. */
export function moveColumn(order: string[], id: string, direction: 'up' | 'down'): string[] {
    const index = order.indexOf(id);
    const target = direction === 'up' ? index - 1 : index + 1;
    if (index === -1 || target < 0 || target >= order.length) return order;
    const next = [...order];
    [next[index], next[target]] = [next[target], next[index]];
    return next;
}

/** A copy of ``widths`` with ``id`` set to ``width`` (not below the minimum). */
export function resizeColumn(widths: Record<string, number>, id: string, width: number): Record<string, number> {
    return { ...widths, [id]: Math.max(MIN_COLUMN_WIDTH, width) };
}
