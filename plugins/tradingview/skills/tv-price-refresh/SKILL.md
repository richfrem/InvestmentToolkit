---
name: tv-price-refresh
plugin: tradingview
description: Pulls real-time prices for portfolio positions from TradingView Desktop only; a ticker TradingView cannot quote is reported, never priced from another source. Trigger on /tv-price-refresh or 'refresh prices'.
allowed-tools: Bash, Read, Write
---

# TradingView Price Refresh

Pulls real-time prices for portfolio positions from TradingView Desktop. Prices never come from another source.

## Contents

- [Constraints](#constraints)
- [Quick start](#quick-start)
- [Workflow](#workflow)
- [Verification](#verification)

## Constraints

- Price source: TradingView Desktop CDP real-time quotes only (port 9222). yfinance is never used for a price.
- When TradingView is not connected, stop and say so: `TradingView not connected, prices not refreshed`. Do not substitute delayed quotes and do not touch stored prices.
- Show each quote's source (always TradingView) with a count of quoted and unquoted tickers. Mark a ticker TradingView cannot quote `ERROR` and keep its previous stored price (listed as stale); never fabricate a price.
- Positions, share counts and book cost are never changed here; route those requests to `/tv-portfolio-sync`.
- Quotes are read from the "TV-Full Watchlist" watchlist; a held or watchlisted ticker that is not on it is reported as unquoted. Add it to that watchlist (`/tv-manage-watchlists`) rather than falling back.
- Database update: `scripts/tv_price_refresh.py` (plugins/tradingview/scripts) is the only price writer. It reads held and watchlisted symbols from `domain_model.sqlite`, resolves prices from TradingView quotes only and writes through the investment repositories; it needs no backend. `tv_batch_quotes.py` prints quotes and writes nothing. Never write prices with ad-hoc SQL.

## Quick start

```bash
python3 plugins/tradingview/scripts/tv_price_refresh.py
python3 plugins/tradingview/skills/tv-price-refresh/scripts/tv_batch_quotes.py '["NVDA","AAPL"]'
```
The first command saves prices and also refreshes the USD->CAD rate (`--skip-fx` to skip). Exit 0: every symbol written; 1: some symbols had no usable quote and keep their old price (listed under `stale`); 2: database not found.

## Workflow

1. Enumerate held tickers from `domain_model.sqlite`.
2. Check if TradingView Desktop CDP is reachable (`scripts/tv_health_check.py`).
3. Fetch real-time quotes with `scripts/tv_batch_quotes.py --tradingview-only` for the on-screen table.
4. Persist prices with `tv_price_refresh.py`; the table in step 3 is not what gets saved. Report any `failed`/`stale` symbols.
5. Output price summary and delta table in chat, with the source of each quote.

## Verification

- Confirm every refreshed symbol's `investment_price.fetched_at` is today (`stale` is empty) and `verify_portfolio_invariants.py` reports `CASH_INVARIANT` passed.
- Validate routing cases against `evals/evals.json`.
