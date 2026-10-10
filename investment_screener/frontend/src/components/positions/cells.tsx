/**
 * cells.tsx - The small cell components every ticker table is built from.
 *
 * Purpose:
 *     One component per kind of cell, so the ticker, the stance badge, a number and a dash look
 *     the same on every screen. Valuation cells (range bar, reward:risk, support, check) already
 *     live in RiskRewardCell and are reused through the column registry.
 *
 * Layer: Frontend / Components / Positions
 *
 * Usage Examples:
 *     <ActionCell row={row} rec={rec} />   <MonoCell>{formatWeight(row.actualPct)}</MonoCell>
 *
 * Key Functions (Index):
 *     - TickerCell, NameCell, TextCell: identity and text cells
 *     - ActionCell: the stance (stanceOf) as a badge plus the recent-trade tag
 *     - MonoCell: a right-aligned number in the table's number style
 *     - EarningsCell: the earnings date with a highlight when it is close
 *
 * Key Input Dependencies:
 *     - utils/riskReward (stanceOf), utils/actionColors, RecentTradeTag
 *
 * Key Output Dependencies:
 *     - columns.ts (the registry)
 */
import type { ReactNode } from 'react';
import type { RecommendationRecord } from '../../services/api';
import { getActionBadgeClass } from '../../utils/actionColors';
import { stanceOf } from '../../utils/riskReward';
import { RecentTradeTag } from '../RecentTradeTag';
import type { PositionRow } from './positionMath';

export function TickerCell({ row }: { row: PositionRow }) {
    return <span className="font-bold text-white">{row.ticker}</span>;
}

export function NameCell({ row }: { row: PositionRow }) {
    return <span className="text-xs text-zinc-300">{row.name}</span>;
}

export function TextCell({ children }: { children: ReactNode }) {
    return <span className="text-xs text-zinc-400">{children}</span>;
}

export function MonoCell({ children }: { children: ReactNode }) {
    return <span className="font-mono text-zinc-200">{children}</span>;
}

/** The one action every page shows, with the recent-trade tag stacked under it. */
export function ActionCell({ row, rec }: { row: PositionRow; rec?: RecommendationRecord | null }) {
    const stance = stanceOf(rec) ?? row.action;
    return (
        <span className="inline-flex flex-col items-start gap-0.5">
            {stance
                ? <span className={`rounded border px-1.5 py-0.5 text-[11px] font-bold ${getActionBadgeClass(stance)}`}>{stance}</span>
                : <span className="text-zinc-600">—</span>}
            <RecentTradeTag rec={rec} />
        </span>
    );
}

/** The earnings date; amber and pulsing within a week, yellow within three weeks. */
export function EarningsCell({ date, days }: { date: string | null | undefined; days: number | null | undefined }) {
    if (!date) return <span className="text-zinc-600">—</span>;
    const near = days != null && days >= 0 && days <= 7;
    const soon = days != null && days > 7 && days <= 21;
    const suffix = days == null ? '' : days === 0 ? ' (today!)' : days > 0 ? ` (${days}d)` : ` (${Math.abs(days)}d ago)`;
    const tone = near ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40 animate-pulse'
        : soon ? 'bg-yellow-500/10 text-yellow-300 border border-yellow-500/30' : 'text-zinc-400';
    return <span className={`inline-flex items-center rounded px-1.5 py-0.5 font-mono text-[11px] font-medium ${tone}`}>{date}{suffix}</span>;
}
