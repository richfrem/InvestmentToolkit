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
        <div className="bg-surface rounded-xl p-4 border border-slate-800">
            {/* Header */}
            <div className="flex justify-between items-center mb-4">
                <div className="flex items-center gap-4">
                    <div>
                        <h3 className="text-lg font-bold text-text">ValuationModeler</h3>
                        <p className="text-secondary text-xs">5-Year Discounted Cash Flow (DCF)</p>
                    </div>
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

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">

                {/* LEFT PANEL: Inputs (Col Span 7) */}
                <div className="lg:col-span-7 space-y-4">

                    {/* Scenario Selector */}
                    <div className="grid grid-cols-3 gap-2 mb-4">
                        {(['bear', 'base', 'bull'] as ScenarioType[]).map(scenario => (
                            <button
                                key={scenario}
                                onClick={() => setActiveScenario(scenario)}
                                className={`py-2 px-3 rounded-lg text-sm font-medium transition-all flex flex-col items-center justify-center gap-1
                                    ${activeScenario === scenario
                                        ? scenarioColors[scenario] + ' text-white shadow-lg ring-1 ring-white/10'
                                        : 'border-slate-700 bg-slate-800/30 hover:bg-slate-800/50 text-secondary'}`}
                            >
                                <div className="flex items-center gap-1.5">
                                    {scenario === 'bear' && <TrendingDown size={14} />}
                                    {scenario === 'base' && <Scale size={14} />}
                                    {scenario === 'bull' && <TrendingUp size={14} />}
                                    <span className="uppercase tracking-wider text-xs">{scenario}</span>
                                </div>
                            </button>
                        ))}
                    </div>

                    {/* Compact Sliders Grid */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-4 bg-slate-900/30 p-4 rounded-xl border border-slate-800/50">

                        {/* Group 1: Core Growth */}
                        <div className="col-span-1 md:col-span-2 text-xs font-bold text-secondary uppercase tracking-wider mb-1 border-b border-slate-800 pb-1">
                            Growth & Profitability
                        </div>

                        {/* Growth Rate */}
                        <SliderControl
                            field="growthRate"
                            value={scenarios[activeScenario].growthRate}
                            onChange={updateScenario}
                            config={VALIDATION.growthRate}
                            yahooHint={`Yahoo: ${stockData.metrics.revenue_growth?.toFixed(1) ?? 'N/A'}%`}
                        />

                        {/* Net Margin */}
                        <SliderControl
                            field="netMargin"
                            value={scenarios[activeScenario].netMargin}
                            onChange={updateScenario}
                            config={VALIDATION.netMargin}
                            yahooHint={`Yahoo: ${stockData.metrics.profit_margin?.toFixed(1) ?? 'N/A'}%`}
                        />

                        {/* Group 2: Valuation Multiples */}
                        <div className="col-span-1 md:col-span-2 text-xs font-bold text-secondary uppercase tracking-wider mb-1 mt-2 border-b border-slate-800 pb-1">
                            Valuation Assumptions
                        </div>

                        {/* Exit P/E */}
                        <SliderControl
                            field="exitPE"
                            value={scenarios[activeScenario].exitPE}
                            onChange={updateScenario}
                            config={VALIDATION.exitPE}
                            yahooHint={`Fwd: ${stockData.metrics.forward_pe?.toFixed(1) ?? 'N/A'}x`}
                            extraInfo={<span className="text-[10px] text-slate-500">Sector: {peRange.min}-{peRange.max}x</span>}
                        />

                        {/* Discount Rate */}
                        <SliderControl
                            field="discountRate"
                            value={scenarios[activeScenario].discountRate}
                            onChange={updateScenario}
                            config={VALIDATION.discountRate}
                            yahooHint="Typ: 8-12%"
                        />

                        {/* Group 3: Capital Structure */}
                        <div className="col-span-1 md:col-span-2 text-xs font-bold text-secondary uppercase tracking-wider mb-1 mt-2 border-b border-slate-800 pb-1">
                            Structure & Time
                        </div>

                        {/* Share Change */}
                        <SliderControl
                            field="shareChange"
                            value={scenarios[activeScenario].shareChange}
                            onChange={updateScenario}
                            config={VALIDATION.shareChange}
                            yahooHint="( - ) Buyback | ( + ) Dilution"
                        />

                        {/* Time Horizon */}
                        <SliderControl
                            field="timeHorizon"
                            value={scenarios[activeScenario].timeHorizon}
                            onChange={updateScenario}
                            config={VALIDATION.timeHorizon}
                            yahooHint="Def: 5yr"
                        />
                    </div>
                </div>

                {/* RIGHT PANEL: Results (Col Span 5) */}
                <div className="lg:col-span-5 space-y-4">

                    {/* Main Result Card */}
                    <div className={`p-5 rounded-xl border ${isPositive ? 'border-green-500/30 bg-green-500/5' : 'border-red-500/30 bg-red-500/5'} flex flex-col items-center justify-center text-center h-32 relative overflow-hidden`}>
                        <div className="absolute top-2 right-2 text-[10px] uppercase tracking-widest text-secondary font-medium">Target Price</div>
                        <div className="z-10">
                            <div className="text-4xl font-bold mb-1 text-white tracking-tight">
                                ${activeTarget.toFixed(0)}
                            </div>
                            <div className={`text-sm font-medium flex items-center gap-1 justify-center ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
                                {isPositive ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
                                {isPositive ? '+' : ''}{activeDiff.toFixed(1)}% Upside
                            </div>
                        </div>
                        {/* Background Spline Effect (simplified) */}
                        <div className={`absolute -bottom-8 -right-8 w-24 h-24 rounded-full blur-2xl opacity-20 ${isPositive ? 'bg-green-500' : 'bg-red-500'}`}></div>
                    </div>

                    {/* Scenario Comparison Table */}
                    <div className="bg-slate-900/50 rounded-xl border border-slate-800 overflow-hidden">
                        <div className="grid grid-cols-3 text-xs font-medium text-secondary text-center py-2 border-b border-slate-800 bg-slate-900">
                            <div>Bear</div>
                            <div>Base</div>
                            <div>Bull</div>
                        </div>
                        <div className="grid grid-cols-3 divide-x divide-slate-800">
                            {(['bear', 'base', 'bull'] as ScenarioType[]).map(s => {
                                const t = targetPrices[s];
                                const d = ((t / currentPrice) - 1) * 100;
                                const isActive = activeScenario === s;
                                return (
                                    <div key={s}
                                        onClick={() => setActiveScenario(s)}
                                        className={`py-3 text-center cursor-pointer transition-colors hover:bg-slate-800/50 ${isActive ? 'bg-white/5' : ''}`}
                                    >
                                        <div className={`font-bold text-lg ${isActive ? 'text-white' : 'text-slate-300'}`}>${t.toFixed(0)}</div>
                                        <div className={`text-xs ${d >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                            {d >= 0 ? '+' : ''}{d.toFixed(0)}%
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </div>

                    {/* Analyst Consensus Summary */}
                    {estimates?.target_mean_price && (
                        <div className="bg-slate-900/30 rounded-lg p-3 border border-slate-800">
                            <div className="flex justify-between items-center mb-2">
                                <h4 className="text-xs font-bold text-secondary uppercase tracking-wider flex items-center gap-1">
                                    <Info size={10} /> Analyst Consensus (12mo)
                                </h4>
                                <span className="text-xs text-slate-400">{estimates.recommendation?.toUpperCase()}</span>
                            </div>
                            <div className="flex items-center justify-between text-sm">
                                <div className="text-red-400 font-medium">${estimates.target_low_price?.toFixed(0)}</div>
                                <div className="text-amber-400 font-medium">${estimates.target_mean_price?.toFixed(0)}</div>
                                <div className="text-green-400 font-medium">${estimates.target_high_price?.toFixed(0)}</div>
                            </div>
                            <div className="w-full h-1.5 bg-slate-800 rounded-full mt-1 relative overflow-hidden">
                                <div className="absolute h-full w-full bg-gradient-to-r from-red-500 via-amber-500 to-green-500 opacity-30"></div>
                                {/* Current Price Marker */}
                                <div
                                    className="absolute h-2.5 w-1 bg-white top-1/2 -translate-y-1/2 shadow-sm rounded-full"
                                    style={{ left: `${Math.min(100, Math.max(0, ((currentPrice - (estimates.target_low_price || 0)) / ((estimates.target_high_price || 1) - (estimates.target_low_price || 0))) * 100))}%` }}
                                />
                            </div>
                        </div>
                    )}
                </div>
            </div>

            {/* Notes Modal (Kept as is) */}
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

// Helper Component for Sliders to reduce boilerplate
function SliderControl({ field, value, onChange, config, yahooHint, extraInfo }: {
    field: keyof ScenarioInputs,
    value: number,
    onChange: (f: keyof ScenarioInputs, v: number) => void,
    config: { min: number, max: number, label: string },
    yahooHint?: string,
    extraInfo?: React.ReactNode
}) {
    return (
        <div className="space-y-1.5">
            <div className="flex justify-between items-center">
                <label className="text-xs font-medium text-slate-300 flex items-center gap-1.5">
                    {config.label}
                    <HelpTrigger topicId={field} size={10} className="opacity-50 hover:opacity-100" />
                </label>
                <div className="flex items-center gap-1.5">
                    <input
                        type="number"
                        value={value}
                        onChange={e => onChange(field, parseFloat(e.target.value) || 0)}
                        className="w-16 bg-slate-800 border border-slate-700 rounded px-1.5 py-0.5 text-right text-xs focus:ring-1 focus:ring-primary focus:border-primary transition-all"
                    />
                    <span className="text-[10px] text-slate-500 w-3">{field === 'exitPE' ? 'x' : field === 'timeHorizon' ? 'yr' : '%'}</span>
                </div>
            </div>
            <div className="relative h-4 flex items-center">
                <input
                    type="range"
                    min={config.min}
                    max={config.max}
                    value={value}
                    onChange={e => onChange(field, parseFloat(e.target.value))}
                    className="w-full h-1.5 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-primary hover:accent-primary/80 transition-all"
                />
            </div>
            <div className="flex justify-between items-center text-[10px] text-slate-500">
                <span>{config.min}</span>
                <span className="text-amber-400/70 font-medium">{yahooHint}</span>
                <span>{config.max}</span>
            </div>
            {extraInfo && <div className="mt-0.5">{extraInfo}</div>}
        </div>
    );
}
