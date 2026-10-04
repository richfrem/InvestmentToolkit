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
- Active chart isolation: TV CDP quotes require active chart symbol matching; batch prices must use yfinance or sequential TV switches.
- Database update: Writes live prices to `domain_model.sqlite` `investment_price` table.

## Quick start

```bash
python3 plugins/tradingview/scripts/tv_price_refresh.py
```

## Workflow

1. Enumerate held tickers from `domain_model.sqlite`.
2. Check if TradingView Desktop CDP is reachable.
3. Fetch real-time quotes via CDP or yfinance fallback.
4. Write updated prices and timestamps to SQLite.
5. Output price summary and delta table in chat.

## Verification

- Confirm prices updated in SQLite `investment_price` table.
- Validate routing cases against `evals/evals.json`.
