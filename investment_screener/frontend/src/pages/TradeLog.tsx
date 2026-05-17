import { useState, useEffect, useCallback } from 'react';
import { RefreshCcw, Zap, X, Filter } from 'lucide-react';
import {
    fetchTradeLog, updateTradeLogEntry, fetchMarketQuotes,
    type TradeLogEntry, type TradeLogStatus, type MarketQuote,
} from '../services/api';
import { TradePrepModal } from '../components/TradePrepModal';
import { PriceSourceBadge } from '../components/PriceSourceBadge';

// ── Chips ─────────────────────────────────────────────────────────────────────

const STATUS_STYLES: Record<TradeLogStatus, string> = {
    suggested: 'bg-amber-500/10 border-amber-500/30 text-amber-400',
    logged:    'bg-indigo-500/10 border-indigo-500/30 text-indigo-400',
    submitted: 'bg-sky-500/10 border-sky-500/30 text-sky-400',
    inactive:  'bg-slate-500/10 border-slate-500/30 text-slate-400',
    filled:    'bg-emerald-500/10 border-emerald-500/30 text-emerald-400',
    cancelled: 'bg-slate-700/40 border-slate-600/30 text-slate-500',
};

function StatusChip({ status }: { status: TradeLogStatus }) {
    return (
        <span className={`px-2 py-0.5 rounded-full border text-[10px] font-bold uppercase tracking-wide ${STATUS_STYLES[status]}`}>
            {status}
        </span>
    );
}

function ActionChip({ action }: { action: string }) {
    return (
        <span className={`px-2 py-0.5 rounded text-[10px] font-black uppercase ${
            action === 'buy' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'
        }`}>
            {action}
        </span>
    );
}

// ── Quote cells ───────────────────────────────────────────────────────────────

function QuoteCell({ value, digits = 2, prefix = '$' }: { value: number | null | undefined; digits?: number; prefix?: string }) {
    if (value == null) return <span className="text-slate-700">—</span>;
    return <span className="text-sky-300 font-mono">{prefix}{value.toFixed(digits)}</span>;
}

function ChangeCell({ pct }: { pct: number | null | undefined }) {
    if (pct == null) return <span className="text-slate-700">—</span>;
    const pos = pct >= 0;
    return (
        <span className={`font-mono text-[11px] font-semibold ${pos ? 'text-emerald-400' : 'text-red-400'}`}>
            {pos ? '+' : ''}{pct.toFixed(2)}%
        </span>
    );
}

// ── TV-style tabs ─────────────────────────────────────────────────────────────

type TabId = 'all' | 'working' | 'inactive' | 'planned' | 'filled' | 'cancelled';
type ActionFilter = 'buy' | 'sell' | 'all';

const TAB_STATUS_MAP: Record<TabId, TradeLogStatus[]> = {
    all:       ['suggested', 'logged', 'submitted', 'inactive', 'filled', 'cancelled'],
    working:   ['submitted'],
    inactive:  ['inactive'],
    planned:   ['suggested', 'logged'],
    filled:    ['filled'],
    cancelled: ['cancelled'],
};

