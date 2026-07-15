/**
 * portfolioSnapshot.ts - Portfolio totals and snapshots computation engine.
 * 
 * Purpose:
 *   Pure utility to calculate market values, USD/CAD totals, actual allocation weights,
 *   and preserve authoritative broker totals without I/O side-effects.
 * 
 * Key Input Dependencies:
 *   None
 * 
 * Key Output Dependencies:
 *   None
 * 
 * Functions Index:
 *   - buildPortfolioSnapshot(holdings, tvSnapshot, exchangeRate, authoritativeTotalUSD) - Compute market values and aggregates portfolio totals
 *   - preserveAuthoritativeTotal(existing, fallback) - Decide whether to preserve previously fetched authoritative TV totals
 *   - computeWeightsMap(holdings, totals) - Compute the actual percentage weights for each ticker holding
 */

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
 * Compute market value per holding and aggregated portfolio totals.
 * 
 * Denominated in USD, and uses authoritative broker totals when available.
 * 
 * @param {any[]} holdings - Holdings entries to compile
 * @param {any} tvSnapshot - Active TradingView broker snapshot info
 * @param {number} exchangeRate - USD/CAD exchange multiplier
 * @param {number|null} [authoritativeTotalUSD] - Real broker combined equity total, if available
 * @returns {PortfolioSnapshot} Enriched snapshot object containing holding data and totals
 */
export function buildPortfolioSnapshot(
    holdings: any[],
    tvSnapshot: any,
    exchangeRate: number,
    authoritativeTotalUSD?: number | null
): PortfolioSnapshot {
    /**
     * Maps holdings to derive market_value, aggregates cash balances, checks
     * for authoritative broker total, and returns populated totals.
     */
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
 * Decide whether to preserve previously fetched authoritative TV totals.
 * 
 * Prevents updated calculations from overwriting a genuine broker balance figure.
 * 
 * @param {PortfolioTotals|null} existing - Previous totals configuration
 * @param {object} fallback - Freshly calculated fallback total
 * @param {number} fallback.totalUSD - Recomputed USD holdings + cash sum
 * @param {number} fallback.totalCAD - Recomputed CAD holdings + cash sum
 * @returns {object} Selected totals to persist with source metadata
 */
export function preserveAuthoritativeTotal(
    existing: PortfolioTotals | null,
    fallback: { totalUSD: number; totalCAD: number }
): { totalUSD: number; totalCAD: number; totalSource: 'tv_authoritative' | 'computed_fallback' } {
    /**
     * Checks if existing source is 'tv_authoritative', returning it if true,
     * otherwise defaulting to the freshly computed shares*price fallback.
     */
    if (existing?.totalSource === 'tv_authoritative') {
        return { totalUSD: existing.totalUSD, totalCAD: existing.totalCAD, totalSource: 'tv_authoritative' };
    }
    return { totalUSD: fallback.totalUSD, totalCAD: fallback.totalCAD, totalSource: 'computed_fallback' };
}

/**
 * Compute the actual percentage weights for each ticker holding.
 * 
 * @param {any[]} holdings - Holdings entries list
 * @param {PortfolioTotals|null} totals - Persisted totals configurations
 * @returns {Record<string, number>} Ticker mapped allocation percentage levels
 */
export function computeWeightsMap(holdings: any[], totals: PortfolioTotals | null): Record<string, number> {
    /**
     * Resolves denominator using authoritative total, loops holdings, and maps
     * percentage allocations relative to denominator.
     */
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

