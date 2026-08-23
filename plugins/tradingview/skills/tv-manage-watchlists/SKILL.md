---
name: tv-manage-watchlists
plugin: tradingview
description: >
  Synchronizes portfolio holdings and researched tickers from projections / watchlist.json
  to TradingView watchlists.
allowed-tools: Bash, Read
---

# TradingView Watchlist Manager Skill

## ⚠️ Pre-flight Check
Before running this skill, verify the TradingView CDP connection is active and debug port 9222 is open:
```bash
python3 "$(find plugins/tradingview/scripts ~/.claude/plugins/cache -name tv_health_check.py -path "*/tradingview/*" 2>/dev/null | sort | tail -1)"
```
*If this check fails, run `/setup-tradingview` first. If using a non-standard install path, set `export TV_CDP_DIR=/path/to/tradingview-cdp` before executing.*

## What This Skill Does

1. **Loads** active holdings from `investment_screener/backend/data/portfolio.json`
2. **Loads** researched watchlists from `investment_screener/backend/data/watchlist.json` (falling back to scanning the projections directory if not found)
3. **Translates** them into two standard watchlists in TradingView (BOATS/overnight watchlist
   removed — TradingView charts now natively support 24h quoting):
   - `TV-Full Watchlist` — All researched tickers (includes Canadian)
   - `TV-Portfolio` — Active portfolio holdings
4. **Maintains** alignment by adding missing tickers and pruning retired tickers dynamically.

---

## Dry Run Verification

Check what additions/removals are planned without applying changes:

```bash
python3 plugins/tradingview/scripts/watchlist_manager.py sync --dry-run
```

---

## Live Synchronisation

Perform the actual update to TradingView Desktop watchlists:

```bash
python3 plugins/tradingview/scripts/watchlist_manager.py sync
```
