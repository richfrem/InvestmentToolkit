# Mode: chart-snapshot (`/tv-snapshot`)

Captures a chart screenshot for a ticker in TradingView Desktop and saves it to PortfolioAnalysis/screenshots/. Trigger on /tv-snapshot [TICKER] or 'chart screenshot [TICKER]'.
Allowed tools: Bash, Read, Write.

Captures a chart screenshot for a ticker in TradingView Desktop and saves it to PortfolioAnalysis/screenshots/.


## Constraints

- Storage directory: All screenshots must be saved to `PortfolioAnalysis/screenshots/{YYYY-MM-DD}/{TICKER}.png`.
- Chart readiness: Await 1.5s post-symbol change before capture to allow indicators and candles to render.
- Zero distortion: Capture full chart viewport without UI menu obstruction.

## Quick start

```bash
node tradingview-cdp/cli.js chart symbol {TICKER} && node tradingview-cdp/cli.js screenshot --output {TICKER}
```

> The earlier version of this skill named a `tv_snapshot.py` script that does not exist. The capture is the Node CLI's `screenshot` command, which writes the PNG under `PortfolioAnalysis/screenshots/`; move or rename it into the dated folder below if that layout is needed.

## Workflow

1. Switch active chart to target ticker via CDP.
2. Allow DOM and indicator series to complete rendering.
3. Capture screenshot via CDP viewport rasterization.
4. Write image file to `PortfolioAnalysis/screenshots/{YYYY-MM-DD}/{TICKER}.png`.
5. Return file path to user in chat.

## Verification

- Confirm image file exists and size > 20KB.
- Validate routing cases against `evals/evals.json`.
