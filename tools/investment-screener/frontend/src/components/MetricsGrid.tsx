import type { StockData } from '../services/api';
import { AlertTriangle, TrendingUp, DollarSign } from 'lucide-react';
import { HelpTrigger } from './HelpModal';

interface MetricsGridProps {
    stockData: StockData;
}

export default function MetricsGrid({ stockData }: MetricsGridProps) {
    const { expert_metrics, metrics } = stockData;

    // Piotroski Logic
    const fScore = expert_metrics.piotroski_f_score.score;
    const fScoreColor = fScore >= 7 ? 'text-green-500' : fScore >= 4 ? 'text-amber-500' : 'text-red-500';
    const fScoreBg = fScore >= 7 ? 'bg-green-500' : fScore >= 4 ? 'bg-amber-500' : 'bg-red-500';

    // Rule of 40 Logic
    const r40Score = expert_metrics.rule_of_40.score;
    const r40Color = r40Score >= 40 ? 'text-green-500' : 'text-red-500';
    const isTech = ['Technology', 'Communication Services'].includes(stockData.profile.sector);

    return (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            {/* Piotroski F-Score */}
            <div className="bg-surface p-6 rounded-xl border border-slate-800 relative overflow-hidden group hover:border-slate-700 transition-colors">
                <div className={`absolute top-0 left-0 w-1 h-full ${fScoreBg} opacity-50`}></div>
                <div className="flex justify-between items-start mb-2">
                    <div className="flex items-center gap-2">
                        <h3 className="text-secondary font-medium uppercase tracking-wider text-sm">Piotroski F-Score</h3>
                        <HelpTrigger topicId="piotroski" size={14} className="opacity-50 hover:opacity-100" />
                    </div>
                    <TrendingUp size={16} className="text-slate-500" />
                </div>
                <div className="flex items-baseline gap-2">
                    <span className={`text-3xl font-bold ${fScoreColor}`}>{fScore}</span>
                    <span className="text-slate-500 text-sm">/ 9</span>
                </div>
                <div className="mt-4 h-2 bg-slate-800 rounded-full overflow-hidden">
                    <div
                        className={`h-full ${fScoreBg} transition-all duration-1000 ease-out`}
                        style={{ width: `${(fScore / 9) * 100}%` }}
                    ></div>
                </div>
                <p className="text-xs text-slate-500 mt-3">
                    {fScore >= 7 ? 'Strong Financial Health' : fScore >= 4 ? 'Stable' : 'Weak Fundamentals'}
                </p>
            </div>

            {/* Rule of 40 */}
            <div className="bg-surface p-6 rounded-xl border border-slate-800 relative overflow-hidden group hover:border-slate-700 transition-colors">
                <div className={`absolute top-0 left-0 w-1 h-full ${r40Score >= 40 ? 'bg-green-500' : 'bg-red-500'} opacity-50`}></div>
                <div className="flex justify-between items-start mb-2">
                    <div className="flex items-center gap-2">
                        <h3 className="text-secondary font-medium uppercase tracking-wider text-sm">Rule of 40</h3>
                        <HelpTrigger topicId="ruleOf40" size={14} className="opacity-50 hover:opacity-100" />
                    </div>
                    {!isTech && (
                        <span title="Sector Mismatch?">
                            <AlertTriangle size={16} className="text-amber-500" />
                        </span>
                    )}
                </div>
                <div className="flex items-baseline gap-2">
                    <span className={`text-3xl font-bold ${r40Color}`}>{r40Score.toFixed(1)}%</span>
                </div>
                <div className="mt-3 text-xs text-slate-400 space-y-1">
                    <div className="flex justify-between">
                        <span>Rev Growth</span>
                        <span className="text-text">{expert_metrics.rule_of_40.revenue_growth.toFixed(1)}%</span>
                    </div>
                    <div className="flex justify-between">
                        <span>EBITDA Margin</span>
                        <span className="text-text">{expert_metrics.rule_of_40.ebitda_margin.toFixed(1)}%</span>
                    </div>
                </div>
                {!isTech && (
                    <p className="text-xs text-amber-500/80 mt-3">
                        Note: Best suited for SaaS/Tech.
                    </p>
                )}
            </div>

            {/* Valuation (PE) */}
            <div className="bg-surface p-6 rounded-xl border border-slate-800 relative overflow-hidden group hover:border-slate-700 transition-colors">
                <div className="absolute top-0 left-0 w-1 h-full bg-blue-500 opacity-50"></div>
                <div className="flex justify-between items-start mb-2">
                    <div className="flex items-center gap-2">
                        <h3 className="text-secondary font-medium uppercase tracking-wider text-sm">Valuation (P/E)</h3>
                        <HelpTrigger topicId="peRatio" size={14} className="opacity-50 hover:opacity-100" />
                    </div>
                    <DollarSign size={16} className="text-slate-500" />
                </div>
                <div className="flex items-baseline gap-2">
                    <span className="text-3xl font-bold text-blue-400">{metrics.pe_ratio?.toFixed(2) || 'N/A'}</span>
                </div>
                <div className="mt-3 text-xs text-slate-400 space-y-1">
                    <div className="flex justify-between">
                        <span>Forward P/E</span>
                        <span className="text-text">{metrics.forward_pe?.toFixed(2) || 'N/A'}</span>
                    </div>
                    <div className="flex justify-between">
                        <span>Market Cap</span>
                        <span className="text-text">${(metrics.market_cap / 1e9).toFixed(2)}B</span>
                    </div>
                </div>
                <p className="text-xs text-slate-500 mt-3">
                    Beta: {metrics.beta?.toFixed(2)}
                </p>
            </div>
        </div>
    );
}
