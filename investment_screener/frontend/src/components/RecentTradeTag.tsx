/**
 * Purpose: show beside an action what the owner actually traded recently.
 * Layer: Frontend / UI. Usage: <RecentTradeTag rec={recommendation} />.
 * Key Functions: RecentTradeTag — "Sold 3 · Oct 6" tag, coloured by whether it follows the action.
 * Key Input Dependencies: RecommendationRecord.recent_trades from recent_trades.py (filled trades only).
 */
import type { RecentTrades, RecommendationRecord } from '../services/api';

const TONES: Record<RecentTrades['context']['status'], string> = {
    ACTED: 'text-emerald-300 border-emerald-500/40 bg-emerald-500/10',
    OPPOSED: 'text-amber-300 border-amber-500/40 bg-amber-500/10',
    RECENT: 'text-slate-300 border-slate-500/40 bg-slate-500/10',
    NONE: '',
};
const ICONS: Record<RecentTrades['context']['status'], string> = { ACTED: '✓', OPPOSED: '!', RECENT: '•', NONE: '' };

/** Trade dates are calendar days: format without shifting them through a time zone. */
function shortDate(iso: string): string {
    const [year, month, day] = iso.split('-').map(Number);
    return new Date(year, month - 1, day).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

/** Nothing is shown when there were no filled trades in the window. */
export function RecentTradeTag({ rec }: { rec?: RecommendationRecord | null }) {
    const trades = rec?.recent_trades;
    if (!trades || !trades.last || trades.context.status === 'NONE') return null;
    const parts = [
        trades.sold_shares > 0 ? `Sold ${Number(trades.sold_shares.toFixed(4))}` : '',
        trades.bought_shares > 0 ? `Bought ${Number(trades.bought_shares.toFixed(4))}` : '',
    ].filter(Boolean).join(', ');
    return (
        <span title={trades.context.note}
            className={`inline-flex items-center gap-1 whitespace-nowrap rounded border px-1.5 py-0.5 text-[10px] font-bold ${TONES[trades.context.status]}`}>
            <span aria-hidden="true">{ICONS[trades.context.status]}</span>{parts} · {shortDate(trades.last.date)}
        </span>
    );
}
