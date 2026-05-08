import { useState, useEffect } from 'react';
import {
    fetchPortfolioSummary,
    fetchPortfolioPerformance,
    fetchStrategyAllocation,
    type PortfolioSummary,
    type PortfolioPerformance,
    type StrategyAllocation,
} from '../services/api';
import PortfolioSummaryCards from '../components/PortfolioSummaryCards';
import PortfolioBreakdown from '../components/PortfolioBreakdown';
import StrategyAllocationChart from '../components/StrategyAllocationChart';

function PeriodCard({
    label,
    perf,
    loading,
}: {
    label: string;
    perf: { change: number; changePct: number } | null | undefined;
    loading: boolean;
}) {
    const isPos = (perf?.change ?? 0) >= 0;
    const sign = isPos ? '+' : '';
    const color = (perf?.change ?? 0) > 0 ? 'text-emerald-400' : (perf?.change ?? 0) < 0 ? 'text-red-400' : 'text-slate-400';
    const glow = (perf?.change ?? 0) > 0 ? 'shadow-emerald-500/10' : (perf?.change ?? 0) < 0 ? 'shadow-red-500/10' : '';

    function fmt(v: number) {
        const abs = Math.abs(v);
        if (abs >= 1000) return `$${Math.abs(v).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
        return `$${Math.abs(v).toFixed(2)}`;
    }

    return (
        <div className={`bg-slate-900/80 border border-slate-800 rounded-xl px-4 py-3 shadow-lg flex items-center gap-4 ${glow}`}>
            <div className="text-xs font-bold text-slate-500 uppercase tracking-widest w-14 shrink-0">{label}</div>
            {loading ? (
                <div className="flex gap-3 items-center">
                    <div className="h-6 w-20 bg-slate-800 rounded animate-pulse" />
                    <div className="h-4 w-14 bg-slate-800/60 rounded animate-pulse" />
                </div>
            ) : perf ? (
                <div className="flex items-baseline gap-3">
                    <span className={`text-xl font-bold ${color}`}>{sign}{perf.changePct.toFixed(2)}%</span>
                    <span className={`text-sm font-semibold ${color}`}>{sign}{fmt(perf.change)}</span>
                </div>
            ) : (
                <div className="text-slate-600 text-sm">Unavailable</div>
            )}
        </div>
    );
}

export default function PortfolioSummaryPage() {
    const [summary, setSummary] = useState<PortfolioSummary | null>(null);
    const [perf, setPerf] = useState<PortfolioPerformance | null>(null);
    const [allocation, setAllocation] = useState<StrategyAllocation | null>(null);
    const [loading, setLoading] = useState(true);
    const [perfLoading, setPerfLoading] = useState(true);
    const [allocLoading, setAllocLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [lastRefreshedAt, setLastRefreshedAt] = useState<Date | null>(null);

    useEffect(() => {
        fetchPortfolioSummary()
            .then(d => { setSummary(d); setLastRefreshedAt(new Date()); })
            .catch(err => setError(err.message || 'Failed to load portfolio summary'))
            .finally(() => setLoading(false));

        // Strategy allocation is fast (pure Node.js file read)
        fetchStrategyAllocation()
            .then(setAllocation)
            .catch(() => setAllocation(null))
            .finally(() => setAllocLoading(false));

        // Performance is slow (yfinance) — load independently so it doesn't block the page
        fetchPortfolioPerformance()
            .then(setPerf)
            .catch(() => setPerf(null))
            .finally(() => setPerfLoading(false));
    }, []);

    if (loading) {
        return (
            <div className="p-6 h-full flex items-center justify-center">
                <div className="text-slate-500 text-sm">Loading portfolio summary...</div>
            </div>
        );
    }

    if (error || !summary) {
        return (
            <div className="p-6 h-full flex items-center justify-center">
                <div className="text-red-400 text-sm">{error || 'No data available'}</div>
            </div>
        );
    }

    return (
        <div className="p-4 h-full space-y-4">
            <div className="flex items-start justify-between">
                <div>
                    <h1 className="text-xl font-bold text-white mb-0.5">Portfolio Summary</h1>
                    <p className="text-sm text-slate-500">
                        YTD performance and total value across all accounts
                    </p>
                </div>
                {lastRefreshedAt && (
                    <div className="flex items-center gap-1 text-xs text-zinc-500 mt-1">
                        <span className="w-1.5 h-1.5 rounded-full inline-block bg-zinc-500" />
                        Refreshed · {lastRefreshedAt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                    </div>
                )}
            </div>

            {/* Row 1: Original 4 summary cards */}
            <PortfolioSummaryCards data={summary} />

            {/* Row 2: Period performance cards (1d / 1w / 1m) */}
            <div className="grid grid-cols-3 gap-3">
                <PeriodCard label="1D" perf={perf?.['1d']} loading={perfLoading} />
                <PeriodCard label="1W" perf={perf?.['1w']} loading={perfLoading} />
                <PeriodCard label="1M" perf={perf?.['1m']} loading={perfLoading} />
            </div>

            {/* Row 3: Strategy allocation chart */}
            <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 shadow-lg">
                <div className="flex items-center justify-between mb-3">
                    <div>
                        <h3 className="text-sm font-bold text-slate-500 uppercase tracking-widest">Strategy Allocation</h3>
                        <p className="text-xs text-slate-600 mt-0.5">Actual holdings by investment pillar</p>
                    </div>
                </div>
                {allocLoading ? (
                    <div className="h-[280px] flex items-center justify-center">
                        <div className="text-slate-600 text-sm">Loading allocation...</div>
                    </div>
                ) : allocation && allocation.allocation.length > 0 ? (
                    <StrategyAllocationChart
                        data={allocation.allocation}
                        totalUSD={allocation.totalUSD}
                        usdCadRate={summary.liveUsdCadRate}
                    />
                ) : (
                    <div className="h-[300px] flex items-center justify-center text-slate-600 text-sm">
                        No allocation data available
                    </div>
                )}
            </div>

            {/* Row 4: Detailed breakdown table */}
            <PortfolioBreakdown data={summary} />
        </div>
    );
}
