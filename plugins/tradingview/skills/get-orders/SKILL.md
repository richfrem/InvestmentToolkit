---
name: get-orders
plugin: tradingview
description: >
  Read Working and Inactive orders from TradingView's broker panel via CDP.
  Returns open order rows including UUID, ticker, side, price, and status.
  Useful for verifying order state, finding order UUIDs for cancel/modify, and
  scripted order management.
allowed-tools: Bash, Read
---

## Trigger

Use when you need to see what orders are currently open in TradingView's broker
panel, or to find an order UUID for use with cancel-order or modify-order.

## Prerequisites

- TradingView Desktop running with `--remote-debugging-port=9222`
- Broker panel visible (Questrade connected)

## Usage

```bash
# All open orders:
python3 scripts/tv_get_orders.py

# Filter by ticker:
python3 scripts/tv_get_orders.py --ticker INTC

# JSON output (for piping):
python3 scripts/tv_get_orders.py --json
```

## Example Output

```
Order ID                                Text
--------------------------------------------------------------------------------
292b5304-0c3d-42c2-02c0-290f6d322c12  INTCBuyLimit1047.00...Good til cancelled

1 order(s) found.
```

## How It Works

Calls `listOpenOrders()` in `trading.js` which reads order rows directly
from the broker panel DOM. Returns an array of `{ orderId, text }` objects where
`orderId` is the UUID extracted from the row text, and `text` is the full raw row.

## Implementation Status

✅ **FULLY IMPLEMENTED**

- `tv_get_orders.py` — `scripts/tv_get_orders.py` (symlink → plugin root)
- `listOpenOrders()` — `tradingview-cdp/core/trading.js`
