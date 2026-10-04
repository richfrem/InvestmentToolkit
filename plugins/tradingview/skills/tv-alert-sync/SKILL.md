---
name: tv-alert-sync
plugin: tradingview
description: Creates TradingView price alerts at DCF bear/base/bull scenario targets for portfolio holdings. Trigger on /tv-alert-sync or 'sync tradingview alerts'.
allowed-tools: Bash, Read, Write
---

# TradingView Alert Sync

Creates TradingView price alerts at DCF bear/base/bull scenario targets for portfolio holdings.

## Contents

- [Constraints](#constraints)
- [Quick start](#quick-start)
- [Workflow](#workflow)
- [Verification](#verification)

## Constraints

- Port 9222 liveness: TradingView Desktop must be running with `--remote-debugging-port=9222`.
- Deduplication: Check active alerts before creating new ones to prevent duplicate triggers.
- Scenario limits: Only create alerts for validated DCF targets (Bear, Base, Bull) from `domain_model.sqlite`.

## Quick start

```bash
python3 plugins/tradingview/scripts/tv_create_alerts.py --all
```

## Workflow

1. Verify CDP connection with `tv_health_check.py`.
2. Read active alerts using `tv_list_alerts.py` to identify existing alert coverage.
3. Query scenario targets from `domain_model.sqlite`.
4. Create missing crossing alerts via CDP for target ticker(s).
5. Report created alerts and confirmation summary.

## Verification

- Verify new alerts appear in `tv_list_alerts.py` output.
- Validate routing cases against `evals/evals.json`.
