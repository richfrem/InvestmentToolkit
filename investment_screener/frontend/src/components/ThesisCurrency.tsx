/**
 * ThesisCurrency.tsx - The "Current developments" panel at the top of a thesis page.
 *
 * Purpose:
 *     Shows the one short note the daily, weekly and review skills keep current for a thesis
 *     document: the most relevant recent news and analysis for the stocks it covers, dated, and
 *     flagged when it is more than a week old. When no note exists yet it says so and who fills
 *     it in. It reads what the thesis route returns; it never writes.
 *
 * Layer: Frontend / Components
 *
 * Usage Examples:
 *     <ThesisCurrency currency={data.currency} />
 *
 * Key Functions (Index):
 *     - ThesisCurrency: the panel
 *
 * Key Input Dependencies:
 *     - currencyNote.ts (CurrencyNote, currencyAgeLabel), MarkdownContent
 *
 * Key Output Dependencies:
 *     - ThesisViewModal
 */
import MarkdownContent from './MarkdownContent';
import { currencyAgeLabel, type CurrencyNote } from './currencyNote';

export function ThesisCurrency({ currency }: { currency: CurrencyNote | null | undefined }) {
    if (!currency) {
        return (
            <section aria-label="Current developments" className="not-prose mb-6 rounded-lg border border-zinc-700 bg-zinc-900/60 p-4">
                <h3 className="text-sm font-bold text-white">Current developments</h3>
                <p className="mt-1 text-xs text-zinc-500">
                    Nothing recorded yet. The daily loop, news sweep and weekly review add the latest news and analysis for this thesis here.
                </p>
            </section>
        );
    }
    return (
        <section aria-label="Current developments"
            className={`not-prose mb-6 rounded-lg border p-4 ${currency.stale ? 'border-amber-500/40 bg-amber-500/5' : 'border-indigo-500/30 bg-indigo-500/5'}`}>
            <div className="mb-2 flex flex-wrap items-baseline justify-between gap-2">
                <h3 className="text-sm font-bold text-white">Current developments</h3>
                <span className={`text-xs ${currency.stale ? 'font-bold text-amber-400' : 'text-zinc-400'}`}>
                    as of {currency.asOf} · {currencyAgeLabel(currency.ageDays)}{currency.stale ? ' · out of date' : ''}
                </span>
            </div>
            <div className="prose prose-sm prose-invert max-w-none">
                <MarkdownContent content={currency.markdown} />
            </div>
        </section>
    );
}
