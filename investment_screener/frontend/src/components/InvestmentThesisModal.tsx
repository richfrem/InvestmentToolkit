/**
 * InvestmentThesisModal.tsx (React Component)
 * =====================================
 *
 * Purpose:
 *     Modal that displays the canonical Investment Thesis document (markdown).
 *
 * Layer: Frontend / UI / Modals
 *
 * Usage Examples:
 *     <InvestmentThesisModal onClose={() => {}} />
 *
 * Key Functions:
 *     - fetchInvestmentThesis() - Async call to retrieve the investment_thesis.md content
 */
import { useEffect, useState } from 'react';
import { X, BookOpen, Loader2 } from 'lucide-react';
import { fetchInvestmentThesis } from '../services/api';
import MarkdownContent from './MarkdownContent';
import ThesisViewModal from './ThesisViewModal';


interface Props { onClose: () => void; }

export default function InvestmentThesisModal({ onClose }: Props) {
    const [content, setContent] = useState<string | null>(null);
    const [thesisName, setThesisName] = useState<string>('Investment Thesis');
    const [thesisDescription, setThesisDescription] = useState<string>('');
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [selectedSubStrategyId, setSelectedSubStrategyId] = useState<string | null>(null);

    useEffect(() => {
        fetchInvestmentThesis()
            .then(d => {
                setContent(d.content);
                if (d.thesisName) setThesisName(d.thesisName);
                if (d.thesisDescription) setThesisDescription(d.thesisDescription);
            })
            .catch(e => setError(e.message))
            .finally(() => setLoading(false));
    }, []);

    // Close on Escape
    useEffect(() => {
        const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
        document.addEventListener('keydown', handler);
        return () => document.removeEventListener('keydown', handler);
    }, [onClose]);

    const handleLinkClick = (href: string) => {
        // Extract the strategy ID from paths like 'sub_strategies/asi_race.md' or similar
        const filename = href.split('/').pop()?.replace('.md', '') || href;
        setSelectedSubStrategyId(filename);
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm" onClick={onClose}>
            <div
                className="relative bg-slate-950 border border-slate-700 rounded-2xl shadow-2xl w-full max-w-4xl max-h-[90vh] flex flex-col"
                onClick={e => e.stopPropagation()}
            >
                {/* Header */}
                <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 shrink-0">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-indigo-500/10 rounded-lg text-indigo-400">
                            <BookOpen size={18} />
                        </div>
                        <div>
                            <h2 className="text-white font-bold text-base">{thesisName}</h2>
                            {thesisDescription && <p className="text-slate-500 text-xs">{thesisDescription}</p>}
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
                            <span className="text-sm">Loading thesis...</span>
                        </div>
                    )}
                    {error && <div className="text-red-400 text-sm p-4 bg-red-500/10 rounded-lg">{error}</div>}
                    {content && <MarkdownContent content={content} accentColor="indigo" onLinkClick={handleLinkClick} />}
                </div>
            </div>

            <ThesisViewModal
                isOpen={!!selectedSubStrategyId}
                onClose={() => setSelectedSubStrategyId(null)}
                thesisId={selectedSubStrategyId}
            />
        </div>
    );
}
