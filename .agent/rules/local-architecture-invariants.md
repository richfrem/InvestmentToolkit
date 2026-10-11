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
