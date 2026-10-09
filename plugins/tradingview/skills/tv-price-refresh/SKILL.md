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
- Database update: only `POST /api/portfolio/refresh-prices` writes `investment_price` (it fetches its own Yahoo quotes and refreshes the USD->CAD rate). `tv_batch_quotes.py` prints quotes and writes nothing. Never write prices with ad-hoc SQL.

## Quick start

```bash
curl -s -X POST -H "Authorization: Bearer $(cat .runtime/api-token)" http://localhost:3001/api/portfolio/refresh-prices
python3 plugins/tradingview/skills/tv-price-refresh/scripts/tv_batch_quotes.py '["NVDA","AAPL"]'
```

## Workflow

1. Enumerate held tickers from `domain_model.sqlite`.
2. Check if TradingView Desktop CDP is reachable (`scripts/tv_health_check.py`).
3. Fetch real-time quotes with `scripts/tv_batch_quotes.py` (TradingView first, yfinance fallback) for the on-screen table.
4. Persist prices by calling the refresh route in Quick start; the table in step 3 is not what gets saved.
5. Output price summary and delta table in chat, with the source of each quote.

## Verification

- Confirm the newest `investment_price.fetched_at` is today and `verify_portfolio_invariants.py` reports `CASH_INVARIANT` passed.
- Validate routing cases against `evals/evals.json`.
