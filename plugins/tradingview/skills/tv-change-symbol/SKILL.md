---
name: tv-change-symbol
plugin: tradingview
description: Change the active TradingView chart symbol via CDP. Trigger on /tv-change-symbol or 'switch chart to [TICKER]'.
allowed-tools: Bash, Read, Write
---

# TradingView Change Symbol

Change the active TradingView chart symbol via CDP.

## Contents

- [Constraints](#constraints)
- [Quick start](#quick-start)
- [Workflow](#workflow)
- [Verification](#verification)

## Constraints

- Exact ticker format: Use exchange-appropriate symbols (e.g. `NVDA`, `PSU.U.TO`).
- Port 9222 liveness: TradingView Desktop must be connected on port 9222.
- Single chart target: Commands modify the active chart layout only.

## Quick start

```bash
node tradingview-cdp/cli.js chart symbol {TICKER}
```

## Workflow

1. Verify CDP connection with `tv_health_check.py`.
2. Dispatch chart symbol command: `node tradingview-cdp/cli.js chart symbol {TICKER}`.
3. Await DOM settlement and confirm active header shows new ticker.

## Verification

- Confirm active chart header matches requested ticker.
- Validate routing cases against `evals/evals.json`.
