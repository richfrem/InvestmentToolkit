/**
 * ThesisPositions.tsx - The positions table for one thesis document.
 *
 * Purpose:
 *     The same table as every other screen, pre-filtered to the stocks one thesis document
 *     lists (thesis_document_member) and given the thesis column set. A toggle switches between
 *     the stocks you hold and every stock the thesis lists. There is no separate "pending"
 *     section: an unheld stock is simply a row with no shares.
 *
 * Layer: Frontend / Components / Positions
 *
 * Usage Examples:
 *     <ThesisPositions documentId="asi_race" />
 *
 * Key Functions (Index):
 *     - ThesisPositions: scope toggle plus PositionsTable
 *
 * Key Input Dependencies:
 *     - PositionRowsProvider (shared rows), THESIS_PRESET, rowsForDocument
 *
 * Key Output Dependencies:
 *     - ThesisViewModal
 */
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { usePositionRows } from './usePositionRows';
import { PositionsTable } from './PositionsTable';
import { THESIS_PRESET } from './presets';
import { rowsForDocument, type DocumentScope } from './positionMath';

export function ThesisPositions({ documentId }: { documentId: string }) {
    const { rows, loading, error } = usePositionRows();
    const navigate = useNavigate();
    const held = rowsForDocument(rows, documentId, 'held');
    const all = rowsForDocument(rows, documentId, 'all');
    const [chosen, setChosen] = useState<DocumentScope | null>(null);
    const scope: DocumentScope = chosen ?? (held.length > 0 ? 'held' : 'all');
    const shown = scope === 'held' ? held : all;

    if (loading && rows.length === 0) return <div className="text-sm text-zinc-500">Loading positions…</div>;
    if (error && rows.length === 0) return <div className="text-sm text-red-400">{error}</div>;

    return (
        <section aria-label="Positions in this thesis" className="not-prose mt-8">
            <div className="mb-3 flex items-center justify-between gap-3">
                <h3 className="text-base font-bold text-white">Positions in this thesis</h3>
                <div role="group" aria-label="Scope" className="inline-flex overflow-hidden rounded-md border border-zinc-700 text-xs font-bold">
                    {([['held', `Held (${held.length})`], ['all', `All (${all.length})`]] as const).map(([value, label]) => (
                        <button key={value} type="button" aria-pressed={scope === value} onClick={() => setChosen(value)}
                            className={`px-3 py-1 ${scope === value ? 'bg-indigo-600 text-white' : 'bg-zinc-900 text-zinc-400 hover:text-zinc-200'}`}>
                            {label}
                        </button>
                    ))}
                </div>
            </div>
            <PositionsTable rows={shown} preset={THESIS_PRESET}
                onRowClick={row => navigate(`/analysis?ticker=${row.ticker}`)}
                emptyMessage={all.length === 0 ? 'No stocks are linked to this thesis yet.' : 'You hold none of the stocks in this thesis.'} />
        </section>
    );
}