// Limit/stop orders logged as 'submitted' (legacy) should display and filter as 'inactive'
function resolvedStatus(e: TradeLogEntry): TradeLogStatus {
    if (e.status === 'submitted' && (e.orderType === 'limit' || e.orderType === 'stop' || e.orderType === 'stop_limit')) {
        return 'inactive';
    }
    return e.status;
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function TradeLog() {
    const [entries, setEntries]   = useState<TradeLogEntry[]>([]);
    const [loading, setLoading]   = useState(true);
    const [quotes, setQuotes]     = useState<Record<string, MarketQuote>>({});
    const [quotesLoading, setQuotesLoading] = useState(false);
    const [execModal, setExecModal] = useState<{ ticker: string; action: 'buy' | 'sell'; shares: number } | null>(null);
    const [priceSource, setPriceSource]       = useState<string | null>(null);
    const [lastRefreshedAt, setLastRefreshedAt] = useState<Date | null>(null);

    const [tab, setTab]               = useState<TabId>('all');
    const [tickerFilter, setTickerFilter] = useState('');
    const [actionFilter, setActionFilter] = useState<ActionFilter>('all');

    const loadQuotes = useCallback(async (data: TradeLogEntry[]) => {
        const unique = [...new Set(data.filter(e => e.status !== 'cancelled').map(e => e.ticker))];
        if (unique.length === 0) return;
        setQuotesLoading(true);
        try {
            const [q, tvStatus] = await Promise.all([
                fetchMarketQuotes(unique),
                fetch('/api/tv-status').then(r => r.json()).catch(() => ({ price_source: null })),
            ]);
            setQuotes(q);
            setPriceSource(tvStatus.price_source ?? 'yfinance');
            setLastRefreshedAt(new Date());
        } catch { /* non-fatal */ }
        finally { setQuotesLoading(false); }
    }, []);

    const load = useCallback(async () => {
        setLoading(true);
        try {
            const { entries: data } = await fetchTradeLog();
            setEntries(data);
            loadQuotes(data);
        } catch { /* show empty */ }
        finally { setLoading(false); }
    }, [loadQuotes]);

    useEffect(() => { load(); }, [load]);

    const cancelEntry = async (id: string) => {
        try {
            await updateTradeLogEntry(id, { status: 'cancelled' });
            setEntries(prev => prev.map(e => e.id === id ? { ...e, status: 'cancelled' as TradeLogStatus } : e));
        } catch { /* ignore */ }
    };

    // Tab counts (use resolvedStatus so legacy 'submitted' limit orders count as 'inactive')
    const counts: Record<TabId, number> = {
        all:       entries.length,
        working:   entries.filter(e => resolvedStatus(e) === 'submitted').length,
        inactive:  entries.filter(e => resolvedStatus(e) === 'inactive').length,
        planned:   entries.filter(e => resolvedStatus(e) === 'suggested' || resolvedStatus(e) === 'logged').length,
        filled:    entries.filter(e => resolvedStatus(e) === 'filled').length,
        cancelled: entries.filter(e => resolvedStatus(e) === 'cancelled').length,
    };

    const filtered = entries.filter(e => {
        if (!TAB_STATUS_MAP[tab].includes(resolvedStatus(e))) return false;
        if (actionFilter !== 'all' && e.action !== actionFilter) return false;
        if (tickerFilter && !e.ticker.includes(tickerFilter.toUpperCase())) return false;
        return true;
    });

    const TABS: { id: TabId; label: string }[] = [
        { id: 'all',       label: 'All' },
        { id: 'working',   label: 'Working' },
        { id: 'inactive',  label: 'Inactive' },
        { id: 'planned',   label: 'Planned' },
        { id: 'filled',    label: 'Filled' },
        { id: 'cancelled', label: 'Cancelled' },
    ];

    return (
        <div className="space-y-4">

            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-2xl font-bold text-text">Trade Log</h2>
                    <p className="text-xs text-slate-500 mt-0.5">
                        {entries.length} entries
                        {quotesLoading && <span className="ml-2 text-sky-500">· fetching live quotes…</span>}
                    </p>
                </div>
                <div className="flex items-center gap-3">
                    <PriceSourceBadge priceSource={priceSource} lastRefreshedAt={lastRefreshedAt} />
                    <button
                        onClick={load}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-400 hover:text-white text-xs font-semibold transition-colors"
                    >
                        <RefreshCcw size={12} /> Refresh
                    </button>
                </div>
            </div>

            {/* TV-style tabs + filter bar */}
            <div className="flex items-end justify-between border-b border-slate-800">
                {/* Tabs */}
                <div className="flex">
                    {TABS.map(t => (
                        <button
                            key={t.id}
                            onClick={() => setTab(t.id)}
                            className={`flex items-center gap-1.5 px-4 py-2.5 text-xs font-semibold transition-colors border-b-2 -mb-px ${
                                tab === t.id
                                    ? 'text-white border-white'
                                    : 'text-slate-500 border-transparent hover:text-slate-300'
                            }`}
                        >
                            {t.label}
                            {counts[t.id] > 0 && (
                                <span className={`text-[10px] font-bold px-1.5 py-px rounded-full ${
                                    tab === t.id ? 'bg-white/15 text-white' : 'bg-slate-800 text-slate-500'
                                }`}>
                                    {counts[t.id]}
                                </span>
                            )}
                        </button>
                    ))}
                </div>

                {/* Compact filters */}
                <div className="flex items-center gap-2 pb-2">
                    <div className="relative">
                        <Filter size={11} className="absolute left-2 top-1/2 -translate-y-1/2 text-slate-500" />
                        <input
                            type="text"
                            placeholder="Ticker…"
                            value={tickerFilter}
                            onChange={e => setTickerFilter(e.target.value)}
                            className="bg-slate-900 border border-slate-700 rounded-lg pl-6 pr-2 py-1 text-xs text-white focus:outline-none focus:border-indigo-500 w-24 placeholder:text-slate-600"
                        />
                    </div>
                    <select
                        value={actionFilter}
                        onChange={e => setActionFilter(e.target.value as ActionFilter)}
                        className="bg-slate-900 border border-slate-700 rounded-lg px-2 py-1 text-xs text-slate-300 focus:outline-none focus:border-indigo-500"
                    >
                        <option value="all">All sides</option>
                        <option value="buy">Buy only</option>
                        <option value="sell">Sell only</option>
                    </select>
                </div>
            </div>

            {/* Table */}
            <div className="bg-surface rounded-xl border border-slate-800 overflow-hidden">
                {loading ? (
                    <div className="flex items-center justify-center h-40 text-slate-500 text-sm gap-2">
                        <RefreshCcw size={14} className="animate-spin" /> Loading…
                    </div>
                ) : filtered.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-40 text-slate-500 gap-2">
                        <span className="text-sm">No trades in this tab</span>
                        {entries.length === 0 && (
                            <span className="text-xs text-slate-600 text-center max-w-sm">
                                Use "Log Trade" from Portfolio Table or Stock Analysis to add entries.
                                The <code className="px-1 bg-slate-800 rounded">/rebalance</code> skill writes suggested trades here automatically.
                            </span>
                        )}
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full text-xs">
                            <thead>
                                <tr className="border-b border-slate-800 text-[10px] uppercase tracking-wider">
                                    <th className="px-4 py-3 text-left text-slate-500 font-semibold">Date</th>
                                    <th className="px-3 py-3 text-left text-slate-500 font-semibold">Ticker</th>
                                    <th className="px-3 py-3 text-left text-slate-500 font-semibold">Side</th>
                                    <th className="px-3 py-3 text-right text-slate-500 font-semibold">Qty</th>
                                    <th className="px-3 py-3 text-right text-slate-500 font-semibold">Limit Price</th>
                                    <th className="px-3 py-3 text-right text-slate-500 font-semibold">Avg Fill</th>
                                    <th className="px-3 py-3 text-right text-slate-500 font-semibold">Total</th>
                                    <th className="px-3 py-3 text-left text-slate-500 font-semibold">Account</th>
                                    <th className="px-3 py-3 text-left text-slate-500 font-semibold">Type</th>
                                    <th className="px-3 py-3 text-right text-sky-500/70 font-semibold border-l border-slate-800">Last</th>
                                    <th className="px-3 py-3 text-right text-sky-500/70 font-semibold">Bid</th>
                                    <th className="px-3 py-3 text-right text-sky-500/70 font-semibold">Ask</th>
                                    <th className="px-3 py-3 text-right text-sky-500/70 font-semibold">Chg%</th>
                                    <th className="px-3 py-3 text-right text-sky-500/70 font-semibold border-r border-slate-800">Vol</th>
                                    <th className="px-3 py-3 text-left text-slate-500 font-semibold">Status</th>
                                    <th className="px-3 py-3 text-left text-slate-500 font-semibold">Source</th>
                                    <th className="px-3 py-3 text-left text-slate-500 font-semibold">Notes</th>
                                    <th className="px-3 py-3 text-right text-slate-500 font-semibold">Actions</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-800/60">
                                {filtered.map(e => {
                                    const q = quotes[e.ticker];
                                    const rs = resolvedStatus(e);
                                    const isFilled = rs === 'filled';
                                    return (
                                        <tr
                                            key={e.id}
                                            className={`hover:bg-slate-800/30 transition-colors ${rs === 'cancelled' ? 'opacity-40' : ''}`}
                                        >
                                            <td className="px-4 py-2.5 text-slate-400 whitespace-nowrap">{e.date}</td>
                                            <td className="px-3 py-2.5 font-mono font-bold text-white">{e.ticker}</td>
                                            <td className="px-3 py-2.5"><ActionChip action={e.action} /></td>
                                            <td className="px-3 py-2.5 text-right font-mono text-slate-200">{e.shares.toLocaleString()}</td>
                                            <td className="px-3 py-2.5 text-right font-mono text-slate-400">
                                                {e.limitPrice != null ? `$${e.limitPrice.toFixed(2)}` : <span className="text-slate-700">—</span>}
                                            </td>
                                            <td className="px-3 py-2.5 text-right font-mono text-slate-300">
                                                {isFilled && e.price > 0 ? `$${e.price.toFixed(2)}` : <span className="text-slate-700">—</span>}
                                            </td>
                                            <td className="px-3 py-2.5 text-right font-mono text-slate-300">
                                                {isFilled && e.totalCost > 0 ? `$${e.totalCost.toFixed(2)}` : <span className="text-slate-700">—</span>}
                                            </td>
                                            <td className="px-3 py-2.5 text-slate-300 font-mono text-[11px]">{e.account}</td>
                                            <td className="px-3 py-2.5 text-slate-400 uppercase text-[10px] tracking-wide">{e.orderType ?? 'market'}</td>
                                            {/* Live market */}
                                            <td className="px-3 py-2.5 text-right border-l border-slate-800/60"><QuoteCell value={q?.price} /></td>
                                            <td className="px-3 py-2.5 text-right">
                                                <div className="flex flex-col items-end">
                                                    <QuoteCell value={q?.bid} />
                                                    {q?.bidSize != null && <span className="text-[9px] text-slate-600">×{q.bidSize}</span>}
                                                </div>
                                            </td>
                                            <td className="px-3 py-2.5 text-right">
                                                <div className="flex flex-col items-end">
                                                    <QuoteCell value={q?.ask} />
                                                    {q?.askSize != null && <span className="text-[9px] text-slate-600">×{q.askSize}</span>}
                                                </div>
                                            </td>
                                            <td className="px-3 py-2.5 text-right"><ChangeCell pct={q?.dayChangePct} /></td>
                                            <td className="px-3 py-2.5 text-right font-mono text-slate-500 text-[10px] border-r border-slate-800/60">
                                                {q?.volume != null ? (q.volume >= 1_000_000 ? `${(q.volume / 1_000_000).toFixed(1)}M` : `${(q.volume / 1_000).toFixed(0)}K`) : <span className="text-slate-700">—</span>}
                                            </td>
                                            <td className="px-3 py-2.5"><StatusChip status={rs} /></td>
                                            <td className="px-3 py-2.5 text-slate-600 text-[10px] uppercase tracking-wide">{e.source ?? 'manual'}</td>
                                            <td className="px-3 py-2.5 text-slate-500 max-w-[160px] truncate" title={e.notes}>
                                                {e.notes || <span className="text-slate-700">—</span>}
                                            </td>
                                            <td className="px-3 py-2.5 whitespace-nowrap text-right">
                                                <div className="flex items-center gap-1 justify-end">
                                                    {(rs === 'suggested' || rs === 'logged') && (
                                                        <button
                                                            onClick={() => setExecModal({ ticker: e.ticker, action: e.action as 'buy' | 'sell', shares: e.shares })}
                                                            title="Execute in TradingView"
                                                            className="flex items-center gap-1 px-2 py-0.5 rounded bg-emerald-900/30 hover:bg-emerald-800/40 border border-emerald-700/30 text-emerald-500 hover:text-emerald-300 text-[10px] font-bold transition-colors"
                                                        >
                                                            <Zap size={10} /> Execute
                                                        </button>
                                                    )}
                                                    {rs !== 'cancelled' && rs !== 'submitted' && rs !== 'filled' && (
                                                        <button
                                                            onClick={() => cancelEntry(e.id)}
                                                            title="Cancel entry"
                                                            className="p-0.5 rounded text-slate-600 hover:text-red-400 transition-colors"
                                                        >
                                                            <X size={12} />
                                                        </button>
                                                    )}
                                                </div>
                                            </td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            {execModal && (
                <TradePrepModal
                    ticker={execModal.ticker}
                    initialAction={execModal.action}
                    initialShares={execModal.shares}
                    onClose={() => { setExecModal(null); load(); }}
                />
            )}
        </div>
    );
}
