import { describe, expect, it } from 'vitest';
import { suggestedShares } from './tradeSizing';

describe('suggestedShares', () => {
    it('sizes the order to close the weight gap at the current price, rounded down', () => {
        // gap 2 points of a $10,000 portfolio = $200; at $30 that is 6.67 shares -> 6
        expect(suggestedShares({ actualPct: 1, targetPct: 3, price: 30, portfolioValue: 10000 })).toBe(6);
    });
    it('uses the absolute gap, so an overweight position sizes a trim the same way', () => {
        expect(suggestedShares({ actualPct: 5, targetPct: 3, price: 30, portfolioValue: 10000 })).toBe(6);
    });
    it('is never below one share', () => {
        expect(suggestedShares({ actualPct: 2.99, targetPct: 3, price: 500, portfolioValue: 1000 })).toBe(1);
    });
    it('falls back to one share when a weight, the price or the portfolio value is missing or zero', () => {
        expect(suggestedShares({ actualPct: null, targetPct: 3, price: 30, portfolioValue: 10000 })).toBe(1);
        expect(suggestedShares({ actualPct: 1, targetPct: null, price: 30, portfolioValue: 10000 })).toBe(1);
        expect(suggestedShares({ actualPct: 1, targetPct: 3, price: null, portfolioValue: 10000 })).toBe(1);
        expect(suggestedShares({ actualPct: 1, targetPct: 3, price: 30, portfolioValue: 0 })).toBe(1);
        expect(suggestedShares({ actualPct: 0, targetPct: 3, price: 30, portfolioValue: 10000 })).toBe(1);
    });
});
