/**
 * positionRows.ts - Assemble the one per-ticker row every table in the web app shows.
 *
 * Purpose:
 *     Joins the database reads (thesis holdings, positions, weights, recommendations, watchlist,
 *     saved valuations) into one row per ticker: shares, cost, market value, actual and target
 *     weight, the gap between them, the stance and the thesis placement. GET /all-holdings
 *     returns these rows and the frontend positions module renders them, so Portfolio,
 *     Portfolio Advisor and the thesis pages all show the same numbers. Pure: no database,
 *     file or network access here.
 *
 * Layer: Backend / Services / Read Models
 *
 * Usage Examples:
 *     const rows = buildPositionRows({ thesisHoldings, positions, weights, recommendations,
 *                                      watched, projected, rationaleByTicker });
 *
 * Key Functions (Index):
 *     - buildPositionRows(): the union of thesis, held, watched and valued tickers as rows
 *
 * Key Input Dependencies:
 *     - InvestmentRepository.listThesisHoldings(), PortfolioRepository.listPositionsBySymbol(),
 *       getWeightsFromDb(), getRecommendations(), WatchlistService, ProjectionRepository
 *
 * Key Output Dependencies:
 *     - routes/screener.ts GET /all-holdings; frontend/src/components/positions
 */
import type { ThesisHoldingView } from './InvestmentRepository';

export interface PositionRowInput {
    thesisHoldings: ThesisHoldingView[];
    positions: Array<{ symbol: string; shares: number; price: number; averageCost: number | null }>;
    /** Actual weight percent per ticker (getWeightsFromDb), the one weight calculation. */
    weights: Record<string, number> | null;
    /** The canonical recommendation record per ticker; its action is used verbatim. */
    recommendations: Record<string, any>;
    watched: Set<string>;
    projected: Set<string>;
    rationaleByTicker: Record<string, string | null | undefined>;
    /** Thesis documents that list each ticker (thesis_document_member). */
    documentsByTicker: Record<string, string[]>;
}

export interface PositionRow {
    ticker: string;
    name: string;
    assetClass: string;
    pillarId: string;
    subStrategyId: string;
    role: string;
    held: boolean;
    shares: number;
    averageCost: number | null;
    bookValue: number | null;
    marketValue: number | null;
    currentPrice: number | null;
    /** Weight in the portfolio: 0 when not held, null only when held but the weight is not known. */
    actualPct: number | null;
    targetPct: number | null;
    /** actualPct minus targetPct in percentage points (an unheld stock gets minus its target); null unless both are known. */
    gapPct: number | null;
    action: string | null;
    recommendation: any;
    rationale: string | null;
    hasValuation: boolean;
    isWatched: boolean;
    /** Thesis documents (sub-strategy files) that list this stock, for the per-thesis table. */
    documents: string[];
}

const isCash = (ticker: string): boolean => ticker === 'USD_CASH' || ticker.includes('CASH');

/** One row per ticker in the union of thesis, held, watched and valued tickers. */
export function buildPositionRows(input: PositionRowInput): PositionRow[] {
    const thesis = new Map(input.thesisHoldings.map(h => [h.ticker, h]));
    const held = new Map(input.positions.map(p => [p.symbol, p]));
    const tickers = new Set<string>([...input.watched, ...thesis.keys(), ...held.keys(), ...input.projected]);

    return Array.from(tickers).map(ticker => {
        const h = thesis.get(ticker);
        const p = held.get(ticker);
        const cash = isCash(ticker);
        // Not held is 0% of the portfolio (a known value); held but not covered by the weight calculation is unknown.
        const actualPct = p ? (input.weights?.[ticker] ?? null) : 0;
        const targetPct = h?.targetWeight ?? null;
        const rec = input.recommendations[ticker] ?? null;
        const shares = p?.shares ?? 0;
        return {
            ticker,
            name: h?.name ?? (ticker === 'USD_CASH' ? 'US Dollar Cash' : ticker),
            assetClass: h?.assetClass ?? (cash ? 'CASH' : 'EQUITY'),
            pillarId: h?.pillarId ?? (cash ? 'cash' : 'other'),
            subStrategyId: h?.subStrategyId ?? (cash ? 'cash' : 'other'),
            role: h?.role ?? (p ? 'untracked' : 'watchlist'),
            held: p !== undefined,
            shares,
            averageCost: p?.averageCost ?? null,
            bookValue: p && p.averageCost != null ? shares * p.averageCost : null,
            marketValue: p ? shares * p.price : null,
            currentPrice: p?.price ?? null,
            actualPct,
            targetPct,
            gapPct: actualPct != null && targetPct != null ? actualPct - targetPct : null,
            action: rec?.action ?? null,
            recommendation: rec,
            rationale: input.rationaleByTicker[ticker] ?? h?.agentRationale ?? h?.thesisForInclusion
                ?? (input.watched.has(ticker) ? 'Monitored via Watchlist' : null),
            hasValuation: input.projected.has(ticker),
            isWatched: input.watched.has(ticker),
            documents: input.documentsByTicker[ticker] ?? [],
        };
    });
}
