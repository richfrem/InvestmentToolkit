---
name: cancel-order
plugin: tradingview
description: >
  Cancel a Working or Inactive order in TradingView via CDP (clicks the × button
  on the order row), then marks it cancelled in the Trade Log. Requires TradingView
  Desktop with --remote-debugging-port=9222.
allowed-tools: Bash, Read, Write
---

## Trigger

Called when a trade-log entry with status `submitted` or `inactive` is cancelled
from the Trade Log UI, or invoked directly by the user.

Planned (`suggested`/`logged`) entries are cancelled in JSON only — no TV action needed.

## Prerequisites

- TradingView Desktop running with `--remote-debugging-port=9222`
- Order must be visible in TV's broker panel (Working or Inactive tab)
- Trade-log entry should have a `tvOrderId` field (populated on submission)

## Method 1: Via Backend API (Trade Log UI)

The Trade Log × button calls `POST /api/trading/cancel`:

```bash
curl -s -X POST http://localhost:3001/api/trading/cancel \
  -H 'Content-Type: application/json' \
  -d '{
    "entryId": "1c96b4ce4b70",
    "tvOrderId": "292b5304-0c3d-42c2-02c0-290f6d322c12",
    "ticker": "INTC",
    "action": "Buy",
    "limitPrice": 47.00
  }'
```

The backend:
1. Calls `place_order.py --cancel --order-id <tvOrderId>`
2. PATCHes the log entry to `cancelled` regardless of TV result

## Method 2: Python script (direct)

```bash
python3 plugins/tradingview/scripts/tv_cancel_order.py \
    --order-id 292b5304-0c3d-42c2-02c0-290f6d322c12 \
    --ticker INTC --action buy --limit-price 47.00
```

## Method 3: place_order.py CLI

```bash
python3 investment_screener/backend/py_services/place_order.py \
    --cancel --order-id <tvOrderId> \
    --ticker INTC --action buy --limit-price 47.00
```

## How It Works

`cancelOrder()` in `tradingview-cdp/core/trading.js`:

1. Searches the current DOM for an order row containing the UUID — **without navigating tabs** (tab navigation was toggling the broker panel closed)
2. Falls back to tab navigation only if the row is not found directly
3. Clicks the × button (`buttonIndex: -1`, last button in the row)
4. Waits for a secondary TV confirmation dialog ("Cancel order" / "Keep order") and clicks "Cancel order"
5. Waits 1 s, verifies the row is gone from the DOM
6. Returns `{ cancelled: true, verified: true, orderId, ticker, action }`

## Error Handling

- **TV not connected**: Backend still marks log entry as cancelled
- **Order not found**: Returns `{ cancelled: false }` — order may have already filled/expired
- **Tab navigation toggling panel**: Solved by search-first approach (never navigates tabs)

## Implementation Status

✅ **FULLY IMPLEMENTED**

- `cancelOrder()` — `tradingview-cdp/core/trading.js`
- `--cancel` flag — `investment_screener/backend/py_services/place_order.py`
- `tv_cancel_order.py` — `plugins/tradingview/scripts/tv_cancel_order.py`
- Backend route — `POST /api/trading/cancel` in `investment_screener/backend/src/routes/trading.ts`
- Trade Log UI — × button on Working/Inactive rows calls backend cancel endpoint
