import { useState } from 'react';
import { Briefcase, AlertTriangle } from 'lucide-react';
import { PortfolioModal } from '../components/PortfolioModal';

export default function Settings() {
    const [isPortfolioOpen, setIsPortfolioOpen] = useState(false);

    return (
        <div className="space-y-6 p-6">
            <h2 className="text-2xl font-bold text-text">Settings</h2>

            <div className="bg-surface p-6 rounded-lg border border-slate-800">
                <p className="text-secondary">Configuration options coming soon.</p>
            </div>

            {/* Advanced section */}
            <div className="bg-surface rounded-lg border border-slate-700">
                <div className="px-6 py-4 border-b border-slate-800">
                    <h3 className="text-sm font-bold text-slate-300 uppercase tracking-wider">Advanced</h3>
                </div>
                <div className="p-6 space-y-4">
                    <div className="flex items-start gap-3 bg-amber-500/5 border border-amber-500/20 rounded-lg p-4">
                        <AlertTriangle size={16} className="text-amber-500 mt-0.5 shrink-0" />
                        <p className="text-amber-300/80 text-xs leading-relaxed">
                            Manual portfolio editing bypasses the TradingView sync and may cause your portfolio.json to go out of sync with live positions.
                            Prefer <strong>/tv-portfolio-sync</strong> for regular updates.
                        </p>
                    </div>
                    <button
                        onClick={() => setIsPortfolioOpen(true)}
                        className="flex items-center gap-3 px-4 py-3 rounded-lg border border-slate-700 hover:border-slate-600 hover:bg-slate-800/50 transition-colors text-slate-300 hover:text-white w-full"
                    >
                        <Briefcase size={18} className="text-slate-500" />
                        <div className="text-left">
                            <div className="text-sm font-medium">Manual Portfolio Editor</div>
                            <div className="text-xs text-slate-500">Edit portfolio.json directly — use only if TV sync is unavailable</div>
                        </div>
                    </button>
                </div>
            </div>

            <PortfolioModal isOpen={isPortfolioOpen} onClose={() => setIsPortfolioOpen(false)} />
        </div>
    );
}
