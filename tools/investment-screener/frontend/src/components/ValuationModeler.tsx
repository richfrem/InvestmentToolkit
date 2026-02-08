import { useState, useEffect } from 'react';
import { Save, RotateCcw, FolderOpen, TrendingUp, TrendingDown, Info, X } from 'lucide-react';
import type { StockData } from '../services/api';
import { ProjectionsPanel } from './ProjectionsPanel';
import { storage } from '../services/storage';

interface ValuationModelerProps {
    stockData: StockData;
}

export default function ValuationModeler({ stockData }: ValuationModelerProps) {
    // --- State ---
    const [scenario, setScenario] = useState<'bear' | 'base' | 'bull'>('base');
    const [showProjectionsPanel, setShowProjectionsPanel] = useState(false);
    const [savedCount, setSavedCount] = useState(0);

    // Save Modal State
    const [showSaveModal, setShowSaveModal] = useState(false);
    const [saveName, setSaveName] = useState('');

    // Inputs (Base defaults)
    const [growthRate, setGrowthRate] = useState(15);
    const [netMargin, setNetMargin] = useState(20);
    const [peRatio, setPeRatio] = useState(25);
    const [discountRate, setDiscountRate] = useState(9);
    const [shareChange, setShareChange] = useState(-2); // Buybacks
    const [timeHorizon, setTimeHorizon] = useState(5);

    // Load initial saved count
    useEffect(() => {
        const saved = storage.getProjections(stockData.symbol);
        setSavedCount(saved.length);
    }, [stockData.symbol]);

    // Initialize with Yahoo Finance data/defaults when stockData changes
    useEffect(() => {
        resetToYahoo();
    }, [stockData, scenario]);

    const resetToYahoo = () => {
        // Simple logic tailored to scenario
        const multiplier = scenario === 'bull' ? 1.2 : scenario === 'bear' ? 0.8 : 1.0;

        // Use metrics from API (Prioritize Analyst Estimates if available)
        // Heuristic: If value > 1, assume it's already a percentage (e.g. 15.5). If < 1, assume decimal (e.g. 0.155)

        const rawGrowth = stockData.analyst_estimates?.revenue_growth ?? stockData.metrics?.revenue_growth ?? 0.15;
        const rawMargin = stockData.analyst_estimates?.profit_margin ?? stockData.metrics?.profit_margin ?? 0.20;

        const baseGrowth = Math.abs(rawGrowth) > 1 ? rawGrowth : rawGrowth * 100;
        const baseMargin = Math.abs(rawMargin) > 1 ? rawMargin : rawMargin * 100;

        const basePe = stockData.analyst_estimates?.forward_pe || stockData.metrics?.forward_pe || stockData.metrics?.pe_ratio || 25;

        setGrowthRate(Math.round(baseGrowth * multiplier));
        setNetMargin(Math.round(baseMargin * multiplier));
        setPeRatio(Math.round(basePe * multiplier));
        setDiscountRate(scenario === 'bull' ? 8 : scenario === 'bear' ? 12 : 10);
        setShareChange(-2);
        setTimeHorizon(5);
    };

    // --- Calculations ---

    const projectPrice = () => {
        const compoundGrowth = Math.pow(1 + growthRate / 100, timeHorizon);

        const currentPE = stockData.metrics?.forward_pe || stockData.metrics?.pe_ratio || 25;
        // Optimization: Avoid division by zero
        const effectiveCurrentPE = currentPE > 0 ? currentPE : 25;

        const fPrice = stockData.price * compoundGrowth * (peRatio / effectiveCurrentPE);

        // Discount back
        const presentValue = fPrice / Math.pow(1 + discountRate / 100, timeHorizon);
        return presentValue;
    };

    const targetPrice = projectPrice();
    const upside = ((targetPrice - stockData.price) / stockData.price) * 100;

    // --- Actions ---

    const handleSaveOpen = () => {
        setSaveName(`Projection ${new Date().toLocaleDateString()}`);
        setShowSaveModal(true);
    };

    const handleSaveConfirm = () => {
        if (!saveName.trim()) return;

        storage.saveProjection({
            id: Date.now().toString(),
            ticker: stockData.symbol,
            savedAt: new Date().toISOString(),
            name: saveName,
            scenarios: {
                growthRate,
                netMargin,
                exitPE: peRatio,
                shareChange,
                discountRate,
                timeHorizon,
                terminalGrowth: 3 // Default structural assumption
            }
        });

        setSavedCount(prev => prev + 1);
        setShowSaveModal(false);
    };

    const handleLoad = (scenarios: any) => {
        // Load parameters
        setGrowthRate(scenarios.growthRate);
        setNetMargin(scenarios.netMargin);
        setPeRatio(scenarios.exitPE);
        setDiscountRate(scenarios.discountRate);
        setShareChange(scenarios.shareChange);
        setTimeHorizon(scenarios.timeHorizon);

        setShowProjectionsPanel(false);
    };

    // --- Components ---

    const SliderInput = ({ label, value, setValue, min, max, unit = '', step = 1, note = '' }: any) => (
        <div className="mb-2">
            <div className="flex justify-between items-center mb-1">
                <label className="text-secondary text-[10px] font-medium uppercase tracking-wider flex items-center gap-1">
                    {label}
                </label>
                <div className="flex items-center bg-slate-800 rounded px-1.5 py-0.5 border border-slate-700">
                    <input
                        type="number"
                        value={value}
                        onChange={(e) => setValue(Number(e.target.value))}
                        className="w-10 bg-transparent text-right text-xs font-bold text-text focus:outline-none"
                    />
                    <span className="text-[10px] text-slate-500 ml-1">{unit}</span>
                </div>
            </div>
            <input
                type="range"
                min={min}
                max={max}
                step={step}
                value={value}
                onChange={(e) => setValue(Number(e.target.value))}
                className="w-full h-1 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-primary hover:accent-primary-hover transition-all"
            />
            <div className="flex justify-between text-[8px] text-slate-600 mt-0.5">
                <span>{min}</span>
                <span className="text-primary/70">{note}</span>
                <span>{max}</span>
            </div>
        </div>
    );

    return (
        <div className="flex flex-col h-full overflow-hidden relative p-1">
            {/* Header: Title & Actions */}
            <div className="flex justify-between items-center mb-4 flex-none">
                <div>
                    <h2 className="text-lg font-bold text-text">Valuation Modeler</h2>
                    <p className="text-[10px] text-secondary">5-Year Discounted Cash Flow (DCF)</p>
                </div>
                <div className="flex gap-2">
                    <button
                        onClick={() => setShowProjectionsPanel(true)}
                        className="flex items-center gap-2 px-2 py-1 rounded-lg bg-slate-800/80 text-primary hover:bg-slate-800 border border-slate-700/50 transition-all text-[10px] font-medium"
                    >
                        <FolderOpen size={12} />
                        My Projections
                        {savedCount > 0 && (
                            <span className="bg-primary text-slate-900 text-[9px] font-bold px-1 rounded-full">
                                {savedCount}
                            </span>
                        )}
                    </button>
                    <button
                        onClick={resetToYahoo}
                        className="flex items-center gap-2 px-2 py-1 rounded-lg bg-slate-800/50 text-slate-400 hover:text-white hover:bg-slate-800 border border-slate-700/50 transition-all text-[10px] font-medium"
                    >
                        <RotateCcw size={12} />
                        Reset
                    </button>
                    <button
                        onClick={handleSaveOpen}
                        className="flex items-center gap-2 px-2 py-1 rounded-lg bg-primary/10 text-primary hover:bg-primary/20 border border-primary/20 transition-all text-[10px] font-medium"
                    >
                        <Save size={12} />
                        Save
                    </button>
                </div>
            </div>

            {/* Top Row: Hero & Matrix (Side-by-side to save vertical space) */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-4 flex-none h-40">
                {/* Hero Section: Target Price (Span 2) */}
                <div className="lg:col-span-2 flex flex-col items-center justify-center bg-gradient-to-r from-slate-900/80 to-slate-900/30 rounded-xl border border-slate-800/50 relative overflow-hidden">
                    <div className="absolute top-2 right-2 flex gap-1 bg-slate-950/50 p-1 rounded-lg border border-slate-800/50 backdrop-blur-sm z-10">
                        {(['bear', 'base', 'bull'] as const).map((s) => (
                            <button
                                key={s}
                                onClick={() => setScenario(s)}
                                className={`px-3 py-1 rounded text-[10px] font-bold uppercase tracking-wider transition-all ${scenario === s
                                        ? s === 'bull' ? 'bg-green-500/20 text-green-400 border border-green-500/30'
                                            : s === 'bear' ? 'bg-red-500/20 text-red-400 border border-red-500/30'
                                                : 'bg-primary/20 text-primary border border-primary/30'
                                        : 'text-slate-600 hover:text-slate-400'
                                    }`}
                            >
                                {s}
                            </button>
                        ))}
                    </div>

                    <div className="text-[10px] font-medium text-secondary mb-1 uppercase tracking-widest mt-4">Target Price ({timeHorizon}yr)</div>
                    <div className="text-5xl font-black text-text tracking-tight mb-1">
                        ${Math.round(targetPrice)}
                    </div>
                    <div className={`flex items-center gap-1 text-sm font-bold px-2 py-0.5 rounded-full ${upside >= 0 ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'}`}>
                        {upside >= 0 ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
                        {upside > 0 ? '+' : ''}{upside.toFixed(1)}% Upside
                    </div>
                </div>

                {/* Vertical Matrix (Span 1) */}
                <div className="bg-surface border border-slate-800/50 rounded-xl p-3 flex flex-col justify-center">
                    <div className="space-y-2">
                        {[
                            { mode: 'Bear', price: Math.round(targetPrice * 0.6), upside: upside - 40, color: 'text-red-400' },
                            { mode: 'Base', price: Math.round(targetPrice), upside: upside, color: 'text-primary' },
                            { mode: 'Bull', price: Math.round(targetPrice * 1.4), upside: upside + 40, color: 'text-green-400' }
                        ].map((item) => (
                            <div key={item.mode} className="flex justify-between items-center p-2 bg-slate-900/50 rounded-lg">
                                <span className="text-xs font-bold text-secondary">{item.mode}</span>
                                <div className="text-right leading-none">
                                    <div className={`text-sm font-bold ${item.color}`}>${item.price}</div>
                                    <div className="text-[10px] text-slate-500">{item.upside > 0 ? '+' : ''}{item.upside.toFixed(0)}%</div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            {/* Inputs Grid: 3 Columns, auto-fit */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 flex-1 min-h-0">
                <section className="bg-slate-900/20 p-4 rounded-xl border border-slate-800">
                    <h3 className="text-xs font-bold text-white mb-3 flex items-center gap-2">
                        <span className="w-1 h-3 bg-primary rounded-full"></span>
                        Growth & Profitability
                    </h3>
                    <div className="space-y-4">
                        <SliderInput
                            label="Growth Rate"
                            value={growthRate}
                            setValue={setGrowthRate}
                            min={-50}
                            max={100}
                            unit="%"
                            note={`Yahoo: ${((() => {
                                const val = stockData.analyst_estimates?.revenue_growth ?? stockData.metrics?.revenue_growth ?? 0;
                                return (Math.abs(val) > 1 ? val : val * 100).toFixed(1);
                            })())}%`}
                        />
                        <SliderInput
                            label="Net Margin"
                            value={netMargin}
                            setValue={setNetMargin}
                            min={-20}
                            max={80}
                            unit="%"
                            note={`Yahoo: ${((() => {
                                const val = stockData.analyst_estimates?.profit_margin ?? stockData.metrics?.profit_margin ?? 0;
                                return (Math.abs(val) > 1 ? val : val * 100).toFixed(1);
                            })())}%`}
                        />
                    </div>
                </section>

                <section className="bg-slate-900/20 p-4 rounded-xl border border-slate-800">
                    <h3 className="text-xs font-bold text-white mb-3 flex items-center gap-2">
                        <span className="w-1 h-3 bg-primary rounded-full"></span>
                        Valuation Assumptions
                    </h3>
                    <div className="space-y-4">
                        <SliderInput
                            label="Exit P/E"
                            value={peRatio}
                            setValue={setPeRatio}
                            min={1}
                            max={100}
                            unit="x"
                            note={`Fwd: ${(stockData.analyst_estimates?.forward_pe || stockData.metrics?.forward_pe || 0).toFixed(1)}x`}
                        />
                        <SliderInput
                            label="Discount Rate"
                            value={discountRate}
                            setValue={setDiscountRate}
                            min={0}
                            max={20}
                            unit="%"
                            note="Typ: 8-12%"
                        />
                    </div>
                </section>

                <section className="bg-slate-900/20 p-4 rounded-xl border border-slate-800 flex flex-col">
                    <h3 className="text-xs font-bold text-white mb-3 flex items-center gap-2">
                        <span className="w-1 h-3 bg-primary rounded-full"></span>
                        Structure & Time
                    </h3>
                    <div className="space-y-4 flex-1">
                        <SliderInput
                            label="Share Change"
                            value={shareChange}
                            setValue={setShareChange}
                            min={-20}
                            max={20}
                            unit="%"
                            note="( - ) Buyback | ( + ) Dilution"
                        />
                        <SliderInput
                            label="Time Horizon"
                            value={timeHorizon}
                            setValue={setTimeHorizon}
                            min={1}
                            max={10}
                            unit="yr"
                            note="Def: 5yr"
                        />
                    </div>
                </section>
            </div>

            {/* Save Modal */}
            {showSaveModal && (
                <div className="absolute inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
                    <div className="bg-surface border border-slate-700 p-6 rounded-xl w-80 shadow-2xl scale-100">
                        <div className="flex justify-between items-center mb-4">
                            <h3 className="text-lg font-bold text-white">Save Projection</h3>
                            <button onClick={() => setShowSaveModal(false)} className="text-slate-400 hover:text-white">
                                <X size={20} />
                            </button>
                        </div>
                        <input
                            type="text"
                            value={saveName}
                            onChange={(e) => setSaveName(e.target.value)}
                            placeholder="Projection Name (e.g. Bull 2026)"
                            className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-white mb-4 focus:outline-none focus:border-primary"
                            autoFocus
                        />
                        <div className="flex gap-2">
                            <button
                                onClick={() => setShowSaveModal(false)}
                                className="flex-1 px-4 py-2 bg-slate-800 text-slate-300 rounded-lg hover:bg-slate-700 font-medium"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleSaveConfirm}
                                disabled={!saveName.trim()}
                                className="flex-1 px-4 py-2 bg-primary text-slate-900 rounded-lg hover:bg-primary-hover font-bold disabled:opacity-50"
                            >
                                Save
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Projections Panel Slide-over */}
            {showProjectionsPanel && (
                <ProjectionsPanel
                    isOpen={showProjectionsPanel}
                    onClose={() => setShowProjectionsPanel(false)}
                    ticker={stockData.symbol}
                    onLoad={handleLoad}
                />
            )}
        </div>
    );
}
