---
name: cancel-order
plugin: tradingview
description: >
  Cancel a Working or Inactive order in TradingView via CDP, then mark it
  cancelled in the Trade Log. Triggered when user cancels a Working or Inactive
  entry in the Trade Log UI. Requires TradingView Desktop with --remote-debugging-port=9222.
allowed-tools: Bash, Read, Write
---

## Trigger

This skill is called when a trade-log entry with status `submitted` or `inactive`
is cancelled from the Trade Log UI. Planned (`suggested`/`logged`) entries are
cancelled in JSON only — no TV action needed.

## Prerequisites

- TradingView Desktop running with `--remote-debugging-port=9222`
- Order must be visible in TV's broker panel (Working or Inactive tab)
- The trade-log entry should ideally have a `tvOrderId` field (populated when
  `verifyOrderInBrokerPanel` runs after submission). If missing, match by ticker + side + price.

## Step 1: Locate the Order in TradingView

```javascript
// In plugins/tradingview/node/core/trading.js
// Call via: python3 investment_screener/backend/py_services/place_order.py --cancel --order-id <tvOrderId>

async function cancelOrder({ ticker, action, limitPrice, tvOrderId }) {
    // Navigate to Orders tab in broker panel
    // Click Working or Inactive sub-tab
    // Find row matching tvOrderId (preferred) OR ticker+action+limitPrice
    // Click the × cancel button on that row
    // Wait 1000ms, verify the row is gone
    // Return: { cancelled: true/false, orderId, ticker, action }
}
```

## Step 2: Mark Cancelled in Trade Log

After successful TV cancellation, PATCH the trade-log entry:
```bash
curl -s -X PATCH http://localhost:3001/api/trading/log/{entry_id} \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"status": "cancelled"}'
```

## Step 3: Report Result

```
✅ Order cancelled in TradingView: {ACTION} {SHARES} {TICKER}
   Trade Log entry updated → CANCELLED
```

## Error Handling

- **TV not connected**: Warn user that TV is offline. Still allow cancelling in Trade Log only (local cancel).
- **Order not found in TV**: Warn "Order may have already filled or been cancelled in TV." Still mark Trade Log as cancelled.
- **Multiple matches**: If no tvOrderId and multiple rows match, present list to user and ask which to cancel.

## Future Work

- Store `tvOrderId` on the trade-log entry when `verifyOrderInBrokerPanel` succeeds after submission
- Add a `tvOrderId` field to `TradeLogEntry` in api.ts
- Pass `tvOrderId` from the audit log entry written in `confirmAndSubmit()`

## Implementation Status

⚠️ **STUB** — CDP cancel automation not yet implemented in `trading.js`.
The skill design is complete. Implementation needed:
1. `cancelOrder()` function in `plugins/tradingview/node/core/trading.js`
2. `--cancel` flag in `investment_screener/backend/py_services/place_order.py`
3. Backend route `POST /api/trading/cancel` that calls place_order.py --cancel
4. Trade Log UI calls this route when user cancels a Working/Inactive entry
