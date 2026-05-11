/**
 * AgentReminderModal.tsx (React Component)
 * =====================================
 *
 * Purpose:
 *     In-app modal reminding users about the Agentic CLI capabilities (Grok, DCF, etc.).
 *
 * Layer: Frontend / UI / Components
 *
 * Usage Examples:
 *     <AgentReminderModal isOpen={true} onClose={() => {}} symbol="AAPL" />
 *
 * Key Functions:
 *     - AgentReminderModal() - Functional component rendering the UI and the current symbol command
 */
import { X, Terminal, ExternalLink } from 'lucide-react';

interface Props {
    isOpen: boolean;
    onClose: () => void;
    symbol?: string;
}

export function AgentReminderModal({ isOpen, onClose, symbol }: Props) {
    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-in fade-in duration-300">
            <div className="relative bg-slate-950 border border-indigo-500/30 rounded-2xl shadow-[0_0_50px_rgba(79,70,229,0.2)] w-full max-w-lg overflow-hidden">
                {/* Decorative background element */}
                <div className="absolute -right-20 -top-20 w-64 h-64 bg-indigo-600/10 blur-[100px] rounded-full"></div>
                
                {/* Header */}
                <div className="relative flex items-center justify-between px-6 py-5 border-b border-slate-800/50">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-indigo-500/10 rounded-lg text-indigo-400">
                            <Terminal size={20} />
                        </div>
                        <div>
                            <h2 className="text-white font-bold text-lg">Agentic OS Required</h2>
                            <p className="text-slate-500 text-xs font-medium uppercase tracking-wider">CLI Environment Only</p>
                        </div>
                    </div>
                    <button 
                        onClick={onClose}
                        className="p-2 text-slate-500 hover:text-white hover:bg-slate-800 rounded-xl transition-all"
                    >
                        <X size={20} />
                    </button>
                </div>

                {/* Body */}
                <div className="relative px-8 py-8 space-y-6">
                    <div className="space-y-3">
                        <p className="text-slate-300 text-sm leading-relaxed">
                            To ensure the highest quality analysis using Pro-tier models (Claude 3.5, Gemini 1.5 Pro), stock research has moved to your **CLI Environment**.
                        </p>
                        <p className="text-indigo-300/80 text-sm font-medium">
                            Please open your terminal and run the following command:
                        </p>
                    </div>

                    <div className="bg-black/50 border border-slate-800 rounded-xl p-4 font-mono text-sm relative group">
                        <div className="flex items-center justify-between text-indigo-400 mb-1">
                            <span className="text-[10px] uppercase font-bold tracking-widest text-slate-500">Terminal Command</span>
                            <span className="text-[10px] text-slate-600 group-hover:text-indigo-500 transition-colors">Copy to clipboard</span>
                        </div>
                        <div className="text-white selection:bg-indigo-500/30">
                            /evaluate-stock {symbol || 'TICKER'}
                        </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4 pt-2">
                        <div className="p-3 bg-slate-900/50 border border-slate-800 rounded-xl space-y-1">
                            <span className="text-[10px] font-bold text-slate-500 uppercase">Step 1</span>
                            <p className="text-xs text-slate-300">Open Gemini CLI, Claude Code, or Copilot CLI</p>
                        </div>
                        <div className="p-3 bg-slate-900/50 border border-slate-800 rounded-xl space-y-1">
                            <span className="text-[10px] font-bold text-slate-500 uppercase">Step 2</span>
                            <p className="text-xs text-slate-300">Type the command and press Enter</p>
                        </div>
                    </div>
                </div>

                {/* Footer */}
                <div className="relative px-8 py-5 bg-indigo-500/5 border-t border-slate-800/50 flex justify-end gap-3">
                    <button 
                        onClick={onClose}
                        className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-sm rounded-xl transition-all shadow-lg shadow-indigo-600/20 active:scale-95"
                    >
                        Got it
                    </button>
                </div>
            </div>
        </div>
    );
}
