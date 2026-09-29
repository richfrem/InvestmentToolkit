/**
 * PerformanceMetrics.tsx (React Component)
 * =====================================
 *
 * Purpose:
 *     Simple display of performance statistics for a stock across multiple time horizons.
 *
 * Layer: Frontend / UI / Components
 *
 * Usage Examples:
 *     <PerformanceMetrics performance={stockData.performance} />
 *
 * Key Functions:
 *     - PerformanceMetrics() - Functional component that maps performance timeframes to visual indicators
 */
import type { StockData } from '../services/api';
import { PRICE_CHANGE_PERIODS, getPeriodChange } from '../utils/priceChangePeriods';

interface PerformanceMetricsProps {
    performance: StockData['performance'];
}

export default function PerformanceMetrics({ performance }: PerformanceMetricsProps) {
    if (!performance) return null;

    // Periods come from the shared list; values are the backend's shared
    // price_changes calculation (null when history doesn't reach — chip hidden).
    const metrics = PRICE_CHANGE_PERIODS.map(p => ({ label: p.label, value: getPeriodChange(performance, p.key) }));

    return (
        <div className="flex gap-1.5 items-center">
            {metrics.filter((m) => m.value != null).map((m) => {
                const isPositive = (m.value as number) >= 0;
                return (
                    <div
                        key={m.label}
                        className={`flex flex-col px-2 py-0.5 rounded border min-w-[54px] text-center
                            ${isPositive
                                ? 'bg-green-500/10 border-green-500/20'
                                : 'bg-red-500/10 border-red-500/20'
                            }`}
                    >
                        <span className="text-[9px] text-slate-500 uppercase font-bold leading-tight">{m.label}</span>
                        <span className={`text-[11px] font-black ${isPositive ? 'text-green-400' : 'text-red-400'} leading-tight`}>
                            {isPositive ? '+' : ''}{(m.value as number).toFixed(1)}%
                        </span>
                    </div>
                );
            })}
        </div>
    );
}
