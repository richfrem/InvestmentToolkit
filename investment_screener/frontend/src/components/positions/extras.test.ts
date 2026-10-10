import { describe, expect, it } from 'vitest';
import { buildExtras, latestProjectionByTicker, type ProjectionLite } from './extras';

const projection = (ticker: string, savedAt: string, over: Partial<ProjectionLite> = {}): ProjectionLite => ({
    ticker, savedAt,
    aiThesis: { model: 'annual_fcff', fairValue: 100 },
    scenarios: {
        base: { growthRate: 20, netMargin: 15, qualityMultiplier: 1.1, scenarioPrice: 110 },
        bear: { scenarioPrice: 60 }, bull: { scenarioPrice: 180 },
    },
    ...over,
});

describe('latestProjectionByTicker', () => {
    it('keeps the newest saved projection per ticker and skips ones without a thesis', () => {
        const out = latestProjectionByTicker([
            projection('A', '2026-01-01'), projection('A', '2026-03-01'), projection('B', '2026-02-01', { aiThesis: undefined }),
        ]);
        expect(out.A.savedAt).toBe('2026-03-01');
        expect(out.B).toBeUndefined();
    });
});

describe('buildExtras', () => {
    it('reads the live price, sector, changes and earnings from the heatmap stock', () => {
        const e = buildExtras({ symbol: 'A', price: 12.5, sector: 'Tech', industry: 'Semis', analyst_target_mean: 20,
            change_1d: 1.5, change_1w: -2, change_overall: 40, earnings_date: '2026-11-01', days_to_earnings: 22 }, undefined);
        expect(e).toMatchObject({ livePrice: 12.5, sector: 'Tech', industry: 'Semis', analystTarget: 20,
            change_1d: 1.5, change_1w: -2, change_overall: 40, earningsDate: '2026-11-01', daysToEarnings: 22 });
    });

    it('reads growth, rule of 40, scenarios, model and date from the saved projection', () => {
        const e = buildExtras(undefined, projection('A', '2026-03-01'));
        expect(e).toMatchObject({ growth: 20, ruleOf40: 35, bear: 60, base: 110, bull: 180, model: 'annual_fcff',
            qualityMultiplier: 1.1, lastAnalyzed: '2026-03-01' });
    });

    it('treats a non-positive or missing price as unknown, never zero', () => {
        expect(buildExtras({ symbol: 'A', price: 0 }, undefined).livePrice).toBeNull();
        expect(buildExtras({ symbol: 'A' }, undefined).livePrice).toBeNull();
    });

    it('leaves rule of 40 unknown when growth or margin is missing', () => {
        const e = buildExtras(undefined, projection('A', 'd', { scenarios: { base: { growthRate: 20 } } }));
        expect(e.growth).toBe(20);
        expect(e.ruleOf40).toBeNull();
    });

    it('returns all-null extras with neither source', () => {
        const e = buildExtras(undefined, undefined);
        expect(Object.values(e).every(v => v === null)).toBe(true);
    });
});
