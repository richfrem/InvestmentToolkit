/**
 * recommendationPresentation.test.ts
 *
 * Purpose:
 *     Tests for the Daily Brief recommendation-card presentation mapping —
 *     recommendation string → trade side, button rating, and chip styling.
 *
 * Layer: Frontend / Utils (vitest)
 */
import { describe, it, expect } from 'vitest';
import { tradeIntent, REC_CHIP_STYLES } from './recommendationPresentation';

describe('tradeIntent', () => {
    it('SELL maps to a sell-side actionable intent', () => {
        expect(tradeIntent('SELL')).toEqual({ side: 'sell', rating: 'SELL' });
    });

    it('TRIM maps to a sell-side actionable intent', () => {
        expect(tradeIntent('TRIM')).toEqual({ side: 'sell', rating: 'SELL' });
    });

    it('BUY maps to a buy-side actionable intent', () => {
        expect(tradeIntent('BUY')).toEqual({ side: 'buy', rating: 'BUY' });
    });

    it('BUY_LIMIT maps to a buy-side actionable intent', () => {
        expect(tradeIntent('BUY_LIMIT')).toEqual({ side: 'buy', rating: 'BUY' });
    });

    it('HOLD and QUEUED have no trade intent (no button)', () => {
        expect(tradeIntent('HOLD')).toBeNull();
        expect(tradeIntent('QUEUED')).toBeNull();
    });

    it('unknown recommendation strings have no trade intent', () => {
        expect(tradeIntent('SOMETHING_NEW')).toBeNull();
    });
});

describe('REC_CHIP_STYLES', () => {
    it('every recommendation kind has a chip style', () => {
        for (const k of ['SELL', 'TRIM', 'BUY', 'BUY_LIMIT', 'HOLD', 'QUEUED']) {
            expect(REC_CHIP_STYLES[k]).toBeDefined();
        }
    });
});
