/**
 * pine.test.js — Jest tests for Pine Editor CDP automation (Tasks 1 & 2)
 *
 * Tests use mock CDP clients — no live TradingView connection required.
 * Live end-to-end tests live in plugins/tradingview/tests/tv_test_harness.py (Section 1).
 *
 * All real implementations use client.Runtime.evaluate; mocks must return
 * JSON-stringified results matching the evaluate contract.
 */

import { jest, describe, it, expect } from '@jest/globals';
import { injectPineScript, removePineScript, readIndicatorValues } from '../core/pine.js';

// ── Task 1: Pine Script Injection ──────────────────────────────────────────────

describe('injectPineScript', () => {
  it('fails gracefully if Pine Editor tab is not found', async () => {
    const mockClient = {
      Runtime: {
        evaluate: jest.fn().mockResolvedValue({
          result: { value: JSON.stringify({ clicked: false }) },
        }),
      },
    };
    const result = await injectPineScript(mockClient, 'plot(close)');
    expect(result.success).toBe(false);
    expect(result.error).toMatch(/Pine Editor not found/);
  });

  it('returns success when tab is found and Monaco is available', async () => {
    const mockClient = {
      Runtime: {
        evaluate: jest.fn()
          // Call 1: tab-click search → clicked
          .mockResolvedValueOnce({ result: { value: JSON.stringify({ clicked: true, text: 'Pine Editor' }) } })
          // Call 2: Monaco inject → success
          .mockResolvedValueOnce({ result: { value: JSON.stringify({ success: true, method: 'monaco-global' }) } })
          // Call 3: "Add to chart" click
          .mockResolvedValueOnce({ result: { value: 'true' } }),
      },
    };
    const result = await injectPineScript(mockClient, 'plot(close)');
    expect(result.success).toBe(true);
  });

  it('fails gracefully if Monaco editor is not found after tab click', async () => {
    const mockClient = {
      Runtime: {
        evaluate: jest.fn()
          .mockResolvedValueOnce({ result: { value: JSON.stringify({ clicked: true, text: 'Pine Editor' }) } })
          .mockResolvedValueOnce({ result: { value: JSON.stringify({ success: false, error: 'Monaco editor not found via global or fiber' }) } }),
      },
    };
    const result = await injectPineScript(mockClient, 'plot(close)');
    expect(result.success).toBe(false);
    expect(result.error).toMatch(/Pine Editor not found/);
  });
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
