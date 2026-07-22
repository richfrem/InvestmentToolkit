# Wave 3 — CAD Exchange-Rate Retained-JSON Rationale Bar (RESOLVED — historical record)

> **RESOLUTION (Wave 3 Task 8):** This gap is now **closed** — no retained-JSON exception is carried
> into the Task 9 exit report. The user resolved it by choosing to add **minimal schema (a single
> exchange-rate scalar)** rather than retain the `portfolio.json` dependency. A singleton
> `broker_exchange_rate` table (one row: `usd_to_cad_rate`, `synced_at`) now stores the ONE
> broker-reported FX fact, inferred at sync time from TradingView's own native
> `totalEquityCADCombined / totalEquityUSDCombined` ratio (CLAUDE.md pitfall #27 — never an external
> FX API). **No CAD-denominated totals are stored** — every CAD figure is computed as
> `usd_value × rate` at read time. Both readers are rewired onto SQLite:
> `helpers.ts::getLiveUsdCadRate()` (via `PortfolioRepository.getExchangeRate()`) and
> `portfolio_repository.py::load_portfolio_state_from_db()` (via `get_exchange_rate(conn) or 1.38`),
> each preserving a static fallback for a fresh/never-synced DB. See the **Wave 3 Addendum** in
> `ADRs/030_portfolio_totals_computed_not_stored.md` for the full design rationale (the rate is a
> *fact* and is stored; CAD totals derived from it are *aggregates* and are not — the same
> "store facts, compute aggregates" principle applied correctly). The remainder of this document is
> retained as the historical record of the investigation that led to this decision.


This is a **genuine schema gap**, not a missed rewire. It is documented here — following the exact
template and precedent of Wave 2's exit report (`docs/superpowers/status/wave2-target-portfolio-report.md`,
"Retained-JSON Rationale Bar" section) — as an open item for the Task 9 exit report. It is **not**
resolved by this Task 8-prep dispatch: eliminating it requires a new schema for CAD-denominated
broker account totals, which is a real design decision requiring explicit user approval and is out
of scope here.

## Context — how this differs from the 3 files rewired in this dispatch

The three missed consumers rewired in this dispatch (`ta_sweep_batch.py::load_portfolio()`,
`order_risk_gates.py::get_available_cash()`, `rebalancer.py::load_account_positions()` + its
staleness check) all read data that **already exists in SQLite** — holdings, USD cash (`CASH_USD`
`account_investment` rows, Wave 0 decision 5), per-account positions (`account_investment` joined to
`investment`/`investment_price`), and sync freshness (`account_investment.last_synced_at`). Those
were genuine oversights and are now fixed.

`getLiveUsdCadRate()` is different: it reads a **CAD-denominated broker equity total**
(`tvSnapshot.snapshots[].balances.totalEquityCADCombined` / `totalEquityUSDCombined`) that the
USD-only v3.2 domain model has never tracked. There is no per-currency broker-account-total column
anywhere in the schema — only per-position `quantity`/`price` (via `account_investment` /
`investment_price`). This is the same gap already documented in
`py_services/domain_model/portfolio_repository.py::load_portfolio_state_from_db()`'s hardcoded
`exchange_rate: 1.38` placeholder, and it is already acknowledged in-code in `helpers.ts`
(lines 55-65, "NOT rewired — documented stop, not an oversight").

Per CLAUDE.md pitfall #27, this rate MUST be inferred from TradingView's own native values
(`totalEquityCADCombined / totalEquityUSDCombined`), never from an external FX API — so the fix is
specifically a *new SQLite representation of those two native broker totals*, not "just call an FX
service."

## Retained-JSON Rationale Bar

### `portfolio.json` — `tvSnapshot.snapshots[].balances.totalEquityCAD/USDCombined` (CAD exchange-rate inference only)

