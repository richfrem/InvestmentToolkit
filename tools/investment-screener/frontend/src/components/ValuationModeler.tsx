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

        // Use metrics from API
        const baseGrowth = stockData.metrics?.revenue_growth ? stockData.metrics.revenue_growth * 100 : 15;
        const baseMargin = stockData.metrics?.profit_margin ? stockData.metrics.profit_margin * 100 : 20;
        const basePe = stockData.metrics?.forward_pe || stockData.metrics?.pe_ratio || 25;

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
        <div className="mb-4">
            <div className="flex justify-between items-center mb-1">
                <label className="text-secondary text-xs font-medium uppercase tracking-wider flex items-center gap-1">
                    {label}
                    <Info size={12} className="text-slate-600" />
                </label>
                <div className="flex items-center bg-slate-800 rounded px-2 py-1 border border-slate-700">
                    <input
                        type="number"
                        value={value}
                        onChange={(e) => setValue(Number(e.target.value))}
                        className="w-12 bg-transparent text-right text-sm font-bold text-text focus:outline-none"
                    />
                    <span className="text-xs text-slate-500 ml-1">{unit}</span>
                </div>
            </div>
            <input
                type="range"
                min={min}
                max={max}
                step={step}
                value={value}
                onChange={(e) => setValue(Number(e.target.value))}
                className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-primary hover:accent-primary-hover transition-all"
            />
            <div className="flex justify-between text-[10px] text-slate-600 mt-1">
                <span>{min}</span>
                <span className="text-primary/70">{note}</span>
                <span>{max}</span>
            </div>
        </div>
    );

    return (
        <div className="flex flex-col h-full overflow-hidden relative">
            {/* Header: Title & Actions */}
            <div className="flex justify-between items-center mb-6">
                <div>
                    <h2 className="text-xl font-bold text-text">Valuation Modeler</h2>
                    <p className="text-xs text-secondary">5-Year Discounted Cash Flow (DCF)</p>
                </div>
                <div className="flex gap-2">
                    <button
                        onClick={() => setShowProjectionsPanel(true)}
                        className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800/80 text-primary hover:bg-slate-800 border border-slate-700/50 transition-all text-xs font-medium"
                    >
                        <FolderOpen size={14} />
                        My Projections
                        {savedCount > 0 && (
                            <span className="bg-primary text-slate-900 text-[10px] font-bold px-1.5 rounded-full">
                                {savedCount}
                            </span>
                        )}
                    </button>
                    <button
                        onClick={resetToYahoo}
                        className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800/50 text-slate-400 hover:text-white hover:bg-slate-800 border border-slate-700/50 transition-all text-xs font-medium"
                    >
                        <RotateCcw size={14} />
                        Reset
                    </button>
                    <button
                        onClick={handleSaveOpen}
                        className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-primary/10 text-primary hover:bg-primary/20 border border-primary/20 transition-all text-xs font-medium"
                    >
                        <Save size={14} />
                        Save
                    </button>
                </div>
            </div>

            {/* Hero Section: Target Price */}
            <div className="flex flex-col items-center justify-center mb-6 py-4 bg-gradient-to-b from-slate-900/50 to-transparent rounded-2xl border border-slate-800/50">
                <div className="text-sm font-medium text-secondary mb-1 uppercase tracking-widest">Target Price ({timeHorizon}yr)</div>
                <div className="text-6xl font-black text-text tracking-tight mb-2">
                    ${Math.round(targetPrice)}
                </div>
                <div className={`flex items-center gap-2 text-lg font-bold px-3 py-1 rounded-full ${upside >= 0 ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'}`}>
                    {upside >= 0 ? <TrendingUp size={20} /> : <TrendingDown size={20} />}
                    {upside > 0 ? '+' : ''}{upside.toFixed(1)}% Upside
                </div>
            </div>

            {/* Scenario Toggles */}
            <div className="flex justify-center mb-8">
                <div className="flex bg-slate-900 p-1 rounded-xl border border-slate-800">
                    {(['bear', 'base', 'bull'] as const).map((s) => (
                        <button
                            key={s}
                            onClick={() => setScenario(s)}
                            className={`px-8 py-2 rounded-lg text-sm font-bold uppercase tracking-wider transition-all ${scenario === s
                                    ? s === 'bull' ? 'bg-green-500/10 text-green-400 shadow-sm border border-green-500/20'
                                        : s === 'bear' ? 'bg-red-500/10 text-red-400 shadow-sm border border-red-500/20'
                                            : 'bg-primary/10 text-primary shadow-sm border border-primary/20'
                                    : 'text-slate-500 hover:text-slate-300'
                                }`}
                        >
                            {s}
                        </button>
                    ))}
                </div>
            </div>

            {/* Main Content Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 overflow-y-auto pr-2 pb-20">

                {/* Left Column: Inputs (Span 2) */}
                <div className="lg:col-span-2 space-y-6">
                    <section className="bg-slate-900/30 p-5 rounded-xl border border-slate-800">
                        <h3 className="text-sm font-bold text-white mb-4 flex items-center gap-2">
                            <span className="w-1 h-4 bg-primary rounded-full"></span>
                            Growth & Profitability
                        </h3>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <SliderInput
                                label="Growth Rate"
                                value={growthRate}
                                setValue={setGrowthRate}
                                min={-50}
                                max={100}
                                unit="%"
                                note={`Yahoo: ${(stockData.metrics?.revenue_growth ? stockData.metrics.revenue_growth * 100 : 0).toFixed(1)}%`}
                            />
                            <SliderInput
                                label="Net Margin"
                                value={netMargin}
                                setValue={setNetMargin}
                                min={-20}
                                max={80}
                                unit="%"
                                note={`Yahoo: ${(stockData.metrics?.profit_margin ? stockData.metrics.profit_margin * 100 : 0).toFixed(1)}%`}
                            />
                        </div>
                    </section>

                    <section className="bg-slate-900/30 p-5 rounded-xl border border-slate-800">
                        <h3 className="text-sm font-bold text-white mb-4 flex items-center gap-2">
                            <span className="w-1 h-4 bg-primary rounded-full"></span>
                            Valuation Assumptions
                        </h3>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <SliderInput
                                label="Exit P/E"
                                value={peRatio}
                                setValue={setPeRatio}
                                min={1}
                                max={100}
                                unit="x"
                                note={`Fwd: ${(stockData.metrics?.forward_pe || 0).toFixed(1)}x`}
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

                    <section className="bg-slate-900/30 p-5 rounded-xl border border-slate-800">
                        <h3 className="text-sm font-bold text-white mb-4 flex items-center gap-2">
                            <span className="w-1 h-4 bg-primary rounded-full"></span>
                            Structure & Time
                        </h3>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
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

                {/* Right Column: Analysis & Scenarios (Span 1) */}
                <div className="space-y-4">
                    <div className="bg-surface border border-slate-700/50 rounded-xl p-5 shadow-lg">
                        <h4 className="text-sm font-bold text-secondary uppercase tracking-wider mb-4 border-b border-slate-800 pb-2">
                            Scenario Matrix
                        </h4>
                        <div className="space-y-3">
                            {/* Simple static calculation for matrix visualization based on multipliers */}
                            {[
                                { mode: 'Bear', price: Math.round(targetPrice * 0.6), upside: upside - 40, color: 'text-red-400' },
                                { mode: 'Base', price: Math.round(targetPrice), upside: upside, color: 'text-primary' },
                                { mode: 'Bull', price: Math.round(targetPrice * 1.4), upside: upside + 40, color: 'text-green-400' }
                            ].map((item) => (
                                <div key={item.mode} className="flex justify-between items-center p-3 bg-slate-900/50 rounded-lg">
                                    <span className="text-sm font-bold text-secondary">{item.mode}</span>
                                    <div className="text-right">
                                        <div className={`text-lg font-bold ${item.color}`}>${item.price}</div>
                                        <div className="text-xs text-slate-500">{item.upside > 0 ? '+' : ''}{item.upside.toFixed(0)}%</div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>

                    <div className="bg-primary/5 border border-primary/10 rounded-xl p-5">
                        <h4 className="text-sm font-bold text-primary mb-2">Expert Analysis</h4>
                        <p className="text-xs text-slate-400 leading-relaxed">
                            {upside > 15
                                ? "Current valuation suggests a strong buying opportunity relative to base case assumptions. Ensure growth targets (CAGR) are realistic given sector headwinds."
                                : upside < -10
                                    ? "Stock appears overvalued vs. model assumptions. Wait for a better entry point or revise growth expectations upward if competitive moat justifies premium."
                                    : "Valuation is fair. Returns likely to track earnings growth. suitable for hold/accumulate strategies."
                            }
                        </p>
                    </div>
                </div>
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
