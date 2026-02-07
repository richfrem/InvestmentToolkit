import { useState, useMemo } from 'react';
import type { StockData } from '../services/api';
import { TrendingUp, TrendingDown, Scale, Info } from 'lucide-react';

interface ValuationModelerProps {
    stockData: StockData;
}

interface ScenarioInputs {
    growthRate: number;
    netMargin: number;
    exitPE: number;
    shareChange: number;
}

type ScenarioType = 'bear' | 'base' | 'bull';

const INITIAL_SCENARIOS: Record<ScenarioType, ScenarioInputs> = {
    bear: { growthRate: 5, netMargin: 15, exitPE: 15, shareChange: 2 },
    base: { growthRate: 10, netMargin: 20, exitPE: 25, shareChange: 0 },
    bull: { growthRate: 20, netMargin: 25, exitPE: 35, shareChange: -2 },
};

const VALIDATION = {
    growthRate: { min: -50, max: 200, label: 'Growth Rate' },
    netMargin: { min: -100, max: 100, label: 'Net Margin' },
    exitPE: { min: 1, max: 200, label: 'Exit P/E' },
    shareChange: { min: -20, max: 20, label: 'Share Change' },
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
    shareChange: number
): number {
    const projectedRevenue = revenue * Math.pow(1 + growthRate / 100, 5);
    const projectedNetIncome = projectedRevenue * (netMargin / 100);
    const projectedShares = shares * Math.pow(1 + shareChange / 100, 5);
    const projectedEPS = projectedNetIncome / projectedShares;
    return projectedEPS * exitPE;
}

function getValuationStatus(
    currentPrice: number,
    bearTarget: number,
    baseTarget: number,
    bullTarget: number
): { label: string; color: string; description: string } {
    if (currentPrice < bearTarget) {
        const upside = ((bearTarget / currentPrice) - 1) * 100;
        return { label: 'Strong Value', color: 'text-green-400', description: `${upside.toFixed(0)}% upside to Bear` };
    } else if (currentPrice < baseTarget) {
        const upside = ((baseTarget / currentPrice) - 1) * 100;
        return { label: 'Potential Value', color: 'text-emerald-400', description: `${upside.toFixed(0)}% upside to Base` };
    } else if (currentPrice < bullTarget) {
        const upside = ((bullTarget / currentPrice) - 1) * 100;
        return { label: 'Fairly Valued', color: 'text-amber-400', description: `${upside.toFixed(0)}% upside to Bull` };
    } else {
        const downside = ((currentPrice / bullTarget) - 1) * 100;
        return { label: 'Overvalued', color: 'text-red-400', description: `${downside.toFixed(0)}% above Bull` };
    }
}

