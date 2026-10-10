/**
 * PositionsTable.tsx - The one table component for a list of tickers.
 *
 * Purpose:
 *     Renders position rows with the columns of a preset: sortable header, row click, optional
 *     totals row. It owns no data and defines no columns: rows come from the shared provider,
 *     columns from the registry (columns.tsx), and the recommendation behind each row from the
 *     shared recommendations context. Every screen that lists tickers uses this component.
 *
 * Layer: Frontend / Components / Positions
 *
 * Usage Examples:
 *     <PositionsTable rows={rows} preset={THESIS_PRESET} onRowClick={r => navigate(...)} />
 *
 * Key Functions (Index):
 *     - PositionsTable: header with sort, body, totals row
 *
 * Key Input Dependencies:
 *     - columns.tsx, presets.ts, positionMath.ts, contexts/useRecommendations, context/PrivacyContext
 *
 * Key Output Dependencies:
 *     - ThesisPositions and the portfolio pages
 */
import { useMemo, useState } from 'react';
import { ChevronDown, ChevronUp, ChevronsUpDown } from 'lucide-react';
import { useRecommendations } from '../../contexts/useRecommendations';
import { usePrivacy } from '../../context/PrivacyContext';
import { COLUMNS_BY_ID } from './columns';
import type { PositionPreset } from './presets';
import { sortRows, totalsFor, type PositionRow } from './positionMath';

interface PositionsTableProps {
    rows: PositionRow[];
    preset: PositionPreset;
    onRowClick?: (row: PositionRow) => void;
    emptyMessage?: string;
}

export function PositionsTable({ rows, preset, onRowClick, emptyMessage = 'No stocks to show.' }: PositionsTableProps) {
    const recommendations = useRecommendations();
    const { isPrivacyMode } = usePrivacy();
    const [sort, setSort] = useState(preset.sort);
    const columns = preset.columns.map(id => COLUMNS_BY_ID[id]).filter(Boolean);

    const sorted = useMemo(() => {
        const column = COLUMNS_BY_ID[sort.id];
        if (!column?.sort) return rows;
        const get = column.sort;
        // Rows tied on the sorted column (for example every unheld stock at 0%) keep the order of
        // largest target weight first, then ticker, so the missing allocations read in priority order.
        const base = sortRows(sortRows(rows, row => row.ticker, 'asc'), row => row.targetPct, 'desc');
        return sortRows(base, row => get(row, recommendations[row.ticker]), sort.dir);
    }, [rows, sort, recommendations]);

    const totals = useMemo(() => totalsFor(rows), [rows]);

    if (rows.length === 0) return <div className="rounded-lg border border-zinc-800 p-4 text-sm text-zinc-500">{emptyMessage}</div>;

    const toggleSort = (id: string) =>
        setSort(prev => prev.id === id ? { id, dir: prev.dir === 'asc' ? 'desc' : 'asc' } : { id, dir: 'desc' });

    return (
        <div className="overflow-x-auto rounded-lg border border-zinc-800">
            <table className="w-full border-collapse text-sm" data-testid="positions-table">
                <thead>
                    <tr className="border-b border-zinc-700 bg-zinc-800/60">
                        {columns.map(col => {
                            const active = sort.id === col.id;
                            return (
                                <th key={col.id} title={col.title} scope="col"
                                    aria-sort={active ? (sort.dir === 'asc' ? 'ascending' : 'descending') : 'none'}
                                    style={{ minWidth: col.width }}
                                    className={`px-3 py-2 text-xs font-semibold uppercase tracking-wider ${col.align === 'right' ? 'text-right' : 'text-left'} ${active ? 'text-amber-400' : 'text-zinc-400'}`}>
                                    {col.sort ? (
                                        <button type="button" onClick={() => toggleSort(col.id)}
                                            className="inline-flex items-center gap-1 hover:text-zinc-200">
                                            {col.label}
                                            {active
                                                ? (sort.dir === 'asc' ? <ChevronUp size={11} /> : <ChevronDown size={11} />)
                                                : <ChevronsUpDown size={11} className="text-zinc-600" />}
                                        </button>
                                    ) : col.label}
                                </th>
                            );
                        })}
                    </tr>
                </thead>
                <tbody>
                    {sorted.map((row, i) => {
                        const rec = recommendations[row.ticker];
                        return (
                            <tr key={row.ticker} onClick={onRowClick ? () => onRowClick(row) : undefined}
                                className={`border-b border-zinc-800 ${onRowClick ? 'cursor-pointer' : ''} ${i % 2 ? 'bg-zinc-900/50' : 'bg-zinc-900'} hover:bg-zinc-800/70`}>
                                {columns.map(col => (
                                    <td key={col.id} className={`px-3 py-2 ${col.align === 'right' ? 'text-right' : 'text-left'}`}>
                                        {col.cell(row, { rec, hidden: isPrivacyMode })}
                                    </td>
                                ))}
                            </tr>
                        );
                    })}
                </tbody>
                {preset.totals && (
                    <tfoot>
                        <tr className="border-t-2 border-zinc-700 bg-zinc-800/40 text-xs font-bold text-zinc-300">
                            {columns.map((col, i) => (
                                <td key={col.id} className={`px-3 py-2 ${col.align === 'right' ? 'text-right' : 'text-left'}`}>
                                    {i === 0 ? <span className="whitespace-nowrap">{`TOTAL · ${totals.heldCount} held`}</span> : col.total ? col.total(totals) : null}
                                </td>
                            ))}
                        </tr>
                    </tfoot>
                )}
            </table>
        </div>
    );
}
