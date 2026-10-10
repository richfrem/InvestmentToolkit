/**
 * heatmapRequest.ts - Decide which tickers to send to the portfolio heatmap.
 *
 * Purpose:
 *     The heatmap (POST /api/portfolio-heatmap) supplies the live price, sector, % changes and
 *     earnings date, and is slow for many tickers on a cold cache. The page therefore asks only
 *     for what the chosen scope needs: the held positions (which also give the portfolio
 *     totals) and any other ticker not loaded yet, sent as a zero-share item. Pure, so the
 *     rule is unit tested.
 *
 * Layer: Frontend / Components / Positions
 *
 * Usage Examples:
 *     const plan = planHeatmapRequest(heldItems, wantedTickers, loadedSet);
 *     if (plan.needed) await postHeatmap(plan.items);
 *
 * Key Functions (Index):
 *     - planHeatmapRequest(): { needed, items } for the next heatmap call
 *
 * Key Input Dependencies:
 *     - GET /api/portfolio items (held positions with their cached names and sectors)
 *
 * Key Output Dependencies:
 *     - useHeatmapExtras
 */

export interface PortfolioItem {
    symbol: string;
    shares: number;
    [key: string]: unknown;
}

export interface HeatmapPlan {
    needed: boolean;
    items: PortfolioItem[];
}

/** The items to request: held positions plus wanted tickers not loaded yet (zero shares). */
export function planHeatmapRequest(held: PortfolioItem[], wanted: string[], loaded: Set<string>): HeatmapPlan {
    const wantedUnique = [...new Set(wanted.filter(Boolean))];
    const needed = wantedUnique.some(ticker => !loaded.has(ticker));
    if (!needed) return { needed: false, items: [] };
    const heldSymbols = new Set(held.map(item => item.symbol));
    const extra = wantedUnique
        .filter(ticker => !heldSymbols.has(ticker) && !loaded.has(ticker))
        .map(ticker => ({ symbol: ticker, shares: 0 }));
    return { needed: true, items: [...held, ...extra] };
}
