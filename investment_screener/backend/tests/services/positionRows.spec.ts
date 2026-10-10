/**
 * positionRows.spec.ts
 *
 * Purpose: proves buildPositionRows, the one place the per-ticker rows every table shows are
 * assembled from the database reads (thesis holdings, positions, weights, recommendations).
 */
import { expect } from 'chai';
import { buildPositionRows, PositionRowInput } from '../../src/services/positionRows';

const input = (over: Partial<PositionRowInput> = {}): PositionRowInput => ({
    thesisHoldings: [
        { ticker: 'NVDA', name: 'NVIDIA', pillarId: 'compute', subStrategyId: 'asi_race', role: 'core',
          targetWeight: 5, thesisForInclusion: 'why', agentRationale: 'agent', assetClass: 'EQUITY' },
        { ticker: 'LDOS', name: 'Leidos', pillarId: 'defense', subStrategyId: 'defense-ai-space', role: 'watchlist',
          targetWeight: 0, thesisForInclusion: null, agentRationale: null, assetClass: 'EQUITY' },
    ],
    positions: [{ symbol: 'NVDA', shares: 4, price: 200, averageCost: 150 }],
    weights: { NVDA: 6.5 },
    recommendations: { NVDA: { action: 'MAINTAIN' }, LDOS: { action: 'INITIATE' } },
    watched: new Set(['LDOS']),
    projected: new Set(['NVDA']),
    rationaleByTicker: {},
    documentsByTicker: { NVDA: ['asi_race', 'power_infrastructure'] },
    ...over,
});

describe('buildPositionRows', () => {
    it('gives a held ticker its shares, cost, market value, weight, target and gap from the database reads', () => {
        const nvda = buildPositionRows(input()).find(r => r.ticker === 'NVDA')!;
        expect(nvda.held).to.equal(true);
        expect(nvda.shares).to.equal(4);
        expect(nvda.averageCost).to.equal(150);
        expect(nvda.bookValue).to.equal(600);
        expect(nvda.marketValue).to.equal(800);
        expect(nvda.actualPct).to.equal(6.5);
        expect(nvda.targetPct).to.equal(5);
        expect(nvda.gapPct).to.be.closeTo(1.5, 1e-9);
        expect(nvda.action).to.equal('MAINTAIN');
        expect(nvda.subStrategyId).to.equal('asi_race');
    });

    it('lists an unheld thesis ticker as 0% of the portfolio with zero shares', () => {
        const ldos = buildPositionRows(input()).find(r => r.ticker === 'LDOS')!;
        expect(ldos.held).to.equal(false);
        expect(ldos.shares).to.equal(0);
        expect(ldos.marketValue).to.equal(null);
        expect(ldos.actualPct).to.equal(0);
        expect(ldos.gapPct).to.equal(0);
        expect(ldos.isWatched).to.equal(true);
        expect(ldos.action).to.equal('INITIATE');
    });

    it('gives an unheld ticker with a target a negative gap: the allocation it is missing', () => {
        const rows = buildPositionRows(input({
            thesisHoldings: [{ ticker: 'AMD', name: 'AMD', pillarId: 'compute', subStrategyId: 'asi_race', role: 'initiate',
                targetWeight: 2, thesisForInclusion: null, agentRationale: null, assetClass: 'EQUITY' }],
            positions: [], weights: {},
        }));
        const amd = rows.find(r => r.ticker === 'AMD')!;
        expect(amd.actualPct).to.equal(0);
        expect(amd.gapPct).to.equal(-2);
    });

    it('leaves the weight unknown (null) for a held ticker the weight calculation does not cover', () => {
        const rows = buildPositionRows(input({ weights: {} }));
        const nvda = rows.find(r => r.ticker === 'NVDA')!;
        expect(nvda.actualPct).to.equal(null);
        expect(nvda.gapPct).to.equal(null);
    });

    it('takes the action from the recommendation verbatim and leaves it null without one', () => {
        const rows = buildPositionRows(input({ recommendations: {} }));
        expect(rows.every(r => r.action === null)).to.equal(true);
    });

    it('includes a held ticker that has no thesis row, as untracked', () => {
        const rows = buildPositionRows(input({
            positions: [{ symbol: 'NVDA', shares: 4, price: 200, averageCost: 150 }, { symbol: 'ZZZ', shares: 1, price: 10, averageCost: null }],
            weights: { NVDA: 6.5, ZZZ: 0.1 },
        }));
        const zzz = rows.find(r => r.ticker === 'ZZZ')!;
        expect(zzz.role).to.equal('untracked');
        expect(zzz.targetPct).to.equal(null);
        expect(zzz.bookValue).to.equal(null);
        expect(zzz.marketValue).to.equal(10);
    });

    it('marks cash rows with the cash pillar and no strategy', () => {
        const rows = buildPositionRows(input({
            positions: [{ symbol: 'USD_CASH', shares: 100, price: 1, averageCost: 1 }], weights: { USD_CASH: 2 },
        }));
        const cash = rows.find(r => r.ticker === 'USD_CASH')!;
        expect(cash.assetClass).to.equal('CASH');
        expect(cash.pillarId).to.equal('cash');
    });

    it('lists the thesis documents a ticker belongs to, empty when none', () => {
        const rows = buildPositionRows(input());
        expect(rows.find(r => r.ticker === 'NVDA')!.documents).to.deep.equal(['asi_race', 'power_infrastructure']);
        expect(rows.find(r => r.ticker === 'LDOS')!.documents).to.deep.equal([]);
    });
});
