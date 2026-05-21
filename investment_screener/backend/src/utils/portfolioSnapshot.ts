export interface PortfolioTotals {
    holdingsUSD: number;
    cashUSD: number;
    totalUSD: number;
    totalCAD: number;
    exchangeRate: number;
    timestamp: string;
}

export interface PortfolioSnapshot {
    holdings: any[];
    totals: PortfolioTotals;
}

/**
 * Pure function — no I/O. Computes market_value per holding and all
 * portfolio totals in one pass. Call once at sync time; persist the
 * result; read it everywhere else.
 */
export function buildPortfolioSnapshot(
    holdings: any[],
    tvSnapshot: any,
    exchangeRate: number
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

    const totalUSD = holdingsUSD + cashUSD;

    return {
        holdings: enriched,
        totals: {
            holdingsUSD,
            cashUSD,
            totalUSD,
            totalCAD: totalUSD * exchangeRate,
            exchangeRate,
            timestamp: new Date().toISOString(),
        },
    };
}
