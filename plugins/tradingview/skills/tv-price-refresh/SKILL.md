---
name: tv-price-refresh
plugin: tradingview
description: Pulls real-time prices for portfolio positions using TradingView Desktop with yfinance fallback. Trigger on /tv-price-refresh or 'refresh prices'.
allowed-tools: Bash, Read, Write
---

# TradingView Price Refresh

Pulls real-time prices for portfolio positions using TradingView Desktop with yfinance fallback.

## Contents

- [Constraints](#constraints)
- [Quick start](#quick-start)
- [Workflow](#workflow)
- [Verification](#verification)

## Constraints

- Price hierarchy: Uses TradingView Desktop CDP live quotes when port 9222 is open, falls back to yfinance per ticker.
- Never fail entirely when TradingView is down: continue on yfinance and put `[yfinance mode — TradingView not connected]` at the top of the output.
- Show each quote's source (TradingView or yfinance) with a summary count of real-time, fallback and error quotes. Mark a ticker that cannot be quoted `ERROR`; never fabricate a price.
- Positions, share counts and book cost are never changed here; route those requests to `/tv-portfolio-sync`.
- Active chart isolation: TV CDP quotes require active chart symbol matching; batch prices must use yfinance or sequential TV switches.
- Database update: `scripts/tv_price_refresh.py` (plugins/tradingview/scripts) is the only price writer. It reads held and watchlisted symbols from `domain_model.sqlite`, resolves prices with the canonical resolver (TradingView first, yfinance fallback) and writes through the investment repositories; it needs no backend. `tv_batch_quotes.py` prints quotes and writes nothing. Never write prices with ad-hoc SQL.

## Quick start

```bash
python3 plugins/tradingview/scripts/tv_price_refresh.py
python3 plugins/tradingview/skills/tv-price-refresh/scripts/tv_batch_quotes.py '["NVDA","AAPL"]'
```
The first command saves prices and also refreshes the USD->CAD rate (`--skip-fx` to skip). Exit 0: every symbol written; 1: some symbols had no usable quote and keep their old price (listed under `stale`); 2: database not found.

## Workflow

1. Enumerate held tickers from `domain_model.sqlite`.
2. Check if TradingView Desktop CDP is reachable (`scripts/tv_health_check.py`).
3. Fetch real-time quotes with `scripts/tv_batch_quotes.py` (TradingView first, yfinance fallback) for the on-screen table.
4. Persist prices with `tv_price_refresh.py`; the table in step 3 is not what gets saved. Report any `failed`/`stale` symbols.
5. Output price summary and delta table in chat, with the source of each quote.

## Verification

- Confirm every refreshed symbol's `investment_price.fetched_at` is today (`stale` is empty) and `verify_portfolio_invariants.py` reports `CASH_INVARIANT` passed.
- Validate routing cases against `evals/evals.json`.
