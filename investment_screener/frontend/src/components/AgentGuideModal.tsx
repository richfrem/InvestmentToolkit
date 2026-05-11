/**
 * AgentGuideModal.tsx (React Component)
 * =====================================
 *
 * Purpose:
 *     Modal that displays the Agent Quick Reference guide for CLI commands and workflows.
 *
 * Layer: Frontend / UI / Modals
 *
 * Usage Examples:
 *     <AgentGuideModal onClose={() => {}} />
 *
 * Key Functions:
 *     - fetchAgentGuide() - Async API call to retrieve the markdown guide from the toolkit-manager plugin
 *     - handler() - Local keyboard event listener for the Escape key to close the modal
 */
import { useEffect, useState } from 'react';
import { X, Terminal, Loader2 } from 'lucide-react';
import { fetchAgentGuide } from '../services/api';
import MarkdownContent from './MarkdownContent';

interface Props { onClose: () => void; }

export default function AgentGuideModal({ onClose }: Props) {
    const [content, setContent] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        fetchAgentGuide()
            .then(d => setContent(d.content))
            .catch(e => setError(e.message))
            .finally(() => setLoading(false));
    }, []);

    useEffect(() => {
        const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
        document.addEventListener('keydown', handler);
        return () => document.removeEventListener('keydown', handler);
    }, [onClose]);

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm" onClick={onClose}>
            <div
                className="relative bg-slate-950 border border-slate-700 rounded-2xl shadow-2xl w-full max-w-4xl max-h-[90vh] flex flex-col"
                onClick={e => e.stopPropagation()}
            >
                {/* Header */}
                <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 shrink-0">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-emerald-500/10 rounded-lg text-emerald-400">
                            <Terminal size={18} />
                        </div>
                        <div>
                            <h2 className="text-white font-bold text-base">Agent Quick Reference</h2>
                            <p className="text-slate-500 text-xs">How to trigger AI skills via Copilot CLI chat</p>
                        </div>
                    </div>
                    <button onClick={onClose} className="p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors">
                        <X size={18} />
                    </button>
                </div>

                {/* Body */}
                <div className="flex-1 overflow-y-auto px-6 py-5 custom-scrollbar">
                    {loading && (
                        <div className="flex items-center justify-center h-48 gap-3 text-slate-400">
                            <Loader2 size={20} className="animate-spin" />
                            <span className="text-sm">Loading guide...</span>
                        </div>
                    )}
                    {error && <div className="text-red-400 text-sm p-4 bg-red-500/10 rounded-lg">{error}</div>}
                    {content && <MarkdownContent content={content} accentColor="emerald" />}
                </div>
            </div>
        </div>
    );
}
