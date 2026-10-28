---
description: Invariant rules for single-source-of-truth calculations, UI position tables, and SQLite ledger synchronization.
globs: ["investment_screener/**/*", "plugins/**/*"]
---

# Architecture Invariants: Calculations, Tables & Ledgers

## 1. One Implementation Per Concept
- MUST consolidate calculations, aggregations, formatters, period changes, and UI helpers into canonical shared modules.
- Python logic belongs in `plugins/<plugin>/scripts/` symlinked into `py_services/`.
- TypeScript logic belongs in `frontend/src/utils/` or `backend/src/services/`.
- NEVER maintain duplicate parallel implementations of the same business formula.

## 2. One Table System, One SQLite Source
- All ticker screens render through `PositionsTable` (`investment_screener/frontend/src/components/positions/`) fed by `GET /api/screener/all-holdings`.
- NEVER hand-write ticker tables or freeze static markdown tables in thesis documents.

## 3. Thesis Pages Currency via Ledger
- Every news sweep MUST record findings in `intelligence.sqlite` via `record_news_sweep.py`.
- Thesis "Current developments" notes update strictly in `domain_model.sqlite` (`thesis_document_currency`) via `thesis_currency.py`.
- Volatile prices and trade weights belong in live queries, NEVER hardcoded in static markdown prose.

## 4. Cash Invariant for Portfolio Totals
- Portfolio total USD MUST strictly compute: `sum(Held Equities Market Value) + sum(Account Cash USD)`.
- NEVER calculate portfolio value from stock market value alone without uninvested cash.

## 5. One Price Refresh
- Exactly one function writes `investment_price`: `tv_price_refresh.py` in the `trading-via-tradingview` skill. The web route, the Refresh button, `/daily` and the weekly review call it; no other price writer may exist (a test MUST fail if one appears; not yet written).
- Order: (1) validate every account's held positions and share counts against the broker; (2) validate the full watchlist against SQLite (every ticker present, none extra); (3) read prices from the watchlist; (4) report every ticker that has no quote by name and exit non-zero.
- The page MUST show unpriced or stale tickers and the oldest price time, never only the position-sync time.

## 6. One Copy Per TradingView List
- Lists are `TV-Full Watchlist` (everything in SQLite that is held or watchlisted) and `TV-Portfolio` (held positions). One copy each.
- Sync updates the existing list. Creating a list whose name already exists is PROHIBITED; when more than one copy of a name exists, stop and report it. Deleting extra copies is a user action.
- Readers MUST scroll the list (TradingView renders only visible rows) and check the row count; an unscrolled read is NEVER evidence that a ticker is missing.

## 7. Ticker Aliases
- `PSU.U`, `PSU.U.TO`, `PSU-U` and `PSU-U.TO` are one fund. Normalize only through `ticker_aliases.normalize_ticker`; a second alias map (such as a local `normalize_symbol`) is PROHIBITED.
- Compare TradingView rows and SQLite symbols in canonical form, and use the TradingView spelling only when talking to TradingView.

