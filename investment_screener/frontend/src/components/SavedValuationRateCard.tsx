/**
 * Purpose: show the persisted valuation rate and its evidence basis near core metrics.
 * Layer: Frontend / UI. Usage: <SavedValuationRateCard projection={savedProjection} />.
 * Key Functions: SavedValuationRateCard — saved-rate card with shared help popups.
 * Key Input Dependencies: saved API Projection; HelpModalProvider; valuationPresentation.
 */
import type { Projection } from '../services/api';
import { savedValuationRate } from '../utils/valuationPresentation';
import { fmtPrice } from '../utils/formatters';
import { HelpTrigger } from './HelpModal';

/** Display saved results only; rate estimation stays in the Python valuation workflow. */
export function SavedValuationRateCard({ projection }: { projection?: Projection | null }) {
    const rate = savedValuationRate(projection);
    return (
        <section aria-label="Saved valuation rate" className="bg-surface p-6 rounded-xl border border-slate-800 relative overflow-hidden hover:border-slate-700 transition-colors">
            <div className="absolute top-0 left-0 w-1 h-full bg-indigo-500 opacity-50" />
            <div className="flex items-center gap-2 mb-2">
                <h3 className="text-secondary font-medium uppercase tracking-wider text-sm">{rate.label}</h3>
                <HelpTrigger topicId={rate.topicId} size={14} />
            </div>
            <div className="text-3xl font-bold text-indigo-300">{rate.value}</div>
            <div className="mt-3 text-xs text-slate-400 space-y-1">
                <div className="flex justify-between items-center">
                    <span className="inline-flex items-center gap-1">Saved Fair Value <HelpTrigger topicId="fairValue" size={12} /></span>
                    <span className="text-text">{fmtPrice(projection?.aiThesis?.fairValue)}</span>
                </div>
                {rate.auditDate && <div className="flex justify-between"><span>Input audit date</span><span>{rate.auditDate}</span></div>}
            </div>
            <p className="text-xs text-slate-500 mt-3">{rate.status}</p>
        </section>
    );
}
