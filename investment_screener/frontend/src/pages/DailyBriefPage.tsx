/**
 * DailyBriefPage.tsx (React Page)
 *
 * Purpose:
 *     Displays the latest daily portfolio brief — macro regime, conviction-scored
 *     holdings (ACCUMULATE / HOLD / WATCH / REDUCE / EXIT), earnings calendar
 *     binary event flags, pillar health aggregation, and score delta vs. yesterday.
 *     Reads from /api/daily-brief/latest which serves the JSON snapshot produced by
 *     plugins/portfolio-advisor/scripts/daily_brief.py.
 *
 * Layer: Frontend / Pages
 */
import { useState, useEffect } from 'react';
import { AlertTriangle, TrendingUp, TrendingDown, Minus, Calendar, Shield, Activity, RefreshCw, Target, Lock } from 'lucide-react';
import { TradeButtons } from '../components/TradeButtons';
import { tradeIntent, REC_CHIP_STYLES } from '../utils/recommendationPresentation';

interface MacroRegime {
    regime: 'RISK-ON' | 'NEUTRAL' | 'RISK-OFF';
    score: number;
    vix: number;
    vix_signal: string;
    spy_vs_200d: number;
    spy_signal: string;
    credit_signal: string;
    details: string[];
}

interface ConvictionScore {
    ticker: string;
    total: number;
    band: 'ACCUMULATE' | 'HOLD' | 'WATCH' | 'REDUCE' | 'EXIT';
    dcf_pts: number;
    ta_pts: number;
    weight_gap_pts: number;
    momentum_pts: number;
    dcf_action: string | null;
    pct_to_fv: number | null;
    rsi: number | null;
    adx: number | null;
    vol_bias: number | null;
    actual_weight: number | null;
    target_weight: number | null;
    weight_gap: number | null;
    flags: string[];
    ta_staleness_days: number | null;
}

interface EarningsEntry {
    ticker: string;
    earnings_date: string | null;
    days_away: number | null;
    flag: 'IMMINENT' | 'APPROACHING' | 'UPCOMING' | 'OK' | 'UNKNOWN';
}

interface PillarHealth {
    pillar: string;
    avg_score: number;
    count: number;
    min: number;
    max: number;
}

interface StandingDecision {
    type: string;
    reason: string;
    source?: string;
    maxEntryPrice?: number;
}

interface ProposedTrade {
    side: 'buy' | 'sell';
    ticker: string;
    approxValueUSD: number;
}

interface Recommendation {
    ticker: string;
    signal: string;
    score: number;
    held: boolean;
    recommendation: string;
    rationale: string;
    actionable: boolean;
    urgency: number;
    standingDecision: StandingDecision | null;
    earnings: EarningsEntry | null;
    proposedTrade: ProposedTrade | null;
}

interface DailyBrief {
    date: string;
    timestamp: string;
    macro_regime: MacroRegime;
    ta_refreshed: boolean;
    conviction_scores: ConvictionScore[];
    recommendations?: Recommendation[];
    total_equity?: number;
    score_deltas: Record<string, number>;
    pillar_health: PillarHealth[];
    pillar_deltas: Record<string, number>;
    earnings_flags: EarningsEntry[];
    yesterday_date: string | null;
}

const BAND_STYLES: Record<string, { bg: string; text: string; border: string }> = {
    ACCUMULATE: { bg: 'bg-emerald-500/10', text: 'text-emerald-400', border: 'border-emerald-500/30' },
    HOLD:       { bg: 'bg-sky-500/10',     text: 'text-sky-400',     border: 'border-sky-500/30' },
    WATCH:      { bg: 'bg-amber-500/10',   text: 'text-amber-400',   border: 'border-amber-500/30' },
    REDUCE:     { bg: 'bg-orange-500/10',  text: 'text-orange-400',  border: 'border-orange-500/30' },
    EXIT:       { bg: 'bg-red-500/10',     text: 'text-red-400',     border: 'border-red-500/30' },
};

const REGIME_STYLES: Record<string, { bg: string; text: string; label: string }> = {
    'RISK-ON':  { bg: 'bg-emerald-500/15', text: 'text-emerald-300', label: '✅ RISK-ON'  },
    'NEUTRAL':  { bg: 'bg-amber-500/15',   text: 'text-amber-300',   label: '⚠️ NEUTRAL'  },
    'RISK-OFF': { bg: 'bg-red-500/15',     text: 'text-red-300',     label: '🔴 RISK-OFF' },
};

