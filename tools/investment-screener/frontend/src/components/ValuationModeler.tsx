import { useState, useMemo, useEffect } from 'react';
import type { StockData } from '../services/api';
import { TrendingUp, TrendingDown, Scale, Info, RotateCcw, Save, X, FileText } from 'lucide-react';
import { HelpTrigger } from './HelpModal';

interface ValuationModelerProps {
    stockData: StockData;
}

interface ScenarioInputs {
    growthRate: number;
    netMargin: number;
    exitPE: number;
    shareChange: number;
    discountRate: number;
    timeHorizon: number;
}

type ScenarioType = 'bear' | 'base' | 'bull';

const INITIAL_SCENARIOS: Record<ScenarioType, ScenarioInputs> = {
    bear: { growthRate: 5, netMargin: 15, exitPE: 15, shareChange: 2, discountRate: 12, timeHorizon: 5 },
    base: { growthRate: 10, netMargin: 20, exitPE: 25, shareChange: 0, discountRate: 10, timeHorizon: 5 },
    bull: { growthRate: 20, netMargin: 25, exitPE: 35, shareChange: -2, discountRate: 8, timeHorizon: 5 },
};

const VALIDATION = {
    growthRate: { min: -50, max: 200, label: 'Growth Rate' },
    netMargin: { min: -100, max: 100, label: 'Net Margin' },
    exitPE: { min: 1, max: 200, label: 'Exit P/E' },
    shareChange: { min: -20, max: 20, label: 'Share Change' },
    discountRate: { min: 0, max: 30, label: 'Discount Rate' },
    timeHorizon: { min: 1, max: 10, label: 'Time Horizon' },
};

const INDUSTRY_PE_RANGES: Record<string, { min: number; max: number }> = {
    'Technology': { min: 25, max: 40 },
    'Healthcare': { min: 15, max: 25 },
    'Retail': { min: 10, max: 20 },
    'Financials': { min: 8, max: 15 },
    'default': { min: 12, max: 25 },
};

function calculateTargetPrice(
    revenue: number,
    growthRate: number,
    netMargin: number,
    exitPE: number,
    shares: number,
    shareChange: number,
    discountRate: number,
    timeHorizon: number
): number {
    const projectedRevenue = revenue * Math.pow(1 + growthRate / 100, timeHorizon);
    const projectedNetIncome = projectedRevenue * (netMargin / 100);
    const projectedShares = shares * Math.pow(1 + shareChange / 100, timeHorizon);
    const projectedEPS = projectedNetIncome / projectedShares;
    const futurePrice = projectedEPS * exitPE;
    // Discount back to present value
    const presentValue = futurePrice / Math.pow(1 + discountRate / 100, timeHorizon);
    return presentValue;
}



