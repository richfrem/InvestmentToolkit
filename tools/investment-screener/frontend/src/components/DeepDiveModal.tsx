import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { X, BookOpen, Loader } from 'lucide-react';

interface DeepDiveModalProps {
    isOpen: boolean;
    onClose: () => void;
    filename: string | null;
}

export const DeepDiveModal: React.FC<DeepDiveModalProps> = ({
    isOpen,
    onClose,
    filename,
}) => {
    const [content, setContent] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (!isOpen || !filename) return;

        setLoading(true);
        setError(null);
        setContent(null);

        fetch(`/api/research/${filename}`)
            .then((res) => {
                if (!res.ok) throw new Error('Report not found');
                return res.json();
            })
            .then((data) => setContent(data.content))
            .catch((err) => setError(err.message))
            .finally(() => setLoading(false));
    }, [isOpen, filename]);

    if (!isOpen) return null;

    const ticker = filename?.split('_')[0] ?? '';
    const date = filename?.split('_')[1]?.replace('.md', '') ?? '';

    return (
        <div
            className="fixed inset-0 z-[60] flex items-center justify-center bg-black/80 backdrop-blur-md animate-in fade-in duration-200"
            onClick={onClose}
        >
            <div
                className="relative w-full max-w-5xl h-[85vh] bg-slate-900 border border-slate-700/50 rounded-2xl overflow-hidden flex flex-col shadow-2xl animate-in zoom-in-95 duration-200"
                onClick={(e) => e.stopPropagation()}
            >
                {/* Sticky Header */}
                <div className="flex items-center justify-between px-6 py-4 border-b border-slate-700/50 bg-slate-900/95 backdrop-blur shrink-0 z-20">
                    <div className="flex items-center gap-4">
                        <div className="p-2 bg-indigo-500/10 rounded-lg text-indigo-400">
                            <BookOpen className="w-6 h-6" />
                        </div>
                        <div>
                            <h2 className="text-xl font-bold text-white tracking-tight">
                                {ticker} <span className="text-slate-500 font-normal mx-2">/</span> Deep Dive Research
                            </h2>
                            <p className="text-xs text-slate-400 font-medium tracking-wide uppercase">
                                Generated {date} • AI Analyst
                            </p>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="text-slate-400 hover:text-white p-2 rounded-lg hover:bg-slate-800 transition-colors"
                    >
                        <X className="w-5 h-5" />
                    </button>
                </div>

                {/* Scrollable Content */}
                <div className="flex-1 overflow-y-auto custom-scrollbar bg-slate-950/30">
                    {loading && (
                        <div className="flex flex-col items-center justify-center h-full gap-4">
                            <Loader className="w-8 h-8 text-indigo-500 animate-spin" />
                            <p className="text-sm text-indigo-300 animate-pulse">Retrieving research data...</p>
                        </div>
                    )}

                    {error && (
                        <div className="flex flex-col items-center justify-center h-full gap-2 text-slate-400">
                            <p className="text-lg font-medium text-red-400">Report unavailable</p>
                            <p className="text-sm">Please run the AI Analyst to generate this report.</p>
                        </div>
                    )}

                    {content && (
                        <div className="max-w-4xl mx-auto px-8 py-10">
                            <article className="prose prose-invert prose-indigo max-w-none">
                                <ReactMarkdown
                                    remarkPlugins={[remarkGfm]}
                                    components={{
                                        // Custom Header Styles
                                        h1: ({ node, ...props }) => (
                                            <h1 className="text-3xl font-black text-white mb-6 pb-4 border-b border-slate-800 tracking-tight" {...props} />
                                        ),
                                        h2: ({ node, ...props }) => (
                                            <h2 className="text-2xl font-bold text-indigo-100 mt-10 mb-4 flex items-center gap-2" {...props} />
                                        ),
                                        h3: ({ node, ...props }) => (
                                            <h3 className="text-lg font-bold text-indigo-200 mt-8 mb-3" {...props} />
                                        ),
                                        // Custom Paragraph
                                        p: ({ node, ...props }) => (
                                            <p className="text-slate-300 leading-relaxed mb-4 text-[15px]" {...props} />
                                        ),
                                        // Custom List Styles
                                        ul: ({ node, ...props }) => (
                                            <ul className="my-4 space-y-2 list-none pl-0" {...props} />
                                        ),
                                        li: ({ node, ...props }) => (
                                            <li className="relative pl-6 text-slate-300">
                                                <span className="absolute left-0 top-2 w-1.5 h-1.5 bg-indigo-500 rounded-full"></span>
                                                {props.children}
                                            </li>
                                        ),
                                        // Custom Blockquote (Callouts)
                                        blockquote: ({ node, ...props }) => (
                                            <blockquote className="border-l-4 border-indigo-500 bg-indigo-500/5 px-6 py-4 rounded-r-lg my-6 text-indigo-100 italic" {...props} />
                                        ),
                                        // Custom Table Styling
                                        table: ({ node, ...props }) => (
                                            <div className="overflow-x-auto my-8 rounded-xl border border-slate-800 shadow-lg">
                                                <table className="w-full text-left border-collapse bg-slate-900/50" {...props} />
                                            </div>
                                        ),
                                        thead: ({ node, ...props }) => (
                                            <thead className="bg-slate-900 border-b border-slate-700" {...props} />
                                        ),
                                        th: ({ node, ...props }) => (
                                            <th className="px-4 py-3 text-xs font-bold text-slate-400 uppercase tracking-wider" {...props} />
                                        ),
                                        tr: ({ node, ...props }) => (
                                            <tr className="border-b border-slate-800/50 last:border-none hover:bg-slate-800/30 transition-colors" {...props} />
                                        ),
                                        td: ({ node, ...props }) => (
                                            <td className="px-4 py-3 text-sm text-slate-300 border-none" {...props} />
                                        ),
                                        // Code blocks
                                        code: ({ node, inline, className, children, ...props }: any) => {
                                            return inline ? (
                                                <code className="bg-slate-800 text-indigo-200 px-1.5 py-0.5 rounded text-sm font-mono" {...props}>
                                                    {children}
                                                </code>
                                            ) : (
                                                <div className="mockup-code bg-slate-950 border border-slate-800 rounded-xl my-6 p-4 overflow-x-auto">
                                                    <code className="text-sm font-mono text-slate-300 block" {...props}>
                                                        {children}
                                                    </code>
                                                </div>
                                            );
                                        },
                                        hr: ({ node, ...props }) => (
                                            <hr className="border-slate-800 my-10" {...props} />
                                        )
                                    }}
                                >
                                    {content}
                                </ReactMarkdown>
                            </article>

                            {/* Footer */}
                            <div className="mt-12 pt-6 border-t border-slate-800 flex justify-between items-center text-xs text-slate-500">
                                <p>Generated by Investment Toolkit AI • Internal Use Only</p>
                                <p>Confidential</p>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};
