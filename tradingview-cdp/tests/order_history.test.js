/**
 * order_history.test.js - Jest tests for parsing the broker panel's Order history table.
 *
 * Purpose:
 *   Verifies that header and cell text captured from the live TradingView
 *   "Order history > Filled" table (2026-10-08) parse into order objects.
 *
 * Key Input Dependencies:
 *   - ../core/order_history.js
 *
 * Key Output Dependencies:
 *   None (reports test execution results to Jest runner console)
 */

import { describe, it, expect } from '@jest/globals';
import { parseNumber, parseOrderHistoryTable } from '../core/order_history.js';

// Captured from the live panel: header order differs from the Orders tab's table.
const HEADS = ['Symbol', 'Side', 'Type', 'Qty', 'Filled Qty', 'Limit Price', 'Stop Price', 'Avg Fill Price', 'Status',
  'Update Time', 'Broker Status', 'Stop Offset', 'Limit Offset', 'Route', 'Sub-route', 'Dollar Amount', 'Order ID', ''];
const BE = ['BE', 'Sell', 'Market', '1', '1', '', '', '293.6581', 'filled', '2026-10-06 07:57:58', 'Executed', '', '', 'AUTO', 'AUTO', '',
  '320209bf-3157-4072-0172-29c808010710', ''];
const KOID = ['KOID', 'Buy', 'Limit', '6', '6', '37.00', '', '36.99', 'filled', '2026-10-04 20:00:10', 'Executed', '', '', 'AUTO', 'AUTO', '',
  '34382b4a-3a46-4362-0b63-05c70d3b6601', ''];

describe('Order history parsing', () => {
  it('maps cells by header name and keeps the broker order id', () => {
    const { orders, missingColumns } = parseOrderHistoryTable(HEADS, [BE, KOID], ['2026-10-06T14:57:58.000Z', null]);
    expect(missingColumns).toEqual([]);
    expect(orders[0]).toEqual({
      symbol: 'BE', side: 'sell', type: 'market', qty: 1, filledQty: 1, limitPrice: null, avgFillPrice: 293.6581,
      status: 'filled', updateTime: '2026-10-06 07:57:58', updateTimeIso: '2026-10-06T14:57:58.000Z',
      orderId: '320209bf-3157-4072-0172-29c808010710', brokerStatus: 'Executed',
    });
    expect(orders[1]).toMatchObject({ symbol: 'KOID', side: 'buy', type: 'limit', filledQty: 6, limitPrice: 37, avgFillPrice: 36.99, updateTimeIso: null });
  });

  it('does not depend on column positions', () => {
    const reversed = [...HEADS].reverse();
    const { orders } = parseOrderHistoryTable(reversed, [[...BE].reverse()]);
    expect(orders[0]).toMatchObject({ symbol: 'BE', avgFillPrice: 293.6581, orderId: '320209bf-3157-4072-0172-29c808010710' });
  });

  it('reports missing required columns instead of guessing', () => {
    const heads = HEADS.filter(head => head !== 'Avg Fill Price');
    expect(parseOrderHistoryTable(heads, [BE])).toEqual({ orders: [], missingColumns: ['Avg Fill Price'] });
  });

  it('skips rows without a symbol or order id and normalises order types', () => {
    const stopLimit = [...BE]; stopLimit[2] = 'Stop Limit';
    const blank = BE.map(() => '');
    const { orders } = parseOrderHistoryTable(HEADS, [blank, stopLimit]);
    expect(orders).toHaveLength(1);
    expect(orders[0].type).toBe('stoplimit');
  });

  it('parses numbers as TradingView prints them', () => {
    expect(parseNumber('1,042.228')).toBe(1042.228);
    expect(parseNumber('−0.5')).toBe(-0.5);
    expect(parseNumber('')).toBeNull();
    expect(parseNumber('n/a')).toBeNull();
  });
});
