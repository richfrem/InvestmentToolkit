import { useState, useEffect } from 'react';
import { Save, RotateCcw, FolderOpen, TrendingUp, TrendingDown, Info, X } from 'lucide-react';
import type { StockData } from '../services/api';
import { ProjectionsPanel } from './ProjectionsPanel';
import { storage } from '../services/storage';
import { HelpTrigger } from './HelpModal';

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

    // Data preferences
    const [growthBasis, setGrowthBasis] = useState<'current' | 'next'>('next');
    const [marginBasis, setMarginBasis] = useState<'ttm' | 'quarterly'>('quarterly');

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

        // --- Growth Logic ---
        let baseGrowth = 15;
        const est = stockData.growth_estimates?.stockTrend;

        if (est) {
            // Default to Next Year (+1y) if user selected 'next', else Current (0y)
            const val = growthBasis === 'next' ? (est['+1y'] || est['0y']) : (est['0y'] || est['+1y']);
            baseGrowth = val ? val * 100 : 15;
        } else {
            // Fallback to historical
            const raw = stockData.analyst_estimates?.revenue_growth ?? stockData.metrics?.revenue_growth ?? 0.15;
            baseGrowth = Math.abs(raw) > 1 ? raw : raw * 100;
        }

        // --- Margin Logic ---
        let baseMargin = 20;
        if (marginBasis === 'quarterly' && stockData.quarterly_margin) {
            baseMargin = stockData.quarterly_margin;
        } else {
            const raw = stockData.analyst_estimates?.profit_margin ?? stockData.metrics?.profit_margin ?? 0.20;
            baseMargin = Math.abs(raw) > 1 ? raw : raw * 100;
        }

        const basePe = stockData.analyst_estimates?.forward_pe || stockData.metrics?.forward_pe || stockData.metrics?.pe_ratio || 25;

        setGrowthRate(Math.round(baseGrowth * multiplier));
        setNetMargin(Math.round(baseMargin * multiplier));
        setPeRatio(Math.round(basePe * multiplier));
        setDiscountRate(scenario === 'bull' ? 8 : scenario === 'bear' ? 12 : 10);
        setShareChange(-2);
        setTimeHorizon(5);
    };

    // --- Calculations ---

    const calculatePrice = (g: number, pe: number) => {
        // 1. Future Revenue (Total)
        const currentRevenue = stockData.metrics.revenue || 0;
        const futureRevenue = currentRevenue * Math.pow(1 + g / 100, timeHorizon);

        // 2. Future Net Income
        const futureNetIncome = futureRevenue * (netMargin / 100);

        // 3. Future Market Cap (Valuation)
        const futureMarketCap = futureNetIncome * pe;

        // 4. Future Share Count (Buybacks/Dilution)
        const currentShares = stockData.metrics.shares_outstanding || 1; // Avoid div/0
        const futureShares = currentShares * Math.pow(1 + shareChange / 100, timeHorizon);

        // 5. Future Price per Share
        const futurePrice = futureShares > 0 ? futureMarketCap / futureShares : 0;

        // 6. Discount to Present Value
        const presentValue = futurePrice / Math.pow(1 + discountRate / 100, timeHorizon);

        return presentValue;
    };

    const targetPrice = calculatePrice(growthRate, peRatio);
    const upside = stockData.price > 0 ? ((targetPrice - stockData.price) / stockData.price) * 100 : 0;

    // --- Actions ---

    const handleSyncToConsensus = () => {
        resetToYahoo(); // Re-use preference logic
    };

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
                terminalGrowth: 3
            }
        });

        setSavedCount(prev => prev + 1);
        setShowSaveModal(false);
    };

    const handleLoad = (scenarios: any) => {
        setGrowthRate(scenarios.growthRate);
        setNetMargin(scenarios.netMargin);
        setPeRatio(scenarios.exitPE);
        setDiscountRate(scenarios.discountRate);
        setShareChange(scenarios.shareChange);
        setTimeHorizon(scenarios.timeHorizon);
        setShowProjectionsPanel(false);
    };

    // --- Components ---

    const SliderInput = ({ label, value, setValue, min, max, unit = '', step = 1, note = '', helpTopic = '', warningThreshold = null }: any) => {
        const isWarning = warningThreshold !== null && value < warningThreshold;

        return (
            <div className="mb-2">
                <div className="flex justify-between items-center mb-1">
                    <div className="flex items-center gap-1">
                        <label className={`text-[10px] font-medium uppercase tracking-wider flex items-center gap-1 ${isWarning ? 'text-red-400' : 'text-secondary'}`}>
                            {label}
                        </label>
                        {helpTopic && (
                            <HelpTrigger topicId={helpTopic} className="opacity-50 hover:opacity-100 transition-opacity" size={12} />
                        )}
                        {isWarning && (
                            <span className="flex items-center text-[9px] text-red-500 font-bold animate-pulse ml-1" title="Below Risk-Free Rate (10y Treasury ~4%)">
                                <Info size={10} className="text-red-500" />
                            </span>
                        )}
                    </div>
                    <div className={`flex items-center rounded px-1.5 py-0.5 border ${isWarning ? 'bg-red-500/10 border-red-500/50' : 'bg-slate-800 border-slate-700'}`}>
                        <input
                            type="number"
                            value={value}
                            onChange={(e) => setValue(Number(e.target.value))}
                            className={`w-10 bg-transparent text-right text-xs font-bold focus:outline-none ${isWarning ? 'text-red-400' : 'text-text'}`}
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
                    className={`w-full h-1 rounded-lg appearance-none cursor-pointer transition-all ${isWarning
                        ? 'bg-red-900/50 accent-red-500 hover:accent-red-400'
                        : 'bg-slate-800 accent-primary hover:accent-primary-hover'
                        }`}
                />
                <div className="flex justify-between text-[8px] text-slate-600 mt-0.5">
                    <span>{min}</span>
                    <span className="text-primary/70">{note}</span>
                    <span>{max}</span>
                </div>
            </div>
        );
    };

    const SensitivityMatrix = () => {
        // Dynamic Ranges centered on current inputs
        // Round to nearest 5 to keep matrix clean, min 5
        const currentPe = Math.max(5, Math.round(peRatio / 5) * 5);
        const currentGrowth = Math.round(growthRate / 5) * 5;

        // Generate ranges centered on current values
        const peRange = [
            currentPe - 15,
            currentPe - 10,
            currentPe - 5,
            currentPe,
            currentPe + 5,
            currentPe + 10,
            currentPe + 15
        ].filter(p => p > 0);

        const growthRange = [
            currentGrowth - 15,
            currentGrowth - 10,
            currentGrowth - 5,
            currentGrowth,
            currentGrowth + 5,
            currentGrowth + 10,
            currentGrowth + 15
        ];

        return (
            <div className="bg-slate-900/20 p-3 rounded-xl border border-slate-800 overflow-x-auto h-full flex flex-col">
                <h3 className="text-xs font-bold text-white mb-2 flex items-center gap-2">
                    <span className="w-1 h-3 bg-purple-500 rounded-full"></span>
                    Sensitivity Matrix
                </h3>
                <div className="flex-1 overflow-auto">
                    <table className="w-full text-[9px] border-collapse min-w-[300px]">
                        <thead>
                            <tr>
                                <th className="p-1 text-slate-500 font-medium text-left border-b border-slate-800">G \ PE</th>
                                {peRange.map(pe => (
                                    <th key={pe} className={`p-1 border-b border-slate-800 ${pe === currentPe ? 'text-primary font-bold' : 'text-slate-500'}`}>
                                        {pe}x
                                    </th>
                                ))}
                            </tr>
                        </thead>
                        <tbody>
                            {growthRange.map(g => (
                                <tr key={g} className="hover:bg-slate-800/30 transition-colors">
                                    <td className={`p-1 font-bold border-r border-slate-800/50 ${g === currentGrowth ? 'text-primary' : 'text-slate-500'}`}>
                                        {g}%
                                    </td>
                                    {peRange.map(pe => {
                                        const price = calculatePrice(g, pe);
                                        const mxUpside = stockData.price > 0 ? ((price - stockData.price) / stockData.price) * 100 : 0;

                                        // Color logic
                                        let colorClass = 'text-slate-600';
                                        if (mxUpside > 50) colorClass = 'bg-green-500/20 text-green-400 font-bold';
                                        else if (mxUpside > 20) colorClass = 'bg-green-500/10 text-green-500';
                                        else if (mxUpside > 0) colorClass = 'text-green-600';
                                        else if (mxUpside > -20) colorClass = 'text-red-400';
                                        else colorClass = 'bg-red-500/10 text-red-500 font-bold';

                                        // Highlight center cell area
                                        if (g === currentGrowth && pe === currentPe) {
                                            colorClass += ' ring-1 ring-primary relative z-10';
                                        }

                                        return (
                                            <td key={pe} className={`p-1 text-right rounded-sm ${colorClass}`}>
                                                ${Math.round(price)}
                                            </td>
                                        );
                                    })}
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        );
    };

    return (
        <div className="flex flex-col h-full overflow-hidden relative p-1">
            {/* Header: Title & Actions */}
            <div className="flex justify-between items-center mb-1 flex-none">
                <div>
                    <h2 className="text-lg font-bold text-text">{stockData.symbol} Valuation Modeler</h2>
                    <p className="text-[10px] text-secondary">5-Year Discounted Cash Flow (DCF)</p>
                </div>
                <div className="flex gap-2">
                    <button
                        onClick={handleSyncToConsensus}
                        className="flex items-center gap-2 px-2 py-1 rounded-lg bg-blue-500/10 text-blue-400 hover:bg-blue-500/20 border border-blue-500/20 transition-all text-[10px] font-medium"
                        title="Snap inputs to Analyst Consensus"
                    >
                        <TrendingUp size={12} />
                        Sync Consensus
                    </button>
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

            {/* Top Row: Hero & Matrix */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-3 mb-2 flex-none min-h-32">
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

                    <div className="text-[10px] font-medium text-secondary mb-0.5 uppercase tracking-widest mt-2">Target Price ({timeHorizon}yr)</div>
                    <div className="text-4xl font-black text-text tracking-tight mb-0.5">
                        ${Math.round(targetPrice)}
                    </div>
                    <div className={`flex items-center gap-1 text-xs font-bold px-2 py-0.5 rounded-full ${upside >= 0 ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'}`}>
                        {upside >= 0 ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
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
                        {/* Growth Toggle */}
                        <div className="flex gap-1 mb-1">
                            <button
                                onClick={() => { setGrowthBasis('current'); resetToYahoo(); }}
                                className={`flex-1 py-0.5 text-[9px] rounded border transition-colors ${growthBasis === 'current' ? 'bg-primary/20 text-primary border-primary/30' : 'bg-slate-800 text-slate-500 border-slate-700 hover:text-slate-300'}`}
                            >
                                Cur Yr: {stockData.growth_estimates?.stockTrend['0y'] ? (stockData.growth_estimates.stockTrend['0y'] * 100).toFixed(1) + '%' : 'N/A'}
                            </button>
                            <button
                                onClick={() => { setGrowthBasis('next'); resetToYahoo(); }}
                                className={`flex-1 py-0.5 text-[9px] rounded border transition-colors ${growthBasis === 'next' ? 'bg-primary/20 text-primary border-primary/30' : 'bg-slate-800 text-slate-500 border-slate-700 hover:text-slate-300'}`}
                            >
                                Next Yr: {stockData.growth_estimates?.stockTrend['+1y'] ? (stockData.growth_estimates.stockTrend['+1y'] * 100).toFixed(1) + '%' : 'N/A'}
                            </button>
                        </div>

                        <SliderInput
                            label="Growth Rate"
                            value={growthRate}
                            setValue={setGrowthRate}
                            min={-50}
                            max={100}
                            unit="%"
                            helpTopic="growthRate"
                            note=""
                        />

                        {/* Margin Toggle */}
                        <div className="flex gap-1 mb-1 mt-4">
                            <button
                                onClick={() => { setMarginBasis('ttm'); resetToYahoo(); }}
                                className={`flex-1 py-0.5 text-[9px] rounded border transition-colors ${marginBasis === 'ttm' ? 'bg-primary/20 text-primary border-primary/30' : 'bg-slate-800 text-slate-500 border-slate-700 hover:text-slate-300'}`}
                            >
                                TTM: {(() => {
                                    const val = stockData.metrics?.profit_margin ?? 0;
                                    return (Math.abs(val) > 1 ? val : val * 100).toFixed(1);
                                })()}%
                            </button>
                            <button
                                onClick={() => { setMarginBasis('quarterly'); resetToYahoo(); }}
                                className={`flex-1 py-0.5 text-[9px] rounded border transition-colors ${marginBasis === 'quarterly' ? 'bg-primary/20 text-primary border-primary/30' : 'bg-slate-800 text-slate-500 border-slate-700 hover:text-slate-300'}`}
                            >
                                Last Q: {stockData.quarterly_margin ? stockData.quarterly_margin.toFixed(1) + '%' : 'N/A'}
                            </button>
                        </div>

                        <SliderInput
                            label="Net Margin"
                            value={netMargin}
                            setValue={setNetMargin}
                            min={-20}
                            max={80}
                            unit="%"
                            helpTopic="netMargin"
                            note=""
                        />
                    </div>
                </section>

                <section className="bg-slate-900/20 p-4 rounded-xl border border-slate-800">
                    <h3 className="text-xs font-bold text-white mb-3 flex items-center gap-2">
                        <span className="w-1 h-3 bg-primary rounded-full"></span>
                        Valuation & Structure
                    </h3>
                    <div className="space-y-4">
                        <SliderInput
                            label="Exit P/E"
                            value={peRatio}
                            setValue={setPeRatio}
                            min={1}
                            max={100}
                            unit="x"
                            helpTopic="exitPE"
                            note={`Fwd: ${(stockData.analyst_estimates?.forward_pe || stockData.metrics?.forward_pe || 0).toFixed(1)}x`}
                        />
                        <SliderInput
                            label="Discount Rate"
                            value={discountRate}
                            setValue={setDiscountRate}
                            min={0}
                            max={20}
                            unit="%"
                            helpTopic="discountRate"
                            warningThreshold={4}
                            note="Typ: 8-12%"
                        />
                        <SliderInput
                            label="Share Change"
                            value={shareChange}
                            setValue={setShareChange}
                            min={-20}
                            max={20}
                            unit="%"
                            helpTopic="shareChange"
                            note="( - ) Buyback"
                        />
                        <SliderInput
                            label="Time Horizon"
                            value={timeHorizon}
                            setValue={setTimeHorizon}
                            min={1}
                            max={10}
                            unit="yr"
                            helpTopic="timeHorizon"
                            note="Def: 5yr"
                        />
                    </div>
                </section>

                {/* Sensitivity Matrix (Col 3) */}
                <SensitivityMatrix />
            </div>



            {/* Red Team / Sanity Check Section */}
            {(discountRate < 4 || peRatio > 80 || growthRate > 50 || netMargin > 50) && (
                <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 mb-4 animate-in fade-in slide-in-from-bottom-2">
                    <h4 className="text-[10px] font-bold text-red-400 uppercase tracking-wider mb-2 flex items-center gap-2">
                        <Info size={12} />
                        Sanity Checks & Risk Flags
                    </h4>
                    <ul className="space-y-1">
                        {discountRate < 4 && (
                            <li className="text-[10px] text-red-300 flex gap-2">
                                <span className="font-bold">• Discount Rate ({discountRate}%):</span>
                                Below 10y Treasury (~4%). Implies zero risk premium. Unrealistic for equity.
                            </li>
                        )}
                        {peRatio > 80 && (
                            <li className="text-[10px] text-red-300 flex gap-2">
                                <span className="font-bold">• Exit P/E ({peRatio}x):</span>
                                Extremely high multiple. Assumes perpetual hyper-growth. Bubbled territory.
                            </li>
                        )}
                        {growthRate > 50 && (
                            <li className="text-[10px] text-red-300 flex gap-2">
                                <span className="font-bold">• Growth Rate ({growthRate}%):</span>
                                Hard to sustain {'>'}50% CAGR for {timeHorizon} years. Law of large numbers risk.
                            </li>
                        )}
                        {netMargin > 50 && (
                            <li className="text-[10px] text-red-300 flex gap-2">
                                <span className="font-bold">• Net Margin ({netMargin}%):</span>
                                Extremely high profitability. Attracts competition / Regulatory scrutiny.
                            </li>
                        )}
                    </ul>
                </div>
            )}

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
