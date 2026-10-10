import { describe, expect, it } from 'vitest';
import { countsFor, filterRows, sectorOptions, strategyOptions, type FilterState } from './scope';
import type { PositionRow } from './positionMath';

const row = (over: Partial<PositionRow>): PositionRow => ({
    ticker: 'AAA', name: 'AAA', assetClass: 'EQUITY', pillarId: 'p', subStrategyId: 's1', role: 'core', held: true,
    shares: 1, averageCost: null, bookValue: null, marketValue: 100, currentPrice: 100, actualPct: 5, targetPct: 4,
    gapPct: 1, action: 'MAINTAIN', rationale: null, hasValuation: true, isWatched: false, documents: [], ...over,
});

const recs = {
    INI: { action: 'INITIATE', fair_value: 10 },
    ACC: { action: 'ACCUMULATE', fair_value: 10 },
    TRM: { action: 'TRIM', fair_value: 10, risk_reward: { reduce_candidate: true } },
    STAND: { action: 'TRIM', decision_check: { effective: 'MAINTAIN' }, fair_value: 10 },
    NOVAL: { action: 'WATCHLIST' },
} as never;

const rows = [
    row({ ticker: 'HELD', held: true, actualPct: 5, targetPct: 4 }),
    row({ ticker: 'INI', held: false, actualPct: 0, targetPct: 2, isWatched: true }),
    row({ ticker: 'ACC', held: true, actualPct: 3, targetPct: 3 }),
    row({ ticker: 'TRM', held: true, actualPct: 2, targetPct: 1 }),
    row({ ticker: 'STAND', held: true, actualPct: 1, targetPct: 1 }),
    row({ ticker: 'WATCH', held: false, actualPct: 0, targetPct: 0, isWatched: true }),
    row({ ticker: 'NOVAL', held: false, actualPct: 0, targetPct: 0, hasValuation: false }),
    row({ ticker: 'USD_CASH', assetClass: 'CASH', held: true, actualPct: 10, targetPct: 12, hasValuation: false }),
];

const state = (over: Partial<FilterState> = {}): FilterState => ({
    scope: 'all', status: 'all', sector: 'all', strategy: 'all', text: {}, ...over,
});
const tickers = (rs: PositionRow[]) => rs.map(r => r.ticker);
const sector = (r: PositionRow) => ({ HELD: 'Tech', ACC: 'Tech', TRM: 'Energy' } as Record<string, string>)[r.ticker] ?? null;

describe('scope', () => {
    it('holdings is anything funded or with a target weight, cash included', () => {
        expect(tickers(filterRows(rows, state({ scope: 'holdings' }), recs, sector)))
            .toEqual(['HELD', 'INI', 'ACC', 'TRM', 'STAND', 'USD_CASH']);
    });
    it('watchlist is the watched tickers', () => {
        expect(tickers(filterRows(rows, state({ scope: 'watchlist' }), recs, sector))).toEqual(['INI', 'WATCH']);
    });
    it('all keeps every row', () => {
        expect(filterRows(rows, state(), recs, sector)).toHaveLength(rows.length);
    });
});

describe('status chips', () => {
    it('match on the one stance (the standing decision wins) and never include cash', () => {
        expect(tickers(filterRows(rows, state({ status: 'trim' }), recs, sector))).toEqual(['TRM']);
        expect(tickers(filterRows(rows, state({ status: 'initiate' }), recs, sector))).toEqual(['INI']);
        expect(tickers(filterRows(rows, state({ status: 'actionable' }), recs, sector))).toEqual(['INI', 'ACC', 'TRM']);
    });
    it('reduce keeps the reduce candidates', () => {
        expect(tickers(filterRows(rows, state({ status: 'reduce' }), recs, sector))).toEqual(['TRM']);
    });
    it('gaps are funded or targeted tickers (not cash) that have no valuation', () => {
        const noVal = [row({ ticker: 'GAP', held: true, hasValuation: false }), row({ ticker: 'OK' }),
            row({ ticker: 'GAPW', held: false, actualPct: 0, targetPct: 0, isWatched: true, hasValuation: false })];
        expect(tickers(filterRows(noVal, state({ status: 'gaps' }), { OK: { fair_value: 10 } } as never, sector))).toEqual(['GAP']);
    });
});

describe('sector, strategy and text filters', () => {
    it('sector filter keeps only that sector; rows with no sector drop out', () => {
        expect(tickers(filterRows(rows, state({ sector: 'Tech' }), recs, sector))).toEqual(['HELD', 'ACC']);
    });
    it('strategy filter matches subStrategyId', () => {
        const mixed = [row({ ticker: 'A', subStrategyId: 'x' }), row({ ticker: 'B', subStrategyId: 'y' })];
        expect(tickers(filterRows(mixed, state({ strategy: 'y' }), recs, sector))).toEqual(['B']);
    });
    it('text filters are case-insensitive substring matches on the named field', () => {
        expect(tickers(filterRows(rows, state({ text: { ticker: 'st' } }), recs, sector))).toEqual(['STAND']);
    });
    it('filters combine', () => {
        expect(tickers(filterRows(rows, state({ scope: 'holdings', sector: 'Tech', status: 'actionable' }), recs, sector))).toEqual(['ACC']);
    });
});

describe('counts and options', () => {
    it('counts each chip and scope from the same rows', () => {
        const c = countsFor(rows, recs);
        expect(c).toMatchObject({ all: 8, initiate: 1, accumulate: 1, trim: 1, reduce: 1, holdings: 6, watchlist: 2 });
        expect(c.actionable).toBe(3);
    });
    it('sector and strategy options are the distinct non-empty values, sorted', () => {
        expect(sectorOptions(rows, sector)).toEqual(['Energy', 'Tech']);
        expect(strategyOptions([row({ subStrategyId: 'b' }), row({ subStrategyId: 'a' }), row({ subStrategyId: 'a' })])).toEqual(['a', 'b']);
    });
});
