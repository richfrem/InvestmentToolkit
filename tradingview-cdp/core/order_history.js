/**
 * order_history.js - Pure parsing of the broker panel's "Order history" table.
 *
 * Purpose:
 *   Turn the header and cell text read from TradingView's Order history table
 *   into order objects. No CDP or DOM access here, so it is testable on its own;
 *   broker_data.js reads the page and calls this.
 *
 * Key Input Dependencies:
 *   None (plain arrays of strings)
 *
 * Key Output Dependencies:
 *   None
 */

const COLUMNS = {
  symbol: 'Symbol', side: 'Side', type: 'Type', qty: 'Qty', filledQty: 'Filled Qty',
  limitPrice: 'Limit Price', avgFillPrice: 'Avg Fill Price', status: 'Status',
  updateTime: 'Update Time', orderId: 'Order ID', brokerStatus: 'Broker Status',
};

/**
 * Parse a number as TradingView prints it ("1,042.228", "−0.5"); blank or unusable text is null.
 *
 * @param {string} text Cell text
 * @returns {number|null} Parsed number, or null
 */
export function parseNumber(text) {
  const cleaned = String(text ?? '').replace(/,/g, '').replace(/[−–]/g, '-').trim();
  if (!cleaned) return null;
  const value = Number(cleaned);
  return Number.isFinite(value) ? value : null;
}

/**
 * Map Order history rows to order objects by header name, not by column position.
 *
 * @param {string[]} heads Header texts of the visible table
 * @param {string[][]} rows Cell texts, one array per row
 * @param {(string|null)[]} [updateTimesIso] ISO timestamp per row for the Update Time column
 * @returns {{orders: object[], missingColumns: string[]}} Parsed orders, and any required column not found
 */
export function parseOrderHistoryTable(heads, rows, updateTimesIso = []) {
  const index = Object.fromEntries(Object.entries(COLUMNS).map(([key, label]) => [key, heads.indexOf(label)]));
  const missingColumns = ['symbol', 'side', 'filledQty', 'avgFillPrice', 'status', 'updateTime', 'orderId']
    .filter(key => index[key] < 0).map(key => COLUMNS[key]);
  if (missingColumns.length) return { orders: [], missingColumns };
  const cell = (row, key) => (index[key] >= 0 ? String(row[index[key]] ?? '').trim() : '');
  const orders = rows
    .filter(row => cell(row, 'symbol') && cell(row, 'orderId'))
    .map((row, position) => ({
      symbol: cell(row, 'symbol'),
      side: cell(row, 'side').toLowerCase(),
      type: cell(row, 'type').toLowerCase().replace(/\s+/g, ''),
      qty: parseNumber(cell(row, 'qty')),
      filledQty: parseNumber(cell(row, 'filledQty')),
      limitPrice: parseNumber(cell(row, 'limitPrice')),
      avgFillPrice: parseNumber(cell(row, 'avgFillPrice')),
      status: cell(row, 'status').toLowerCase(),
      updateTime: cell(row, 'updateTime'),
      updateTimeIso: updateTimesIso[position] ?? null,
      orderId: cell(row, 'orderId'),
      brokerStatus: cell(row, 'brokerStatus') || null,
    }));
  return { orders, missingColumns: [] };
}
