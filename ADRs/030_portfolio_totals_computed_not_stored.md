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
