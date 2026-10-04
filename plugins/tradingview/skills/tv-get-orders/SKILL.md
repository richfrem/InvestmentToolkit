---
name: tv-get-orders
plugin: tradingview
description: Read Working and Inactive orders from TradingView broker panel via CDP. Trigger on /tv-get-orders or 'show open orders'.
allowed-tools: Bash, Read, Write
---

# TradingView Get Orders

Read Working and Inactive orders from TradingView broker panel via CDP.

## Contents

- [Constraints](#constraints)
- [Quick start](#quick-start)
- [Workflow](#workflow)
- [Verification](#verification)

## Constraints

- Read-only: Queries open order rows without modifying order status.
- Broker panel check: Requires broker panel to be connected and logged in.
- Attribute completeness: Returns UUID, Ticker, Side, Quantity, Price, and Status.

## Quick start

```bash
python3 plugins/tradingview/scripts/place_order.py --list
```

## Workflow

1. Check CDP reachability on port 9222.
2. Scrape Working and Inactive orders from broker panel DOM.
3. Format order list in Markdown table: `UUID`, `Ticker`, `Side`, `Qty`, `Price`, `Status`.

## Verification

- Confirm order list renders or reports 'No active orders'.
- Validate routing cases against `evals/evals.json`.
