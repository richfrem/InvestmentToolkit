---
name: tv-place-order
plugin: tradingview
description: Place buy or sell orders via TradingView connected broker panel using CDP with mandatory HITL approval. Trigger on /place-order or 'buy [N] shares of [TICKER]'.
allowed-tools: Bash, Read, Write
---

# TradingView Place Order

Place buy or sell orders via TradingView connected broker panel using CDP with mandatory HITL approval.

## Contents

- [Constraints](#constraints)
- [Quick start](#quick-start)
- [Workflow](#workflow)
- [Verification](#verification)

## Constraints

- No autonomous execution: Adheres strictly to Rule #17; requires explicit HITL user confirmation.
- Account isolation: Verify target account (TFSA, RRSP, Cash) before filling order dialog.
- Day order default: Orders submitted as Day orders; user must change to GTC manually in UI if desired.
- Capital sourcing: Sells PSU-U.TO in the same account to fund equity purchases.

## Quick start

```bash
python3 plugins/tradingview/scripts/place_order.py --ticker {TICKER} --shares {SHARES} --price {PRICE} --dry-run
```

## Workflow

1. Pre-flight check: Verify broker login and account buying power.
2. Staging: Calculate share count and check PSU-U.TO capital sourcing.
3. Open order dialog via CDP and fill ticker, side, shares, and limit price.
4. Screenshot filled order form and present confirmation card to user.
5. On explicit user 'CONFIRM', click submit.
6. Trigger `/tv-portfolio-sync` post-execution.

## Verification

- Confirm order appears in Working orders table.
- Validate routing cases against `evals/evals.json`.
