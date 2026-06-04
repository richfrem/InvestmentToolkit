import { useEffect, useState } from 'react';
import { BookOpen, Calendar, Target, Activity, FileText } from 'lucide-react';
import ThesisViewModal from '../components/ThesisViewModal';
import InvestmentThesisModal from '../components/InvestmentThesisModal';

interface SubStrategySummary {
    id: string;
    title: string;
    status: string;
    date: string;
    targetWeight: string;
}

export default function ThesesPage() {
    const [strategies, setStrategies] = useState<SubStrategySummary[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedId, setSelectedId] = useState<string | null>(null);
    const [isMasterOpen, setIsMasterOpen] = useState(false);

    useEffect(() => {
        fetch('/api/theses/sub-strategies')
            .then(res => res.json())
            .then(data => {
                setStrategies(data);
                setLoading(false);
            })
            .catch(err => {
                console.error('Failed to load sub-strategies', err);
                setLoading(false);
            });
    }, []);

    const getStatusColor = (status: string) => {
        if (status === 'APPROVED' || status === 'ACTIVE') return 'text-emerald-400 bg-emerald-400/10 border-emerald-400/20';
        if (status === 'REJECTED') return 'text-red-400 bg-red-400/10 border-red-400/20';
        return 'text-amber-400 bg-amber-400/10 border-amber-400/20';
    };

    return (
        <div className="p-8 max-w-7xl mx-auto">
            <div className="flex justify-between items-center mb-8">
                <div>
                    <h1 className="text-3xl font-bold text-white tracking-tight flex items-center gap-3">
                        <BookOpen className="w-8 h-8 text-indigo-400" />
                        Investment Theses
                    </h1>
                    <p className="text-gray-400 mt-2">Active sub-strategies and historical proposals defining the portfolio's direction.</p>
                </div>
                <div>
                    <button
                        onClick={() => setIsMasterOpen(true)}
                        className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl font-medium transition-all shadow-lg hover:shadow-indigo-600/20 shrink-0"
                    >
                        <FileText className="w-4 h-4" />
                        View Master Thesis
                    </button>
                </div>
            </div>

            {loading ? (
                <div className="flex justify-center items-center h-64">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500"></div>
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {strategies.map(strategy => (
                        <div
                            key={strategy.id}
                            onClick={() => setSelectedId(strategy.id)}
                            className="bg-[#1C1C1E] border border-white/5 rounded-2xl p-6 hover:border-indigo-500/50 hover:bg-[#2C2C2E] transition-all cursor-pointer group"
                        >
                            <div className="flex justify-between items-start mb-4">
                                <h3 className="text-lg font-semibold text-white group-hover:text-indigo-400 transition-colors line-clamp-2">
                                    {strategy.title}
                                </h3>
                                <span className={`px-2.5 py-1 text-xs font-medium rounded-md border ${getStatusColor(strategy.status)}`}>
                                    {strategy.status}
                                </span>
                            </div>

                            <div className="space-y-3 mt-6">
                                <div className="flex items-center text-sm text-gray-400">
                                    <Target className="w-4 h-4 mr-3 text-gray-500" />
                                    <span>Target Weight: <strong className="text-white ml-1">{strategy.targetWeight}</strong></span>
                                </div>
                                <div className="flex items-center text-sm text-gray-400">
                                    <Calendar className="w-4 h-4 mr-3 text-gray-500" />
                                    <span>{strategy.date || 'No Date'}</span>
                                </div>
                                <div className="flex items-center text-sm text-gray-400">
                                    <Activity className="w-4 h-4 mr-3 text-gray-500" />
                                    <span className="font-mono text-xs">{strategy.id}.md</span>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            <ThesisViewModal
                isOpen={!!selectedId}
                onClose={() => setSelectedId(null)}
                thesisId={selectedId}
            />

            {isMasterOpen && (
                <InvestmentThesisModal onClose={() => setIsMasterOpen(false)} />
            )}
        </div>
    );
}
