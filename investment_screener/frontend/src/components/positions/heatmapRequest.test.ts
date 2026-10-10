import { describe, expect, it } from 'vitest';
import { planHeatmapRequest, type PortfolioItem } from './heatmapRequest';

const held: PortfolioItem[] = [{ symbol: 'A', shares: 2 }, { symbol: 'B', shares: 1 }];

describe('planHeatmapRequest', () => {
    it('asks for nothing when every wanted ticker is already loaded', () => {
        const plan = planHeatmapRequest(held, ['A', 'B'], new Set(['A', 'B']));
        expect(plan.needed).toBe(false);
    });

    it('asks for the held items (they give the totals) when held tickers are wanted and not loaded', () => {
        const plan = planHeatmapRequest(held, ['A', 'B'], new Set());
        expect(plan.needed).toBe(true);
        expect(plan.items.map(i => i.symbol)).toEqual(['A', 'B']);
    });

    it('adds unheld wanted tickers as zero-share items and keeps the held ones', () => {
        const plan = planHeatmapRequest(held, ['A', 'W1', 'W2'], new Set(['A']));
        expect(plan.needed).toBe(true);
        expect(plan.items).toEqual([...held, { symbol: 'W1', shares: 0 }, { symbol: 'W2', shares: 0 }]);
    });

    it('does not re-request an unheld ticker that is already loaded', () => {
        const plan = planHeatmapRequest(held, ['W1', 'W2'], new Set(['W1']));
        expect(plan.items.map(i => i.symbol)).toEqual(['A', 'B', 'W2']);
    });

    it('ignores duplicates and blanks in the wanted list', () => {
        const plan = planHeatmapRequest(held, ['W1', 'W1', ''], new Set());
        expect(plan.items.filter(i => i.symbol === 'W1')).toHaveLength(1);
        expect(plan.items.some(i => i.symbol === '')).toBe(false);
    });
});
