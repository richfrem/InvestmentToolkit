/**
 * Purpose: render the shared reward-versus-risk columns identically on every holdings table.
 * Layer: Frontend / UI. Usage: <RiskRewardCell columnId="rr_ratio" rec={recommendation} />.
 * Key Functions: RiskRewardCell — one cell per column id; ReduceCandidatesChip — counted filter toggle.
 * Key Input Dependencies: RecommendationRecord from the recommendations context; utils/riskReward.
 */
import type { RecommendationRecord } from '../services/api';
import {
    alignmentStyle, formatRewardRisk, formatSignedPct, verdictStyle, type RiskRewardColumnId,
} from '../utils/riskReward';
import { ValuationRangeBar } from './ValuationRangeBar';

const DASH = <span className="text-slate-600 text-xs">—</span>;

function RatioPill({ rec }: { rec: RecommendationRecord }) {
    const view = rec.risk_reward!;
    if (view.reward_risk == null && !view.no_modelled_downside) return DASH;
    const tone = verdictStyle(view.verdict);
    const title = view.no_modelled_downside
        ? 'Every saved scenario is above today\'s price'
        : `Expected gain ${formatSignedPct(view.expected_gain_pct)} against expected loss `
            + `${formatSignedPct(view.expected_loss_pct == null ? null : -view.expected_loss_pct)}; `
            + `bear case ${formatSignedPct(view.downside_to_bear_pct)}. ${tone.label} reward for the risk.`;
    return (
        <span title={title} className={`inline-flex items-center rounded border px-1.5 py-0.5 font-mono text-[11px] font-bold ${tone.text} ${tone.bg} ${tone.border}`}>
            {formatRewardRisk(view)}
        </span>
    );
}

function LossOdds({ value }: { value: number | null }) {
    if (value == null) return DASH;
    const colour = value >= 60 ? 'bg-rose-400' : value >= 40 ? 'bg-amber-400' : 'bg-emerald-400';
    return (
        <span className="inline-flex items-center gap-1.5" title={`${value.toFixed(0)}% of scenario probability is below today's price`}>
            <span className="h-1.5 w-10 overflow-hidden rounded-full bg-slate-800">
                <span className={`block h-full ${colour}`} style={{ width: `${Math.min(100, value)}%` }} />
            </span>
            <span className="font-mono text-[11px] text-slate-300">{value.toFixed(0)}%</span>
        </span>
    );
}

function SupportPips({ rec }: { rec: RecommendationRecord }) {
    const support = rec.support;
    if (!support || support.level === 'NONE') return <span className="text-slate-600 text-xs" title="No saved valuation">None</span>;
    const title = `${support.score} of ${support.max} evidence checks pass. `
        + support.checks.map(check => `${check.ok ? '✓' : '✕'} ${check.label}: ${check.note}`).join('. ') + '.';
    return (
        <span role="img" aria-label={`Valuation support ${support.score} of ${support.max}`} title={title} className="inline-flex items-center gap-1">
            {support.checks.map(check => (
                <span key={check.id} data-ok={check.ok}
                    className={`h-2.5 w-2.5 rounded-sm ${check.ok ? 'bg-emerald-400' : 'bg-slate-700 ring-1 ring-inset ring-slate-600'}`} />
            ))}
        </span>
    );
}

/** Standing-decision relations that need the owner's attention, mapped to the chip's status. */
const DECISION_STATUS: Record<string, 'CONFLICT' | 'REVIEW'> = { CONFLICT: 'CONFLICT', OUTDATED: 'REVIEW', UNCLEAR: 'REVIEW', WAITS: 'REVIEW' };

function AlignmentChip({ rec }: { rec: RecommendationRecord }) {
    // A disagreement with the owner's own standing decision outranks the reward:risk cross-check.
    const decisionStatus = DECISION_STATUS[rec.decision_check?.relation ?? ''];
    const alignment = decisionStatus
        ? { status: decisionStatus, note: rec.decision_check!.note }
        : rec.risk_reward!.alignment;
    const tone = alignmentStyle(alignment.status);
    return (
        <span title={alignment.note} className={`inline-flex items-center gap-1 rounded border px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide ${tone.text} ${tone.bg} ${tone.border}`}>
            <span aria-hidden="true">{tone.icon}</span>{tone.label}
        </span>
    );
}

const DEBT_TONES: Record<string, string> = {
    SEVERE: 'text-rose-300 border-rose-500/50 bg-rose-500/10',
    HIGH: 'text-orange-300 border-orange-500/50 bg-orange-500/10',
    MODERATE: 'text-amber-300/90 border-amber-500/30 bg-transparent',
    UNCHECKED: 'text-slate-400 border-slate-600 border-dashed bg-transparent',
};

/**
 * Debt badge beside the check: the leverage grade saved with the valuation, a rate that is too
 * low for equity earnings, or "debt ?" when the valuation was never checked for debt.
 * Low leverage with a sound rate shows nothing.
 */
