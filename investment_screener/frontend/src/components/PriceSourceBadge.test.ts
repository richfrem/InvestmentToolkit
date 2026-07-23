/**
 * PriceSourceBadge.test.ts
 *
 * Purpose:
 *     Tests for the price-source badge's backend-value -> label/color mapping.
 *     Regression coverage for a bug where the SQLite-backed price_source value
 *     ('domain_model_sqlite', the normal case after Wave 3's cutover and any
 *     /refresh-prices run) was indistinguishable from the true yfinance-fallback
 *     state — both rendered as "yfinance", hiding that a refresh had actually
 *     succeeded.
 *
 * Layer: Frontend / Components (vitest)
 */
import { describe, it, expect } from 'vitest';
import { describeSource } from './PriceSourceBadge';

describe('describeSource', () => {
    it('tradingview maps to TV Live, emerald', () => {
        expect(describeSource('tradingview')).toEqual({ label: 'TV Live', color: 'emerald' });
    });

    it('domain_model_sqlite maps to SQLite, emerald (not yfinance)', () => {
        expect(describeSource('domain_model_sqlite')).toEqual({ label: 'SQLite', color: 'emerald' });
    });

    it('yfinance maps to yfinance, zinc', () => {
        expect(describeSource('yfinance')).toEqual({ label: 'yfinance', color: 'zinc' });
    });

    it('null maps to the yfinance fallback', () => {
        expect(describeSource(null)).toEqual({ label: 'yfinance', color: 'zinc' });
    });

    it('an unrecognized value falls back to yfinance rather than throwing', () => {
        expect(describeSource('some-future-source')).toEqual({ label: 'yfinance', color: 'zinc' });
    });
});
