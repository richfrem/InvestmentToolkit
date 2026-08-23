---
name: tv-alert-reconcile
description: "Reconciles active TradingView price alerts against SQLite target levels and flags missing or drifted alerts."
triggers:
  - "/tv-alert-reconcile"
  - "reconcile alerts"
  - "check price alerts"
---

# /tv-alert-reconcile — Reconcile Price Alerts

Compares active alerts in TradingView Desktop against the target entry, fair value, and stop-loss price levels in `domain_model.sqlite`.

## Usage
```bash
# Reconcile all tickers
python3 plugins/tradingview/scripts/tv_create_alerts.py --reconcile

# Reconcile single ticker
python3 plugins/tradingview/scripts/tv_create_alerts.py --ticker <TICKER> --reconcile
```
