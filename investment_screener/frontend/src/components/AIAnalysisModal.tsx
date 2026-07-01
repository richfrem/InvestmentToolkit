/**
 * AIAnalysisModal.tsx (React Component)
 * =====================================
 *
 * Purpose:
 *     Modal component for displaying deep AI analysis and projections for a specific stock.
 *
 * Layer: Frontend / UI / Modals
 *
 * Usage Examples:
 *     <AIAnalysisModal isOpen={true} onClose={() => {}} symbol="AAPL" />
 *
 * Key Functions:
 *     - loadAIProjection() - Fetches and filters AI-specific DCF projections
 *     - handlePresetChange() - Manages switching between different valuation scenarios
 */
import React, { useEffect, useState } from 'react';
import { X, BrainCircuit, TrendingUp, TrendingDown, AlertTriangle, BookOpen } from 'lucide-react';
import { type Projection, fetchProjections } from '../services/api';
import { SmartText } from './SmartText';
import { HelpTrigger } from './HelpModal';
import { DeepDiveModal } from './DeepDiveModal';
import { getActionBadgeClass } from '../utils/actionColors';

interface AIAnalysisModalProps {
    symbol: string;
    onClose: () => void;
    isOpen: boolean;
    initialProjection?: Projection | null; // Added prop
}

