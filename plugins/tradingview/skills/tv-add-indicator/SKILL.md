---
name: tv-add-indicator
plugin: tradingview
description: Add a built-in TradingView indicator or personal Pine Script to the active chart via CDP. Trigger on /tv-add-indicator or 'add indicator [NAME]'.
allowed-tools: Bash, Read, Write
---

# TradingView Add Indicator

Add a built-in TradingView indicator or personal Pine Script to the active chart via CDP.

## Contents

- [Constraints](#constraints)
- [Quick start](#quick-start)
- [Workflow](#workflow)
- [Verification](#verification)

## Constraints

- Active chart requirement: TradingView Desktop must be running with remote debugging on port 9222.
- Avoid duplicates: Check loaded indicators with tv-manage-indicators before adding a new indicator.
- Dialog overlay safety: Ensure Pine Editor is closed before searching indicators dialog to avoid click interception.

## Quick start

```bash
node tradingview-cdp/cli.js chart addIndicator "Relative Strength Index"
```

## Workflow

1. Confirm Port 9222 Reachability: Run `python3 plugins/tradingview/scripts/tv_health_check.py`.
2. Open Indicators Dialog: Dispatch input event to open the indicator search modal via CDP.
3. Search & Select: Type indicator name (e.g. 'Relative Strength Index', 'Volume Profile', or personal Pine name) and select matching row.
4. Close Dialog: Dismiss the modal once indicator is rendered on chart.

## Verification

- Confirm indicator appears in the chart legend via `node tradingview-cdp/cli.js chart read`.
- Validate routing cases against `evals/evals.json`.
