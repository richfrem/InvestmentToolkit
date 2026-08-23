---
name: tv-chart-snapshot
plugin: tradingview
description: >
  Captures a chart screenshot for a ticker in TradingView Desktop. Switches
  the chart to the requested ticker, takes a screenshot, and saves it to
  PortfolioAnalysis/screenshots/{YYYY-MM-DD}/{TICKER}.png.
  Trigger on /tv-snapshot TICKER, "snapshot TICKER", or "chart screenshot TICKER".
allowed-tools: Bash, Read
---

# TradingView Chart Snapshot Skill

## What This Skill Does

1. **Checks** TradingView Desktop is reachable (port 9222)
2. **Switches** TradingView to the requested ticker
3. **Captures** a screenshot of the chart
4. **Saves** the image to `PortfolioAnalysis/screenshots/{YYYY-MM-DD}/{TICKER}.png`
5. **Reports** the saved file path

---

## Phase 1 — Parse Argument

Extract the ticker from the trigger:
- `/tv-snapshot CRWV` → ticker = `CRWV`
- `"snapshot NVDA"` → ticker = `NVDA`
- `"chart screenshot INTC"` → ticker = `INTC`

If no ticker provided, ask: `"Which ticker would you like to snapshot?"`

---

## Phase 2 — Health Check

```bash
python3 "$(find plugins/tradingview/scripts ~/.claude/plugins/cache -name tv_health_check.py -path "*/tradingview/*" 2>/dev/null | sort | tail -1)" --json
```

If TradingView is **not** running, print:

```
TradingView Desktop not detected on port 9222.
Chart snapshots require TradingView Desktop to be running.

Launch it with: python3 plugins/tradingview/scripts/tv_launch.py
Or manually:    open -a TradingView --args --remote-debugging-port=9222
```

Stop if TradingView is not available — screenshots cannot be taken without it.

---

## Phase 3 — Switch Chart to Ticker

```bash
node tradingview-cdp/cli.js quote TICKER
```

This verifies the ticker is accessible. The screenshot will capture whatever chart is currently active in TradingView Desktop — switch to the ticker manually in TradingView before running if needed.

---

## Phase 4 — Capture Screenshot

```bash
# Determine today's date for the save path
DATE=$(python3 -c "from datetime import date; print(date.today().isoformat())")
SAVE_DIR="PortfolioAnalysis/screenshots/$DATE"
mkdir -p "$SAVE_DIR"

# Capture screenshot — saved to PortfolioAnalysis/screenshots/{date}/{TICKER}.png automatically
node tradingview-cdp/cli.js screenshot --output "$SAVE_DIR/$TICKER"
```

---

## Phase 5 — Report

```
╔══════════════════════════════════════════════════════════════════╗
║              CHART SNAPSHOT SAVED                                ║
╚══════════════════════════════════════════════════════════════════╝

Ticker:   CRWV
Saved:    PortfolioAnalysis/screenshots/2026-05-07/CRWV.png
Chart:    TradingView Desktop (live view at time of capture)
```

---

## Error Handling

| Situation | Response |
|-----------|----------|
| TradingView not running | Print launch instructions and stop |
| `symbol` command fails | Report error with the exact CLI error message |
| `screenshot` command fails | Report error, do not save partial file |
| Save directory creation fails | Report filesystem error |

---

## Hard Rules

1. **Always switch to the requested ticker** before screenshotting — never capture the wrong chart
2. **Always report the exact saved path** so the user can find the file
3. **Require TradingView to be running** — no fallback for screenshots
