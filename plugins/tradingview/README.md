# TradingView Plugin

Real-time price integration for InvestmentToolkit via TradingView Desktop and Chrome DevTools Protocol (CDP).

---

## Requirements

### TradingView Desktop (required)

You must have **TradingView Desktop** installed on your machine.

- Download: https://www.tradingview.com/desktop/
- macOS install path: `/Applications/TradingView.app`
- The app must be launched with the `--remote-debugging-port=9222` flag for this plugin to connect. The startup script (`run_investment_toolkit.py`) handles this automatically.

### TradingView Premium subscription (required for real-time data)

This plugin reads price data directly from your TradingView session. **A Premium or higher subscription is required** to get real-time (non-delayed) quotes.

- Free accounts: data is delayed 15–20 minutes — same as yfinance, no improvement
- Essential / Plus / Premium+: real-time data — this is the improvement the plugin provides
- See plans: https://www.tradingview.com/pricing/

Without a Premium subscription the plugin still works (it reads from your active chart), but the prices won't be any fresher than the yfinance fallback.

### Node.js 18+ (required)

The owned CDP client (`node/cli.js`) runs on Node.js.

```bash
node --version   # must be 18+
```

### One-time setup

```bash
cd plugins/tradingview/node
npm install
cd ../../..

# Verify
python3 plugins/tradingview/scripts/tv_health_check.py
```

---

## How It Works

```
Python script
  └─ subprocess → plugins/tradingview/node/cli.js  (owned, no external MCP server)
        └─ Chrome DevTools Protocol (localhost:9222)
              └─ TradingView Desktop
                    └─ Your Premium real-time feed
```

TradingView Desktop is launched at startup with `--remote-debugging-port=9222`. The Python scripts connect to it via the owned Node.js CLI and read the active chart's price and change%.

**yfinance is not replaced** — it remains the source for:
- Historical OHLCV (1w, 1m, YTD, 1y price changes)
- Financial fundamentals (revenue, margins, EPS, ratios) used in DCF
- All data when TradingView Desktop is closed

TradingView adds a real-time price layer **only for current price and 1d change%**.

**Automatic fallback:** if TradingView is not running or not reachable, every script silently falls back to yfinance. The screener, heatmap, and portfolio table continue working exactly as before.

---

## Skills

| Skill | Command | Purpose |
|-------|---------|---------|
| Price Refresh | `/tv-price-refresh` | Live prices for all portfolio positions (TV → yfinance fallback per ticker) |
| Alert Sync | `/tv-alert-sync` | Create TradingView price alerts at DCF bear/base/bull targets |
| Alert Sync (single) | `/tv-alert-sync CRWV` | Alert sync for one ticker |
| Chart Snapshot | `/tv-snapshot CRWV` | Capture chart screenshot → `PortfolioAnalysis/screenshots/` |
| TA Snapshot | `/tv-ta CRWV` | Screenshot + visual technical analysis — trend, S/R levels, indicator readings, buy/sell zones |

### `/tv-ta` — Technical Analysis Snapshot

Captures a live chart screenshot and runs a full visual TA analysis using Claude's vision:

```
/tv-ta CRWV        # TA on current CRWV chart
/tv-ta NVDA 1W     # Weekly chart TA (note the timeframe for context)
```

**What you get:**
- Trend direction (higher highs/lows or range-bound)
- Key support and resistance levels read directly from the chart
- Indicator readings for whatever you have configured in TradingView (RSI, MACD, MAs, volume, Bollinger Bands, etc.)
- Buy zone with entry range, invalidation (stop) level, and risk/reward ratio
- Sell/trim zone at next logical resistance
- DCF cross-reference: if a projection exists for the ticker, the TA levels are mapped against bear/base/bull scenarios

**Setup tip:** Configure your TradingView chart with the indicators you want before running `/tv-ta`. The skill reads whatever is on screen — add RSI, MACD, volume, moving averages in TradingView Desktop first for richer analysis.

---

## Scripts (direct use)

All scripts run from the repo root:

```bash
# Single ticker quote (reads active chart; label shows requested symbol)
python3 plugins/tradingview/scripts/tv_quote.py CRWV

# Batch quotes
python3 plugins/tradingview/scripts/tv_batch_quotes.py '["CRWV","NVDA","INTC","AMD"]'

# Create DCF alerts for all holdings
python3 plugins/tradingview/scripts/tv_create_alerts.py

# Create DCF alerts for one ticker
python3 plugins/tradingview/scripts/tv_create_alerts.py --ticker CRWV

# Dry run (shows what would be created)
python3 plugins/tradingview/scripts/tv_create_alerts.py --dry-run

# Health check
python3 plugins/tradingview/scripts/tv_health_check.py
python3 plugins/tradingview/scripts/tv_health_check.py --json

# Launch TradingView manually (also done automatically at startup)
python3 plugins/tradingview/scripts/tv_launch.py
```

---

## Port 9222 Conflict

Port 9222 is the standard Chrome DevTools remote debugging port. If Google Chrome or a browser-based tool is already using it, the health check will report port 9222 as "reachable" but CLI calls will fail or time out because the target is Chrome, not TradingView.

**Fix:** close any app that uses remote Chrome DevTools on port 9222 before launching TradingView, or ensure they don't start together.

---

## Node.js CDP Client

The plugin owns its Node.js CDP code at `plugins/tradingview/node/`. There is no runtime dependency on `temp/tradingview-mcp` or any external MCP server.

```
plugins/tradingview/node/
├── cli.js           ← entry point (status, quote, alert, screenshot)
├── router.js        ← command dispatcher
├── connection.js    ← CDP connect / evaluate helpers
├── package.json     ← single dep: chrome-remote-interface
└── core/
    ├── data.js      ← getQuote, getOhlcv, getStudyValues
    ├── alerts.js    ← create, list, delete
    ├── health.js    ← healthCheck
    └── capture.js   ← captureScreenshot → PortfolioAnalysis/screenshots/
```

---

## Recommended Workflow

**Daily:**
```
1. run_investment_toolkit.py   → launches screener + TradingView Desktop automatically
2. /tv-price-refresh           → check where all positions are right now
3. /x-news-sweep               → daily news sweep
```

**After a stock evaluation:**
```
1. /evaluate-stock CRWV        → fresh DCF
2. /tv-alert-sync CRWV         → set alerts at new bear/base/bull targets
```
