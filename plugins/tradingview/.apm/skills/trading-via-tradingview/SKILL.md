---
name: trading-via-tradingview
plugin: tradingview
description: Places and manages orders and syncs account data through the broker connected in TradingView Desktop, always with the owner approving. Covers placing, modifying, cancelling and listing orders, syncing holdings, cash and executed trades into domain_model.sqlite, refreshing prices from TradingView quotes only, and syncing watchlists. Trigger on /place-order, /tv-modify-order, /tv-cancel-order, /tv-get-orders, /tv-portfolio-sync, /tv-price-refresh, /tv-manage-watchlists, "buy [N] shares of [TICKER]", "cancel order [ID]", "modify order [UUID]", "show open orders", "sync portfolio from TV", "refresh prices" or "sync watchlists".
allowed-tools: Bash, Read, Write
---

# Trading via TradingView

The broker-facing half of the TradingView integration: orders, portfolio and trade sync, prices and watchlists. TradingView is the default broker and price source for the toolkit (Questrade is optional). Chart control and alerts are in `operating-tradingview-charts`.

## Contents

- [Quick start](#quick-start) · [Workflow](#workflow) · [Constraints](#constraints) · [Modes](#modes) · [Scripts](#scripts) · [Verification](#verification) · [References](#references)

## Quick start

Check the connection, then read the mode:

```bash
python3 investment_screener/backend/py_services/tv_health_check.py
```

Paths starting with `scripts/` are relative to this skill's folder; the shared broker engine (`place_order.py`, `fetch_broker_data.py`, `tv_client.py`) is in `investment_screener/backend/py_services/`.

## Workflow

1. Match the request to a mode and read its mode file.
2. Run the health check; stop and say so if TradingView or the broker panel is not connected.
3. For anything that changes an order or the database, show the owner a preview (order card, holdings diff, price table) and wait for an explicit go-ahead.
4. Verify as the mode describes, and run the closing refresh where the mode asks for it.

## Constraints

- **No autonomous execution** (Rule #17): every order needs explicit human confirmation of ticker, side, quantity and price; orders are Day orders unless the owner changes them in the UI; PSU-U.TO is sold in the same account to fund purchases.
- **Account isolation**: confirm the target account (TFSA, RRSP, Cash) before filling any order form.
- **Single source of truth**: holdings, balances and trades are written only to `domain_model.sqlite`; if TradingView returns zero positions, stop and tell the owner rather than overwriting valid data.
- **Prices come from TradingView quotes only**; a ticker TradingView cannot quote is reported and keeps its previous price. No other price source is substituted.
- **Never write prices or holdings with ad hoc SQL.**

## Modes

| Mode | Trigger | What it does |
|---|---|---|
| [place-order](references/modes/place-order.md) | `/place-order` | Stage, preview and (after CONFIRM) submit a buy or sell order |
| [modify-order](references/modes/modify-order.md) | `/tv-modify-order` | Change the limit price or quantity of a Working order |
| [cancel-order](references/modes/cancel-order.md) | `/tv-cancel-order` | Cancel a Working or Inactive order and mark it in the Trade Log |
| [get-orders](references/modes/get-orders.md) | `/tv-get-orders` | List Working and Inactive orders |
| [portfolio-sync](references/modes/portfolio-sync.md) | `/tv-portfolio-sync` | Sync holdings, cash and executed trades from the broker panel into SQLite |
| [price-refresh](references/modes/price-refresh.md) | `/tv-price-refresh` | Refresh stored prices from TradingView quotes |
| [manage-watchlists](references/modes/manage-watchlists.md) | `/tv-manage-watchlists` | Sync holdings and researched tickers to TradingView watchlists |

## Scripts

- `scripts/`: `tv_get_orders`, `tv_modify_order`, `tv_cancel_order`, `tv_trades_import`, `tv_batch_quotes`, `tv_price_refresh`, `watchlist_manager`.
- Shared engine (`py_services/`): `place_order.py` (also `--modify`, `--cancel`, `--list`), `fetch_broker_data.py`, `tv_account_coverage.py`, `tv_client.py`, `tv_health_check.py`.
- Tests: `tests/` (pass the path explicitly; pytest skips dot-directories).

## Verification

- Orders: the order appears (or disappears, or changes) in the broker panel's Working orders table.
- Sync: `python3 investment_screener/backend/py_services/verify_portfolio_invariants.py` exits 0.
- Prices: every refreshed symbol's `investment_price.fetched_at` is today and `stale` is empty.
- Routing cases for every mode are in `evals/evals.json`.

## References

- [Reading and driving TradingView lists reliably](references/tradingview-ui-reading.md): visible-rows-only reads, hashed selectors, one copy per list, symbol spelling, validation order. Read before changing code that reads a list or positions table.
- The `operating-tradingview-charts` skill: connection setup, indicators, alerts.
- The `analyzing-charts` skill: technical-analysis sweeps and the red-team reviewer.
