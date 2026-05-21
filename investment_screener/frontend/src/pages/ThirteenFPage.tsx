import { useState, useEffect, useMemo } from 'react';
import { TradeButtons } from '../components/TradeButtons';

interface Holding {
    ticker: string;
    name: string;
    cusip: string;
    value_usd: number;
    shares: number;
    put_call: 'Put' | 'Call' | null;
    value_pct: number;
    married_put?: boolean;
    put_value?: number;
    change?: string;
}

interface DiffEntry {
    ticker: string;
    name: string;
    cusip: string;
    value_usd: number;
    shares: number;
    put_call: 'Put' | 'Call' | null;
    married_put?: boolean;
    put_value?: number;
    shares_change?: number;
    shares_change_pct?: number;
    value_pct?: number;
}

interface Summary {
    meta: {
        fund: string; filing_date: string; period: string;
        aum_usd: number; aum_prev_usd: number | null; position_count: number; prev_period: string | null;
    };
    holdings: Holding[];
    diff: {
        new_positions: DiffEntry[];
        closed_positions: DiffEntry[];
        increased: DiffEntry[];
        decreased: DiffEntry[];
    } | null;
}

const TABS = ['Overview', 'Top Buys', 'Top Exits', 'All Holdings'] as const;
type Tab = typeof TABS[number];

function fmtM(v: number) {
    if (v >= 1e9) return `$${(v / 1e9).toFixed(2)}B`;
    if (v >= 1e6) return `$${(v / 1e6).toFixed(0)}M`;
    return `$${v.toLocaleString()}`;
}

function marriedPutBadge(putValue: number) {
    return (
        <span title={`Married put: ${fmtM(putValue)} put position alongside this long`}
            className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-amber-900/60 text-amber-300 border border-amber-700/50 cursor-help">
            ⚠ PUT {fmtM(putValue)}
        </span>
    );
}

function typeBadge(putCall: 'Put' | 'Call' | null) {
    if (putCall === 'Put')  return <span className="px-1.5 py-0.5 rounded text-xs font-bold bg-red-900/60 text-red-300">PUT</span>;
    if (putCall === 'Call') return <span className="px-1.5 py-0.5 rounded text-xs font-bold bg-blue-900/60 text-blue-300">CALL</span>;
    return <span className="px-1.5 py-0.5 rounded text-xs font-bold bg-emerald-900/60 text-emerald-300">LONG</span>;
}

// function changeBadge(label: string, color: string) {
//     return <span className={`px-1.5 py-0.5 rounded text-xs font-bold ${color}`}>{label}</span>;
// }

