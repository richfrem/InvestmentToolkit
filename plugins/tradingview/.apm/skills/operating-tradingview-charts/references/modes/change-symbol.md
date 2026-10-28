# Mode: change-symbol (`/tv-change-symbol`)

Change the active TradingView chart symbol via CDP. Trigger on /tv-change-symbol or 'switch chart to [TICKER]'.
Allowed tools: Bash, Read, Write.

Change the active TradingView chart symbol via CDP.


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

## Levels follow the symbol

The AI TA Levels indicator keeps its levels as inputs, which stay on the chart when the symbol changes, and it draws them only on the ticker named in its "Levels for ticker" input. After switching a chart to a ticker, draw that ticker's stored levels: `python3 investment_screener/backend/py_services/pine_level_inputs.py --draw TICKER` (it switches the chart and sets the levels and the ticker together). Without it the chart shows a red "Levels are for X, not Y" warning and no levels.

