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

## Price Source Priority (enforced in tv_batch_quotes.py)

| Priority | Source | When used |
|----------|--------|-----------|
| **1 (primary)** | TradingView watchlist via CDP | TradingView running (port 9222) |
| **2 (fallback)** | yfinance `fast_info.last_price` | TV unreachable, or ticker not in watchlist |

`tv_batch_quotes.py` reads the live `TV-Full Watchlist` via CDP — a single watchlist for all hours,
but each row is session-aware: outside regular hours, TradingView freezes its regular "last" price
and surfaces the extended/overnight move in a separate cell (labeled "Pre-market", "Post-market", or
"Overnight via BOATS"). `_select_effective_price()` picks the current tradable price per a 3-tier
priority — regular hours -> extended hours -> overnight/BOATS — rather than reporting the frozen
regular-session price after close.
yfinance is **only** used when TradingView is not running.

## What This Skill Does

1. **Checks** TradingView Desktop status (non-blocking — uses fallback if unavailable)
2. **Loads** all tickers from `portfolio.json` and `target-portfolio.json`
3. **Fetches** live quotes — TV watchlist (`TV-Full Watchlist`) first, yfinance only for misses
4. **Prints** a price table with live data, 1d change%, and source indicator
5. **Summarises** how many quotes came from TradingView vs. yfinance fallback

---

## Phase 1 — Health Check

```bash
python3 "$(find plugins/tradingview/scripts ~/.claude/plugins/cache -name tv_health_check.py -path "*/tradingview/*" 2>/dev/null | sort | tail -1)" --json
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

---

## Related: Backend `/refresh-prices` Endpoint (routes/portfolio.ts)

The Express `POST /refresh-prices` endpoint (separate code path from this skill's CLI
tools) calls `py_services/fetch_portfolio_heatmap.py`, not `tv_batch_quotes.py`. Two rules
apply there — do not regress either when touching that endpoint or its Python script:

1. **Always use the most current available price, regular or extended hours.**
   `fetch_portfolio_heatmap.py` already implements this: TradingView watchlist-first via CDP
   (`TV-Full Watchlist`, session-aware via `tv_batch_quotes._select_effective_price()` —
   regular hours -> extended hours -> overnight/BOATS), falling back to yfinance
   `fast_info.last_price` only when TV is unreachable. Never swap this for a plain
   `regularMarketPrice`/last-close lookup — that would silently drop extended-hours coverage.
2. **A price refresh must also refresh the stored USD/CAD exchange rate at the same time.**
   Wave 3 Task 8: `POST /refresh-prices` now calls
   `fetch_broker_data.py --refresh-exchange-rate` (a lightweight balances-only CDP fetch via
   `refresh_exchange_rate_only()`) in the same `Promise.all` as the price fetch, so the stored
   rate in `broker_exchange_rate` never goes stale relative to freshly-refreshed USD prices.
   This is separate from a full `--snapshot` broker sync — do not remove it under the
   assumption that only a full sync should touch the exchange rate.
