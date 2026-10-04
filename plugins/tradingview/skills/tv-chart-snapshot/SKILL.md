---
name: tv-chart-snapshot
plugin: tradingview
description: Captures a chart screenshot for a ticker in TradingView Desktop and saves it to PortfolioAnalysis/screenshots/. Trigger on /tv-snapshot [TICKER] or 'chart screenshot [TICKER]'.
allowed-tools: Bash, Read, Write
---

# TradingView Chart Snapshot

Captures a chart screenshot for a ticker in TradingView Desktop and saves it to PortfolioAnalysis/screenshots/.

## Contents

- [Constraints](#constraints)
- [Quick start](#quick-start)
- [Workflow](#workflow)
- [Verification](#verification)

## Constraints

- Storage directory: All screenshots must be saved to `PortfolioAnalysis/screenshots/{YYYY-MM-DD}/{TICKER}.png`.
- Chart readiness: Await 1.5s post-symbol change before capture to allow indicators and candles to render.
- Zero distortion: Capture full chart viewport without UI menu obstruction.

## Quick start

```bash
python3 plugins/tradingview/scripts/tv_snapshot.py {TICKER}
```

## Workflow

1. Switch active chart to target ticker via CDP.
2. Allow DOM and indicator series to complete rendering.
3. Capture screenshot via CDP viewport rasterization.
4. Write image file to `PortfolioAnalysis/screenshots/{YYYY-MM-DD}/{TICKER}.png`.
5. Return file path to user in chat.

## Verification

- Confirm image file exists and size > 20KB.
- Validate routing cases against `evals/evals.json`.
