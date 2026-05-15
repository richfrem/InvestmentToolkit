interface Props {
    priceSource: string | null;
    lastRefreshedAt: Date | null;
}

export function PriceSourceBadge({ priceSource, lastRefreshedAt }: Props) {
    if (!lastRefreshedAt) return null;
    const isTV = priceSource === 'tradingview';
    return (
        <div className={`flex items-center gap-1 text-xs ${isTV ? 'text-emerald-400' : 'text-zinc-500'}`}>
            <span className={`w-1.5 h-1.5 rounded-full inline-block ${isTV ? 'bg-emerald-400' : 'bg-zinc-500'}`} />
            {isTV ? 'TV Live' : 'yfinance'} · {lastRefreshedAt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
        </div>
    );
}
