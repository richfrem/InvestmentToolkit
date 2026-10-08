/**
 * Purpose: one presentation contract for reward-versus-risk columns on every holdings table.
 * Layer: Frontend / Utils. Usage: RISK_REWARD_COLUMNS, riskRewardRowFields(rec), verdictStyle(v).
 * Key Functions: riskRewardRowFields — sortable values; isReduceCandidate; mergeColumnPrefs;
 *     verdictStyle, alignmentStyle, formatRewardRisk — shared labels and colours;
 *     rangeGeometry, riskRewardRowAccent — range-bar positions and row accent;
 *     fairValueGap — the one live gain/upside-to-fair-value calculation for table columns.
 *     stanceOf — the one action every page shows; actedOn, compareByActionPriority — action sort.
 * Key Input Dependencies: RecommendationRecord.risk_reward / support from risk_reward.py.
 *     Nothing here estimates a valuation; it only formats saved server values.
 */
import type { RecommendationRecord, RiskRewardView } from '../services/api';
import { getActionPriority } from './actionColors';

export type RiskRewardColumnId =
    'rr_range' | 'rr_premium' | 'rr_ratio' | 'rr_lossOdds' | 'rr_weightGap' | 'rr_support' | 'rr_check';

export interface RiskRewardColumn {
    id: RiskRewardColumnId;
    label: string;
    defaultOn: boolean;
    align: 'left' | 'right';
    width: number;
    /** Header tooltip: what the column means, in one sentence. */
    title: string;
}

/** Column order here is the display order after the Action column. */
export const RISK_REWARD_COLUMNS: RiskRewardColumn[] = [
    { id: 'rr_range', label: 'Valuation Range', defaultOn: true, align: 'left', width: 190,
        title: 'Where the price sits between the saved bear and bull values. The white tick is fair value: a marker to its right means the price is above fair value.' },
    { id: 'rr_premium', label: 'vs Fair Value', defaultOn: true, align: 'right', width: 125,
        title: 'Price above (+) or below (−) the saved fair value.' },
    { id: 'rr_ratio', label: 'Reward:Risk', defaultOn: true, align: 'right', width: 120,
        title: 'Probability-weighted gain divided by probability-weighted loss across the bear, base and bull values at this price. Below 1 means the expected loss is larger than the expected gain.' },
    { id: 'rr_lossOdds', label: 'Loss Odds', defaultOn: false, align: 'right', width: 90,
        title: 'Share of scenario probability that sits below today\'s price.' },
    { id: 'rr_weightGap', label: 'vs Target', defaultOn: false, align: 'right', width: 85,
        title: 'Current weight minus target weight, in percentage points. Context only: targets never drive the action.' },
    { id: 'rr_support', label: 'Support', defaultOn: true, align: 'left', width: 90,
        title: 'Evidence behind the fair value: recent, full scenario range, audited discount rate, forward-earnings review.' },
    { id: 'rr_check', label: 'Check', defaultOn: true, align: 'left', width: 105,
        title: 'Whether the action agrees with reward versus risk.' },
];

const COLUMN_IDS = new Set<string>(RISK_REWARD_COLUMNS.map(column => column.id));
const CHECK_RANK: Record<string, number> = { CONFLICT: 0, REVIEW: 1, UNKNOWN: 2, ALIGNED: 3 };
/** Sort rank when the owner's standing decision disagrees with the action (worst first). */
const DECISION_RANK: Record<string, number> = { CONFLICT: 0, OUTDATED: 1, UNCLEAR: 1, WAITS: 1 };
/** Sort value for "no modelled downside": better than any finite ratio. */
const NO_DOWNSIDE_SORT = 999;

export function isRiskRewardColumn(id: string): id is RiskRewardColumnId {
    return COLUMN_IDS.has(id);
}

export type RiskRewardRowFields = Record<RiskRewardColumnId, number | null>;

/** Sortable numbers for each column; null sorts as missing. */
export function riskRewardRowFields(rec?: RecommendationRecord | null): RiskRewardRowFields {
    const view = rec?.risk_reward;
    const ratio = view?.no_modelled_downside ? NO_DOWNSIDE_SORT : view?.reward_risk ?? null;
    return {
        rr_range: view?.premium_pct ?? null,
        rr_premium: view?.premium_pct ?? null,
        rr_ratio: ratio,
        rr_lossOdds: view?.loss_odds_pct ?? null,
        rr_weightGap: view?.weight_gap_pp ?? null,
        rr_support: rec?.support && rec.support.level !== 'NONE' ? rec.support.score : null,
        rr_check: view ? Math.min(CHECK_RANK[view.alignment.status] ?? 3, DECISION_RANK[rec?.decision_check?.relation ?? ''] ?? 3) : null,
    };
}

/**
 * The action to show for a ticker: the valuation action, or the stance reconciled with the
 * owner's standing decision when they disagree (standing_decision_check.py). Every page uses
 * this, so a card and a table never show different actions for the same position.
 */
export function stanceOf(rec?: RecommendationRecord | null): string | null {
    return rec?.decision_check?.effective ?? rec?.action ?? null;
}

/** True when recent filled trades already follow the action (recent_trades.py). */
export function actedOn(rec?: RecommendationRecord | null): boolean {
    return rec?.recent_trades?.context?.status === 'ACTED';
}

/** Action-column sort: open actions by priority, then upside; actions already acted on go last. */
export function compareByActionPriority(dir: 'asc' | 'desc') {
    type Row = { action?: string | null; actedOn?: boolean; upside?: number | null };
    return (a: Row, b: Row): number => {
        if (!!a.actedOn !== !!b.actedOn) return a.actedOn ? 1 : -1;
        const pA = getActionPriority(a.action), pB = getActionPriority(b.action);
        if (pA !== pB) return dir === 'asc' ? pA - pB : pB - pA;
        return (b.upside ?? -999) - (a.upside ?? -999);
    };
}

