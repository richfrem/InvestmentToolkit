---
name: tv-portfolio-sync
plugin: tradingview
description: Syncs broker holdings and cash from TradingView broker panel into SQLite domain model via CDP. Trigger on /tv-portfolio-sync or 'sync portfolio from TV'.
allowed-tools: Bash, Read, Write
---

# TradingView Portfolio Sync

Syncs broker holdings and cash from TradingView broker panel into SQLite domain model via CDP.

## Contents

- [Constraints](#constraints)
- [Quick start](#quick-start)
- [Workflow](#workflow)
- [Verification](#verification)

## Constraints

- Single source of truth: Holdings and balances must be written to `domain_model.sqlite`; never write to retired target-portfolio.json.
- Zero positions guard: If TV returns 0 positions (broker disconnected), halt and alert user; never overwrite valid data with empty arrays.
- HITL confirmation: Present full holdings diff (new, closed, qty changes) before committing changes.
- Cash invariant: Portfolio totals must strictly include uninvested cash.

## Quick start

```bash
python3 plugins/tradingview/scripts/fetch_broker_data.py --snapshot
```

## Workflow

1. Run pre-flight health check on port 9222.
2. Fetch TV broker snapshot across all accounts (TFSA, RRSP, Cash):
   `python3 plugins/tradingview/scripts/fetch_broker_data.py --snapshot`
3. Compute diff vs existing SQLite database holdings.
4. Present diff table to user and await explicit confirmation.
5. Commit snapshot to `domain_model.sqlite`.
6. Run invariant audit: `verify_portfolio_invariants.py`.

## Verification

- Confirm `verify_portfolio_invariants.py` returns exit code 0.
- Validate routing cases against `evals/evals.json`.
