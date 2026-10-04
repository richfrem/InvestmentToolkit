---
name: tv-change-type
plugin: tradingview
description: Change the active TradingView chart type (candlestick, Heikin Ashi, line, area, Renko). Trigger on /tv-change-type or 'change chart type to [TYPE]'.
allowed-tools: Bash, Read, Write
---

# TradingView Change Type

Change the active TradingView chart type (candlestick, Heikin Ashi, line, area, Renko).

## Contents

- [Constraints](#constraints)
- [Quick start](#quick-start)
- [Workflow](#workflow)
- [Verification](#verification)
- [References](#references)

## Constraints

- Supported types only: Candlestick (1), Bar (0), Line (2), Area (3), Heikin Ashi (8), Renko (4).
- Port 9222 liveness: TradingView Desktop must be running on port 9222.
- No layout disruption: Preserves existing indicators and drawings.

## Quick start

```bash
node tradingview-cdp/cli.js chart style {STYLE_ID}
```

## Workflow

1. Map user request to style ID (e.g. 'heikin-ashi' -> 8, 'candlestick' -> 1).
2. Execute CLI command via CDP: `node tradingview-cdp/cli.js chart style {STYLE_ID}`.
3. Confirm chart visual updates to requested presentation.

## Verification

- Confirm chart reflects requested candle style.
- Validate routing cases against `evals/evals.json`.

## References

- [Chart Types Reference](references/chart-types-reference.md): Mapping of chart style names to internal TradingView numeric IDs.
