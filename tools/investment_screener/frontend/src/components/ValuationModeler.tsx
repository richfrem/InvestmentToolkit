import { useState, useEffect } from 'react';
import { Save, RotateCcw, TrendingUp, TrendingDown, Info, X, AlertTriangle } from 'lucide-react';
import type { StockData } from '../services/api';
import { ProjectionsPanel } from './ProjectionsPanel';
import { storage } from '../services/storage';
import { HelpTrigger } from './HelpModal';
import { runAIAnalysis, type ValuationResult, type Projection, type Scenario } from '../services/api';
import { Sparkles, BrainCircuit, Loader2, FolderOpen } from 'lucide-react';
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
    const [saveAsDefault, setSaveAsDefault] = useState(false);
    const [showPresetModal, setShowPresetModal] = useState(false);

    const [viewingProjection, setViewingProjection] = useState<Projection | null>(null); // State for modal viewing
    const [activeProjection, setActiveProjection] = useState<{ id: string, version: number } | null>(null); // Track loaded projection for updates

    // Global Settings
    const [discountRate, setDiscountRate] = useState(10);
    const [timeHorizon, setTimeHorizon] = useState(5);

    // Scenario Data (Bear, Base, Bull)
    const [scenarios, setScenarios] = useState<{
        bear: Scenario & { weight: number };
        base: Scenario & { weight: number };
        bull: Scenario & { weight: number };
    }>({
        bear: { growthRate: 5, netMargin: 10, exitPE: 15, qualityMultiplier: 0.9, shareChange: 0, moatScore: 1, managementScore: 1, weight: 0.2 },
        base: { growthRate: 15, netMargin: 20, exitPE: 25, qualityMultiplier: 1.0, shareChange: -1, moatScore: 2, managementScore: 2, weight: 0.5 },
        bull: { growthRate: 25, netMargin: 25, exitPE: 35, qualityMultiplier: 1.2, shareChange: -2, moatScore: 3, managementScore: 3, weight: 0.3 }
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
    const moatScore = current.moatScore ?? 0;
    const managementScore = current.managementScore ?? 0;

    const totalWeight = scenarios.bear.weight + scenarios.base.weight + scenarios.bull.weight;
    const currentWeight = Math.round(current.weight * 100);

    const setGrowthRate = (v: number) => updateCurrent({ growthRate: v });
    const setNetMargin = (v: number) => updateCurrent({ netMargin: v });
    const setPeRatio = (v: number) => updateCurrent({ exitPE: v });
    const setQualityMultiplier = (v: number) => updateCurrent({ qualityMultiplier: v });
    const setShareChange = (v: number) => updateCurrent({ shareChange: v });
    const setMoatScore = (v: number) => updateCurrent({ moatScore: v });
    const setManagementScore = (v: number) => updateCurrent({ managementScore: v });
    const setWeight = (v: number) => updateCurrent({ weight: v / 100 });

    // Data preferences

    // Data preferences
    const [growthBasis, setGrowthBasis] = useState<'current' | 'next'>('next');
    const [marginBasis, setMarginBasis] = useState<'ttm' | 'quarterly'>('quarterly');

    // Initialize: Try to load latest saved projection, otherwise default to Yahoo
    useEffect(() => {
        const init = async () => {
            // 1. Sync & Fetch saved projections
            const saved = await storage.syncProjections(stockData.symbol);
            setSavedCount(saved.length);

            // 2. Auto-load the default or most recent
            if (saved.length > 0) {
                // Priority: isDefault=true, then latest updatedAt
                const defaults = saved.filter(p => p.isDefault);
                let target;
                if (defaults.length > 0) {
                    target = defaults.sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime())[0];
                    console.log(`[AutoLoad] Loading default projection: ${target.name}`);
                } else {
                    target = saved.sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime())[0];
                    console.log(`[AutoLoad] Loading latest projection (no default set): ${target.name}`);
                }
                handleLoad(target);
            } else {
                // 3. Fallback to Yahoo defaults
                resetToYahoo();
            }
        };
        init();
    }, [stockData.symbol]); // Re-run when ticker changes

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

        // Fix for negative earners (Turnaround logic)
        // If margin is negative, default to 5% to show a recovery scenario rather than bankruptcy
        if (baseMargin < 0) {
            baseMargin = 5.0;
        }

        const basePe = stockData.analyst_estimates?.forward_pe || stockData.metrics?.forward_pe || stockData.metrics?.pe_ratio || 25;

        setDiscountRate(10);
        setTimeHorizon(5);

        setActiveProjection(null); // Clear active projection tracking for clean slate

        setScenarios({
            bear: {
                growthRate: Math.round(baseGrowth * 0.5),
                netMargin: Math.round(baseMargin * 0.8),
                exitPE: Math.round(basePe * 0.7),
                qualityMultiplier: 0.9,
                shareChange: 0,
                moatScore: 1,
                managementScore: 1,
                weight: 0.2
            },
            base: {
                growthRate: Math.round(baseGrowth),
                netMargin: Math.round(baseMargin),
                exitPE: Math.round(basePe),
                qualityMultiplier: 1.0,
                shareChange: -1,
                moatScore: 2,
                managementScore: 2,
                weight: 0.5
            },
            bull: {
                growthRate: Math.round(baseGrowth * 1.3),
                netMargin: Math.round(baseMargin * 1.2),
                exitPE: Math.round(basePe * 1.3),
                qualityMultiplier: 1.2,
                shareChange: -2,
                moatScore: 3,
                managementScore: 3,
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
        let futurePrice = futureShares > 0 ? futureMarketCap / futureShares : 0;

        // 6. Apply Moat & Management Premiums (0-5 score, each point = 5% premium)
        // This reflects "Drivers" that expand the multiple or cash flow reliability
        const moatPremium = (s.moatScore ?? 0) * 0.05;
        const mgmtPremium = (s.managementScore ?? 0) * 0.05;
        futurePrice = futurePrice * (1 + moatPremium + mgmtPremium);

        // 7. Discount to PV
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
    // Reverted to Weighted Average per user request (with explanation)
    const targetPrice = weightedPrice;

    // Active Scenario Helpers for UI (Dynamic secondary display)
    const activePrice = activeScenario === 'bull' ? bullPrice : activeScenario === 'bear' ? bearPrice : basePrice;
    // Calculate upside for active scenario
    const activeUpside = stockData.price > 0 ? ((activePrice - stockData.price) / stockData.price) * 100 : 0;

    const upside = stockData.price > 0 ? ((targetPrice - stockData.price) / stockData.price) * 100 : 0;

    // --- Actions ---



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
            id: activeProjection?.id || crypto.randomUUID(), // Use existing ID if updating
            source: 'USER',
            ticker: stockData.symbol,
            schemaVersion: '1.1',
            version: activeProjection ? activeProjection.version + 1 : 1, // Increment version if updating
            savedAt: new Date().toISOString(),
            updatedAt: new Date().toISOString(),
            name: saveName,
            isDefault: saveAsDefault,
            snapshot,
            dataPreferences: { growthBasis, marginBasis },
            scenarios: scenarios, // Save all 3
            globalSettings: { discountRate, timeHorizon },
            // Preserve AI Thesis if available
            aiThesis: aiResult ? {
                model: aiResult.model_name,
                rationale: aiResult.rationale,
                fairValue: aiResult.fair_value,
                action: (aiResult.action as any) || 'HOLD',
                analyzedAt: new Date().toISOString(),
                // If we have a report link, preserve it (though it might not be in aiResult unless we put it there)
                researchReport: (aiResult as any).researchReport
            } : undefined
        };

        storage.saveProjection(projection)
            .then(() => {
                setSavedCount(prev => prev + 1);
                // Update active projection state to match the newly saved one
                setActiveProjection({ id: projection.id, version: projection.version });
                setShowSaveModal(false);
            })
            .catch(err => alert("Failed to save: " + err.message));
    };

    const handleLoad = (loadedProjection: any) => {
        // We expect a full Projection object here, but older callers might pass just scenarios.
        // Actually storage.syncProjections returns Projection[]. 
        // ProjectionsPanel onLoad passes `p.scenarios` or `p`.

        let p = loadedProjection;
        // If it's a full projection object (has id/ticker), use it. 
        // If it's a full projection object (has id/ticker), use it. 
        if (p.id && p.ticker) {
            // CRITICAL fix: Only treat it as an "active" projection to update if it's a USER one.
            // If it's an AI or System projection, treat it as a "Template" (Load values, but don't bind ID).
            // This ensures saving creates a new USER entry instead of overwriting the AI/System one.
            if (p.source === 'USER') {
                setActiveProjection({ id: p.id, version: p.version });
            } else {
                setActiveProjection(null);
            }

            // Also take scenarios from it
            if (p.scenarios) {
                // Normalize Percentages (if saved as decimals 0.15 instead of 15)
                const normalize = (s: Scenario) => ({
                    ...s,
                    growthRate: Math.abs(s.growthRate) <= 1 && s.growthRate !== 0 ? s.growthRate * 100 : s.growthRate,
                    netMargin: Math.abs(s.netMargin) <= 1 && s.netMargin !== 0 ? s.netMargin * 100 : s.netMargin,
                    shareChange: Math.abs(s.shareChange) <= 1 && s.shareChange !== 0 ? s.shareChange * 100 : s.shareChange,
                });

                setScenarios({
                    bear: normalize(p.scenarios.bear),
                    base: normalize(p.scenarios.base),
                    bull: normalize(p.scenarios.bull)
                });
            } else if (p.base && p.bull && p.bear) {
                // Legacy support
                const normalize = (s: any) => ({
                    ...s,
                    growthRate: Math.abs(s.growthRate) <= 1 && s.growthRate !== 0 ? s.growthRate * 100 : s.growthRate,
                    netMargin: Math.abs(s.netMargin) <= 1 && s.netMargin !== 0 ? s.netMargin * 100 : s.netMargin,
                    shareChange: Math.abs(s.shareChange) <= 1 && s.shareChange !== 0 ? s.shareChange * 100 : s.shareChange,
                });
                setScenarios({
                    bear: normalize(p.bear),
                    base: normalize(p.base),
                    bull: normalize(p.bull)
                });
            }
        } else {
            // Legacy or partial load - treat as new
            setActiveProjection(null);
            // Try to patch from legacy structure
            if (p.scenarios) {
                // Normalize Percentages
                const normalize = (s: Scenario) => ({
                    ...s,
                    growthRate: Math.abs(s.growthRate) <= 1 && s.growthRate !== 0 ? s.growthRate * 100 : s.growthRate,
                    netMargin: Math.abs(s.netMargin) <= 1 && s.netMargin !== 0 ? s.netMargin * 100 : s.netMargin,
                    shareChange: Math.abs(s.shareChange) <= 1 && s.shareChange !== 0 ? s.shareChange * 100 : s.shareChange,
                });
                setScenarios({
                    bear: normalize(p.scenarios.bear),
                    base: normalize(p.scenarios.base),
                    bull: normalize(p.scenarios.bull)
                });
            } else if (p.base && p.bull && p.bear) {
                const normalize = (s: any) => ({
                    ...s,
                    growthRate: Math.abs(s.growthRate) <= 1 && s.growthRate !== 0 ? s.growthRate * 100 : s.growthRate,
                    netMargin: Math.abs(s.netMargin) <= 1 && s.netMargin !== 0 ? s.netMargin * 100 : s.netMargin,
                    shareChange: Math.abs(s.shareChange) <= 1 && s.shareChange !== 0 ? s.shareChange * 100 : s.shareChange,
                });
                setScenarios({
                    bear: normalize(p.bear),
                    base: normalize(p.base),
                    bull: normalize(p.bull)
                });
            }
        }

        if (p.globalSettings) {
            setDiscountRate(p.globalSettings.discountRate);
            setTimeHorizon(p.globalSettings.timeHorizon);
        }

        if (p.dataPreferences) {
            setGrowthBasis(p.dataPreferences.growthBasis);
            setMarginBasis(p.dataPreferences.marginBasis);
        }

        if (p.name) setSaveName(p.name);

        setShowProjectionsPanel(false);
    };

    const handlePresetLoad = async (preset: any) => {
        if (preset.type === 'yahoo') {
            // Load Yahoo Consensus
            resetToYahoo();
        } else if (preset.type === 'ai') {
            // Load specific AI Analysis from the preset
            const aiProjection = preset.aiProjection;
            if (aiProjection && aiProjection.scenarios) {
                setScenarios(aiProjection.scenarios);
                if (aiProjection.globalSettings) {
                    setDiscountRate(aiProjection.globalSettings.discountRate);
                    setTimeHorizon(aiProjection.globalSettings.timeHorizon);
                }

                // Also load the thesis into the AI Result view
                const thesis = aiProjection.aiThesis;
                const base = aiProjection.scenarios.base;
                if (thesis) {
                    setAiResult({
                        fair_value: thesis.fairValue,
                        model_name: thesis.model,
                        rationale: thesis.rationale,
                        action: thesis.action,
                        growth_assumption: base ? base.growthRate / 100 : 0,
                        suggested_growth: base ? base.growthRate / 100 : undefined,
                        suggested_margin: base ? base.netMargin / 100 : undefined,
                        exit_pe: base ? base.exitPE : undefined,
                        quality_multiplier: base ? base.qualityMultiplier : undefined
                    });
                }

                // Open the modal with this projection
                setViewingProjection(aiProjection);
                setShowAIModal(true);

                setActiveScenario('base');
            } else {
                console.error('AI Preset missing projection data');
                alert('Failed to load this specific AI Analysis');
            }
        } else if (preset.type === 'user' && preset.data) {
            // Load User Preset
            setScenarios(preset.data.scenarios);
            setDiscountRate(preset.data.globalSettings.discountRate);
            setTimeHorizon(preset.data.globalSettings.timeHorizon);

            // Also restore AI Analysis if saved with it (User Presets often inherit AI data)
            const p = preset.data as any; // Cast to access optional aiThesis
            if (p.aiThesis) {
                const thesis = p.aiThesis;
                const base = preset.data.scenarios.base;
                setAiResult({
                    fair_value: thesis.fairValue,
                    model_name: thesis.model,
                    rationale: thesis.rationale,
                    action: thesis.action,
                    growth_assumption: base ? base.growthRate / 100 : 0,
                    suggested_growth: base ? base.growthRate / 100 : undefined,
                    suggested_margin: base ? base.netMargin / 100 : undefined,
                    exit_pe: base ? base.exitPE : undefined,
                    quality_multiplier: base ? base.qualityMultiplier : undefined,
                    researchReport: thesis.researchReport // Preserve report link
                } as any);
            } else {
                // Clear AI result if loading a manual preset that has no AI data
                setAiResult(null);
            }

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

                    <div className="text-[10px] font-medium text-secondary mb-0.5 uppercase tracking-widest mt-2 flex items-center gap-2">
                        Weighted Fair Value (5yr)
                        <HelpTrigger topicId="fairValue" />
                    </div>
                    ${Math.round(targetPrice)}
                </div>

                {/* AI Calibration Alert */}
                {aiResult && aiResult.fair_value && Math.abs(targetPrice - aiResult.fair_value) / aiResult.fair_value > 0.05 && (
                    <div className="mb-2 px-2 py-1 bg-yellow-500/10 border border-yellow-500/30 rounded-lg flex items-center gap-2 animate-in fade-in slide-in-from-top-1">
                        <div className="text-[10px] text-yellow-200 text-left leading-tight">
                            <span className="font-bold">Mismatch:</span> AI Thesis suggests <span className="underline decoration-dotted" title="The AI model likely used different implied assumptions (e.g. higher moat/quality scores) than the current slider defaults.">${aiResult.fair_value.toFixed(0)}</span>.
                        </div>
                        <button
                            onClick={() => {
                                // Auto-Calibrate: Scale Quality Multipliers to match AI Target
                                const ratio = aiResult.fair_value / targetPrice;
                                updateCurrent({
                                    qualityMultiplier: Math.min(2.0, Math.max(0.5, current.qualityMultiplier * ratio))
                                });
                                // Apply to all scenarios for consistency (optional, but cleaner)
                                setScenarios(prev => ({
                                    bear: { ...prev.bear, qualityMultiplier: Math.min(2.0, Math.max(0.5, prev.bear.qualityMultiplier * ratio)) },
                                    base: { ...prev.base, qualityMultiplier: Math.min(2.0, Math.max(0.5, prev.base.qualityMultiplier * ratio)) },
                                    bull: { ...prev.bull, qualityMultiplier: Math.min(2.0, Math.max(0.5, prev.bull.qualityMultiplier * ratio)) }
                                }));
                            }}
                            className="px-1.5 py-0.5 bg-yellow-500/20 hover:bg-yellow-500/30 text-yellow-300 text-[9px] font-bold uppercase rounded border border-yellow-500/30 transition-colors whitespace-nowrap"
                            title="Auto-adjust Quality Multipliers to align the model output with the AI's fair value."
                        >
                            Sync to ${aiResult.fair_value.toFixed(0)}
                        </button>
                    </div>
                )}

                {/* Active Scenario Indicator (Dynamic) */}
                <div className={`flex items-center gap-2 text-xs px-3 py-1.5 rounded-lg border transition-all ${activeScenario === 'bull' ? 'bg-green-500/10 border-green-500/20 text-green-400' :
                    activeScenario === 'bear' ? 'bg-red-500/10 border-red-500/20 text-red-400' :
                        'bg-primary/10 border-primary/20 text-primary'
                    }`}>
                    <span className="font-bold uppercase text-[9px] tracking-wider">{activeScenario} Case:</span>
                    <span className="font-bold">${Math.round(activePrice)}</span>
                    <span className="opacity-80 text-[10px]">
                        ({activeUpside > 0 ? '+' : ''}{activeUpside.toFixed(0)}%)
                    </span>
                </div>
            </div>

            {/* Vertical Matrix (Span 1) */}
            <div className="bg-surface border border-slate-800/50 rounded-xl p-3 flex flex-col justify-center">
                <div className="space-y-2">
                    {[
                        { mode: 'Bear', price: Math.round(bearPrice), upside: ((bearPrice - stockData.price) / stockData.price) * 100, color: 'text-red-400' },
                        { mode: 'Base', price: Math.round(basePrice), upside: ((basePrice - stockData.price) / stockData.price) * 100, color: 'text-primary' },
                        { mode: 'Bull', price: Math.round(bullPrice), upside: ((bullPrice - stockData.price) / stockData.price) * 100, color: 'text-green-400' }
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


            {/* AI Thesis Section */}
            {
                (aiResult || isAnalyzing || aiError) && (
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
                                <div className="flex items-center gap-2">
                                    <button
                                        onClick={() => { setAiResult(null); setAiError(null); setActiveCoachMetric(null); }}
                                        className="text-slate-500 hover:text-white transition-colors"
                                    >
                                        <X size={16} />
                                    </button>
                                </div>
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
                                <div className="relative z-10">
                                    <p className="text-xs text-slate-300 leading-relaxed font-medium italic">
                                        "{aiResult.rationale}"
                                    </p>
                                </div>
                            ) : null}
                        </div>
                    </div>
                )
            }

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
                    <div className="grid grid-cols-2 gap-x-4 gap-y-2">
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
                        <SliderInput
                            label="Strategic Moat"
                            value={moatScore}
                            setValue={setMoatScore}
                            min={0}
                            max={5}
                            unit="/5"
                            helpTopic="moatScore"
                            note="+5% per pt"
                        />
                        <SliderInput
                            label="Govt / Insider"
                            value={managementScore}
                            setValue={setManagementScore}
                            min={0}
                            max={5}
                            unit="/5"
                            helpTopic="managementScore"
                            note="+5% per pt"
                        />
                    </div>
                </section>

                {/* Sensitivity Matrix (Col 3) */}
                <SensitivityMatrix />
            </div>



            {/* Red Team / Sanity Check Section */}
            {
                (discountRate < 4 || peRatio > 80 || growthRate > 50 || netMargin > 50) && (
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
                )
            }

            {/* AI Analysis Modal */}
            <AIAnalysisModal
                isOpen={showAIModal}
                onClose={() => { setShowAIModal(false); setViewingProjection(null); }}
                symbol={stockData.symbol}
                initialProjection={viewingProjection}
            />

            {/* Save Modal */}
            {
                showSaveModal && (
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
                            <div className="flex items-center gap-2 mb-4">
                                <input
                                    type="checkbox"
                                    id="saveAsDefault"
                                    checked={saveAsDefault}
                                    onChange={(e) => setSaveAsDefault(e.target.checked)}
                                    className="rounded border-slate-700 bg-slate-900 text-primary focus:ring-primary"
                                />
                                <label htmlFor="saveAsDefault" className="text-xs text-slate-300 cursor-pointer select-none">
                                    Set as Default Load (Auto-load on refresh)
                                </label>
                            </div>
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
                )
            }

            {/* Projections Panel Slide-over */}
            {
                showProjectionsPanel && (
                    <ProjectionsPanel
                        isOpen={showProjectionsPanel}
                        onClose={() => setShowProjectionsPanel(false)}
                        ticker={stockData.symbol}
                        onLoad={handleLoad}
                    />
                )
            }

            {/* Preset Selector Modal */}
            {
                showPresetModal && (
                    <PresetSelectorModal
                        symbol={stockData.symbol}
                        onLoad={handlePresetLoad}
                        onViewReport={(aiProjection) => {
                            setShowPresetModal(false);
                            setViewingProjection(aiProjection);
                            setShowAIModal(true);
                            // Map stored AIThesis (camelCase) to ValuationResult (snake_case)
                            const thesis = aiProjection.aiThesis;
                            const base = aiProjection.scenarios?.base;
                            if (thesis) {
                                setAiResult({
                                    fair_value: thesis.fairValue,
                                    model_name: thesis.model,
                                    rationale: thesis.rationale,
                                    action: thesis.action,
                                    // Map data from base scenario if available
                                    growth_assumption: base ? base.growthRate / 100 : 0,
                                    suggested_growth: base ? base.growthRate / 100 : undefined,
                                    suggested_margin: base ? base.netMargin / 100 : undefined,
                                    exit_pe: base ? base.exitPE : undefined,
                                    quality_multiplier: base ? base.qualityMultiplier : undefined
                                });
                            }
                        }}
                        onClose={() => setShowPresetModal(false)}
                    />
                )
            }
        </div >
    );
}
