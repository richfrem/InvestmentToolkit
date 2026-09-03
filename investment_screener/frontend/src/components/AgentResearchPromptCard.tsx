/**
 * AgentResearchPromptCard.tsx (React Presentation Component)
 * ==========================================================
 *
 * Purpose:
 *     Prominent, institutional call-to-action card shown on stock analysis screens
 *     when a stock lacks active fundamental research or Technical Analysis sweep data.
 *     Features a single 1-shot master command `/update-stock-analysis {TICKER}`.
 *
 * Layer: Frontend / Components / Education
 */

import React, { useState } from 'react';
import { Sparkles, Check } from 'lucide-react';

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
                    <div className="space-y-3">
                        <div className="flex items-center gap-2">
                            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 flex items-center gap-1">
                                <Sparkles size={11} className="text-emerald-400" /> One-Click Complete Analysis
                            </span>
                            <span className="text-xs text-slate-400 font-medium">No saved model yet for <strong className="text-white">{symbol}</strong></span>
                        </div>
                        <h2 className="text-xl md:text-2xl font-black text-white tracking-tight">
                            Run All-in-One Valuation & Technicals for {symbol}
                        </h2>
                        <p className="text-sm text-slate-300 max-w-2xl leading-relaxed">
                            Run a single master command in your agent chat to perform fundamentals research, extract TradingView technical levels, and calibrate DCF target prices in one shot:
                        </p>
                    </div>

                    {/* Master 1-Shot Command Trigger */}
                    <div className="flex flex-col sm:flex-row items-stretch gap-3 shrink-0">
                        <button
                            onClick={() => handleCopy(`/stock-intake ${symbol}`)}
                            className="bg-gradient-to-r from-emerald-600 via-teal-600 to-indigo-600 hover:from-emerald-500 hover:to-indigo-500 text-white font-bold p-4 rounded-xl text-left transition-all shadow-xl hover:shadow-emerald-500/20 border border-emerald-400/40 flex items-center gap-4 group cursor-pointer"
                        >
                            <div className="p-2.5 bg-black/30 rounded-lg">
                                <Sparkles size={22} className="text-emerald-300 group-hover:scale-110 transition-transform" />
                            </div>
                            <div>
                                <div className="text-[10px] uppercase font-black text-emerald-200 tracking-wider flex items-center gap-1">
                                    {copiedCmd === `/stock-intake ${symbol}` ? (
                                        <span className="text-white flex items-center gap-1"><Check size={12} /> Copied to Clipboard!</span>
                                    ) : (
                                        <span>Master 5-in-1 Pipeline (Click to Copy)</span>
                                    )}
                                </div>
                                <div className="font-mono text-base font-black text-white mt-0.5">/stock-intake {symbol}</div>
                                <p className="text-[11px] text-emerald-100/80 mt-0.5">Financials + TradingView TA + DCF Scenarios + Intelligence DB in 1 shot</p>
                            </div>
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};
