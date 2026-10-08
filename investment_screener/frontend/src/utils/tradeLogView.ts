/**
 * Purpose: one place for how the Trade Log page orders, limits and dates its entries.
 * Layer: Frontend / Utils. Usage: recentFirst(entries), latestFilledTrade(entries), TRADE_SYNC_COMMAND.
 * Key Functions: recentFirst — newest trade date first; latestFilledTrade — freshness of executed trades;
 *     daysSince — whole calendar days from a trade date to today; tradeDateParts — day and order time for display.
 * Key Input Dependencies: TradeLogEntry rows from GET /api/trading/log. `date` is YYYY-MM-DD, or an ISO
 *     timestamp in US Eastern time for imported market orders; its first ten characters are always the trade date.
 */
import type { TradeLogEntry, TradeLogStatus } from '../services/api';

export type TradeLogTab = 'all' | 'open' | 'filled' | 'other';

/**
 * The page is about what is live at the broker: open orders and executed trades.
 * Planned and cancelled entries stay in the database and sit behind the "other" view.
 * `inactive` is a submitted limit or stop order that is resting, so it is an open order.
 */
export const TRADE_LOG_TAB_STATUSES: Record<TradeLogTab, TradeLogStatus[]> = {
    all:    ['submitted', 'inactive', 'filled'],
    open:   ['submitted', 'inactive'],
    filled: ['filled'],
    other:  ['suggested', 'logged', 'cancelled'],
};

/** Rows shown before "Show all" is pressed: about three months of trading at the owner's pace. */
export const TRADE_LOG_PAGE_SIZE = 100;
/** Executed trades come from the broker through the agent, which needs a Questrade sign-in. */
export const TRADE_SYNC_COMMAND = '/questrade-sync-portfolio';
/** Days without a newly recorded fill after which the page nudges a refresh. */
export const TRADE_REFRESH_NUDGE_DAYS = 7;

/** Newest trade date first; entries on the same day keep newest-logged first. */
export function recentFirst(entries: TradeLogEntry[]): TradeLogEntry[] {
    return [...entries].sort((a, b) =>
        String(b.date ?? '').localeCompare(String(a.date ?? '')) || String(b.loggedAt ?? '').localeCompare(String(a.loggedAt ?? '')));
}

/** The most recent executed trade, or null when none has been recorded. */
export function latestFilledTrade(entries: TradeLogEntry[]): TradeLogEntry | null {
    return recentFirst(entries.filter(entry => entry.status === 'filled'))[0] ?? null;
}

/** Whole calendar days from a YYYY-MM-DD trade date to `today`; null when the date is unusable. */
export function daysSince(isoDate: string | null | undefined, today: Date = new Date()): number | null {
    const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(isoDate ?? ''));
    if (!match) return null;
    const then = Date.UTC(Number(match[1]), Number(match[2]) - 1, Number(match[3]));
    const now = Date.UTC(today.getFullYear(), today.getMonth(), today.getDate());
    return Math.round((now - then) / 86_400_000);
}

/**
 * Split a saved trade date into its day and, when the broker supplied one, the order time.
 * The time is shown exactly as stored (US Eastern, the market's clock), never converted to the
 * viewer's time zone, so it always agrees with the trade date beside it.
 */
export function tradeDateParts(value: string | null | undefined): { day: string; time: string | null } {
    const match = /^(\d{4}-\d{2}-\d{2})(?:T(\d{2}):(\d{2}))?/.exec(String(value ?? ''));
    if (!match) return { day: String(value ?? '—') || '—', time: null };
    if (match[2] == null) return { day: match[1], time: null };
    const hour = Number(match[2]);
    return { day: match[1], time: `${hour % 12 || 12}:${match[3]} ${hour < 12 ? 'AM' : 'PM'} ET` };
}
