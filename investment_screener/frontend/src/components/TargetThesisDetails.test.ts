/**
 * TargetThesisDetails.test.ts
 *
 * Purpose:
 *     update_price_levels.py now writes bear-derived levels >50% below price
 *     with status 'suppressed' (e.g. APLD's $2.76 stop on a $26 stock). The
 *     thesis card must not display them as actionable tiers.
 *
 * Layer: Frontend / Components (vitest)
 */
import { describe, it, expect } from 'vitest';
import { visibleTiers } from './TargetThesisDetails';

const levels = {
    buyTiers: [
        { tier: 1, price: 16.34, status: 'active' },
        { tier: 2, price: 3.06, status: 'suppressed' },
    ],
    sellTiers: [
        { tier: 1, price: 21.78, status: 'active' },
        { tier: 2, price: 61.04, status: 'inactive' },
    ],
    stopLoss: { price: 2.76, status: 'suppressed' },
};

describe('visibleTiers', () => {
    it('hides suppressed and inactive tiers and stop', () => {
        const v = visibleTiers(levels);
        expect(v.buyTiers.map(t => t.tier)).toEqual([1]);
        expect(v.sellTiers.map(t => t.tier)).toEqual([1]);
        expect(v.stopLoss).toBeNull();
    });

    it('keeps an active stop', () => {
        expect(visibleTiers({ stopLoss: { price: 20.53, status: 'active' } }).stopLoss?.price).toBe(20.53);
    });
});
