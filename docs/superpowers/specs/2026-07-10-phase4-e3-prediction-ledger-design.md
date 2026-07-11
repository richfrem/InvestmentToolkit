# Phase 4, Sub-Spec 1 — E3 Prediction Ledger

**Status:** Draft, pending user review
**Phase:** Fable5 elevation guide, Phase 4 ("Track Record")
**Sub-spec order:** E3 (this doc) → B4 (earnings intelligence) → G4 (structured events) → E4 (backtest harness)

## 1. Problem

Every `/daily`, `/evaluate-stock`, and `/rebalance` run emits graded claims — an `aiThesis.action`
rating, a DCF fair value, an ACCUMULATE/TRIM order, a thesis-breaker forecast — but nothing
records whether any of them turn out to be right. The evolution log captures anecdotes and
process incidents, not calibration. Per the elevation guide, this is "the single highest-leverage
addition" in the whole document: it converts the system's track record from vibes into a
queryable, gradable history, and tells us which signal sources (DCF vs TA vs breakers) actually
deserve trust.

## 2. Scope

**In scope (this sub-spec):**
- A prediction ledger schema and two append-only JSONL stores.
- A harvester that reads already-persisted artifacts and logs new/changed claims — 4 claim
  types: `action_rating`, `dcf_fair_value`, `rebalance_order`, `breaker_forecast`.
- A grading job with one unified directional-return grading function.
- A report generator producing rolling hit rates by claim type.
- Wiring: harvester into `/daily` (new, non-blocking step), grading + report into
  `/weekly-review` (new phase).

**Out of scope (deferred to later sub-specs or follow-ups):**
- `earnings_expectation` claims — B4 (next sub-spec) adds the emitter; this sub-spec only
  reserves the enum value in the schema so B4 needs no migration.
- The backtest harness (E4) — independent, comes after G4.
- Retroactively backfilling history for claims already made before this ships. The ledger
  starts recording from whenever it's deployed; no attempt to reconstruct past claims from
  git history (unlike E4, which explicitly mines `target-portfolio.json` history — different
  problem, different data availability).
- A `Predictions.tsx` frontend page. Backend-only this pass, same posture E1 took for
  `Risk.tsx` — a real fast-follow, not a blocker.

## 3. Current-state findings that shape this design

- **`analyticsLog.dcf` is populated on only 2 of 80 current projections** (`CRSP`, `LLY`) —
  everything else predates the Phase 2a valuation-committee gate. CLAUDE.md's pitfall #6
  ("DCF signal is in `analyticsLog.valuationAction`") refers to a field that does not exist
  anywhere in the codebase — stale documentation, not fixed here (unrelated scope). The
  harvester must fall back to `aiThesis.fairValue` / `aiThesis.action` when
  `analyticsLog.dcf` is absent, or it would be a near-total no-op today.
- **`rebalance_plan.json` doesn't exist on disk until `/rebalance` is run** — the harvester
  must treat a missing file as "nothing to harvest," not an error.
- **`thesis_breaker_state.json` currently has zero holdings populated** (B5 deliberately left
  backfilling real breaker data out of scope) — the `breaker_forecast` claim type will be
  sparse for a while. This is expected, matching how B5/C2 shipped "produce the data, don't
  gate yet" and let real data accumulate over time.
- **`aiThesis.action` is read/written across 12 files** — this sub-spec only reads from
  `projections/*.json` (the persisted output), never touches any of the 12 emitting scripts.

## 4. Architecture

Two new append-only JSONL files, following the existing convention set by
`context/events.jsonl` and B5's `data/theses/breaker-overrides.jsonl`:

- **`data/predictions.jsonl`** — one record per claim, written only by `harvest_predictions.py`.
- **`data/predictions_graded.jsonl`** — one record per graded outcome, written only by
  `grade_predictions.py`, referencing a prediction's `id`.

Neither file is ever rewritten in place. Grading appends a new record rather than mutating the
claim it grades — the ledger is a pure historical log, consistent with "reproducibility over
cleverness." A prediction's graded/ungraded state is *derived* by checking whether its `id`
appears in `predictions_graded.jsonl`; there is no mutable status field on the prediction record
itself.

**Dedup without an extra state file:** `harvest_predictions.py` scans the tail of
`predictions.jsonl` for the most recent record matching `(ticker, type)` and only appends a new
record if the source artifact's current claim value differs from that last-logged value (or no
prior record exists). This makes the ledger itself the single source of truth for "have I
already logged this" — no separate `harvest_state.json` to keep in sync.

