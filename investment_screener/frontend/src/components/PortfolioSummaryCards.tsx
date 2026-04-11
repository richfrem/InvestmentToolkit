import type { PortfolioSummary } from '../services/api';
import { TrendingUp, TrendingDown, DollarSign, BarChart3, ArrowUpDown } from 'lucide-react';

interface Props {
    data: PortfolioSummary;
}

function formatCurrency(value: number, decimals = 2): string {
    const abs = Math.abs(value);
    if (abs >= 1_000_000) return `$${(value / 1_000_000).toFixed(2)}M`;
    if (abs >= 1_000) return `$${value.toLocaleString(undefined, { minimumFractionDigits: decimals, maximumFractionDigits: decimals })}`;
    return `$${value.toFixed(decimals)}`;
}

function formatPct(value: number): string {
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
}

function changeColor(value: number): string {
    if (value > 0) return 'text-emerald-400';
    if (value < 0) return 'text-red-400';
    return 'text-slate-400';
}

function changeBgGlow(value: number): string {
    if (value > 0) return 'shadow-emerald-500/10';
    if (value < 0) return 'shadow-red-500/10';
    return '';
}

export default function PortfolioSummaryCards({ data }: Props) {
    const cards = [
        {
            title: 'YTD Performance',
            icon: data.ytdChangePctCAD >= 0 ? TrendingUp : TrendingDown,
            primary: formatPct(data.ytdChangePctCAD),
            primaryColor: changeColor(data.ytdChangePctCAD),
            rows: [
                { label: 'CAD', value: `${data.ytdChangeCAD >= 0 ? '+' : ''}${formatCurrency(data.ytdChangeCAD)}`, color: changeColor(data.ytdChangeCAD) },
                { label: 'USD', value: `${data.ytdChangeUSD >= 0 ? '+' : ''}${formatCurrency(data.ytdChangeUSD)}`, color: changeColor(data.ytdChangeUSD) },
            ],
            glow: changeBgGlow(data.ytdChangePctCAD),
        },
        {
            title: 'Total Market Value',
            icon: DollarSign,
            primary: formatCurrency(data.totalMarketValueCAD),
            primaryColor: 'text-white',
            rows: [
                { label: 'USD', value: formatCurrency(data.totalMarketValueUSD), color: 'text-slate-300' },
                { label: 'Positions', value: `${data.positionCount}`, color: 'text-slate-400' },
            ],
            glow: '',
        },
        {
            title: 'Book vs Market',
            icon: BarChart3,
            primary: formatPct(data.unrealizedGainPctUSD),
            primaryColor: changeColor(data.unrealizedGainPctUSD),
            rows: [
                { label: 'USD', value: `${data.unrealizedGainUSD >= 0 ? '+' : ''}${formatCurrency(data.unrealizedGainUSD)}`, color: changeColor(data.unrealizedGainUSD) },
                { label: 'CAD', value: `${data.unrealizedGainCAD >= 0 ? '+' : ''}${formatCurrency(data.unrealizedGainCAD)}`, color: changeColor(data.unrealizedGainCAD) },
            ],
            glow: changeBgGlow(data.unrealizedGainPctUSD),
        },
        {
            title: 'Exchange Rate',
            icon: ArrowUpDown,
            primary: `${data.liveUsdCadRate.toFixed(4)}`,
            primaryColor: 'text-amber-400',
            rows: [
                { label: 'Live USD/CAD', value: data.liveUsdCadRate.toFixed(4), color: 'text-slate-300' },
                { label: 'Jan 1 Rate', value: data.jan1UsdCadRate.toFixed(4), color: 'text-slate-500' },
            ],
            glow: '',
        },
    ];

    return (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
            {cards.map((card) => (
                <div
                    key={card.title}
                    className={`bg-slate-900/80 border border-slate-800 rounded-xl p-5 shadow-lg ${card.glow}`}
                >
                    <div className="flex items-center justify-between mb-3">
                        <h3 className="text-xs font-bold text-slate-500 uppercase tracking-widest">
                            {card.title}
                        </h3>
                        <card.icon size={16} className="text-slate-600" />
                    </div>
                    <div className={`text-2xl font-bold mb-3 ${card.primaryColor}`}>
                        {card.primary}
                    </div>
                    <div className="space-y-1">
                        {card.rows.map((row) => (
                            <div key={row.label} className="flex justify-between text-sm">
                                <span className="text-slate-500">{row.label}</span>
                                <span className={`font-medium ${row.color}`}>{row.value}</span>
                            </div>
                        ))}
                    </div>
                </div>
            ))}
        </div>
    );
}