| Field | Answer |
|---|---|
| File / pattern | `investment_screener/backend/data/portfolio.json` — specifically the `tvSnapshot.snapshots[].balances.totalEquityCADCombined` / `totalEquityUSDCombined` CAD/USD broker-equity totals, read by `investment_screener/backend/src/utils/helpers.ts::getLiveUsdCadRate()`. Only this narrow CAD-total read is retained; every other `portfolio.json` read (holdings, USD cash, per-account positions, staleness) is now SQLite-sourced. |
| Why not SQLite? | The v3.2 domain model is USD-only and has no column, anywhere, for a CAD-denominated broker account equity total. `account_investment`/`investment_price` store only per-position `quantity` and (USD) `price` — not a per-currency, per-account broker rollup total. Representing `totalEquityCADCombined`/`totalEquityUSDCombined` requires new schema; no schema changes were permitted this wave. |
| Why not event model (`intelligence_event`)? | Not an event/narrative domain — this is a live, mutable broker-reported balance pair used to derive a spot FX rate, not an append-only graded observation. |
| Why not generated from SQLite? | Nothing in SQLite can generate it — the CAD figure is a native broker value that has never been persisted relationally. A generated file would have no source of truth to generate from (the same reason `load_portfolio_state_from_db()` falls back to the `1.38` literal). |
| Category | genuine schema gap — pending a design decision, not a config file or a separate approved ledger. |
| Who writes it? | The TradingView CDP portfolio-sync path (`fetch_broker_data.py --snapshot` / the Express sync-tv apply route) writes the full `tvSnapshot` block into `portfolio.json`, including the CAD/USD balance totals. |
| Who reads it? | `helpers.ts::getLiveUsdCadRate()` (the only real reader of the CAD-total specifically). Its callers `routes/portfolio.ts` and `routes/stock.ts` consume the *derived rate*; their own `totalUSD` reads were already rewired onto SQLite. `portfolio_repository.py::load_portfolio_state_from_db()` does NOT read it — it uses a `1.38` placeholder and is the Python-side face of the same gap. |
| What breaks if removed? | The dashboard's live USD→CAD exchange rate silently falls back to the static `JAN1_USD_CAD_RATE` constant (or the `EXCHANGE_RATE_API_KEY` endpoint), losing the CLAUDE.md pitfall #27-mandated "infer from TradingView's own native values" behavior — a real accuracy regression for any CAD-denominated display. |
| User-approved exception? | **RESOLVED — no exception needed (Wave 3 Task 8).** The user resolved this by choosing to add minimal schema (a single `broker_exchange_rate` scalar row, inferred from TV's native CAD/USD ratio), NOT to retain the JSON dependency and NOT to store CAD-denominated totals. Both readers are rewired onto SQLite. See the Wave 3 Addendum in `ADRs/030_portfolio_totals_computed_not_stored.md`. |
| Future migration trigger | Add a schema representation of the native broker CAD/USD equity totals (e.g. an `account_balance_snapshot` row carrying `total_equity_cad` / `total_equity_usd` per account, or a portfolio-wide broker-totals row), populated by the same sync path that writes `tvSnapshot`. Then rewire both `getLiveUsdCadRate()` (TS) and `load_portfolio_state_from_db()`'s `exchange_rate` field (Python) to infer the rate as `total_cad / total_usd` from SQLite — resolving both faces of this single gap together. |

## Confirmation: the two py_services rewires do NOT touch this CAD gap

Both `order_risk_gates.py::get_available_cash()` and `rebalancer.py::load_account_positions()` /
`_check_no_trade_conditions()` were checked (grep for `CAD` / `totalEquity` / `exchangeRate` in both
files: zero matches). Their `portfolio.json` reads were exclusively **USD cash**, **per-account
positions**, and **sync-timestamp staleness** — all fully derivable from existing SQLite tables and
all now rewired. Neither file ever read the CAD-total data. The CAD-total gap is isolated to
`getLiveUsdCadRate()` (TS) and the mirrored `exchange_rate` placeholder in
`load_portfolio_state_from_db()` (Python).
