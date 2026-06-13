/**
 * ScreenerTable.tsx (React Component)
 * =====================================
 *
 * Purpose:
 *     The primary data grid for the investment screener, featuring sorting, 
 *     filtering, and high-density financial metrics.
 *
 * Layer: Frontend / UI / Components
 *
 * Usage Examples:
 *     <ScreenerTable />
 *
 * Key Functions:
 *     - fetchData() - Pulls all projections and portfolio holdings from the backend
 *     - startResize() - Handles column width resizing logic
 *     - rows (memo) - Computes sorted and filtered data for the grid
 */
import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { SlidersHorizontal, ChevronUp, ChevronDown, ChevronsUpDown, Filter, ArrowUp, ArrowDown, BrainCircuit, ExternalLink, Activity, Star } from 'lucide-react';
import { type Projection, addToWatchlist, removeFromWatchlist } from '../services/api';
import { TradeButtons } from './TradeButtons';
import { safeNum, fmtPct, fmtDollar, fmtPrice, changeBgUpside, sortByColumn } from '../utils/formatters';
import { getActionBadgeClass } from '../utils/actionColors';

// ─── Types ────────────────────────────────────────────────────────────────────

interface ScreenerRow {
    symbol: string;
    name: string;
    model: string;
    action: string;
    portfolioRationale: string | null;
    currentPct: number | null;
    recommendedPct: number | null;
    rationale: string | null;
    fairValue: number | null;
    currentPrice: number;
    gainLoss: number | null;
    upside: number | null;
    growth: number | null;
    margin: number | null;
    ruleOf40: number | null;
    bear: number | null;
    base: number | null;
    bull: number | null;
    lastAnalyzed: string;
    qualityMultiplier: number | null;
    rowKind: 'projection' | 'holding'; // 'holding' = no DCF projection yet
    subStrategyId: string | null;
    change_1d: number | null;
    change_overall: number | null;
    sector: string | null;
    shares: number | null;
    book_price: number | null;
    total_book: number | null;
    total_market: number | null;
    change_1w: number | null;
    change_1m: number | null;
    change_ytd: number | null;
    change_1y: number | null;
    isWatched: boolean;
}

// ─── Column Definitions ───────────────────────────────────────────────────────

interface ColDef {
    id: keyof ScreenerRow;
    label: string;
    always?: boolean;
    isChange?: boolean;
    defaultOn?: boolean;
    align?: 'left' | 'right';
    format: (v: any) => string;
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
    symbol: 80, action: 185, fairValue: 95, currentPrice: 80, gainLoss: 85,
    change_1d: 65, change_overall: 80, change_1w: 65, change_1m: 65, change_ytd: 65, change_1y: 65, sector: 115, shares: 60, book_price: 72, total_book: 80, total_market: 80, 
    upside: 85, ruleOf40: 70, growth: 80, model: 130, base: 80,
    bear: 80, bull: 80, qualityMultiplier: 80, subStrategyId: 140, lastAnalyzed: 90,
    currentPct: 90, recommendedPct: 85, rationale: 260,
};

// ─── Persistence ──────────────────────────────────────────────────────────────

const STORAGE_KEY = 'ai-screener-table-prefs-v3';

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

const changeBg = changeBgUpside;
const sortRows = (rows: ScreenerRow[], col: keyof ScreenerRow, dir: 'asc' | 'desc') => sortByColumn(rows, col, dir);

// ─── Component ────────────────────────────────────────────────────────────────

