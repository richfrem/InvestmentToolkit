/**
 * useColumnPrefs.ts - Keep the owner's column choices (shown, order, widths) for one table.
 *
 * Purpose:
 *     Wraps the pure rules in columnPrefs.ts with React state and localStorage so a table
 *     remembers its columns between visits. Storage may be unavailable (private window, blocked
 *     site data), so every access is guarded and the table works without it.
 *
 * Layer: Frontend / Components / Positions
 *
 * Usage Examples:
 *     const prefs = useColumnPrefs('portfolio-table-v1', COLUMNS, PORTFOLIO_PRESET.columns);
 *
 * Key Functions (Index):
 *     - useColumnPrefs(): { visible, order, widths, toggle, move, resize, reset }
 *
 * Key Input Dependencies:
 *     - columnPrefs.ts, browser localStorage (optional)
 *
 * Key Output Dependencies:
 *     - PortfolioPage, ColumnPicker, PositionsTable
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import { moveColumn, resizeColumn, resolveColumns, toggleColumn, type ColumnMeta, type ColumnPrefs } from './columnPrefs';

function loadPrefs(key: string): ColumnPrefs | null {
    try {
        const raw = localStorage.getItem(key);
        return raw ? (JSON.parse(raw) as ColumnPrefs) : null;
    } catch {
        return null;
    }
}

function savePrefs(key: string, prefs: ColumnPrefs): void {
    try {
        localStorage.setItem(key, JSON.stringify(prefs));
    } catch { /* quota or blocked storage: the table still works */ }
}

export function useColumnPrefs(storageKey: string, columns: ColumnMeta[], defaults: string[]) {
    const initial = useMemo(() => resolveColumns(loadPrefs(storageKey), columns, defaults), [storageKey, columns, defaults]);
    const [visible, setVisible] = useState<Set<string>>(initial.visible);
    const [order, setOrder] = useState<string[]>(initial.order);
    const [widths, setWidths] = useState<Record<string, number>>(initial.widths);
    const always = useMemo(() => new Set(columns.filter(c => c.always).map(c => c.id)), [columns]);

    useEffect(() => {
        savePrefs(storageKey, { visible: [...visible], columnOrder: order, columnWidths: widths });
    }, [storageKey, visible, order, widths]);

    const toggle = useCallback((id: string) => setVisible(v => toggleColumn(v, id, always)), [always]);
    const move = useCallback((id: string, direction: 'up' | 'down') => setOrder(o => moveColumn(o, id, direction)), []);
    const resize = useCallback((id: string, width: number) => setWidths(w => resizeColumn(w, id, width)), []);
    const reset = useCallback(() => {
        const fresh = resolveColumns(null, columns, defaults);
        setVisible(fresh.visible);
        setOrder(fresh.order);
        setWidths({});
    }, [columns, defaults]);

    return { visible, order, widths, toggle, move, resize, reset };
}
