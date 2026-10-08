/**
 * @vitest-environment jsdom
 * Purpose: the shared reward-versus-risk columns show saved server values and never guess.
 * Layer: Frontend integration. Usage: vitest run tests/RiskRewardColumns.test.tsx.
 * Key Functions: range bar, ratio pill, support pips, alignment chip, reduce chip, prefs merge.
 * Key Input Dependencies: real components; RecommendationRecord shaped like risk_reward.py output.
 */
import { afterEach, expect, it } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { ReduceCandidatesChip, RiskRewardCell } from '../src/components/RiskRewardCell';
import { ValuationRangeBar } from '../src/components/ValuationRangeBar';
import type { RecommendationRecord } from '../src/services/api';
import { heatmapPrice } from '../src/utils/heatmapPrice';
import {
    RISK_REWARD_COLUMNS, fairValueGap, isReduceCandidate, mergeColumnPrefs, rangeGeometry, riskRewardRowAccent, riskRewardRowFields,
} from '../src/utils/riskReward';

afterEach(cleanup);

/** A held position above fair value: the reduce case. */
const above = {
    ticker: 'PLTR', action: 'MAINTAIN', reason: '', valuation: 'HOLD', upside_pct: -6.8, current_weight_pct: 2.9,
    held: true, fair_value: 178.93, price: 192.07, standing_decision: null,
    scenarios: { bear: 28.67, base: 146.68, bull: 393.7 },
    risk_reward: {
        premium_pct: 7.3, reward_risk: 0.79, expected_gain_pct: 26.2, expected_loss_pct: 33.1, loss_odds_pct: 75,
        downside_to_bear_pct: -85.1, upside_to_bull_pct: 105, no_modelled_downside: false, verdict: 'UNFAVOURABLE',
        reduce_candidate: true, reduce_reasons: ['7% above fair value'], weight_gap_pp: 0.4,
        alignment: { status: 'REVIEW', note: 'MAINTAIN but reward:risk 0.8' },
    },
    support: { level: 'PARTIAL', score: 2, max: 4, age_days: 37, checks: [
        { id: 'fresh', label: 'Recent valuation', ok: true, note: 'Saved 37 days ago' },
        { id: 'scenarios', label: 'Scenario range', ok: true, note: 'Bear, base and bull saved with probabilities' },
        { id: 'rate_audit', label: 'Audited discount rate', ok: false, note: 'No audited discount rate; rate basis unverified' },
        { id: 'forward_review', label: 'Forward-earnings review', ok: false, note: 'No forward-earnings review recorded with this valuation' },
    ] },
} as RecommendationRecord;

const below = { ...above, ticker: 'CRWV', action: 'ACCUMULATE', price: 91.72, fair_value: 249.87,
    scenarios: { bear: 23.22, base: 195.94, bull: 724.69 },
    risk_reward: { ...above.risk_reward!, premium_pct: -63.3, reward_risk: 8.7, verdict: 'FAVOURABLE', reduce_candidate: false,
        reduce_reasons: [], alignment: { status: 'ALIGNED', note: 'ACCUMULATE agrees with reward:risk 8.7' } },
} as RecommendationRecord;

it('places the price marker right of the fair-value tick when the price is above fair value', () => {
    const { container } = render(<ValuationRangeBar rec={above} />);
    const left = (mark: string) => parseFloat((container.querySelector(`[data-mark="${mark}"]`) as HTMLElement).style.left.replace('calc(', ''));
    expect(left('price')).toBeGreaterThan(left('fair'));
    expect(screen.getByRole('img').getAttribute('aria-label')).toContain('7% above fair value');
    cleanup();
    const under = render(<ValuationRangeBar rec={below} />).container;
    const leftUnder = (mark: string) => parseFloat((under.querySelector(`[data-mark="${mark}"]`) as HTMLElement).style.left.replace('calc(', ''));
    expect(leftUnder('price')).toBeLessThan(leftUnder('fair'));
    expect(screen.getByRole('img').getAttribute('aria-label')).toContain('63% below fair value');
});

it('clamps a price outside the scenario range and reports which side', () => {
    expect(rangeGeometry(10, 110, 60, 5)).toMatchObject({ price: 0, outside: 'below', fair: 50 });
    expect(rangeGeometry(10, 110, 60, 150)).toMatchObject({ price: 100, outside: 'above' });
    expect(rangeGeometry(10, 110, 60, 60, 35)).toMatchObject({ price: 50, outside: null, base: 25 });
});

it('shows no range instead of inventing one when scenarios are missing', () => {
    render(<ValuationRangeBar rec={{ ...above, scenarios: { bear: null, base: null, bull: null } }} />);
    expect(screen.getByText('No range')).toBeTruthy();
    expect(screen.queryByRole('img')).toBeNull();
});