export default function ThirteenFPage() {
    const [data, setData] = useState<Summary | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [tab, setTab] = useState<Tab>('Overview');
    const [sortCol, setSortCol] = useState<'value' | 'ticker' | 'pct'>('value');
    const [sortDir, setSortDir] = useState<'desc' | 'asc'>('desc');
    const [filterType, setFilterType] = useState<'all' | 'long' | 'put' | 'call'>('all');
    const [search, setSearch] = useState('');

    useEffect(() => {
        fetch('/api/13f/summary')
            .then(r => r.json())
            .then(d => { setData(d); setLoading(false); })
            .catch(e => { setError(e.message); setLoading(false); });
    }, []);

    const filteredHoldings = useMemo(() => {
        if (!data) return [];
        let h = [...data.holdings];
        if (filterType === 'long') h = h.filter(x => x.put_call === null);
        if (filterType === 'put')  h = h.filter(x => x.put_call === 'Put');
        if (filterType === 'call') h = h.filter(x => x.put_call === 'Call');
        if (search) {
            const q = search.toLowerCase();
            h = h.filter(x => x.ticker.toLowerCase().includes(q) || x.name.toLowerCase().includes(q));
        }
        h.sort((a, b) => {
            let av = sortCol === 'value' ? a.value_usd : sortCol === 'pct' ? a.value_pct : 0;
            let bv = sortCol === 'value' ? b.value_usd : sortCol === 'pct' ? b.value_pct : 0;
            if (sortCol === 'ticker') return sortDir === 'asc' ? a.ticker.localeCompare(b.ticker) : b.ticker.localeCompare(a.ticker);
            return sortDir === 'desc' ? bv - av : av - bv;
        });
        return h;
    }, [data, filterType, search, sortCol, sortDir]);

    function toggleSort(col: typeof sortCol) {
        if (sortCol === col) setSortDir(d => d === 'desc' ? 'asc' : 'desc');
        else { setSortCol(col); setSortDir('desc'); }
    }

    if (loading) return <div className="p-6 flex items-center justify-center h-full"><div className="text-slate-500 text-sm">Loading 13F data...</div></div>;
    if (error || !data) return <div className="p-6 flex items-center justify-center h-full"><div className="text-red-400 text-sm">{error || 'No data'}</div></div>;

    const { meta, holdings, diff } = data;
    const longs = holdings.filter(h => h.put_call === null);
    const puts  = holdings.filter(h => h.put_call === 'Put');
    const calls = holdings.filter(h => h.put_call === 'Call');
    const longsValue = longs.reduce((s, h) => s + h.value_usd, 0);
    const putsValue  = puts.reduce((s, h) => s + h.value_usd, 0);
    const callsValue = calls.reduce((s, h) => s + h.value_usd, 0);
    const aumChange  = meta.aum_prev_usd ? ((meta.aum_usd - meta.aum_prev_usd) / meta.aum_prev_usd * 100) : null;

    // Treemap: longs sorted by value, proportional boxes
    const treemapTotal = longsValue || 1;

    return (
        <div className="p-4 h-full flex flex-col gap-4 overflow-auto">
            {/* Header */}
            <div className="flex items-start justify-between">
                <div>
                    <h1 className="text-xl font-bold text-white">13F — {meta.fund}</h1>
                    <p className="text-xs text-slate-500 mt-0.5">Q{Math.ceil(new Date(meta.period).getMonth() / 3) || 4} {new Date(meta.period).getFullYear()} · Filed {meta.filing_date} · {meta.position_count} positions</p>
                </div>
                <div className="text-right">
                    <div className="text-lg font-bold text-white">{fmtM(meta.aum_usd)}</div>
                    <div className="text-xs text-slate-400">AUM {aumChange != null ? <span className={aumChange >= 0 ? 'text-emerald-400' : 'text-red-400'}>{aumChange >= 0 ? '+' : ''}{aumChange.toFixed(0)}% QoQ</span> : ''}</div>
                </div>
            </div>

            {/* AUM breakdown cards */}
            <div className="grid grid-cols-3 gap-3">
                <div className="bg-slate-900/80 border border-emerald-800/40 rounded-xl px-4 py-3">
                    <div className="text-xs text-slate-500 uppercase tracking-wider mb-1">Long Book</div>
                    <div className="text-lg font-bold text-emerald-400">{fmtM(longsValue)}</div>
                    <div className="text-xs text-slate-500">{(longsValue / meta.aum_usd * 100).toFixed(1)}% of AUM · {longs.length} positions</div>
                </div>
                <div className="bg-slate-900/80 border border-red-800/40 rounded-xl px-4 py-3">
                    <div className="text-xs text-slate-500 uppercase tracking-wider mb-1">Put Book</div>
                    <div className="text-lg font-bold text-red-400">{fmtM(putsValue)}</div>
                    <div className="text-xs text-slate-500">{(putsValue / meta.aum_usd * 100).toFixed(1)}% of AUM · {puts.length} positions</div>
                </div>
                <div className="bg-slate-900/80 border border-blue-800/40 rounded-xl px-4 py-3">
                    <div className="text-xs text-slate-500 uppercase tracking-wider mb-1">Call Book</div>
                    <div className="text-lg font-bold text-blue-400">{fmtM(callsValue)}</div>
                    <div className="text-xs text-slate-500">{(callsValue / meta.aum_usd * 100).toFixed(1)}% of AUM · {calls.length} positions</div>
                </div>
            </div>

            {/* Tabs */}
            <div className="flex gap-1 border-b border-slate-800">
                {TABS.map(t => (
                    <button key={t} onClick={() => setTab(t)}
                        className={`px-4 py-2 text-sm font-medium transition-colors ${tab === t ? 'text-white border-b-2 border-emerald-500' : 'text-slate-500 hover:text-slate-300'}`}>
                        {t}
                    </button>
                ))}
            </div>

            {/* Tab content */}
            {tab === 'Overview' && (
                <div className="space-y-4">
                    <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4">
                        <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">Long Book Heatmap</h3>
                        <div className="flex flex-wrap gap-1.5">
                            {longs.sort((a,b) => b.value_usd - a.value_usd).map(h => {
                                const pct = h.value_usd / treemapTotal;
                                const minW = 48;
                                const w = Math.max(minW, Math.round(pct * 900));
                                const opacity = 0.3 + pct * 4;
                                return (
                                    <div key={h.ticker + h.cusip}
                                        style={{ width: `${Math.min(w, 280)}px`, opacity: Math.min(opacity, 1) }}
                                        className={`rounded flex flex-col items-center justify-center p-1 cursor-default min-h-[40px] ${h.married_put ? 'bg-amber-800 border border-amber-600/60' : 'bg-emerald-700'}`}
                                        title={h.married_put ? `${h.name} — ${fmtM(h.value_usd)} long + ${fmtM(h.put_value ?? 0)} PUT (married put)` : `${h.name} — ${fmtM(h.value_usd)} (${h.value_pct.toFixed(2)}%)`}>
                                        <span className="text-white text-xs font-bold">{h.ticker}</span>
                                        <span className={`text-[10px] ${h.married_put ? 'text-amber-200' : 'text-emerald-200'}`}>
                                            {h.married_put ? '⚠ PUT' : `${h.value_pct.toFixed(1)}%`}
                                        </span>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                    <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4">
                        <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">Put Book — Bearish Hedges</h3>
                        <div className="flex flex-wrap gap-1.5">
                            {puts.sort((a,b) => b.value_usd - a.value_usd).map(h => {
                                const pct = h.value_usd / putsValue;
                                const w = Math.max(48, Math.round(pct * 900));
                                return (
                                    <div key={h.ticker + h.cusip}
                                        style={{ width: `${Math.min(w, 280)}px`, opacity: Math.min(0.4 + pct * 3, 1) }}
                                        className="bg-red-800 rounded flex flex-col items-center justify-center p-1 cursor-default min-h-[40px]"
                                        title={`${h.name} PUT — ${fmtM(h.value_usd)} (${h.value_pct.toFixed(2)}%)`}>
                                        <span className="text-white text-xs font-bold">{h.ticker}</span>
                                        <span className="text-red-200 text-[10px]">{h.value_pct.toFixed(1)}%</span>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                </div>
            )}

            {tab === 'Top Buys' && diff && (
                <div className="space-y-4">
                    <div className="bg-slate-900/80 border border-slate-800 rounded-xl overflow-hidden">
                        <div className="px-4 py-2 border-b border-slate-800 text-xs font-bold text-emerald-400 uppercase tracking-wider">New Positions</div>
                        <table className="w-full text-sm">
                            <thead><tr className="text-xs text-slate-500 border-b border-slate-800">
                                <th className="text-left px-4 py-2">Ticker</th>
                                <th className="text-left px-4 py-2">Name</th>
                                <th className="text-right px-4 py-2">Value</th>
                                <th className="text-center px-4 py-2">Type</th>
                                <th className="text-right px-4 py-2">Action</th>
                            </tr></thead>
                            <tbody>
                                {diff.new_positions.filter(h => h.put_call === null).sort((a,b) => b.value_usd - a.value_usd).map(h => (
                                    <tr key={h.ticker + h.cusip} className={`border-b border-slate-800/50 hover:bg-slate-800/30 ${h.married_put ? 'bg-amber-950/20' : ''}`}>
                                        <td className="px-4 py-2 font-bold text-white">{h.ticker}</td>
                                        <td className="px-4 py-2 text-slate-400 text-xs">{h.name}</td>
                                        <td className="px-4 py-2 text-right text-emerald-400 font-mono">{fmtM(h.value_usd)}</td>
                                        <td className="px-4 py-2 text-center flex items-center gap-1.5 justify-center">
                                            {typeBadge(h.put_call)}
                                            {h.married_put && h.put_value ? marriedPutBadge(h.put_value) : null}
                                        </td>
                                        <td className="px-4 py-2 text-right"><TradeButtons ticker={h.ticker} size="sm" /></td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                    <div className="bg-slate-900/80 border border-slate-800 rounded-xl overflow-hidden">
                        <div className="px-4 py-2 border-b border-slate-800 text-xs font-bold text-emerald-400 uppercase tracking-wider">Increased Positions</div>
                        <table className="w-full text-sm">
                            <thead><tr className="text-xs text-slate-500 border-b border-slate-800">
                                <th className="text-left px-4 py-2">Ticker</th>
                                <th className="text-left px-4 py-2">Name</th>
                                <th className="text-right px-4 py-2">Value</th>
                                <th className="text-right px-4 py-2">Δ Shares</th>
                                <th className="text-center px-4 py-2">Type</th>
                                <th className="text-right px-4 py-2">Action</th>
                            </tr></thead>
                            <tbody>
                                {diff.increased.filter(h => h.put_call === null).sort((a,b) => b.value_usd - a.value_usd).map(h => (
                                    <tr key={h.ticker + h.cusip} className={`border-b border-slate-800/50 hover:bg-slate-800/30 ${h.married_put ? 'bg-amber-950/20' : ''}`}>
                                        <td className="px-4 py-2 font-bold text-white">{h.ticker}</td>
                                        <td className="px-4 py-2 text-slate-400 text-xs">{h.name}</td>
                                        <td className="px-4 py-2 text-right text-emerald-400 font-mono">{fmtM(h.value_usd)}</td>
                                        <td className="px-4 py-2 text-right text-slate-400 font-mono text-xs">
                                            {h.shares_change ? `+${(h.shares_change/1e6).toFixed(2)}M` : ''}
                                            {h.shares_change_pct ? <span className="text-emerald-400 ml-1">+{h.shares_change_pct.toFixed(0)}%</span> : ''}
                                        </td>
                                        <td className="px-4 py-2 text-center flex items-center gap-1.5 justify-center">
                                            {typeBadge(h.put_call)}
                                            {h.married_put && h.put_value ? marriedPutBadge(h.put_value) : null}
                                        </td>
                                        <td className="px-4 py-2 text-right"><TradeButtons ticker={h.ticker} size="sm" /></td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {tab === 'Top Exits' && diff && (
                <div className="space-y-4">
                    <div className="bg-slate-900/80 border border-slate-800 rounded-xl overflow-hidden">
                        <div className="px-4 py-2 border-b border-slate-800 text-xs font-bold text-red-400 uppercase tracking-wider">Closed Positions</div>
                        <table className="w-full text-sm">
                            <thead><tr className="text-xs text-slate-500 border-b border-slate-800">
                                <th className="text-left px-4 py-2">Ticker</th>
                                <th className="text-left px-4 py-2">Name</th>
                                <th className="text-right px-4 py-2">Prior Value</th>
                                <th className="text-center px-4 py-2">Type</th>
                                <th className="text-right px-4 py-2">Action</th>
                            </tr></thead>
                            <tbody>
                                {diff.closed_positions.sort((a,b) => b.value_usd - a.value_usd).map(h => (
                                    <tr key={h.ticker + h.cusip} className="border-b border-slate-800/50 hover:bg-slate-800/30">
                                        <td className="px-4 py-2 font-bold text-white">{h.ticker}</td>
                                        <td className="px-4 py-2 text-slate-400 text-xs">{h.name}</td>
                                        <td className="px-4 py-2 text-right text-red-400 font-mono">{fmtM(h.value_usd)}</td>
                                        <td className="px-4 py-2 text-center">{typeBadge(h.put_call)}</td>
                                        <td className="px-4 py-2 text-right"><TradeButtons ticker={h.ticker} size="sm" /></td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                    <div className="bg-slate-900/80 border border-slate-800 rounded-xl overflow-hidden">
                        <div className="px-4 py-2 border-b border-slate-800 text-xs font-bold text-amber-400 uppercase tracking-wider">Trimmed Positions</div>
                        <table className="w-full text-sm">
                            <thead><tr className="text-xs text-slate-500 border-b border-slate-800">
                                <th className="text-left px-4 py-2">Ticker</th>
                                <th className="text-left px-4 py-2">Name</th>
                                <th className="text-right px-4 py-2">Current Value</th>
                                <th className="text-right px-4 py-2">Δ Shares</th>
                                <th className="text-center px-4 py-2">Type</th>
                                <th className="text-right px-4 py-2">Action</th>
                            </tr></thead>
                            <tbody>
                                {diff.decreased.sort((a,b) => b.value_usd - a.value_usd).map(h => (
                                    <tr key={h.ticker + h.cusip} className="border-b border-slate-800/50 hover:bg-slate-800/30">
                                        <td className="px-4 py-2 font-bold text-white">{h.ticker}</td>
                                        <td className="px-4 py-2 text-slate-400 text-xs">{h.name}</td>
                                        <td className="px-4 py-2 text-right text-amber-400 font-mono">{fmtM(h.value_usd)}</td>
                                        <td className="px-4 py-2 text-right text-slate-400 font-mono text-xs">
                                            {h.shares_change ? `${(h.shares_change/1e6).toFixed(2)}M` : ''}
                                            {h.shares_change_pct ? <span className="text-red-400 ml-1">{h.shares_change_pct.toFixed(0)}%</span> : ''}
                                        </td>
                                        <td className="px-4 py-2 text-center">{typeBadge(h.put_call)}</td>
                                        <td className="px-4 py-2 text-right"><TradeButtons ticker={h.ticker} size="sm" /></td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {tab === 'All Holdings' && (
                <div className="bg-slate-900/80 border border-slate-800 rounded-xl overflow-hidden">
                    {/* Filters */}
                    <div className="px-4 py-3 border-b border-slate-800 flex items-center gap-3">
                        <input value={search} onChange={e => setSearch(e.target.value)}
                            placeholder="Search ticker or name..."
                            className="bg-slate-800 text-white text-sm px-3 py-1.5 rounded border border-slate-700 w-48 placeholder:text-slate-500" />
                        <div className="flex gap-1">
                            {(['all','long','put','call'] as const).map(f => (
                                <button key={f} onClick={() => setFilterType(f)}
                                    className={`px-3 py-1 rounded text-xs font-medium transition-colors ${filterType === f
                                        ? f === 'long' ? 'bg-emerald-700 text-white' : f === 'put' ? 'bg-red-800 text-white' : f === 'call' ? 'bg-blue-800 text-white' : 'bg-slate-600 text-white'
                                        : 'bg-slate-800 text-slate-400 hover:text-slate-200'}`}>
                                    {f.toUpperCase()}
                                </button>
                            ))}
                        </div>
                        <span className="text-xs text-slate-500 ml-auto">{filteredHoldings.length} positions</span>
                    </div>
                    <div className="overflow-auto">
                        <table className="w-full text-sm">
                            <thead className="sticky top-0 bg-slate-900">
                                <tr className="text-xs text-slate-500 border-b border-slate-800">
                                    <th className="text-left px-4 py-2 cursor-pointer hover:text-slate-300" onClick={() => toggleSort('ticker')}>
                                        Ticker {sortCol === 'ticker' ? (sortDir === 'desc' ? '↓' : '↑') : ''}
                                    </th>
                                    <th className="text-left px-4 py-2">Name</th>
                                    <th className="text-right px-4 py-2 cursor-pointer hover:text-slate-300" onClick={() => toggleSort('value')}>
                                        Value {sortCol === 'value' ? (sortDir === 'desc' ? '↓' : '↑') : ''}
                                    </th>
                                    <th className="text-right px-4 py-2 cursor-pointer hover:text-slate-300" onClick={() => toggleSort('pct')}>
                                        % AUM {sortCol === 'pct' ? (sortDir === 'desc' ? '↓' : '↑') : ''}
                                    </th>
                                    <th className="text-center px-4 py-2">Type</th>
                                    <th className="text-right px-4 py-2">Action</th>
                                </tr>
                            </thead>
                            <tbody>
                                {filteredHoldings.map(h => (
                                    <tr key={h.ticker + h.cusip + h.put_call} className={`border-b border-slate-800/40 hover:bg-slate-800/30 ${h.married_put ? 'bg-amber-950/20' : ''}`}>
                                        <td className="px-4 py-2 font-bold text-white">{h.ticker}</td>
                                        <td className="px-4 py-2 text-slate-400 text-xs max-w-[200px] truncate">{h.name}</td>
                                        <td className={`px-4 py-2 text-right font-mono font-medium ${h.put_call === 'Put' ? 'text-red-400' : h.put_call === 'Call' ? 'text-blue-400' : 'text-emerald-400'}`}>
                                            {fmtM(h.value_usd)}
                                        </td>
                                        <td className="px-4 py-2 text-right text-slate-400 font-mono text-xs">{h.value_pct.toFixed(2)}%</td>
                                        <td className="px-4 py-2 text-center">
                                            <div className="flex items-center gap-1.5 justify-center">
                                                {typeBadge(h.put_call)}
                                                {h.married_put && h.put_value ? marriedPutBadge(h.put_value) : null}
                                            </div>
                                        </td>
                                        <td className="px-4 py-2 text-right">
                                            {h.put_call === null && <TradeButtons ticker={h.ticker} size="sm" />}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}
        </div>
    );
}