export const AIAnalysisModal: React.FC<AIAnalysisModalProps> = ({ symbol, onClose, isOpen, initialProjection }) => {
    const [projection, setProjection] = useState<Projection | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [deepDiveFile, setDeepDiveFile] = useState<string | null>(null);

    useEffect(() => {
        if (isOpen) {
            if (initialProjection) {
                setProjection(initialProjection);
                setLoading(false);
                setError(null);
            } else if (symbol) {
                loadAIProjection();
            }
        }
    }, [isOpen, symbol, initialProjection]);

    const loadAIProjection = async () => {
        setLoading(true);
        setError(null);
        try {
            const projections = await fetchProjections(symbol);
            if (!projections) {
                setError("Failed to load projections.");
                return;
            }

            // Find the latest AI_AGENT projection
            const aiProjections = projections.filter(p => p.source === 'AI_AGENT');
            if (aiProjections.length === 0) {
                setError("No AI analysis found for this stock. Run the AI Analyst first.");
                setProjection(null);
            } else {
                // Sort by savedAt descending (newest first)
                aiProjections.sort((a, b) => new Date(b.savedAt).getTime() - new Date(a.savedAt).getTime());
                setProjection(aiProjections[0]);
            }
        } catch (err) {
            setError("An unexpected error occurred.");
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 animate-in fade-in duration-200">
            <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col shadow-2xl animate-in zoom-in-95 duration-200">

                {/* Header */}
                <div className="flex-none p-4 border-b border-slate-800 flex justify-between items-center bg-slate-900/50">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-indigo-500/20 rounded-lg text-indigo-400">
                            <BrainCircuit size={24} />
                        </div>
                        <div>
                            <h2 className="text-xl font-bold text-white flex items-center gap-2">
                                AI Investment Thesis
                                <span className="text-xs font-normal text-slate-400 bg-slate-800 px-2 py-0.5 rounded-full border border-slate-700">
                                    {symbol}
                                </span>
                            </h2>
                            <p className="text-xs text-indigo-300 font-medium">
                                Autonomous Analyst Report • {projection ? new Date(projection.savedAt).toLocaleDateString() : 'Loading...'}
                            </p>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 hover:bg-slate-800 rounded-full text-slate-400 hover:text-white transition-colors"
                    >
                        <X size={20} />
                    </button>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto p-6 custom-scrollbar">
                    {loading ? (
                        <div className="flex flex-col items-center justify-center h-64 gap-4">
                            <div className="w-12 h-12 border-4 border-indigo-500/30 border-t-indigo-500 rounded-full animate-spin"></div>
                            <p className="text-slate-400 animate-pulse">Retrieving intelligent analysis...</p>
                        </div>
                    ) : error ? (
                        <div className="flex flex-col items-center justify-center h-64 gap-3 text-center">
                            <div className="p-3 bg-red-500/10 rounded-full text-red-400">
                                <AlertTriangle size={32} />
                            </div>
                            <p className="text-slate-300 font-medium">{error}</p>
                            <button
                                onClick={onClose}
                                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg text-sm text-white transition-colors"
                            >
                                Close
                            </button>
                        </div>
                    ) : projection && (
                        <div className="space-y-6">

                            {/* Top Stats Row */}
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                {(() => {
                                    const action = projection.aiThesis?.action ?? '—';
                                    const valuationAction = (projection as any).analyticsLog?.valuationAction as string | undefined;
                                    const portfolioUrgency = (projection as any).analyticsLog?.portfolioUrgency as string | undefined;
                                    const urgencyColors: Record<string, string> = {
                                        URGENT: 'text-red-400 bg-red-500/10 border-red-500/30',
                                        NORMAL: 'text-slate-400 bg-slate-500/10 border-slate-500/30',
                                        LOW:    'text-slate-500 bg-slate-800/40 border-slate-700/30',
                                    };
                                    const badgeCls = getActionBadgeClass(action);
                                    // Split combined badge class into bg+border (for card) and text (for label)
                                    const cardBg = badgeCls.match(/bg-\S+/)?.[0] ?? 'bg-slate-500/10';
                                    const cardBorder = badgeCls.match(/border-\S+/)?.[0] ?? 'border-slate-500/30';
                                    const cardText = badgeCls.match(/text-\S+/)?.[0] ?? 'text-slate-300';
                                    return (
                                        <div className={`p-4 rounded-xl border flex flex-col items-center justify-center text-center ${cardBg} ${cardBorder}`}>
                                            <span className="text-xs font-bold uppercase tracking-wider opacity-70 mb-1">Recommendation</span>
                                            <span className={`text-3xl font-black ${cardText}`}>{action}</span>
                                            <div className="flex items-center gap-2 mt-2 flex-wrap justify-center">
                                                {valuationAction && (
                                                    <span className="text-[9px] px-2 py-0.5 rounded-full border border-slate-600/40 bg-slate-800/60 text-slate-400 font-bold uppercase tracking-wider">
                                                        DCF: {valuationAction}
                                                    </span>
                                                )}
                                                {portfolioUrgency && (
                                                    <span className={`text-[9px] px-2 py-0.5 rounded-full border font-bold uppercase tracking-wider ${urgencyColors[portfolioUrgency] ?? ''}`}>
                                                        {portfolioUrgency}
                                                    </span>
                                                )}
                                            </div>
                                        </div>
                                    );
                                })()}


                                <div className="p-4 rounded-xl bg-slate-800/50 border border-slate-700 flex flex-col items-center justify-center text-center">
                                    <span className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-1 flex items-center gap-1">
                                        Fair Value
                                        <HelpTrigger topicId="fairValue" size={12} />
                                    </span>
                                    <span className="text-3xl font-black text-white">
                                        ${projection.aiThesis?.fairValue?.toFixed(2) || '---'}
                                    </span>
                                    {projection.aiThesis?.fairValue && projection.snapshot?.price && (
                                        <div className={`text-xs font-bold mt-1 ${projection.aiThesis.fairValue > projection.snapshot.price
                                            ? 'text-green-400'
                                            : 'text-red-400'
                                            }`}>
                                            {((projection.aiThesis.fairValue - projection.snapshot.price) / projection.snapshot.price * 100).toFixed(1)}% Upside
                                        </div>
                                    )}
                                </div>

                                <div className="p-4 rounded-xl bg-slate-800/50 border border-slate-700 flex flex-col items-center justify-center text-center">
                                    <span className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-1">Configuration</span>
                                    <div className="flex flex-col gap-1 text-xs text-slate-300">
                                        <span>Model: <span className="text-indigo-300">{projection.aiThesis?.model || 'Unknown'}</span></span>
                                        <span>Horizon: {projection.globalSettings.timeHorizon} Years</span>
                                        <span>Discount Rate: {projection.globalSettings.discountRate}%</span>
                                    </div>
                                </div>
                            </div>

                            {/* Executive Summary */}
                            <div className="bg-slate-800/30 border border-slate-700 rounded-xl p-5">
                                <h3 className="text-sm font-bold text-white mb-3 flex items-center gap-2">
                                    <span className="w-1 h-4 bg-indigo-500 rounded-full"></span>
                                    Executive Thesis
                                </h3>
                                <SmartText text={projection.rationale || ""} className="text-slate-300" />
                            </div>

                            {/* Scenarios Table */}
                            <div className="bg-slate-800/30 border border-slate-700 rounded-xl overflow-hidden">
                                <div className="px-5 py-3 border-b border-slate-700 bg-slate-800/50">
                                    <h3 className="text-sm font-bold text-white flex items-center gap-2">
                                        <span className="w-1 h-4 bg-purple-500 rounded-full"></span>
                                        Scenario Analysis
                                    </h3>
                                </div>
                                <div className="overflow-x-auto">
                                    <table className="w-full text-left text-sm">
                                        <thead>
                                            <tr className="border-b border-slate-700 text-slate-400 text-xs uppercase tracking-wider">
                                                <th className="px-5 py-3 font-medium">Scenario</th>
                                                <th className="px-5 py-3 font-medium text-right">Probability</th>
                                                <th className="px-5 py-3 font-medium text-right">Target Price</th>
                                                <th className="px-5 py-3 font-medium text-right">Implied Upside</th>
                                                <th className="px-5 py-3 font-medium text-right">Rev CAGR</th>
                                                <th className="px-5 py-3 font-medium text-right">Net Margin</th>
                                                <th className="px-5 py-3 font-medium text-right">Exit P/E</th>
                                                <th className="px-5 py-3 font-medium">Key Driver</th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-slate-700/50">
                                            {(['bear', 'base', 'bull'] as const).map(type => {
                                                const s = projection.scenarios[type];
                                                const isBear = type === 'bear';
                                                const isBull = type === 'bull';

                                                // Calculate Price (Global Settings + Scenario Assumptions)
                                                const qualityMultiplier = s.qualityMultiplier ?? 1.0;
                                                const shareChange = s.shareChange ?? 0;
                                                const timeHorizon = projection.globalSettings.timeHorizon;
                                                const discountRate = projection.globalSettings.discountRate;

                                                // 1. Future Revenue
                                                const currentRevenue = projection.snapshot.revenue || 0;
                                                const futureRevenue = currentRevenue * Math.pow(1 + s.growthRate / 100, timeHorizon);

                                                // 2. Future Net Income
                                                const futureNetIncome = futureRevenue * (s.netMargin / 100);

                                                // 3. Future Market Cap
                                                const futureMarketCap = futureNetIncome * s.exitPE * qualityMultiplier;

                                                // 4. Future Share Count
                                                const currentShares = projection.snapshot.shares || 1;
                                                const futureShares = currentShares * Math.pow(1 + shareChange / 100, timeHorizon);

                                                // 5. Future Price
                                                const futurePrice = futureShares > 0 ? futureMarketCap / futureShares : 0;

                                                // 6. Discount to PV
                                                const targetPrice = futurePrice / Math.pow(1 + discountRate / 100, timeHorizon);

                                                // 7. Upside
                                                const currentPrice = projection.snapshot.price || 0;
                                                const upside = currentPrice > 0 ? ((targetPrice - currentPrice) / currentPrice) * 100 : 0;

                                                const rowClass = isBear ? 'bg-red-500/5 hover:bg-red-500/10' :
                                                    isBull ? 'bg-green-500/5 hover:bg-green-500/10' :
                                                        'hover:bg-slate-800/50';
                                                const textClass = isBear ? 'text-red-400' : isBull ? 'text-green-400' : 'text-slate-300';

                                                return (
                                                    <tr key={type} className={`transition-colors ${rowClass}`}>
                                                        <td className="px-5 py-4 font-bold capitalize text-white flex items-center gap-2">
                                                            {isBear && <TrendingDown size={14} className="text-red-400" />}
                                                            {isBull && <TrendingUp size={14} className="text-green-400" />}
                                                            {!isBear && !isBull && <div className="w-3.5" />}
                                                            {type}
                                                        </td>
                                                        <td className="px-5 py-4 text-right font-medium text-slate-300">
                                                            {(s.weight * 100).toFixed(0)}%
                                                        </td>
                                                        <td className="px-5 py-4 text-right font-black text-white">
                                                            ${targetPrice.toFixed(2)}
                                                        </td>
                                                        <td className={`px-5 py-4 text-right font-bold ${upside >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                                            {upside > 0 ? '+' : ''}{upside.toFixed(1)}%
                                                        </td>
                                                        <td className={`px-5 py-4 text-right font-bold ${textClass}`}>
                                                            {s.growthRate}%
                                                        </td>
                                                        <td className="px-5 py-4 text-right text-slate-300">
                                                            {s.netMargin}%
                                                        </td>
                                                        <td className="px-5 py-4 text-right text-slate-300">
                                                            {s.exitPE}x
                                                        </td>
                                                        <td className="px-5 py-4 text-xs text-slate-400 max-w-xs truncate" title={s.rationale}>
                                                            {s.rationale}
                                                        </td>
                                                    </tr>
                                                );
                                            })}
                                        </tbody>
                                    </table>
                                </div>
                            </div>

                            {/* Portfolio Rationale */}
                            {(projection as any).analyticsLog?.portfolioRationale && (
                                <div className="bg-slate-800/30 border border-slate-700 rounded-xl p-5">
                                    <h3 className="text-sm font-bold text-white mb-2 flex items-center gap-2">
                                        <span className="w-1 h-4 bg-amber-500 rounded-full"></span>
                                        Portfolio Action Rationale
                                    </h3>
                                    <p className="text-sm text-slate-300 leading-relaxed">
                                        {(projection as any).analyticsLog.portfolioRationale}
                                    </p>
                                </div>
                            )}

                            {/* TA Price Levels */}
                            {projection.taLevels && (
                                <div className="bg-slate-800/30 border border-slate-700 rounded-xl p-5">
                                    <h3 className="text-sm font-bold text-white mb-3 flex items-center gap-2">
                                        <span className="w-1 h-4 bg-cyan-500 rounded-full"></span>
                                        TA Price Levels
                                        <span className="text-xs font-normal text-slate-500 ml-auto">
                                            {projection.taLevels.signal} · score {projection.taLevels.score > 0 ? '+' : ''}{projection.taLevels.score} · {projection.taLevels.date}
                                        </span>
                                    </h3>
                                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
                                        {projection.taLevels.priceLevels.stopLoss != null && (
                                            <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/25 text-center">
                                                <div className="text-[10px] font-bold text-red-400 uppercase tracking-wider mb-1">Stop / Exit</div>
                                                <div className="text-lg font-black text-red-300">${projection.taLevels.priceLevels.stopLoss}</div>
                                            </div>
                                        )}
                                        {projection.taLevels.priceLevels.trimAt != null && (
                                            <div className="p-3 rounded-lg bg-orange-500/10 border border-orange-500/25 text-center">
                                                <div className="text-[10px] font-bold text-orange-400 uppercase tracking-wider mb-1">Trim At</div>
                                                <div className="text-lg font-black text-orange-300">${projection.taLevels.priceLevels.trimAt}</div>
                                            </div>
                                        )}
                                        {projection.taLevels.priceLevels.holdLo != null && projection.taLevels.priceLevels.holdHi != null && (
                                            <div className="p-3 rounded-lg bg-yellow-500/10 border border-yellow-500/25 text-center">
                                                <div className="text-[10px] font-bold text-yellow-400 uppercase tracking-wider mb-1">Hold Zone</div>
                                                <div className="text-sm font-black text-yellow-300">${projection.taLevels.priceLevels.holdLo}–${projection.taLevels.priceLevels.holdHi}</div>
                                            </div>
                                        )}
                                        <div className="p-3 rounded-lg bg-green-500/10 border border-green-500/25 text-center">
                                            <div className="text-[10px] font-bold text-green-400 uppercase tracking-wider mb-1">Accumulate At</div>
                                            <div className="text-lg font-black text-green-300">
                                                {projection.taLevels.priceLevels.accumulateAt != null
                                                    ? `$${projection.taLevels.priceLevels.accumulateAt}`
                                                    : <span className="text-sm text-slate-500">Not yet</span>
                                                }
                                            </div>
                                        </div>
                                    </div>
                                    {projection.taLevels.notes && (
                                        <p className="text-xs text-slate-400 italic">{projection.taLevels.notes}</p>
                                    )}
                                </div>
                            )}

                            {/* AI Rationale / Deep Dive */}
                            {projection.aiThesis?.rationale && projection.aiThesis.rationale !== projection.rationale && (
                                <div className="bg-indigo-900/10 border border-indigo-500/20 rounded-xl p-5">
                                    <h3 className="text-sm font-bold text-indigo-300 mb-2 flex items-center gap-2">
                                        <BrainCircuit size={16} />
                                        Deep Dive Notes
                                    </h3>
                                    <p className="text-sm text-indigo-200/80 leading-relaxed italic">
                                        "<SmartText text={projection.aiThesis.rationale} />"
                                    </p>
                                </div>
                            )}

                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="p-4 border-t border-slate-800 bg-slate-900/50 flex justify-between items-center">
                    <span className="text-xs text-slate-500">
                        Generated by Agentic AI • Investment Toolkit
                    </span>
                    <div className="flex items-center gap-3">
                        {projection?.aiThesis?.researchReport && (
                            <button
                                onClick={() => setDeepDiveFile(projection.aiThesis!.researchReport!)}
                                className="px-4 py-2 bg-purple-900/30 hover:bg-purple-800/40 text-purple-300 border border-purple-500/30 hover:border-purple-400/50 font-bold rounded-lg transition-colors text-sm flex items-center gap-2"
                            >
                                <BookOpen size={14} />
                                Deep Dive
                            </button>
                        )}
                        <button
                            onClick={onClose}
                            className="px-6 py-2 bg-white text-slate-900 font-bold rounded-lg hover:bg-slate-200 transition-colors text-sm"
                        >
                            Done
                        </button>
                    </div>
                </div>
            </div>

            {/* Deep Dive Modal */}
            <DeepDiveModal
                isOpen={!!deepDiveFile}
                onClose={() => setDeepDiveFile(null)}
                filename={deepDiveFile}
            />
        </div>
    );
};
