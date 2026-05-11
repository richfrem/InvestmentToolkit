/**
 * FinancialChart.tsx (React Component)
 * =====================================
 *
 * Purpose:
 *     Dynamic multi-mode chart for visualizing historical and forecasted financial data (Revenue, NI, EPS, FCF).
 *
 * Layer: Frontend / UI / Components / Analysis
 *
 * Usage Examples:
 *     <FinancialChart stockData={stockData} mode="revenue" />
 *
 * Key Functions:
 *     - historicalData - Computed array of historical financial points aligned by year
 *     - forecastData - Computed array of analyst forecast points with low/high range cones
 *     - formatCurrency() - Formats numeric values into human-readable B/M strings
 *     - FinancialChart() - Main render logic that switches between Recharts configurations based on the 'mode' prop
 */
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
    const { financials, analyst_revenue_forecast, analyst_earnings_forecast } = stockData;
    const currentYear = new Date().getFullYear();

    // 1. Prepare Historical Data
    // We assume the backend returns 5 years ending in LAST FULL YEAR (usually currentYear - 1 or currentYear)
    const histCount = financials.historical_revenue?.length || 0;
    const historyStartYear = currentYear - histCount;

    const safeGet = (arr: number[] | undefined, index: number) =>
        arr && arr.length > index ? arr[index] : 0;

    const historicalData = Array.from({ length: histCount }, (_, i) => {
        const year = (historyStartYear + i).toString();

        const rev = safeGet(financials.historical_revenue, i);
        const ni = safeGet(financials.historical_net_income, i);
        const eps = safeGet(financials.historical_eps, i);

        const isLast = i === histCount - 1;

        return {
            year,
            type: 'history',
            revenue: rev,
            netIncome: ni,
            fcf: safeGet(financials.historical_fcf, i),
            eps: eps,
            grossMargin: safeGet(financials.historical_gross_margin, i),
            operatingMargin: safeGet(financials.historical_operating_margin, i),
            netMargin: safeGet(financials.historical_net_margin, i),

            // Forecast Anchors (Start from last history point)
            revForecastRange: isLast ? [rev, rev] : null,
            revForecastAvg: isLast ? rev : null,

            epsForecastRange: isLast ? [eps, eps] : null,
            epsForecastAvg: isLast ? eps : null,

            netIncomeForecastAvg: isLast ? ni : null,
        };
    });

    // 2. Prepare Forecast Data
    // We look for forecasts strictly AFTER the last historical year to avoid overlaps/drops
    const lastHistYear = parseInt(historicalData[historicalData.length - 1]?.year || (currentYear - 1).toString());

    const forecastMap = new Map<number, any>();

    if (analyst_revenue_forecast) {
        analyst_revenue_forecast.forEach((f) => {
            if (f.year > lastHistYear) {
                if (!forecastMap.has(f.year)) forecastMap.set(f.year, { year: f.year.toString(), type: 'forecast' });
                const entry = forecastMap.get(f.year);
                entry.revForecastAvg = f.avg;
                // Recharts Area range: [min, max]
                entry.revForecastRange = [f.low, f.high];
            }
        });
    }

    if (analyst_earnings_forecast) {
        analyst_earnings_forecast.forEach((f) => {
            if (f.year > lastHistYear) {
                if (!forecastMap.has(f.year)) forecastMap.set(f.year, { year: f.year.toString(), type: 'forecast' });
                const entry = forecastMap.get(f.year);

                entry.epsForecastAvg = f.avg;
                entry.epsForecastRange = [f.low, f.high];

                // Net Income approx (using shares from metrics)
                const shares = stockData.metrics.shares_outstanding || 0;
                if (shares > 0) {
                    entry.netIncomeForecastAvg = f.avg * shares;
                }
            }
        });
    }

    const forecastData = Array.from(forecastMap.values()).sort((a, b) => parseInt(a.year) - parseInt(b.year));

    // Combine
    const data = [...historicalData, ...forecastData];

    // 3. Formatters
    const formatCurrency = (val: number | undefined) => {
        if (val === undefined || val === null) return '';
        if (typeof val !== 'number') return '';
        if (Math.abs(val) >= 1e9) return `$${(val / 1e9).toFixed(1)}B`;
        if (Math.abs(val) >= 1e6) return `$${(val / 1e6).toFixed(1)}M`;
        return `$${val.toFixed(0)}`;
    };

    const formatPercentage = (val: number | undefined) => {
        if (typeof val !== 'number') return '';
        return `${val.toFixed(1)}%`;
    };

    const formatNumber = (val: number | undefined) => {
        if (typeof val !== 'number') return '';
        return val.toFixed(2);
    };

    // Tooltip custom label
    const tooltipFormatter = (value: any, name: any) => {
        if (Array.isArray(value)) {
            // Range
            return [`${formatCurrency(value[0])} - ${formatCurrency(value[1])}`, name];
        }
        if (String(name).includes("Forecast") || String(name).includes("Range")) {
            return [formatCurrency(value), name.replace("revForecast", "Rev ").replace("netIncomeForecast", "NI ").replace("Range", " Range")];
        }
        return [formatCurrency(value), name];
    };

    const epsTooltipFormatter = (value: any, name: any) => {
        if (Array.isArray(value)) {
            return [`${formatNumber(value[0])} - ${formatNumber(value[1])}`, name];
        }
        return [formatNumber(value), name];
    };

    // 4. Render
    if (mode === 'revenue') {
        return (
            <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#334155" opacity={0.5} />
                    <XAxis dataKey="year" stroke="#94a3b8" tick={{ fontSize: 12 }} tickLine={false} axisLine={false} />
                    <YAxis yAxisId="left" stroke="#94a3b8" tickFormatter={formatCurrency} tick={{ fontSize: 12 }} tickLine={false} axisLine={false} />
                    <Tooltip
                        contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', color: '#f8fafc' }}
                        formatter={tooltipFormatter}
                    />
                    <Legend wrapperStyle={{ paddingTop: '10px' }} />

                    {/* History */}
                    <Line yAxisId="left" type="monotone" dataKey="revenue" name="Revenue (Top Line)" stroke="#0ea5e9" strokeWidth={4} dot={{ r: 4, fill: '#0ea5e9' }} activeDot={{ r: 8 }} />
                    <Line yAxisId="left" type="monotone" dataKey="netIncome" name="Net Income (Bottom Line)" stroke="#10b981" strokeWidth={4} dot={{ r: 4, fill: '#10b981' }} activeDot={{ r: 8 }} />

                    {/* Forecast Revenue Range (Cone) */}
                    <Area yAxisId="left" type="monotone" dataKey="revForecastRange" name="Rev Range" stroke="none" fill="#38bdf8" fillOpacity={0.15} connectNulls />

                    {/* Forecast Revenue Avg */}
                    <Line yAxisId="left" type="monotone" dataKey="revForecastAvg" name="Rev Forecast" stroke="#38bdf8" strokeDasharray="5 5" strokeWidth={2} dot={{ r: 3 }} connectNulls />

                    {/* Forecast Net Income (Simple Line) */}
                    <Line yAxisId="left" type="monotone" dataKey="netIncomeForecastAvg" name="NI Forecast" stroke="#34d399" strokeDasharray="5 5" strokeWidth={2} dot={{ r: 3 }} connectNulls />
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
                        formatter={(val: any) => formatPercentage(val)}
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
                        formatter={(val: any) => formatCurrency(val)}
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
                        formatter={epsTooltipFormatter}
                    />
                    <Legend wrapperStyle={{ paddingTop: '10px' }} />
                    <Area type="monotone" dataKey="eps" name="EPS ($)" stroke="#8b5cf6" fillOpacity={1} fill="url(#colorEps)" strokeWidth={3} />

                    {/* EPS Forecast Range */}
                    <Area type="monotone" dataKey="epsForecastRange" name="EPS Range" stroke="none" fill="#a78bfa" fillOpacity={0.15} connectNulls />

                    {/* EPS Forecast Avg */}
                    <Line type="monotone" dataKey="epsForecastAvg" name="EPS Forecast" stroke="#a78bfa" strokeDasharray="5 5" strokeWidth={2} dot={{ r: 3 }} connectNulls />
                </ComposedChart>
            </ResponsiveContainer>
        );
    }

    return <div className="text-center text-slate-500 p-10">Select a chart mode</div>;
}
