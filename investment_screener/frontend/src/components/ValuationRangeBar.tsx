/**
 * Purpose: show at a glance where the price sits between the saved bear, fair and bull values.
 * Layer: Frontend / UI. Usage: <ValuationRangeBar rec={recommendation} />.
 * Key Functions: ValuationRangeBar — range bar drawn from utils/riskReward rangeGeometry.
 * Key Input Dependencies: RecommendationRecord scenarios, fair_value, price and risk_reward verdict.
 *     Draws saved server values only; it never derives a fair value or an action.
 */
import type { RecommendationRecord } from '../services/api';
import { fmtDollar, fmtPrice } from '../utils/formatters';
import { rangeGeometry, verdictStyle } from '../utils/riskReward';

const isNum = (value: unknown): value is number => typeof value === 'number' && Number.isFinite(value);

function summary(rec: RecommendationRecord): string {
    const view = rec.risk_reward;
    const premium = view?.premium_pct;
    const size = isNum(premium) ? `${Math.abs(premium).toFixed(0)}%` : '';
    const position = !isNum(premium) ? 'no fair value comparison'
        : premium > 0 ? `${size} above fair value` : premium < 0 ? `${size} below fair value` : 'at fair value';
    return `Price ${fmtPrice(rec.price)}: ${position}. Bear ${fmtDollar(rec.scenarios?.bear)}, `
        + `fair value ${fmtDollar(rec.fair_value)}, bull ${fmtDollar(rec.scenarios?.bull)}.`;
}

/** Bear→bull bar with a fair-value tick and a price marker coloured by reward versus risk. */
export function ValuationRangeBar({ rec, hideValues = false }: { rec?: RecommendationRecord | null; hideValues?: boolean }) {
    const bear = rec?.scenarios?.bear;
    const bull = rec?.scenarios?.bull;
    if (!rec || !isNum(bear) || !isNum(bull) || !isNum(rec.fair_value) || !isNum(rec.price) || bull <= bear) {
        return <span className="text-slate-600 text-xs" title="No saved bear and bull values for this position">No range</span>;
    }
    const marks = rangeGeometry(bear, bull, rec.fair_value, rec.price, rec.scenarios?.base);
    const tone = verdictStyle(rec.risk_reward?.verdict);
    const label = summary(rec);
    return (
        <div role="img" aria-label={label} title={label} className="w-full min-w-[120px]">
            <div className="relative h-3 rounded-full overflow-hidden bg-slate-800">
                {/* Left of fair value: price here is below fair value. Right: above it. */}
                <div className="absolute inset-y-0 left-0 bg-emerald-500/25" style={{ width: `${marks.fair}%` }} />
                <div className="absolute inset-y-0 right-0 bg-rose-500/25" style={{ width: `${100 - marks.fair}%` }} />
                {marks.base != null && (
                    <div className="absolute inset-y-0 w-px bg-slate-400/50" style={{ left: `${marks.base}%` }} />
                )}
                <div data-mark="fair" className="absolute inset-y-0 w-0.5 bg-white" style={{ left: `calc(${marks.fair}% - 1px)` }} />
            </div>
            <div className="relative h-0">
                <div data-mark="price" data-outside={marks.outside ?? undefined}
                    className="absolute -top-[15px] h-[18px] w-[18px] -translate-x-1/2 rounded-full border-2 border-slate-950 shadow"
                    style={{ left: `${marks.price}%`, backgroundColor: tone.fill }} />
            </div>
            <div className="mt-1 flex justify-between text-[9px] font-mono text-slate-500 leading-none">
                <span>{hideValues ? '$••' : fmtDollar(bear)}</span>
                <span className="text-slate-300">{hideValues ? 'FV $••' : `FV ${fmtDollar(rec.fair_value)}`}</span>
                <span>{hideValues ? '$••' : fmtDollar(bull)}</span>
            </div>
        </div>
    );
}
