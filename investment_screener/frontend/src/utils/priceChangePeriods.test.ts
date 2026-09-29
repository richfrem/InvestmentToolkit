/**
 * priceChangePeriods.test.ts
 *
 * Purpose:
 *     One period list (labels, payload fields, colour scale) for every surface that
 *     shows % change: heatmap toggle, Portfolio Table / Screener columns, Stock
 *     Analysis chips (AGENTS.md rule 22). Previously three hand-written copies.
 *
 * Layer: Frontend / Utils (vitest)
 */
import { describe, it, expect } from 'vitest';
import {
    PRICE_CHANGE_PERIODS, PORTFOLIO_PERIODS, DEFAULT_PERIOD, getPeriodChange, periodScale, legendRange,
    portfolioPeriodFields,
} from './priceChangePeriods';

describe('price change periods', () => {
    it('is the single list, in display order', () => {
        expect(PRICE_CHANGE_PERIODS.map(p => p.label)).toEqual(['1D', '1W', '1M', '3M', 'YTD', '1Y', '5Y']);
        expect(PRICE_CHANGE_PERIODS.map(p => p.field)).toEqual(
            ['change_1d', 'change_1w', 'change_1m', 'change_3m', 'change_ytd', 'change_1y', 'change_5y']);
        expect(DEFAULT_PERIOD).toBe('1d');
    });

    it('portfolio surfaces get every period the heatmap payload carries (no 5Y)', () => {
        expect(PORTFOLIO_PERIODS.map(p => p.key)).toEqual(['1d', '1w', '1m', '3m', 'ytd', '1y']);
    });

    it('reads a row by field, or a performance object by key; null when missing', () => {
        const row = { change_pct: -6.91, change_1w: -9.2, change_3m: -33.0, change_1y: null };
        expect(getPeriodChange(row, '1w')).toBe(-9.2);
        expect(getPeriodChange(row, '1d')).toBe(-6.91);      // legacy change_pct fallback
        expect(getPeriodChange(row, '1y')).toBeNull();
        expect(getPeriodChange({ '1m': 3.1, '5y': null }, '1m')).toBe(3.1);
        expect(getPeriodChange({ '1m': 3.1, '5y': null }, '5y')).toBeNull();
    });

    it('widens the colour scale and legend for longer periods', () => {
        expect(periodScale('1d')).toBe(1);
        expect(periodScale('1y')).toBe(10);
        expect(legendRange('1d')).toBe(5);
        expect(legendRange('1m')).toBe(15);
    });

    it('copies every portfolio period field from a heatmap row (one mapping for all tables)', () => {
        const heatmapRow = { change_pct: 1.2, change_1d: 1.2, change_1w: -3, change_1m: 4, change_3m: -30, change_ytd: 2, change_1y: null };
        expect(portfolioPeriodFields(heatmapRow)).toEqual({
            change_1d: 1.2, change_1w: -3, change_1m: 4, change_3m: -30, change_ytd: 2, change_1y: null,
        });
        expect(portfolioPeriodFields(undefined)).toEqual({
            change_1d: null, change_1w: null, change_1m: null, change_3m: null, change_ytd: null, change_1y: null,
        });
    });
});
