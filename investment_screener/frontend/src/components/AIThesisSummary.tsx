/**
 * AIThesisSummary.tsx (React Component)
 * =====================================
 *
 * Purpose:
 *     Displays a summary of the AI-generated investment thesis with markdown support.
 *
 * Layer: Frontend / UI / Components
 *
 * Usage Examples:
 *     <AIThesisSummary 
 *         aiResult={result} 
 *         onViewFullReport={() => {}} 
 *         onClose={() => {}} 
 *     />
 *
 * Key Functions:
 *     - AIThesisSummary() - Functional component managing loading, error, and rendering of the AI rationale markdown
 */
import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { BrainCircuit, FolderOpen, X, AlertTriangle, Loader2, Sparkles, Check, Clock } from 'lucide-react';
import { getActionBadgeClass } from '../utils/actionColors';

interface AIThesisSummaryProps {
    aiResult: any;
    isAnalyzing?: boolean;
    aiError?: string | null;
    symbol?: string;
    onViewFullReport: () => void;
    onClose?: () => void;
}

export function AIThesisSummary({ aiResult, isAnalyzing, aiError, symbol, onViewFullReport, onClose }: AIThesisSummaryProps) {
    const [copied, setCopied] = useState(false);
    if (!aiResult && !isAnalyzing && !aiError) return null;

    const ticker = symbol || aiResult?.ticker || '';
    const reviewedAt = aiResult?.reviewedAt || aiResult?.analyzedAt;
    const formattedDate = reviewedAt ? new Date(reviewedAt).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : null;

    const handleCopySkill = () => {
        if (!ticker) return;
        navigator.clipboard.writeText(`/guide-valuation ${ticker}`);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    return (
        <div className="mb-4 animate-in fade-in slide-in-from-top-4 duration-500">
            <div className="bg-gradient-to-br from-indigo-900/40 via-slate-900/60 to-purple-900/30 border border-indigo-500/30 rounded-xl p-4 shadow-xl overflow-hidden relative group">
                <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-indigo-500 via-purple-500 to-indigo-500 opacity-50"></div>
                <div className="absolute -right-10 -top-10 w-32 h-32 bg-indigo-500/10 blur-3xl rounded-full group-hover:bg-indigo-500/20 transition-all duration-1000"></div>

                <div className="flex justify-between items-start mb-3 relative z-10">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-indigo-500/20 rounded-lg text-indigo-400">
                            <BrainCircuit size={20} />
                        </div>
                        <div>
                            <div className="flex items-center gap-3">
                                <h3 className="text-base font-bold text-white">AI Expert Thesis</h3>
                                {aiResult?.action && (
                                    <span className={`text-[10px] px-2 py-0.5 rounded-full uppercase font-black tracking-wider border ${getActionBadgeClass(aiResult.action)}`}>
                                        {aiResult.action}
                                    </span>
                                )}
                            </div>
                            <div className="flex items-center gap-2 mt-0.5">
                                <p className="text-[10px] text-indigo-300 font-bold tracking-widest uppercase">{aiResult?.model_name || 'AI ANALYST'} ANALYSIS</p>
                                {formattedDate && (
                                    <span className="text-[10px] text-slate-400 flex items-center gap-1 border-l border-slate-700 pl-2">
                                        <Clock size={11} className="text-slate-400" /> Reviewed: <strong className="text-slate-300">{formattedDate}</strong>
                                    </span>
                                )}
                            </div>
                        </div>
                    </div>
                    <div className="flex items-center gap-2">
                        {ticker && (
                            <button
                                onClick={handleCopySkill}
                                title={`Copy command: /guide-valuation ${ticker}`}
                                className="text-[11px] font-semibold text-indigo-300 bg-indigo-950/60 hover:bg-indigo-900/80 border border-indigo-500/40 px-2.5 py-1 rounded-lg flex items-center gap-1.5 transition-all shadow-sm"
                            >
                                {copied ? <Check size={13} className="text-emerald-400" /> : <Sparkles size={13} className="text-indigo-400" />}
                                {copied ? 'Copied /guide-valuation!' : 'Update via /guide-valuation'}
                            </button>
                        )}
                        {onClose && (
                            <button
                                onClick={onClose}
                                className="text-slate-500 hover:text-white transition-colors"
                            >
                                <X size={18} />
                            </button>
                        )}
                    </div>
                </div>

                {isAnalyzing ? (
                    <div className="py-8 flex flex-col items-center justify-center gap-3">
                        <Loader2 size={28} className="text-indigo-400 animate-spin" />
                        <div className="flex flex-col items-center">
                            <p className="text-sm text-indigo-200 animate-pulse">Analyzing financials & growth vectors...</p>
                            <p className="text-[10px] text-slate-500">Processing Investment Thesis</p>
                        </div>
                    </div>
                ) : aiError ? (
                    <div className="py-6 text-center">
                        <div className="text-red-400 font-bold mb-2 flex items-center justify-center gap-2 text-sm">
                            <AlertTriangle size={18} /> Analysis Failed
                        </div>
                        <p className="text-xs text-slate-400">{aiError}</p>
                    </div>
                ) : aiResult ? (
                    <div className="z-10 transition-all duration-300 ease-in-out">
                        <div className="relative">
                            <div className="text-sm text-slate-300 leading-relaxed font-medium mb-3">
                                <ReactMarkdown components={{
                                    strong: ({ node, ...props }: any) => <span className="font-bold text-indigo-200" {...props} />,
                                    p: ({ node, ...props }: any) => <p className="mb-2 last:mb-0" {...props} />
                                }}>
                                    {aiResult.rationale}
                                </ReactMarkdown>
                            </div>
                        </div>
                        <div className="flex justify-between items-center mt-2">
                            <button
                                onClick={onViewFullReport}
                                className="text-[11px] uppercase font-black text-indigo-400 hover:text-indigo-300 flex items-center gap-2 bg-slate-800/80 px-3 py-1.5 rounded-lg border border-indigo-500/20 transition-all hover:bg-slate-800"
                            >
                                View Full Report <FolderOpen size={14} />
                            </button>
                            
                            {aiResult.fair_value && (
                                <div className="flex flex-col items-end">
                                    <span className="text-[9px] text-slate-500 uppercase font-bold tracking-wider">AI Target Price</span>
                                    <span className="text-lg font-black text-white leading-none">${Math.round(aiResult.fair_value)}</span>
                                </div>
                            )}
                        </div>
                    </div>
                ) : null}
            </div>
        </div>
    );
}
