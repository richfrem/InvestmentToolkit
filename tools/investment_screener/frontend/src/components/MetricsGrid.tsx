import type { StockData } from '../services/api';
import { AlertTriangle, TrendingUp, DollarSign, Percent, Activity, PieChart, Calculator, BarChart3, Target } from 'lucide-react';
import { HelpTrigger } from './HelpModal';

interface MetricsGridProps {
    stockData: StockData;
}

export default function MetricsGrid({ stockData }: MetricsGridProps) {
    const { expert_metrics, metrics, financials } = stockData;

    // === DATA EXTRACTION ===

    // Margins - determine format (decimal 0.xx vs percentage xx.xx)
    const latestGrossMargin = financials?.historical_gross_margin?.[(financials?.historical_gross_margin?.length || 0) - 1];
    const latestOperatingMargin = financials?.historical_operating_margin?.[(financials?.historical_operating_margin?.length || 0) - 1];
    const latestNetMargin = financials?.historical_net_margin?.[(financials?.historical_net_margin?.length || 0) - 1];
    const prevGrossMargin = financials?.historical_gross_margin?.[(financials?.historical_gross_margin?.length || 0) - 2];
    const prevOperatingMargin = financials?.historical_operating_margin?.[(financials?.historical_operating_margin?.length || 0) - 2];

    const isDecimal = latestGrossMargin !== undefined && latestGrossMargin <= 1;
    const formatMargin = (margin: number | undefined) => {
        if (margin === undefined) return 'N/A';
        return isDecimal ? `${(margin * 100).toFixed(1)}%` : `${margin.toFixed(1)}%`;
    };
    const getMarginValue = (margin: number | undefined) => {
        if (margin === undefined) return 0;
        return isDecimal ? margin * 100 : margin;
    };

    // Margin trends
    const grossMarginTrend = latestGrossMargin && prevGrossMargin
        ? (latestGrossMargin > prevGrossMargin ? 'up' : latestGrossMargin < prevGrossMargin ? 'down' : 'flat')
        : 'flat';
    const opMarginTrend = latestOperatingMargin && prevOperatingMargin
        ? (latestOperatingMargin > prevOperatingMargin ? 'up' : latestOperatingMargin < prevOperatingMargin ? 'down' : 'flat')
        : 'flat';

    // FCF data
    const latestFCF = financials?.historical_fcf?.[(financials?.historical_fcf?.length || 0) - 1];
    const prevFCF = financials?.historical_fcf?.[(financials?.historical_fcf?.length || 0) - 2];
    const fcfTrend = latestFCF && prevFCF
        ? (latestFCF > prevFCF ? 'up' : latestFCF < prevFCF ? 'down' : 'flat')
        : 'flat';
    const fcfYield = latestFCF && metrics.market_cap ? (latestFCF / metrics.market_cap) * 100 : null;

    // EPS data
    const latestEPS = financials?.historical_eps?.[(financials?.historical_eps?.length || 0) - 1];
    const prevEPS = financials?.historical_eps?.[(financials?.historical_eps?.length || 0) - 2];
    const epsTrend = latestEPS && prevEPS
        ? (latestEPS > prevEPS ? 'up' : latestEPS < prevEPS ? 'down' : 'flat')
        : 'flat';
    const epsGrowthRate = latestEPS && prevEPS && prevEPS !== 0
        ? ((latestEPS - prevEPS) / Math.abs(prevEPS)) * 100
        : null;

    // Analyst estimates
    const analystTarget = stockData.analyst_estimates?.target_mean_price;
    const upsidePct = analystTarget && stockData.price
        ? ((analystTarget - stockData.price) / stockData.price) * 100
        : null;

    // Growth & Valuation
    const revenueGrowth = metrics.revenue_growth || expert_metrics.rule_of_40.revenue_growth;
    const epsGrowthEst = stockData.growth_estimates?.stockTrend?.['+1y'];
    const pegRatio = metrics.peg_ratio || (metrics.pe_ratio && epsGrowthEst && epsGrowthEst > 0
        ? metrics.pe_ratio / epsGrowthEst
        : null);
    const peCompression = metrics.pe_ratio && metrics.forward_pe
        ? ((metrics.forward_pe - metrics.pe_ratio) / metrics.pe_ratio) * 100
        : null;

    // Quality scores
    const fScore = expert_metrics.piotroski_f_score.score;
    const fScoreColor = fScore >= 7 ? 'text-green-500' : fScore >= 4 ? 'text-amber-500' : 'text-red-500';
    const fScoreBg = fScore >= 7 ? 'bg-green-500' : fScore >= 4 ? 'bg-amber-500' : 'bg-red-500';

    const r40Score = expert_metrics.rule_of_40.score;
    const r40Color = r40Score >= 40 ? 'text-green-500' : 'text-red-500';
    const isTech = ['Technology', 'Communication Services'].includes(stockData.profile.sector);

    // === COLOR HELPERS ===
    const getMarginColor = (val: number) => val >= 70 ? 'text-green-500' : val >= 50 ? 'text-amber-500' : 'text-red-500';
    const getOpMarginColor = (val: number) => val >= 30 ? 'text-green-500' : val >= 15 ? 'text-amber-500' : 'text-red-500';
    const getNetMarginColor = (val: number) => val >= 20 ? 'text-green-500' : val >= 10 ? 'text-amber-500' : 'text-red-500';

    return (
        <div className="space-y-6">
            {/* ROW 1: MOST CRITICAL - Growth & Cash Flow (What drives valuation) */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {/* Revenue Growth - Core driver */}
                <div className="bg-surface p-6 rounded-xl border border-slate-800 relative overflow-hidden group hover:border-slate-700 transition-colors">
                    <div className={`absolute top-0 left-0 w-1 h-full ${revenueGrowth && revenueGrowth >= 20 ? 'bg-green-500' : 'bg-amber-500'} opacity-50`}></div>
                    <div className="flex justify-between items-start mb-2">
                        <div className="flex items-center gap-2">
                            <h3 className="text-secondary font-medium uppercase tracking-wider text-sm">Revenue Growth</h3>
                            <HelpTrigger topicId="revenueGrowthMetric" size={14} className="opacity-50 hover:opacity-100" />
                        </div>
                        <TrendingUp size={16} className="text-slate-500" />
                    </div>
                    <div className="flex items-baseline gap-2">
                        <span className={`text-3xl font-bold ${revenueGrowth && revenueGrowth >= 20 ? 'text-green-500' : revenueGrowth && revenueGrowth >= 10 ? 'text-amber-500' : 'text-red-500'}`}>
                            {revenueGrowth !== undefined ? `${revenueGrowth.toFixed(1)}%` : 'N/A'}
                        </span>
                    </div>
                    <div className="mt-3 text-xs text-slate-400 space-y-1">
                        <div className="flex justify-between">
                            <span>TTM Revenue</span>
                            <span className="text-text">{metrics.revenue ? `$${(metrics.revenue / 1e9).toFixed(1)}B` : 'N/A'}</span>
                        </div>
                        <div className="flex justify-between">
                            <span>Target</span>
                            <span className="text-primary">&gt;20% CAGR</span>
                        </div>
                    </div>
                    <p className="text-xs text-slate-500 mt-3">
                        {revenueGrowth && revenueGrowth >= 30 ? 'Hypergrowth' : revenueGrowth && revenueGrowth >= 20 ? 'Strong growth' : 'Moderate growth'}
                    </p>
                </div>

                {/* Free Cash Flow - What actually matters */}
                <div className="bg-surface p-6 rounded-xl border border-slate-800 relative overflow-hidden group hover:border-slate-700 transition-colors">
                    <div className={`absolute top-0 left-0 w-1 h-full ${latestFCF && latestFCF > 0 ? 'bg-green-500' : 'bg-red-500'} opacity-50`}></div>
                    <div className="flex justify-between items-start mb-2">
                        <div className="flex items-center gap-2">
                            <h3 className="text-secondary font-medium uppercase tracking-wider text-sm">Free Cash Flow</h3>
                            <HelpTrigger topicId="fcf" size={14} className="opacity-50 hover:opacity-100" />
                        </div>
                        <DollarSign size={16} className="text-slate-500" />
                    </div>
                    <div className="flex items-baseline gap-2">
                        <span className={`text-3xl font-bold ${latestFCF && latestFCF > 0 ? 'text-green-500' : 'text-red-500'}`}>
                            {latestFCF ? `$${(latestFCF / 1e9).toFixed(1)}B` : 'N/A'}
                        </span>
                        {fcfTrend === 'up' && <span className="text-green-500 text-sm">↑</span>}
                        {fcfTrend === 'down' && <span className="text-red-500 text-sm">↓</span>}
                    </div>
                    <div className="mt-3 text-xs text-slate-400 space-y-1">
                        <div className="flex justify-between">
                            <span>FCF Yield</span>
                            <span className={fcfYield && fcfYield > 5 ? 'text-green-400' : 'text-text'}>{fcfYield ? `${fcfYield.toFixed(1)}%` : 'N/A'}</span>
                        </div>
                        <div className="flex justify-between">
                            <span>Prior Year</span>
                            <span className="text-text">{prevFCF ? `$${(prevFCF / 1e9).toFixed(1)}B` : 'N/A'}</span>
                        </div>
                    </div>
                    <p className="text-xs text-slate-500 mt-3">
                        {latestFCF && latestFCF > 0 ? 'Cash generating' : 'Cash burning'}
                    </p>
                </div>

                {/* Operating Margin - Profitability efficiency */}
                <div className="bg-surface p-6 rounded-xl border border-slate-800 relative overflow-hidden group hover:border-slate-700 transition-colors">
                    <div className={`absolute top-0 left-0 w-1 h-full ${getMarginValue(latestOperatingMargin) >= 20 ? 'bg-green-500' : 'bg-amber-500'} opacity-50`}></div>
                    <div className="flex justify-between items-start mb-2">
                        <div className="flex items-center gap-2">
                            <h3 className="text-secondary font-medium uppercase tracking-wider text-sm">Operating Margin</h3>
                            <HelpTrigger topicId="operatingMargin" size={14} className="opacity-50 hover:opacity-100" />
                        </div>
                        <Activity size={16} className="text-slate-500" />
                    </div>
                    <div className="flex items-baseline gap-2">
                        <span className={`text-3xl font-bold ${getOpMarginColor(getMarginValue(latestOperatingMargin))}`}>
                            {formatMargin(latestOperatingMargin)}
                        </span>
                        {opMarginTrend === 'up' && <span className="text-green-500 text-sm">↑</span>}
                        {opMarginTrend === 'down' && <span className="text-red-500 text-sm">↓</span>}
                    </div>
                    <div className="mt-4 h-2 bg-slate-800 rounded-full overflow-hidden">
                        <div className="h-full bg-gradient-to-r from-red-500 via-amber-500 to-green-500" style={{ width: `${Math.min(getMarginValue(latestOperatingMargin) * 2, 100)}%` }}></div>
                    </div>
                    <p className="text-xs text-slate-500 mt-3">
                        {getMarginValue(latestOperatingMargin) >= 30 ? 'Excellent efficiency' : getMarginValue(latestOperatingMargin) >= 15 ? 'Good leverage' : 'Room to improve'}
                    </p>
                </div>
            </div>

            {/* ROW 2: VALUATION MULTIPLES - How expensive is the stock */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {/* P/E Ratio */}
                <div className="bg-surface p-6 rounded-xl border border-slate-800 relative overflow-hidden group hover:border-slate-700 transition-colors">
                    <div className="absolute top-0 left-0 w-1 h-full bg-blue-500 opacity-50"></div>
                    <div className="flex justify-between items-start mb-2">
                        <div className="flex items-center gap-2">
                            <h3 className="text-secondary font-medium uppercase tracking-wider text-sm">P/E Ratio</h3>
                            <HelpTrigger topicId="peRatio" size={14} className="opacity-50 hover:opacity-100" />
                        </div>
                        <DollarSign size={16} className="text-slate-500" />
                    </div>
                    <div className="flex items-baseline gap-2">
                        <span className="text-3xl font-bold text-blue-400">{metrics.pe_ratio?.toFixed(1) || 'N/A'}x</span>
                    </div>
                    <div className="mt-3 text-xs text-slate-400 space-y-1">
                        <div className="flex justify-between">
                            <span>Forward P/E</span>
                            <span className="text-text">{metrics.forward_pe?.toFixed(1) || 'N/A'}x</span>
                        </div>
                        <div className="flex justify-between">
                            <span>Market Cap</span>
                            <span className="text-text">{metrics.market_cap ? `$${(metrics.market_cap / 1e9).toFixed(0)}B` : 'N/A'}</span>
                        </div>
                    </div>
                    <p className="text-xs text-slate-500 mt-3">
                        {metrics.pe_ratio && metrics.pe_ratio < 20 ? 'Value territory' : metrics.pe_ratio && metrics.pe_ratio < 35 ? 'Growth pricing' : 'Premium valuation'}
                    </p>
                </div>

                {/* PEG Ratio */}
                <div className="bg-surface p-6 rounded-xl border border-slate-800 relative overflow-hidden group hover:border-slate-700 transition-colors">
                    <div className={`absolute top-0 left-0 w-1 h-full ${pegRatio && pegRatio < 1 ? 'bg-green-500' : pegRatio && pegRatio < 2 ? 'bg-amber-500' : 'bg-red-500'} opacity-50`}></div>
                    <div className="flex justify-between items-start mb-2">
                        <div className="flex items-center gap-2">
                            <h3 className="text-secondary font-medium uppercase tracking-wider text-sm">PEG Ratio</h3>
                            <HelpTrigger topicId="pegRatio" size={14} className="opacity-50 hover:opacity-100" />
                        </div>
                        <Calculator size={16} className="text-slate-500" />
                    </div>
                    <div className="flex items-baseline gap-2">
                        <span className={`text-3xl font-bold ${pegRatio && pegRatio < 1 ? 'text-green-500' : pegRatio && pegRatio < 2 ? 'text-amber-500' : 'text-red-500'}`}>
                            {pegRatio ? pegRatio.toFixed(2) : 'N/A'}
                        </span>
                    </div>
                    <div className="mt-3 text-xs text-slate-400 space-y-1">
                        <div className="flex justify-between">
                            <span>P/E ÷ Growth</span>
                            <span className="text-text">{metrics.pe_ratio?.toFixed(0)} ÷ {epsGrowthEst?.toFixed(0) || '?'}</span>
                        </div>
                        <div className="flex justify-between">
                            <span>Target</span>
                            <span className="text-primary">&lt;1.0 = Undervalued</span>
                        </div>
                    </div>
                    <p className="text-xs text-slate-500 mt-3">
                        {pegRatio && pegRatio < 1 ? 'Undervalued vs growth' : pegRatio && pegRatio < 2 ? 'Fair value' : 'Premium vs growth'}
                    </p>
                </div>

                {/* Analyst Price Target */}
                <div className="bg-surface p-6 rounded-xl border border-slate-800 relative overflow-hidden group hover:border-slate-700 transition-colors">
                    <div className={`absolute top-0 left-0 w-1 h-full ${upsidePct && upsidePct > 0 ? 'bg-green-500' : 'bg-red-500'} opacity-50`}></div>
                    <div className="flex justify-between items-start mb-2">
                        <div className="flex items-center gap-2">
                            <h3 className="text-secondary font-medium uppercase tracking-wider text-sm">Analyst Target</h3>
                            <HelpTrigger topicId="targetPrice" size={14} className="opacity-50 hover:opacity-100" />
                        </div>
                        <Target size={16} className="text-slate-500" />
                    </div>
                    <div className="flex items-baseline gap-2">
                        <span className={`text-3xl font-bold ${upsidePct && upsidePct > 10 ? 'text-green-500' : upsidePct && upsidePct > 0 ? 'text-amber-500' : 'text-red-500'}`}>
                            ${analystTarget?.toFixed(0) || 'N/A'}
                        </span>
                        {upsidePct !== null && <span className={`text-sm ${upsidePct > 0 ? 'text-green-400' : 'text-red-400'}`}>
                            {upsidePct > 0 ? '+' : ''}{upsidePct.toFixed(0)}%
                        </span>}
                    </div>
                    <div className="mt-3 text-xs text-slate-400 space-y-1">
                        <div className="flex justify-between">
                            <span>Range</span>
                            <span className="text-text">${stockData.analyst_estimates?.target_low_price?.toFixed(0) || '?'} - ${stockData.analyst_estimates?.target_high_price?.toFixed(0) || '?'}</span>
                        </div>
                        <div className="flex justify-between">
                            <span>Current</span>
                            <span className="text-text">${stockData.price?.toFixed(2)}</span>
                        </div>
                    </div>
                    <p className="text-xs text-slate-500 mt-3">
                        {stockData.analyst_estimates?.recommendation || 'No rating'}
                    </p>
                </div>
            </div>

            {/* ROW 3: PROFITABILITY - Margin analysis */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {/* Gross Margin */}
                <div className="bg-surface p-6 rounded-xl border border-slate-800 relative overflow-hidden group hover:border-slate-700 transition-colors">
                    <div className={`absolute top-0 left-0 w-1 h-full ${getMarginValue(latestGrossMargin) >= 50 ? 'bg-green-500' : 'bg-amber-500'} opacity-50`}></div>
                    <div className="flex justify-between items-start mb-2">
                        <div className="flex items-center gap-2">
                            <h3 className="text-secondary font-medium uppercase tracking-wider text-sm">Gross Margin</h3>
                            <HelpTrigger topicId="grossMargin" size={14} className="opacity-50 hover:opacity-100" />
                        </div>
                        <Percent size={16} className="text-slate-500" />
                    </div>
                    <div className="flex items-baseline gap-2">
                        <span className={`text-3xl font-bold ${getMarginColor(getMarginValue(latestGrossMargin))}`}>
                            {formatMargin(latestGrossMargin)}
                        </span>
                        {grossMarginTrend === 'up' && <span className="text-green-500 text-sm">↑</span>}
                        {grossMarginTrend === 'down' && <span className="text-red-500 text-sm">↓</span>}
                    </div>
                    <div className="mt-4 h-2 bg-slate-800 rounded-full overflow-hidden">
                        <div className="h-full bg-gradient-to-r from-amber-500 to-green-500" style={{ width: `${Math.min(getMarginValue(latestGrossMargin), 100)}%` }}></div>
                    </div>
                    <p className="text-xs text-slate-500 mt-3">
                        {getMarginValue(latestGrossMargin) >= 70 ? 'Premium pricing power' : getMarginValue(latestGrossMargin) >= 50 ? 'Healthy margin' : 'Competitive pressure'}
                    </p>
                </div>

                {/* Net Margin */}
                <div className="bg-surface p-6 rounded-xl border border-slate-800 relative overflow-hidden group hover:border-slate-700 transition-colors">
                    <div className={`absolute top-0 left-0 w-1 h-full ${getMarginValue(latestNetMargin) >= 15 ? 'bg-green-500' : 'bg-amber-500'} opacity-50`}></div>
                    <div className="flex justify-between items-start mb-2">
                        <div className="flex items-center gap-2">
                            <h3 className="text-secondary font-medium uppercase tracking-wider text-sm">Net Margin</h3>
                            <HelpTrigger topicId="netMargin" size={14} className="opacity-50 hover:opacity-100" />
                        </div>
                        <PieChart size={16} className="text-slate-500" />
                    </div>
                    <div className="flex items-baseline gap-2">
                        <span className={`text-3xl font-bold ${getNetMarginColor(getMarginValue(latestNetMargin))}`}>
                            {formatMargin(latestNetMargin)}
                        </span>
                    </div>
                    <div className="mt-4 h-2 bg-slate-800 rounded-full overflow-hidden">
                        <div className="h-full bg-gradient-to-r from-red-500 via-amber-500 to-green-500" style={{ width: `${Math.min(getMarginValue(latestNetMargin) * 2.5, 100)}%` }}></div>
                    </div>
                    <p className="text-xs text-slate-500 mt-3">
                        {getMarginValue(latestNetMargin) >= 25 ? 'Highly profitable' : getMarginValue(latestNetMargin) >= 15 ? 'Strong profitability' : 'Average profitability'}
                    </p>
                </div>

                {/* Rule of 40 (EBITDA component) */}
                <div className="bg-surface p-6 rounded-xl border border-slate-800 relative overflow-hidden group hover:border-slate-700 transition-colors">
                    <div className={`absolute top-0 left-0 w-1 h-full ${r40Score >= 40 ? 'bg-green-500' : 'bg-red-500'} opacity-50`}></div>
                    <div className="flex justify-between items-start mb-2">
                        <div className="flex items-center gap-2">
                            <h3 className="text-secondary font-medium uppercase tracking-wider text-sm">Rule of 40</h3>
                            <HelpTrigger topicId="ruleOf40" size={14} className="opacity-50 hover:opacity-100" />
                        </div>
                        {!isTech && <AlertTriangle size={16} className="text-amber-500" />}
                    </div>
                    <div className="flex items-baseline gap-2">
                        <span className={`text-3xl font-bold ${r40Color}`}>{r40Score?.toFixed(1) || '0.0'}%</span>
                    </div>
                    <div className="mt-3 text-xs text-slate-400 space-y-1">
                        <div className="flex justify-between">
                            <span>Rev Growth</span>
                            <span className="text-text">{expert_metrics.rule_of_40.revenue_growth?.toFixed(1) || '0.0'}%</span>
                        </div>
                        <div className="flex justify-between">
                            <span>EBITDA Margin</span>
                            <span className="text-text">{expert_metrics.rule_of_40.ebitda_margin?.toFixed(1) || '0.0'}%</span>
                        </div>
                    </div>
                    <p className="text-xs text-slate-500 mt-3">{r40Score >= 40 ? 'Passes Rule of 40' : 'Below target'}</p>
                </div>
            </div>

            {/* ROW 4: EARNINGS & EPS */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {/* EPS */}
                <div className="bg-surface p-6 rounded-xl border border-slate-800 relative overflow-hidden group hover:border-slate-700 transition-colors">
                    <div className={`absolute top-0 left-0 w-1 h-full ${latestEPS && latestEPS > 0 ? 'bg-green-500' : 'bg-red-500'} opacity-50`}></div>
                    <div className="flex justify-between items-start mb-2">
                        <div className="flex items-center gap-2">
                            <h3 className="text-secondary font-medium uppercase tracking-wider text-sm">EPS (TTM)</h3>
                            <HelpTrigger topicId="epsEstimate" size={14} className="opacity-50 hover:opacity-100" />
                        </div>
                        <DollarSign size={16} className="text-slate-500" />
                    </div>
                    <div className="flex items-baseline gap-2">
                        <span className={`text-3xl font-bold ${latestEPS && latestEPS > 0 ? 'text-green-500' : 'text-red-500'}`}>
                            ${latestEPS?.toFixed(2) || 'N/A'}
                        </span>
                        {epsTrend === 'up' && <span className="text-green-500 text-sm">↑</span>}
                        {epsTrend === 'down' && <span className="text-red-500 text-sm">↓</span>}
                    </div>
                    <div className="mt-3 text-xs text-slate-400 space-y-1">
                        <div className="flex justify-between">
                            <span>Prior Year</span>
                            <span className="text-text">${prevEPS?.toFixed(2) || 'N/A'}</span>
                        </div>
                        <div className="flex justify-between">
                            <span>EPS Growth</span>
                            <span className={epsGrowthRate && epsGrowthRate > 0 ? 'text-green-400' : 'text-red-400'}>
                                {epsGrowthRate ? `${epsGrowthRate.toFixed(1)}%` : 'N/A'}
                            </span>
                        </div>
                    </div>
                    <p className="text-xs text-slate-500 mt-3">Earnings per share</p>
                </div>

                {/* Forward P/E */}
                <div className="bg-surface p-6 rounded-xl border border-slate-800 relative overflow-hidden group hover:border-slate-700 transition-colors">
                    <div className="absolute top-0 left-0 w-1 h-full bg-cyan-500 opacity-50"></div>
                    <div className="flex justify-between items-start mb-2">
                        <div className="flex items-center gap-2">
                            <h3 className="text-secondary font-medium uppercase tracking-wider text-sm">Forward P/E</h3>
                            <HelpTrigger topicId="forwardPE" size={14} className="opacity-50 hover:opacity-100" />
                        </div>
                        <Calculator size={16} className="text-slate-500" />
                    </div>
                    <div className="flex items-baseline gap-2">
                        <span className="text-3xl font-bold text-cyan-400">{metrics.forward_pe?.toFixed(1) || 'N/A'}x</span>
                    </div>
                    <div className="mt-3 text-xs text-slate-400 space-y-1">
                        <div className="flex justify-between">
                            <span>Trailing P/E</span>
                            <span className="text-text">{metrics.pe_ratio?.toFixed(1) || 'N/A'}x</span>
                        </div>
                        <div className="flex justify-between">
                            <span>P/E Compression</span>
                            <span className={peCompression && peCompression < 0 ? 'text-green-400' : 'text-amber-400'}>
                                {peCompression ? `${peCompression.toFixed(0)}%` : 'N/A'}
                            </span>
                        </div>
                    </div>
                    <p className="text-xs text-slate-500 mt-3">{peCompression && peCompression < -10 ? 'Earnings catching up' : 'Stable outlook'}</p>
                </div>

                {/* Piotroski F-Score */}
                <div className="bg-surface p-6 rounded-xl border border-slate-800 relative overflow-hidden group hover:border-slate-700 transition-colors">
                    <div className={`absolute top-0 left-0 w-1 h-full ${fScoreBg} opacity-50`}></div>
                    <div className="flex justify-between items-start mb-2">
                        <div className="flex items-center gap-2">
                            <h3 className="text-secondary font-medium uppercase tracking-wider text-sm">Piotroski F-Score</h3>
                            <HelpTrigger topicId="piotroski" size={14} className="opacity-50 hover:opacity-100" />
                        </div>
                        <BarChart3 size={16} className="text-slate-500" />
                    </div>
                    <div className="flex items-baseline gap-2">
                        <span className={`text-3xl font-bold ${fScoreColor}`}>{fScore}</span>
                        <span className="text-slate-500 text-sm">/ 9</span>
                    </div>
                    <div className="mt-4 h-2 bg-slate-800 rounded-full overflow-hidden">
                        <div className={`h-full ${fScoreBg}`} style={{ width: `${(fScore / 9) * 100}%` }}></div>
                    </div>
                    <p className="text-xs text-slate-500 mt-3">{fScore >= 7 ? 'Strong Financial Health' : fScore >= 4 ? 'Stable' : 'Weak Fundamentals'}</p>
                </div>
            </div>

            {/* ROW 5: RISK & CONTEXT */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {/* Beta */}
                <div className="bg-surface p-6 rounded-xl border border-slate-800 relative overflow-hidden group hover:border-slate-700 transition-colors">
                    <div className={`absolute top-0 left-0 w-1 h-full ${metrics.beta && metrics.beta > 1.5 ? 'bg-red-500' : metrics.beta && metrics.beta > 1 ? 'bg-amber-500' : 'bg-green-500'} opacity-50`}></div>
                    <div className="flex justify-between items-start mb-2">
                        <div className="flex items-center gap-2">
                            <h3 className="text-secondary font-medium uppercase tracking-wider text-sm">Beta (Risk)</h3>
                            <HelpTrigger topicId="beta" size={14} className="opacity-50 hover:opacity-100" />
                        </div>
                        <AlertTriangle size={16} className="text-slate-500" />
                    </div>
                    <div className="flex items-baseline gap-2">
                        <span className={`text-3xl font-bold ${metrics.beta && metrics.beta > 1.5 ? 'text-red-400' : metrics.beta && metrics.beta > 1 ? 'text-amber-400' : 'text-green-400'}`}>
                            {metrics.beta?.toFixed(2) || 'N/A'}
                        </span>
                    </div>
                    <div className="mt-3 text-xs text-slate-400 space-y-1">
                        <div className="flex justify-between">
                            <span>Market = 1.0</span>
                            <span className="text-text">{metrics.beta && metrics.beta > 1.5 ? 'High' : metrics.beta && metrics.beta > 1 ? 'Moderate' : 'Low'}</span>
                        </div>
                    </div>
                    <p className="text-xs text-slate-500 mt-3">{metrics.beta && metrics.beta > 1.5 ? 'Moves 1.5x+ vs market' : metrics.beta && metrics.beta > 1 ? 'More volatile than market' : 'Less volatile than market'}</p>
                </div>

                {/* Shares Outstanding */}
                <div className="bg-surface p-6 rounded-xl border border-slate-800 relative overflow-hidden group hover:border-slate-700 transition-colors">
                    <div className="absolute top-0 left-0 w-1 h-full bg-purple-500 opacity-50"></div>
                    <div className="flex justify-between items-start mb-2">
                        <div className="flex items-center gap-2">
                            <h3 className="text-secondary font-medium uppercase tracking-wider text-sm">Shares Outstanding</h3>
                            <HelpTrigger topicId="shareChange" size={14} className="opacity-50 hover:opacity-100" />
                        </div>
                        <TrendingUp size={16} className="text-slate-500" />
                    </div>
                    <div className="flex items-baseline gap-2">
                        <span className="text-3xl font-bold text-purple-400">{metrics.shares_outstanding ? `${(metrics.shares_outstanding / 1e9).toFixed(2)}B` : 'N/A'}</span>
                    </div>
                    <div className="mt-3 text-xs text-slate-400 space-y-1">
                        <div className="flex justify-between">
                            <span>Market Cap</span>
                            <span className="text-text">${(metrics.market_cap / 1e9).toFixed(0)}B</span>
                        </div>
                    </div>
                    <p className="text-xs text-slate-500 mt-3">Track for buybacks/dilution</p>
                </div>

                {/* Sector */}
                <div className="bg-surface p-6 rounded-xl border border-slate-800 relative overflow-hidden group hover:border-slate-700 transition-colors">
                    <div className="absolute top-0 left-0 w-1 h-full bg-indigo-500 opacity-50"></div>
                    <div className="flex justify-between items-start mb-2">
                        <div className="flex items-center gap-2">
                            <h3 className="text-secondary font-medium uppercase tracking-wider text-sm">Sector</h3>
                        </div>
                        <PieChart size={16} className="text-slate-500" />
                    </div>
                    <div className="flex items-baseline gap-2">
                        <span className="text-2xl font-bold text-indigo-400">{stockData.profile.sector || 'N/A'}</span>
                    </div>
                    <div className="mt-3 text-xs text-slate-400 space-y-1">
                        <div className="flex justify-between">
                            <span>Industry</span>
                            <span className="text-text truncate ml-2">{stockData.profile.industry || 'N/A'}</span>
                        </div>
                    </div>
                    <p className="text-xs text-slate-500 mt-3 line-clamp-1">{stockData.profile.description?.slice(0, 60) || 'No description'}...</p>
                </div>
            </div>
        </div>
    );
}
