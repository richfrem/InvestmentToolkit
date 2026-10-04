---
name: tv-alert-list
plugin: tradingview
description: Fetches, analyzes, and lists active TradingView price alerts, saving the snapshot to the backend data folder for offline caching. Trigger on /tv-alert-list or 'list tradingview alerts'.
allowed-tools: Bash, Read, Write
---

# TradingView Alert List

Fetches, analyzes, and lists active TradingView price alerts, saving the snapshot to the backend data folder for offline caching.

## Contents

- [Constraints](#constraints)
- [Quick start](#quick-start)
- [Workflow](#workflow)
- [Verification](#verification)

## Constraints

- CDP liveness: Requires TradingView Desktop running on port 9222.
- Single source of alerts: Persists offline snapshot to `investment_screener/backend/data/tradingview_alerts_actual.json`.
- Read-only query: Does not delete, modify, or trigger alerts.

## Quick start

```bash
python3 plugins/tradingview/scripts/tv_list_alerts.py
```

## Workflow

1. Verify CDP connection on port 9222.
2. Execute listing script: `python3 plugins/tradingview/scripts/tv_list_alerts.py`.
3. Cache snapshot to `investment_screener/backend/data/tradingview_alerts_actual.json`.
4. Render formatted Markdown table with columns: `Ticker`, `Price`, `Condition`, `Label/Message`.

## Verification

- Confirm JSON snapshot is written to `investment_screener/backend/data/tradingview_alerts_actual.json`.
- Validate routing cases against `evals/evals.json`.