function ScoreBadge({ score }: { score: number }) {
    const color = score >= 3 ? 'text-emerald-400' : score >= 1 ? 'text-sky-400' :
                  score === 0 ? 'text-amber-400' : score >= -2 ? 'text-orange-400' : 'text-red-400';
    return <span className={`font-mono font-bold ${color}`}>{score > 0 ? `+${score}` : score}</span>;
}

function DeltaBadge({ delta }: { delta: number }) {
    if (delta === 0) return <span className="text-zinc-500">—</span>;
    const color = delta > 0 ? 'text-emerald-400' : 'text-red-400';
    const Icon = delta > 0 ? TrendingUp : TrendingDown;
    return (
        <span className={`flex items-center gap-0.5 ${color} text-xs`}>
            <Icon size={11} />
            {delta > 0 ? `+${delta}` : delta}
        </span>
    );
}

export default function DailyBriefPage() {
    const [brief, setBrief] = useState<DailyBrief | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [activeFilter, setActiveFilter] = useState<string>('all');

    useEffect(() => {
        fetch('/api/daily-brief/latest')
            .then(r => r.ok ? r.json() : Promise.reject(r.statusText))
            .then(setBrief)
            .catch(e => setError(String(e)))
            .finally(() => setLoading(false));
    }, []);

    if (loading) return (
        <div className="flex items-center justify-center h-64 text-zinc-400">
            <RefreshCw className="animate-spin mr-2" size={18} /> Loading daily brief...
        </div>
    );

    if (error || !brief) return (
        <div className="p-8">
            <div className="bg-zinc-900 border border-zinc-700 rounded-lg p-6 text-center">
                <AlertTriangle className="mx-auto mb-3 text-amber-400" size={32} />
                <p className="text-zinc-300 mb-2">No daily brief available.</p>
                <p className="text-zinc-500 text-sm mb-4">
                    Run the daily brief script to generate today's analysis:
                </p>
                <code className="block bg-zinc-800 rounded px-4 py-2 text-emerald-300 text-sm font-mono">
                    python3 plugins/portfolio-advisor/scripts/daily_brief.py
                </code>
                {error && <p className="text-red-400 text-xs mt-3">{error}</p>}
            </div>
        </div>
    );

    const macro     = brief.macro_regime;
    const regStyle  = REGIME_STYLES[macro.regime] ?? REGIME_STYLES['NEUTRAL'];
    const scores    = brief.conviction_scores ?? [];
    const deltas    = brief.score_deltas ?? {};
    const earnings  = (brief.earnings_flags ?? []).filter(e => e.flag !== 'OK' && e.flag !== 'UNKNOWN');
    const pillars   = brief.pillar_health ?? [];
    const pDeltas   = brief.pillar_deltas ?? {};

    const filtered = activeFilter === 'all' ? scores :
        scores.filter(s => s.band === activeFilter.toUpperCase());

    const bandCounts = {
        ACCUMULATE: scores.filter(s => s.band === 'ACCUMULATE').length,
        HOLD:       scores.filter(s => s.band === 'HOLD').length,
        WATCH:      scores.filter(s => s.band === 'WATCH').length,
        REDUCE:     scores.filter(s => s.band === 'REDUCE').length,
        EXIT:       scores.filter(s => s.band === 'EXIT').length,
    };

    return (
        <div className="p-6 space-y-6 max-w-7xl mx-auto">

            {/* Header */}
            <div className="flex items-start justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-white">Daily Portfolio Brief</h1>
                    <p className="text-zinc-400 text-sm mt-1">
                        {brief.date}
                        {brief.yesterday_date && <span className="ml-2 text-zinc-600">· vs {brief.yesterday_date}</span>}
                        {brief.ta_refreshed && <span className="ml-2 text-emerald-600 text-xs">· TA refreshed</span>}
                    </p>
                </div>
                <div className={`px-4 py-2 rounded-lg border ${regStyle.bg} border-zinc-700`}>
                    <span className={`font-bold text-lg ${regStyle.text}`}>{regStyle.label}</span>
                    <span className="text-zinc-400 text-sm ml-2">score={macro.score}</span>
                </div>
            </div>

            {/* Macro + Earnings row */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

                {/* Macro details */}
                <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-3">
                        <Shield size={16} className="text-zinc-400" />
                        <h2 className="text-sm font-semibold text-zinc-300 uppercase tracking-wide">Macro Regime</h2>
                    </div>
                    <div className="space-y-1">
                        {macro.details.map((d, i) => (
                            <p key={i} className="text-sm text-zinc-400 font-mono">{d}</p>
                        ))}
                    </div>
                    {macro.regime === 'RISK-OFF' && (
                        <p className="mt-3 text-red-400 text-xs bg-red-500/10 rounded px-3 py-2 border border-red-500/20">
                            ⛔ Gate all ACCUMULATE signals. Execute REDUCE / EXIT only today.
                        </p>
                    )}
                    {macro.regime === 'NEUTRAL' && (
                        <p className="mt-3 text-amber-400 text-xs bg-amber-500/10 rounded px-3 py-2 border border-amber-500/20">
                            ⚠️ Only score ≥ +4 ACCUMULATE candidates are actionable.
                        </p>
                    )}
                </div>

                {/* Earnings calendar */}
                <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-3">
                        <Calendar size={16} className="text-zinc-400" />
                        <h2 className="text-sm font-semibold text-zinc-300 uppercase tracking-wide">
                            Binary Events {earnings.length > 0 && <span className="text-amber-400">({earnings.length})</span>}
                        </h2>
                    </div>
                    {earnings.length === 0 ? (
                        <p className="text-zinc-600 text-sm">No earnings within 30 days.</p>
                    ) : (
                        <div className="space-y-2">
                            {earnings.map(e => {
                                const isUrgent = e.flag === 'IMMINENT' || e.flag === 'APPROACHING';
                                return (
                                    <div key={e.ticker}
                                         className={`flex items-center justify-between text-sm px-3 py-1.5 rounded border
                                             ${isUrgent ? 'bg-amber-500/10 border-amber-500/30' : 'bg-zinc-800 border-zinc-700'}`}>
                                        <span className="font-mono font-bold text-white">{e.ticker}</span>
                                        <span className="text-zinc-400">{e.earnings_date ?? '—'}</span>
                                        <span className={`text-xs px-1.5 py-0.5 rounded font-medium
                                            ${e.flag === 'IMMINENT' ? 'bg-red-500/20 text-red-300' :
                                              e.flag === 'APPROACHING' ? 'bg-amber-500/20 text-amber-300' :
                                              'bg-zinc-700 text-zinc-400'}`}>
                                            {e.days_away}d · {e.flag}
                                        </span>
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </div>
            </div>

            {/* Recommendations — summarized actions with rationales */}
            {(brief.recommendations ?? []).length > 0 && (
                <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
                    <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-2">
                            <Target size={16} className="text-zinc-400" />
                            <h2 className="text-sm font-semibold text-zinc-300 uppercase tracking-wide">
                                Recommendations ({(brief.recommendations ?? []).length})
                            </h2>
                        </div>
                        <p className="text-xs text-zinc-600">
                            Review each rationale — buttons open the order prep flow, nothing executes without your confirm.
                        </p>
                    </div>
                    <div className="space-y-3">
                        {(brief.recommendations ?? []).map(rec => {
                            const chip = REC_CHIP_STYLES[rec.recommendation] ?? REC_CHIP_STYLES.HOLD;
                            const sigStyle = BAND_STYLES[rec.signal] ?? BAND_STYLES.HOLD;
                            const intent = tradeIntent(rec.recommendation);
                            return (
                                <div key={rec.ticker}
                                     className="flex flex-col md:flex-row md:items-center gap-3 bg-zinc-800/60 border border-zinc-700/60 rounded-lg px-4 py-3">
                                    {/* Left: ticker + chips */}
                                    <div className="flex items-center gap-2 md:w-64 shrink-0 flex-wrap">
                                        <span className="text-zinc-600 text-xs font-mono w-5">{rec.urgency}.</span>
                                        <span className="font-mono font-bold text-white text-base">{rec.ticker}</span>
                                        <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium border ${sigStyle.bg} ${sigStyle.text} ${sigStyle.border}`}>
                                            {rec.signal} <ScoreBadge score={rec.score} />
                                        </span>
                                        <span className={`px-2 py-0.5 rounded text-xs font-bold border ${chip.bg} ${chip.text} ${chip.border}`}>
                                            {rec.recommendation.replace('_', ' ')}
                                        </span>
                                    </div>

                                    {/* Middle: rationale + standing decision */}
                                    <div className="flex-1 min-w-0">
                                        <p className="text-sm text-zinc-300 leading-snug">{rec.rationale}</p>
                                        {rec.standingDecision && (
                                            <p className="mt-1 flex items-center gap-1.5 text-xs text-amber-400/90">
                                                <Lock size={11} className="shrink-0" />
                                                Standing decision · {rec.standingDecision.type.replace(/_/g, ' ')}
                                                {rec.standingDecision.source && (
                                                    <span className="text-zinc-600">— {rec.standingDecision.source}</span>
                                                )}
                                            </p>
                                        )}
                                    </div>

                                    {/* Right: proposed value + action buttons */}
                                    <div className="flex items-center gap-3 shrink-0">
                                        {rec.proposedTrade && (
                                            <span className="text-sm font-mono text-zinc-400">
                                                ~${rec.proposedTrade.approxValueUSD.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                                            </span>
                                        )}
                                        {rec.actionable && intent ? (
                                            <TradeButtons ticker={rec.ticker} rating={intent.rating} size="md" />
                                        ) : (
                                            <span className="text-xs text-zinc-600 italic px-2">
                                                {rec.recommendation === 'QUEUED' ? 'macro-gated' : 'no trade without your direction'}
                                            </span>
                                        )}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>
            )}

            {/* Pillar health */}
            {pillars.length > 0 && (
                <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-3">
                        <Activity size={16} className="text-zinc-400" />
                        <h2 className="text-sm font-semibold text-zinc-300 uppercase tracking-wide">Pillar Health</h2>
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                        {pillars.map(p => {
                            const pd = pDeltas[p.pillar];
                            const avgColor = p.avg_score >= 2 ? 'text-emerald-400' :
                                            p.avg_score >= 0 ? 'text-sky-400' :
                                            p.avg_score >= -1 ? 'text-amber-400' : 'text-red-400';
                            return (
                                <div key={p.pillar} className="bg-zinc-800 rounded-lg p-3 border border-zinc-700">
                                    <p className="text-xs text-zinc-500 truncate mb-1">{p.pillar}</p>
                                    <div className="flex items-center justify-between">
                                        <span className={`text-xl font-bold font-mono ${avgColor}`}>
                                            {p.avg_score > 0 ? `+${p.avg_score}` : p.avg_score}
                                        </span>
                                        {pd !== undefined && pd !== 0 && (
                                            <DeltaBadge delta={Math.round(pd)} />
                                        )}
                                    </div>
                                    <p className="text-xs text-zinc-600 mt-1">
                                        n={p.count} · [{p.min > 0 ? '+' : ''}{p.min}→{p.max > 0 ? '+' : ''}{p.max}]
                                    </p>
                                </div>
                            );
                        })}
                    </div>
                </div>
            )}

            {/* Conviction scores table */}
            <div className="bg-zinc-900 border border-zinc-800 rounded-lg">
                {/* Filter bar */}
                <div className="flex items-center gap-2 p-4 border-b border-zinc-800 flex-wrap">
                    <span className="text-xs text-zinc-500 mr-1">Filter:</span>
                    {(['all', 'ACCUMULATE', 'HOLD', 'WATCH', 'REDUCE', 'EXIT'] as const).map(f => {
                        const style = f === 'all' ? { text: 'text-zinc-300', bg: 'bg-zinc-700' } :
                                      BAND_STYLES[f] ?? { text: 'text-zinc-400', bg: 'bg-zinc-800' };
                        const count = f === 'all' ? scores.length : bandCounts[f as keyof typeof bandCounts];
                        const isActive = activeFilter === f;
                        return (
                            <button key={f}
                                    onClick={() => setActiveFilter(f)}
                                    className={`px-3 py-1 rounded-full text-xs font-medium border transition-all
                                        ${isActive ? `${style.bg} ${style.text} border-transparent` :
                                                     `bg-transparent ${style.text} border-zinc-700 opacity-60 hover:opacity-100`}`}>
                                {f === 'all' ? `All (${count})` : `${f} (${count})`}
                            </button>
                        );
                    })}
                </div>

                {/* Table */}
                <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="text-xs text-zinc-500 uppercase tracking-wide border-b border-zinc-800">
                                <th className="text-left px-4 py-3">Ticker</th>
                                <th className="text-center px-3 py-3">Score</th>
                                <th className="text-center px-3 py-3">Band</th>
                                <th className="text-center px-3 py-3">DCF</th>
                                <th className="text-center px-3 py-3">TA</th>
                                <th className="text-center px-3 py-3">Gap</th>
                                <th className="text-center px-3 py-3">Mom</th>
                                <th className="text-left px-3 py-3">DCF Action</th>
                                <th className="text-center px-3 py-3">%→FV</th>
                                <th className="text-center px-3 py-3">RSI</th>
                                <th className="text-center px-3 py-3">ADX</th>
                                <th className="text-center px-3 py-3">Wgt Gap</th>
                                <th className="text-center px-3 py-3">Δ</th>
                                <th className="text-left px-3 py-3">Flags</th>
                            </tr>
                        </thead>
                        <tbody>
                            {filtered.map(s => {
                                const bs = BAND_STYLES[s.band] ?? BAND_STYLES.HOLD;
                                const delta = deltas[s.ticker];
                                return (
                                    <tr key={s.ticker}
                                        className="border-b border-zinc-800/50 hover:bg-zinc-800/40 transition-colors">
                                        <td className="px-4 py-2.5 font-mono font-bold text-white">{s.ticker}</td>
                                        <td className="px-3 py-2.5 text-center">
                                            <ScoreBadge score={s.total} />
                                        </td>
                                        <td className="px-3 py-2.5 text-center">
                                            <span className={`px-2 py-0.5 rounded text-xs font-medium border ${bs.bg} ${bs.text} ${bs.border}`}>
                                                {s.band}
                                            </span>
                                        </td>
                                        <td className="px-3 py-2.5 text-center text-zinc-400 font-mono text-xs">
                                            {s.dcf_pts > 0 ? `+${s.dcf_pts}` : s.dcf_pts}
                                        </td>
                                        <td className="px-3 py-2.5 text-center text-zinc-400 font-mono text-xs">
                                            {s.ta_pts > 0 ? `+${s.ta_pts}` : s.ta_pts}
                                        </td>
                                        <td className="px-3 py-2.5 text-center text-zinc-400 font-mono text-xs">
                                            {s.weight_gap_pts > 0 ? `+${s.weight_gap_pts}` : s.weight_gap_pts}
                                        </td>
                                        <td className="px-3 py-2.5 text-center text-zinc-400 font-mono text-xs">
                                            {s.momentum_pts > 0 ? `+${s.momentum_pts}` : s.momentum_pts}
                                        </td>
                                        <td className="px-3 py-2.5">
                                            <span className={`text-xs font-medium
                                                ${(s.dcf_action ?? '').toUpperCase() === 'BUY' || (s.dcf_action ?? '').toUpperCase() === 'ACCUMULATE'
                                                    ? 'text-emerald-400'
                                                    : (s.dcf_action ?? '').toUpperCase() === 'SELL'
                                                    ? 'text-red-400'
                                                    : (s.dcf_action ?? '').toUpperCase() === 'TRIM'
                                                    ? 'text-orange-400'
                                                    : 'text-zinc-400'}`}>
                                                {s.dcf_action ?? '—'}
                                            </span>
                                        </td>
                                        <td className="px-3 py-2.5 text-center font-mono text-xs">
                                            {s.pct_to_fv !== null
                                                ? <span className={s.pct_to_fv > 0 ? 'text-emerald-400' : 'text-red-400'}>
                                                    {s.pct_to_fv > 0 ? '+' : ''}{s.pct_to_fv?.toFixed(1)}%
                                                  </span>
                                                : <span className="text-zinc-600">—</span>}
                                        </td>
                                        <td className={`px-3 py-2.5 text-center font-mono text-xs
                                            ${(s.rsi ?? 50) < 35 ? 'text-emerald-400' :
                                              (s.rsi ?? 50) > 70 ? 'text-red-400' : 'text-zinc-400'}`}>
                                            {s.rsi?.toFixed(1) ?? '—'}
                                        </td>
                                        <td className="px-3 py-2.5 text-center font-mono text-xs text-zinc-400">
                                            {s.adx?.toFixed(1) ?? '—'}
                                        </td>
                                        <td className={`px-3 py-2.5 text-center font-mono text-xs
                                            ${(s.weight_gap ?? 0) > 0.5 ? 'text-emerald-400' :
                                              (s.weight_gap ?? 0) < -0.5 ? 'text-orange-400' : 'text-zinc-400'}`}>
                                            {s.weight_gap !== null
                                                ? `${s.weight_gap > 0 ? '+' : ''}${s.weight_gap.toFixed(1)}%`
                                                : '—'}
                                        </td>
                                        <td className="px-3 py-2.5 text-center">
                                            {delta !== undefined ? <DeltaBadge delta={delta} /> : <Minus size={12} className="text-zinc-700 mx-auto" />}
                                        </td>
                                        <td className="px-3 py-2.5">
                                            <div className="flex flex-wrap gap-1">
                                                {s.flags.slice(0, 3).map(f => (
                                                    <span key={f} className="text-xs bg-zinc-800 text-zinc-400 px-1.5 py-0.5 rounded font-mono">
                                                        {f}
                                                    </span>
                                                ))}
                                            </div>
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}