## 5. Schema

### `predictions.jsonl` record

```json
{
  "id": "CORZ:action_rating:2026-05-02",
  "date": "2026-05-02",
  "ticker": "CORZ",
  "type": "action_rating | dcf_fair_value | rebalance_order | breaker_forecast | earnings_expectation",
  "claim": { "...": "type-specific, see below" },
  "direction": "bullish | bearish",
  "horizonDays": 90,
  "basePrice": 5.32,
  "baseSpyPrice": 612.40,
  "confidence": null,
  "inputsHash": "sha256 of the source artifact's relevant fields at harvest time",
  "harvestedAt": "2026-07-10T18:00:00Z"
}
```

- `id`: `f"{ticker}:{type}:{date}"` — stable, reconstructible, used as the dedup and grading key.
  If the harvester ever logs two claims of the same type for the same ticker on the same date
  (shouldn't happen given the dedup rule, but defensively), the second is skipped with a
  logged warning rather than silently overwriting — `id` collisions are a bug signal, not a
  normal path.
- `claim`: type-specific payload, sourced from real fields (see §6) — never fabricated fields.
- `direction`: derived once at harvest time (see §7) so grading never has to re-derive intent
  from a claim payload that might change shape across claim types.
- `confidence`: reserved, `null` until a claim type actually provides one (none do yet).
- `inputsHash`: lets a future audit tell whether the underlying inputs changed between two
  claims that happen to have the same date — not used for grading logic in this sub-spec,
  just recorded for traceability.

### `predictions_graded.jsonl` record

```json
{
  "predictionId": "CORZ:action_rating:2026-05-02",
  "gradedAt": "2026-08-02",
  "tickerReturn": -0.041,
  "spyReturn": 0.012,
  "relativeReturn": -0.053,
  "verdict": "correct | incorrect | inconclusive"
}
```

## 6. Claim sources (real fields, not fabricated)

| Claim type | Source artifact | Fields read | Claim payload |
|---|---|---|---|
| `action_rating` | `projections/{TICKER}.json` `[0].aiThesis` | `action`, `analyzedAt` | `{"action": aiThesis.action}` |
| `dcf_fair_value` | same, `analyticsLog.dcf` if present else `aiThesis` | `dcf.weightedFairValue`/`dcf.upsidePct` or `fairValue` | `{"fairValue": ..., "upsidePct": ..., "source": "analyticsLog.dcf"|"aiThesis"}` |
| `rebalance_order` | `data/rebalance_plan.json` `.orders[]` | `ticker`, `action` (`buy`/`sell`), `riskGateWarnings`, `breakerWarnings` | `{"action": ..., "gateWarningsPresent": bool}` |
| `breaker_forecast` | `data/thesis_breaker_state.json` `.holdings[ticker][breakerId]` | `status`, `metric`, `threshold`, `streak` | `{"breakerId": ..., "metric": ..., "status": "TRIGGERED"}` |

Only `TRIGGERED` breaker entries are harvested — a breaker sitting at `OK` isn't a claim about
the future, it's the absence of one.

`basePrice`/`baseSpyPrice` come from `market_data.get_prices()` (Phase 1) at harvest time —
never refetched or recomputed at grading time, so a later data revision can't retroactively
change what was "claimed."

## 7. Grading semantics

Every claim type reduces to one question: **did price move consistent with the claim's
directional implication, relative to SPY, by the horizon?**

Direction is assigned once, at harvest time:

| Claim type | Bullish when | Bearish when |
|---|---|---|
| `action_rating` | `INITIATE`, `ACCUMULATE` | `TRIM`, `EXIT` |
| `dcf_fair_value` | `upsidePct > 0` | `upsidePct < 0` |
| `rebalance_order` | `action == "buy"` | `action == "sell"` |
| `breaker_forecast` | never (breakers are always a downside flag) | always (status is `TRIGGERED`) |

`MAINTAIN`/`WATCHLIST` action ratings are not harvested as claims — they carry no directional
prediction to grade.

`grade_predictions.py` finds every prediction where `today >= date + horizonDays` and no
matching record exists yet in `predictions_graded.jsonl`. For each, it fetches the ticker's and
SPY's price at the grading date via `market_data.get_prices()`, computes:

```
tickerReturn = (price_now - basePrice) / basePrice
spyReturn    = (spy_now - baseSpyPrice) / baseSpyPrice
relativeReturn = tickerReturn - spyReturn
```

Verdict: `correct` if `relativeReturn` agrees with `direction` beyond a **±2% inconclusive
band** (bullish correct when `relativeReturn > 0.02`, bearish correct when
`relativeReturn < -0.02`), `incorrect` if it disagrees beyond the band, `inconclusive`
otherwise. One function, `grade_claim(direction, relative_return) -> verdict`, shared by all
four claim types — no bespoke per-type grading path.

Default horizons: 90 days for `action_rating`, `rebalance_order`, and `breaker_forecast`; 180
days for `dcf_fair_value` (the guide mentions checking at "6/12 months" — 180 days is the
conservative middle, revisit if the first graded cohort shows the 12-month checkpoint is more
informative).

## 8. Components

- **`py_services/prediction_ledger.py`** — `PredictionRecord`/`GradeRecord` dataclasses,
  `append_prediction()`, `append_grade()`, `load_predictions()`, `load_graded()`,
  `grade_claim(direction, relative_return) -> verdict`. No CLI beyond a `--validate` mode that
  schema-checks both JSONL files (reuses the `jsonschema` dependency F4 already added).
- **`py_services/harvest_predictions.py`** — reads the four source artifacts, applies the
  dedup rule, calls `append_prediction()` for genuinely new/changed claims. CLI: `python3
  harvest_predictions.py [--dry-run]`. Missing `rebalance_plan.json` or empty
  `thesis_breaker_state.json` holdings are normal, not errors — skip that claim type silently
  for this run.
- **`py_services/grade_predictions.py`** — finds matured, ungraded predictions, grades them,
  calls `append_grade()`. CLI: `python3 grade_predictions.py [--dry-run]`.
- **`py_services/generate_track_record_report.py`** — joins both files, outputs rolling hit
  rate by claim type and by ticker, plus a total graded/ungraded count. CLI: `python3
  generate_track_record_report.py [--json]`.

## 9. Integration points

- **`/daily`**: new non-blocking step (after the existing risk/regime/breaker steps) runs
  `harvest_predictions.py`. On failure, print a stderr breadcrumb and continue — same
  degrade-gracefully posture as `risk_engine.py`'s integration in `daily_brief.py`. Never
  blocks the brief.
- **`/weekly-review`**: new phase (or extension of Phase 1) runs `grade_predictions.py` then
  `generate_track_record_report.py`, surfacing a "graded-predictions section" in the review.
  Matches the acceptance criterion verbatim: "will be sparse initially — fine."

## 10. Testing

- **Idempotency**: fixture `projections/`, `rebalance_plan.json`, `thesis_breaker_state.json`
  → harvester run twice produces the claim set once; second run appends nothing.
- **Change detection**: a fixture projection whose `aiThesis.action` changes between two
  harvester runs produces a second `action_rating` record for the same ticker.
  Fallback-source test: a fixture projection with no `analyticsLog.dcf` correctly harvests
  `dcf_fair_value` from `aiThesis.fairValue` instead.
  Missing-artifact tests: no `rebalance_plan.json` on disk → harvester completes with zero
  `rebalance_order` claims, not an exception. Empty `thesis_breaker_state.json.holdings` →
  zero `breaker_forecast` claims.
- **Grading**: `grade_claim()` unit tests covering clearly-correct, clearly-incorrect, and
  inconclusive-band cases for both bullish and bearish directions. `grade_predictions.py`
  integration test with a stubbed `market_data.get_prices()` verifying it only grades matured
  predictions and never re-grades an already-graded `id`.
- **Schema validation**: both JSONL formats validate against a `schemas/prediction.schema.json`
  (new, following F4's schema-as-source-of-truth convention) added to
  `validate_all_projections.py`'s sibling validation set — a `--validate` mode invocable
  standalone, not gating any existing write path.

## 11. Standing constraints checked

- **HITL is sacred**: N/A — this sub-spec is entirely read/report, no order-touching code path.
- **No silent schema breaks**: this is a new schema (`v: 1` field on both record types from
  day one), not a change to an existing one — no migration needed. `earnings_expectation` is
  reserved as an enum value now specifically so B4 doesn't require a migration later.
- **Reproducibility over cleverness**: every number in a graded record traces to a stored
  `basePrice`/`baseSpyPrice` and a `market_data.get_prices()` call at grading time — nothing
  is estimated or interpolated.
