export interface PortfolioTotals {
    holdingsUSD: number;
    cashUSD: number;
    totalUSD: number;
    totalCAD: number;
    exchangeRate: number;
    timestamp: string;
    totalSource: 'tv_authoritative' | 'computed_fallback';
}

export interface PortfolioSnapshot {
    holdings: any[];
    totals: PortfolioTotals;
}

/**
 * Pure function — no I/O. Computes market_value per holding and all
 * portfolio totals in one pass. Call once at sync time; persist the
 * result; read it everywhere else.
 *
 * `authoritativeTotalUSD` — the TV broker's real combined equity (e.g. from
 * getAccountTotals()/totalEquityUSDCombined), when known. Never recompute
 * totalUSD from shares*price when this is available — the broker figure
 * includes cash and live pricing the holdings array doesn't fully capture,
 * and silently overwriting it with a weaker approximation is the exact
 * portfolio-total-validation bug this project has hit repeatedly.
 */
export function buildPortfolioSnapshot(
    holdings: any[],
    tvSnapshot: any,
    exchangeRate: number,
    authoritativeTotalUSD?: number | null
): PortfolioSnapshot {
    const enriched = holdings.map(h => ({
        ...h,
        market_value: (h.shares ?? 0) * (h.price ?? h.book_price ?? 0),
    }));

    const holdingsUSD = enriched
        .filter(h => (h.symbol || h.ticker) !== 'USD_CASH')
        .reduce((sum, h) => sum + (h.market_value ?? 0), 0);

    let cashUSD = (tvSnapshot?.snapshots ?? []).reduce(
        (sum: number, snap: any) => sum + (snap?.balances?.cashUSD ?? 0),
        0
    );

    // Fallback to portfolio USD_CASH holding if TV snapshot cash is missing/empty
    if (cashUSD === 0) {
        const cashHolding = enriched.find(h => (h.symbol || h.ticker) === 'USD_CASH');
        if (cashHolding) {
            cashUSD = cashHolding.market_value ?? cashHolding.shares ?? 0;
        }
    }

    const hasAuthoritativeTotal = authoritativeTotalUSD != null && authoritativeTotalUSD > 0;
    const totalUSD = hasAuthoritativeTotal ? (authoritativeTotalUSD as number) : holdingsUSD + cashUSD;
    const totalSource: 'tv_authoritative' | 'computed_fallback' =
        hasAuthoritativeTotal ? 'tv_authoritative' : 'computed_fallback';

    return {
        holdings: enriched,
        totals: {
            holdingsUSD,
            cashUSD,
            totalUSD,
            totalCAD: totalUSD * exchangeRate,
            exchangeRate,
            timestamp: new Date().toISOString(),
            totalSource,
        },
    };
}

/**
 * Decides whether a write should carry forward a previously-known TV-authoritative
 * total, or use a freshly computed shares*price fallback.
 *
 * A write path (e.g. refresh-prices, sync-tv/promote) often has no fresh broker fetch
 * to work with — only updated share/price data. Without this, that write would silently
 * replace a genuine broker-authoritative total with a weaker approximation, which is the
 * exact portfolio-total-validation bug this project has hit repeatedly. If the existing
 * persisted total was itself only ever a fallback, there's nothing authoritative to
 * preserve, so the fresh fallback is used as normal.
 */
export function preserveAuthoritativeTotal(
    existing: PortfolioTotals | null,
    fallback: { totalUSD: number; totalCAD: number }
): { totalUSD: number; totalCAD: number; totalSource: 'tv_authoritative' | 'computed_fallback' } {
    if (existing?.totalSource === 'tv_authoritative') {
        return { totalUSD: existing.totalUSD, totalCAD: existing.totalCAD, totalSource: 'tv_authoritative' };
    }
    return { totalUSD: fallback.totalUSD, totalCAD: fallback.totalCAD, totalSource: 'computed_fallback' };
}

/**
 * Single canonical "actual weight %" calculator. Every consumer (Express routes,
 * chat-agent Python scripts via the parity-tested mirror in validate_weights.py,
 * conviction scoring) must go through this formula — not recompute independently.
 *
 * Denominator is the persisted totals.totalUSD (TV-authoritative when available,
 * per buildPortfolioSnapshot/preserveAuthoritativeTotal) — falls back to a locally
 * recomputed shares*price sum only when totals is unavailable or zero.
 */
export function computeWeightsMap(holdings: any[], totals: PortfolioTotals | null): Record<string, number> {
    const marketValue = (h: any) => (h.shares ?? 0) * (h.price ?? h.book_price ?? 0);
    const denominator = totals?.totalUSD && totals.totalUSD > 0
        ? totals.totalUSD
        : holdings.reduce((sum, h) => sum + marketValue(h), 0);

    const map: Record<string, number> = {};
    if (denominator <= 0) return map;
    for (const h of holdings) {
        const ticker = h.symbol ?? h.ticker;
        if (ticker) map[ticker] = (marketValue(h) / denominator) * 100;
    }
    return map;
}
