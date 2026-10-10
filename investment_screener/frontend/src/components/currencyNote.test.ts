import { describe, expect, it } from 'vitest';
import { currencyAgeLabel } from './currencyNote';

describe('currencyAgeLabel', () => {
    it('says today, yesterday, or how many days ago', () => {
        expect(currencyAgeLabel(0)).toBe('today');
        expect(currencyAgeLabel(1)).toBe('yesterday');
        expect(currencyAgeLabel(5)).toBe('5 days ago');
    });
    it('never says a negative age', () => {
        expect(currencyAgeLabel(-3)).toBe('today');
    });
});
