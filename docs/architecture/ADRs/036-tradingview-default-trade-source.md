# ADR-036: TradingView is the default source for executed trades

Date: 2026-10-08
Status: Proposed

## Problem

ADR-035 imported executed trades through Questrade only. That contradicts the
broker policy (TradingView is the baseline every user has; Questrade is an
optional augment), left users without Questrade with an empty trade log, and
gave skills no way to know whether Questrade may be used: they inferred it from
whether a session happened to be connected.

## Decision

1. **Read filled orders from TradingView.** `tradingview-cdp/core/broker_data.js`
   gains `getOrderHistory()` (active account) and `getOrderHistoryAllAccounts()`,
   which read the broker panel's "Order history" > "Filled" table and restore the
   selected account. Cell parsing is a pure module (`core/order_history.js`) that
   maps by header name. `plugins/tradingview/scripts/tv_trades_import.py` maps the
   orders to the shared trade contract and imports them.
2. **One import core.** `py_services/trade_log_import.py` owns validation, stable
   ids, de-duplication and writes for every source; the Questrade and TradingView
   scripts only fetch and map. A fill is the same trade when it shares a stable id
   or broker order id; otherwise when account, symbol, side, shares and price
   match within five days; and several orders at one price that add up to one
   saved trade are that trade. TradingView's order id equals Questrade's, and is
   stored in `tv_order_id`.
3. **An explicit setting.** `QUESTRADE_ENABLED` in `.env` (default false) says
   whether Questrade may be used. `py_services/broker_sources.py` is the only
   reader; the backend exposes it at `GET /api/trading/broker-sources`.
   TradingView stays the default even when Questrade is enabled, and the owner is
   asked which source to use for a refresh. Onboarding asks the question once and
   `questrade-setup` records the answer.
4. **Page and skills.** The Trade Log page's "Sync from TV" button now also
   imports executed trades (only on click: it switches through every account in
   TradingView, which is too intrusive for the silent reconcile on page load).
   The Questrade reminder chip appears only when Questrade is enabled.
   `tv-portfolio-sync` imports trades with every sync; `daily-loop`,
   `weekly-review` and `update-stock-analysis` refresh through it by default.

## Consequences

- TradingView's order history reaches back about 30 days and its "Update Time"
  is when the order last changed. A limit order's stored date can be its
  placement day, and only market orders get a time. Questrade's activity feed has
  the true trade date and longer history, which is why it remains worth offering.
- TradingView reports orders, Questrade reports posted trades; the multi-order
  rule above is what keeps the two from double-counting.
- The setting is read on each request, so changing `.env` needs no restart.
