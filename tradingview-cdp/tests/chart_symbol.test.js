/**
 * chart_symbol.test.js - Jest tests for reading the active chart symbol.
 *
 * Purpose:
 *   Verifies getSymbol() returns the symbol shown on the chart toolbar, and fails clearly when
 *   the symbol box is missing, using a mock CDP client.
 *
 * Key Input Dependencies:
 *   - ../core/chart.js
 */
import { jest, describe, it, expect } from '@jest/globals';
import { getSymbol } from '../core/chart.js';

describe('getSymbol', () => {
  it('returns the symbol shown on the chart toolbar', async () => {
    const client = { Runtime: { evaluate: jest.fn().mockResolvedValue({ result: { value: JSON.stringify({ symbol: 'HOOD' }) } }) } };
    expect(await getSymbol(client)).toEqual({ success: true, symbol: 'HOOD' });
  });

  it('fails clearly when the symbol box is not found', async () => {
    const client = { Runtime: { evaluate: jest.fn().mockResolvedValue({ result: { value: JSON.stringify({ symbol: null }) } }) } };
    const result = await getSymbol(client);
    expect(result.success).toBe(false);
    expect(result.error).toMatch(/Symbol box/);
  });
});
