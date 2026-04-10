import {
    AreaChart,
    Area,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
    ResponsiveContainer,
} from 'recharts';
import type { StockData } from '../../services/api';

interface FundamentalChartProps {
    stockData: StockData;
}

export default function FundamentalChart({ stockData }: FundamentalChartProps) {
    // stockData.financials.historical_revenue is array of numbers
    // we assume they are last 4-5 years ordered? 
    // fetch_financials.py: "historical_revenue": financials.loc['Total Revenue'].head(5).tolist()[::-1] if 'Total Revenue' in financials.index else [],
    // So it returns last 5 years reversed (Chronological: Oldest -> Newest). Correct.

    const revenues = stockData.financials.historical_revenue || [];
    const income = stockData.financials.historical_net_income || [];

    const years = Array.from({ length: revenues.length }, (_, i) => new Date().getFullYear() - (revenues.length - 1) + i);

    const data = years.map((year, index) => ({
        year: year.toString(),
        revenue: revenues[index] || 0,
        netIncome: income[index] || 0,
    }));

    const formatCurrency = (value: number) => {
        if (Math.abs(value) >= 1e9) return `$${(value / 1e9).toFixed(1)}B`;
        if (Math.abs(value) >= 1e6) return `$${(value / 1e6).toFixed(1)}M`;
        return `$${value}`;
    };

    return (
        <div className="bg-surface p-6 rounded-xl border border-slate-800 h-[400px]">
            <h3 className="text-secondary font-medium uppercase tracking-wider text-sm mb-4">Fundamentals</h3>
            <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={data}>
                    <defs>
                        <linearGradient id="colorRevenue" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#22c55e" stopOpacity={0.3} />
                            <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
                        </linearGradient>
                        <linearGradient id="colorIncome" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.3} />
                            <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
                        </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                    <XAxis dataKey="year" stroke="#94a3b8" fontSize={12} tickLine={false} axisLine={false} />
                    <YAxis stroke="#94a3b8" fontSize={12} tickLine={false} axisLine={false} tickFormatter={formatCurrency} />
                    <Tooltip
                        formatter={(value: number | string | Array<number | string> | undefined) => formatCurrency(Number(value || 0))}
                        contentStyle={{ backgroundColor: '#0f172a', borderColor: '#1e293b', color: '#e2e8f0' }}
                        itemStyle={{ color: '#e2e8f0' }}
                    />
                    <Legend />
                    <Area type="monotone" dataKey="revenue" name="Total Revenue" stroke="#22c55e" fillOpacity={1} fill="url(#colorRevenue)" />
                    <Area type="monotone" dataKey="netIncome" name="Net Income" stroke="#f59e0b" fillOpacity={1} fill="url(#colorIncome)" />
                </AreaChart>
            </ResponsiveContainer>
        </div>
    );
}