export default function ValuationModeler({ stockData }: ValuationModelerProps) {
    const [activeScenario, setActiveScenario] = useState<ScenarioType>('base');
    const [scenarios, setScenarios] = useState<Record<ScenarioType, ScenarioInputs>>(INITIAL_SCENARIOS);
    const [notes, setNotes] = useState('');
    const [showNotesModal, setShowNotesModal] = useState(false);

    const revenue = stockData.metrics.revenue || 0;
    const shares = stockData.metrics.shares_outstanding || 1;
    const currentPrice = stockData.price;
    const sector = stockData.profile.sector || 'default';
    const peRange = INDUSTRY_PE_RANGES[sector] || INDUSTRY_PE_RANGES['default'];

    // Get analyst estimates from API
    const estimates = stockData.analyst_estimates;

    // Load saved projections from localStorage
    useEffect(() => {
        const key = `projection_${stockData.symbol}`;
        const saved = localStorage.getItem(key);
        if (saved) {
            try {
                const data = JSON.parse(saved);
                if (data.scenarios) {
                    setScenarios(data.scenarios);
                }
                if (data.notes) {
                    setNotes(data.notes);
                }
            } catch (e) {
                console.warn('Failed to parse saved projection:', e);
            }
        }
    }, [stockData.symbol]);

    // Update scenarios when stock data changes (only if no saved projection)
    useEffect(() => {
        const key = `projection_${stockData.symbol}`;
        const saved = localStorage.getItem(key);
        if (saved) return; // Don't override saved projections

        if (estimates) {
            const newBaseGrowth = Math.round(estimates.revenue_growth || 10);
            const newBaseMargin = Math.round(estimates.profit_margin || 20);
            const newBasePE = Math.round(estimates.forward_pe || 25);
            setScenarios(prev => ({
                bear: { ...prev.bear, growthRate: Math.max(newBaseGrowth - 5, 0), netMargin: Math.max(newBaseMargin - 5, 5), exitPE: Math.max(newBasePE - 10, 10), shareChange: 2 },
                base: { ...prev.base, growthRate: newBaseGrowth, netMargin: newBaseMargin, exitPE: newBasePE, shareChange: 0 },
                bull: { ...prev.bull, growthRate: newBaseGrowth + 10, netMargin: newBaseMargin + 5, exitPE: newBasePE + 10, shareChange: -2 },
            }));
        }
    }, [stockData.symbol]);

    const targetPrices = useMemo(() => ({
        bear: calculateTargetPrice(revenue, scenarios.bear.growthRate, scenarios.bear.netMargin, scenarios.bear.exitPE, shares, scenarios.bear.shareChange, scenarios.bear.discountRate, scenarios.bear.timeHorizon),
        base: calculateTargetPrice(revenue, scenarios.base.growthRate, scenarios.base.netMargin, scenarios.base.exitPE, shares, scenarios.base.shareChange, scenarios.base.discountRate, scenarios.base.timeHorizon),
        bull: calculateTargetPrice(revenue, scenarios.bull.growthRate, scenarios.bull.netMargin, scenarios.bull.exitPE, shares, scenarios.bull.shareChange, scenarios.bull.discountRate, scenarios.bull.timeHorizon),
    }), [scenarios, revenue, shares]);



    const updateScenario = (field: keyof ScenarioInputs, value: number) => {
        const validation = VALIDATION[field];
        const clampedValue = Math.max(validation.min, Math.min(validation.max, value));
        setScenarios(prev => ({
            ...prev,
            [activeScenario]: { ...prev[activeScenario], [field]: clampedValue }
        }));
    };

    // Reset current scenario to Yahoo analyst estimates
    const resetToYahoo = () => {
        const yahooGrowth = Math.round(stockData.metrics.revenue_growth ?? estimates?.revenue_growth ?? 10);
        const yahooMargin = Math.round(stockData.metrics.profit_margin ?? estimates?.profit_margin ?? 20);
        const yahooPE = Math.round(stockData.metrics.forward_pe ?? estimates?.forward_pe ?? 25);
        // Default values for new sliders
        const defaultDiscountRate = 10;
        const defaultTimeHorizon = 5;

        if (activeScenario === 'bear') {
            setScenarios(prev => ({ ...prev, bear: { ...prev.bear, growthRate: Math.max(yahooGrowth - 5, 0), netMargin: Math.max(yahooMargin - 5, 5), exitPE: Math.max(yahooPE - 10, 10), shareChange: 2, discountRate: 12, timeHorizon: defaultTimeHorizon } }));
        } else if (activeScenario === 'base') {
            setScenarios(prev => ({ ...prev, base: { ...prev.base, growthRate: yahooGrowth, netMargin: yahooMargin, exitPE: yahooPE, shareChange: 0, discountRate: defaultDiscountRate, timeHorizon: defaultTimeHorizon } }));
        } else {
            setScenarios(prev => ({ ...prev, bull: { ...prev.bull, growthRate: yahooGrowth + 10, netMargin: yahooMargin + 5, exitPE: yahooPE + 10, shareChange: -2, discountRate: 8, timeHorizon: defaultTimeHorizon } }));
        }
    };

    // Save custom projection with notes to localStorage
    const saveProjection = () => {
        const key = `projection_${stockData.symbol}`;
        localStorage.setItem(key, JSON.stringify({
            symbol: stockData.symbol,
            scenarios,
            notes,
            savedAt: new Date().toISOString()
        }));
        setShowNotesModal(false);
        alert(`Saved projection for ${stockData.symbol}`);
    };

    const scenarioColors: Record<ScenarioType, string> = {
        bear: 'border-red-500/50 bg-red-500/10',
        base: 'border-amber-500/50 bg-amber-500/10',
        bull: 'border-green-500/50 bg-green-500/10',
    };

    // Calculate percentage for ACTIVE scenario
    const activeTarget = targetPrices[activeScenario];
    const activeDiff = ((activeTarget / currentPrice) - 1) * 100;
    const isPositive = activeDiff >= 0;

    return (
        <div className="bg-surface rounded-xl p-4 border border-slate-800 space-y-3">
            <div className="flex justify-between items-center">
                <div className="flex items-center gap-4">
                    <div>
                        <h3 className="text-lg font-bold text-text">ValuationModeler</h3>
                        <p className="text-secondary text-xs">5-Year Target</p>
                    </div>
                    <div className="flex gap-2">
                        <button
                            onClick={resetToYahoo}
                            className="flex items-center gap-2 px-3 py-1.5 text-xs bg-slate-700 hover:bg-slate-600 border border-slate-600 rounded-lg transition-colors"
                            title="Reset to Yahoo Estimates"
                        >
                            <RotateCcw size={12} />
                            Reset
                        </button>
                        {notes && (
                            <button
                                onClick={() => setShowNotesModal(true)}
                                className="flex items-center gap-2 px-3 py-1.5 text-xs bg-slate-700 hover:bg-slate-600 border border-slate-600 rounded-lg transition-colors"
                            >
                                <FileText size={12} />
                                Notes
                            </button>
                        )}
                        <button
                            onClick={() => setShowNotesModal(true)}
                            className="flex items-center gap-2 px-3 py-1.5 text-xs bg-primary/20 hover:bg-primary/30 border border-primary/50 text-primary rounded-lg transition-colors"
                        >
                            <Save size={12} />
                            Save
                        </button>
                    </div>
                </div>
                <div className={`px-4 py-2 rounded-lg border ${isPositive ? 'border-green-500/40 bg-green-500/10' : 'border-red-500/40 bg-red-500/10'}`}>
                    <div className={`text-2xl font-bold ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
                        {isPositive ? '+' : ''}{activeDiff.toFixed(0)}%
                    </div>
                    <div className="text-xs text-secondary capitalize">{activeScenario} → ${activeTarget.toFixed(0)}</div>
                </div>
            </div>

            {/* Scenario Tabs */}
            <div className="grid grid-cols-3 gap-2">
                {(['bear', 'base', 'bull'] as ScenarioType[]).map(scenario => (
                    <button
                        key={scenario}
                        onClick={() => setActiveScenario(scenario)}
                        className={`py-2 px-3 rounded-lg text-sm font-medium transition-all
                            ${activeScenario === scenario
                                ? scenarioColors[scenario] + ' text-white shadow-lg'
                                : 'border-slate-700 bg-slate-800/50 hover:bg-slate-800'}`}
                    >
                        {scenario === 'bear' && <TrendingDown className="inline mr-1 h-3 w-3" />}
                        {scenario === 'base' && <Scale className="inline mr-1 h-3 w-3" />}
                        {scenario === 'bull' && <TrendingUp className="inline mr-1 h-3 w-3" />}
                        {scenario}
                        <span className="ml-2 text-xs text-secondary">${targetPrices[scenario].toFixed(0)}</span>
                    </button>
                ))}
            </div>



            {/* Input Sliders with Yahoo Hints */}
            <div className="grid grid-cols-2 gap-4">
                {(Object.keys(VALIDATION) as Array<keyof ScenarioInputs>).map(field => {
                    const config = VALIDATION[field];
                    const value = scenarios[activeScenario][field];
                    // Yahoo reference values for hints
                    // Helper to properly handle 0/negative values (avoiding || operator which treats them as falsy)
                    const getYahooValue = (primary: number | undefined, secondary: number | undefined, suffix: string = ''): string => {
                        if (primary !== undefined && primary !== null) return `${primary.toFixed(1)}${suffix}`;
                        if (secondary !== undefined && secondary !== null) return `${secondary.toFixed(1)}${suffix}`;
                        return `N/A${suffix}`;
                    };

                    const yahooHints: Record<keyof ScenarioInputs, string> = {
                        growthRate: `Yahoo: ${getYahooValue(stockData.metrics.revenue_growth, estimates?.revenue_growth, '%')}`,
                        netMargin: `Yahoo: ${getYahooValue(stockData.metrics.profit_margin, estimates?.profit_margin, '%')}`,
                        exitPE: `Yahoo Fwd: ${getYahooValue(stockData.metrics.forward_pe, estimates?.forward_pe, 'x')}`,
                        shareChange: 'Your estimate',
                        discountRate: 'Typical: 8-12%',
                        timeHorizon: 'Default: 5 years',
                    };
                    return (
                        <div key={field} className="space-y-1">
                            <div className="flex justify-between items-center">
                                <label className="text-sm text-secondary flex items-center gap-1">
                                    {config.label}
                                    <HelpTrigger topicId={field} size={12} />
                                </label>
                                <div className="flex items-center gap-2">
                                    <input
                                        type="number"
                                        value={value}
                                        onChange={e => updateScenario(field, parseFloat(e.target.value) || 0)}
                                        className="w-20 bg-slate-800 border border-slate-700 rounded px-2 py-1 text-right text-sm focus:ring-2 focus:ring-primary/50 focus:border-primary"
                                    />
                                    <span className="text-xs text-secondary">{field === 'exitPE' ? 'x' : field === 'timeHorizon' ? 'yr' : '%'}</span>
                                </div>
                            </div>
                            <input
                                type="range"
                                min={config.min}
                                max={config.max}
                                value={value}
                                onChange={e => updateScenario(field, parseFloat(e.target.value))}
                                className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-primary"
                            />
                            <div className="flex justify-between text-xs text-slate-500">
                                <span>{config.min}{field === 'exitPE' ? 'x' : field === 'timeHorizon' ? 'yr' : '%'}</span>
                                <span className="text-amber-400/80">{yahooHints[field]}</span>
                                <span>{config.max}{field === 'exitPE' ? 'x' : field === 'timeHorizon' ? 'yr' : '%'}</span>
                            </div>
                            {field === 'exitPE' && (
                                <div className="flex items-center gap-1 text-xs text-secondary">
                                    <Info size={12} />
                                    <span>Typical {sector} range: {peRange.min}x - {peRange.max}x</span>
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>

            {/* Analyst Consensus Bar */}
            {estimates?.target_low_price && (
                <div className="flex items-center gap-2 text-xs pt-3 border-t border-slate-800">
                    <Info size={12} className="text-amber-400" />
                    <span className="text-secondary">Analysts ({estimates.number_of_analysts})</span>
                    <span className="text-red-400 font-medium">${estimates.target_low_price.toFixed(0)}</span>
                    <div className="flex-1 h-1 bg-slate-700 rounded-full relative mx-1">
                        <div
                            className="absolute h-full bg-gradient-to-r from-red-500 via-amber-500 to-green-500 rounded-full opacity-50"
                            style={{
                                left: '0%',
                                right: '0%' // Simplified for now
                            }}
                        />
                        {/* Current Price Marker */}
                        <div
                            className="absolute h-2 w-2 bg-white rounded-full top-1/2 -translate-y-1/2 shadow"
                            style={{
                                left: `${Math.max(0, Math.min(100, ((currentPrice - estimates.target_low_price) / (estimates.target_high_price - estimates.target_low_price)) * 100))}%`
                            }}
                        />
                    </div>
                    <span className="text-green-400 font-medium">${estimates.target_high_price?.toFixed(0)}</span>
                    <span className="text-amber-400 text-sm font-medium">Mean: ${estimates?.target_mean_price?.toFixed(0)}</span>
                    <span className="text-xs text-secondary">{estimates?.recommendation?.toUpperCase()}</span>
                </div>
            )}

            {/* Price Targets Summary - Compact Row */}
            <div className="grid grid-cols-3 gap-3 pt-3 border-t border-slate-800">
                {(['bear', 'base', 'bull'] as ScenarioType[]).map(scenario => {
                    const target = targetPrices[scenario];
                    const diff = ((target / currentPrice) - 1) * 100;
                    return (
                        <div key={scenario} className={`p-3 rounded-lg ${scenarioColors[scenario]} text-center`}>
                            <div className="text-xs uppercase text-secondary">{scenario}</div>
                            <div className="text-xl font-bold">${target.toFixed(0)}</div>
                            <div className={`text-xs ${diff >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                {diff >= 0 ? '+' : ''}{diff.toFixed(0)}%
                            </div>
                        </div>
                    );
                })}
            </div>

            {/* Notes Modal */}
            {showNotesModal && (
                <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={() => setShowNotesModal(false)}>
                    <div className="bg-surface border border-slate-700 rounded-xl max-w-lg w-full shadow-2xl" onClick={e => e.stopPropagation()}>
                        <div className="flex justify-between items-center p-4 border-b border-slate-800">
                            <h3 className="text-lg font-bold">Save {stockData.symbol} Projection</h3>
                            <button onClick={() => setShowNotesModal(false)} className="p-1 hover:bg-slate-800 rounded">
                                <X size={20} className="text-secondary" />
                            </button>
                        </div>
                        <div className="p-4 space-y-4">
                            <div className="grid grid-cols-3 gap-2 text-sm">
                                <div className="text-center p-2 bg-red-500/10 rounded"><span className="text-secondary">Bear:</span> <span className="font-medium">${targetPrices.bear.toFixed(0)}</span></div>
                                <div className="text-center p-2 bg-amber-500/10 rounded"><span className="text-secondary">Base:</span> <span className="font-medium">${targetPrices.base.toFixed(0)}</span></div>
                                <div className="text-center p-2 bg-green-500/10 rounded"><span className="text-secondary">Bull:</span> <span className="font-medium">${targetPrices.bull.toFixed(0)}</span></div>
                            </div>
                            <div>
                                <label className="text-sm text-secondary block mb-2">Investment Thesis & Rationale</label>
                                <textarea
                                    value={notes}
                                    onChange={e => setNotes(e.target.value)}
                                    placeholder="Why these assumptions? E.g., 'Growth likely to decelerate from 63% to ~40% due to law of large numbers, TSMC bottlenecks, and competition from AMD/custom silicon...'"
                                    className="w-full h-32 bg-slate-800 border border-slate-700 rounded-lg p-3 text-sm resize-none focus:ring-2 focus:ring-primary/50 focus:border-primary"
                                />
                            </div>
                        </div>
                        <div className="p-4 border-t border-slate-800 flex gap-2 justify-end">
                            <button onClick={() => setShowNotesModal(false)} className="px-4 py-2 text-sm bg-slate-700 hover:bg-slate-600 rounded-lg">Cancel</button>
                            <button onClick={saveProjection} className="px-4 py-2 text-sm bg-primary text-black font-medium rounded-lg hover:bg-primary/90">Save Projection</button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
