/**
 * usePositionRows.ts - Read the shared position rows.
 *
 * Purpose:
 *     The context and hook for the rows PositionRowsProvider loads once for the whole app.
 *     Kept apart from the provider so that file exports only a component.
 *
 * Layer: Frontend / Components / Positions
 *
 * Usage Examples:
 *     const { rows, loading, error, refresh } = usePositionRows();
 *
 * Key Functions (Index):
 *     - PositionRowsContext: the context the provider fills
 *     - usePositionRows(): { rows, loading, error, refresh }
 *
 * Key Input Dependencies:
 *     - PositionRowsProvider (the only writer of the context)
 *
 * Key Output Dependencies:
 *     - ThesisPositions and the portfolio pages
 */
import { createContext, useContext } from 'react';
import type { PositionRow } from './positionMath';

export interface PositionRowsValue {
    rows: PositionRow[];
    loading: boolean;
    error: string | null;
    refresh: () => Promise<void>;
}

export const PositionRowsContext = createContext<PositionRowsValue>({
    rows: [], loading: true, error: null, refresh: async () => undefined,
});

export function usePositionRows(): PositionRowsValue {
    return useContext(PositionRowsContext);
}
