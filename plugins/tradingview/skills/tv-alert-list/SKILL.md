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
- Single source of alerts: Persists the alerts to the `alert` table in `domain_model.sqlite` (the offline copy).
- Read-only query: Does not delete, modify, or trigger alerts.

## Quick start

```bash
python3 plugins/tradingview/scripts/tv_list_alerts.py
```

## Workflow

1. Verify CDP connection on port 9222.
2. Execute listing script: `python3 plugins/tradingview/scripts/tv_list_alerts.py`.
3. Persist the alerts to the `alert` table in `domain_model.sqlite`.
4. Render formatted Markdown table with columns: `Ticker`, `Price`, `Condition`, `Label/Message`.

## Verification

- Confirm the alerts are upserted into the `alert` table of `domain_model.sqlite`.
- Validate routing cases against `evals/evals.json`.
