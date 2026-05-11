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

interface PerformanceMetricsProps {
    performance: StockData['performance'];
}

export default function PerformanceMetrics({ performance }: PerformanceMetricsProps) {
    if (!performance) return null;

    const metrics = [
        { label: '1D', value: performance['1d'] },
        { label: '1W', value: performance['1w'] },
        { label: '1M', value: performance['1m'] },
        { label: '3M', value: performance['3m'] },
        { label: 'YTD', value: performance['ytd'] },
        { label: '1Y', value: performance['1y'] },
        { label: '5Y', value: performance['5y'] },
    ];

    return (
        <div className="flex gap-1.5 items-center">
            {metrics.map((m) => {
                const isPositive = m.value >= 0;
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
                            {isPositive ? '+' : ''}{m.value.toFixed(1)}%
                        </span>
                    </div>
                );
            })}
        </div>
    );
}
