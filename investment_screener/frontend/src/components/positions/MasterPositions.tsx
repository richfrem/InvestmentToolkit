/**
 * MasterPositions.tsx - The portfolio by pillar, live, inside the master thesis.
 *
 * Purpose:
 *     Replaces the frozen "Portfolio Blueprint" markdown tables. For each strategy pillar it
 *     shows the pillar's name, how the combined weight of its stocks compares with the pillar
 *     target, and the same positions table every other screen uses (stance, valuation range,
 *     shares, actual and target weight, gap, totals). A toggle switches between the portfolio
 *     (held or targeted stocks) and every stock the thesis lists, and a closing line gives the
 *     whole-portfolio totals. Rows are the shared ones, so it can never disagree with another page.
 *
 * Layer: Frontend / Components / Positions
 *
 * Usage Examples:
 *     <MasterPositions />
 *
 * Key Functions (Index):
 *     - MasterPositions: scope toggle, one table per pillar, portfolio totals
 *
 * Key Input Dependencies:
 *     - usePositionRows (shared rows), GET /api/theses/pillars, pillars.ts, scope.ts, PositionsTable
 *
 * Key Output Dependencies:
 *     - InvestmentThesisModal
 */
import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { formatGap, formatWeight, totalsFor } from './positionMath';
import { groupByPillar, type Pillar } from './pillars';
import { PositionsTable } from './PositionsTable';
import { THESIS_PRESET } from './presets';
import { filterRows, type FilterState, type Scope } from './scope';
import { usePositionRows } from './usePositionRows';

const BASE: FilterState = { scope: 'holdings', status: 'all', sector: 'all', strategy: 'all', text: {} };

export function MasterPositions() {
    const { rows, loading, error } = usePositionRows();
    const navigate = useNavigate();
    const [pillars, setPillars] = useState<Pillar[]>([]);
    const [scope, setScope] = useState<Scope>('holdings');

    useEffect(() => {
        let cancelled = false;
        void fetch('/api/theses/pillars')
            .then(r => (r.ok ? r.json() : []))
            .then(list => { if (!cancelled && Array.isArray(list)) setPillars(list as Pillar[]); })
            .catch(() => undefined);
        return () => { cancelled = true; };
    }, []);

    const shown = useMemo(() => filterRows(rows, { ...BASE, scope }, {}, () => null), [rows, scope]);
    const groups = useMemo(() => groupByPillar(shown, pillars), [shown, pillars]);
    const totals = useMemo(() => totalsFor(shown), [shown]);

    if (loading && rows.length === 0) return <div className="text-sm text-zinc-500">Loading positions…</div>;
    if (error && rows.length === 0) return <div className="text-sm text-red-400">{error}</div>;

    return (
        <section aria-label="Portfolio by pillar" className="not-prose my-4">
            <div className="mb-3 flex items-center justify-between gap-3">
                <h3 className="text-base font-bold text-white">Portfolio by pillar</h3>
                <div role="group" aria-label="Scope" className="inline-flex overflow-hidden rounded-md border border-zinc-700 text-xs font-bold">
                    {([['holdings', 'Holdings'], ['all', 'All']] as const).map(([value, label]) => (
                        <button key={value} type="button" aria-pressed={scope === value} onClick={() => setScope(value)}
                            className={`px-3 py-1 ${scope === value ? 'bg-indigo-600 text-white' : 'bg-zinc-900 text-zinc-400 hover:text-zinc-200'}`}>
                            {label}
                        </button>
                    ))}
                </div>
            </div>
            {groups.length === 0 && <div className="rounded-lg border border-zinc-800 p-4 text-sm text-zinc-500">No stocks to show.</div>}
            {groups.map(group => (
                <div key={group.pillarId} className="mb-5">
                    <div className="mb-1.5 flex flex-wrap items-baseline justify-between gap-2">
                        <h4 className="text-sm font-bold text-white">{group.name}</h4>
                        <span className="text-xs text-zinc-400">
                            stocks {formatWeight(group.actualPct)} held · {formatWeight(group.targetPct)} target
                            {group.pillarTarget != null && <> · pillar target {formatWeight(group.pillarTarget)}</>}
                        </span>
                    </div>
                    <PositionsTable rows={group.rows} columnIds={THESIS_PRESET.columns} initialSort={THESIS_PRESET.sort} totals
                        onRowClick={row => navigate(`/analysis?ticker=${row.ticker}`)} />
                </div>
            ))}
            <div className="rounded-lg border border-zinc-700 bg-zinc-900/60 px-4 py-2 text-xs font-bold text-zinc-200">
                {scope === 'holdings' ? 'All holdings' : 'All listed stocks'} · {totals.heldCount} held ·
                actual {formatWeight(totals.actualPct)} · target {formatWeight(totals.targetPct)} · gap {formatGap(totals.gapPct)}
            </div>
        </section>
    );
}
