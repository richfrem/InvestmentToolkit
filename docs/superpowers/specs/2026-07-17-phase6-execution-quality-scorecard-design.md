# Phase 6, Sub-Project 4 — Execution Quality Scorecard (Reward-Modeling Groundwork) — Design

_Date: 2026-07-17_

## Context

`start_here.md` speculatively noted "Phase 6 (future) will use Phase 5's audit trails
(`orders_executed.jsonl`) to train reward models on execution quality" — flagged at the time as
one candidate among several, not a locked requirement. Brainstorming this session resolved the
key fork: this repo has zero ML training infrastructure (no GPU pipeline, no training framework,
no model serving) and every other analytical component is a deterministic Python script
(`risk_engine.py`, `framework_score.py`, `generate_track_record_report.py`). Building a literal
trained reward model would be a first-of-its-kind, disproportionate undertaking. The user
confirmed: build a deterministic execution-quality scorecard instead, matching the existing
pattern exactly.

## Gap this closes

`order_risk_gates.py`'s `log_order_execution()` (Phase 5E-8) has appended to
`data/orders_executed.jsonl` since Phase 5 shipped, but its own docstring says: "a reader isn't
requested by the plan and isn't needed by any other Task 5E function, so it isn't built here
(YAGNI)." No script has ever read this file. Separately, `generate_track_record_report.py` (E3)
computes hit-rates from `predictions.jsonl`/`predictions_graded.jsonl` but never touches
`orders_executed.jsonl` — these are two different data sources that have never been joined.

## Scope

New script: `investment_screener/backend/py_services/execution_quality_scorecard.py`.

**Reads:**
- `data/orders_executed.jsonl` (gitignored, append-only — one record per order attempt: `order`,
  `decision` ∈ {EXECUTED, BLOCKED, OVERRIDDEN}, `gate_result` with per-gate pass/fail + reasons,
  optional `trade_execution_result`)
- `data/trade-log.json` (existing order history, for cross-referencing tickers only — not for
  return/P&L computation, which isn't available there)

**Computes:**
1. **Decision breakdown** — count of EXECUTED / BLOCKED / OVERRIDDEN across all logged attempts.
2. **Per-gate fail rate** — of the 6 gates in `check_risk_gates()`'s output (`mrc`,
   `cluster_variance`, `breaker_veto`, `size`, `balance`, `data_readiness`), how often each one's
   `passed` is `False` across all logged attempts. This is the foundational signal a future,
   more sophisticated correlation (gate failure → subsequent performance) would build on.
3. **Overridden-order registry** — a flat list of every `OVERRIDDEN` decision with its ticker,
   which gate(s) it overrode, and the stated reason — a manual-review worklist, not an automated
   verdict (no outcome/return computation in this pass — that needs price-history joining this
   script deliberately does not do, consistent with "groundwork" scope).

**Explicitly NOT in scope for this pass:** any return/P&L correlation (would require joining
price history the script doesn't fetch), any ML model training, any change to
`aiThesis.action` or `standingDecision` (informational only, matching every other signal in this
repo).

## Degradation posture

`orders_executed.jsonl` currently has 5 sandbox/test entries (all `BLOCKED`, insufficient-cash
test data), zero real `EXECUTED` or `OVERRIDDEN` entries. The script must degrade gracefully on
this — same posture `generate_track_record_report.py` already documents: "expected to be sparse
for a while after this ships, which is fine." Missing file → empty report, not a crash.

## Integration

Wired into `/weekly-review` as a new advisory-only section, immediately after the existing
Phase 1b track-record section (same file, same pattern):
```bash
python3 investment_screener/backend/py_services/execution_quality_scorecard.py --json
```
Presented alongside the hit-rate table with the same "may be empty for now, that's expected"
framing. Never gates any recommendation.

## Testing

Following `test_generate_track_record_report.py`'s exact pattern: pure functions tested via
injected `tmp_path` fixtures (never touching the real gitignored `orders_executed.jsonl`), one
test class per function, an explicit "empty/missing file" test case per function.

## Out of Scope

- ML reward-model training (ruled out during brainstorming).
- Return/P&L correlation requiring price-history joins.
- The other Phase 6 sub-projects (all now complete or addressed this session).