export default function ValuationModeler({ stockData }: ValuationModelerProps) {
    const [activeScenario, setActiveScenario] = useState<ScenarioType>('base');
    const [scenarios, setScenarios] = useState<Record<ScenarioType, ScenarioInputs>>(INITIAL_SCENARIOS);

    const revenue = stockData.metrics.revenue || 0;
    const shares = stockData.metrics.shares_outstanding || 1;
    const currentPrice = stockData.price;
    const sector = stockData.profile.sector || 'default';
    const peRange = INDUSTRY_PE_RANGES[sector] || INDUSTRY_PE_RANGES['default'];

    const targetPrices = useMemo(() => ({
        bear: calculateTargetPrice(revenue, scenarios.bear.growthRate, scenarios.bear.netMargin, scenarios.bear.exitPE, shares, scenarios.bear.shareChange),
        base: calculateTargetPrice(revenue, scenarios.base.growthRate, scenarios.base.netMargin, scenarios.base.exitPE, shares, scenarios.base.shareChange),
        bull: calculateTargetPrice(revenue, scenarios.bull.growthRate, scenarios.bull.netMargin, scenarios.bull.exitPE, shares, scenarios.bull.shareChange),
    }), [scenarios, revenue, shares]);

    const valuationStatus = useMemo(() =>
        getValuationStatus(currentPrice, targetPrices.bear, targetPrices.base, targetPrices.bull),
        [currentPrice, targetPrices]
    );

    const updateScenario = (field: keyof ScenarioInputs, value: number) => {
        const validation = VALIDATION[field];
        const clampedValue = Math.max(validation.min, Math.min(validation.max, value));
        setScenarios(prev => ({
            ...prev,
            [activeScenario]: { ...prev[activeScenario], [field]: clampedValue }
        }));
    };

    const scenarioColors: Record<ScenarioType, string> = {
        bear: 'border-red-500/50 bg-red-500/10',
        base: 'border-amber-500/50 bg-amber-500/10',
        bull: 'border-green-500/50 bg-green-500/10',
    };

    return (
        <div className="bg-surface rounded-xl p-6 border border-slate-800 space-y-6">
            <div className="flex justify-between items-start">
                <div>
                    <h3 className="text-xl font-bold text-text">Valuation Modeler</h3>
                    <p className="text-secondary text-sm">5-Year Target Price Analysis</p>
                </div>
                <div className={`px-4 py-2 rounded-lg border ${valuationStatus.color.replace('text-', 'border-')}/30 ${valuationStatus.color.replace('text-', 'bg-')}/10`}>
                    <div className={`font-bold ${valuationStatus.color}`}>{valuationStatus.label}</div>
                    <div className="text-xs text-secondary">{valuationStatus.description}</div>
                </div>
            </div>

            {/* Scenario Tabs */}
            <div className="flex gap-2">
                {(['bear', 'base', 'bull'] as ScenarioType[]).map(scenario => (
                    <button
                        key={scenario}
                        onClick={() => setActiveScenario(scenario)}
                        className={`flex-1 py-3 px-4 rounded-lg border transition-all duration-200 font-medium capitalize
                            ${activeScenario === scenario
                                ? scenarioColors[scenario] + ' ring-2 ring-offset-2 ring-offset-background ring-primary/50'
                                : 'border-slate-700 bg-slate-800/50 hover:bg-slate-800'}`}
                    >
                        {scenario === 'bear' && <TrendingDown className="inline mr-2 h-4 w-4" />}
                        {scenario === 'base' && <Scale className="inline mr-2 h-4 w-4" />}
                        {scenario === 'bull' && <TrendingUp className="inline mr-2 h-4 w-4" />}
                        {scenario}
                        <span className="block text-xs mt-1 text-secondary">${targetPrices[scenario].toFixed(2)}</span>
                    </button>
                ))}
            </div>

            {/* Input Sliders */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {(Object.keys(VALIDATION) as Array<keyof ScenarioInputs>).map(field => {
                    const config = VALIDATION[field];
                    const value = scenarios[activeScenario][field];
                    return (
                        <div key={field} className="space-y-2">
                            <div className="flex justify-between items-center">
                                <label className="text-sm text-secondary">{config.label}</label>
                                <div className="flex items-center gap-2">
                                    <input
                                        type="number"
                                        value={value}
                                        onChange={e => updateScenario(field, parseFloat(e.target.value) || 0)}
                                        className="w-20 bg-slate-800 border border-slate-700 rounded px-2 py-1 text-right text-sm focus:ring-2 focus:ring-primary/50 focus:border-primary"
                                    />
                                    <span className="text-xs text-secondary">{field === 'exitPE' ? 'x' : '%'}</span>
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
                                <span>{config.min}{field === 'exitPE' ? 'x' : '%'}</span>
                                <span>{config.max}{field === 'exitPE' ? 'x' : '%'}</span>
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

            {/* Price Targets Summary */}
            <div className="grid grid-cols-3 gap-4 pt-4 border-t border-slate-800">
                {(['bear', 'base', 'bull'] as ScenarioType[]).map(scenario => {
                    const target = targetPrices[scenario];
                    const diff = ((target / currentPrice) - 1) * 100;
                    return (
                        <div key={scenario} className={`p-4 rounded-lg ${scenarioColors[scenario]} text-center`}>
                            <div className="text-xs uppercase text-secondary mb-1">{scenario}</div>
                            <div className="text-2xl font-bold">${target.toFixed(2)}</div>
                            <div className={`text-sm ${diff >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                {diff >= 0 ? '+' : ''}{diff.toFixed(1)}%
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
