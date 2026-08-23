---
name: tv-modify-order
plugin: tradingview
description: >
  Modify the limit price (and optionally quantity) of a Working or Inactive order
  in TradingView via CDP. Uses keyboard events to fill the modify form so React's
  onChange fires correctly. Requires TradingView Desktop with --remote-debugging-port=9222.
allowed-tools: Bash, Read, Write
---

## Trigger

Invoked when the user wants to change the price of an open limit order, or when
the Trade Log ✏ (pencil) button is clicked on a Working/Inactive row.

## Prerequisites

- TradingView Desktop running with `--remote-debugging-port=9222`
- Order must be visible in TV's broker panel (Working or Inactive tab)
- Trade-log entry should have a `tvOrderId` (populated on submission)

## Method 1: Python script (direct)

```bash
python3 plugins/tradingview/scripts/tv_modify_order.py \
    --order-id 292b5304-0c3d-42c2-02c0-290f6d322c12 \
    --new-price 47.00 \
    --ticker INTC --action buy
```

Optional `--new-shares N` to change quantity.

## Method 2: Via Trade Log UI

The ✏ button on Working/Inactive rows opens the ModifyModal, which calls
`PUT /api/trading/modify` → `place_order.py --modify`.

## How It Works

Two-step process in `tradingview-cdp/core/trading.js`:

### Step 1: `modifyOrder({ orderId, ticker, action, newPrice, newShares })`

1. Finds the order row by UUID (search-first, no tab navigation)
2. Clicks the ✏ pencil button (`buttonIndex: -2`, second-to-last in the row)
3. Waits for the modify form to appear
4. Uses CDP keyboard events to fill the price field:
   - `Ctrl+A` to select all existing text
   - `Input.insertText` to type the new value
   - `Tab` to commit (triggers React's `onChange`)
5. Returns `{ modified: true, formBefore: [...], orderId }`

**Why keyboard events?** Setting `input.value` via React's property setter shows
the new value visually but does NOT trigger `onChange` — TV's React state keeps
the old price and submits it on Confirm. Keyboard events properly fire `onChange`.

### Step 2: `submitModify({ ticker, action, newPrice, orderId })`

1. Finds and clicks the first visible "Confirm" / "Send Order" / "Save" / "Modify" button
2. Waits for a secondary TV confirmation dialog and clicks it
3. Reads the broker panel to verify the new price is reflected
4. Returns `{ clicked, secondaryConfirm, priceMatch, text }`

## Error Handling

- **Form not appearing**: Row not found or pencil click missed — retry or check UUID
- **priceMatch: false**: TV broker panel may take a moment to refresh; the order
  was submitted but the panel hasn't updated yet. Verify manually in TV.

## Implementation Status

✅ **FULLY IMPLEMENTED**

- `modifyOrder()` — `tradingview-cdp/core/trading.js`
- `submitModify()` — `tradingview-cdp/core/trading.js`
- `tv_modify_order.py` — `plugins/tradingview/scripts/tv_modify_order.py`
