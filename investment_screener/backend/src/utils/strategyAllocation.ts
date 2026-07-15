/**
 * strategyAllocation.ts - Portfolio allocation metrics calculator.
 * 
 * Purpose:
 *   Pure function to aggregate holding positions by sub-strategy, sector, and thesis pillars,
 *   using authoritative total parameters.
 * 
 * Key Input Dependencies:
 *   None
 * 
 * Key Output Dependencies:
 *   None
 * 
 * Functions Index:
 *   - normalizeTicker(sym: string) - Standardize ticker symbol for strategy mapping
 *   - computeStrategyAllocation(positions, totals, thesis) - Calculate strategy allocation categories across active portfolio holdings
 */

export interface StrategyHolding {
    symbol: string;
    name: string;
    sector: string;
    subStrategyId: string | null;
    shares: number;
    price: number;
    valueUSD: number;
    pct: number;
}

export interface StrategyAllocationItem {
    id: string;
    name: string;
    valueUSD: number;
    pct: number;
    holdings: StrategyHolding[];
}

export interface StrategyAllocation {
    allocation: StrategyAllocationItem[];
    totalUSD: number;
}

/**
 * Standardize ticker symbol for strategy mapping.
 * 
 * @param {string} sym - Input ticker symbol
 * @returns {string} Standardized ticker string
 */
function normalizeTicker(sym: string): string {
    /**
     * Maps variations of PSU/ETH symbols to their canonical tsx formatting.
     */
    const s = (sym || '').toUpperCase();
    if (s === 'PSU.U' || s === 'PSU.U.TO' || s === 'PSU-U.TO') return 'PSU-U.TO';
    if (s === 'ETH.U' || s === 'ETH.U.TO' || s === 'ETH-U.TO') return 'ETH-U.TO';
    return sym;
}

/**
 * Calculate strategy allocation categories across active portfolio holdings.
 * 
 * @param {any[]} positions - Active portfolio holdings positions list
 * @param {any|null} totals - Persisted totals snapshot details
 * @param {any|null} thesis - Investment thesis configuration object
 * @returns {StrategyAllocation} Strategy allocation stats report
 */
export function computeStrategyAllocation(
    positions: any[],
    totals: any | null,
    thesis: any | null
): StrategyAllocation {
    /**
     * Constructs maps of pillars and strategies, iterates positions to sum USD values by pillar,
     * resolves totalUSD, and projects percentage metrics before sorting by valueUSD.
     */
    const pillarMap: Record<string, string> = {};
    const subStrategyMap: Record<string, string> = {};
    let pillars: Array<{ id: string; name: string }> = [];

    if (thesis) {
        pillars = thesis.pillars ?? [];
        for (const h of (thesis.holdings ?? [])) {
            if (h.ticker && h.pillarId) pillarMap[h.ticker] = h.pillarId;
            if (h.ticker && h.subStrategyId) subStrategyMap[h.ticker] = h.subStrategyId;
        }
    }

    const pillarValues: Record<string, number> = {};
    const pillarPositions: Record<string, any[]> = {};

    for (const pos of positions) {
        const price = pos.price ?? pos.book_price ?? 0;
        const value = (pos.shares ?? 0) * price;
        const normSym = normalizeTicker(pos.symbol);
        const pillarId = (pos.symbol === 'USD_CASH' || pos.sector === 'CASH') ? 'cash' : (pillarMap[normSym] ?? 'other');
        pillarValues[pillarId] = (pillarValues[pillarId] ?? 0) + value;
        (pillarPositions[pillarId] ??= []).push(pos);
    }

    // Sum of positions (fallback)
    const computedTotalUSD = Object.values(pillarValues).reduce((a, b) => a + b, 0);

    // Use authoritative totalUSD if available and greater than 0, else fallback to computed total
    const totalUSD = (totals != null && (totals.totalUSD ?? 0) > 0)
        ? totals.totalUSD
        : computedTotalUSD;

    const pillarNameMap: Record<string, string> = { other: 'Other' };
    for (const p of pillars) {
        pillarNameMap[p.id] = p.name;
    }

    const allocation = Object.entries(pillarValues)
        .map(([id, value]) => ({
            id,
            name: pillarNameMap[id] ?? id,
            valueUSD: Math.round(value * 100) / 100,
            pct: totalUSD > 0 ? Math.round((value / totalUSD) * 10000) / 100 : 0,
            holdings: (pillarPositions[id] ?? [])
                .map((pos: any) => {
                    const price = pos.price ?? pos.book_price ?? 0;
                    const valueUSD = (pos.shares ?? 0) * price;
                    const normSym = normalizeTicker(pos.symbol);
                    return {
                        symbol: pos.symbol as string,
                        name: (pos.name ?? pos.symbol) as string,
                        sector: (pos.sector ?? 'Other') as string,
                        subStrategyId: (subStrategyMap[normSym] ?? (pos.symbol === 'USD_CASH' ? 'cash' : null)) as string | null,
                        shares: (pos.shares ?? 0) as number,
                        price: price as number,
                        valueUSD: Math.round(valueUSD * 100) / 100,
                        pct: totalUSD > 0 ? Math.round((valueUSD / totalUSD) * 10000) / 100 : 0,
                    };
                })
                .sort((a: any, b: any) => b.valueUSD - a.valueUSD),
        }))
        .filter(a => a.valueUSD > 0)
        .sort((a, b) => b.valueUSD - a.valueUSD);

    return {
        allocation,
        totalUSD: Math.round(totalUSD * 100) / 100
    };
}
