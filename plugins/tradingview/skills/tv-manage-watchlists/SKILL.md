---
name: tv-manage-watchlists
plugin: tradingview
description: Synchronizes portfolio holdings and researched tickers to TradingView watchlists. Trigger on /tv-manage-watchlists or 'sync watchlists'.
allowed-tools: Bash, Read, Write
---

# TradingView Manage Watchlists

Synchronizes portfolio holdings and researched tickers to TradingView watchlists.

## Contents

- [Constraints](#constraints)
- [Quick start](#quick-start)
- [Workflow](#workflow)
- [Verification](#verification)

## Constraints

- Database authority: Source tickers are read directly from `domain_model.sqlite`.
- Dry run first: Always support `--dry-run` to preview watchlist additions.
- Section separation: Group by Strategy Pillar (Power, Compute, Data Infra, Software, Cash).

## Quick start

```bash
python3 plugins/tradingview/scripts/manage_watchlists.py --sync
```

## Workflow

1. Query portfolio and watchlisted tickers from `domain_model.sqlite`.
2. Preview changes with `manage_watchlists.py --dry-run`.
3. Execute synchronization: `manage_watchlists.py --sync`.
4. Report added and removed tickers per watchlist section.

## Verification

- Verify tickers appear in TradingView Desktop watchlist panel.
- Validate routing cases against `evals/evals.json`.
