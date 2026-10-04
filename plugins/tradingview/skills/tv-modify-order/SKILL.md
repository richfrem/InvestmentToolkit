---
name: tv-modify-order
plugin: tradingview
description: Modify the limit price or quantity of a Working order in TradingView via CDP. Trigger on /tv-modify-order or 'modify order [UUID]'.
allowed-tools: Bash, Read, Write
---

# TradingView Modify Order

Modify the limit price or quantity of a Working order in TradingView via CDP.

## Contents

- [Constraints](#constraints)
- [Quick start](#quick-start)
- [Workflow](#workflow)
- [Verification](#verification)

## Constraints

- Human confirmation: Require user confirmation before dispatching price/quantity modifications.
- React input simulation: Form fields must use keyboard events to trigger React onChange handlers.
- Working orders only: Confirm order is still open before modifying.

## Quick start

```bash
python3 plugins/tradingview/scripts/place_order.py --modify <UUID> --price <NEW_PRICE>
```

## Workflow

1. Locate order by UUID or ticker using `tv-get-orders`.
2. Display proposed modification table (Old Price -> New Price, Old Qty -> New Qty).
3. On user approval, click Modify in TradingView broker panel.
4. Fill new values using simulated keyboard inputs and submit.
5. Confirm updated order state.

## Verification

- Confirm order in broker panel reflects new price/quantity.
- Validate routing cases against `evals/evals.json`.
