---
name: tv-chart-setup
plugin: tradingview
description: Complete agent workspace setup: switch to agent-layout, change symbol, and set timeframe in one shot. Trigger on /tv-chart-setup or 'setup chart for [TICKER]'.
allowed-tools: Bash, Read, Write
---

# TradingView Chart Setup

Complete agent workspace setup: switch to agent-layout, change symbol, and set timeframe in one shot.

## Contents

- [Constraints](#constraints)
- [Quick start](#quick-start)
- [Workflow](#workflow)
- [Verification](#verification)

## Constraints

- Layout authority: Uses designated `agent-layout` to avoid disrupting user custom layouts.
- Standard timeframes: Supports 1D (daily), 1W (weekly), 1h (hourly), 15m.
- Sequential execution: Switch layout -> switch symbol -> set timeframe.

## Quick start

```bash
node tradingview-cdp/cli.js chart symbol {TICKER} && node tradingview-cdp/cli.js chart timeframe 1D
```

## Workflow

1. Switch to `agent-layout`: `node tradingview-cdp/cli.js chart saveLayout` / select layout.
2. Set requested symbol: `node tradingview-cdp/cli.js chart symbol {TICKER}`.
3. Set timeframe (default `1D`): `node tradingview-cdp/cli.js chart timeframe {TIMEFRAME}`.
4. Verify layout is clean and ready for analysis.

## Verification

- Confirm symbol and timeframe reflect requested parameters.
- Validate routing cases against `evals/evals.json`.
