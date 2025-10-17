import { describe, it, expect } from 'vitest';
import { getAllAccountData } from '../../src/services/questradeService.ts';

describe('Integration: getAllAccountData', () => {
  it('should fetch all account data from Questrade API', async () => {
    const result = await getAllAccountData();
    expect(result).toHaveProperty('accounts');
    expect(result).toHaveProperty('positions');
    expect(result).toHaveProperty('balances');
    expect(Array.isArray(result.accounts)).toBe(true);
    expect(Array.isArray(result.positions)).toBe(true);
    expect(Array.isArray(result.balances)).toBe(true);
  });
});
