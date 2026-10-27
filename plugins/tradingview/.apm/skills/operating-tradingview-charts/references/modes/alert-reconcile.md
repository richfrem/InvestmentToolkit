# Mode: alert-reconcile (`/tv-alert-reconcile`)

Reconciles active TradingView price alerts against SQLite target levels and flags missing or drifted alerts. Trigger on /tv-alert-reconcile or 'reconcile alerts'.
Allowed tools: Bash, Read, Write.

Reconciles active TradingView price alerts against SQLite target levels and flags missing or drifted alerts.


## Constraints

- Drift tolerance: Flags price target discrepancies greater than 1.0% between SQLite price levels and TradingView active alerts.
- Database authority: Domain levels in `domain_model.sqlite` are authoritative over alert text.
- Read-only audit: Compares levels without mutating alerts unless user triggers alert sync.

## Quick start

```bash
python3 scripts/tv_create_alerts.py --reconcile
```

## Workflow

1. Scrape live alert snapshot via `tv_list_alerts.py`.
2. Query target price levels (Target Entry, Fair Value, Breaker) from `domain_model.sqlite`.
3. Compare alert price vs database target per ticker.
4. Present reconciliation table highlighting matched, drifted, and missing alerts.

## Verification

- Confirm reconciliation report displays drift metrics.
- Validate routing cases against `evals/evals.json`.
