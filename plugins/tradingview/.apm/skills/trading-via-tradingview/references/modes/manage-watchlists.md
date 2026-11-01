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

## Watchlist Browsing & Chart Price Levels

When clicking through tickers in the TradingView watchlist, the chart indicator (`AI TA Levels`) retains the price levels of whichever stock was drawn last, displaying a red warning on any different ticker.
To synchronize price levels automatically:
- **Live auto-follower**: Run `python3 plugins/tradingview/.apm/skills/operating-tradingview-charts/scripts/batch_update_price_levels.py --follow` in the background. It detects symbol clicks via CDP and updates chart levels in real time.
- **Batch recalculation**: Run `python3 plugins/tradingview/.apm/skills/operating-tradingview-charts/scripts/batch_update_price_levels.py --recalculate` to batch derive and write fresh DCF/TA price levels for all watchlist names in `domain_model.sqlite`.
- For full details, see the [`batch-price-levels` mode in `operating-tradingview-charts`](../../../operating-tradingview-charts/references/modes/batch-price-levels.md).
