/**
 * ValuationModeler.tsx (React Component)
 * =====================================
 *
 * Purpose:
 *     Complex interactive DCF modeler supporting dynamic scenarios and preset comparisons.
 *
 * Layer: Frontend / UI / Components
 *
 * Usage Examples:
 *     <ValuationModeler symbol="AAPL" data={stockData} />
 *
 * Key Functions:
 *     - calculateDCF() - Core mathematical logic for intrinsic value computation
 *     - handleInputChange() - Debounced state updates for model inputs
 *     - saveAsPreset() - Persists the current model configuration to local storage
 */
import { useState, useEffect, useCallback, useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import { Save, RotateCcw, Info, X, AlertTriangle, Table2, SlidersHorizontal, ChevronUp, ChevronDown } from 'lucide-react';
import type { StockData } from '../services/api';
import { ProjectionsPanel } from './ProjectionsPanel';
import { storage } from '../services/storage';
import { HelpTrigger } from './HelpModal';
import { computeScenario } from '../utils/valuationMath';
import { Sparkles, BrainCircuit, Loader2, FolderOpen } from 'lucide-react';
import { AIAnalysisModal } from './AIAnalysisModal';
import { AgentReminderModal } from './AgentReminderModal';
import { PresetSelectorModal } from './PresetSelectorModal';
import { saveUserPreset } from '../services/presets';

// --- Extracted Components (defined outside render to avoid remounting) ---

interface SliderInputProps {
    label: string;
    value: number;
    setValue: (v: number) => void;
    min: number;
    max: number;
    unit?: string;
    step?: number;
    note?: string;
    helpTopic?: string;
    warningThreshold?: number | null;
    impact?: 'High' | 'Med' | 'Low';
}

function SliderInput({ label, value, setValue, min, max, unit = '', step = 1, note = '', helpTopic = '', warningThreshold = null, impact = 'Low' }: SliderInputProps) {
    const isWarning = warningThreshold !== null && value < warningThreshold;
    const impactColor = impact === 'High' ? 'bg-purple-500' : impact === 'Med' ? 'bg-blue-400' : 'bg-slate-600';

    return (
        <div className="mb-1.5 group">
            <div className="flex justify-between items-center mb-1">
                <div className="flex items-center gap-2">
                    <div className={`w-1 h-3 rounded-full ${impactColor}`} title={`${impact} Impact on Valuation`}></div>
                    <label className={`text-[10px] font-bold uppercase tracking-wider flex items-center gap-1 ${isWarning ? 'text-red-400' : 'text-slate-300 group-hover:text-white transition-colors'}`}>
                        {label}
                    </label>
                    {helpTopic && (
                        <HelpTrigger topicId={helpTopic} className="opacity-30 hover:opacity-100 transition-opacity" size={12} />
                    )}
                </div>
                <div className="flex items-baseline gap-2">
                    {note && <span className="text-[9px] text-slate-600 font-medium">{note}</span>}
                    <div className={`flex items-center rounded px-2 py-0.5 border ${isWarning ? 'bg-red-500/10 border-red-500/50' : 'bg-slate-800 border-slate-700 group-hover:border-slate-500 transition-colors'}`}>
                        <input
                            type="number"
                            value={value}
                            step={step}
                            onChange={(e) => setValue(Number(e.target.value))}
                            className={`w-12 bg-transparent text-right text-xs font-bold focus:outline-none ${isWarning ? 'text-red-400' : 'text-white'}`}
                        />
                        <span className="text-[10px] text-slate-500 ml-0.5">{unit}</span>
                    </div>
                </div>
            </div>

            <input
                type="range"
                min={min}
                max={max}
                step={step}
                value={value}
                onChange={(e) => setValue(Number(e.target.value))}
                style={{
                    background: `linear-gradient(to right, ${isWarning ? '#ef4444' : '#6366f1'} 0%, ${isWarning ? '#ef4444' : '#6366f1'} ${((value - min) / (max - min)) * 100}%, #1e293b ${((value - min) / (max - min)) * 100}%, #1e293b 100%)`
                }}
                className={`w-full h-1.5 rounded-lg appearance-none cursor-pointer transition-all mt-1 focus:outline-none focus:ring-1 focus:ring-indigo-500/50
                    [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-3 [&::-webkit-slider-thumb]:h-3 
                    [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-white 
                    [&::-webkit-slider-thumb]:shadow-[0_0_10px_rgba(0,0,0,0.5)] [&::-webkit-slider-thumb]:mt-[-3px] 
                    ${isWarning ? '[&::-webkit-slider-thumb]:ring-2 [&::-webkit-slider-thumb]:ring-red-500' : ''}`}
            />

            <div className="flex justify-between text-[8px] text-slate-700 mt-0.5 px-0.5">
                <span>{min}</span>
                <span>{max}</span>
            </div>
        </div>
    );
}

interface SensitivityMatrixProps {
    peRatio: number;
    growthRate: number;
    stockPrice: number;
    calculatePrice: (g: number, pe: number) => number;
}

function SensitivityMatrix({ peRatio, growthRate, stockPrice, calculatePrice }: SensitivityMatrixProps) {
    const currentPe = Math.max(5, Math.round(peRatio / 5) * 5);
    const currentGrowth = Math.round(growthRate / 5) * 5;

    const peRange = useMemo(() =>
        [currentPe - 10, currentPe - 5, currentPe, currentPe + 5, currentPe + 10].filter(p => p > 0),
        [currentPe]
    );

    const growthRange = useMemo(() =>
        [currentGrowth - 10, currentGrowth - 5, currentGrowth, currentGrowth + 5, currentGrowth + 10],
        [currentGrowth]
    );

    return (
        <div className="h-full flex flex-col">
            <div className="flex-1 overflow-auto">
                <table className="w-full text-[9px] border-collapse min-w-[280px]">
                    <thead>
                        <tr>
                            <th className="p-1 text-slate-500 font-medium text-left border-b border-slate-800">G \ PE</th>
                            {peRange.map(pe => (
                                <th key={pe} className={`p-1 border-b border-slate-800 text-center transition-colors duration-300 ${pe === currentPe ? 'text-white font-bold bg-purple-500/20' : 'text-slate-600'}`}>
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
                                    const mxUpside = stockPrice > 0 ? ((price - stockPrice) / stockPrice) * 100 : 0;

                                    let colorClass = 'text-slate-600';
                                    if (mxUpside > 50) colorClass = 'bg-green-500/20 text-green-400 font-bold';
                                    else if (mxUpside > 20) colorClass = 'bg-green-500/10 text-green-500';
                                    else if (mxUpside > 0) colorClass = 'text-green-600';
                                    else if (mxUpside > -20) colorClass = 'text-red-400';
                                    else colorClass = 'bg-red-500/10 text-red-500 font-bold';

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
}

// --- Normalization helper (extracted to avoid duplication) ---

function normalizeScenario(s: any): Scenario & { weight: number } {
    return {
        ...s,
        growthRate: (Math.abs(s.growthRate) > 0 && Math.abs(s.growthRate) < 1.0) ? s.growthRate * 100 : s.growthRate,
        netMargin: (Math.abs(s.netMargin) > 0 && Math.abs(s.netMargin) < 1.0) ? s.netMargin * 100 : s.netMargin,
        shareChange: (Math.abs(s.shareChange) > 0 && Math.abs(s.shareChange) < 1.0) ? s.shareChange * 100 : s.shareChange,
    };
}

function extractScenariosFromProjection(p: any): { bear: Scenario & { weight: number }; base: Scenario & { weight: number }; bull: Scenario & { weight: number } } | null {
    if (p.scenarios?.bear && p.scenarios?.base && p.scenarios?.bull) {
        return {
            bear: normalizeScenario(p.scenarios.bear),
            base: normalizeScenario(p.scenarios.base),
            bull: normalizeScenario(p.scenarios.bull),
        };
    }
    if (p.bear && p.base && p.bull) {
        return {
            bear: normalizeScenario(p.bear),
            base: normalizeScenario(p.base),
            bull: normalizeScenario(p.bull),
        };
    }
    return null;
}

// --- Main Component ---

interface ValuationModelerProps {
    stockData: StockData;
}

export default function ValuationModeler({ stockData }: ValuationModelerProps) {
    // --- State ---
    const [activeScenario, setActiveScenario] = useState<'bear' | 'base' | 'bull'>('base');
    const [showProjectionsPanel, setShowProjectionsPanel] = useState(false);
    const [savedCount, setSavedCount] = useState(0);

    // AI State
    const [isAnalyzing] = useState(false);
    const [aiResult, setAiResult] = useState<ValuationResult | null>(null);
    const [aiError, setAiError] = useState<string | null>(null);
    const [activeCoachMetric, setActiveCoachMetric] = useState<string | null>(null);

    // Save Modal State
    const [showSaveModal, setShowSaveModal] = useState(false);
    const [showAIModal, setShowAIModal] = useState(false);
    const [showAgentReminder, setShowAgentReminder] = useState(false);
    const [saveName, setSaveName] = useState('');
    const [saveAsDefault, setSaveAsDefault] = useState(false);
    const [showPresetModal, setShowPresetModal] = useState(false);
    const [showAdvanced, setShowAdvanced] = useState(false);
    const [viewingProjection, setViewingProjection] = useState<Projection | null>(null);
    const [activeProjection, setActiveProjection] = useState<{ id: string; version: number } | null>(null);

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
    const updateCurrent = useCallback((updates: Partial<Scenario & { weight: number }>) => {
        setScenarios(prev => ({
            ...prev,
            [activeScenario]: { ...prev[activeScenario], ...updates }
        }));
    }, [activeScenario]);

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

    const setGrowthRate = useCallback((v: number) => updateCurrent({ growthRate: v }), [updateCurrent]);
    const setNetMargin = useCallback((v: number) => updateCurrent({ netMargin: v }), [updateCurrent]);
    const setPeRatio = useCallback((v: number) => updateCurrent({ exitPE: v }), [updateCurrent]);
    const setQualityMultiplier = useCallback((v: number) => updateCurrent({ qualityMultiplier: v }), [updateCurrent]);
    const setShareChange = useCallback((v: number) => updateCurrent({ shareChange: v }), [updateCurrent]);
    const setMoatScore = useCallback((v: number) => updateCurrent({ moatScore: v }), [updateCurrent]);
    const setManagementScore = useCallback((v: number) => updateCurrent({ managementScore: v }), [updateCurrent]);
    const setWeight = useCallback((v: number) => updateCurrent({ weight: v / 100 }), [updateCurrent]);

    // Data preferences
    const [growthBasis, setGrowthBasis] = useState<'current' | 'next'>('next');
    const [marginBasis, setMarginBasis] = useState<'ttm' | 'quarterly'>('quarterly');

    // --- Calculations ---

    // Derived Prices
    const bearResult = useMemo(() => computeScenario(stockData.metrics.revenue, stockData.metrics.market_cap / stockData.price, discountRate/100, timeHorizon, scenarios.bear), [stockData, discountRate, timeHorizon, scenarios.bear]);
    const baseResult = useMemo(() => computeScenario(stockData.metrics.revenue, stockData.metrics.market_cap / stockData.price, discountRate/100, timeHorizon, scenarios.base), [stockData, discountRate, timeHorizon, scenarios.base]);
    const bullResult = useMemo(() => computeScenario(stockData.metrics.revenue, stockData.metrics.market_cap / stockData.price, discountRate/100, timeHorizon, scenarios.bull), [stockData, discountRate, timeHorizon, scenarios.bull]);

    const bearPrice = bearResult.presentValue;
    const basePrice = baseResult.presentValue;
    const bullPrice = bullResult.presentValue;

    const weightedPrice = (bearPrice * scenarios.bear.weight) + (basePrice * scenarios.base.weight) + (bullPrice * scenarios.bull.weight);
    const targetPrice = Math.round(weightedPrice * 100) / 100;

    const activePrice = activeScenario === 'bull' ? bullPrice : activeScenario === 'bear' ? bearPrice : basePrice;
    const activeResult = activeScenario === 'bull' ? bullResult : activeScenario === 'bear' ? bearResult : baseResult;
    
    const activeUpside = stockData.price > 0 ? ((activePrice - stockData.price) / stockData.price) * 100 : 0;
    const upside = stockData.price > 0 ? ((targetPrice - stockData.price) / stockData.price) * 100 : 0;

    // Helper used by Sensitivity Matrix (now using shared logic)
    const calculatePrice = useCallback((g: number, pe: number) => {
        const tempScenario = {
            ...current,
            growthRate: g,
            exitPE: pe,
        };
        return computeScenario(stockData.metrics.revenue, stockData.metrics.market_cap / stockData.price, discountRate/100, timeHorizon, tempScenario).presentValue;
    }, [stockData, discountRate, timeHorizon, current]);

    // --- resetToYahoo ---
    const resetToYahoo = useCallback(() => {
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

        if (baseMargin < 0) {
            baseMargin = 5.0;
        }

        const basePe = stockData.analyst_estimates?.forward_pe || stockData.metrics?.forward_pe || stockData.metrics?.pe_ratio || 25;

        setDiscountRate(10);
        setTimeHorizon(5);
        setActiveProjection(null);

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
    }, [stockData, growthBasis, marginBasis]);

    // --- handleLoad ---
    const handleLoad = useCallback((loadedProjection: any) => {
        const p = loadedProjection;

        if (p.id && p.ticker) {
            if (p.source === 'USER') {
                setActiveProjection({ id: p.id, version: p.version });
            } else {
                setActiveProjection(null);
            }
        } else {
            setActiveProjection(null);
        }

        const extracted = extractScenariosFromProjection(p);
        if (extracted) {
            setScenarios(extracted);
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

        // Populate aiResult if aiThesis exists in the loaded projection
        if (p.aiThesis) {
            const thesis = p.aiThesis;
            const base = extracted?.base || p.scenarios?.base; // Use extracted if available, else raw
            setAiResult({
                fair_value: thesis.fairValue,
                model_name: thesis.model,
                rationale: p.rationale || thesis.rationale, // Prefer root rationale (summary) over thesis detail
                action: thesis.action,
                growth_assumption: base ? base.growthRate / 100 : 0,
                suggested_growth: base ? base.growthRate / 100 : undefined,
                suggested_margin: base ? base.netMargin / 100 : undefined,
                exit_pe: base ? base.exitPE : undefined,
                quality_multiplier: base ? base.qualityMultiplier : undefined,
                researchReport: thesis.researchReport
            } as any);
        } else {
            setAiResult(null);
        }

        setShowProjectionsPanel(false);
    }, []);

    // Initialize: Try to load latest saved projection, otherwise default to Yahoo
    useEffect(() => {
        const init = async () => {
            const saved = await storage.syncProjections(stockData.symbol);
            setSavedCount(saved.length);

            if (saved.length > 0) {
                const defaults = saved.filter(p => p.isDefault);
                let target;
                if (defaults.length > 0) {
                    target = defaults.sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime())[0];
                } else {
                    target = saved.sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime())[0];
                }
                handleLoad(target);
            } else {
                resetToYahoo();
            }
        };
        init();
    }, [stockData.symbol, handleLoad, resetToYahoo]);

    // --- Actions ---

    const handleAIAnalysis = useCallback(() => {
        setShowAgentReminder(true);
    }, []);

    const handleSaveConfirm = useCallback(() => {
        if (!saveName.trim()) return;

        const snapshot = {
            price: stockData.price,
            currency: stockData.currency,
            shares: stockData.metrics.shares_outstanding || 0,
            revenue: stockData.metrics.revenue || 0,
            lastActualPS: stockData.metrics.market_cap / (stockData.metrics.revenue || 1),
            analystGrowthEstimate: stockData.analyst_estimates?.revenue_growth,
            analystMarginEstimate: stockData.analyst_estimates?.profit_margin,
            fiscalPeriod: "TTM"
        };

        const projection: Projection = {
            id: activeProjection?.id || crypto.randomUUID(),
            source: 'USER',
            ticker: stockData.symbol,
            schemaVersion: '1.1',
            version: activeProjection ? activeProjection.version + 1 : 1,
            savedAt: new Date().toISOString(),
            updatedAt: new Date().toISOString(),
            name: saveName,
            isDefault: saveAsDefault,
            snapshot,
            dataPreferences: { growthBasis, marginBasis },
            scenarios: scenarios,
            globalSettings: { discountRate, timeHorizon },
            aiThesis: aiResult ? {
                model: aiResult.model_name,
                rationale: aiResult.rationale,
                fairValue: aiResult.fair_value,
                action: (aiResult.action as any) || 'HOLD',
                analyzedAt: new Date().toISOString(),
                researchReport: (aiResult as any).researchReport
            } : undefined
        };

        storage.saveProjection(projection)
            .then(() => {
                setSavedCount(prev => prev + 1);
                setActiveProjection({ id: projection.id, version: projection.version });
                setShowSaveModal(false);
            })
            .catch(err => alert("Failed to save: " + err.message));
    }, [saveName, stockData, activeProjection, saveAsDefault, growthBasis, marginBasis, scenarios, discountRate, timeHorizon, aiResult]);

    const handlePresetLoad = useCallback(async (preset: any) => {
        if (preset.type === 'yahoo') {
            resetToYahoo();
        } else if (preset.type === 'ai') {
            const aiProjection = preset.aiProjection;
            if (aiProjection && aiProjection.scenarios) {
                const newSettings = aiProjection.globalSettings || { discountRate: 10, timeHorizon: 5 };

                const newScenarios = {
                    bear: { ...aiProjection.scenarios.bear },
                    base: { ...aiProjection.scenarios.base },
                    bull: { ...aiProjection.scenarios.bull }
                };

                setScenarios(newScenarios);
                setDiscountRate(newSettings.discountRate);
                setTimeHorizon(newSettings.timeHorizon);

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

                setViewingProjection(aiProjection);
                setShowAIModal(true);
                setActiveScenario('base');
            } else {
                console.error('AI Preset missing projection data');
                alert('Failed to load this specific AI Analysis');
            }
        } else if (preset.type === 'user' && preset.data) {
            setScenarios(preset.data.scenarios);
            setDiscountRate(preset.data.globalSettings.discountRate);
            setTimeHorizon(preset.data.globalSettings.timeHorizon);

            const p = preset.data as any;
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
                    researchReport: thesis.researchReport
                } as any);
            } else {
                setAiResult(null);
            }

            setActiveScenario('base');
        }
        setShowPresetModal(false);
    }, [resetToYahoo, calculateScenarioPrice]);

    const handleSaveAsPreset = useCallback(() => {
        const presetName = prompt('Name this preset:');
        if (!presetName?.trim()) return;

        saveUserPreset(
            stockData.symbol,
            presetName,
            scenarios,
            { discountRate, timeHorizon }
        );

        alert(`Saved preset: ${presetName}`);
    }, [stockData.symbol, scenarios, discountRate, timeHorizon]);

    const handleViewFullReport = useCallback(() => {
        const tempProjection: Projection = {
            id: 'temp-ai-view',
            source: 'AI_AGENT',
            schemaVersion: '1.1',
            ticker: stockData.symbol,
            version: 1,
            savedAt: new Date().toISOString(),
            updatedAt: new Date().toISOString(),
            name: 'Current AI Analysis',
            rationale: aiResult?.rationale,
            snapshot: {
                price: stockData.price,
                currency: stockData.currency,
                revenue: stockData.metrics.revenue || 0,
                shares: stockData.metrics.shares_outstanding || 0,
                lastActualPS: stockData.metrics.market_cap / (stockData.metrics.revenue || 1),
                fiscalPeriod: "TTM",
                analystGrowthEstimate: stockData.analyst_estimates?.revenue_growth,
                analystMarginEstimate: stockData.analyst_estimates?.profit_margin
            },
            dataPreferences: { growthBasis, marginBasis },
            scenarios: scenarios,
            globalSettings: { discountRate, timeHorizon },
            aiThesis: aiResult ? {
                model: aiResult.model_name,
                rationale: aiResult.rationale,
                fairValue: aiResult.fair_value,
                action: (aiResult.action as 'BUY' | 'SELL' | 'HOLD') || 'HOLD',
                analyzedAt: new Date().toISOString(),
                researchReport: (aiResult as any).researchReport
            } : undefined
        };
        setViewingProjection(tempProjection);
        setShowAIModal(true);
    }, [aiResult, stockData, scenarios, growthBasis, marginBasis, discountRate, timeHorizon]);

    const handleSyncToAI = useCallback(() => {
        if (!aiResult?.fair_value) return;
        const ratio = aiResult.fair_value / targetPrice;
        setScenarios(prev => ({
            bear: { ...prev.bear, qualityMultiplier: Math.min(2.0, Math.max(0.5, prev.bear.qualityMultiplier * ratio)) },
            base: { ...prev.base, qualityMultiplier: Math.min(2.0, Math.max(0.5, prev.base.qualityMultiplier * ratio)) },
            bull: { ...prev.bull, qualityMultiplier: Math.min(2.0, Math.max(0.5, prev.bull.qualityMultiplier * ratio)) }
        }));
    }, [aiResult, targetPrice]);

    // Memoized growth estimate display values
    const currentYearGrowth = useMemo(() => {
        const val = stockData.growth_estimates?.stockTrend['0y'];
        if (val === undefined) return 'N/A';
        return (Math.abs(val) > 1 ? val : val * 100).toFixed(1) + '%';
    }, [stockData.growth_estimates]);

    const nextYearGrowth = useMemo(() => {
        const val = stockData.growth_estimates?.stockTrend['+1y'];
        if (val === undefined) return 'N/A';
        return (Math.abs(val) > 1 ? val : val * 100).toFixed(1) + '%';
    }, [stockData.growth_estimates]);

    const ttmMarginDisplay = useMemo(() => {
        const val = stockData.metrics?.profit_margin ?? 0;
        return (Math.abs(val) > 1 ? val : val * 100).toFixed(1);
    }, [stockData.metrics?.profit_margin]);

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
                        onClick={() => handleAIAnalysis()}
                        disabled={isAnalyzing}
                        className={`flex items-center gap-2 px-2 py-1 rounded-lg transition-all text-[10px] font-medium border ${isAnalyzing
                            ? 'bg-purple-500/20 text-purple-300 border-purple-500/30 cursor-not-allowed'
                            : 'bg-indigo-500/10 text-indigo-400 hover:bg-indigo-500/20 border-indigo-500/20'
                            }`}
                        title="Run professional deep-research analysis in your terminal"
                    >
                        {isAnalyzing ? <Loader2 size={12} className="animate-spin" /> : <Sparkles size={12} />}
                        AI Analyst (CLI)
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

            {/* AI Calibration Alert (Overlay) */}
            {aiResult && aiResult.fair_value && Math.abs(targetPrice - aiResult.fair_value) / aiResult.fair_value > 0.05 && (
                <div className="absolute bottom-16 left-1/2 -translate-x-1/2 z-30">
                    <button
                        onClick={handleSyncToAI}
                        className="px-3 py-1 bg-yellow-500/10 hover:bg-yellow-500/20 text-yellow-200 text-[10px] font-bold uppercase rounded-full border border-yellow-500/30 transition-colors whitespace-nowrap flex items-center gap-2 backdrop-blur-md shadow-lg animate-pulse"
                    >
                        <AlertTriangle size={10} />
                        Sync to AI Target: ${aiResult.fair_value.toFixed(0)}
                    </button>
                </div>
            )}

            {/* AI Thesis Section */}
            {(aiResult || isAnalyzing || aiError) && (
                <div className="mb-2 flex-none animate-in fade-in slide-in-from-top-4 duration-500">
                    <div className="bg-gradient-to-br from-indigo-900/40 via-slate-900/60 to-purple-900/30 border border-indigo-500/30 rounded-xl p-3 shadow-xl overflow-hidden relative group">
                        <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-indigo-500 via-purple-500 to-indigo-500 opacity-50"></div>
                        <div className="absolute -right-10 -top-10 w-32 h-32 bg-indigo-500/10 blur-3xl rounded-full group-hover:bg-indigo-500/20 transition-all duration-1000"></div>

                        <div className="flex justify-between items-start mb-2 relative z-10">
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
                                    <p className="text-[10px] text-slate-500">Processing Investment Thesis</p>
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
                            <div className="z-10 transition-all duration-300 ease-in-out">
                                <div className="relative">
                                    <div className={`text-xs text-slate-300 leading-relaxed font-medium pr-2 custom-scrollbar max-h-[44px] overflow-hidden`}>
                                        <ReactMarkdown components={{
                                            strong: ({ node, ...props }: any) => <span className="font-bold text-indigo-200" {...props} />,
                                            h1: ({ node, ...props }: any) => <span className="block font-bold mt-2 mb-1" {...props} />,
                                            h2: ({ node, ...props }: any) => <span className="block font-bold mt-2 mb-1" {...props} />,
                                            h3: ({ node, ...props }: any) => <span className="block font-bold mt-1 mb-0.5" {...props} />,
                                            p: ({ node, ...props }: any) => <p className="mb-1 last:mb-0 inline" {...props} />
                                        }}>
                                            {aiResult.rationale}
                                        </ReactMarkdown>
                                    </div>
                                    <div className="absolute bottom-0 left-0 right-0 h-8 bg-gradient-to-t from-slate-900 to-transparent pointer-events-none"></div>
                                </div>
                                <button
                                    onClick={handleViewFullReport}
                                    className="mt-1 text-[10px] uppercase font-bold text-indigo-400 hover:text-indigo-300 flex items-center gap-1 bg-slate-800/50 px-2 py-0.5 rounded transition-colors group-hover:bg-slate-800"
                                >
                                    View Full Report <FolderOpen size={10} />
                                </button>
                            </div>
                        ) : null}
                    </div>
                </div>
            )}

            {/* Main Body: 2-Column Grid (Left: Drivers, Right: Analysis) */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-3 mb-1 min-h-0 flex-1 overflow-hidden pr-1">
                {/* Left Column (65%): Hero + Drivers */}
                <div className="lg:col-span-8 flex flex-col gap-2 overflow-y-auto custom-scrollbar pr-1">

                    {/* Hero Section (Target Price Dashboard) */}
                    <div className="w-full bg-gradient-to-r from-slate-900/80 to-slate-900/30 rounded-xl border border-slate-800/50 relative overflow-hidden flex flex-col justify-between p-2 shrink-0">
                        <div className="absolute top-3 right-3 flex gap-1 z-20 bg-slate-950/40 p-1 rounded-lg border border-white/5 backdrop-blur-sm">
                            {(['bear', 'base', 'bull'] as const).map((s) => (
                                <button
                                    key={s}
                                    onClick={() => setActiveScenario(s)}
                                    className={`px-3 py-1 rounded text-[9px] font-bold uppercase tracking-wider transition-all ${activeScenario === s
                                        ? s === 'bull' ? 'bg-green-500/20 text-green-400 border border-green-500/30 shadow-[0_0_10px_rgba(74,222,128,0.2)]'
                                            : s === 'bear' ? 'bg-red-500/20 text-red-400 border border-red-500/30 shadow-[0_0_10px_rgba(248,113,113,0.2)]'
                                                : 'bg-primary/20 text-primary border border-primary/30 shadow-[0_0_10px_rgba(99,102,241,0.2)]'
                                        : 'text-slate-500 hover:text-slate-300 hover:bg-white/5'
                                        }`}
                                >
                                    {s}
                                </button>
                            ))}
                        </div>

                        <div className="flex flex-col items-center justify-center flex-1 z-10">
                            <span className="text-[10px] font-bold text-secondary uppercase tracking-[0.2em] mb-1 flex items-center gap-1.5 opacity-80">
                                Weighted Fair Value
                            </span>
                            <div className="text-3xl font-black text-white tracking-tight flex items-baseline gap-2 drop-shadow-2xl">
                                ${Math.round(targetPrice)}
                                <span className={`text-sm font-bold ${upside > 0 ? 'text-green-400' : 'text-red-400'}`}>
                                    ({upside > 0 ? '+' : ''}{upside.toFixed(0)}%)
                                </span>
                            </div>
                        </div>

                        <div className="mt-auto w-full border-t border-white/5 pt-2 flex justify-between items-center z-10">
                            <div className="flex items-center gap-2">
                                <span className="text-[10px] text-slate-400 uppercase">Active Case:</span>
                                <span className={`text-xs font-bold uppercase ${activeScenario === 'bull' ? 'text-green-400' : activeScenario === 'bear' ? 'text-red-400' : 'text-indigo-400'}`}>
                                    {activeScenario}
                                </span>
                            </div>
                            <div className="flex items-center gap-4 text-[10px] text-slate-400">
                                <span>Target: <span className="text-white font-bold">${Math.round(activePrice)}</span></span>
                                <span>Upside: <span className={activeUpside > 0 ? 'text-green-400 font-bold' : 'text-red-400 font-bold'}>{activeUpside > 0 ? '+' : ''}{activeUpside.toFixed(0)}%</span></span>
                            </div>
                        </div>
                    </div>

                    {/* Drivers Panel */}
                    <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-3 backdrop-blur-sm">
                        <div className="flex justify-between items-center mb-2 border-b border-slate-800/50 pb-1">
                            <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                                <SlidersHorizontal size={16} className="text-indigo-400" />
                                Model Drivers
                            </h3>
                            <button
                                onClick={() => setShowAdvanced(!showAdvanced)}
                                className="text-[10px] uppercase font-bold text-slate-500 hover:text-indigo-400 transition-colors flex items-center gap-1 bg-slate-800/50 px-2 py-1 rounded hover:bg-slate-800"
                            >
                                {showAdvanced ? 'Hide Advanced' : 'Show Advanced'}
                                {showAdvanced ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                            </button>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-2">
                            {/* Core Inputs: Growth */}
                            <div>
                                <div className="flex justify-between mb-2 items-center">
                                    <span className="text-[10px] font-bold text-indigo-300 uppercase tracking-wider">Growth Engine</span>
                                    <div className="flex gap-1">
                                        <button
                                            onClick={() => { setGrowthBasis('current'); resetToYahoo(); }}
                                            className={`px-1.5 py-0.5 text-[8px] rounded border transition-colors ${growthBasis === 'current' ? 'bg-primary/20 text-primary border-primary/30' : 'bg-slate-800 text-slate-500 border-slate-700 hover:text-slate-300'}`}
                                        >
                                            Cur: {currentYearGrowth}
                                        </button>
                                        <button
                                            onClick={() => { setGrowthBasis('next'); resetToYahoo(); }}
                                            className={`px-1.5 py-0.5 text-[8px] rounded border transition-colors ${growthBasis === 'next' ? 'bg-primary/20 text-primary border-primary/30' : 'bg-slate-800 text-slate-500 border-slate-700 hover:text-slate-300'}`}
                                        >
                                            Next: {nextYearGrowth}
                                        </button>
                                    </div>
                                </div>
                                <SliderInput
                                    label="Revenue Growth"
                                    value={growthRate}
                                    setValue={setGrowthRate}
                                    min={-50} max={100} unit="%"
                                    impact="High"
                                    helpTopic="growthRate"
                                />
                            </div>

                            {/* Core Inputs: Profitability */}
                            <div>
                                <div className="flex justify-between mb-2 items-center">
                                    <span className="text-[10px] font-bold text-indigo-300 uppercase tracking-wider">Profitability</span>
                                    <div className="flex gap-1">
                                        <button
                                            onClick={() => { setMarginBasis('ttm'); resetToYahoo(); }}
                                            className={`px-1.5 py-0.5 text-[8px] rounded border transition-colors ${marginBasis === 'ttm' ? 'bg-primary/20 text-primary border-primary/30' : 'bg-slate-800 text-slate-500 border-slate-700 hover:text-slate-300'}`}
                                        >
                                            TTM: {ttmMarginDisplay}%
                                        </button>
                                        <button
                                            onClick={() => { setMarginBasis('quarterly'); resetToYahoo(); }}
                                            className={`px-1.5 py-0.5 text-[8px] rounded border transition-colors ${marginBasis === 'quarterly' ? 'bg-primary/20 text-primary border-primary/30' : 'bg-slate-800 text-slate-500 border-slate-700 hover:text-slate-300'}`}
                                        >
                                            Q: {stockData.quarterly_margin ? stockData.quarterly_margin.toFixed(1) + '%' : 'N/A'}
                                        </button>
                                    </div>
                                </div>
                                <SliderInput
                                    label="Net Margin"
                                    value={netMargin}
                                    setValue={setNetMargin}
                                    min={-20} max={80} unit="%"
                                    impact="High"
                                    helpTopic="netMargin"
                                />
                            </div>

                            {/* Core Inputs: Valuation */}
                            <div>
                                <div className="text-[10px] font-bold text-indigo-300 uppercase mb-2 tracking-wider flex justify-between items-center">
                                    Valuation
                                    <div className={`text-[9px] px-1.5 py-0.5 rounded border ${Math.abs(totalWeight - 1.0) < 0.01 ? 'bg-green-500/10 text-green-400 border-green-500/20' : 'bg-red-500/10 text-red-400 border-red-500/20 animate-pulse'}`}>
                                        Risk Weight: {Math.round(totalWeight * 100)}%
                                    </div>
                                </div>
                                <SliderInput
                                    label="Exit P/E"
                                    value={peRatio}
                                    setValue={setPeRatio}
                                    min={1} max={100} unit="x"
                                    impact="High"
                                    helpTopic="exitPE"
                                    note={`Fwd: ${(stockData.analyst_estimates?.forward_pe || stockData.metrics?.forward_pe || 0).toFixed(1)}x`}
                                />
                                <SliderInput
                                    label="Scenario Prob."
                                    value={currentWeight}
                                    setValue={setWeight}
                                    min={0} max={100} unit="%"
                                    impact="High"
                                    helpTopic="probabilityWeight"
                                    note="Weight"
                                />
                            </div>

                            {/* Core Inputs: Structure */}
                            <div>
                                <div className="text-[10px] font-bold text-indigo-300 uppercase mb-2 tracking-wider">Structure</div>
                                <SliderInput
                                    label="Discount Rate"
                                    value={discountRate}
                                    setValue={setDiscountRate}
                                    min={0} max={20} unit="%"
                                    impact="Med"
                                    helpTopic="discountRate"
                                    warningThreshold={4}
                                    note="Typ: 8-12%"
                                />
                            </div>
                        </div>

                        {/* Collapsible Advanced Section */}
                        {showAdvanced && (
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-2 mt-2 pt-2 border-t border-slate-800/50 animate-in fade-in slide-in-from-top-2">
                                <div>
                                    <div className="text-[10px] font-bold text-slate-500 uppercase mb-2 tracking-wider">Advanced Evaluation</div>
                                    <div className="space-y-3">
                                        <SliderInput
                                            label="Quality Multiplier"
                                            value={qualityMultiplier}
                                            setValue={setQualityMultiplier}
                                            min={0.5} max={2.0} step={0.05} unit="x"
                                            impact="Med"
                                            helpTopic="qualityMultiplier"
                                            note="Typ: 1.0x"
                                        />
                                        <SliderInput
                                            label="Share Change"
                                            value={shareChange}
                                            setValue={setShareChange}
                                            min={-20} max={20} unit="%"
                                            impact="Med"
                                            helpTopic="shareChange"
                                            note="(-) Buyback"
                                        />
                                    </div>
                                </div>
                                <div>
                                    <div className="text-[10px] font-bold text-slate-500 uppercase mb-2 tracking-wider">Qualitative Factors</div>
                                    <div className="space-y-3">
                                        <SliderInput
                                            label="Time Horizon"
                                            value={timeHorizon}
                                            setValue={setTimeHorizon}
                                            min={1} max={10} unit="yr"
                                            impact="Low"
                                            helpTopic="timeHorizon"
                                        />
                                        <SliderInput
                                            label="Strategic Moat"
                                            value={moatScore}
                                            setValue={setMoatScore}
                                            min={0} max={5} unit="/5"
                                            impact="Low"
                                            helpTopic="moatScore"
                                            note="+5% per pt"
                                        />
                                        <SliderInput
                                            label="Govt / Insider"
                                            value={managementScore}
                                            setValue={setManagementScore}
                                            min={0} max={5} unit="/5"
                                            impact="Low"
                                            helpTopic="managementScore"
                                            note="+5% per pt"
                                        />
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>
                </div>

                {/* Right Column (35%): Live Analysis */}
                <div className="lg:col-span-4 flex flex-col gap-2 overflow-y-auto custom-scrollbar">
                    <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-3 h-full backdrop-blur-sm flex flex-col">
                        <h3 className="text-xs font-bold text-white mb-2 uppercase tracking-wider border-b border-slate-800 pb-1 flex justify-between items-center">
                            <span>Live Projections</span>
                            <span className="text-[10px] text-slate-500">{activeScenario} Case</span>
                        </h3>

                        <div className="space-y-2 mb-2 flex-1">
                            <div className="flex justify-between items-center p-2 bg-slate-800/30 rounded-lg">
                                <div className="text-[10px] text-slate-400 uppercase tracking-wide">Revenue (T+5)</div>
                                <div className="text-sm font-bold text-white">
                                    ${((stockData.metrics.revenue || 0) * Math.pow(1 + growthRate / 100, timeHorizon) / 1000000000).toFixed(1)}B
                                </div>
                            </div>
                            <div className="flex justify-between items-center p-2 bg-slate-800/30 rounded-lg">
                                <div className="text-[10px] text-slate-400 uppercase tracking-wide">Net Income (T+5)</div>
                                <div className="text-sm font-bold text-secondary">
                                    ${((stockData.metrics.revenue || 0) * Math.pow(1 + growthRate / 100, timeHorizon) * (netMargin / 100) / 1000000000).toFixed(1)}B
                                </div>
                            </div>
                            <div className="flex justify-between items-center p-2 bg-slate-800/30 rounded-lg border border-indigo-500/20 bg-indigo-500/5">
                                <div className="text-[10px] text-indigo-300 uppercase tracking-wide font-bold">Terminal Value</div>
                                <div className="text-sm font-bold text-indigo-300">
                                    ${(((stockData.metrics.revenue || 0) * Math.pow(1 + growthRate / 100, timeHorizon) * (netMargin / 100) * peRatio) / 1000000000).toFixed(1)}B
                                </div>
                            </div>
                        </div>

                        <div className="mt-auto pt-2 border-t border-slate-800">
                            <h4 className="text-[10px] font-bold text-slate-500 uppercase mb-1.5 flex items-center gap-2">
                                <Table2 size={12} />
                                Target Range
                            </h4>
                            <div className="space-y-1.5">
                                <div className="flex justify-between text-xs items-center group cursor-pointer hover:bg-white/5 p-2 rounded transition-colors" onClick={() => setActiveScenario('bear')}>
                                    <span className="text-red-400 font-bold flex items-center gap-2">
                                        <div className={`w-2 h-2 rounded-full ${activeScenario === 'bear' ? 'bg-red-400 ring-2 ring-red-400/30' : 'bg-red-900'}`}></div>
                                        Bear
                                    </span>
                                    <span className="text-slate-300 font-mono">${Math.round(bearPrice)}</span>
                                </div>
                                <div className="flex justify-between text-xs items-center group cursor-pointer hover:bg-white/5 p-2 rounded transition-colors" onClick={() => setActiveScenario('base')}>
                                    <span className="text-indigo-400 font-bold flex items-center gap-2">
                                        <div className={`w-2 h-2 rounded-full ${activeScenario === 'base' ? 'bg-indigo-400 ring-2 ring-indigo-400/30' : 'bg-indigo-900'}`}></div>
                                        Base
                                    </span>
                                    <span className="text-white font-bold font-mono">${Math.round(basePrice)}</span>
                                </div>
                                <div className="flex justify-between text-xs items-center group cursor-pointer hover:bg-white/5 p-2 rounded transition-colors" onClick={() => setActiveScenario('bull')}>
                                    <span className="text-green-400 font-bold flex items-center gap-2">
                                        <div className={`w-2 h-2 rounded-full ${activeScenario === 'bull' ? 'bg-green-400 ring-2 ring-green-400/30' : 'bg-green-900'}`}></div>
                                        Bull
                                    </span>
                                    <span className="text-slate-300 font-mono">${Math.round(bullPrice)}</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Sensitivity Matrix - Narrow Version */}
                    <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-3 backdrop-blur-sm flex-none">
                        <div className="flex justify-between items-center mb-2">
                            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider flex items-center gap-2">
                                <Table2 size={12} className="text-purple-400" />
                                Sensitivity Matrix
                            </span>
                        </div>
                        <SensitivityMatrix
                            peRatio={peRatio}
                            growthRate={growthRate}
                            stockPrice={stockData.price}
                            calculatePrice={calculatePrice}
                        />
                    </div>
                </div>
            </div>

            {/* Bottom: Removed Sensitivity Matrix Footer */}

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
                onClose={() => { setShowAIModal(false); setViewingProjection(null); }}
                symbol={stockData.symbol}
                initialProjection={viewingProjection}
            />

            {/* CLI Agent Reminder Modal */}
            <AgentReminderModal
                isOpen={showAgentReminder}
                onClose={() => setShowAgentReminder(false)}
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
                    onViewReport={(aiProjection) => {
                        setShowPresetModal(false);
                        setViewingProjection(aiProjection);
                        setShowAIModal(true);
                        const thesis = aiProjection.aiThesis;
                        const base = aiProjection.scenarios?.base;
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
                    }}
                    onClose={() => setShowPresetModal(false)}
                />
            )}
        </div>
    );
}
