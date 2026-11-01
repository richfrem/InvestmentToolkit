# Mode: batch-price-levels (`/tv-batch-levels`)

Batch recalculates, persists, and synchronizes structured price levels across all watchlist and portfolio investments in TradingView. Trigger on /tv-batch-levels, "batch update price levels", "update every chart", or "sync watchlist price levels".
Allowed tools: Bash, Read, Write.

Batch recalculates, persists, and synchronizes structured price levels across all watchlist and portfolio investments in TradingView.


## Architecture & Context

TradingView Desktop operates with a **single active chart canvas per tab**. The custom `AI TA Levels` Pine Script indicator runs on that single canvas, storing its drawn price levels as chart study inputs tagged with `levels_for = {TICKER}`.

- When you click a ticker in your watchlist, TradingView switches the symbol on the chart canvas, but the indicator's inputs still belong to the previous ticker.
- If the ticker tag does not match the active chart symbol, the indicator intentionally displays a red guard:
  `⚠ Levels are for {PREV}, not {NEW}. Redraw: update_price_levels.py --ticker {NEW} --write --draw`
- Running a batch script that loops through 100 tickers leaves only the *last* ticker on the canvas. Clicking any earlier stock re-triggers the warning.
- To resolve this permanently when browsing watchlists, run the **live symbol follower** (`--follow`), which listens to symbol changes via CDP port 9222 and dynamically redraws levels in under 1 second.

## Constraints

- Port 9222 liveness: TradingView Desktop must be connected on port 9222.
- Source of truth: All DCF scenarios, targets, and chart support/resistance levels are persisted in `domain_model.sqlite`.
- Non-destructive: Does not overwrite user indicator settings or layout templates.

## Quick start

```bash
# 1. Batch recalculate & persist fresh price levels in SQLite for all followed names:
python3 plugins/tradingview/.apm/skills/operating-tradingview-charts/scripts/batch_update_price_levels.py --recalculate

# 2. Run the live symbol follower (auto-syncs chart levels on watchlist clicks):
python3 plugins/tradingview/.apm/skills/operating-tradingview-charts/scripts/batch_update_price_levels.py --follow

# 3. Sequentially sweep and draw every watchlist chart in TradingView Desktop:
python3 plugins/tradingview/.apm/skills/operating-tradingview-charts/scripts/batch_update_price_levels.py --sweep
```

## Workflow

1. **Batch Calculation**: Run `--recalculate` to batch derive combined levels (DCF fair value + chart support/resistance shelves) and write them into `domain_model.sqlite`.
2. **Interactive Watchlist Browsing**: Leave `--follow` running in a terminal session. As you click through your TradingView watchlist (`TV-Full Watchlist`), the follower detects each symbol change and updates the chart inputs in real time without warnings.
3. **Automated Sweep & Verification**: Run `--sweep` to have TradingView Desktop step through every symbol in the watchlist, draw its levels, and confirm CDP sets each study input cleanly.

## Verification

- Confirm terminal outputs `✓ {TICKER}: levels set on 'AI TA Levels v6'` without errors.
- Confirm active TradingView chart displays matching Buy, Trim, Stop, and Fair Value levels for the active symbol.