it('renders reward:risk, premium, support and the action check from the saved record', () => {
    render(<>{RISK_REWARD_COLUMNS.map(column => <div key={column.id}><RiskRewardCell columnId={column.id} rec={above} /></div>)}</>);
    expect(screen.getByText('0.8×').className).toContain('text-rose-300');
    expect(screen.getByText('+7%').className).toContain('text-rose-300');
    expect(screen.getByText('75%')).toBeTruthy();
    expect(screen.getByText('+0.4pp')).toBeTruthy();
    const support = screen.getByRole('img', { name: 'Valuation support 2 of 4' });
    expect(support.querySelectorAll('[data-ok="true"]').length).toBe(2);
    expect(support.getAttribute('title')).toContain('No audited discount rate');
    expect(screen.getByText('Review').closest('span[title]')!.getAttribute('title')).toBe('MAINTAIN but reward:risk 0.8');
});

it('shows a dash for every column when the record has no reward-versus-risk view', () => {
    const legacy = { ...above, risk_reward: undefined, support: undefined } as RecommendationRecord;
    const { container } = render(<>{RISK_REWARD_COLUMNS.map(column => <RiskRewardCell key={column.id} columnId={column.id} rec={legacy} />)}</>);
    expect(container.textContent).toBe('—'.repeat(RISK_REWARD_COLUMNS.length));
});

it('labels a position with no modelled downside instead of an infinite ratio', () => {
    const safe = { ...below, risk_reward: { ...below.risk_reward!, reward_risk: null, no_modelled_downside: true } } as RecommendationRecord;
    render(<RiskRewardCell columnId="rr_ratio" rec={safe} />);
    expect(screen.getByText('No downside')).toBeTruthy();
    expect(riskRewardRowFields(safe).rr_ratio).toBeGreaterThan(riskRewardRowFields(below).rr_ratio!);
});

it('counts and toggles reduce candidates, and accents their rows', () => {
    let toggled = 0;
    render(<ReduceCandidatesChip count={[above, below].filter(isReduceCandidate).length} active={false} onToggle={() => { toggled++; }} />);
    const chip = screen.getByRole('button', { name: /Reduce candidates/ });
    expect(chip.textContent).toContain('1');
    expect(chip.getAttribute('aria-pressed')).toBe('false');
    fireEvent.click(chip);
    expect(toggled).toBe(1);
    expect(riskRewardRowAccent(above)).toContain('#fb7185');
    expect(riskRewardRowAccent(below)).toBe('');
});

it('sorts worst reward:risk and worst action check first', () => {
    expect(riskRewardRowFields(above).rr_ratio).toBeLessThan(riskRewardRowFields(below).rr_ratio!);
    expect(riskRewardRowFields(above).rr_check).toBeLessThan(riskRewardRowFields(below).rr_check!);
    expect(riskRewardRowFields(undefined)).toMatchObject({ rr_ratio: null, rr_support: null, rr_check: null });
});

it('shows brand-new default columns after Action for users with saved table preferences', () => {
    const columns = [
        { id: 'symbol', always: true, defaultOn: true }, { id: 'action', defaultOn: true },
        ...RISK_REWARD_COLUMNS, { id: 'fairValue', defaultOn: true }, { id: 'sector', defaultOn: false },
    ];
    const saved = { visible: ['symbol', 'fairValue'], columnOrder: ['symbol', 'fairValue', 'action', 'sector', 'retired'] };
    const merged = mergeColumnPrefs(saved, columns, 'action');
    expect(merged.order.slice(0, 5)).toEqual(['symbol', 'fairValue', 'action', 'rr_range', 'rr_premium']);
    expect(merged.order).not.toContain('retired');
    expect(merged.visible.has('rr_range')).toBe(true);
    expect(merged.visible.has('rr_lossOdds')).toBe(false); // new but default-off stays hidden
    expect(merged.visible.has('action')).toBe(false);      // an existing choice to hide is kept
    expect(mergeColumnPrefs(null, columns, 'action').order[2]).toBe('rr_range');
});

it('reads the heatmap price field and treats missing prices as unknown', () => {
    expect(heatmapPrice({ price: 24.61 })).toBe(24.61);
    expect(heatmapPrice({ price: 0 })).toBeNull();
    expect(heatmapPrice({ currentPrice: 24.61 } as never)).toBeNull();
    expect(heatmapPrice(undefined)).toBeNull();
});

it('computes the gain and upside columns from the recommendation fair value and a live price', () => {
    expect(fairValueGap(44.64, 46.31)).toEqual({ gainLoss: 44.64 - 46.31, upside: ((44.64 - 46.31) / 46.31) * 100 });
    expect(fairValueGap(null, 46.31)).toEqual({ gainLoss: null, upside: null });
    expect(fairValueGap(44.64, 0)).toEqual({ gainLoss: null, upside: null });
});
