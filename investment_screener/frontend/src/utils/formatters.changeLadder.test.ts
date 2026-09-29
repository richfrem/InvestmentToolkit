/**
 * formatters.changeLadder.test.ts
 *
 * Purpose:
 *     One threshold ladder for % change colours, with two palettes (table cell
 *     rgba, heatmap tile solid) and a per-period scale. Before 2026-09-28 the
 *     heatmap carried its own copy of the thresholds.
 *
 * Layer: Frontend / Utils (vitest)
 */
import { describe, it, expect } from 'vitest';
import { changeBgDaily, changeTileColor, NO_DATA_TILE_COLOR } from './formatters';

describe('shared % change colour ladder', () => {
    it('table colours at scale 1 are unchanged (regression)', () => {
        expect(changeBgDaily(8)).toBe('rgba(0,77,0,0.85)');
        expect(changeBgDaily(0.2)).toBe('rgba(30,180,30,0.30)');
        expect(changeBgDaily(-0.2)).toBe('rgba(200,30,30,0.30)');
        expect(changeBgDaily(-6)).toBe('rgba(100,0,0,0.80)');
        expect(changeBgDaily(-9)).toBe('rgba(70,0,0,0.85)');
        expect(changeBgDaily(null)).toBe('transparent');
    });

    it('heatmap tile colours at scale 1 are unchanged (regression)', () => {
        expect(changeTileColor(8)).toBe('#004d00');
        expect(changeTileColor(0.2)).toBe('#40ff40');
        expect(changeTileColor(-6)).toBe('#600000');
        expect(changeTileColor(-9)).toBe('#400000');
        expect(changeTileColor(null)).toBe(NO_DATA_TILE_COLOR);
    });

    it('both palettes step at the same scaled thresholds', () => {
        // -6% is "very dark red" for a day but only "light red" at 10x (1Y)
        expect(changeTileColor(-6, 10)).toBe('#e00000');
        expect(changeBgDaily(-6, 10)).toBe('rgba(210,0,0,0.55)');
        expect(changeTileColor(4, 8)).toBe('#00e000');
        expect(changeBgDaily(4, 8)).toBe('rgba(0,220,0,0.55)');
    });
});
