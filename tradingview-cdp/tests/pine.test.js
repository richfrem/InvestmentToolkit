/**
 * pine.test.js - Jest tests for Pine Editor CDP automation.
 * 
 * Purpose:
 *   Verifies Pine Script editor automation features (injection, removal, and reading values)
 *   using mock CDP clients without requiring a live TradingView connection.
 * 
 * Key Input Dependencies:
 *   - ../core/pine.js
 * 
 * Key Output Dependencies:
 *   None (reports test execution results to Jest runner console)
 */

import { jest, describe, it, expect } from '@jest/globals';
import { injectPineScript, removePineScript, readIndicatorValues } from '../core/pine.js';

// ── Task 1: Pine Script Injection ──────────────────────────────────────────────

describe('injectPineScript', () => {
  // Routes each CDP evaluate() by the step its expression implements, so the
  // tests don't depend on call order (the prior order-based mocks went stale
  // as steps were added and all three failed on main as of 2026-09-28).
  const SCRIPT = "//@version=6\nindicator('AI Thesis APLD', shorttitle='AI Thesis', overlay=true)\nplot(close)";
  const mockClient = ({ inject = { success: true }, activeSource = '', studies = [] } = {}) => ({
    Runtime: {
      evaluate: jest.fn(async ({ expression }) => {
        if (expression.includes('pine-dialog-button not found')) return { result: { value: JSON.stringify({ alreadyOpen: true }) } };
        if (expression.includes('This script is read-only')) return { result: { value: JSON.stringify({ needsNewTab: false }) } };
        if (expression.includes('activeSource')) return { result: { value: JSON.stringify({ activeSource }) } };
        if (expression.includes("executeEdits('pine-inject'")) return { result: { value: JSON.stringify(inject) } };
        if (expression.includes('getAllStudies')) return { result: { value: JSON.stringify({ studies }) } };
        return { result: { value: undefined } };
      }),
    },
  });

  it('reports success only when the indicator is on the chart', async () => {
    const result = await injectPineScript(mockClient({ studies: [{ id: 'a', name: 'AI Thesis APLD' }] }), SCRIPT);
    expect(result).toEqual({ success: true, verified: true, study: 'AI Thesis APLD' });
  }, 30000);

  it('fails when the indicator never appears on the chart', async () => {
    const result = await injectPineScript(mockClient({ studies: [{ id: 'b', name: 'AI TA Levels v6' }] }), SCRIPT);
    expect(result.success).toBe(false);
    expect(result.error).toMatch(/not found on chart/);
    expect(result.studies).toEqual(['AI TA Levels v6']);
  }, 30000);

  it('fails when the Monaco edit itself fails', async () => {
    const result = await injectPineScript(mockClient({ inject: { success: false, error: 'Monaco editor not found via fiber' } }), SCRIPT);
    expect(result.success).toBe(false);
    expect(result.error).toMatch(/Monaco editor not found/);
  }, 30000);

  it('refuses to overwrite an active tab holding a different script', async () => {
    const client = mockClient({ activeSource: "//@version=6\nindicator('AI TA Levels v6')\nplot(close)" });
    const result = await injectPineScript(client, SCRIPT);
    expect(result.success).toBe(false);
    expect(result.error).toMatch(/refusing to overwrite 'AI TA Levels v6'/);
    const exprs = client.Runtime.evaluate.mock.calls.map(c => c[0].expression);
    expect(exprs.some(e => e.includes("executeEdits('pine-inject'"))).toBe(false);
  }, 30000);

  it('refusing to overwrite leaves the chart legend untouched', async () => {
    // 2026-09-28: the legend cleanup ran before the guard and removed the
    // user's "AI TA Levels v6" from the APLD chart even though inject refused.
    const client = mockClient({ activeSource: "//@version=6\nindicator('AI TA Levels v6')\nplot(close)" });
    await injectPineScript(client, SCRIPT);
    const exprs = client.Runtime.evaluate.mock.calls.map(c => c[0].expression);
    expect(exprs.some(e => e.includes('aria-label="Remove"'))).toBe(false);
  }, 30000);

  it('legend cleanup targets only this script family, not other AI indicators', async () => {
    // "AI TA Levels v6" is a separate indicator; injecting the thesis overlay
    // must not remove it (it was removed from the APLD chart on 2026-09-28).
    const overlay = "//@version=6\nindicator(\"AI Thesis Overlay - APLD\", overlay=true)\nplot(close)";
    const client = mockClient({ studies: [{ id: 'c', name: 'AI Thesis Overlay - APLD' }] });
    await injectPineScript(client, overlay);
    const cleanup = client.Runtime.evaluate.mock.calls.map(c => c[0].expression)
      .find(e => e.includes('aria-label="Remove"'));
    expect(cleanup).toBeDefined();
    expect(cleanup).not.toMatch(/ai ta levels/);
    expect(cleanup).not.toMatch(/'ai-ta'/);
    expect(cleanup).toMatch(/ai thesis overlay/);
  }, 30000);

  it('replaces an overlay from the same family (e.g. another ticker)', async () => {
    const overlay = "//@version=6\nindicator(\"AI Thesis Overlay - APLD\", overlay=true)\nplot(close)";
    const client = mockClient({
      activeSource: "//@version=6\nindicator(\"AI Thesis Overlay - NBIS\", overlay=true)\nplot(close)",
      studies: [{ id: 'c', name: 'AI Thesis Overlay - APLD' }],
    });
    const result = await injectPineScript(client, overlay);
    expect(result).toEqual({ success: true, verified: true, study: 'AI Thesis Overlay - APLD' });
  }, 30000);
});

describe('removePineScript', () => {
  it('returns success when Runtime.evaluate resolves', async () => {
    const mockClient = {
      Runtime: {
        evaluate: jest.fn().mockResolvedValue({ result: { value: 'true' } }),
      },
    };
    const result = await removePineScript(mockClient, 'AI_Custom_TA');
    expect(result.success).toBe(true);
  });

  it('returns failure if Runtime throws', async () => {
    const mockClient = {
      Runtime: {
        evaluate: jest.fn().mockRejectedValue(new Error('CDP error')),
      },
    };
    const result = await removePineScript(mockClient, 'AI_Custom_TA');
    expect(result.success).toBe(false);
  });
});

// ── Task 2: Data Window Extraction ────────────────────────────────────────────

describe('readIndicatorValues', () => {
  it('reads indicator values from the Data Window', async () => {
    const mockClient = {
      Runtime: {
        evaluate: jest.fn().mockResolvedValue({
          result: { value: JSON.stringify({ MACD: '1.25', Signal: 'BUY' }) },
        }),
      },
    };
    const result = await readIndicatorValues(mockClient, 'AI_Custom_TA');
    expect(result.success).toBe(true);
    expect(result.data.MACD).toBe('1.25');
  });

  it('returns failure if Runtime.evaluate throws', async () => {
    const mockClient = {
      Runtime: {
        evaluate: jest.fn().mockRejectedValue(new Error('Runtime error')),
      },
    };
    const result = await readIndicatorValues(mockClient, 'AI_Custom_TA');
    expect(result.success).toBe(false);
    expect(result.error).toBeTruthy();
  });
});
