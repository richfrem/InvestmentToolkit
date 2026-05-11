/**
 * AnalysisChartToggle.tsx (React Component)
 * =====================================
 *
 * Purpose:
 *     Selection control for toggling between different financial visualization modes (Revenue, FCF, Margins, EPS).
 *
 * Layer: Frontend / UI / Components / Analysis
 *
 * Usage Examples:
 *     <AnalysisChartToggle activeMode="revenue" onModeChange={(mode) => setMode(mode)} />
 *
 * Key Functions:
 *     - AnalysisChartToggle() - Renders a button group for switching chart context within the analysis view
 */
import { BarChart3, TrendingUp, PieChart, Coins } from 'lucide-react';

export type ChartMode = 'revenue' | 'fcf' | 'margins' | 'eps';

interface AnalysisChartToggleProps {
    activeMode: ChartMode;
    onModeChange: (mode: ChartMode) => void;
}

export default function AnalysisChartToggle({ activeMode, onModeChange }: AnalysisChartToggleProps) {
    const modes: { id: ChartMode; label: string; icon: React.ElementType }[] = [
        { id: 'revenue', label: 'Revenue & Earnings', icon: BarChart3 },
        { id: 'margins', label: 'Margins', icon: PieChart },
        { id: 'fcf', label: 'Free Cash Flow', icon: Coins },
        { id: 'eps', label: 'EPS Trend', icon: TrendingUp },
    ];

    return (
        <div className="flex bg-slate-900/50 p-1 rounded-lg border border-slate-800 inline-flex">
            {modes.map(mode => {
                const isActive = activeMode === mode.id;
                const Icon = mode.icon;

                return (
                    <button
                        key={mode.id}
                        onClick={() => onModeChange(mode.id)}
                        className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium transition-all
                            ${isActive
                                ? 'bg-amber-500/10 text-amber-500 shadow-sm ring-1 ring-amber-500/20'
                                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                            }`}
                    >
                        <Icon size={14} />
                        {mode.label}
                    </button>
                );
            })}
        </div>
    );
}