/**
 * Dollar gap and upside from a live price to fair value, for the Gain and Upside columns.
 * Tables pass the recommendation's fair value so these columns agree with the action.
 */
export function fairValueGap(fairValue: number | null | undefined, price: number | null | undefined) {
    if (!fairValue || !price || price <= 0) return { gainLoss: null, upside: null };
    return { gainLoss: fairValue - price, upside: ((fairValue - price) / price) * 100 };
}

export function isReduceCandidate(rec?: RecommendationRecord | null): boolean {
    return rec?.risk_reward?.reduce_candidate === true;
}

export function formatRewardRisk(view?: RiskRewardView | null): string {
    if (!view) return '—';
    if (view.no_modelled_downside) return 'No downside';
    return view.reward_risk == null ? '—' : `${view.reward_risk.toFixed(1)}×`;
}

export function formatSignedPct(value: number | null | undefined, digits = 0): string {
    if (value == null || !Number.isFinite(value)) return '—';
    return `${value > 0 ? '+' : value < 0 ? '−' : ''}${Math.abs(value).toFixed(digits)}%`;
}

interface Tone { text: string; bg: string; border: string; fill: string; label: string }

/** One colour language everywhere: green favourable, amber thin, red unfavourable, grey unrated. */
const VERDICT_TONES: Record<RiskRewardView['verdict'], Tone> = {
    FAVOURABLE:   { text: 'text-emerald-300', bg: 'bg-emerald-500/15', border: 'border-emerald-500/40', fill: '#34d399', label: 'Favourable' },
    THIN:         { text: 'text-amber-300',   bg: 'bg-amber-500/15',   border: 'border-amber-500/40',   fill: '#fbbf24', label: 'Thin' },
    UNFAVOURABLE: { text: 'text-rose-300',    bg: 'bg-rose-500/15',    border: 'border-rose-500/40',    fill: '#fb7185', label: 'Unfavourable' },
    UNRATED:      { text: 'text-slate-400',   bg: 'bg-slate-500/10',   border: 'border-slate-600/40',   fill: '#94a3b8', label: 'Unrated' },
};

export function verdictStyle(verdict?: RiskRewardView['verdict'] | null): Tone {
    return VERDICT_TONES[verdict ?? 'UNRATED'] ?? VERDICT_TONES.UNRATED;
}

const ALIGNMENT_TONES: Record<RiskRewardView['alignment']['status'], Tone & { icon: string }> = {
    ALIGNED:  { ...VERDICT_TONES.FAVOURABLE, label: 'Aligned', icon: '✓' },
    REVIEW:   { ...VERDICT_TONES.THIN, label: 'Review', icon: '!' },
    CONFLICT: { ...VERDICT_TONES.UNFAVOURABLE, label: 'Conflict', icon: '✕' },
    UNKNOWN:  { ...VERDICT_TONES.UNRATED, label: 'No data', icon: '?' },
};

export function alignmentStyle(status?: RiskRewardView['alignment']['status'] | null) {
    return ALIGNMENT_TONES[status ?? 'UNKNOWN'] ?? ALIGNMENT_TONES.UNKNOWN;
}

/** Percent positions (0–100) for fair value, base and price on the bear→bull scale. */
export function rangeGeometry(bear: number, bull: number, fairValue: number, price: number, base?: number | null) {
    const span = bull - bear;
    const at = (value: number) => Math.min(100, Math.max(0, ((value - bear) / span) * 100));
    return {
        fair: at(fairValue),
        base: typeof base === 'number' && Number.isFinite(base) ? at(base) : null,
        price: at(price),
        outside: price < bear ? 'below' as const : price > bull ? 'above' as const : null,
    };
}

/** Left accent for a table row: red when it is a reduce candidate, amber when the action needs a second look. */
export function riskRewardRowAccent(rec?: RecommendationRecord | null): string {
    const view = rec?.risk_reward;
    if (!view) return '';
    if (view.reduce_candidate) return 'shadow-[inset_3px_0_0_0_#fb7185]';
    if (view.alignment.status === 'CONFLICT' || view.alignment.status === 'REVIEW') return 'shadow-[inset_3px_0_0_0_#fbbf24]';
    return '';
}

interface SavedColumnPrefs { visible: string[]; columnOrder: string[] }
interface ColumnMeta { id: string; always?: boolean; defaultOn: boolean }

/**
 * Merge saved table preferences with the current column list. Columns the saved
 * order has never seen are brand-new: default-on ones become visible, and all of
 * them are placed after `anchor` (in definition order) instead of at the far right.
 */
export function mergeColumnPrefs(prefs: SavedColumnPrefs | null, columns: ColumnMeta[], anchor: string) {
    const ids = columns.map(column => column.id);
    const defaults = columns.filter(column => column.always || column.defaultOn).map(column => column.id);
    if (!prefs) return { visible: new Set(defaults), order: ids };
    const valid = new Set(ids);
    const savedOrder = prefs.columnOrder.filter(id => valid.has(id));
    const known = new Set(savedOrder);
    const brandNew = ids.filter(id => !known.has(id));
    const visible = new Set(prefs.visible.filter(id => valid.has(id)));
    for (const id of brandNew) if (defaults.includes(id)) visible.add(id);
    const at = savedOrder.indexOf(anchor);
    const order = at < 0 ? [...savedOrder, ...brandNew]
        : [...savedOrder.slice(0, at + 1), ...brandNew, ...savedOrder.slice(at + 1)];
    return { visible, order };
}
