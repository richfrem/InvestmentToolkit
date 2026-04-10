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
        <div className="flex gap-2 flex-wrap">
            {metrics.map((m) => {
                const isPositive = m.value >= 0;
                return (
                    <div
                        key={m.label}
                        className={`flex flex-col px-2 py-1 rounded border min-w-[60px] text-center
                            ${isPositive
                                ? 'bg-green-500/5 border-green-500/20'
                                : 'bg-red-500/5 border-red-500/20'
                            }`}
                    >
                        <span className="text-[10px] text-secondary uppercase font-semibold">{m.label}</span>
                        <span className={`text-xs font-bold ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
                            {isPositive ? '+' : ''}{m.value.toFixed(1)}%
                        </span>
                    </div>
                );
            })}
        </div>
    );
}
