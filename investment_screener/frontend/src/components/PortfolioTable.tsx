import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { SlidersHorizontal, ChevronUp, ChevronDown, ChevronsUpDown } from 'lucide-react';

// ─── Types ────────────────────────────────────────────────────────────────────

interface StockRow {
    symbol: string;
    name: string;
    sector: string;
    industry: string;
    price: number;
    book_price: number | null;
    shares: number;
    position_value: number;
    total_market: number;
    total_book: number | null;
    change_1d: number | null;
    change_1w: number | null;
    change_1m: number | null;
    change_ytd: number | null;
    change_1y: number | null;
    change_overall: number | null;
}

interface HeatmapResponse {
    stocks: StockRow[];
    total_value: number;
}

// ─── Column Definitions ───────────────────────────────────────────────────────

interface ColDef {
    id: keyof StockRow;
    label: string;
    always?: boolean;       // cannot be hidden
    isChange?: boolean;     // heatmap-coloured background
    defaultOn?: boolean;
    align?: 'left' | 'right';
    format: (v: number | string | null) => string;
}

const COLUMNS: ColDef[] = [
    { id: 'symbol',         label: 'Symbol',    always: true,  defaultOn: true, align: 'left',  format: v => v },
    { id: 'name',           label: 'Name',      always: true,  defaultOn: true, align: 'left',  format: v => v },
    { id: 'sector',         label: 'Sector',    defaultOn: false, align: 'left', format: v => v ?? '—' },
    { id: 'shares',         label: 'Shares',    defaultOn: false, align: 'right', format: v => v?.toLocaleString() ?? '—' },
    { id: 'price',          label: 'Price',     defaultOn: true, align: 'right', format: v => v != null ? `$${v.toFixed(2)}` : '—' },
    { id: 'book_price',     label: 'Avg Cost',  defaultOn: true, align: 'right', format: v => v != null ? `$${v.toFixed(2)}` : '—' },
    { id: 'change_1d',      label: '1D %',   isChange: true, defaultOn: true,  align: 'right', format: fmtPct },
    { id: 'change_1w',      label: '1W %',   isChange: true, defaultOn: true,  align: 'right', format: fmtPct },
    { id: 'change_1m',      label: '1M %',   isChange: true, defaultOn: true,  align: 'right', format: fmtPct },
    { id: 'change_ytd',     label: 'YTD %',  isChange: true, defaultOn: true,  align: 'right', format: fmtPct },
    { id: 'change_1y',      label: '1Y %',   isChange: true, defaultOn: true,  align: 'right', format: fmtPct },
    { id: 'change_overall', label: 'Overall %', isChange: true, defaultOn: true, align: 'right', format: fmtPct },
    { id: 'total_book',     label: 'Book Value',   defaultOn: true, align: 'right', format: fmtDollar },
    { id: 'total_market',   label: 'Mkt Value',    defaultOn: true, align: 'right', format: fmtDollar },
];

// ─── Helpers ──────────────────────────────────────────────────────────────────

function fmtPct(v: number | null): string {
    if (v == null) return '—';
    return `${v >= 0 ? '+' : ''}${v.toFixed(2)}%`;
}

function fmtDollar(v: number | null): string {
    if (v == null) return '—';
    if (v >= 1_000_000) return `$${(v / 1_000_000).toFixed(2)}M`;
    if (v >= 1_000)     return `$${(v / 1_000).toFixed(1)}K`;
    return `$${v.toFixed(0)}`;
}

/** Finviz-style heatmap colour with reduced opacity for table cells */
function changeBg(v: number | null): string {
    if (v == null) return 'transparent';
    if (v >=  8) return 'rgba(0,77,0,0.85)';
    if (v >=  5) return 'rgba(0,102,0,0.80)';
    if (v >=  3) return 'rgba(0,128,0,0.75)';
    if (v >=  2) return 'rgba(0,160,0,0.70)';
    if (v >=  1) return 'rgba(0,192,0,0.65)';
    if (v >=  0.5) return 'rgba(0,220,0,0.55)';
    if (v >=  0) return 'rgba(30,180,30,0.30)';
    if (v >= -0.5) return 'rgba(200,30,30,0.30)';
    if (v >= -1) return 'rgba(210,0,0,0.55)';
    if (v >= -2) return 'rgba(185,0,0,0.65)';
    if (v >= -3) return 'rgba(160,0,0,0.70)';
    if (v >= -5) return 'rgba(130,0,0,0.75)';
    if (v >= -8) return 'rgba(100,0,0,0.80)';
    return 'rgba(70,0,0,0.85)';
}

