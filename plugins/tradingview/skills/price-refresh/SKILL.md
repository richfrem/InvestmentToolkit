---
name: tv_price_refresh
plugin: tradingview
description: >
  Pulls real-time prices for all portfolio positions. Uses TradingView Desktop
  if running (port 9222), falls back to yfinance automatically per ticker.
  Trigger on /tv-price-refresh, "refresh prices", or "get live prices".
allowed-tools: Bash, Read
---

# TradingView Price Refresh Skill

## What This Skill Does

1. **Checks** TradingView Desktop status (non-blocking — uses fallback if unavailable)
2. **Loads** all tickers from `portfolio.json` and `target-portfolio.json`
3. **Fetches** real-time quotes for all tickers in parallel (ThreadPoolExecutor)
4. **Prints** a price table with live data, 1d change%, and source indicator
5. **Summarises** how many quotes came from TradingView vs. yfinance fallback

---

## Phase 1 — Health Check

```bash
python3 plugins/tradingview/scripts/tv_health_check.py --json
```

If TradingView is not running, **do not stop** — proceed with yfinance fallback.
Note at the top of output: `[yfinance mode — TradingView not connected]`

---

## Phase 2 — Load Tickers

Load tickers from both sources and deduplicate:

```bash
# Read portfolio.json for actual holdings
cat investment_screener/backend/data/portfolio.json

# Read target-portfolio.json for watch-list / INITIATE targets
cat investment_screener/backend/data/theses/target-portfolio.json
```

Combine symbols from both files into a deduplicated list.
Exclude `USD_CASH` (not a tradeable symbol).

---

## Phase 3 — Fetch Quotes

```bash
python3 plugins/tradingview/scripts/tv_batch_quotes.py '["CRWV","NVDA","INTC",...]'
```

---

## Phase 4 — Display Results

Format and print a price table:

```
╔══════════════════════════════════════════════════════════════════════╗
║              LIVE PRICE REFRESH  [2026-05-07 14:32 ET]              ║
╚══════════════════════════════════════════════════════════════════════╝
[Source: TradingView real-time | yfinance fallback]

Ticker       Price        1d Change%    Source
----------   ---------    ----------    ----------
CRWV         $115.26      -6.07%        TradingView
NVDA         $497.32      +1.23%        TradingView
INTC         $22.15       -0.45%        yfinance
AAPL         $189.50      +0.12%        TradingView
...

Summary: 35 tickers | 33 real-time (TradingView) | 2 yfinance fallback | 0 errors
```

Highlight large moves (>5% either direction) with a marker.

---

## Error Handling

| Situation | Response |
|-----------|----------|
| TradingView not running | Note in header, use yfinance for all |
| yfinance fails for one ticker | Mark as "ERROR" in table, continue |
| portfolio.json missing | Report error, try target-portfolio.json only |
| Empty ticker list | Print message and exit cleanly |

---

## Hard Rules

1. **Never fail entirely** if TradingView is down — yfinance fallback must always work
2. **Always show the source** for each price so the user knows what's real-time vs. delayed
3. **Never modify** any portfolio files — this is a read-only operation
