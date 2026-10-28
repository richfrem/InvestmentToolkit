/**
 * watchlist.test.js - Jest tests for Watchlist CDP automation.
 * 
 * Purpose:
 *   Verifies Watchlist automation features (open, get, add, remove, create, and delete)
 *   using mock CDP clients.
 * 
 * Key Input Dependencies:
 *   - ../core/watchlist.js
 * 
 * Key Output Dependencies:
 *   None (reports test execution results to Jest runner console)
 */

import { jest, describe, it, expect } from '@jest/globals';
import { readFileSync } from 'fs';
import {
  openWatchlist,
  getWatchlist,
  addWatchlistItem,
  removeWatchlistItem,
  createWatchlist,
  deleteWatchlist
} from '../core/watchlist.js';

describe('Watchlist Automation Core (CDP)', () => {
  describe('openWatchlist', () => {
    it('should evaluate expression to open watchlist by name', async () => {
      const mockClient = {
        Runtime: {
          evaluate: jest.fn().mockResolvedValue({
            result: { value: JSON.stringify({ success: true, name: 'IT_Holdings' }) }
          })
        }
      };
      const result = await openWatchlist(mockClient, 'IT_Holdings');
      expect(result.success).toBe(true);
      expect(result.name).toBe('IT_Holdings');
    });
  });

  describe('getWatchlist', () => {
    it('should read all tickers and prices from the current watchlist', async () => {
      const mockClient = {
        Runtime: {
          evaluate: jest.fn().mockResolvedValue({
            result: { value: JSON.stringify({
              success: true,
              watchlist: 'IT_Holdings',
              items: [
                { symbol: 'BE', price: 261.18, changePercent: 4.94, extendedChangePercent: null, sessionLabel: null },
                { symbol: 'BTCUSD', price: 63086, changePercent: -0.74, extendedChangePercent: null, sessionLabel: null }
              ]
            }) }
          })
        }
      };
      const result = await getWatchlist(mockClient);
      expect(result.success).toBe(true);
      expect(result.items).toHaveLength(2);
      expect(result.items[0].symbol).toBe('BE');
    });

    it('should surface extendedChangePercent and sessionLabel when the row is outside regular hours', async () => {
      const mockClient = {
        Runtime: {
          evaluate: jest.fn().mockResolvedValue({
            result: { value: JSON.stringify({
              success: true,
              watchlist: 'TV-Full Watchlist',
              items: [
                { symbol: 'NBIS', price: 187.77, changePercent: -15.02, extendedChangePercent: 4.08, sessionLabel: 'Overnight via BOATS' }
              ]
            }) }
          })
        }
      };
      const result = await getWatchlist(mockClient);
      expect(result.items[0].extendedChangePercent).toBe(4.08);
      expect(result.items[0].sessionLabel).toBe('Overnight via BOATS');
    });
  });

  describe('addWatchlistItem', () => {
    it('should insert a symbol into the watchlist', async () => {
      const mockClient = {
        Runtime: {
          evaluate: jest.fn().mockResolvedValue({
            result: { value: JSON.stringify({ success: true, symbol: 'NVDA' }) }
          })
        }
      };
      const result = await addWatchlistItem(mockClient, 'IT_Holdings', 'NVDA');
      expect(result.success).toBe(true);
    });
  });

  describe('removeWatchlistItem', () => {
    it('should delete a symbol from the watchlist', async () => {
      const mockClient = {
        Runtime: {
          evaluate: jest.fn()
            // openWatchlist calls:
            .mockResolvedValueOnce({ result: { value: 'true' } }) // sidebar click
            .mockResolvedValueOnce({ result: { value: 'true' } }) // dropdown click
            .mockResolvedValueOnce({ result: { value: JSON.stringify({ success: true }) } }) // click item
            // removeWatchlistItem calls:
            .mockResolvedValueOnce({ result: { value: JSON.stringify({ cx: 100, cy: 100 }) } }),
        },
        Input: {
          dispatchMouseEvent: jest.fn().mockResolvedValue({})
        }
      };
      const result = await removeWatchlistItem(mockClient, 'IT_Holdings', 'NVDA');
      expect(result.success).toBe(true);
    });
  });

  describe('createWatchlist', () => {
    it('should trigger creation of a new watchlist name', async () => {
      const mockClient = {
        Runtime: {
          evaluate: jest.fn()
            .mockResolvedValueOnce({ result: { value: 'true' } }) // sidebar active
            .mockResolvedValueOnce({ result: { value: 'true' } }) // dropdown click
            .mockResolvedValueOnce({ result: { value: JSON.stringify({ exists: false, copies: 0 }) } }) // existence probe
            .mockResolvedValueOnce({ result: { value: JSON.stringify({ cx: 100, cy: 100 }) } }) // getCreateCoords
            .mockResolvedValueOnce({ result: { value: 'true' } }) // fill input
            .mockResolvedValueOnce({ result: { value: 'true' } }), // confirm enter
        },
        Input: {
          dispatchMouseEvent: jest.fn().mockResolvedValue({})
        }
      };
      const result = await createWatchlist(mockClient, 'IT_New');
      expect(result.success).toBe(true);
    });

    it('should reuse a list that already exists and never create a second copy', async () => {
      const mockClient = {
        Runtime: {
          evaluate: jest.fn()
            .mockResolvedValueOnce({ result: { value: 'true' } }) // sidebar active
            .mockResolvedValueOnce({ result: { value: 'true' } }) // dropdown click
            .mockResolvedValueOnce({ result: { value: JSON.stringify({ exists: true, copies: 1 }) } }) // existence probe
            .mockResolvedValueOnce({ result: { value: 'true' } }), // close menu
        },
        Input: {
          dispatchMouseEvent: jest.fn().mockResolvedValue({})
        }
      };
      const result = await createWatchlist(mockClient, 'TV-Full Watchlist');
      expect(result.success).toBe(true);
      expect(result.existed).toBe(true);
      // No click on "Create new list...", so no new list is made.
      expect(mockClient.Input.dispatchMouseEvent).not.toHaveBeenCalled();
    });
  });

  describe('deleteWatchlist', () => {
    it('should delete the specified watchlist', async () => {
      const mockClient = {
        Runtime: {
          evaluate: jest.fn()
            // openWatchlist calls:
            .mockResolvedValueOnce({ result: { value: 'true' } })
            .mockResolvedValueOnce({ result: { value: 'true' } })
            .mockResolvedValueOnce({ result: { value: JSON.stringify({ success: true }) } })
            // deleteWatchlist calls:
            .mockResolvedValueOnce({ result: { value: 'true' } }) // open settings
            .mockResolvedValueOnce({ result: { value: JSON.stringify({ cx: 100, cy: 100 }) } }) // getDeleteCoords
            .mockResolvedValueOnce({ result: { value: 'true' } }), // confirm dialog
        },
        Input: {
          dispatchMouseEvent: jest.fn().mockResolvedValue({})
        }
      };
      const result = await deleteWatchlist(mockClient, 'IT_New');
      expect(result.success).toBe(true);
    }, 15000);
  });

  describe('row selectors', () => {
    it('never match a symbol row by its hashed class suffix, which changes with every TradingView release', () => {
      const src = readFileSync(new URL('../core/watchlist.js', import.meta.url), 'utf-8');
      expect(src).not.toMatch(/\[class\*="symbol-[A-Za-z0-9_]{6,}"\]/);
    });
  });

  describe('getWatchlist on a virtualized list', () => {
    it('scrolls the panel and awaits the page script so rows outside the viewport are read', async () => {
      const mockClient = {
        Runtime: {
          evaluate: jest.fn().mockResolvedValue({
            result: { value: JSON.stringify({ success: true, watchlist: 'W', items: [] }) }
          })
        }
      };
      await getWatchlist(mockClient);
      const call = mockClient.Runtime.evaluate.mock.calls[0][0];
      expect(call.awaitPromise).toBe(true);
      expect(call.expression).toContain('scrollTop');
      expect(call.expression).toContain('scrollHeight');   // scrolls until the end of the list
    });
  });
});
