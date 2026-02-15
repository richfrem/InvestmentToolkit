import { useState, useEffect } from 'react';
import { Save, RotateCcw, FolderOpen, TrendingUp, TrendingDown, Info, X, AlertTriangle } from 'lucide-react';
import type { StockData } from '../services/api';
import { ProjectionsPanel } from './ProjectionsPanel';
import { storage } from '../services/storage';
import { HelpTrigger } from './HelpModal';
import { runAIAnalysis, type ValuationResult, type Projection, type Scenario, fetchProjections } from '../services/api';
import { Sparkles, BrainCircuit, Loader2, FileText } from 'lucide-react';
import { AIAnalysisModal } from './AIAnalysisModal';
import { PresetSelectorModal } from './PresetSelectorModal';
import { saveUserPreset } from '../services/presets';

interface ValuationModelerProps {
    stockData: StockData;
}

export default function ValuationModeler({ stockData }: ValuationModelerProps) {
    // --- State ---
    const [activeScenario, setActiveScenario] = useState<'bear' | 'base' | 'bull'>('base');
    const [showProjectionsPanel, setShowProjectionsPanel] = useState(false);
    const [savedCount, setSavedCount] = useState(0);

    // AI State
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [aiResult, setAiResult] = useState<ValuationResult | null>(null);
    const [aiError, setAiError] = useState<string | null>(null);
    const [activeCoachMetric, setActiveCoachMetric] = useState<string | null>(null);

    // Save Modal State
    const [showSaveModal, setShowSaveModal] = useState(false);
    const [showAIModal, setShowAIModal] = useState(false);
    const [saveName, setSaveName] = useState('');
    const [showPresetModal, setShowPresetModal] = useState(false);

    // Global Settings
    const [discountRate, setDiscountRate] = useState(10);
    const [timeHorizon, setTimeHorizon] = useState(5);

    // Scenario Data (Bear, Base, Bull)
    const [scenarios, setScenarios] = useState<{
        bear: Scenario & { weight: number };
        base: Scenario & { weight: number };
        bull: Scenario & { weight: number };
    }>({
        bear: { growthRate: 5, netMargin: 10, exitPE: 15, qualityMultiplier: 0.9, shareChange: 0, weight: 0.2 },
        base: { growthRate: 15, netMargin: 20, exitPE: 25, qualityMultiplier: 1.0, shareChange: -1, weight: 0.5 },
        bull: { growthRate: 25, netMargin: 25, exitPE: 35, qualityMultiplier: 1.2, shareChange: -2, weight: 0.3 }
    });

    // Helpers to get/set current scenario values
    const current = scenarios[activeScenario];
    const updateCurrent = (updates: Partial<Scenario & { weight: number }>) => {
        setScenarios(prev => ({
            ...prev,
            [activeScenario]: { ...prev[activeScenario], ...updates }
        }));
    };

    // Derived State for UI Compatibility
    const growthRate = current.growthRate;
    const netMargin = current.netMargin;
    const peRatio = current.exitPE;
    const qualityMultiplier = current.qualityMultiplier;
    const shareChange = current.shareChange;

    const totalWeight = scenarios.bear.weight + scenarios.base.weight + scenarios.bull.weight;
    const currentWeight = Math.round(current.weight * 100);

    const setGrowthRate = (v: number) => updateCurrent({ growthRate: v });
    const setNetMargin = (v: number) => updateCurrent({ netMargin: v });
    const setPeRatio = (v: number) => updateCurrent({ exitPE: v });
    const setQualityMultiplier = (v: number) => updateCurrent({ qualityMultiplier: v });
    const setShareChange = (v: number) => updateCurrent({ shareChange: v });
    const setWeight = (v: number) => updateCurrent({ weight: v / 100 });

    // Data preferences

    // Data preferences
    const [growthBasis, setGrowthBasis] = useState<'current' | 'next'>('next');
    const [marginBasis, setMarginBasis] = useState<'ttm' | 'quarterly'>('quarterly');

    // Load initial saved count
    useEffect(() => {
        const init = async () => {
            const saved = await storage.syncProjections(stockData.symbol);
            setSavedCount(saved.length);
        };
        init();
    }, [stockData.symbol]);

    // Initialize with Yahoo Finance data/defaults when stockData changes
    useEffect(() => {
        resetToYahoo();
    }, [stockData]); // Only re-run if stockData changes, not on scenario switch (state persists)

    const resetToYahoo = () => {
        // --- Base Logic ---
        let baseGrowth = 15;
        const est = stockData.growth_estimates?.stockTrend;
        if (est) {
            const val = growthBasis === 'next' ? (est['+1y'] || est['0y']) : (est['0y'] || est['+1y']);
            baseGrowth = val ? (Math.abs(val) > 1 ? val : val * 100) : 15;
        } else {
            const raw = stockData.analyst_estimates?.revenue_growth ?? stockData.metrics?.revenue_growth ?? 0.15;
            baseGrowth = Math.abs(raw) > 1 ? raw : raw * 100;
        }

        let baseMargin = 20;
        if (marginBasis === 'quarterly' && stockData.quarterly_margin) {
            baseMargin = stockData.quarterly_margin;
        } else {
            const raw = stockData.analyst_estimates?.profit_margin ?? stockData.metrics?.profit_margin ?? 0.20;
            baseMargin = Math.abs(raw) > 1 ? raw : raw * 100;
        }

        const basePe = stockData.analyst_estimates?.forward_pe || stockData.metrics?.forward_pe || stockData.metrics?.pe_ratio || 25;

        setDiscountRate(10);
        setTimeHorizon(5);

        setScenarios({
            bear: {
                growthRate: Math.round(baseGrowth * 0.5),
                netMargin: Math.round(baseMargin * 0.8),
                exitPE: Math.round(basePe * 0.7),
                qualityMultiplier: 0.9,
                shareChange: 0,
                weight: 0.2
            },
            base: {
                growthRate: Math.round(baseGrowth),
                netMargin: Math.round(baseMargin),
                exitPE: Math.round(basePe),
                qualityMultiplier: 1.0,
                shareChange: -1,
                weight: 0.5
            },
            bull: {
                growthRate: Math.round(baseGrowth * 1.3),
                netMargin: Math.round(baseMargin * 1.2),
                exitPE: Math.round(basePe * 1.3),
                qualityMultiplier: 1.2,
                shareChange: -2,
                weight: 0.3
            }
        });
    };

    // --- Calculations ---

    // Helper to calculate price for a specific scenario object
    const calculateScenarioPrice = (s: Scenario) => {
        // 1. Future Revenue
        const currentRevenue = stockData.metrics.revenue || 0;
        const futureRevenue = currentRevenue * Math.pow(1 + s.growthRate / 100, timeHorizon);

        // 2. Future Net Income
        const futureNetIncome = futureRevenue * (s.netMargin / 100);

        // 3. Future Market Cap
        const futureMarketCap = futureNetIncome * s.exitPE * s.qualityMultiplier;

        // 4. Future Share Count
        const currentShares = stockData.metrics.shares_outstanding || 1;
        const futureShares = currentShares * Math.pow(1 + s.shareChange / 100, timeHorizon);

        // 5. Future Price
        const futurePrice = futureShares > 0 ? futureMarketCap / futureShares : 0;

        // 6. Discount to PV
        return futurePrice / Math.pow(1 + discountRate / 100, timeHorizon);
    };

    // Used by Sensitivity Matrix (uses current scenario context but overrides g/pe)
    const calculatePrice = (g: number, pe: number) => {
        const tempScenario: Scenario = {
            ...current,
            growthRate: g,
            exitPE: pe,
        };
        return calculateScenarioPrice(tempScenario);
    };

    // Derived Prices
    const bearPrice = calculateScenarioPrice(scenarios.bear);
    const basePrice = calculateScenarioPrice(scenarios.base);
    const bullPrice = calculateScenarioPrice(scenarios.bull);

    // Weighted Average
    const weightedPrice = (bearPrice * scenarios.bear.weight) + (basePrice * scenarios.base.weight) + (bullPrice * scenarios.bull.weight);

    // Target Price for Hero (Interactive)
    const targetPrice = weightedPrice;
    const upside = stockData.price > 0 ? ((targetPrice - stockData.price) / stockData.price) * 100 : 0;

    // --- Actions ---

    const handleSyncToConsensus = () => {
        resetToYahoo(); // Re-use preference logic
    };

    const handleAIAnalysis = async (metric?: string) => {
        setIsAnalyzing(true);
        setAiError(null);
        setActiveCoachMetric(metric || null);

        let userMessage = "";
        if (metric === "Growth Rate") {
            userMessage = "Focus on recommending a realistic 5-year revenue growth rate based on historical trends and industry TAM.";
        } else if (metric === "Net Margin") {
            userMessage = "Focus on recommending a sustainable 5-year average net profit margin based on operational leverage and peer benchmarks.";
        } else if (metric === "Exit PE") {
            userMessage = "Focus on recommending a realistic Terminal Exit P/E multiple based on historical sector averages and growth profile.";
        }

        try {
            const result = await runAIAnalysis(stockData.symbol, userMessage);
            setAiResult(result);
            if (result.growth_assumption && metric === "Growth Rate") {
                setGrowthRate(Math.round(result.growth_assumption * 100));
            }
        } catch (err: any) {
            setAiError(err.message || 'Failed to get AI Analysis');
        } finally {
            setIsAnalyzing(false);
        }
    };

    const handleApplyAISuggestions = () => {
        if (!aiResult) return;
        if (aiResult.suggested_growth) setGrowthRate(Math.round(aiResult.suggested_growth * 100));
        if (aiResult.suggested_margin) setNetMargin(Math.round(aiResult.suggested_margin * 100));
        if (aiResult.exit_pe) setPeRatio(aiResult.exit_pe);
        if (aiResult.quality_multiplier) setQualityMultiplier(aiResult.quality_multiplier);
    };

    const handleSaveOpen = () => {
        setSaveName(`Projection ${new Date().toLocaleDateString()}`);
        setShowSaveModal(true);
    };

    const handleSaveConfirm = () => {
        if (!saveName.trim()) return;

        // Current snapshot
        const snapshot = {
            price: stockData.price,
            currency: stockData.currency,
            shares: stockData.metrics.shares_outstanding || 0,
            revenue: stockData.metrics.revenue || 0,
            lastActualPS: stockData.metrics.market_cap / (stockData.metrics.revenue || 1),
            analystGrowthEstimate: stockData.analyst_estimates?.revenue_growth,
            analystMarginEstimate: stockData.analyst_estimates?.profit_margin,
            fiscalPeriod: "TTM" // Simplified
        };

        const projection: Projection = {
            id: Date.now().toString(), // Helper will be replaced by backend ID usually, but local first
            ticker: stockData.symbol,
            schemaVersion: '1.1',
            version: 1,
            savedAt: new Date().toISOString(),
            updatedAt: new Date().toISOString(),
            name: saveName,
            snapshot,
            dataPreferences: { growthBasis, marginBasis },
            scenarios: scenarios, // Save all 3
            globalSettings: { discountRate, timeHorizon }
        };

        storage.saveProjection(projection)
            .then(() => {
                setSavedCount(prev => prev + 1);
                setShowSaveModal(false);
            })
            .catch(err => alert("Failed to save: " + err.message));
    };

    const handleLoad = (loadedProjection: any) => {
        // We expect a full Projection object here, but older callers might pass just scenarios.
        // Actually storage.syncProjections returns Projection[]. 
        // ProjectionsPanel onLoad passes `p.scenarios` or `p`.
        // Let's assume it passes the WHOLE projection settings usually, 
        // but looking at ProjectionsPanel is safer.
        // For now, let's assume it passes just the scenarios object + global settings if available.

        // If it's a "Projecton" object
        if (loadedProjection.scenarios) {
            setScenarios(loadedProjection.scenarios);
            if (loadedProjection.globalSettings) {
                setDiscountRate(loadedProjection.globalSettings.discountRate);
                setTimeHorizon(loadedProjection.globalSettings.timeHorizon);
            }
            setActiveScenario('base');
        } else {
            console.warn("Legacy/Invalid load structure");
            // Try to patch
            if (loadedProjection.base) {
                setScenarios(loadedProjection);
            }
        }
        setShowProjectionsPanel(false);
    };

    const handlePresetLoad = async (preset: any) => {
        if (preset.type === 'yahoo') {
            // Load Yahoo Consensus
            resetToYahoo();
        } else if (preset.type === 'ai') {
            // Load AI Analysis
            try {
                const projections = await fetchProjections(stockData.symbol);
                const aiProjection = projections?.find(p => p.source === 'AI_AGENT');

                if (aiProjection && aiProjection.scenarios) {
                    setScenarios(aiProjection.scenarios);
                    if (aiProjection.globalSettings) {
                        setDiscountRate(aiProjection.globalSettings.discountRate);
                        setTimeHorizon(aiProjection.globalSettings.timeHorizon);
                    }
                    setActiveScenario('base');
                }
            } catch (error) {
                console.error('Failed to load AI projection:', error);
                alert('Failed to load AI Analysis');
            }
        } else if (preset.type === 'user' && preset.data) {
            // Load User Preset
            setScenarios(preset.data.scenarios);
            setDiscountRate(preset.data.globalSettings.discountRate);
            setTimeHorizon(preset.data.globalSettings.timeHorizon);
            setActiveScenario('base');
        }
        setShowPresetModal(false);
    };

    const handleSaveAsPreset = () => {
        const presetName = prompt('Name this preset:');
        if (!presetName?.trim()) return;

        saveUserPreset(
            stockData.symbol,
            presetName,
            scenarios,
            { discountRate, timeHorizon }
        );

        alert(`Saved preset: ${presetName}`);
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
                            step={step}
                            onChange={(e) => setValue(Number(e.target.value))}
                            className={`w-14 bg-transparent text-right text-xs font-bold focus:outline-none ${isWarning ? 'text-red-400' : 'text-text'}`}
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
                        onClick={() => setShowAIModal(true)}
                        className="flex items-center gap-2 px-2 py-1 rounded-lg bg-indigo-500/10 text-indigo-400 hover:bg-indigo-500/20 border border-indigo-500/20 transition-all text-[10px] font-medium"
                        title="View Report from Autonomous AI Agent"
                    >
                        <FileText size={12} />
                        View AI Report
                    </button>
                    <button
                        onClick={() => handleAIAnalysis()} // Call without specific metric for general analysis
                        disabled={isAnalyzing}
                        className={`flex items-center gap-2 px-2 py-1 rounded-lg transition-all text-[10px] font-medium border ${isAnalyzing
                            ? 'bg-purple-500/20 text-purple-300 border-purple-500/30 cursor-not-allowed'
                            : 'bg-indigo-500/10 text-indigo-400 hover:bg-indigo-500/20 border-indigo-500/20'
                            }`}
                        title="Get AI feedback from the 'Valuation Expert'"
                    >
                        {isAnalyzing ? <Loader2 size={12} className="animate-spin" /> : <Sparkles size={12} />}
                        AI Analyst
                    </button>
                    <button
                        onClick={() => setShowPresetModal(true)}
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
                        onClick={handleSaveAsPreset}
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
                                onClick={() => setActiveScenario(s)}
                                className={`px-3 py-1 rounded text-[10px] font-bold uppercase tracking-wider transition-all ${activeScenario === s
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

            {/* AI Thesis Section (Expanded when result exists) */}
            {(aiResult || isAnalyzing || aiError) && (
                <div className="mb-4 flex-none animate-in fade-in slide-in-from-top-4 duration-500">
                    <div className="bg-gradient-to-br from-indigo-900/40 via-slate-900/60 to-purple-900/30 border border-indigo-500/30 rounded-xl p-4 shadow-xl overflow-hidden relative group">
                        {/* Glow effect */}
                        <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-indigo-500 via-purple-500 to-indigo-500 opacity-50"></div>
                        <div className="absolute -right-10 -top-10 w-32 h-32 bg-indigo-500/10 blur-3xl rounded-full group-hover:bg-indigo-500/20 transition-all duration-1000"></div>

                        <div className="flex justify-between items-start mb-3 relative z-10">
                            <div className="flex items-center gap-2">
                                <div className="p-1.5 bg-indigo-500/20 rounded-lg text-indigo-400">
                                    <BrainCircuit size={18} />
                                </div>
                                <div>
                                    <h3 className="text-sm font-bold text-white flex items-center gap-2">
                                        {activeCoachMetric ? `AI Coach: ${activeCoachMetric}` : 'AI Expert Thesis'}
                                        {aiResult?.action && (
                                            <span className={`text-[10px] px-1.5 py-0.5 rounded-full uppercase tracking-tighter border ${aiResult.action === 'BUY' ? 'bg-green-500/20 text-green-400 border-green-500/30' :
                                                aiResult.action === 'SELL' ? 'bg-red-500/20 text-red-400 border-red-500/30' :
                                                    'bg-slate-500/20 text-slate-400 border-slate-500/30'
                                                }`}>
                                                {aiResult.action}
                                            </span>
                                        )}
                                    </h3>
                                    <p className="text-[10px] text-indigo-300 font-medium tracking-wide uppercase">{aiResult?.model_name || 'AI ANALYST'} ANALYSIS</p>
                                </div>
                            </div>
                            <button
                                onClick={() => { setAiResult(null); setAiError(null); setActiveCoachMetric(null); }}
                                className="text-slate-500 hover:text-white transition-colors"
                            >
                                <X size={16} />
                            </button>
                        </div>

                        {isAnalyzing ? (
                            <div className="py-6 flex flex-col items-center justify-center gap-3">
                                <Loader2 size={24} className="text-indigo-400 animate-spin" />
                                <div className="flex flex-col items-center">
                                    <p className="text-sm text-indigo-200 animate-pulse">Analyzing financials & growth vectors...</p>
                                    <p className="text-[10px] text-slate-500">Processing "Twin Revolutions" Framework</p>
                                </div>
                            </div>
                        ) : aiError ? (
                            <div className="py-4 text-center">
                                <div className="text-red-400 font-bold mb-1 flex items-center justify-center gap-2">
                                    <AlertTriangle size={16} /> Analysis Failed
                                </div>
                                <p className="text-xs text-slate-400">{aiError}</p>
                            </div>
                        ) : aiResult ? (
                            <div className="relative z-10 grid grid-cols-1 md:grid-cols-4 gap-4">
                                <div className="md:col-span-3">
                                    <p className="text-xs text-slate-300 leading-relaxed font-medium italic">
                                        "{aiResult.rationale}"
                                    </p>
                                </div>
                                <div className="bg-black/20 rounded-lg p-3 border border-white/5 flex flex-col items-center justify-center text-center">
                                    <div className="text-[10px] text-slate-500 uppercase font-bold mb-1">AI Fair Value</div>
                                    <div className="text-2xl font-black text-indigo-400 leading-none">${aiResult.fair_value}</div>
                                    <div className="text-[9px] text-indigo-300 mt-1">Rec. Growth: {Math.round((aiResult.suggested_growth || aiResult.growth_assumption) * 100)}%</div>
                                    <button
                                        onClick={handleApplyAISuggestions}
                                        className="mt-2 w-full py-1 bg-indigo-500/20 hover:bg-indigo-500/40 text-indigo-200 text-[9px] font-bold rounded border border-indigo-500/30 transition-all uppercase tracking-tight"
                                    >
                                        Apply Suggestions
                                    </button>
                                </div>
                            </div>
                        ) : null}
                    </div>
                </div>
            )}

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
                                Cur Yr: {(() => {
                                    const val = stockData.growth_estimates?.stockTrend['0y'];
                                    if (val === undefined) return 'N/A';
                                    return (Math.abs(val) > 1 ? val : val * 100).toFixed(1) + '%';
                                })()}
                            </button>
                            <button
                                onClick={() => { setGrowthBasis('next'); resetToYahoo(); }}
                                className={`flex-1 py-0.5 text-[9px] rounded border transition-colors ${growthBasis === 'next' ? 'bg-primary/20 text-primary border-primary/30' : 'bg-slate-800 text-slate-500 border-slate-700 hover:text-slate-300'}`}
                            >
                                Next Yr: {(() => {
                                    const val = stockData.growth_estimates?.stockTrend['+1y'];
                                    if (val === undefined) return 'N/A';
                                    return (Math.abs(val) > 1 ? val : val * 100).toFixed(1) + '%';
                                })()}
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
                    <h3 className="text-xs font-bold text-white mb-3 flex items-center gap-2 justify-between">
                        <div className="flex items-center gap-2">
                            <span className="w-1 h-3 bg-primary rounded-full"></span>
                            Valuation & Structure
                        </div>
                        <div className={`text-[9px] px-1.5 py-0.5 rounded border ${Math.abs(totalWeight - 1.0) < 0.01 ? 'bg-green-500/10 text-green-400 border-green-500/20' : 'bg-red-500/10 text-red-400 border-red-500/20 animate-pulse'}`}>
                            Total Prob: {Math.round(totalWeight * 100)}%
                        </div>
                    </h3>
                    <div className="space-y-4">
                        <SliderInput
                            label="Probability"
                            value={currentWeight}
                            setValue={setWeight}
                            min={0}
                            max={100}
                            unit="%"
                            helpTopic="probabilityWeight"
                            note="Scen. Weight"
                        />
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
                            label="Quality Mult."
                            value={qualityMultiplier}
                            setValue={setQualityMultiplier}
                            min={0.5}
                            max={2.0}
                            step={0.05}
                            unit="x"
                            helpTopic="qualityMultiplier"
                            note="Typ: 1.0x"
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

            {/* AI Analysis Modal */}
            <AIAnalysisModal
                isOpen={showAIModal}
                onClose={() => setShowAIModal(false)}
                symbol={stockData.symbol}
            />

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

            {/* Preset Selector Modal */}
            {showPresetModal && (
                <PresetSelectorModal
                    symbol={stockData.symbol}
                    onLoad={handlePresetLoad}
                    onClose={() => setShowPresetModal(false)}
                />
            )}
        </div>
    );
}
