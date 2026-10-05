/**
 * Purpose: display counted filters for canonical recommendation labels.
 * Layer: Frontend / Presentation. Usage: Daily Brief cards and conviction table.
 * Key Functions: RecommendationFilters.
 * Key Input Dependencies: current action labels; shared REC_CHIP_STYLES.
 */
import { REC_CHIP_STYLES } from '../utils/recommendationPresentation';

const OPTIONS = [
    ['all', 'All'], ['EXIT', '🔴 Exit'], ['TRIM', '🟠 Trim'],
    ['INITIATE', '🟢 Initiate'], ['ACCUMULATE', '🔵 Accumulate'],
    ['MAINTAIN', 'Maintain'], ['WATCHLIST', 'Watchlist'],
] as const;

interface RecommendationFiltersProps {
    actions: string[];
    active: string;
    onChange: (action: string) => void;
    label: string;
}

/** Render all action choices, retaining zero counts so empty filters can be reset. */
export function RecommendationFilters({ actions, active, onChange, label }: RecommendationFiltersProps) {
    const counts: Record<string, number> = {};
    for (const action of actions) counts[action] = (counts[action] ?? 0) + 1;
    return (
        <div role="group" aria-label={label} className="flex flex-wrap items-center gap-2">
            {OPTIONS.map(([action, text]) => {
                const style = REC_CHIP_STYLES[action] ?? REC_CHIP_STYLES.MAINTAIN;
                const count = action === 'all' ? actions.length : counts[action] ?? 0;
                const selected = active === action;
                return (
                    <button key={action} type="button" aria-pressed={selected}
                        onClick={() => onChange(action)}
                        className={`inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs font-bold transition-colors
                            ${style.text} ${selected ? `${style.bg} ${style.border} ring-1 ring-current` : 'border-zinc-700 bg-transparent hover:bg-zinc-800'}`}>
                        {text}
                        <span className="rounded-full bg-zinc-800 px-1.5 text-[10px]">{count}</span>
                    </button>
                );
            })}
        </div>
    );
}
