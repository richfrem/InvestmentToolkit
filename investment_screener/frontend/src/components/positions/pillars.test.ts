import { describe, expect, it } from 'vitest';
import { groupByPillar, type Pillar } from './pillars';
import type { PositionRow } from './positionMath';

const row = (over: Partial<PositionRow>): PositionRow => ({
    ticker: 'AAA', name: 'AAA', assetClass: 'EQUITY', pillarId: 'compute', subStrategyId: 's', role: 'core', held: true,
    shares: 1, averageCost: null, bookValue: null, marketValue: 100, currentPrice: 100, actualPct: 5, targetPct: 4,
    gapPct: 1, action: 'MAINTAIN', rationale: null, hasValuation: true, isWatched: false, documents: [], ...over,
});

const pillars: Pillar[] = [
    { id: 'compute', name: 'Compute', targetWeight: 30 },
    { id: 'security', name: 'Security', targetWeight: 10 },
    { id: 'power', name: 'Power', targetWeight: 15 },
];

describe('groupByPillar', () => {
    const rows = [
        row({ ticker: 'A', pillarId: 'compute', actualPct: 10, targetPct: 8 }),
        row({ ticker: 'B', pillarId: 'compute', actualPct: 5, targetPct: 6 }),
        row({ ticker: 'C', pillarId: 'security', actualPct: 2, targetPct: 3 }),
        row({ ticker: 'D', pillarId: 'power', actualPct: 0, targetPct: 0, held: false }),
    ];

    it('groups rows under their pillar with the pillar name', () => {
        const g = groupByPillar(rows, pillars);
        expect(g.find(x => x.pillarId === 'compute')!.rows.map(r => r.ticker)).toEqual(['A', 'B']);
        expect(g.find(x => x.pillarId === 'security')!.name).toBe('Security');
    });

    it('orders pillars by target weight, largest first', () => {
        expect(groupByPillar(rows, pillars).map(g => g.pillarId)).toEqual(['compute', 'power', 'security']);
    });

    it('sums the actual and target weight of the rows shown in each group', () => {
        const c = groupByPillar(rows, pillars).find(g => g.pillarId === 'compute')!;
        expect(c.actualPct).toBe(15);
        expect(c.targetPct).toBe(14);
    });

    it('shows the pillar target from the pillars list, separate from the sum of its stocks', () => {
        expect(groupByPillar(rows, pillars).find(g => g.pillarId === 'compute')!.pillarTarget).toBe(30);
    });

    it('puts rows whose pillar is unknown into an Other group at the end, never dropping them', () => {
        const g = groupByPillar([...rows, row({ ticker: 'X', pillarId: 'mystery' })], pillars);
        expect(g[g.length - 1].name).toBe('Other');
        expect(g[g.length - 1].rows.map(r => r.ticker)).toEqual(['X']);
    });

    it('omits pillars with no rows and returns no groups for no rows', () => {
        expect(groupByPillar([row({ ticker: 'A', pillarId: 'compute' })], pillars).map(g => g.pillarId)).toEqual(['compute']);
        expect(groupByPillar([], pillars)).toEqual([]);
    });
});
