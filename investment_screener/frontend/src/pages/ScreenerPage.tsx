/**
 * ScreenerPage.tsx (React Page)
 * =====================================
 *
 * Purpose:
 *     The primary interface for the Portfolio Advisor, featuring deep-dive agent analyses and investment thesis management.
 *
 * Layer: Frontend / Pages
 *
 * Usage Examples:
 *     <ScreenerPage />
 *
 * Key Functions:
 *     - ScreenerPage() - Orchestrates the main layout for the Portfolio Advisor, including quick-access buttons for Thesis, Review, and Guide modals
 */
import { useState } from 'react';
import ScreenerTable from '../components/ScreenerTable';
import InvestmentThesisModal from '../components/InvestmentThesisModal';
import LatestReviewModal from '../components/LatestReviewModal';
import AgentGuideModal from '../components/AgentGuideModal';
import { BookOpen, FileBarChart2, Terminal } from 'lucide-react';

export default function ScreenerPage() {
    const [showThesis, setShowThesis] = useState(false);
    const [showReview, setShowReview] = useState(false);
    const [showGuide, setShowGuide] = useState(false);

    return (
        <div className="p-6 h-full flex flex-col">
            <div className="mb-6 flex items-start justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-white mb-2">Portfolio Advisor</h1>
                    <p className="text-slate-400 text-sm">
                        AI-powered portfolio intelligence · deep-dive agent analyses
                    </p>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                    <button
                        onClick={() => setShowThesis(true)}
                        className="flex items-center gap-2 px-3 py-2 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 hover:bg-indigo-500/20 text-xs font-bold transition-all"
                    >
                        <BookOpen size={14} />
                        Investment Thesis
                    </button>
                    <button
                        onClick={() => setShowReview(true)}
                        className="flex items-center gap-2 px-3 py-2 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-300 hover:bg-amber-500/20 text-xs font-bold transition-all"
                    >
                        <FileBarChart2 size={14} />
                        Latest Review
                    </button>
                    <button
                        onClick={() => setShowGuide(true)}
                        className="flex items-center gap-2 px-3 py-2 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 hover:bg-emerald-500/20 text-xs font-bold transition-all"
                    >
                        <Terminal size={14} />
                        Agent Guide
                    </button>
                </div>
            </div>

            <div className="flex-1 min-h-0">
                <ScreenerTable />
            </div>

            {showThesis && <InvestmentThesisModal onClose={() => setShowThesis(false)} />}
            {showReview && <LatestReviewModal onClose={() => setShowReview(false)} />}
            {showGuide && <AgentGuideModal onClose={() => setShowGuide(false)} />}
        </div>
    );
}
