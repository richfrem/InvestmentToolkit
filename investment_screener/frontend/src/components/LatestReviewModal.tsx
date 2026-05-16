/**
 * LatestReviewModal.tsx (React Component)
 * =====================================
 *
 * Purpose:
 *     Modal summary of the most recent portfolio review, showing drift and thesis updates.
 *
 * Layer: Frontend / UI / Modals
 *
 * Usage Examples:
 *     <LatestReviewModal onClose={() => {}} />
 *
 * Key Functions:
 *     - fetchLatestReviewData() - Async call to retrieve the latest review summary from backend
 */
import { useEffect, useState } from 'react';
import { X, TrendingUp, TrendingDown, Minus, AlertTriangle, Clock, CheckCircle2, Loader2, FileBarChart2 } from 'lucide-react';
import { fetchLatestReviewData } from '../services/api';
import { getActionTextClass } from '../utils/actionColors';

interface Props { onClose: () => void; }

function DeltaIcon({ delta }: { delta: number }) {
    if (delta > 0.1) return <TrendingUp size={12} className="text-green-400 shrink-0" />;
    if (delta < -0.1) return <TrendingDown size={12} className="text-red-400 shrink-0" />;
    return <Minus size={12} className="text-slate-500 shrink-0" />;
}

export default function LatestReviewModal({ onClose }: Props) {
    const [data, setData] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [tab, setTab] = useState<'urgent' | 'all' | 'formula'>('urgent');

    useEffect(() => {
        fetchLatestReviewData()
            .then(setData)
            .catch(e => setError(e.message))
            .finally(() => setLoading(false));
    }, []);

    useEffect(() => {
        const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
        document.addEventListener('keydown', handler);
        return () => document.removeEventListener('keydown', handler);
    }, [onClose]);

    const urgentHoldings  = data?.holdings?.filter((h: any) => h.urgency === 'URGENT') ?? [];
    const normalHoldings  = data?.holdings?.filter((h: any) => h.urgency === 'NORMAL') ?? [];
    const lowHoldings     = data?.holdings?.filter((h: any) => h.urgency === 'LOW')    ?? [];
    const changedHoldings = data?.holdings?.filter((h: any) => h.delta !== 0)           ?? [];

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm" onClick={onClose}>
            <div
                className="relative bg-slate-950 border border-slate-700 rounded-2xl shadow-2xl w-full max-w-4xl max-h-[90vh] flex flex-col"
                onClick={e => e.stopPropagation()}
            >
                {/* Header */}
                <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 shrink-0">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-amber-500/10 rounded-lg text-amber-400">
                            <FileBarChart2 size={18} />
                        </div>
                        <div>
                            <h2 className="text-white font-bold text-base">Portfolio Analysis</h2>
                            <p className="text-slate-500 text-xs">
                                {data ? `${data.reviewDate} · ${data.thesisName} · Status: ${data.status}` : 'Loading...'}
                            </p>
                        </div>
                    </div>
                    <button onClick={onClose} className="p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors">
                        <X size={18} />
                    </button>
                </div>

                {/* Tabs */}
                <div className="flex gap-1 px-6 pt-3 shrink-0 border-b border-slate-800 pb-0">
                    {([
                        { id: 'urgent', label: `🔴 Urgent (${urgentHoldings.length})` },
                        { id: 'all',    label: `All Changes (${changedHoldings.length})` },
                        { id: 'formula',label: 'Formula Impact' },
                    ] as const).map(t => (
                        <button
                            key={t.id}
                            onClick={() => setTab(t.id)}
                            className={`px-4 py-2.5 text-xs font-bold rounded-t-lg transition-colors border-b-2 -mb-px
                                ${tab === t.id
                                    ? 'text-white border-amber-400 bg-amber-500/5'
                                    : 'text-slate-500 border-transparent hover:text-slate-300'}`}
                        >
                            {t.label}
                        </button>
                    ))}
                </div>

                {/* Body */}
                <div className="flex-1 overflow-y-auto custom-scrollbar">
                    {loading && (
                        <div className="flex items-center justify-center h-48 gap-3 text-slate-400">
                            <Loader2 size={20} className="animate-spin" />
                            <span className="text-sm">Loading analysis...</span>
                        </div>
                    )}
                    {error && <div className="text-red-400 text-sm m-6 p-4 bg-red-500/10 rounded-lg">{error}</div>}

                    {data && (
                        <div className="p-6">
                            {/* Summary Stats */}
                            <div className="grid grid-cols-4 gap-3 mb-6">
                                {[
                                    { label: 'Urgent', value: data.summary?.urgentActions ?? 0, icon: <AlertTriangle size={14} />, color: 'text-red-400 bg-red-500/10' },
                                    { label: 'Normal', value: data.summary?.normalActions ?? 0, icon: <Clock size={14} />, color: 'text-amber-400 bg-amber-500/10' },
                                    { label: 'Low', value: data.summary?.lowActions ?? 0, icon: <CheckCircle2 size={14} />, color: 'text-slate-400 bg-slate-500/10' },
                                    { label: 'Weight Shift', value: `${data.summary?.totalWeightShifted ?? 0}%`, icon: <TrendingUp size={14} />, color: 'text-indigo-400 bg-indigo-500/10' },
                                ].map(s => (
                                    <div key={s.label} className={`flex items-center gap-2 px-3 py-2.5 rounded-xl ${s.color} border border-white/5`}>
                                        <span className="shrink-0">{s.icon}</span>
                                        <div>
                                            <div className="text-[10px] uppercase tracking-widest font-black text-current opacity-70">{s.label}</div>
                                            <div className="text-lg font-black text-white">{s.value}</div>
                                        </div>
                                    </div>
                                ))}
                            </div>

                            {/* Urgent Tab */}
                            {tab === 'urgent' && (
                                <HoldingTable holdings={urgentHoldings} title="Act within 30 days" />
                            )}

                            {/* All Changes Tab */}
                            {tab === 'all' && (
                                <div className="space-y-4">
                                    {urgentHoldings.length > 0 && <HoldingTable holdings={urgentHoldings} title="🔴 URGENT" />}
                                    {normalHoldings.length > 0 && <HoldingTable holdings={normalHoldings} title="🟡 NORMAL" />}
                                    {lowHoldings.length > 0   && <HoldingTable holdings={lowHoldings}   title="⚪ LOW" />}
                                </div>
                            )}

                            {/* Formula Tab */}
                            {tab === 'formula' && (
                                <div className="space-y-4">
                                    <div className="text-xs text-slate-500 mb-3">Pillar weight impact from proposed holding changes</div>
                                    <div className="rounded-xl overflow-hidden border border-slate-800">
                                        <table className="w-full text-sm">
                                            <thead>
                                                <tr className="bg-slate-900 border-b border-slate-800">
                                                    {['Pillar', 'Current', 'Proposed', 'Delta'].map(h => (
                                                        <th key={h} className="px-4 py-2.5 text-left text-[10px] font-black uppercase tracking-widest text-slate-500">{h}</th>
                                                    ))}
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {(data.pillars ?? []).map((p: any) => (
                                                    <tr key={p.id} className="border-b border-slate-800/50 hover:bg-white/[0.02]">
                                                        <td className="px-4 py-2.5 text-slate-300 font-bold text-xs">{p.name}</td>
                                                        <td className="px-4 py-2.5 font-mono text-xs text-slate-400">{p.currentTarget.toFixed(2)}%</td>
                                                        <td className="px-4 py-2.5 font-mono text-xs text-white">{p.recommendedTarget.toFixed(2)}%</td>
                                                        <td className="px-4 py-2.5 font-mono text-xs">
                                                            <span className={p.delta > 0.05 ? 'text-green-400' : p.delta < -0.05 ? 'text-red-400' : 'text-slate-500'}>
                                                                {p.delta > 0 ? '+' : ''}{p.delta.toFixed(2)}pp
                                                            </span>
                                                        </td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                    <p className="text-[11px] text-slate-600 mt-2">
                                        ⚠️ Total weight shift of {data.summary?.totalWeightShifted}% across {data.summary?.holdingsWithChanges} holdings.
                                        Status: <span className={data.status === 'PROPOSED' ? 'text-amber-400' : data.status === 'APPROVED' ? 'text-green-400' : 'text-indigo-400'}>{data.status}</span>.
                                        {data.status === 'PROPOSED' && ' Run /update-portfolio-targets to apply.'}
                                    </p>
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

function HoldingTable({ holdings, title }: { holdings: any[]; title: string }) {
    if (!holdings.length) return <div className="text-slate-500 text-sm">No holdings in this group.</div>;
    return (
        <div>
            <div className="text-[10px] uppercase tracking-widest font-black text-slate-500 mb-2">{title}</div>
            <div className="rounded-xl overflow-hidden border border-slate-800">
                <table className="w-full text-sm">
                    <thead>
                        <tr className="bg-slate-900 border-b border-slate-800">
                            {['Ticker', 'Action', 'Actual %', 'Proposed %', 'Δ', 'Rationale'].map(h => (
                                <th key={h} className="px-3 py-2.5 text-left text-[10px] font-black uppercase tracking-widest text-slate-500">{h}</th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {holdings.map((h: any) => (
                            <tr key={h.ticker} className="border-b border-slate-800/50 hover:bg-white/[0.02]">
                                <td className="px-3 py-3 font-black text-white tracking-tighter">{h.ticker}</td>
                                <td className="px-3 py-3">
                                    <span className={`text-[10px] font-black uppercase ${getActionTextClass(h.action)}`}>{h.action}</span>
                                </td>
                                <td className="px-3 py-3 font-mono text-xs text-slate-400">{(h.actualPct ?? 0).toFixed(2)}%</td>
                                <td className="px-3 py-3 font-mono text-xs text-white">{h.recommendedTarget?.toFixed(2)}%</td>
                                <td className="px-3 py-3">
                                    <div className="flex items-center gap-1">
                                        <DeltaIcon delta={h.actualDelta ?? h.delta ?? 0} />
                                        <span className={`font-mono text-xs ${(h.actualDelta ?? h.delta ?? 0) > 0.05 ? 'text-green-400' : (h.actualDelta ?? h.delta ?? 0) < -0.05 ? 'text-red-400' : 'text-slate-500'}`}>
                                            {(h.actualDelta ?? h.delta) != null ? `${(h.actualDelta ?? h.delta) > 0 ? '+' : ''}${(h.actualDelta ?? h.delta).toFixed(2)}pp` : '—'}
                                        </span>
                                    </div>
                                </td>
                                <td className="px-3 py-3 text-xs text-slate-400 max-w-xs truncate" title={h.rationale}>{h.rationale}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
