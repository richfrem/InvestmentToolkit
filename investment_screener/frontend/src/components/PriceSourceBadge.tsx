interface Props {
    priceSource: string | null;
    lastRefreshedAt: Date | null;
}

/** Maps a backend `price_source` value to its badge label/color.
 *
 * `domain_model_sqlite` (Wave 3's SQLite-backed read, the common case once
 * /refresh-prices has run at least once) is distinct from a raw `yfinance`
 * fallback (no priced SQLite data yet) — collapsing them into one "yfinance"
 * label made a healthy, live SQLite refresh look identical to the
 * before-first-sync fallback state.
 */
export function describeSource(priceSource: string | null): { label: string; color: 'emerald' | 'zinc' } {
    switch (priceSource) {
        case 'tradingview':
            return { label: 'TV Live', color: 'emerald' };
        case 'domain_model_sqlite':
            return { label: 'SQLite', color: 'emerald' };
        default:
            return { label: 'yfinance', color: 'zinc' };
    }
}

export function PriceSourceBadge({ priceSource, lastRefreshedAt }: Props) {
    if (!lastRefreshedAt) return null;
    const { label, color } = describeSource(priceSource);
    const isLive = color === 'emerald';
    return (
        <div className={`flex items-center gap-1 text-xs ${isLive ? 'text-emerald-400' : 'text-zinc-500'}`}>
            <span className={`w-1.5 h-1.5 rounded-full inline-block ${isLive ? 'bg-emerald-400' : 'bg-zinc-500'}`} />
            {label} · {lastRefreshedAt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
        </div>
    );
}
