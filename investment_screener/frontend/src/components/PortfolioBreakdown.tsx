/**
 * PortfolioBreakdown.tsx (React Component)
 * =====================================
 *
 * Purpose:
 *     Table displaying total market value, book value, and unrealized gains in USD and CAD.
 *
 * Layer: Frontend / UI / Components
 *
 * Usage Examples:
 *     <PortfolioBreakdown data={summaryData} />
 *
 * Key Functions:
 *     - formatCurrency() - Formats numeric values as localized currency strings with 2 decimal places
 *     - PortfolioBreakdown() - Functional component that maps summary metrics into a structured comparison table
 */
import type { PortfolioSummary } from '../services/api';

interface Props {
    data: PortfolioSummary;
}

function formatCurrency(value: number): string {
    return `$${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export default function PortfolioBreakdown({ data }: Props) {
    const rows = [
        {
            label: 'Total Market Value',
            usd: formatCurrency(data.totalMarketValueUSD),
            cad: formatCurrency(data.totalMarketValueCAD),
        },
        {
            label: 'Total Book Value',
            usd: formatCurrency(data.totalBookValueUSD),
            cad: formatCurrency(data.totalBookValueCAD),
        },
        {
            label: 'Unrealized Gain/Loss',
            usd: `${data.unrealizedGainUSD >= 0 ? '+' : ''}${formatCurrency(data.unrealizedGainUSD)}`,
            cad: `${data.unrealizedGainCAD >= 0 ? '+' : ''}${formatCurrency(data.unrealizedGainCAD)}`,
            color: data.unrealizedGainUSD >= 0 ? 'text-emerald-400' : 'text-red-400',
        },
        {
            label: 'YTD Start Value (Jan 1)',
            usd: formatCurrency(data.ytdStartValueUSD),
            cad: formatCurrency(data.ytdStartValueCAD),
        },
        {
            label: 'YTD Change',
            usd: `${data.ytdChangeUSD >= 0 ? '+' : ''}${formatCurrency(data.ytdChangeUSD)}`,
            cad: `${data.ytdChangeCAD >= 0 ? '+' : ''}${formatCurrency(data.ytdChangeCAD)}`,
            color: data.ytdChangeCAD >= 0 ? 'text-emerald-400' : 'text-red-400',
        },
    ];

    return (
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 shadow-lg">
            <h3 className="text-base font-bold text-slate-500 uppercase tracking-widest mb-4">
                Detailed Breakdown
            </h3>
            <div className="overflow-x-auto">
                <table className="w-full">
                    <thead>
                        <tr className="border-b border-slate-800">
                            <th className="text-left text-base font-semibold text-slate-500 uppercase pb-3 pr-4">
                                Metric
                            </th>
                            <th className="text-right text-base font-semibold text-slate-500 uppercase pb-3 px-4">
                                USD
                            </th>
                            <th className="text-right text-base font-semibold text-slate-500 uppercase pb-3 pl-4">
                                CAD
                            </th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows.map((row) => (
                            <tr key={row.label} className="border-b border-slate-800/50">
                                <td className="text-lg text-slate-300 py-3 pr-4">
                                    {row.label}
                                </td>
                                <td className={`text-lg text-right py-3 px-4 font-semibold ${row.color || 'text-slate-300'}`}>
                                    {row.usd}
                                </td>
                                <td className={`text-lg text-right py-3 pl-4 font-semibold ${row.color || 'text-slate-300'}`}>
                                    {row.cad}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
            <div className="mt-4 pt-3 border-t border-slate-800 flex justify-between text-xs text-slate-600">
                <span>Live rate: 1 USD = {data.liveUsdCadRate.toFixed(4)} CAD</span>
                <span>Last updated: {new Date(data.lastUpdated).toLocaleString()}</span>
            </div>
        </div>
    );
}
