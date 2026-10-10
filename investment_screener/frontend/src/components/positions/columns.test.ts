import { describe, expect, it } from 'vitest';
import { COLUMNS, COLUMNS_BY_ID } from './columns';
import { THESIS_PRESET } from './presets';

describe('column registry', () => {
    it('has unique ids', () => {
        expect(new Set(COLUMNS.map(c => c.id)).size).toBe(COLUMNS.length);
    });
    it('every preset column exists in the registry', () => {
        for (const id of THESIS_PRESET.columns) expect(COLUMNS_BY_ID[id], id).toBeDefined();
        expect(COLUMNS_BY_ID[THESIS_PRESET.sort.id]).toBeDefined();
    });
    it('every column has a label, a width and a cell', () => {
        for (const c of COLUMNS) {
            expect(c.label.length, c.id).toBeGreaterThan(0);
            expect(c.width, c.id).toBeGreaterThan(0);
            expect(typeof c.cell, c.id).toBe('function');
        }
    });
    it('the weight columns that the totals row needs define a total', () => {
        for (const id of ['actualPct', 'targetPct', 'gapPct']) expect(typeof COLUMNS_BY_ID[id].total, id).toBe('function');
    });
});
