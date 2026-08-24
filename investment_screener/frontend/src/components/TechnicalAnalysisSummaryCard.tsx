/**
 * TechnicalAnalysisSummaryCard.tsx (React Presentation Component)
 * =================================================================
 *
 * Purpose:
 *     Institutional-grade Technical Analysis summary card for the Stock Analysis page.
 *     Translates Multi-EMA alignment, ADX trend velocity, Volume Bias %, and Squeeze signals
 *     into clear, plain-English action recommendations for both holdings and non-holdings.
 *     Integrates with SmartText to provide 1-click educational help modals for unfamiliar TA terms.
 *
 * Layer: Frontend / Components / Analysis
 */

import React from 'react';
import { Activity, ShieldAlert, TrendingUp, TrendingDown, Layers, Zap, Compass, CheckCircle2, AlertCircle } from 'lucide-react';
import type { TechnicalAnalysisData } from '../services/api';
import { SmartText } from './SmartText';

interface TechnicalAnalysisSummaryCardProps {
    data: TechnicalAnalysisData;
    currentPrice?: number;
}

export const TechnicalAnalysisSummaryCard: React.FC<TechnicalAnalysisSummaryCardProps> = ({ data, currentPrice }) => {
    const { technicalAction, regime, rationale, keyLevels, metrics, effectiveAt } = data;
    const livePrice = currentPrice || data.price;

    const getActionBadge = (action: string) => {
        switch (action) {
            case 'ACCUMULATE':
                return {
                    bg: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
                    icon: <TrendingUp className="w-4 h-4 text-emerald-400" />,
                    label: 'ACCUMULATE (BUY SUPPORT)',
                };
            case 'INITIATE':
                return {
                    bg: 'bg-teal-500/10 text-teal-400 border-teal-500/30',
                    icon: <CheckCircle2 className="w-4 h-4 text-teal-400" />,
                    label: 'INITIATE POSITION',
                };
            case 'MAINTAIN':
                return {
                    bg: 'bg-sky-500/10 text-sky-400 border-sky-500/30',
                    icon: <Layers className="w-4 h-4 text-sky-400" />,
                    label: 'MAINTAIN / HOLD',
                };
            case 'TRIM':
                return {
                    bg: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
                    icon: <TrendingDown className="w-4 h-4 text-amber-400" />,
                    label: 'TRIM (TAKE PROFIT)',
                };
            case 'EXIT':
                return {
                    bg: 'bg-rose-500/10 text-rose-400 border-rose-500/30',
                    icon: <AlertCircle className="w-4 h-4 text-rose-400" />,
                    label: 'EXIT / STOP OUT',
                };
            case 'AVOID':
                return {
                    bg: 'bg-red-500/10 text-red-400 border-red-500/30',
                    icon: <ShieldAlert className="w-4 h-4 text-red-400" />,
                    label: 'AVOID (DOWNTREND)',
                };
            default:
                return {
                    bg: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/30',
                    icon: <Compass className="w-4 h-4 text-indigo-400" />,
                    label: 'WATCHLIST / MONITOR',
                };
        }
    };

    const getRegimeLabel = (reg: string) => {
        switch (reg) {
            case 'BULLISH_TREND':
                return { label: 'Bullish Trend', color: 'text-emerald-400 bg-emerald-950/40 border-emerald-800/40' };
            case 'BULLISH_CONSOLIDATION':
                return { label: 'Bullish Consolidation', color: 'text-teal-400 bg-teal-950/40 border-teal-800/40' };
            case 'COMPRESSION':
                return { label: 'TTM Squeeze (Compression)', color: 'text-indigo-400 bg-indigo-950/40 border-indigo-800/40' };
            case 'DISTRIBUTION':
                return { label: 'Distribution Pressure', color: 'text-amber-400 bg-amber-950/40 border-amber-800/40' };
            case 'BEARISH_TREND':
                return { label: 'Bearish Downtrend', color: 'text-rose-400 bg-rose-950/40 border-rose-800/40' };
            default:
                return { label: 'Consolidation', color: 'text-slate-300 bg-slate-900 border-slate-700' };
        }
    };

    const badge = getActionBadge(technicalAction);
    const regimeBadge = getRegimeLabel(regime);

    return (
        <div className="mb-6 bg-gradient-to-br from-slate-900/90 via-slate-950/90 to-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-xl relative overflow-hidden backdrop-blur-sm">
            {/* Top decorative gradient bar */}
            <div className="absolute top-0 left-0 w-full h-0.5 bg-gradient-to-r from-teal-500 via-indigo-500 to-amber-500 opacity-70" />

            {/* Header: Title + Action Badges */}
            <div className="flex flex-wrap items-center justify-between gap-4 mb-4 pb-4 border-b border-slate-800/70">
                <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-teal-500/10 text-teal-400 border border-teal-500/20 shadow-inner">
                        <Activity className="w-5 h-5" />
                    </div>
                    <div>
                        <div className="flex items-center gap-2">
                            <h3 className="text-base font-bold text-white tracking-wide">Technical Analysis Summary</h3>
                            <span className={`text-[10px] px-2.5 py-0.5 rounded-full font-semibold border ${regimeBadge.color}`}>
                                {regimeBadge.label}
                            </span>
                        </div>
                        <p className="text-[10px] text-slate-500 uppercase tracking-wider mt-0.5">
                            Institutional Multi-EMA & Momentum Flow · As of {effectiveAt}
                        </p>
                    </div>
                </div>

                <div className="flex items-center gap-3">
                    <div className={`px-3 py-1.5 rounded-lg border text-xs font-bold flex items-center gap-2 shadow-sm ${badge.bg}`}>
                        {badge.icon}
                        <span>{badge.label}</span>
                    </div>
                </div>
            </div>

            {/* Plain-English Executive Summary with SmartText Links */}
            <div className="mb-5 bg-slate-900/60 rounded-lg p-3.5 border border-slate-800/60 text-xs text-slate-300 leading-relaxed shadow-inner">
                <div className="flex items-start gap-2.5">
                    <Zap className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                    <div>
                        <span className="font-semibold text-white mr-1.5">Executive Technical Setup:</span>
                        <SmartText text={rationale} className="text-slate-300" />
                    </div>
                </div>
            </div>

            {/* 3-Column Actionable Key Levels */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-5">
                {/* 1. Support / Accumulation Shelf */}
                <div className="bg-slate-950/60 border border-slate-800/80 rounded-xl p-3.5 flex flex-col justify-between">
                    <div>
                        <div className="flex items-center justify-between mb-2">
                            <span className="text-xs font-bold text-emerald-400 flex items-center gap-1.5">
                                <TrendingDown className="w-3.5 h-3.5" /> Accumulation & Support
                            </span>
                            <span className="text-[10px] text-slate-500 uppercase">Dip Buy Shelf</span>
                        </div>
                        <div className="space-y-2 mt-2">
                            <div className="flex justify-between items-center bg-slate-900/50 px-2.5 py-1.5 rounded border border-slate-800/50">
                                <span className="text-[11px] text-slate-400 flex items-center gap-1">
                                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" /> 21 EMA (Dynamic Pivot)
                                </span>
                                <span className="text-xs font-bold text-emerald-400">${keyLevels.support1.toFixed(2)}</span>
                            </div>
                            <div className="flex justify-between items-center bg-slate-900/50 px-2.5 py-1.5 rounded border border-slate-800/50">
                                <span className="text-[11px] text-slate-400 flex items-center gap-1">
                                    <span className="w-1.5 h-1.5 rounded-full bg-teal-400" /> 50 EMA (Trend Floor)
                                </span>
                                <span className="text-xs font-bold text-teal-300">${keyLevels.support2.toFixed(2)}</span>
                            </div>
                        </div>
                    </div>
                    <p className="text-[10px] text-slate-500 mt-2.5 pt-2 border-t border-slate-800/40">
                        Macro Floor (200 EMA): <strong className="text-slate-300">${keyLevels.macroFloor.toFixed(2)}</strong>
                    </p>
                </div>

                {/* 2. Resistance / Profit Targets */}
                <div className="bg-slate-950/60 border border-slate-800/80 rounded-xl p-3.5 flex flex-col justify-between">
                    <div>
                        <div className="flex items-center justify-between mb-2">
                            <span className="text-xs font-bold text-indigo-400 flex items-center gap-1.5">
                                <TrendingUp className="w-3.5 h-3.5" /> Staged Take-Profit Tiers
                            </span>
                            <span className="text-[10px] text-slate-500 uppercase">Trim Targets</span>
                        </div>
                        <div className="space-y-2 mt-2">
                            {keyLevels.profitTiers && keyLevels.profitTiers.length > 0 ? (
                                keyLevels.profitTiers.map((tier) => (
                                    <div key={tier.tier} className="flex justify-between items-center bg-slate-900/50 px-2.5 py-1.5 rounded border border-slate-800/50">
                                        <div className="flex flex-col">
                                            <span className="text-[11px] text-slate-300 font-semibold flex items-center gap-1">
                                                <span className={`w-1.5 h-1.5 rounded-full ${tier.tier === 1 ? 'bg-indigo-400' : tier.tier === 2 ? 'bg-purple-400' : 'bg-pink-400'}`} />
                                                Tier {tier.tier} Trim (-{tier.trimPct}%)
                                            </span>
                                            <span className="text-[9px] text-slate-500">{tier.basis}</span>
                                        </div>
                                        <div className="text-right">
                                            <span className="text-xs font-bold text-indigo-300">${tier.price.toFixed(2)}</span>
                                            <span className="text-[10px] text-emerald-400 block font-medium">+{tier.gainPct}%</span>
                                        </div>
                                    </div>
                                ))
                            ) : (
                                <>
                                    <div className="flex justify-between items-center bg-slate-900/50 px-2.5 py-1.5 rounded border border-slate-800/50">
                                        <span className="text-[11px] text-slate-400 flex items-center gap-1">
                                            <span className="w-1.5 h-1.5 rounded-full bg-indigo-400" /> Tier 1 Tactical Trim (-20%)
                                        </span>
                                        <span className="text-xs font-bold text-indigo-300">${keyLevels.resistance1.toFixed(2)}</span>
                                    </div>
                                    <div className="flex justify-between items-center bg-slate-900/50 px-2.5 py-1.5 rounded border border-slate-800/50">
                                        <span className="text-[11px] text-slate-400 flex items-center gap-1">
                                            <span className="w-1.5 h-1.5 rounded-full bg-purple-400" /> Tier 2 Base Trim (-30%)
                                        </span>
                                        <span className="text-xs font-bold text-purple-300">${(keyLevels.baseTarget || keyLevels.resistance2).toFixed(2)}</span>
                                    </div>
                                </>
                            )}
                        </div>
                    </div>
                    <p className="text-[10px] text-slate-500 mt-2.5 pt-2 border-t border-slate-800/40">
                        Immediate Target 1 Upside: <strong className="text-emerald-400">+{(((keyLevels.resistance1 - livePrice) / livePrice) * 100).toFixed(1)}%</strong>
                    </p>
                </div>

                {/* 3. Stop Loss / Invalidation */}
                <div className="bg-slate-950/60 border border-slate-800/80 rounded-xl p-3.5 flex flex-col justify-between">
                    <div>
                        <div className="flex items-center justify-between mb-2">
                            <span className="text-xs font-bold text-rose-400 flex items-center gap-1.5">
                                <ShieldAlert className="w-3.5 h-3.5" /> Stop Loss & Risk Threshold
                            </span>
                            <span className="text-[10px] text-slate-500 uppercase">Structural Risk</span>
                        </div>
                        <div className="space-y-2 mt-2">
                            <div className="flex justify-between items-center bg-slate-900/50 px-2.5 py-1.5 rounded border border-slate-800/50">
                                <span className="text-[11px] text-slate-400 flex items-center gap-1">
                                    <span className="w-1.5 h-1.5 rounded-full bg-rose-500" /> Stop Loss Limit
                                </span>
                                <span className="text-xs font-bold text-rose-400">${keyLevels.stopLoss.toFixed(2)}</span>
                            </div>
                            <div className="flex justify-between items-center bg-slate-900/50 px-2.5 py-1.5 rounded border border-slate-800/50">
                                <span className="text-[11px] text-slate-400 flex items-center gap-1">
                                    <span className="w-1.5 h-1.5 rounded-full bg-amber-400" /> Expected Daily ATR
                                </span>
                                <span className="text-xs font-bold text-amber-300">±${keyLevels.atrExpectedSwing.toFixed(2)}</span>
                            </div>
                        </div>
                    </div>
                    <p className="text-[10px] text-slate-500 mt-2.5 pt-2 border-t border-slate-800/40">
                        Risk Buffer from Price: <strong className="text-rose-400">{(((livePrice - keyLevels.stopLoss) / livePrice) * 100).toFixed(1)}%</strong>
                    </p>
                </div>
            </div>

            {/* Bottom Quick-Metric Gauges Strip */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-3 border-t border-slate-800/60">
                <div className="bg-slate-900/40 p-2.5 rounded-lg border border-slate-800/50 text-center">
                    <div className="text-[10px] text-slate-500 font-medium">Trend Strength (ADX)</div>
                    <div className="text-sm font-bold text-white mt-0.5 flex items-center justify-center gap-1">
                        <span>{metrics.adx}</span>
                        <span className="text-[10px] text-slate-500">
                            {metrics.adx >= 25 ? '(Strong)' : '(Ranging)'}
                        </span>
                    </div>
                </div>

                <div className="bg-slate-900/40 p-2.5 rounded-lg border border-slate-800/50 text-center">
                    <div className="text-[10px] text-slate-500 font-medium">Volume Flow Bias</div>
                    <div className={`text-sm font-bold mt-0.5 ${metrics.volBias >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                        {metrics.volBias >= 0 ? `+${metrics.volBias}%` : `${metrics.volBias}%`}
                    </div>
                </div>

                <div className="bg-slate-900/40 p-2.5 rounded-lg border border-slate-800/50 text-center">
                    <div className="text-[10px] text-slate-500 font-medium">RSI (14-Day)</div>
                    <div className={`text-sm font-bold mt-0.5 ${metrics.rsi >= 70 ? 'text-rose-400' : metrics.rsi <= 30 ? 'text-emerald-400' : 'text-sky-300'}`}>
                        {metrics.rsi}
                    </div>
                </div>

                <div className="bg-slate-900/40 p-2.5 rounded-lg border border-slate-800/50 text-center">
                    <div className="text-[10px] text-slate-500 font-medium">Volatility Squeeze</div>
                    <div className="text-sm font-bold mt-0.5 flex items-center justify-center gap-1">
                        {metrics.isSqueeze ? (
                            <span className="text-amber-400 flex items-center gap-1">
                                <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" /> Squeeze ON
                            </span>
                        ) : (
                            <span className="text-slate-400">Normal Range</span>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};
