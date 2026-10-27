# Mode: alert-sync (`/tv-alert-sync`)

Creates TradingView price alerts at DCF bear/base/bull scenario targets for portfolio holdings. Trigger on /tv-alert-sync or 'sync tradingview alerts'.
Allowed tools: Bash, Read, Write.

Creates TradingView price alerts at DCF bear/base/bull scenario targets for portfolio holdings.


## Constraints

- Port 9222 liveness: TradingView Desktop must be running with `--remote-debugging-port=9222`.
- Deduplication: Check active alerts before creating new ones to prevent duplicate triggers.
- Scenario limits: Only create alerts for validated DCF targets (Bear, Base, Bull) from `domain_model.sqlite`.

## Quick start

```bash
python3 scripts/tv_create_alerts.py --all
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
