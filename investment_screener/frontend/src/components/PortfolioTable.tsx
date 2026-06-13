/**
 * PortfolioTable.tsx (React Component)
 * =====================================
 *
 * Purpose:
 *     Interactive table for viewing and sorting portfolio positions with live pricing and drift metrics.
 *
 * Layer: Frontend / UI / Components
 *
 * Usage Examples:
 *     <PortfolioTable />
 *
 * Key Functions:
 *     - startResize() - Column resizing interaction logic
 *     - fetchPortfolioData() - Retrieves holdings and joins with latest AI projections
 *     - stocksWithPct (memo) - Calculates portfolio weighting and drift against target
 */
import { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { fetchAllProjections, syncAndRefreshPortfolio, addToWatchlist, removeFromWatchlist } from '../services/api';
import { SlidersHorizontal, ChevronUp, ChevronDown, ChevronsUpDown, Filter, ArrowUp, ArrowDown, Star } from 'lucide-react';
import { PriceSourceBadge } from './PriceSourceBadge';
import { TradeButtons } from './TradeButtons';
import { TradeLogModal } from './TradeLogModal';
import { safeNum, fmtPct, fmtDollar, fmtPrice, changeBgDaily, sortByColumn } from '../utils/formatters';

function computeSuggestedShares(currentPct: number | null, targetPct: number | null, price: number | null, totalValue: number): number {
    if (!currentPct || !targetPct || !price || totalValue <= 0) return 1;
    const dollarGap = Math.abs((targetPct - currentPct) * totalValue) / 100;
    return Math.max(1, Math.floor(dollarGap / price));
}

// ─── Types ────────────────────────────────────────────────────────────────────

interface StockRow {
    symbol: string;
    name: string;
    sector: string;
    industry: string;
    currentPrice: number;
    book_price: number | null;
    shares: number;
    position_value: number;
    total_market: number;
    total_book: number | null;
    currentPct: number | null;
    subStrategyId: string | null;
    change_1d: number | null;
    change_1w: number | null;
    change_1m: number | null;
    change_ytd: number | null;
    change_1y: number | null;
    change_overall: number | null;
    action: string | null;
    recommendedPct: number | null;
    rationale: string | null;
    fairValue: number | null;
    gainLoss: number | null;
    upside: number | null;
    growth: number | null;
    ruleOf40: number | null;
    model: string | null;
    bear: number | null;
    base: number | null;
    bull: number | null;
    qualityMultiplier: number | null;
    lastAnalyzed: string | null;
}

interface HeatmapResponse {
    stocks: StockRow[];
    total_value: number;
    total_value_usd?: number;
    total_value_cad?: number;
    price_source?: string;
    refreshed_at?: string;
    exchange_rate?: number;
}

// ─── Column Definitions ───────────────────────────────────────────────────────

interface ColDef {
    id: keyof StockRow;
    label: string;
    always?: boolean;
    isChange?: boolean;
    defaultOn?: boolean;
    align?: 'left' | 'right';
    format: (v: number | string | null) => string;
}

const COLUMNS: ColDef[] = [
    { id: 'symbol',         label: 'Ticker',     always: true,  defaultOn: true,  align: 'left',  format: v => String(v ?? '') },
    { id: 'name',           label: 'Name',       always: true,  defaultOn: false, align: 'left',  format: v => String(v ?? '') },
    { id: 'action',         label: 'Action',     defaultOn: true,  align: 'left',  format: v => String(v ?? '—') },
    { id: 'currentPct',     label: 'Current %',  defaultOn: true,  align: 'right', format: v => safeNum(v) != null ? `${safeNum(v)!.toFixed(2)}%` : '—' },
    { id: 'recommendedPct', label: 'Target %',   defaultOn: true,  align: 'right', format: v => safeNum(v) != null ? `${safeNum(v)!.toFixed(2)}%` : '—' },
    { id: 'rationale',      label: 'Rationale',  defaultOn: false, align: 'left',  format: v => String(v ?? '—') },
    { id: 'fairValue',      label: 'Fair Value', defaultOn: true,  align: 'right', format: fmtDollar },
    { id: 'currentPrice',   label: 'Price',      defaultOn: true,  align: 'right', format: fmtPrice },
    { id: 'gainLoss',       label: 'Gain ($)',   isChange: true, defaultOn: true,  align: 'right', format: v => safeNum(v) != null ? `${safeNum(v)! >= 0 ? '+$' : '-$'}${Math.abs(Math.round(safeNum(v)!))}` : '—' },
    { id: 'upside',         label: 'Upside (%)', isChange: true, defaultOn: true,  align: 'right', format: fmtPct },
    { id: 'ruleOf40',       label: 'R40',        defaultOn: true,  align: 'right', format: v => safeNum(v) != null ? safeNum(v)!.toFixed(1) : '—' },
    { id: 'growth',         label: 'Growth',     defaultOn: true,  align: 'right', format: v => safeNum(v) != null ? `${safeNum(v)!.toFixed(1)}%` : '—' },
    { id: 'model',          label: 'Analyst',    defaultOn: true,  align: 'left',  format: v => String(v ?? '—') },
    { id: 'bear',           label: 'Bear',       defaultOn: false, align: 'right', format: fmtDollar },
    { id: 'base',           label: 'Base',       defaultOn: false, align: 'right', format: fmtDollar },
    { id: 'bull',           label: 'Bull',       defaultOn: false, align: 'right', format: fmtDollar },
    { id: 'change_1d',      label: '1D %',       isChange: true, defaultOn: true,  align: 'right', format: fmtPct },
    { id: 'change_1w',      label: '1W %',       isChange: true, defaultOn: false, align: 'right', format: fmtPct },
    { id: 'change_1m',      label: '1M %',       isChange: true, defaultOn: false, align: 'right', format: fmtPct },
    { id: 'change_ytd',     label: 'YTD %',      isChange: true, defaultOn: false, align: 'right', format: fmtPct },
    { id: 'change_1y',      label: '1Y %',       isChange: true, defaultOn: false, align: 'right', format: fmtPct },
    { id: 'change_overall', label: 'Overall %',  isChange: true, defaultOn: true,  align: 'right', format: fmtPct },
    { id: 'sector',         label: 'Sector',     defaultOn: false, align: 'left',  format: v => String(v ?? '—') },
    { id: 'shares',         label: 'Shares',     defaultOn: false, align: 'right', format: v => safeNum(v) != null ? safeNum(v)!.toLocaleString() : '—' },
    { id: 'book_price',     label: 'Avg Cost',   defaultOn: false, align: 'right', format: fmtPrice },
    { id: 'total_book',     label: 'Book Value', defaultOn: false, align: 'right', format: fmtDollar },
    { id: 'total_market',   label: 'Mkt Value',  defaultOn: false, align: 'right', format: fmtDollar },
    { id: 'qualityMultiplier', label: 'Quality', defaultOn: false, align: 'right', format: v => safeNum(v) != null ? `${safeNum(v)!.toFixed(2)}x` : '—' },
    { id: 'subStrategyId',  label: 'Strategy',   defaultOn: false, align: 'left',  format: v => String(v ?? '—') },
    { id: 'lastAnalyzed',   label: 'Analyzed',   defaultOn: true,  align: 'right', format: v => v ? new Date(v as string).toLocaleDateString() : '—' },
];

const DEFAULT_WIDTHS: Record<string, number> = {
    symbol: 70, name: 170, currentPct: 90, subStrategyId: 130, sector: 115, shares: 60, currentPrice: 72,
    book_price: 72, change_1d: 65, change_1w: 65, change_1m: 65,
    change_ytd: 65, change_1y: 65, change_overall: 80,
    total_book: 80, total_market: 80,
    action: 115, fairValue: 95, gainLoss: 85, upside: 85, ruleOf40: 70, growth: 80,
    model: 130, base: 80, bear: 80, bull: 80, qualityMultiplier: 80, lastAnalyzed: 90,
    recommendedPct: 85, rationale: 260,
};

// ─── Persistence ──────────────────────────────────────────────────────────────

const STORAGE_KEY = 'portfolio-table-prefs-v3';

interface TablePrefs {
    visible: string[];
    columnOrder: string[];
    columnWidths: Record<string, number>;
}

function loadPrefs(): TablePrefs | null {
    try {
        const raw = localStorage.getItem(STORAGE_KEY);
        return raw ? (JSON.parse(raw) as TablePrefs) : null;
    } catch { return null; }
}

function savePrefs(prefs: TablePrefs) {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs)); } catch { /* quota */ }
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

