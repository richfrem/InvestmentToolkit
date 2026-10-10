import { describe, expect, it } from 'vitest';
import { formatGap, formatWeight, moneyText, normalizePositionRows, weightHeat, rowsForDocument, sortRows, totalsFor, type PositionRow } from './positionMath';

const row = (over: Partial<PositionRow>): PositionRow => ({
    ticker: 'AAA', name: 'AAA', assetClass: 'EQUITY', pillarId: 'p', subStrategyId: 's', role: 'core', held: true,
    shares: 1, averageCost: null, bookValue: null, marketValue: 100, currentPrice: 100, actualPct: 5, targetPct: 4,
    gapPct: 1, action: 'MAINTAIN', rationale: null, hasValuation: true, isWatched: false, documents: [], ...over,
});

describe('formatWeight and formatGap', () => {
    it('shows a dash for an unknown weight, never 0', () => {
        expect(formatWeight(null)).toBe('—');
        expect(formatWeight(0)).toBe('0.00%');
        expect(formatWeight(6.546)).toBe('6.55%');
    });
    it('shows the gap signed in percentage points and a dash when unknown', () => {
        expect(formatGap(null)).toBe('—');
        expect(formatGap(1.5)).toBe('+1.50pp');
        expect(formatGap(-0.004)).toBe('0.00pp');
        expect(formatGap(0.004)).toBe('0.00pp');
        expect(formatGap(0)).toBe('0.00pp');
        expect(formatGap(-0.06)).toBe('-0.06pp');
        expect(formatGap(-2.444)).toBe('-2.44pp');
    });
});

describe('rowsForDocument', () => {
    const rows = [row({ ticker: 'A', documents: ['asi'] }), row({ ticker: 'B', documents: ['asi', 'power'] }),
        row({ ticker: 'C', documents: [], held: false })];
    it('keeps only the tickers the document lists', () => {
        expect(rowsForDocument(rows, 'asi', 'all').map(r => r.ticker)).toEqual(['A', 'B']);
        expect(rowsForDocument(rows, 'power', 'all').map(r => r.ticker)).toEqual(['B']);
    });
    it('held scope drops tickers that are not held', () => {
        const mixed = [row({ ticker: 'A', documents: ['asi'] }), row({ ticker: 'B', documents: ['asi'], held: false })];
        expect(rowsForDocument(mixed, 'asi', 'held').map(r => r.ticker)).toEqual(['A']);
    });
});

describe('totalsFor', () => {
    it('sums actual and target weight and reports the gap, ignoring unknown weights', () => {
        const t = totalsFor([row({ actualPct: 5, targetPct: 4 }), row({ actualPct: null, targetPct: 2 }), row({ actualPct: 3, targetPct: null })]);
        expect(t.actualPct).toBe(8);
        expect(t.targetPct).toBe(6);
        expect(t.gapPct).toBe(2);
        expect(t.heldCount).toBe(3);
    });
    it('counts only held rows as positions', () => {
        expect(totalsFor([row({ held: true }), row({ held: false, actualPct: null })]).heldCount).toBe(1);
    });
});

describe('sortRows', () => {
    it('sorts numbers with unknown values last in both directions', () => {
        const rows = [row({ ticker: 'A', actualPct: 2 }), row({ ticker: 'B', actualPct: null }), row({ ticker: 'C', actualPct: 9 })];
        const get = (r: PositionRow) => r.actualPct;
        expect(sortRows(rows, get, 'desc').map(r => r.ticker)).toEqual(['C', 'A', 'B']);
        expect(sortRows(rows, get, 'asc').map(r => r.ticker)).toEqual(['A', 'C', 'B']);
    });
    it('sorts text case-insensitively and does not change the input', () => {
        const rows = [row({ ticker: 'b' }), row({ ticker: 'A' })];
        expect(sortRows(rows, r => r.ticker, 'asc').map(r => r.ticker)).toEqual(['A', 'b']);
        expect(rows.map(r => r.ticker)).toEqual(['b', 'A']);
    });
});

describe('moneyText', () => {
    const fmt = (v: number) => `$${v}`;
    it('formats, masks in privacy mode, and dashes an unknown value', () => {
        expect(moneyText(5, false, fmt)).toBe('$5');
        expect(moneyText(5, true, fmt)).toBe('$••••');
        expect(moneyText(null, true, fmt)).toBe('—');
        expect(moneyText(0, false, fmt)).toBe('$0');
    });
});

describe('sortRows ties', () => {
    it('keeps the incoming order for rows that tie, so a pre-ordering shows through', () => {
        const rows = [row({ ticker: 'A', actualPct: 0 }), row({ ticker: 'B', actualPct: 0 }), row({ ticker: 'C', actualPct: 3 })];
        expect(sortRows(rows, r => r.actualPct, 'desc').map(r => r.ticker)).toEqual(['C', 'A', 'B']);
    });
});

describe('weightHeat', () => {
    it('shades a funded weight, stronger for bigger weights, and leaves 0 and unknown unshaded', () => {
        expect(weightHeat(null, 'actual')).toBeUndefined();
        expect(weightHeat(0, 'target')).toBeUndefined();
        expect(weightHeat(12, 'actual')).toContain('16, 185, 129');
        expect(weightHeat(12, 'target')).toContain('99, 102, 241');
        expect(weightHeat(24, 'actual')).toBe(weightHeat(12, 'actual'));
        expect(weightHeat(3, 'actual')).not.toBe(weightHeat(9, 'actual'));
    });
});

describe('totalsFor market and book value', () => {
    it('sums market value and book value, skipping unknown values', () => {
        const t = totalsFor([row({ marketValue: 100, bookValue: 80 }), row({ marketValue: 50, bookValue: null }), row({ marketValue: null, bookValue: 10 })]);
        expect(t.marketValue).toBe(150);
        expect(t.bookValue).toBe(90);
    });
});

describe('rows from an older or partial backend', () => {
    it('rowsForDocument treats a row with no documents list as in no thesis instead of crashing', () => {
        const old = { ...row({ ticker: 'OLD' }), documents: undefined } as unknown as PositionRow;
        expect(rowsForDocument([old, row({ ticker: 'NEW', documents: ['asi'] })], 'asi', 'all').map(r => r.ticker)).toEqual(['NEW']);
    });

    it('normalizePositionRows fills what an older /all-holdings row lacks', () => {
        const [r] = normalizePositionRows([{ ticker: 'LDOS', name: 'Leidos', actualPct: null, targetPct: 0, action: 'INITIATE' }]);
        expect(r.documents).toEqual([]);
        expect(r.held).toBe(false);
        expect(r.shares).toBe(0);
        expect(r.marketValue).toBeNull();
        expect(r.gapPct).toBeNull();
        expect(r.isWatched).toBe(false);
        expect(r.ticker).toBe('LDOS');
    });

    it('treats a row with shares as held when the backend does not say so', () => {
        expect(normalizePositionRows([{ ticker: 'A', shares: 3 }])[0].held).toBe(true);
    });

    it('keeps every field the current backend sends', () => {
        const full = row({ ticker: 'FULL', documents: ['d'], held: false, actualPct: 0 });
        expect(normalizePositionRows([full])[0]).toEqual(full);
    });

    it('drops entries with no ticker and returns an empty list for a non-list', () => {
        expect(normalizePositionRows([{ name: 'x' }, null, 5, { ticker: 'OK' }]).map(r => r.ticker)).toEqual(['OK']);
        expect(normalizePositionRows({ error: 'boom' })).toEqual([]);
        expect(normalizePositionRows(null)).toEqual([]);
    });
});
