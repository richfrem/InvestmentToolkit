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
 * Pure calculation logic for computing the strategy allocation.
 * Aggregates portfolio positions by thesis pillars, sub-strategies, and sectors.
 * - Uses pos.price ?? pos.book_price ?? 0 to match total summary and prevent new synced positions from being zeroed out.
 * - Uses authoritative totals.totalUSD if available to align with the summary card total.
 */
function normalizeTicker(sym: string): string {
    const s = (sym || '').toUpperCase();
    if (s === 'PSU.U' || s === 'PSU.U.TO' || s === 'PSU-U.TO') return 'PSU-U.TO';
    if (s === 'ETH.U' || s === 'ETH.U.TO' || s === 'ETH-U.TO') return 'ETH-U.TO';
    return sym;
}

export function computeStrategyAllocation(
    positions: any[],
    totals: any | null,
    thesis: any | null
): StrategyAllocation {
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
