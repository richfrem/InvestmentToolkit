# TradingView Plugin — Implementation Summary

**Status:** Implemented and verified — 2026-05-08  
**Plugin location:** `plugins/tradingview/`  
**Implemented by:** Sub-agent (Claude Sonnet), reviewed and patched by primary session

---

## What Was Built

A new fourth plugin (`tradingview`) added alongside the existing three (`portfolio-advisor`, `stock-valuation`, `toolkit-manager`). It bridges InvestmentToolkit's AI agents and Python backend to TradingView Desktop's real-time market data — without installing a separate MCP server process.

### Files Created (14 new + 1 modified)

```
plugins/tradingview/
├── plugin.json                       ← skill registry, commands, external dependencies
├── .claude-plugin/plugin.json        ← marketplace metadata
├── commands/
│   ├── tv-alert-sync.md              ← /tv-alert-sync slash command
│   ├── tv-price-refresh.md           ← /tv-price-refresh slash command
│   └── tv-snapshot.md                ← /tv-snapshot slash command
├── skills/
│   ├── alert-sync/SKILL.md           ← create DCF target alerts in TradingView
│   ├── price-refresh/SKILL.md        ← pull real-time prices for all positions
│   └── chart-snapshot/SKILL.md       ← capture TradingView chart screenshot
└── scripts/
    ├── tv_client.py                  ← core: subprocess caller, health check, fallback
    ├── tv_quote.py                   ← single-ticker real-time quote
    ├── tv_batch_quotes.py            ← parallel batch quotes (ThreadPoolExecutor)
    ├── tv_create_alerts.py           ← create price alerts from projection JSONs
    ├── tv_health_check.py            ← verify TradingView + CLI are ready
    └── tv_launch.py                  ← launch TradingView with CDP flag

investment_screener/backend/py_services/fetch_portfolio_heatmap.py   ← MODIFIED
```

---

## How It Works

Python scripts call an **owned Node.js CDP client** at `plugins/tradingview/node/cli.js` via `subprocess`. No MCP server process is needed — Python calls the CLI directly and parses the JSON output. The Node.js code is fully owned in this repo; there is no runtime dependency on `temp/tradingview-mcp`.

```
Python script
  └─ subprocess.run(["node", "plugins/tradingview/node/cli.js", "quote", "CRWV"])
        └─ Owned Node.js CLI  →  Chrome DevTools Protocol (localhost:9222)
              └─ TradingView Desktop  →  real-time data from your Premium subscription
```

**All scripts have automatic yfinance fallback.** If TradingView Desktop is not running, every call silently uses yfinance instead. Nothing breaks.

---

## Dependencies

### Required (already present)
| Dependency | Version | Where |
|------------|---------|-------|
| Node.js | 18+ | System — `node --version` to confirm |
| `plugins/tradingview/node/node_modules` | installed | Run `cd plugins/tradingview/node && npm install` once |
| `yfinance` | any | Already in `requirements.txt` — used as fallback |
| Python 3.10+ | — | Required for `list[str]` type hints in scripts |

### Required for TradingView path
| Dependency | Notes |
|------------|-------|
| TradingView Desktop | Installed at `/Applications/TradingView.app` ✅ confirmed |
| TradingView Premium subscription | Required for real-time data (not delayed) |
| CDP port 9222 free | Must not be occupied by Chrome when TV is running |

### No new Python packages needed
The plugin reuses `yfinance` (already installed) and `subprocess`/`socket`/`json` from the standard library.

---

## Assumptions

1. **TradingView Desktop is not always running.** The plugin degrades gracefully — every script falls back to yfinance per-ticker if TradingView is unavailable. The heatmap, screener, and portfolio table continue working exactly as before.

2. **yfinance is NOT being replaced.** Yahoo Finance remains the source for:
   - Historical OHLCV data (used in DCF scenario modelling)
   - Financial ratios, revenue, margins, EPS (fundamental data for `/evaluate-stock`)
   - 1-week, 1-month, YTD, 1-year price changes in the screener heatmap
   - The `history_store.py` price history cache
   - All data when TradingView Desktop is closed

3. **TradingView replaces yfinance only for current price and 1d change%.** That's the specific improvement: the "right now" price and today's % move become real-time (from your Premium subscription) instead of 15–20 min delayed.

4. **The Node.js CLI must have been npm-installed at least once.** `tv_health_check.py` will flag this if missing.

5. **Port 9222 conflict:** If Google Chrome or a browser-based IDE extension is already using port 9222, the health check will report the port as "reachable" but CLI calls will time out. Close Chrome DevTools remote debugging or use a different CDP port before launching TradingView. (Current setup: VS Code/IDE uses 9222 — close TradingView will use it cleanly when Chrome DevTools is not active.)

6. **macOS only for TradingView Desktop.** The launch script (`tv_launch.py`) targets macOS. The data scripts work cross-platform as long as TradingView is somehow running with CDP enabled.

---

## Yahoo Finance vs. TradingView — Division of Responsibility

