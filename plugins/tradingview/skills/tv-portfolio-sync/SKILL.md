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
- Trades with every sync: import executed trades in the same run so the Trade Log and the recommendations' recent-trade context match the new positions. This is the default trade source for every user.

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
6. Import executed trades from TradingView's order history (all accounts), previewing first:
   `python3 plugins/tradingview/scripts/tv_trades_import.py --dry-run`, then without `--dry-run`.
   Trades already recorded (including from Questrade) are skipped; report any warnings or rejections as printed.
7. Run invariant audit: `verify_portfolio_invariants.py`.
8. Closing refresh: run `python3 plugins/portfolio-advisor/scripts/refresh_all.py --publish` so the Portfolio Advisor and Daily Brief pages reflect this session.

## Verification

- Confirm `verify_portfolio_invariants.py` returns exit code 0.
- Validate routing cases against `evals/evals.json`.
