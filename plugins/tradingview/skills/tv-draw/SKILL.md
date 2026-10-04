---
name: tv-draw
plugin: tradingview
description: Draws and annotates horizontal level lines, entry/exit price zones, and text tags directly onto the active TradingView chart. Trigger on /tv-draw or 'draw horizontal line'.
allowed-tools: Bash, Read, Write
---

# TradingView Draw

Draws and annotates horizontal level lines, entry/exit price zones, and text tags directly onto the active TradingView chart.

## Contents

- [Constraints](#constraints)
- [Quick start](#quick-start)
- [Workflow](#workflow)
- [Verification](#verification)

## Constraints

- Active chart boundary: Operates on active TradingView chart layout via CDP.
- Color convention: Support/Buy zones (Green), Resistance/Trim zones (Orange/Red), Fair Value (Blue).
- Coordinate precision: Price levels must use decimal float values.

## Quick start

```bash
node tradingview-cdp/cli.js chart draw horizontal --price {PRICE} --color "#00FF00"
```

## Workflow

1. Resolve target price level and drawing type (line, zone, annotation).
2. Execute drawing command via CDP dispatch.
3. Confirm drawing object appears on active chart canvas.

## Verification

- Confirm drawing rendered on chart viewport.
- Validate routing cases against `evals/evals.json`.