function sortRows(rows: StockRow[], col: keyof StockRow, dir: 'asc' | 'desc'): StockRow[] {
    return [...rows].sort((a, b) => {
        const av = a[col];
        const bv = b[col];
        if (av == null && bv == null) return 0;
        if (av == null) return 1;
        if (bv == null) return -1;
        const cmp = av < bv ? -1 : av > bv ? 1 : 0;
        return dir === 'asc' ? cmp : -cmp;
    });
}

// ─── Component ────────────────────────────────────────────────────────────────

export default function PortfolioTable() {
    const navigate = useNavigate();
    const [data, setData] = useState<HeatmapResponse | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Column visibility — keyed by col id
    const defaultVisible = new Set(COLUMNS.filter(c => c.always || c.defaultOn).map(c => c.id));
    const [visible, setVisible] = useState<Set<string>>(defaultVisible);
    const [pickerOpen, setPickerOpen] = useState(false);
    const pickerRef = useRef<HTMLDivElement>(null);

    // Sorting
    const [sortCol, setSortCol] = useState<keyof StockRow>('total_market');
    const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');

    useEffect(() => { fetchData(); }, []);

    // Close picker on outside click
    useEffect(() => {
        function handle(e: MouseEvent) {
            if (pickerRef.current && !pickerRef.current.contains(e.target as Node)) {
                setPickerOpen(false);
            }
        }
        document.addEventListener('mousedown', handle);
        return () => document.removeEventListener('mousedown', handle);
    }, []);

    async function fetchData() {
        setLoading(true);
        setError(null);
        try {
            const portRes = await fetch('/api/portfolio');
            if (!portRes.ok) throw new Error('Failed to fetch portfolio');
            const portConfig = await portRes.json() as { items?: StockRow[] };
            const items: StockRow[] = portConfig.items ?? [];

            const res = await fetch('/api/portfolio-heatmap', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ items }),
            });
            if (!res.ok) throw new Error('Failed to fetch heatmap data');
            setData(await res.json());
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : 'Failed to load');
        } finally {
            setLoading(false);
        }
    }

    function handleSort(col: keyof StockRow) {
        if (sortCol === col) {
            setSortDir(d => d === 'asc' ? 'desc' : 'asc');
        } else {
            setSortCol(col);
            setSortDir('desc');
        }
    }

    function toggleCol(id: string) {
        setVisible(prev => {
            const next = new Set(prev);
            if (next.has(id)) next.delete(id); else next.add(id);
            return next;
        });
    }

    const visibleCols = COLUMNS.filter(c => visible.has(c.id));
    const rows = data ? sortRows(data.stocks, sortCol, sortDir) : [];

    // ── Loading / error states ───────────────────────────────────────────────

    if (loading) return (
        <div className="flex items-center justify-center h-64 bg-zinc-900 rounded-lg">
            <div className="flex flex-col items-center gap-3">
                <div className="animate-spin rounded-full h-8 w-8 border-2 border-amber-500 border-t-transparent" />
                <span className="text-zinc-400 text-sm">Loading portfolio data…</span>
                <span className="text-zinc-600 text-xs">Fetching historical prices (first load may take ~10s)</span>
            </div>
        </div>
    );

    if (error) return (
        <div className="bg-red-900/30 text-red-400 p-4 rounded-lg text-center">
            <div className="font-medium mb-2">{error}</div>
            <button onClick={fetchData} className="px-3 py-1 bg-red-800/50 rounded text-sm">Retry</button>
        </div>
    );

    if (!data) return null;

    // ── Render ───────────────────────────────────────────────────────────────

    return (
        <div className="flex flex-col bg-zinc-900 rounded-lg overflow-hidden border border-zinc-800">

            {/* Header bar */}
            <div className="flex items-center justify-between px-4 py-2.5 bg-zinc-900 border-b border-zinc-800">
                <div className="flex items-center gap-4">
                    <span className="text-white font-semibold text-sm">Portfolio Table</span>
                    <span className="text-zinc-500 text-xs">{rows.length} positions</span>
                </div>
                <div className="flex items-center gap-3">
                    <span className="text-zinc-300 text-sm font-bold">{fmtDollar(data.total_value)}</span>

                    {/* Column picker */}
                    <div className="relative" ref={pickerRef}>
                        <button
                            onClick={() => setPickerOpen(o => !o)}
                            className="flex items-center gap-1.5 px-3 py-1 bg-zinc-800 text-zinc-300 rounded text-xs hover:bg-zinc-700 transition-colors"
                        >
                            <SlidersHorizontal size={13} />
                            Columns
                        </button>
                        {pickerOpen && (
                            <div className="absolute right-0 top-8 z-50 w-48 bg-zinc-800 border border-zinc-700 rounded-lg shadow-2xl p-2">
                                <div className="text-[10px] text-zinc-500 uppercase font-bold px-2 pb-1 mb-1 border-b border-zinc-700">
                                    Toggle Columns
                                </div>
                                {COLUMNS.filter(c => !c.always).map(col => (
                                    <label key={col.id} className="flex items-center gap-2 px-2 py-1.5 rounded hover:bg-zinc-700 cursor-pointer">
                                        <input
                                            type="checkbox"
                                            checked={visible.has(col.id)}
                                            onChange={() => toggleCol(col.id)}
                                            className="accent-amber-500 w-3.5 h-3.5"
                                        />
                                        <span className="text-xs text-zinc-300">{col.label}</span>
                                    </label>
                                ))}
                            </div>
                        )}
                    </div>

                    <button
                        onClick={fetchData}
                        className="px-3 py-1 bg-zinc-800 text-zinc-300 rounded text-xs hover:bg-zinc-700 transition-colors"
                    >
                        ↻ Refresh
                    </button>
                </div>
            </div>

            {/* Table */}
            <div className="overflow-auto">
                <table className="w-full text-sm border-collapse">
                    <thead>
                        <tr className="bg-zinc-800/60 border-b border-zinc-700">
                            {visibleCols.map(col => {
                                const active = sortCol === col.id;
                                return (
                                    <th
                                        key={col.id}
                                        onClick={() => handleSort(col.id)}
                                        className={`px-3 py-2.5 font-semibold text-xs uppercase tracking-wider cursor-pointer select-none whitespace-nowrap
                                            ${col.align === 'right' ? 'text-right' : 'text-left'}
                                            ${active ? 'text-amber-400' : 'text-zinc-400 hover:text-zinc-200'}`}
                                    >
                                        <span className="inline-flex items-center gap-1">
                                            {col.label}
                                            {active
                                                ? sortDir === 'asc'
                                                    ? <ChevronUp size={11} className="text-amber-400" />
                                                    : <ChevronDown size={11} className="text-amber-400" />
                                                : <ChevronsUpDown size={11} className="text-zinc-600" />
                                            }
                                        </span>
                                    </th>
                                );
                            })}
                        </tr>
                    </thead>
                    <tbody>
                        {rows.map((row, i) => (
                            <tr
                                key={row.symbol}
                                onClick={() => navigate(`/analysis?ticker=${row.symbol}`)}
                                className={`border-b border-zinc-800 cursor-pointer transition-colors
                                    ${i % 2 === 0 ? 'bg-zinc-900' : 'bg-zinc-900/50'}
                                    hover:bg-zinc-800/70`}
                            >
                                {visibleCols.map(col => {
                                    const val = row[col.id];
                                    const numVal = typeof val === 'number' ? val : null;
                                    const isChange = col.isChange;
                                    return (
                                        <td
                                            key={col.id}
                                            className={`px-3 py-2.5 whitespace-nowrap ${col.align === 'right' ? 'text-right' : 'text-left'}`}
                                            style={isChange ? { backgroundColor: changeBg(numVal) } : undefined}
                                        >
                                            {col.id === 'symbol' ? (
                                                <span className="font-bold text-white">{val}</span>
                                            ) : col.id === 'name' ? (
                                                <span className="text-zinc-300 text-xs">{val}</span>
                                            ) : isChange ? (
                                                <span className={`font-semibold text-xs ${val == null ? 'text-zinc-600' : val >= 0 ? 'text-white' : 'text-white'}`}>
                                                    {col.format(val)}
                                                </span>
                                            ) : (
                                                <span className="text-zinc-300">{col.format(val)}</span>
                                            )}
                                        </td>
                                    );
                                })}
                            </tr>
                        ))}
                    </tbody>

                    {/* Totals footer */}
                    <tfoot>
                        <tr className="border-t-2 border-zinc-700 bg-zinc-800/40">
                            {visibleCols.map((col, i) => {
                                let content: string = '';
                                if (col.id === 'symbol') content = 'TOTAL';
                                else if (col.id === 'total_market') content = fmtDollar(data.total_value);
                                else if (col.id === 'total_book') {
                                    const tb = rows.reduce((s, r) => r.total_book != null ? s + r.total_book : s, 0);
                                    content = tb > 0 ? fmtDollar(tb) : '—';
                                }
                                return (
                                    <td key={col.id} className={`px-3 py-2 text-xs font-bold ${col.align === 'right' ? 'text-right' : 'text-left'} ${i === 0 ? 'text-zinc-400' : 'text-zinc-300'}`}>
                                        {content}
                                    </td>
                                );
                            })}
                        </tr>
                    </tfoot>
                </table>
            </div>
        </div>
    );
}
