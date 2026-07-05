# ADR: Valuation Committee (Phase 2a)

**Status:** Accepted
**Date:** 2026-07-04
**Context:** Fable5 Elevation Guide Phase 2a — see `docs/superpowers/specs/2026-07-04-valuation-committee-design.md`

## Decision

`aiThesis.action = "ACCUMULATE"` now requires at least 2 of 3 independent
valuation lenses to agree:

1. **DCF upside** — `analyticsLog.dcf.upsidePct > 15%` (the existing BUY threshold).
2. **Comps upside** — the peer-median EV/Sales-implied price range's midpoint
   exceeds the current price (`analyticsLog.comps`).
3. **Implied growth below base case** — the market's reverse-DCF-implied
   5-year revenue CAGR is *less* than our own base-case growth assumption
   (`analyticsLog.reverseDcf.impliedGrowthVsBaseCase < 0`) — a margin-of-safety signal.

This is enforced in `validate_projection.py`'s `check_accumulate_gate()`,
which blocks (validation error, non-persistable) any projection where fewer
than 2 of 3 lenses agree for an ACCUMULATE action. All other actions
(`INITIATE`, `MAINTAIN`, `TRIM`, `EXIT`, `WATCHLIST`, `BUY`, `HOLD`, `SELL`)
are unaffected by this gate.

Additionally, whenever the three lenses' implied prices disagree by more
than 25% (`analyticsLog` DCF fair value vs. comps midpoint), a warning is
printed requiring the disagreement to be documented in `rationale` — this
is a warning, not a blocking error, since disagreement itself is valuable
information the agent must surface, not resolve by picking a side.

## Why 4 lenses instead of 1

A single DCF-weighted fair value is a single point of failure: if its
growth/margin/exit-PE assumptions are wrong, nothing catches it, because
nothing else is being asked. Four independent lenses — forward DCF,
reverse-DCF (what the market is pricing in), Monte Carlo (a probability
distribution, not one number), and peer comps (an entirely different
methodology) — catch a wrong DCF assumption when at least one of the other
three doesn't corroborate it. Requiring 2-of-3 agreement (not 3-of-3, and
not just "average them") reflects that any single lens can be wrong for
idiosyncratic reasons (bad peer set, thin regression data for beta, a
temporarily depressed comps sector) without invalidating the whole signal —
while still blocking the case where only one lens supports the recommended
action.

## Scope boundaries taken in this pass

- **EV/EBITDA comps deferred.** No EBITDA source exists anywhere in the
  current data layer (`market_data.get_fundamentals()` has no clean raw
  EBITDA field, and `fetch_financials.py`'s `expert_metrics.rule_of_40.ebitda_margin`
  is a derived ratio, not a raw figure suitable for EV/EBITDA). `comps_valuation.py`
  computes **EV/Sales only** this pass.
- **`totalDebt`/`cashAndEquivalents`/`interestExpense` are yfinance-only.**
  No EDGAR XBRL tag mapping exists for these yet in `edgar_facts.py` —
  mirrors the existing `operatingIncome`-is-EDGAR-only precedent, inverted.
- **Peer lists are seeded only for the ~10 actively-held tickers** with
  confident sector-peer knowledge as of this pass (see the design spec §8
  and the implementation plan's Task 8). New tickers get a `peers` list
  the next time they go through `/evaluate-stock`; an unseeded ticker
  correctly returns `{"status": "insufficient_peer_data"}`, not a fabricated range.
- **Capital-structure weighting for WACC** uses market cap (equity) and
  `totalDebt` (debt) only — no preferred stock or minority-interest
  adjustments in this pass.

## Consequences

- Existing `projections/*.json` entries with `aiThesis.action = ACCUMULATE`
  predate this gate and have no `analyticsLog.{dcf,comps,reverseDcf}` data —
  they are **not retroactively invalidated**, but the migration-audit test
  (`test_accumulate_gate_migration.py`) documents which ones would currently
  fail the gate, as a re-review list for the agent.
- `dcf_scenarios.py`'s discount rate is no longer always 10% — any tooling
  or documentation that assumed a flat rate must account for `--wacc-file`
  now being the normal path (an explicit `--discount-rate` still overrides
  it for reproducing old runs).
