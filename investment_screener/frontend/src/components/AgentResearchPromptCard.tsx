/**
 * AgentResearchPromptCard.tsx (React Presentation Component)
 * ==========================================================
 *
 * Purpose:
 *     Prominent, institutional call-to-action card shown on stock analysis screens
 *     when a stock lacks active fundamental research or Technical Analysis sweep data.
 *     Provides 1-click clipboard triggers for agent commands:
 *     - `/guide-valuation {TICKER}` — interactive DCF calibration & scenario alignment
 *     - `/tv-ta-sweep {TICKER}` — TradingView Multi-EMA, Volume Bias & Squeeze sweep
 *     - `/stock-research {TICKER}` — Deep fundamental research & catalyst audit
 *
 * Layer: Frontend / Components / Education
 */

import React, { useState } from 'react';
import { Sparkles, Check, BrainCircuit, Activity, BookOpen, Copy } from 'lucide-react';

interface AgentResearchPromptCardProps {
    symbol: string;
    hasThesis?: boolean;
    hasTechnicals?: boolean;
}

export const AgentResearchPromptCard: React.FC<AgentResearchPromptCardProps> = ({
    symbol,
    hasThesis = false,
    hasTechnicals = false,
}) => {
    const [copiedCmd, setCopiedCmd] = useState<string | null>(null);

    const handleCopy = (cmd: string) => {
        navigator.clipboard.writeText(cmd);
        setCopiedCmd(cmd);
        setTimeout(() => setCopiedCmd(null), 2500);
    };

    if (hasThesis && hasTechnicals) return null;

    return (
        <div className="mb-6 animate-in fade-in slide-in-from-top-4 duration-500">
            <div className="bg-gradient-to-br from-indigo-950/80 via-slate-900/90 to-purple-950/80 border-2 border-indigo-500/40 rounded-2xl p-6 shadow-2xl relative overflow-hidden">
                {/* Glow decorations */}
                <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500"></div>
                <div className="absolute -right-16 -top-16 w-48 h-48 bg-indigo-500/10 blur-3xl rounded-full"></div>

                <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 relative z-10">
                    <div className="space-y-2">
                        <div className="flex items-center gap-2">
                            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 flex items-center gap-1">
                                <Sparkles size={11} className="text-indigo-400" /> AI Agent Research Suite
                            </span>
                            <span className="text-xs text-slate-400 font-medium">No fresh analysis recorded for <strong className="text-white">{symbol}</strong></span>
                        </div>
                        <h2 className="text-xl md:text-2xl font-black text-white tracking-tight">
                            Run Autonomous AI Research & Valuation for {symbol}
                        </h2>
                        <p className="text-sm text-slate-300 max-w-2xl leading-relaxed">
                            To calibrate DCF target prices, calculate Multi-EMA support levels, and synchronize SQLite & JSON data stores, copy and run any of these commands in your agent chat:
                        </p>
                    </div>

                    {/* Command Triggers */}
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 shrink-0">
                        {/* 1. /guide-valuation */}
                        <button
                            onClick={() => handleCopy(`/guide-valuation ${symbol}`)}
                            className="bg-slate-900/80 hover:bg-slate-800/90 border border-indigo-500/40 hover:border-indigo-400 p-3.5 rounded-xl text-left transition-all group shadow-md"
                        >
                            <div className="flex items-center justify-between mb-1.5">
                                <BrainCircuit size={16} className="text-indigo-400" />
                                {copiedCmd === `/guide-valuation ${symbol}` ? (
                                    <span className="text-[10px] font-bold text-emerald-400 flex items-center gap-1">
                                        <Check size={12} /> Copied!
                                    </span>
                                ) : (
                                    <Copy size={12} className="text-slate-500 group-hover:text-slate-300" />
                                )}
                            </div>
                            <div className="font-mono text-xs font-bold text-indigo-300">/guide-valuation</div>
                            <p className="text-[10px] text-slate-400 mt-1">Calibrate DCF sliders & target ranges interactively</p>
                        </button>

                        {/* 2. /tv-ta-sweep */}
                        <button
                            onClick={() => handleCopy(`/tv-ta-sweep ${symbol}`)}
                            className="bg-slate-900/80 hover:bg-slate-800/90 border border-teal-500/40 hover:border-teal-400 p-3.5 rounded-xl text-left transition-all group shadow-md"
                        >
                            <div className="flex items-center justify-between mb-1.5">
                                <Activity size={16} className="text-teal-400" />
                                {copiedCmd === `/tv-ta-sweep ${symbol}` ? (
                                    <span className="text-[10px] font-bold text-emerald-400 flex items-center gap-1">
                                        <Check size={12} /> Copied!
                                    </span>
                                ) : (
                                    <Copy size={12} className="text-slate-500 group-hover:text-slate-300" />
                                )}
                            </div>
                            <div className="font-mono text-xs font-bold text-teal-300">/tv-ta-sweep</div>
                            <p className="text-[10px] text-slate-400 mt-1">Extract 21/50/200 EMAs, ADX & Volume Bias</p>
                        </button>

                        {/* 3. /stock-research */}
                        <button
                            onClick={() => handleCopy(`/stock-research ${symbol}`)}
                            className="bg-slate-900/80 hover:bg-slate-800/90 border border-purple-500/40 hover:border-purple-400 p-3.5 rounded-xl text-left transition-all group shadow-md"
                        >
                            <div className="flex items-center justify-between mb-1.5">
                                <BookOpen size={16} className="text-purple-400" />
                                {copiedCmd === `/stock-research ${symbol}` ? (
                                    <span className="text-[10px] font-bold text-emerald-400 flex items-center gap-1">
                                        <Check size={12} /> Copied!
                                    </span>
                                ) : (
                                    <Copy size={12} className="text-slate-500 group-hover:text-slate-300" />
                                )}
                            </div>
                            <div className="font-mono text-xs font-bold text-purple-300">/stock-research</div>
                            <p className="text-[10px] text-slate-400 mt-1">Deep fundamental thesis & catalyst report</p>
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};
