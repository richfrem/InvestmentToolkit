import {
    ComposedChart,
    Bar,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
    ResponsiveContainer,
    Area
} from 'recharts';
import type { StockData } from '../../services/api';
import type { ChartMode } from './AnalysisChartToggle';

interface FinancialChartProps {
    stockData: StockData;
    mode: ChartMode;
}

export default function FinancialChart({ stockData, mode }: FinancialChartProps) {
    // Helper to generate simple year labels (assuming last 5 years)
    // In a production app, we would pass exact dates from backend.
    const currentYear = new Date().getFullYear();
    const generateYears = (count: number) =>
        Array.from({ length: count }, (_, i) => (currentYear - count + i + 1).toString());

    const years = generateYears(5);
    const financials = stockData.financials;

    // 1. Prepare Data for Recharts
    // Backend now returns [Oldest, ..., Newest]
    const data = years.map((year, i) => {
        // Safety check for array bounds
        const safeGet = (arr: number[] | undefined, index: number) =>
            arr && arr.length > index ? arr[index] : 0;

        return {
            year,
            revenue: safeGet(financials.historical_revenue, i),
            netIncome: safeGet(financials.historical_net_income, i),
            fcf: safeGet(financials.historical_fcf, i),
            eps: safeGet(financials.historical_eps, i),
            grossMargin: safeGet(financials.historical_gross_margin, i),
            operatingMargin: safeGet(financials.historical_operating_margin, i),
            netMargin: safeGet(financials.historical_net_margin, i),
        };
    });

    // 2. Formatters
    const formatCurrency = (val: number | undefined) => { // Fixed type
        if (val === undefined) return '';
        if (Math.abs(val) >= 1e9) return `$${(val / 1e9).toFixed(1)}B`;
        if (Math.abs(val) >= 1e6) return `$${(val / 1e6).toFixed(1)}M`;
        return `$${val.toFixed(0)}`;
    };

    const formatPercentage = (val: number | undefined) => val !== undefined ? `${val.toFixed(1)}%` : '';
    const formatNumber = (val: number | undefined) => val !== undefined ? val.toFixed(2) : '';

    // 3. Render Variants
    if (mode === 'revenue') {
        return (
            <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#334155" opacity={0.5} />
                    <XAxis dataKey="year" stroke="#94a3b8" tick={{ fontSize: 12 }} tickLine={false} axisLine={false} />
                    <YAxis yAxisId="left" stroke="#94a3b8" tickFormatter={formatCurrency} tick={{ fontSize: 12 }} tickLine={false} axisLine={false} />
                    <Tooltip
                        contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', color: '#f8fafc' }}
                        formatter={(value: number) => formatCurrency(value)}
                    />
                    <Legend wrapperStyle={{ paddingTop: '10px' }} />
                    <Bar yAxisId="left" dataKey="revenue" name="Total Revenue" fill="#0ea5e9" radius={[4, 4, 0, 0]} maxBarSize={50} />
                    <Line yAxisId="left" type="monotone" dataKey="netIncome" name="Net Income" stroke="#10b981" strokeWidth={3} dot={{ r: 4, fill: '#10b981' }} />
                </ComposedChart>
            </ResponsiveContainer>
        );
    }

    if (mode === 'margins') {
        return (
            <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#334155" opacity={0.5} />
                    <XAxis dataKey="year" stroke="#94a3b8" tick={{ fontSize: 12 }} tickLine={false} axisLine={false} />
                    <YAxis stroke="#94a3b8" tickFormatter={formatPercentage} domain={['auto', 'auto']} tick={{ fontSize: 12 }} tickLine={false} axisLine={false} />
                    <Tooltip
                        contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', color: '#f8fafc' }}
                        formatter={(value: number) => formatPercentage(value)}
                    />
                    <Legend wrapperStyle={{ paddingTop: '10px' }} />
                    <Line type="monotone" dataKey="grossMargin" name="Gross Margin" stroke="#a855f7" strokeWidth={3} dot={{ r: 4 }} />
                    <Line type="monotone" dataKey="operatingMargin" name="Operating Margin" stroke="#f59e0b" strokeWidth={3} dot={{ r: 4 }} />
                    <Line type="monotone" dataKey="netMargin" name="Net Margin" stroke="#10b981" strokeWidth={3} dot={{ r: 4 }} />
                </ComposedChart>
            </ResponsiveContainer>
        );
    }

    if (mode === 'fcf') {
        return (
            <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#334155" opacity={0.5} />
                    <XAxis dataKey="year" stroke="#94a3b8" tick={{ fontSize: 12 }} tickLine={false} axisLine={false} />
                    <YAxis stroke="#94a3b8" tickFormatter={formatCurrency} tick={{ fontSize: 12 }} tickLine={false} axisLine={false} />
                    <Tooltip
                        contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', color: '#f8fafc' }}
                        formatter={(value: number) => formatCurrency(value)}
                    />
                    <Legend wrapperStyle={{ paddingTop: '10px' }} />
                    <Bar dataKey="fcf" name="Free Cash Flow" fill="#14b8a6" radius={[4, 4, 0, 0]} maxBarSize={50} />
                </ComposedChart>
            </ResponsiveContainer>
        );
    }

    if (mode === 'eps') {
        return (
            <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                    <defs>
                        <linearGradient id="colorEps" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.3} />
                            <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0} />
                        </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#334155" opacity={0.5} />
                    <XAxis dataKey="year" stroke="#94a3b8" tick={{ fontSize: 12 }} tickLine={false} axisLine={false} />
                    <YAxis stroke="#94a3b8" tickFormatter={formatNumber} tick={{ fontSize: 12 }} tickLine={false} axisLine={false} />
                    <Tooltip
                        contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', color: '#f8fafc' }}
                        formatter={(value: number) => formatNumber(value)}
                    />
                    <Legend wrapperStyle={{ paddingTop: '10px' }} />
                    <Area type="monotone" dataKey="eps" name="EPS ($)" stroke="#8b5cf6" fillOpacity={1} fill="url(#colorEps)" strokeWidth={3} />
                </ComposedChart>
            </ResponsiveContainer>
        );
    }

    return <div className="text-center text-slate-500 p-10">Select a chart mode</div>;
}
