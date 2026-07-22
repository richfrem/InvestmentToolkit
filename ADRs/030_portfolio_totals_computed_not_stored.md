# ADR-030: Portfolio Totals Are Computed From Holdings, Not Stored as Broker Snapshots

## Status
Accepted

## Context

Wave 3 of the Domain Data Model v3.2 migration (`docs/superpowers/plans/2026-07-20-domain-data-model-v3-wave3-implementation-plan.md`)
migrates `portfolio.json` (gitignored, real broker/account holdings for TFSA + RRSP) into the
SQLite domain model (`account`, `account_investment`, `investment_price`).

Task 0's pre-implementation verification sweep found the real `portfolio.json`'s per-account data
lives in `tvSnapshot.snapshots[].positions[]` (quantity, avgFillPrice, keyed by real `accountId`/
`accountType`), not in the flat, cross-account-aggregated `holdings[]` array the plan's first draft
assumed. It also found that the file's top-level `totals.totalUSD` (30,373.98 in the real data
sampled) does not exactly equal the sum of the three real accounts' own `tvSnapshot.snapshots[].balances.totalEquityUSDCombined`
figures (9,249.57 + 76.01 + 19,771.48 = 29,097.06) — a real ~$1,277 gap, not rounding noise.

This discrepancy triggered a design question: should the migration store the broker-reported
totals (`totals.totalUSD`, and/or each account's `totalEquityUSDCombined`) verbatim in new SQLite
tables, treating them as authoritative external facts that must never be recomputed — or should
the domain model compute these totals live from `account_investment`/`investment_price`, the same
way any normal relational schema derives an aggregate from its detail rows?

The first draft of this decision (informed by a misreading of this project's own standing rule —
see `investment_screener/backend/data/theses` project memory: *"NEVER compute portfolio totals
from shares×price... User has hit this bug many times"*) proposed two new tables
(`account_broker_snapshot`, `portfolio_broker_snapshot`) to store the broker's numbers verbatim,
reasoning that if a computed total can diverge from the broker's own reported total by a material
amount, the broker's number must be the one source of truth and the divergence itself is evidence
the two are independent facts.

The user corrected this reasoning directly: the original rule was never "do not compute totals
from holdings." CLAUDE.md rule 27 already states the opposite explicitly: *"Compute totals using
the formula: cash value all accounts + sum(portfolio holding price × shares). Never convert USD to
CAD via external API calls; always infer the exchange rate directly from TradingView's native
values."* The actual intent of the "never compute" memory entry was narrower: never invent your
own FX conversion rate, and treat a *large* variance between the computed total and the broker's
reported total as a signal of a real sync/data problem (stale price, a missed position, a broken
refresh) — not as license to silently store two permanently-diverging numbers and stop comparing
them. A small variance (cents to a few dollars, from price movement or refresh lag) is expected and
not a bug; a large variance (on the order of hundreds to thousands of dollars) is a bug to
investigate, not a new "authoritative" figure to enshrine in its own table.

## Decision

**Portfolio and account totals are computed on read from `account_investment` + `investment_price`,
not stored as separate broker-snapshot tables.** No new schema is added for this purpose.

Specifically:

1. **Holdings** (quantity, average cost) come from `tvSnapshot.snapshots[].positions[]` per real
   account, written into the existing `account_investment` table — one row per (account, holding).
2. **Cash** is a real `investment` row (`asset_class='CASH'`, e.g. `CASH_USD`/`CASH_CAD`), held via
   `account_investment` like any other position — per Wave 0's already-approved resolved design
   decision 5 (`docs/superpowers/specs/2026-07-19-domain-data-model-v3-implementation-design.md` §3).
   Per-account cash balances (`balances.cashUSD`/`cashCAD` in the real sync payload) populate these
   rows on sync; no separate cash-balance table is added.
3. **Portfolio total** is computed live as `SUM(quantity × price)` across every `account_investment`
   row (holdings and cash) joined to `investment_price`, exactly matching CLAUDE.md rule 27's
   existing formula. This computation lives in `portfolio_repository.py`
   (`investment_screener/backend/py_services/domain_model/`), the same module `portfolio_io.py`'s
   `load_portfolio_state()` delegates to after Wave 3's cutover.
4. **Reconciliation, not storage, is the safeguard against drift.** The computed total is compared
   against the broker's own reported total (`totals.totalUSD` from the live sync payload) at sync
   time — this is the existing responsibility of `verify_portfolio_total.py` (already a confirmed
   real consumer of this domain, per Wave 3's inventory). A small variance is expected and logged,
   not flagged. A large variance (the exact threshold is this script's own responsibility to define,
   not re-litigated by this ADR) is a real signal — of a stale price, a missed sync, or a genuine
   data bug — and must be surfaced, never silently absorbed by trusting whichever number happens to
   be more "authoritative."

## Consequences

- No new tables are added to the v3.2 schema for this domain. Wave 3's Tasks 2–3 (previously drafted
  against an invented `"account"` field on a flat `holdings[]` array, per Task 0's finding) are
  rewritten to read the real `tvSnapshot.snapshots[].positions[]`/`balances` shape and to compute
  totals rather than cache them.
- `verify_portfolio_total.py`'s existing reconciliation role becomes the load-bearing check against
  sync/data drift, rather than a second table's mere existence implying correctness. Its variance
  threshold and alerting behavior are unchanged by this ADR — this decision only settles where the
  total comes from, not how large a variance is tolerable.
- The general principle this ADR establishes for future waves and domains: **a large, real,
  reproducible discrepancy between a computed value and an external system's reported value is
  evidence of a bug to fix, not evidence that the computed value should be abandoned in favor of
  storing the external system's number as a second, permanently-parallel source of truth.** Storing
  an unreconciled snapshot instead of fixing the underlying variance would be exactly the kind of
  silent, unexamined hybrid state ADR-029 and the Domain Data Model v3.2 spec's Anti-Regression
  Lessons already prohibit — this ADR extends that same discipline to the "which number do we trust"
  question specifically, so it does not need to be re-derived by a later wave that hits the same
  broker-vs-computed variance question in a different domain.
- CLAUDE.md rule 27 remains the binding formula and is not amended by this ADR — this document
  exists only to correct a specific misapplication of it that arose mid-Wave-3, and to make the
  corrected reasoning discoverable for future sessions without needing to re-read this
  conversation's history.

## Wave 3 Addendum — The USD→CAD Exchange Rate IS Stored (as a single scalar fact)

Added Wave 3 Task 8, per an explicit user design decision, to close the last CAD-related schema
gap (documented in `docs/superpowers/status/wave3-cad-exchange-rate-retained-json.md`). This is a
**narrow extension of the same "store facts, not derived aggregates" principle above, not a
contradiction of it.**

**The distinction that decides it:** the live USD→CAD exchange rate is a genuine broker-reported
*fact* — it cannot be derived from anything else the schema stores (holdings are USD-only quantities
and prices; nothing relational yields the spot FX rate). A CAD *total*, by contrast, is a derived
*aggregate*: `usd_value × rate`. The rule "store facts, compute aggregates" therefore says to store
the rate and compute the CAD totals — exactly what this addendum does.

Concretely:

1. **One scalar, stored:** a new singleton table `broker_exchange_rate` (`id` fixed at 1,
   `usd_to_cad_rate`, `synced_at`) holds exactly one row, overwritten each sync. This mirrors
   `investment_price`'s "store this one broker fact, don't invent history we don't need" shape —
   deliberately **not** a per-account or historical table.
2. **No CAD totals stored, ever:** per-currency broker equity totals
   (`totalEquityCADCombined`/`totalEquityUSDCombined`) are **not** persisted. They are consumed only
   transiently at sync time to *infer* the rate (`sum(CAD) / sum(USD)` across accounts), per
   CLAUDE.md pitfall #27's mandate that the rate come from TradingView's own native values, never an
   external FX API. Any CAD figure the app displays is computed as `usd_value × rate` at read time.
3. **Written once at sync time** by the same broker-sync path that already writes holdings/cash:
   `fetch_broker_data.py::_persist_snapshot_to_db()` (Python) and
   `BrokerSyncService.ts::persistSnapshotToDb()` (TS), each computing the rate with identical math
   and calling `upsert_exchange_rate()` / `PortfolioRepository.upsertExchangeRate()`.
4. **Read with a static fallback** by both former JSON readers, now SQLite-sourced:
   `portfolio_repository.py::load_portfolio_state_from_db()` (`get_exchange_rate(conn) or 1.38`) and
   `helpers.ts::getLiveUsdCadRate()` (via `PortfolioRepository.getExchangeRate()`), each degrading to
   its existing static fallback for a fresh/never-synced database.

This resolves both faces of the gap (TS `getLiveUsdCadRate` and Python `load_portfolio_state_from_db`
`exchange_rate`) together, and eliminates the retained-`portfolio.json` exception that would
otherwise have been carried into the Wave 3 exit report. The reconciliation discipline of the main
decision above is unaffected: totals are still computed, still reconciled against the broker's
reported total; only the FX rate — the one thing that is a fact and not an aggregate — is stored.