const changeBg = changeBgDaily;
const sortRows = (rows: StockRow[], col: keyof StockRow, dir: 'asc' | 'desc') => sortByColumn(rows, col, dir);

// ─── Component ────────────────────────────────────────────────────────────────

export default function PortfolioTable() {
    const navigate = useNavigate();
    const [data, setData] = useState<HeatmapResponse | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [priceSource, setPriceSource] = useState<string | null>(null);
    const [lastRefreshedAt, setLastRefreshedAt] = useState<Date | null>(null);
    const [exchangeRate, setExchangeRate] = useState<number>(1.38);
    const [logModal, setLogModal] = useState<{ ticker: string } | null>(null);
    const [watchedTickers, setWatchedTickers] = useState<Set<string>>(new Set());

    // Load persisted prefs once
    const savedPrefs = useRef<TablePrefs | null>(null);
    if (savedPrefs.current === null) savedPrefs.current = loadPrefs();
    const prefs = savedPrefs.current;

    const validIds = new Set<string>(COLUMNS.map(c => c.id as string));
    const defaultVisible = new Set(COLUMNS.filter(c => c.always || c.defaultOn).map(c => c.id));
    const filteredPrefsOrder = (prefs?.columnOrder.filter(id => validIds.has(id)) ?? null) as (keyof StockRow)[] | null;
    const [visible, setVisible] = useState<Set<string>>(
        prefs ? new Set(prefs.visible.filter(id => validIds.has(id))) : defaultVisible
    );
    const [columnOrder, setColumnOrder] = useState<string[]>(
        filteredPrefsOrder
            ? [...filteredPrefsOrder, ...COLUMNS.map(c => c.id).filter(id => !filteredPrefsOrder.includes(id))]
            : COLUMNS.map(c => c.id)
    );
    const [columnWidths, setColumnWidths] = useState<Record<string, number>>(
        { ...DEFAULT_WIDTHS, ...(prefs?.columnWidths ?? {}) }
    );

    const [pickerOpen, setPickerOpen] = useState(false);
    const pickerRef = useRef<HTMLDivElement>(null);
    const [showFilters, setShowFilters] = useState(false);
    const [filters, setFilters] = useState<Record<string, string>>({});
    const [sortCol, setSortCol] = useState<keyof StockRow>('total_market');
    const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');

    // Resize drag state — stored in ref to avoid re-renders during drag
    const dragRef = useRef<{ colId: string; startX: number; startWidth: number } | null>(null);

    // Persist prefs whenever they change
    useEffect(() => {
        savePrefs({ visible: [...visible], columnOrder, columnWidths });
    }, [visible, columnOrder, columnWidths]);

    useEffect(() => { fetchData(); }, []);

    useEffect(() => {
        const handler = () => fetchData();
        window.addEventListener('portfolio-synced', handler);
        return () => window.removeEventListener('portfolio-synced', handler);
    }, []);


    // Close picker on outside click
    useEffect(() => {
        function handle(e: MouseEvent) {
            if (pickerRef.current && !pickerRef.current.contains(e.target as Node))
                setPickerOpen(false);
        }
        document.addEventListener('mousedown', handle);
        return () => document.removeEventListener('mousedown', handle);
    }, []);

    // Global mouse handlers for column resize
    useEffect(() => {
        function onMouseMove(e: MouseEvent) {
            if (!dragRef.current) return;
            const { colId, startX, startWidth } = dragRef.current;
            const newWidth = Math.max(40, startWidth + (e.clientX - startX));
            setColumnWidths(prev => ({ ...prev, [colId]: newWidth }));
        }
        function onMouseUp() {
            if (dragRef.current) dragRef.current = null;
            document.body.style.cursor = '';
            document.body.style.userSelect = '';
        }
        document.addEventListener('mousemove', onMouseMove);
        document.addEventListener('mouseup', onMouseUp);
        return () => {
            document.removeEventListener('mousemove', onMouseMove);
            document.removeEventListener('mouseup', onMouseUp);
        };
    }, []);

    const startResize = useCallback((e: React.MouseEvent, colId: string) => {
        e.preventDefault();
        e.stopPropagation();
        dragRef.current = { colId, startX: e.clientX, startWidth: columnWidths[colId] ?? DEFAULT_WIDTHS[colId] ?? 100 };
        document.body.style.cursor = 'col-resize';
        document.body.style.userSelect = 'none';
    }, [columnWidths]);

    async function syncAndRefresh() {
        setLoading(true);
        setError(null);
        try {
            await syncAndRefreshPortfolio();
        } catch (e) {
            console.error('Unified sync failed', e);
        } finally {
            await fetchData();
            window.dispatchEvent(new CustomEvent('portfolio-synced'));
        }
    }

    const toggleWatch = useCallback(async (e: React.MouseEvent, ticker: string, currentlyWatched: boolean) => {
        e.stopPropagation();
        try {
            if (currentlyWatched) {
                await removeFromWatchlist(ticker);
            } else {
                await addToWatchlist(ticker);
            }
            fetchData();
        } catch (err) {
            console.error('Error toggling watchlist:', err);
        }
    }, []);

    async function fetchData() {
        setLoading(true);
        setError(null);
        try {
            // Fetch portfolio first (allItems needed for heatmap body); run all others in parallel
            const portRes = await fetch('/api/portfolio');
            if (!portRes.ok) throw new Error('Failed to fetch portfolio');
            const portConfig = await portRes.json() as { items?: any[] };
            const allItems = portConfig.items ?? [];

            const [weightsRes, heatmapRes, thesisRes, pData, ahRes, rvRes] = await Promise.all([
                fetch('/api/portfolio/weights'),
                fetch('/api/portfolio-heatmap', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ items: allItems }),
                }),
                fetch('/api/theses/target-portfolio').catch(() => null),
                fetchAllProjections().catch(() => []),
                fetch('/api/screener/all-holdings').catch(() => null),
                fetch('/api/docs/latest-review-data').catch(() => null),
            ]);

            if (!heatmapRes.ok) throw new Error('Failed to fetch heatmap data');
            const weightsMap: Record<string, number> = weightsRes.ok ? await weightsRes.json() : {};
            const heatmapData = await heatmapRes.json() as HeatmapResponse;

            let strategyMap: Record<string, string> = {};
            if (thesisRes?.ok) {
                const thesis = await thesisRes.json() as { holdings?: { ticker: string; subStrategyId?: string }[] };
                for (const h of thesis.holdings ?? []) {
                    if (h.ticker && h.subStrategyId) strategyMap[h.ticker] = h.subStrategyId;
                }
            }

            const aiOnly = (pData as any[]).filter((p: any) => p.source === 'AI_AGENT');
            const latest = aiOnly.reduce((acc: any, curr: any) => {
                if (!acc[curr.ticker] || new Date(curr.savedAt) > new Date(acc[curr.ticker].savedAt)) acc[curr.ticker] = curr;
                return acc;
            }, {});
            const aiProjs: any[] = Object.values(latest);

            let actionsMap: Record<string, any> = {};
            let reviewMap: Record<string, any> = {};
            const watched = new Set<string>();
            if (ahRes?.ok) {
                const ahData = await ahRes.json();
                for (const h of ahData) {
                    actionsMap[h.ticker] = h.action;
                    if (h.isWatched) {
                        watched.add(h.ticker);
                    }
                }
            }
            setWatchedTickers(watched);
            if (rvRes?.ok) {
                const rvData = await rvRes.json();
                for (const h of [...(rvData.holdings ?? []), ...(rvData.holdingsUnchanged ?? [])]) reviewMap[h.ticker] = h;
            }

            const projMap: Record<string, any> = aiProjs.reduce((m, p) => { m[p.ticker] = p; return m; }, {});

            const totalValue = heatmapData.total_value ?? 0;
            const stocksWithPct: StockRow[] = heatmapData.stocks.map(s => {
                const p = projMap[s.symbol];
                const rev = reviewMap[s.symbol];
                const fairValue = p?.aiThesis?.fairValue ?? null;
                const base = p?.scenarios?.base;
                // Use heatmap-derived weight (live prices) — avoids stale portfolio.json prices
                const hmPct = (s.total_market != null && totalValue > 0)
                    ? (s.total_market / totalValue) * 100
                    : null;
                const wPct = weightsMap[s.symbol];
                const currentPct = (hmPct != null) ? hmPct : (wPct != null && wPct > 0 ? wPct : null);

                return {
                    ...s,
                    currentPct,
                    subStrategyId: strategyMap[s.symbol] ?? null,
                    action: actionsMap[s.symbol] ?? 'WATCHLIST',
                    recommendedPct: rev?.recommendedTarget ?? null,
                    rationale: rev?.rationale ?? null,
                    fairValue: fairValue,
                    gainLoss: (fairValue && s.currentPrice) ? fairValue - s.currentPrice : null,
                    upside: (fairValue && s.currentPrice) ? ((fairValue - s.currentPrice) / s.currentPrice) * 100 : null,
                    growth: base?.growthRate ?? null,
                    ruleOf40: base ? base.growthRate + base.netMargin : null,
                    model: p?.aiThesis?.model ?? '—',
                    bear: p?.scenarios?.bear?.scenarioPrice ?? null,
                    base: base?.scenarioPrice ?? null,
                    bull: p?.scenarios?.bull?.scenarioPrice ?? null,
                    qualityMultiplier: base?.qualityMultiplier ?? null,
                    lastAnalyzed: p?.savedAt ?? null,
                };
            });

            setData({ stocks: stocksWithPct, total_value: heatmapData.total_value, total_value_usd: heatmapData.total_value_usd, total_value_cad: heatmapData.total_value_cad });
            if (heatmapData.price_source) setPriceSource(heatmapData.price_source);
            if (heatmapData.refreshed_at) setLastRefreshedAt(new Date(heatmapData.refreshed_at));
            if (heatmapData.exchange_rate && heatmapData.exchange_rate > 0) setExchangeRate(heatmapData.exchange_rate);
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : 'Failed to load');
        } finally {
            setLoading(false);
        }
    }

    function handleSort(col: keyof StockRow) {
        if (sortCol === col) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
        else { setSortCol(col); setSortDir('desc'); }
    }

    function toggleCol(id: string) {
        setVisible(prev => {
            const next = new Set(prev);
            if (next.has(id)) next.delete(id); else next.add(id);
            return next;
        });
    }

    function moveColumn(id: string, direction: 'up' | 'down') {
        setColumnOrder(prev => {
            const idx = prev.indexOf(id);
            if (idx === -1) return prev;
            const nextIdx = direction === 'up' ? idx - 1 : idx + 1;
            if (nextIdx < 0 || nextIdx >= prev.length) return prev;
            const next = [...prev];
            [next[idx], next[nextIdx]] = [next[nextIdx], next[idx]];
            return next;
        });
    }

    const orderedCols = columnOrder.map(id => COLUMNS.find(c => c.id === id)!).filter(Boolean);
    const visibleCols = orderedCols.filter(c => visible.has(c.id));

    const filteredRows = (data?.stocks ?? []).filter(row =>
        Object.entries(filters).every(([colId, filterVal]) => {
            if (!filterVal) return true;
            const val = row[colId as keyof StockRow];
            return val != null && String(val).toLowerCase().includes(filterVal.toLowerCase());
        })
    );
    const rows = sortRows(filteredRows, sortCol, sortDir);

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
        <>
        <div className="flex flex-col bg-zinc-900 rounded-lg border border-zinc-800">

            {/* Header bar */}
            <div className="flex items-center justify-between px-4 py-2.5 bg-zinc-900 border-b border-zinc-800">
                <div className="flex items-center gap-4">
                    <span className="text-white font-semibold text-sm">Portfolio Table</span>
                    <span className="text-zinc-500 text-xs">{rows.length} positions</span>
                </div>
                <div className="flex items-center gap-3">
                    <div className="flex items-baseline gap-2 mr-1">
                        <span className="text-white text-sm font-bold">${Math.round(data.total_value_usd ?? data.total_value).toLocaleString()}</span>
                        <span className="text-zinc-500 text-xs font-medium">USD</span>
                        <span className="text-zinc-600 text-xs">/</span>
                        <span className="text-zinc-400 text-sm font-semibold">${(data.total_value_cad ?? Math.round((data.total_value_usd ?? data.total_value) * exchangeRate)).toLocaleString()}</span>
                        <span className="text-zinc-500 text-xs font-medium">CAD</span>
                    </div>

                    <button
                        onClick={() => setShowFilters(s => !s)}
                        className={`flex items-center gap-1.5 px-3 py-1 rounded text-xs transition-colors ${showFilters ? 'bg-amber-500/20 text-amber-400 border border-amber-500/50' : 'bg-zinc-800 text-zinc-300 hover:bg-zinc-700'}`}
                    >
                        <Filter size={13} /> Filter
                    </button>

                    <div className="relative" ref={pickerRef}>
                        <button
                            onClick={() => setPickerOpen(o => !o)}
                            className="flex items-center gap-1.5 px-3 py-1 bg-zinc-800 text-zinc-300 rounded text-xs hover:bg-zinc-700 transition-colors"
                        >
                            <SlidersHorizontal size={13} /> Columns
                        </button>
                        {pickerOpen && (
                            <div className="absolute right-0 top-8 z-50 w-64 bg-zinc-800 border border-zinc-700 rounded-lg shadow-2xl p-2 max-h-96 overflow-y-auto">
                                <div className="text-[10px] text-zinc-500 uppercase font-bold px-2 pb-1 mb-1 border-b border-zinc-700">
                                    Configure Columns
                                </div>
                                {columnOrder.map((colId, idx) => {
                                    const col = COLUMNS.find(c => c.id === colId)!;
                                    return (
                                        <div key={colId} className="flex items-center justify-between px-2 py-1.5 rounded hover:bg-zinc-700 group">
                                            <label className="flex items-center gap-2 cursor-pointer flex-1">
                                                <input
                                                    type="checkbox"
                                                    disabled={col.always}
                                                    checked={visible.has(col.id)}
                                                    onChange={() => toggleCol(col.id)}
                                                    className="accent-amber-500 w-3.5 h-3.5"
                                                />
                                                <span className={`text-xs ${visible.has(col.id) ? 'text-zinc-200' : 'text-zinc-500'}`}>{col.label}</span>
                                            </label>
                                            <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                                <button onClick={() => moveColumn(colId, 'up')} disabled={idx === 0} className="p-1 hover:bg-zinc-600 rounded text-zinc-400 disabled:text-zinc-700">
                                                    <ArrowUp size={12} />
                                                </button>
                                                <button onClick={() => moveColumn(colId, 'down')} disabled={idx === columnOrder.length - 1} className="p-1 hover:bg-zinc-600 rounded text-zinc-400 disabled:text-zinc-700">
                                                    <ArrowDown size={12} />
                                                </button>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        )}
                    </div>

                    <button onClick={syncAndRefresh} className="px-3 py-1 bg-zinc-800 text-zinc-300 rounded text-xs hover:bg-zinc-700 transition-colors">
                        ↻ Refresh
                    </button>
                    <PriceSourceBadge priceSource={priceSource} lastRefreshedAt={lastRefreshedAt} />
                </div>
            </div>

            {/* Table */}
            <div className="overflow-auto rounded-b-lg">
                <table className="text-sm border-collapse" style={{ tableLayout: 'fixed', width: '100%', minWidth: visibleCols.reduce((sum, c) => sum + (columnWidths[c.id] ?? DEFAULT_WIDTHS[c.id] ?? 100), 0) + 195 }}>
                    <colgroup>
                        {visibleCols.map(col => (
                            <col key={col.id} style={{ width: columnWidths[col.id] ?? DEFAULT_WIDTHS[col.id] ?? 100 }} />
                        ))}
                        <col style={{ width: 195 }} />
                    </colgroup>
                    <thead>
                        <tr className="bg-zinc-800/60 border-b border-zinc-700">
                            {visibleCols.map(col => {
                                const active = sortCol === col.id;
                                return (
                                    <th
                                        key={col.id}
                                        onClick={() => handleSort(col.id)}
                                        className={`relative px-3 py-2.5 font-semibold text-xs uppercase tracking-wider cursor-pointer select-none whitespace-nowrap overflow-hidden
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
                                        {/* Resize handle */}
                                        <div
                                            className="absolute right-0 top-0 bottom-0 w-[5px] cursor-col-resize hover:bg-amber-500/40 active:bg-amber-500/70 transition-colors z-10"
                                            onMouseDown={e => startResize(e, col.id)}
                                            onClick={e => e.stopPropagation()}
                                        />
                                    </th>
                                );
                            })}
                            <th className="px-2 py-2.5 text-right text-xs font-semibold uppercase tracking-wider text-zinc-500">Actions</th>
                        </tr>
                        {showFilters && (
                            <tr className="bg-zinc-800/40 border-b border-zinc-700">
                                {visibleCols.map(col => (
                                    <th key={`filter-${col.id}`} className="px-2 py-1.5">
                                        <input
                                            type="text"
                                            placeholder={`Filter…`}
                                            value={filters[col.id] ?? ''}
                                            onChange={e => setFilters(prev => ({ ...prev, [col.id]: e.target.value }))}
                                            className="w-full bg-zinc-900 border border-zinc-700 rounded px-2 py-1 text-[11px] text-zinc-300 focus:outline-none focus:border-amber-500/50 placeholder:text-zinc-600"
                                            onClick={e => e.stopPropagation()}
                                        />
                                    </th>
                                ))}
                                <th className="px-2 py-1.5" />
                            </tr>
                        )}
                    </thead>
                    <tbody>
                        {rows.map((row, i) => {
                            const suggestedShares = computeSuggestedShares(row.currentPct, row.recommendedPct, row.currentPrice, data.total_value);
                            return (
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
                                        const isPctCol = col.id === 'currentPct';
                                        const pctBg = isPctCol && numVal != null
                                            ? `rgba(34,197,94,${Math.min(numVal / 15, 1) * 0.55 + (numVal > 0 ? 0.08 : 0)})`
                                            : undefined;
                                        return (
                                            <td
                                                key={col.id}
                                                className={`px-3 py-2.5 whitespace-nowrap overflow-hidden text-ellipsis ${col.align === 'right' ? 'text-right' : 'text-left'}`}
                                                style={col.isChange ? { backgroundColor: changeBg(numVal) } : isPctCol ? { backgroundColor: pctBg } : undefined}
                                            >
                                                {col.id === 'symbol' ? (
                                                     <div className="flex items-center gap-1.5">
                                                         <button
                                                             onClick={(e) => toggleWatch(e, row.symbol, watchedTickers.has(row.symbol))}
                                                             className="text-slate-600 hover:text-yellow-400 active:scale-95 transition-all p-0.5 focus:outline-none"
                                                             title={watchedTickers.has(row.symbol) ? "Remove from watchlist" : "Add to watchlist"}
                                                         >
                                                             <Star
                                                                 size={13}
                                                                 className={watchedTickers.has(row.symbol) ? "fill-yellow-400 text-yellow-400" : "text-zinc-600"}
                                                             />
                                                         </button>
                                                         <span className="font-bold text-white">{val}</span>
                                                     </div>
                                                ) : col.id === 'name' ? (
                                                    <span className="text-zinc-300 text-xs">{val}</span>
                                                ) : col.isChange ? (
                                                    <span className="font-semibold text-xs text-white">{col.format(val)}</span>
                                                ) : (
                                                    <span className="text-zinc-300">{col.format(val)}</span>
                                                )}
                                            </td>
                                        );
                                    })}
                                    {/* Actions column */}
                                    <td className="px-2 py-1.5 whitespace-nowrap" onClick={e => e.stopPropagation()}>
                                        <div className="flex items-center gap-1 justify-end">
                                            <TradeButtons ticker={row.symbol} shares={suggestedShares} size="sm" />
                                            <button
                                                onClick={() => setLogModal({ ticker: row.symbol })}
                                                title="Log a trade to journal"
                                                className="px-2 py-0.5 text-[10px] font-bold rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-400 hover:text-amber-400 transition-colors"
                                            >
                                                Log
                                            </button>
                                            <button
                                                onClick={() => navigate(`/analysis?ticker=${row.symbol}`)}
                                                title="Analyze in Stock Analysis"
                                                className="px-2 py-0.5 text-[10px] font-bold rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-400 hover:text-white transition-colors"
                                            >
                                                Analyze
                                            </button>
                                        </div>
                                    </td>
                                </tr>
                            );
                        })}
                    </tbody>

                    <tfoot>
                        <tr className="border-t-2 border-zinc-700 bg-zinc-800/40">
                            {visibleCols.map((col, i) => {
                                let content = '';
                                if (col.id === 'symbol') content = 'TOTAL';
                                else if (col.id === 'total_market') content = fmtDollar(data.total_value);
                                else if (col.id === 'total_book') {
                                    const tb = rows.reduce((s, r) => r.total_book != null ? s + r.total_book : s, 0);
                                    content = tb > 0 ? fmtDollar(tb) : '—';
                                } else if (col.id === 'currentPct') {
                                    const tot = rows.reduce((s, r) => r.currentPct != null ? s + r.currentPct : s, 0);
                                    content = tot > 0 ? `${tot.toFixed(2)}%` : '—';
                                }
                                return (
                                    <td key={col.id} className={`px-3 py-2 text-xs font-bold overflow-hidden text-ellipsis ${col.align === 'right' ? 'text-right' : 'text-left'} ${i === 0 ? 'text-zinc-400' : 'text-zinc-300'}`}>
                                        {content}
                                    </td>
                                );
                            })}
                            <td className="px-2 py-2" />
                        </tr>
                    </tfoot>
                </table>
            </div>
        </div>

        {logModal && (
            <TradeLogModal
                ticker={logModal.ticker}
                onClose={() => setLogModal(null)}
            />
        )}
        </>
    );
}
