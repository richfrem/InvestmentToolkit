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
            className="fixed inset-0 z-[60] flex items-center justify-center bg-black/70 backdrop-blur-sm"
            onClick={onClose}
        >
            <div
                className="relative w-full max-w-4xl max-h-[90vh] bg-gray-900 border border-gray-700 rounded-2xl overflow-hidden flex flex-col shadow-2xl"
                onClick={(e) => e.stopPropagation()}
            >
                {/* Sticky Header */}
                <div className="flex items-center justify-between px-6 py-4 border-b border-gray-700 bg-gray-900/95 backdrop-blur shrink-0">
                    <div className="flex items-center gap-3">
                        <BookOpen className="w-6 h-6 text-purple-400" />
                        <div>
                            <h2 className="text-lg font-semibold text-white">
                                {ticker} — Deep Dive Research Report
                            </h2>
                            <p className="text-sm text-gray-400">{date}</p>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="text-gray-400 hover:text-white p-2 rounded-lg hover:bg-gray-800 transition-colors"
                    >
                        <X className="w-5 h-5" />
                    </button>
                </div>

                {/* Scrollable Content */}
                <div className="flex-1 overflow-y-auto px-8 py-6 custom-scrollbar">
                    {loading && (
                        <div className="flex items-center justify-center py-20">
                            <Loader className="w-8 h-8 text-purple-500 animate-spin" />
                        </div>
                    )}

                    {error && (
                        <div className="text-center py-20 text-gray-400">
                            <p className="text-lg mb-2">Report not available</p>
                            <p className="text-sm">
                                Run the AI analyst to generate a deep dive for this ticker.
                            </p>
                        </div>
                    )}

                    {content && (
                        <article
                            className="prose prose-invert prose-purple max-w-none
                prose-headings:text-white prose-h1:text-2xl prose-h2:text-xl prose-h3:text-lg
                prose-p:text-gray-300 prose-strong:text-white
                prose-table:border-collapse
                prose-th:bg-gray-800 prose-th:text-gray-300 prose-th:px-4 prose-th:py-2 prose-th:text-left prose-th:border prose-th:border-gray-700
                prose-td:text-gray-400 prose-td:px-4 prose-td:py-2 prose-td:border prose-td:border-gray-700
                prose-a:text-purple-400 hover:prose-a:text-purple-300
                prose-code:text-purple-300 prose-code:bg-gray-800 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded
                prose-hr:border-gray-700
                pb-10"
                        >
                            <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                {content}
                            </ReactMarkdown>
                        </article>
                    )}
                </div>
            </div>
        </div>
    );
};