export default function ScreenerTable() {
    const navigate = useNavigate();
    const [projections, setProjections] = useState<Projection[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Load persisted prefs
    const [visible, setVisible] = useState<Set<string>>(new Set());
    const [columnOrder, setColumnOrder] = useState<string[]>([]);
    const [columnWidths, setColumnWidths] = useState<Record<string, number>>({});

    const [pickerOpen, setPickerOpen] = useState(false);
    const pickerRef = useRef<HTMLDivElement>(null);
    const [showFilters, setShowFilters] = useState(false);
    const [filters, setFilters] = useState<Record<string, string>>({});
    const [sortCol, setSortCol] = useState<keyof ScreenerRow>('upside');
    const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');

    const dragRef = useRef<{ colId: string; startX: number; startWidth: number } | null>(null);

    // Initialize Prefs
    useEffect(() => {
        const prefs = loadPrefs();
        const defaultVisible = new Set(COLUMNS.filter(c => c.always || c.defaultOn).map(c => c.id));
        if (prefs) {
            // Filter out stale IDs no longer in COLUMNS (schema changes between versions)
            const validIds = new Set<string>(COLUMNS.map(c => c.id as string));
            const filteredOrder = prefs.columnOrder.filter(id => validIds.has(id)) as (keyof ScreenerRow)[];
            // Merge: add any new defaultOn columns not in the saved set
            const merged = new Set(prefs.visible.filter(id => validIds.has(id)));
            for (const id of defaultVisible) {
                if (!filteredOrder.includes(id)) merged.add(id); // brand-new column
            }
            setVisible(merged);
            // Append any new columns to the end of columnOrder
            const knownIds = new Set(filteredOrder);
            const newCols = COLUMNS.map(c => c.id).filter(id => !knownIds.has(id));
            setColumnOrder([...filteredOrder, ...newCols]);
        } else {
            setVisible(defaultVisible);
            setColumnOrder(COLUMNS.map(c => c.id));
        }
        setColumnWidths({ ...DEFAULT_WIDTHS, ...(prefs?.columnWidths ?? {}) });
    }, []);

    // Persist prefs
    useEffect(() => {
        if (visible.size > 0) {
            savePrefs({ visible: [...visible], columnOrder, columnWidths });
        }
    }, [visible, columnOrder, columnWidths]);

    const [portfolioWeights, setPortfolioWeights] = useState<Record<string, { actualPct: number; targetPct: number }>>({});
    const [allPortfolioWeights, setAllPortfolioWeights] = useState<Record<string, number>>({});
    const [reviewRecommendations, setReviewRecommendations] = useState<Record<string, { target: number; rationale: string; actualPct: number; action?: string }>>({});
    const [allHoldings, setAllHoldings] = useState<any[]>([]);
    const [heatmapMap, setHeatmapMap] = useState<Record<string, any>>({});
    const allHoldingsMap = useMemo(() => allHoldings.reduce((m, h) => { m[h.ticker] = h; return m; }, {} as Record<string, any>), [allHoldings]);

    const fetchData = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const [healthData, weightsData, reviewData, holdingsData, portData, allProjData] = await Promise.all([
                fetch('/api/theses/target-portfolio/health').then(r => r.ok ? r.json() : null).catch(() => null),
                fetch('/api/portfolio/weights').then(r => r.ok ? r.json() : null).catch(() => null),
                fetch('/api/docs/latest-review-data').then(r => r.ok ? r.json() : null).catch(() => null),
                fetch('/api/screener/all-holdings').then(r => r.ok ? r.json() : null).catch(() => null),
                fetch('/api/portfolio').then(r => r.ok ? r.json() : null).catch(() => null),
                fetch('/api/projections').then(r => r.ok ? r.json() : null).catch(() => null),
            ]);

            if (allProjData) {
                const aiOnly = (allProjData as Projection[]).filter(p => p.source === 'AI_AGENT');
                const latestByTicker = aiOnly.reduce((acc, curr) => {
                    if (!acc[curr.ticker] || new Date(curr.savedAt) > new Date(acc[curr.ticker].savedAt)) {
                        acc[curr.ticker] = curr;
                    }
                    return acc;
                }, {} as Record<string, Projection>);
                setProjections(Object.values(latestByTicker));
            }

            if (healthData) {
                const map: Record<string, { actualPct: number; targetPct: number }> = {};
                for (const h of healthData.holdingHealth ?? []) {
                    map[h.ticker] = { actualPct: h.actualPct ?? 0, targetPct: h.targetPct ?? 0 };
                }
                setPortfolioWeights(map);
            }
            if (weightsData) setAllPortfolioWeights(weightsData);
            if (reviewData) {
                const map: Record<string, { target: number; rationale: string; actualPct: number }> = {};
                for (const h of [...(reviewData.holdings ?? []), ...(reviewData.holdingsUnchanged ?? [])]) {
                    map[h.ticker] = {
                        target: h.recommendedTarget,
                        rationale: h.rationale ?? '',
                        actualPct: h.actualPct ?? null,
                    };
                }
                setReviewRecommendations(map);
            }
            if (holdingsData) setAllHoldings(holdingsData);

            const portfolioItems: any[] = portData?.items ?? [];
            const coveredSymbols = new Set(portfolioItems.map((i: any) => (i.symbol as string).toUpperCase()));

            const thesisExtras = (holdingsData ?? [])
                .filter((h: any) => !coveredSymbols.has((h.ticker as string).toUpperCase()))
                .map((h: any) => { coveredSymbols.add((h.ticker as string).toUpperCase()); return { symbol: h.ticker, shares: 0 }; });

            const projTickers = (allProjData ?? [])
                .filter((p: any) => p.source === 'AI_AGENT' && !coveredSymbols.has((p.ticker as string).toUpperCase()))
                .map((p: any) => { coveredSymbols.add((p.ticker as string).toUpperCase()); return { symbol: p.ticker, shares: 0 }; });

            const allItems = [...portfolioItems, ...thesisExtras, ...projTickers];

            if (allItems.length > 0) {
                const heatmapData = await fetch('/api/portfolio-heatmap', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ items: allItems }),
                }).then(r => r.ok ? r.json() : null).catch(() => null);

                if (heatmapData?.stocks) {
                    const map: Record<string, any> = {};
                    for (const s of heatmapData.stocks) map[s.symbol] = s;
                    setHeatmapMap(map);
                }
            }
        } catch (err: any) {
            setError(err.message || 'Failed to load screener data');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { fetchData(); }, [fetchData]);

    useEffect(() => {
        window.addEventListener('portfolio-synced', fetchData);
        return () => window.removeEventListener('portfolio-synced', fetchData);
    }, [fetchData]);

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
    }, [fetchData]);

    // Close picker on outside click
    useEffect(() => {
        function handle(e: MouseEvent) {
            if (pickerRef.current && !pickerRef.current.contains(e.target as Node))
                setPickerOpen(false);
        }
        document.addEventListener('mousedown', handle);
        return () => document.removeEventListener('mousedown', handle);
    }, []);

    // Resize handlers
    useEffect(() => {
        function onMouseMove(e: MouseEvent) {
            if (!dragRef.current) return;
            const { colId, startX, startWidth } = dragRef.current;
            const newWidth = Math.max(40, startWidth + (e.clientX - startX));
            setColumnWidths(prev => ({ ...prev, [colId]: newWidth }));
        }
        function onMouseUp() {
            dragRef.current = null;
            document.body.style.cursor = '';
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
        dragRef.current = { colId, startX: e.clientX, startWidth: columnWidths[colId] ?? DEFAULT_WIDTHS[colId] };
        document.body.style.cursor = 'col-resize';
    }, [columnWidths]);

    // Map Projections to Table Rows
    const rows = useMemo(() => {
        // --- Projection rows (have DCF analysis) ---
        const projectionRows: ScreenerRow[] = projections.map(p => {
            const thesis = p.aiThesis;
            const base = p.scenarios?.base;
            const bear = p.scenarios?.bear;
            const bull = p.scenarios?.bull;

            const currentPrice = p.snapshot?.price ?? 0;
            const fairValue = thesis?.fairValue ?? null;
            const upside = (fairValue && currentPrice) ? ((fairValue - currentPrice) / currentPrice) * 100 : null;
            const gainLoss = (fairValue && currentPrice) ? (fairValue - currentPrice) : null;

            const growth = base?.growthRate ?? null;
            const margin = base?.netMargin ?? null;

            const rev = reviewRecommendations[p.ticker];
            const health = portfolioWeights[p.ticker];
            const currentPct = allPortfolioWeights[p.ticker] ?? health?.actualPct ?? rev?.actualPct ?? null;
            const recommendedPct = health?.targetPct ?? null;
            // Action from backend Python — single source of truth
            const action = allHoldingsMap[p.ticker]?.action ?? 'WATCHLIST';

            return {
                symbol: p.ticker,
                name: p.name,
                model: thesis?.model || '—',
                action,
                portfolioRationale: (p as any).analyticsLog?.portfolioRationale ?? null,
                fairValue,
                currentPrice,
                gainLoss,
                upside,
                growth,
                margin,
                ruleOf40: (growth != null && margin != null) ? growth + margin : null,
                bear: bear?.scenarioPrice || null,
                base: base?.scenarioPrice || null,
                bull: bull?.scenarioPrice || null,
                qualityMultiplier: base?.qualityMultiplier ?? null,
                lastAnalyzed: p.savedAt,
                currentPct,
                recommendedPct,
                rationale: rev?.rationale ?? null,
                rowKind: 'projection',
                subStrategyId: allHoldingsMap[p.ticker]?.subStrategyId ?? null,
                change_1d: heatmapMap[p.ticker]?.change_1d ?? null,
                change_overall: heatmapMap[p.ticker]?.change_overall ?? null,
                sector: heatmapMap[p.ticker]?.sector ?? null,
                shares: heatmapMap[p.ticker]?.shares ?? null,
                book_price: heatmapMap[p.ticker]?.book_price ?? null,
                total_book: heatmapMap[p.ticker]?.total_book ?? null,
                total_market: heatmapMap[p.ticker]?.total_market ?? null,
                change_1w: heatmapMap[p.ticker]?.change_1w ?? null,
                change_1m: heatmapMap[p.ticker]?.change_1m ?? null,
                change_ytd: heatmapMap[p.ticker]?.change_ytd ?? null,
                change_1y: heatmapMap[p.ticker]?.change_1y ?? null,
                isWatched: allHoldingsMap[p.ticker]?.isWatched ?? false,
            };
        });

        // --- Holding stub rows (in thesis/portfolio but no DCF projection yet) ---
        const projectionTickers = new Set(projections.map(p => p.ticker));
        const holdingRows: ScreenerRow[] = allHoldings
            .filter(h => !projectionTickers.has(h.ticker))
            .map(h => {
                const hPct = h.actualPct ?? allPortfolioWeights[h.ticker] ?? null;
                return {
                    symbol: h.ticker,
                    name: h.name,
                    model: '—',
                    action: h.action,  // from backend Python
                    portfolioRationale: null,
                    fairValue: null,
                    currentPrice: h.currentPrice ?? 0,
                    gainLoss: null,
                    upside: null,
                    growth: null,
                    margin: null,
                    ruleOf40: null,
                    bear: null,
                    base: null,
                    bull: null,
                    qualityMultiplier: null,
                    lastAnalyzed: '',
                    currentPct: hPct,
                    recommendedPct: h.targetPct ?? null,
                    rationale: h.rationale ?? null,
                    rowKind: 'holding',
                    subStrategyId: h.subStrategyId ?? null,
                    change_1d: heatmapMap[h.ticker]?.change_1d ?? null,
                    change_overall: heatmapMap[h.ticker]?.change_overall ?? null,
                    sector: heatmapMap[h.ticker]?.sector ?? null,
                    shares: heatmapMap[h.ticker]?.shares ?? null,
                    book_price: heatmapMap[h.ticker]?.book_price ?? null,
                    total_book: heatmapMap[h.ticker]?.total_book ?? null,
                    total_market: heatmapMap[h.ticker]?.total_market ?? null,
                    change_1w: heatmapMap[h.ticker]?.change_1w ?? null,
                    change_1m: heatmapMap[h.ticker]?.change_1m ?? null,
                    change_ytd: heatmapMap[h.ticker]?.change_ytd ?? null,
                    change_1y: heatmapMap[h.ticker]?.change_1y ?? null,
                    isWatched: h.isWatched ?? false,
                };
            });

        return [...projectionRows, ...holdingRows];
    }, [projections, portfolioWeights, allPortfolioWeights, reviewRecommendations, allHoldings, allHoldingsMap, heatmapMap]);

    const filteredRows = rows.filter(row =>
        Object.entries(filters).every(([colId, filterVal]) => {
            if (!filterVal) return true;
            const val = row[colId as keyof ScreenerRow];
            return val != null && String(val).toLowerCase().includes(filterVal.toLowerCase());
        })
    );

    const sortedRows = sortRows(filteredRows, sortCol, sortDir);

    const visibleCols = columnOrder.map(id => COLUMNS.find(c => c.id === id)!).filter(c => c && visible.has(c.id));

    // Column totals for % allocation check
    const totalCurrentPct  = sortedRows.reduce((s, r) => s + (r.currentPct ?? 0), 0);
    const totalRecommendedPct = sortedRows.reduce((s, r) => s + (r.recommendedPct ?? 0), 0);

    // Heatmap background for % allocation cells
    function pctHeatBg(pct: number | null, type: 'current' | 'target'): string | undefined {
        if (!pct || pct <= 0) return undefined;
        const intensity = Math.min(pct / 12, 1); // 12%+ = full intensity
        return type === 'current'
            ? `rgba(16, 185, 129, ${intensity * 0.32})`   // emerald for current
            : `rgba(99, 102, 241, ${intensity * 0.32})`;  // indigo for target
    }

    if (loading) return (
        <div className="flex flex-col items-center justify-center h-64 bg-slate-900/50 rounded-xl border border-slate-800 animate-pulse">
            <BrainCircuit size={32} className="text-indigo-500 mb-4 animate-bounce" />
            <span className="text-slate-400 font-medium">Aggregating AI Insights...</span>
        </div>
    );

    if (error) return (
        <div className="bg-red-500/10 border border-red-500/30 text-red-400 p-6 rounded-xl text-center">
            <div className="font-bold mb-2">Aggregation Failed</div>
            <div className="text-sm mb-4">{error}</div>
            <button onClick={fetchData} className="px-4 py-2 bg-red-500/20 hover:bg-red-500/30 rounded-lg text-sm font-bold transition-colors">Retry</button>
        </div>
    );

    return (
        <>
        <div className="flex flex-col bg-slate-900/40 rounded-xl border border-slate-800 backdrop-blur-md h-full">
            {/* Header bar */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800 bg-slate-900/60">
                <div className="flex items-center gap-4">
                    <div className="p-2 bg-indigo-500/10 rounded-lg text-indigo-400">
                        <Activity size={18} />
                    </div>
                    <div>
                        <span className="text-white font-bold text-sm block">Intelligence Feed</span>
                        <span className="text-slate-500 text-[10px] uppercase font-black tracking-widest">{sortedRows.length} Deep Dives</span>
                    </div>
                </div>
                
                <div className="flex items-center gap-2">
                    <form onSubmit={async (e) => {
                        e.preventDefault();
                        const form = e.currentTarget;
                        const input = form.elements.namedItem('watchlistTicker') as HTMLInputElement;
                        const ticker = input.value.trim().toUpperCase();
                        if (ticker) {
                            try {
                                await addToWatchlist(ticker);
                                input.value = '';
                                fetchData();
                            } catch (err) {
                                console.error('Error adding to watchlist:', err);
                            }
                        }
                    }} className="flex items-center bg-slate-800 border border-slate-700 rounded-lg overflow-hidden focus-within:border-indigo-500/50 transition-all px-2 py-1 mr-2">
                        <input
                            name="watchlistTicker"
                            type="text"
                            placeholder="Add Ticker..."
                            className="bg-transparent text-xs font-bold text-white w-24 focus:outline-none placeholder:text-slate-500 px-1 py-0.5"
                        />
                        <button type="submit" className="text-indigo-400 hover:text-indigo-300 px-2 py-0.5 rounded text-xs font-black transition-colors">
                            + Add
                        </button>
                    </form>

                    <button
                        onClick={() => setShowFilters(s => !s)}
                        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${showFilters ? 'bg-indigo-500 text-white shadow-lg shadow-indigo-500/20' : 'bg-slate-800 text-slate-400 hover:text-white border border-slate-700'}`}
                    >
                        <Filter size={13} /> Filter
                    </button>

                    <div className="relative" ref={pickerRef}>
                        <button
                            onClick={() => setPickerOpen(o => !o)}
                            className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 text-slate-400 rounded-lg text-xs font-bold hover:text-white border border-slate-700 transition-all"
                        >
                            <SlidersHorizontal size={13} /> Columns
                        </button>
                        {pickerOpen && (
                            <div className="absolute right-0 top-10 z-50 w-64 bg-slate-900 border border-slate-700 rounded-xl shadow-2xl p-2 max-h-[70vh] overflow-y-auto backdrop-blur-xl">
                                <div className="text-[10px] text-slate-500 uppercase font-black tracking-[0.2em] px-3 py-2 mb-1 border-b border-slate-800">
                                    Display Metrics
                                </div>
                                {columnOrder.map((colId) => {
                                    const col = COLUMNS.find(c => c.id === colId)!;
                                    const isVisible = visible.has(colId);
                                    return (
                                        <div key={colId} className="flex items-center justify-between px-2 py-1.5 rounded-lg hover:bg-white/5 group">
                                            <label className="flex items-center gap-3 cursor-pointer flex-1 py-1">
                                                <input
                                                    type="checkbox"
                                                    disabled={col.always}
                                                    checked={isVisible}
                                                    onChange={() => setVisible(prev => {
                                                        const next = new Set(prev);
                                                        if (next.has(colId)) next.delete(colId); else next.add(colId);
                                                        return next;
                                                    })}
                                                    className="accent-indigo-500 w-4 h-4 rounded border-slate-700 bg-slate-800"
                                                />
                                                <span className={`text-xs font-bold ${isVisible ? 'text-white' : 'text-slate-600'}`}>{col.label}</span>
                                            </label>
                                            <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                                <button onClick={() => setColumnOrder(prev => {
                                                    const next = [...prev];
                                                    const i = next.indexOf(colId);
                                                    if (i > 0) [next[i], next[i-1]] = [next[i-1], next[i]];
                                                    return next;
                                                })} className="p-1 hover:bg-slate-700 rounded text-slate-400">
                                                    <ChevronUp size={14} />
                                                </button>
                                                <button onClick={() => setColumnOrder(prev => {
                                                    const next = [...prev];
                                                    const i = next.indexOf(colId);
                                                    if (i < next.length - 1) [next[i], next[i+1]] = [next[i+1], next[i]];
                                                    return next;
                                                })} className="p-1 hover:bg-slate-700 rounded text-slate-400">
                                                    <ChevronDown size={14} />
                                                </button>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        )}
                    </div>

                    <button onClick={fetchData} className="p-1.5 bg-slate-800 text-slate-400 rounded-lg hover:text-white border border-slate-700 transition-all">
                        <ChevronsUpDown size={16} className="rotate-90" />
                    </button>
                </div>
            </div>

            {/* Table */}
            <div className="flex-1 overflow-auto custom-scrollbar min-h-0 rounded-b-xl">
                <table className="text-sm border-collapse w-full" style={{ tableLayout: 'fixed' }}>
                    <colgroup>
                        {visibleCols.map(col => (
                            <col key={col.id} style={{ width: columnWidths[col.id] ?? 100 }} />
                        ))}
                    </colgroup>
                    <thead className="sticky top-0 z-20">
                        <tr className="bg-slate-900 border-b border-slate-800">
                            {visibleCols.map(col => {
                                const active = sortCol === col.id;
                                return (
                                    <th
                                        key={col.id}
                                        onClick={() => {
                                            if (sortCol === col.id) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
                                            else { setSortCol(col.id as any); setSortDir('desc'); }
                                        }}
                                        className={`relative px-4 py-3 font-black text-[10px] uppercase tracking-widest cursor-pointer select-none whitespace-nowrap
                                            ${col.align === 'right' ? 'text-right' : 'text-left'}
                                            ${active ? 'text-indigo-400 bg-indigo-500/5' : 'text-slate-500 hover:text-slate-200'}`}
                                    >
                                        <div className={`flex items-center gap-1.5 ${col.align === 'right' ? 'justify-end' : 'justify-start'}`}>
                                            {col.label}
                                            {active && (sortDir === 'asc' ? <ArrowUp size={10} /> : <ArrowDown size={10} />)}
                                        </div>
                                        <div
                                            className="absolute right-0 top-0 bottom-0 w-[5px] cursor-col-resize hover:bg-indigo-500/50 active:bg-indigo-500/80 transition-colors z-10"
                                            onMouseDown={e => startResize(e, col.id)}
                                            onClick={e => e.stopPropagation()}
                                        />
                                    </th>
                                );
                            })}
                        </tr>
                        {showFilters && (
                            <tr className="bg-slate-900/80 border-b border-slate-800 backdrop-blur-sm">
                                {visibleCols.map(col => (
                                    <th key={`filter-${col.id}`} className="px-3 py-2">
                                        <input
                                            type="text"
                                            placeholder={`Filter…`}
                                            value={filters[col.id] ?? ''}
                                            onChange={e => setFilters(prev => ({ ...prev, [col.id]: e.target.value }))}
                                            className="w-full bg-slate-950 border border-slate-800 rounded px-2 py-1.5 text-[10px] font-bold text-white focus:outline-none focus:border-indigo-500/50 placeholder:text-slate-700"
                                            onClick={e => e.stopPropagation()}
                                        />
                                    </th>
                                ))}
                            </tr>
                        )}
                    </thead>
                    <tbody>
                        {sortedRows.map((row, i) => (
                            <tr
                                key={row.symbol}
                                onClick={() => navigate(`/analysis?ticker=${row.symbol}`)}
                                className={`group border-b border-slate-800/50 cursor-pointer transition-all duration-200
                                    ${row.rowKind === 'holding' ? 'opacity-80' : ''}
                                    ${i % 2 === 0 ? 'bg-transparent' : 'bg-white/[0.02]'}
                                    hover:bg-indigo-500/10`}
                            >
                                {visibleCols.map(col => {
                                    const val = row[col.id];
                                    const numVal = typeof val === 'number' ? val : null;

                                    // For holding rows, DCF-specific columns show as pending
                                    const isDcfCol = ['fairValue','gainLoss','upside','ruleOf40','growth','model','bear','base','bull','qualityMultiplier','lastAnalyzed'].includes(col.id);
                                    if (row.rowKind === 'holding' && isDcfCol) {
                                        return (
                                            <td key={col.id} className={`px-4 py-4 whitespace-nowrap ${col.align === 'right' ? 'text-right' : 'text-left'}`}>
                                                {col.id === 'model' ? (
                                                    <span
                                                        className="inline-flex items-center px-2 py-0.5 rounded border text-[9px] font-black uppercase tracking-wider text-slate-600 border-slate-700/40 bg-slate-800/30 cursor-pointer"
                                                        title="No DCF analysis yet — click to analyze"
                                                    >
                                                        + Analyze
                                                    </span>
                                                ) : (
                                                    <span className="text-slate-700 text-xs">—</span>
                                                )}
                                            </td>
                                        );
                                    }
                                    
                                    let cellContent;
                                    if (col.id === 'symbol') {
                                        cellContent = (
                                            <div className="flex items-center gap-2">
                                                <button
                                                    onClick={(e) => toggleWatch(e, row.symbol, row.isWatched)}
                                                    className="text-slate-600 hover:text-yellow-400 active:scale-95 transition-all p-0.5 focus:outline-none"
                                                    title={row.isWatched ? "Remove from watchlist" : "Add to watchlist"}
                                                >
                                                    <Star
                                                        size={14}
                                                        className={row.isWatched ? "fill-yellow-400 text-yellow-400" : "text-slate-600/70"}
                                                    />
                                                </button>
                                                <span className="font-black text-white text-base tracking-tighter group-hover:text-indigo-300 transition-colors">{val}</span>
                                                {row.rowKind === 'holding'
                                                    ? <span className="text-[8px] font-black uppercase tracking-widest text-slate-600 border border-slate-700/50 rounded px-1 py-px">FUND</span>
                                                    : <ExternalLink size={10} className="opacity-0 group-hover:opacity-100 transition-opacity text-indigo-400" />
                                                }
                                            </div>
                                        );
                                    } else if (col.id === 'action') {
                                        const cls = getActionBadgeClass(String(val));
                                        const tip = row.portfolioRationale;
                                        cellContent = (
                                            <div className="flex items-center gap-1.5" onClick={e => e.stopPropagation()}>
                                                <span
                                                    className={`inline-flex items-center px-2 py-0.5 rounded border text-[10px] font-black uppercase tracking-wider cursor-default ${cls}`}
                                                    title={tip ?? undefined}
                                                >
                                                    {val}
                                                </span>
                                                <TradeButtons ticker={row.symbol} size="sm" />
                                            </div>
                                        );
                                    } else if (col.id === 'currentPct' || col.id === 'recommendedPct') {
                                        const pct = val as number | null;
                                        const isDelta = col.id === 'recommendedPct' && row.currentPct != null && pct != null;
                                        const delta = isDelta ? (pct! - row.currentPct!) : 0;
                                        cellContent = (
                                            <div className="flex flex-col items-end gap-0.5">
                                                <span className="font-mono text-xs font-bold text-slate-200">{pct != null ? `${pct.toFixed(2)}%` : '—'}</span>
                                                {isDelta && Math.abs(delta) > 0.05 && (
                                                    <span className={`text-[9px] font-bold ${delta > 0 ? 'text-green-400' : 'text-red-400'}`}>
                                                        {delta > 0 ? '▲' : '▼'} {Math.abs(delta).toFixed(2)}pp
                                                    </span>
                                                )}
                                            </div>
                                        );
                                    } else if (col.id === 'rationale') {
                                        const text = val as string | null;
                                        cellContent = text ? (
                                            <span
                                                className="text-slate-400 text-xs leading-snug block overflow-hidden"
                                                style={{ display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}
                                                title={text}
                                            >
                                                {text}
                                            </span>
                                        ) : <span className="text-slate-700 text-xs">—</span>;
                                    } else {
                                        cellContent = (
                                            <span className={`font-bold ${col.align === 'right' ? 'font-mono' : ''} ${isVisibleCol(col.id) ? 'text-slate-200' : 'text-slate-400'}`}>
                                                {col.format(val)}
                                            </span>
                                        );
                                    }

                                    return (
                                        <td
                                            key={col.id}
                                            className={`px-4 py-4 text-ellipsis ${col.id === 'action' ? 'relative z-10' : 'overflow-hidden'} ${col.id === 'rationale' ? 'whitespace-normal align-top' : 'whitespace-nowrap'} ${col.align === 'right' ? 'text-right' : 'text-left'}`}
                                            style={{
                                                ...(col.isChange ? { backgroundColor: changeBg(numVal) } : {}),
                                                ...(col.id === 'currentPct' ? { backgroundColor: pctHeatBg(row.currentPct, 'current') } : {}),
                                                ...(col.id === 'recommendedPct' ? { backgroundColor: pctHeatBg(row.recommendedPct, 'target') } : {}),
                                            }}
                                        >
                                            {cellContent}
                                        </td>
                                    );
                                })}
                            </tr>
                        ))}
                    </tbody>
                    {/* Totals footer — allocation check */}
                    <tfoot className="sticky bottom-0 z-20 bg-slate-900 border-t-2 border-slate-600">
                        <tr>
                            {visibleCols.map((col, i) => {
                                const isCurrent = col.id === 'currentPct';
                                const isTarget  = col.id === 'recommendedPct';
                                if (!isCurrent && !isTarget && i !== 0) {
                                    return <td key={col.id} className="px-4 py-3" />;
                                }
                                if (i === 0) {
                                    return (
                                        <td key={col.id} className="px-4 py-3 text-left">
                                            <span className="text-[10px] font-black uppercase tracking-widest text-slate-500">Total</span>
                                        </td>
                                    );
                                }
                                const total = isCurrent ? totalCurrentPct : totalRecommendedPct;
                                const off = Math.abs(total - 100);
                                const color = off < 1 ? 'text-emerald-400' : off < 5 ? 'text-amber-400' : 'text-red-400';
                                const bg = isCurrent ? pctHeatBg(Math.min(total / 8, 12), 'current') : pctHeatBg(Math.min(total / 8, 12), 'target');
                                return (
                                    <td key={col.id} className="px-4 py-3 text-right" style={{ backgroundColor: bg }}>
                                        <span className={`font-mono text-sm font-black ${color}`}>
                                            {total.toFixed(2)}%
                                        </span>
                                        <div className={`text-[9px] font-bold ${off < 1 ? 'text-emerald-500' : 'text-slate-500'}`}>
                                            {off < 0.5 ? '✓ 100%' : `${total < 100 ? '−' : '+'}${off.toFixed(1)}pp`}
                                        </div>
                                    </td>
                                );
                            })}
                        </tr>
                    </tfoot>
                </table>
            </div>
        </div>

        </>
    );
}

function isVisibleCol(id: string) {
    return !['model', 'lastAnalyzed'].includes(id);
}
