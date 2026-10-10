/**
 * PositionRowsProvider.tsx - Load the position rows once and share them with every table.
 *
 * Purpose:
 *     One fetch of GET /api/screener/all-holdings for the whole app, refreshed on focus, on a
 *     timer and when positions or recommendations change. Portfolio, Portfolio Advisor and the
 *     thesis pages all read these rows, so the same ticker shows the same shares, weight and
 *     target everywhere and opening a thesis does not trigger more requests.
 *
 * Layer: Frontend / Components / Positions
 *
 * Usage Examples:
 *     <PositionRowsProvider><App /></PositionRowsProvider>
 *     (read the rows with usePositionRows() from ./usePositionRows)
 *
 * Key Functions (Index):
 *     - PositionRowsProvider: fetches, refreshes and provides the rows
 *
 * Key Input Dependencies:
 *     - services/api fetchPositionRows (GET /api/screener/all-holdings)
 *
 * Key Output Dependencies:
 *     - PositionsTable consumers (ThesisPositions, portfolio pages)
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { fetchPositionRows } from '../../services/api';
import type { PositionRow } from './positionMath';
import { PositionRowsContext } from './usePositionRows';


export function PositionRowsProvider({ children }: { children: ReactNode }) {
    const [rows, setRows] = useState<PositionRow[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const version = useRef(0);

    const refresh = useCallback(async () => {
        const request = ++version.current;
        try {
            const data = await fetchPositionRows();
            if (request !== version.current) return;
            setRows(data);
            setError(null);
        } catch (e) {
            if (request === version.current) setError(e instanceof Error ? e.message : 'Failed to load positions');
        } finally {
            if (request === version.current) setLoading(false);
        }
    }, []);

    useEffect(() => {
        const reload = () => { void refresh(); };
        const initial = window.setTimeout(reload, 0);
        const timer = window.setInterval(reload, 60_000);
        window.addEventListener('focus', reload);
        window.addEventListener('portfolio-synced', reload);
        window.addEventListener('recommendation-data-changed', reload);
        return () => {
            window.clearTimeout(initial);
            window.clearInterval(timer);
            window.removeEventListener('focus', reload);
            window.removeEventListener('portfolio-synced', reload);
            window.removeEventListener('recommendation-data-changed', reload);
        };
    }, [refresh]);

    const value = useMemo(() => ({ rows, loading, error, refresh }), [rows, loading, error, refresh]);
    return <PositionRowsContext.Provider value={value}>{children}</PositionRowsContext.Provider>;
}
