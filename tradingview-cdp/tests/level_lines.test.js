/**
 * level_lines.test.js - Jest tests for drawing stored price levels as per-symbol chart lines.
 *
 * Purpose:
 *   Verifies which existing drawings the clear step removes (only lines this tool drew, or every
 *   line when asked), and that syncing one symbol switches the chart, clears, draws one labelled
 *   line per level and checks the result, using a mock CDP client.
 *
 * Key Input Dependencies:
 *   - ../core/level_lines.js
 */
import { jest, describe, it, expect } from '@jest/globals';
import { LINE_PREFIX, planClear, syncSymbolLevels, syncLevelPlan } from '../core/level_lines.js';

const shapes = [
  { id: 'a', name: 'horizontal_line', text: `${LINE_PREFIX} Buy 1 $10.00` },
  { id: 'b', name: 'horizontal_line', text: 'my own support' },
  { id: 'c', name: 'trend_line', text: '' },
  { id: 'd', name: 'text', text: `${LINE_PREFIX} note` },
  { id: 'e', name: 'horizontal_ray', text: '' },
];

describe('planClear', () => {
  it('removes only lines this tool drew by default', () => {
    expect(planClear(shapes)).toEqual(['a']);
  });

  it('removes every line drawing, and only line drawings, with allLines', () => {
    expect(planClear(shapes, { allLines: true })).toEqual(['a', 'b', 'c', 'e']);
  });
});

function mockClient(responses) {
  const evaluate = jest.fn();
  responses.forEach((r) => evaluate.mockResolvedValueOnce({ result: { value: JSON.stringify(r) } }));
  return { Runtime: { evaluate } };
}

describe('syncSymbolLevels', () => {
  const lines = [{ price: 10, label: 'Buy 1', color: '#26a69a' }, { price: 20, label: 'Trim 1', color: '#fdd835' }];

  it('switches, clears, draws and verifies the lines for one symbol', async () => {
    const client = mockClient([
      { success: true, symbol: 'NASDAQ:SMCI', shapes: [shapes[0], shapes[1]] },   // switch + list
      { success: true, removed: 1, drawn: 2, tagged: 2 },                        // clear + draw + verify
    ]);
    const out = await syncSymbolLevels(client, 'SMCI', lines);
    expect(out).toEqual({ success: true, symbol: 'SMCI', chartSymbol: 'NASDAQ:SMCI', removed: 1, drawn: 2 });
    const drawCall = client.Runtime.evaluate.mock.calls[1][0].expression;
    expect(drawCall).toContain('"a"');           // tagged line removed
    expect(drawCall).not.toContain('"b"');       // owner's line kept
    expect(drawCall).toContain(`${LINE_PREFIX} Buy 1 $10.00`);
  });

  it('fails without drawing when the chart did not switch to the symbol', async () => {
    const client = mockClient([{ success: true, symbol: 'NASDAQ:ZS', shapes: [] }]);
    const out = await syncSymbolLevels(client, 'SMCI', lines);
    expect(out.success).toBe(false);
    expect(out.error).toMatch(/ZS/);
    expect(client.Runtime.evaluate).toHaveBeenCalledTimes(1);
  });

  it('fails when fewer lines are on the chart than were asked for', async () => {
    const client = mockClient([
      { success: true, symbol: 'NASDAQ:SMCI', shapes: [] },
      { success: true, removed: 0, drawn: 2, tagged: 1 },
    ]);
    const out = await syncSymbolLevels(client, 'SMCI', lines);
    expect(out.success).toBe(false);
    expect(out.error).toMatch(/1 of 2/);
  });

  it('dry run lists what would be removed and drawn without changing the chart', async () => {
    const client = mockClient([{ success: true, symbol: 'NASDAQ:SMCI', shapes: [shapes[0], shapes[1]] }]);
    const out = await syncSymbolLevels(client, 'SMCI', lines, { dryRun: true });
    expect(out).toMatchObject({ success: true, dryRun: true, wouldRemove: 1, wouldDraw: 2, otherLines: 1 });
    expect(client.Runtime.evaluate).toHaveBeenCalledTimes(1);
  });
});

describe('syncLevelPlan', () => {
  it('syncs every symbol in the plan and reports failures by name', async () => {
    const client = mockClient([
      { success: true, symbol: 'NASDAQ:AAPL', shapes: [] },
      { success: true, removed: 0, drawn: 1, tagged: 1 },
      { success: true, symbol: 'NASDAQ:ZS', shapes: [] },   // asked for SMCI, chart stayed on ZS
    ]);
    const plan = { AAPL: [{ price: 1, label: 'Buy 1', color: '#fff' }], SMCI: [{ price: 2, label: 'Buy 1', color: '#fff' }] };
    const out = await syncLevelPlan(client, plan, { settleMs: 0 });
    expect(out.success).toBe(false);
    expect(out.synced).toEqual(['AAPL']);
    expect(out.failed.map((f) => f.symbol)).toEqual(['SMCI']);
  });
});
