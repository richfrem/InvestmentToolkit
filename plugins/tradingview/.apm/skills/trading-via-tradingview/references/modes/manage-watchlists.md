# Mode: manage-watchlists (`/tv-manage-watchlists`)

Synchronizes portfolio holdings and researched tickers to TradingView watchlists. Trigger on /tv-manage-watchlists or 'sync watchlists'.
Allowed tools: Bash, Read, Write.

Synchronizes portfolio holdings and researched tickers to TradingView watchlists.


## Constraints

- Database authority: Source tickers are read directly from `domain_model.sqlite`.
- Dry run first: Always support `--dry-run` to preview watchlist additions.
- Section separation: Group by Strategy Pillar (Power, Compute, Data Infra, Software, Cash).

## Quick start

```bash
python3 scripts/watchlist_manager.py sync
```

## Workflow

1. Query portfolio and watchlisted tickers from `domain_model.sqlite`.
2. Preview changes with `python3 scripts/watchlist_manager.py sync --dry-run`.
3. Execute synchronization: `python3 scripts/watchlist_manager.py sync`.
4. Report added and removed tickers per watchlist section.

## Verification

- Verify tickers appear in TradingView Desktop watchlist panel.
- Validate routing cases against `evals/evals.json`.
