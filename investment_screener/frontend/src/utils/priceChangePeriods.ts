/**
 * priceChangePeriods.ts
 * =====================================
 * Purpose: the single list of price-change periods (label, payload field, colour
 * scale) for every surface showing % change: heatmap toggle, Portfolio Table and
 * Screener columns, Stock Analysis chips (AGENTS.md rule 22). Values come from the
 * backend's shared price_changes.period_changes(); colours from formatters'
 * changeBgDaily / changeTileColor ladder.
 *
 * Key Functions (Index):
 *   - getPeriodChange(source, period) - % change from a row (change_* fields) or a
 *     performance object ({1d, 1w, ...}); null when missing
 *   - portfolioPeriodFields(row) - {change_1d..change_1y} copied from a heatmap row
 *   - periodScale(period) - colour-threshold multiplier for the period
 *   - legendRange(period) - +/- % at the ends of a colour legend
 */

export type PricePeriod = '1d' | '1w' | '1m' | '3m' | 'ytd' | '1y' | '5y';

export interface PricePeriodDef {
    key: PricePeriod;
    label: string;
    /** Field name on portfolio/heatmap rows. */
    field: string;
    /** Multiplier on the 1-day colour thresholds. */
    scale: number;
    /** Carried by the heatmap/portfolio payload (1 year of stored history). */
    inPortfolioData: boolean;
}

export const PRICE_CHANGE_PERIODS: PricePeriodDef[] = [
    { key: '1d', label: '1D', field: 'change_1d', scale: 1, inPortfolioData: true },
    { key: '1w', label: '1W', field: 'change_1w', scale: 2, inPortfolioData: true },
    { key: '1m', label: '1M', field: 'change_1m', scale: 3, inPortfolioData: true },
    { key: '3m', label: '3M', field: 'change_3m', scale: 5, inPortfolioData: true },
    { key: 'ytd', label: 'YTD', field: 'change_ytd', scale: 8, inPortfolioData: true },
    { key: '1y', label: '1Y', field: 'change_1y', scale: 10, inPortfolioData: true },
    { key: '5y', label: '5Y', field: 'change_5y', scale: 20, inPortfolioData: false },
];

export const PORTFOLIO_PERIODS = PRICE_CHANGE_PERIODS.filter(p => p.inPortfolioData);

export const DEFAULT_PERIOD: PricePeriod = '1d';

const periodDef = (period: PricePeriod): PricePeriodDef =>
    PRICE_CHANGE_PERIODS.find(p => p.key === period) ?? PRICE_CHANGE_PERIODS[0];

const asNumber = (v: unknown): number | null =>
    typeof v === 'number' && Number.isFinite(v) ? v : null;

export function getPeriodChange(source: Record<string, any>, period: PricePeriod): number | null {
    const def = periodDef(period);
    const value = asNumber(source[def.field]) ?? asNumber(source[def.key]);
    if (value !== null) return value;
    // 1D has historically been served as change_pct on heatmap rows.
    return period === '1d' ? asNumber(source.change_pct) : null;
}

/** Row fields for the portfolio periods (change_1d … change_1y). */
export type PortfolioPeriodFields = {
    change_1d: number | null; change_1w: number | null; change_1m: number | null;
    change_3m: number | null; change_ytd: number | null; change_1y: number | null;
};

/** Every portfolio period field from a heatmap row, null when absent — the one
 * mapping the Portfolio Table and Screener use to build rows. */
export function portfolioPeriodFields(row: Record<string, any> | undefined | null): PortfolioPeriodFields {
    return Object.fromEntries(
        PORTFOLIO_PERIODS.map(p => [p.field, row ? getPeriodChange(row, p.key) : null]),
    ) as PortfolioPeriodFields;
}

export const periodScale = (period: PricePeriod): number => periodDef(period).scale;

export const legendRange = (period: PricePeriod): number => 5 * periodScale(period);
