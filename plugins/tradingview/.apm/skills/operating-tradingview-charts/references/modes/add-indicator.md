# Mode: add-indicator (`/tv-add-indicator`)

Add a built-in TradingView indicator or personal Pine Script to the active chart via CDP. Trigger on /tv-add-indicator or 'add indicator [NAME]'.
Allowed tools: Bash, Read, Write.

Add a built-in TradingView indicator or personal Pine Script to the active chart via CDP.


## Constraints

- Active chart requirement: TradingView Desktop must be running with remote debugging on port 9222.
- Avoid duplicates: Check loaded indicators with [manage-indicators mode](manage-indicators.md) before adding a new indicator.
- Dialog overlay safety: Ensure Pine Editor is closed before searching indicators dialog to avoid click interception.

## Quick start

```bash
node tradingview-cdp/cli.js chart addIndicator "Relative Strength Index"
```

## Workflow

1. Confirm Port 9222 Reachability: Run `python3 investment_screener/backend/py_services/tv_health_check.py`.
2. Open Indicators Dialog: Dispatch input event to open the indicator search modal via CDP.
3. Search & Select: Type indicator name (e.g. 'Relative Strength Index', 'Volume Profile', or personal Pine name) and select matching row.
4. Close Dialog: Dismiss the modal once indicator is rendered on chart.

## Verification

- Confirm indicator appears in the chart legend via `node tradingview-cdp/cli.js chart read`.
- Validate routing cases against `evals/evals.json`.
