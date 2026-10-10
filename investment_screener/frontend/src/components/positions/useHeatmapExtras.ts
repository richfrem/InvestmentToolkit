/**
 * useHeatmapExtras.ts - Load the live heatmap and saved projections the portfolio table adds to the rows.
 *
 * Purpose:
 *     The position rows come from the database read model; the live price, sector, % changes and
 *     earnings date come from POST /api/portfolio-heatmap, and growth, scenarios and the model
 *     from the saved projections. This hook loads both, asking the heatmap only for the tickers
 *     the chosen scope wants (heatmapRequest.ts), merges them with buildExtras, and exposes the
 *     portfolio totals, the price source and a refresh that syncs from the broker first.
 *
 * Layer: Frontend / Components / Positions
 *
 * Usage Examples:
 *     const { extrasFor, totals, priceSource, refreshedAt, loading, error, refresh } = useHeatmapExtras(wantedTickers);
 *
 * Key Functions (Index):
 *     - useHeatmapExtras(): { extrasFor, totals, priceSource, refreshedAt, loading, error, refresh }
 *
 * Key Input Dependencies:
 *     - GET /api/portfolio (held items), POST /api/portfolio-heatmap, GET /api/projections,
 *       syncAndRefreshPortfolio, heatmapRequest.ts, extras.ts
 *
 * Key Output Dependencies:
 *     - PortfolioPage
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { fetchAllProjections, syncAndRefreshPortfolio } from '../../services/api';
import { buildExtras, latestProjectionByTicker, type HeatmapStock, type PositionExtras, type ProjectionLite } from './extras';
import { planHeatmapRequest, type PortfolioItem } from './heatmapRequest';

export interface HeatmapTotals {
    usd: number | null;
    cad: number | null;
    exchangeRate: number | null;
}

interface HeatmapResponse {
    stocks: HeatmapStock[];
    total_value?: number;
    total_value_usd?: number;
    total_value_cad?: number;
    price_source?: string;
    refreshed_at?: string;
    exchange_rate?: number;
}

const EMPTY: PositionExtras = buildExtras(null, null);

export function useHeatmapExtras(wanted: string[]) {
    const [stocks, setStocks] = useState<Record<string, HeatmapStock>>({});
    const [projections, setProjections] = useState<Record<string, ProjectionLite>>({});
    const [totals, setTotals] = useState<HeatmapTotals>({ usd: null, cad: null, exchangeRate: null });
    const [priceSource, setPriceSource] = useState<string | null>(null);
    const [refreshedAt, setRefreshedAt] = useState<Date | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const loaded = useRef(new Set<string>());
    const inFlight = useRef(false);
    const wantedKey = useMemo(() => [...new Set(wanted)].sort().join(','), [wanted]);

    const load = useCallback(async (tickers: string[]) => {
        if (inFlight.current) return;
        inFlight.current = true;
        setLoading(true);
        try {
            const portfolio = await fetch('/api/portfolio').then(r => (r.ok ? r.json() : { items: [] })).catch(() => ({ items: [] }));
            const held: PortfolioItem[] = (portfolio.items ?? []) as PortfolioItem[];
            const plan = planHeatmapRequest(held, tickers, loaded.current);
            if (!plan.needed) return;
            const response = await fetch('/api/portfolio-heatmap', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ items: plan.items }),
            });
            if (!response.ok) throw new Error('Failed to fetch live prices');
            const data = await response.json() as HeatmapResponse;
            for (const item of plan.items) loaded.current.add(item.symbol);
            setStocks(prev => ({ ...prev, ...Object.fromEntries(data.stocks.map(s => [s.symbol, s])) }));
            setTotals({
                usd: data.total_value_usd ?? data.total_value ?? null,
                cad: data.total_value_cad ?? null,
                exchangeRate: data.exchange_rate && data.exchange_rate > 0 ? data.exchange_rate : null,
            });
            if (data.price_source) setPriceSource(data.price_source);
            setRefreshedAt(data.refreshed_at ? new Date(data.refreshed_at) : new Date());
            setError(null);
        } catch (e) {
            setError(e instanceof Error ? e.message : 'Failed to load live prices');
        } finally {
            inFlight.current = false;
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        const timer = window.setTimeout(() => { void load(wantedKey ? wantedKey.split(',') : []); }, 0);
        return () => window.clearTimeout(timer);
    }, [wantedKey, load]);

    useEffect(() => {
        let cancelled = false;
        void fetchAllProjections()
            .then(list => { if (!cancelled) setProjections(latestProjectionByTicker(list as unknown as ProjectionLite[])); })
            .catch(() => undefined);
        return () => { cancelled = true; };
    }, []);

    /** Sync from the broker, then reload everything the scope wants. */
    const refresh = useCallback(async () => {
        try {
            await syncAndRefreshPortfolio();
        } catch (e) {
            console.error('Unified sync failed', e);
        } finally {
            loaded.current = new Set();
            await load(wantedKey ? wantedKey.split(',') : []);
            window.dispatchEvent(new CustomEvent('portfolio-synced'));
        }
    }, [load, wantedKey]);

    const extrasFor = useCallback(
        (ticker: string): PositionExtras => (stocks[ticker] || projections[ticker] ? buildExtras(stocks[ticker], projections[ticker]) : EMPTY),
        [stocks, projections],
    );

    return { extrasFor, totals, priceSource, refreshedAt, loading, error, refresh };
}