| Data Type | Source | Notes |
|-----------|--------|-------|
| **Current price** (live) | TradingView → yfinance fallback | TradingView = real-time (Premium); yfinance = 15-20 min delayed |
| **1d change %** | TradingView → yfinance fallback | Same split as above |
| **Historical OHLCV** (1w, 1m, YTD, 1y bars) | yfinance only | Not changing — TV not used here |
| **Financials** (revenue, margins, EPS, ratios) | yfinance only | DCF valuation data — not changing |
| **DCF fair value** | Calculated from yfinance fundamentals | Not changing |
| **Book value / cost basis** | Questrade API | Not changing |
| **Portfolio positions** | Questrade API | Not changing |
| **News / analyst estimates** | Grok / manual | Not changing |

**Summary:** yfinance does everything it did before. TradingView adds a real-time price layer on top for the "current price" column specifically.

---

## What This Improves

### Before (yfinance only)
- Current prices in screener/portfolio table: **15–20 min delayed**
- DCF price snapshot at eval time: **up to 20 min stale**
- No TradingView alerts from thesis data
- No way to pull prices from within a Claude Code session

### After (TradingView plugin)
- Current prices when TV is running: **real-time** (your Premium subscription)
- DCF price snapshot at eval time: **real-time**
- **`/tv-alert-sync`**: creates TradingView price alerts at your DCF bear/base/bull targets for every holding with a projection — you get notified when a position hits a thesis price level
- **`/tv-price-refresh`**: instant price table for all ~35 positions, showing source (TradingView vs yfinance) per ticker
- **`/tv-snapshot TICKER`**: chart screenshot saved to `PortfolioAnalysis/screenshots/` — useful for embedding in sweep reports

---

## How to Run

### One-time setup
```bash
# 1. Install Node.js dependencies for the owned CLI
cd /Users/richardfremmerlid/Projects/InvestmentToolkit/plugins/tradingview/node
npm install
cd ../../..   # back to repo root

# 2. Verify setup
python3 plugins/tradingview/scripts/tv_health_check.py
```

### Launch TradingView with CDP enabled (do this before using the plugin)
```bash
python3 plugins/tradingview/scripts/tv_launch.py
# Or manually:
open /Applications/TradingView.app --args --remote-debugging-port=9222
```

### Verify connection
```bash
python3 plugins/tradingview/scripts/tv_health_check.py
# Expected output:
#   [PASS]  Port 9222 reachable
#   [PASS]  CLI status command
#   [PASS]  npm node_modules
#   All checks passed — TradingView is connected and CLI is ready.
```

### Use the skills (in Claude Code session)

```
/tv-price-refresh          → live prices for all portfolio positions
/tv-alert-sync             → create DCF target alerts for all holdings with projections
/tv-alert-sync CRWV        → single-ticker alert sync
/tv-snapshot CRWV          → capture CRWV chart screenshot
```

### Use the scripts directly (from repo root)
```bash
# Single ticker quote
python3 plugins/tradingview/scripts/tv_quote.py CRWV

# Batch quotes for a list of tickers
python3 plugins/tradingview/scripts/tv_batch_quotes.py '["CRWV","NVDA","INTC","AMD"]'

# Create DCF alerts for all holdings
python3 plugins/tradingview/scripts/tv_create_alerts.py

# Create DCF alerts for one ticker
python3 plugins/tradingview/scripts/tv_create_alerts.py --ticker CRWV

# Dry run (shows what would be created, doesn't call TV)
python3 plugins/tradingview/scripts/tv_create_alerts.py --dry-run

# Health check (machine-readable)
python3 plugins/tradingview/scripts/tv_health_check.py --json
```

### Heatmap integration (automatic — no action needed)
The `fetch_portfolio_heatmap.py` modification is passive. When the backend calls the heatmap script and TradingView is running, current prices are automatically upgraded to real-time for that request. When TradingView is closed, it's pure yfinance as before. No backend restart needed.

---

## Known Limitations

| Limitation | Impact | Workaround |
|------------|--------|-----------|
| TradingView Desktop must be open | Plugin only active when TV is running | yfinance fallback is automatic |
| Port 9222 conflict with Chrome DevTools | Health check passes but CLI times out | Don't have Chrome DevTools remote debugging active on same port |
| Undocumented TV internal API | Any TV Desktop update could break CLI | yfinance fallback always available; pin `tradingview-mcp` version |
| 500-bar max per OHLCV request | Fine for portfolio use; not for deep history | yfinance handles historical data needs |
| macOS only (launch script) | Windows/Linux need manual launch | Data scripts work cross-platform if TV is somehow running |
| Real-time data subject to TradingView ToS | Personal/research use only | Not redistributing data; personal tool only |

---

## Recommended Workflow Integration

After each **`/x-news-sweep`** session:
```
1. /x-news-sweep          → gated recommendations + apply changes
2. /evaluate-stock TICKER  → (if any ticker needs fresh DCF)
3. /tv-alert-sync          → sync updated fair value targets as TV price alerts
```

At the start of each **trading day**:
```
1. python3 plugins/tradingview/scripts/tv_launch.py   → ensure TV is running with CDP
2. /tv-price-refresh                                   → check where all positions are
3. /x-news-sweep                                       → daily news sweep
```

---

*Summary by Claude Sonnet 4.6 — 2026-05-08*  
*Plugin implemented by sub-agent, reviewed and patched by primary session*
