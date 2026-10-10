import { describe, expect, it } from 'vitest';
import { moveColumn, resizeColumn, resolveColumns, toggleColumn } from './columnPrefs';

const meta = [
    { id: 'symbol', always: true }, { id: 'action' }, { id: 'price' }, { id: 'sector' }, { id: 'earnings' },
];
const defaults = ['symbol', 'action', 'price'];

describe('resolveColumns', () => {
    it('with no saved prefs shows the preset columns in registry order', () => {
        const r = resolveColumns(null, meta, defaults);
        expect([...r.visible].sort()).toEqual(['action', 'price', 'symbol']);
        expect(r.order).toEqual(['symbol', 'action', 'price', 'sector', 'earnings']);
    });
    it('keeps the saved choices, drops ids that no longer exist, and shows brand-new preset columns', () => {
        const r = resolveColumns({ visible: ['symbol', 'sector', 'gone'], columnOrder: ['sector', 'symbol', 'gone', 'action'], columnWidths: { sector: 150 } },
            meta, [...defaults, 'earnings']);
        expect(r.visible.has('sector')).toBe(true);
        expect(r.visible.has('gone')).toBe(false);
        expect(r.visible.has('earnings')).toBe(true);
        expect(r.order).not.toContain('gone');
        expect(r.widths).toEqual({ sector: 150 });
    });
    it('always includes the always-on columns', () => {
        const r = resolveColumns({ visible: ['action'], columnOrder: ['symbol', 'action'], columnWidths: {} }, meta, defaults);
        expect(r.visible.has('symbol')).toBe(true);
    });
});

describe('toggleColumn', () => {
    it('adds or removes a column but never an always-on one', () => {
        const always = new Set(['symbol']);
        const v = new Set(['symbol', 'action']);
        expect([...toggleColumn(v, 'price', always)].sort()).toEqual(['action', 'price', 'symbol']);
        expect([...toggleColumn(v, 'action', always)]).toEqual(['symbol']);
        expect([...toggleColumn(v, 'symbol', always)].sort()).toEqual(['action', 'symbol']);
        expect([...v].sort()).toEqual(['action', 'symbol']); // input not mutated
    });
});

describe('moveColumn', () => {
    it('moves one place up or down and stops at the ends', () => {
        expect(moveColumn(['a', 'b', 'c'], 'b', 'up')).toEqual(['b', 'a', 'c']);
        expect(moveColumn(['a', 'b', 'c'], 'b', 'down')).toEqual(['a', 'c', 'b']);
        expect(moveColumn(['a', 'b', 'c'], 'a', 'up')).toEqual(['a', 'b', 'c']);
        expect(moveColumn(['a', 'b', 'c'], 'c', 'down')).toEqual(['a', 'b', 'c']);
        expect(moveColumn(['a', 'b'], 'zzz', 'up')).toEqual(['a', 'b']);
    });
});

describe('resizeColumn', () => {
    it('sets a width, never below the minimum, without mutating', () => {
        const w = { a: 100 };
        expect(resizeColumn(w, 'a', 150)).toEqual({ a: 150 });
        expect(resizeColumn(w, 'a', 10)).toEqual({ a: 40 });
        expect(w).toEqual({ a: 100 });
    });
});