export function DebtBadge({ rec }: { rec: RecommendationRecord }) {
    const debt = rec.debt;
    if (!debt || debt.status === 'NONE') return null;
    const key = debt.status === 'NOT_ASSESSED' ? 'UNCHECKED'
        : debt.rate_status === 'MISMATCH' && !['HIGH', 'SEVERE'].includes(debt.tier ?? '') ? 'HIGH' : debt.tier ?? '';
    if (!DEBT_TONES[key]) return null;
    const label = key === 'UNCHECKED' ? 'Debt ?' : debt.rate_status === 'MISMATCH' ? 'Rate low' : `Debt ${debt.tier!.toLowerCase()}`;
    const was = debt.previous_fair_value != null ? ` Fair value before this adjustment: $${debt.previous_fair_value.toFixed(2)}.` : '';
    return (
        <span title={`${debt.note}.${was}`}
            className={`inline-flex items-center rounded border px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide ${DEBT_TONES[key]}`}>
            {label}
        </span>
    );
}

/** One cell of the shared columns; shows a dash rather than a guess when data is missing. */
export function RiskRewardCell({ columnId, rec, hideValues = false }: {
    columnId: RiskRewardColumnId; rec?: RecommendationRecord | null; hideValues?: boolean;
}) {
    const view = rec?.risk_reward;
    if (!rec || !view) return DASH;
    switch (columnId) {
        case 'rr_range': return <ValuationRangeBar rec={rec} hideValues={hideValues} />;
        case 'rr_ratio': return <RatioPill rec={rec} />;
        case 'rr_lossOdds': return <LossOdds value={view.loss_odds_pct} />;
        case 'rr_support': return <SupportPips rec={rec} />;
        case 'rr_check': return <span className="inline-flex flex-wrap items-center gap-1"><AlignmentChip rec={rec} /><DebtBadge rec={rec} /></span>;
        case 'rr_premium': {
            if (view.premium_pct == null) return DASH;
            const above = view.premium_pct > 0;
            return (
                <span title={above ? 'Price is above the saved fair value' : 'Price is below the saved fair value'}
                    className={`font-mono text-xs font-bold ${above ? 'text-rose-300' : 'text-emerald-300'}`}>
                    {formatSignedPct(view.premium_pct)}
                </span>
            );
        }
        case 'rr_weightGap': {
            if (view.weight_gap_pp == null) return DASH;
            const over = view.weight_gap_pp > 0;
            return (
                <span className={`font-mono text-xs ${Math.abs(view.weight_gap_pp) < 0.25 ? 'text-slate-400' : over ? 'text-amber-300' : 'text-sky-300'}`}>
                    {over ? '+' : view.weight_gap_pp < 0 ? '−' : ''}{Math.abs(view.weight_gap_pp).toFixed(1)}pp
                </span>
            );
        }
    }
}

/**
 * The table's valuation columns as one compact row, for cards: range bar, gap to fair value,
 * reward:risk, evidence checks and the debt badge. Renders nothing without a saved valuation.
 */
export function ValuationStrip({ rec, hideValues = false }: { rec?: RecommendationRecord | null; hideValues?: boolean }) {
    if (!rec?.risk_reward || rec.fair_value == null) return null;
    const cell = (columnId: RiskRewardColumnId) => <RiskRewardCell columnId={columnId} rec={rec} hideValues={hideValues} />;
    const labelled = (label: string, columnId: RiskRewardColumnId) => (
        <span className="inline-flex items-center gap-1.5">
            <span className="text-[9px] font-semibold uppercase tracking-wider text-slate-500">{label}</span>{cell(columnId)}
        </span>
    );
    return (
        <div role="group" aria-label={`${rec.ticker} valuation`} className="mb-2 flex flex-wrap items-center gap-x-4 gap-y-2">
            <div className="w-56 shrink-0">{cell('rr_range')}</div>
            {labelled('vs fair value', 'rr_premium')}
            {labelled('reward:risk', 'rr_ratio')}
            {labelled('support', 'rr_support')}
            <DebtBadge rec={rec} />
        </div>
    );
}

/** Counted toggle for held positions whose reward no longer covers the risk. */
export function ReduceCandidatesChip({ count, active, onToggle }: { count: number; active: boolean; onToggle: () => void }) {
    return (
        <button type="button" aria-pressed={active} onClick={onToggle}
            title="Held positions that are above fair value, or whose expected loss is larger than the expected gain"
            className={`inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-[11px] font-black transition-all ${
                active ? 'bg-rose-600 text-white border-rose-500 shadow-md shadow-rose-900/30'
                    : count > 0 ? 'bg-rose-950/40 text-rose-300 border-rose-800/60 hover:bg-rose-900/50'
                        : 'bg-slate-900/40 text-slate-500 border-slate-800 hover:text-slate-300'}`}>
            <span>⚖️ Reduce candidates</span>
            <span className={`rounded-full px-1.5 text-[9px] font-bold ${active ? 'bg-rose-800 text-white' : 'bg-rose-950 text-rose-300 border border-rose-700/50'}`}>{count}</span>
        </button>
    );
}
