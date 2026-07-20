# Wave 2 (Investment/Target/Watchlist/Alerts/Thesis-Breaker) — Handoff

Status: **Complete, PR to be opened, awaiting review/merge. Wave 3 not started.**

## What Wave 2 Accomplished

Migrated `target-portfolio.json` (real path: `data/theses/target-portfolio.json`),
`watchlist.json`, `tradingview_alerts_actual.json`, and `thesis_breaker_state.json` — plus their
embedded sub-domains (price levels, investment notes/`agentRationale`, standing decision, thesis
breaker status) — into the v3.2 SQLite domain model. 6 real producers and 23 real consumer files
cut over. 2 files fully archived (`watchlist.json`, `tradingview_alerts_actual.json`). 2 files
retained under a completed, user-approved Retained-JSON Rationale Bar
(`target-portfolio.json`, `thesis_breaker_state.json`) — real architecture boundaries, not
incomplete work; full rationale in the exit report.

**JSON reduction:** 2 files archived this wave (4 → 2 active for this domain's file count).

## The Plan's Original Inventory Was Significantly Wrong — Same Pattern as Wave 1

Wave 1 found the real file count was 82, not 144. Wave 2 found:
- **7 of 11 "producers"** in the plan were never real writers of any of these 4 files at all
  (`market_regime.py`, `risk_engine.py`, `rebalancer.py`, `backtest_harness.py`,
  `ta_sweep_batch.py`, `daily_brief.py`, `BrokerSyncService.ts`).
- **2 real consumers were missing from the plan entirely** (`market_regime.py`, `risk_engine.py`
  — found only by this wave's own archive-readiness grep, not the original investigation).
- **The real `agentRationale` writer was misattributed** — the plan said `update_thesis.py`; the
  real writer is `apply_catalyst.py`, not in the plan's producer list at all.
- **`portfolio_action.py`** (6 symlinked copies) was missing from the consumer list, caught before
  implementation via a dedicated pre-execution investigation.
- **`watchlist.json`'s real shape** is `{"watchlist": [...]}`, not a flat array as assumed.
- **A real architecture boundary, not a gap**: `ThesisService.ts`'s full-document CRUD genuinely
  cannot be cut over without new schema (fields like `globalSettings`, `bandConfig`, `shares`,
  full `thesisBreakers`/`standingDecision` sub-objects have no SQLite column). Presented to the
  user; explicit decision made to accept as a documented retained exception rather than expand
  scope mid-wave.

## Seven Real Bugs Found and Fixed (not scope creep — each blocked correctness)

1. Two stale pre-move path references (`order_risk_gates.py`, `backtest_harness.py`) — fixed in
   Task 0, before migration code, with dedicated tests.
2. Two real FK gaps caught during the actual `--write` (not a fixture): `target-portfolio.json`
   has no `subStrategies[]` definition array (only inline references), and one holding uses
   `pillarId="other"`, undefined in `pillars[]`. Both auto-resolved with minimal placeholder rows.
3. `generate_review.py`'s EXIT/INITIATE counts had been **silently always 0 in production** — the
   pre-rewire code checked a `"holdings"` key on pillar entries that real data never has.
4. `tv_create_alerts.py` had been reading from `data/projections/` since Wave 1 archived that
   directory — a real, live dead-read-path bug this rewire fixed as a side effect.
5. A test regression: `earnings_expectations.py`'s rewire left one test file mocking `open()`
   with no effect on the new SQLite read path, leaking real production data (`NVDA`) into 2 test
   assertions. Caught by this wave's own full-suite-verification discipline, fixed by seeding a
   real tmp SQLite db.
6. `market_regime.py`/`risk_engine.py` were live, unrewired consumers the plan's inventory missed
   entirely — found by the archive-readiness grep, fixed before archiving.
7. A background sub-agent hit its API session limit mid-file, leaving `harvest_predictions.py`
   broken (renamed function, stale call sites referencing undefined names). Caught by direct
   diagnostics, manually finished and independently verified (63 tests passing) before merging.

Every one of these was caught by independent verification against real data/code/test runs — not
by any single dispatch's self-report — following this migration's standing discipline.

## Wave KPI Summary

| KPI | Value |
|---|---|
| Active JSON files before | 4 |
| Active JSON files after | 2 archived + 2 retained-with-rationale |
| Files archived | 2 |
| Real producers migrated | 6 / 6 |
| Real consumers migrated | 23 / 25 confirmed real (2 confirmed not real consumers) |
| Real bugs found & fixed | 7 |
| Migration parity | All counts reconciled exactly against dry-run baseline, user-verified before write |
| `standingDecision` anchor rule (CLAUDE.md #8) | Explicitly re-verified — PASS, byte-for-byte parity test against real ticker VST |
| Test regressions introduced (net, after fixes) | 0 |

Full KPI table, Retained-JSON Rationale Bars, producer/consumer cutover table, and validation
evidence: `docs/superpowers/status/wave2-target-portfolio-report.md`

## Open Issues (non-blocking, named for whoever picks these up)

- **`target-portfolio.json` remains JSON-authoritative for `ThesisService.ts`'s full-document
  CRUD.** Future trigger: add schema for `globalSettings`/`changeLog`/`bandConfig`/`shares`/full
  `thesisBreakers`/full `standingDecision` sub-object, then rewire in a dedicated future wave.
- **`thesis_breaker_state.json` remains JSON-authoritative** for `thesis_breakers.py` (producer)
  and `order_risk_gates.py`/`rebalancer.py`/`harvest_predictions.py` (consumers) — real
  per-breaker-id granularity `investment.thesis_breaker_status`'s single scalar column can't
  represent. Future trigger: a `thesis_breaker_definition` child table, or fold into
  `intelligence_event` (an option named but not decided).
- **`update_thesis.py`** writes `role` and `thesisBreakers` definitions to `target-portfolio.json`
  with no schema destination — same category as the two above, tracked together.
- **Reference-data anomalies** (14 auto-inferred sub-strategy placeholder names, 1 auto-inferred
  pillar placeholder name) — a real product/governance question (should these get authored
  display names eventually?), not a migration defect. Full list in the exit report.
- **Doc/SKILL.md text references** to these filenames were not updated this wave — same category
  Wave 1 left open, no runtime dependency.
- **Plugin/skill/agent instruction updates (spec §4 table)** were not done this wave — deferred,
  same as Wave 1.

## Remaining Migration Waves (from the approved implementation plan)

- **Wave 3** — Account holdings (`portfolio.json`, gitignored, largest domain — 20 producers,
  ~32 consumers per the original plan's estimate — **re-verify this count fresh, do not trust it**,
  per every wave's own experience so far). Not started.
- **Wave 4** — Portfolio operations (trade log, order executions, cash flows). Not started.
- **Wave 5A–5E** — Generated research views (closes prior-effort debt) → TA sweep → daily briefs
  → predictions → account policy. Not started.

## Exact Branch/Commit References

- Branch: `worktree-domain-model-v3-wave2`
- Commit range: `80eeab2b..d1f5b090` (24 commits: 23 implementation + 1 exit report not yet
  committed at the time of this writing — will be included before PR)
- Base (Wave 1 merge point): `1df90086` (main HEAD at Wave 2 start, includes Wave 0+1 via PR
  #84/#85)
- Archive commit: `d1f5b090`
- **PR not yet created** — to be opened after this handoff and the exit report are committed.
- **`main` has NOT been updated** — Wave 2's commits exist only on this branch pending PR review.

## Instructions for the Next Fresh Session

1. **If picking up Wave 2 review/merge**: review the PR on GitHub once opened, then either merge
   it yourself or tell the agent to merge once approved. Do not assume it's merged — check
   `git log origin/main` for commit `d1f5b090` before trusting anything downstream depends on
   Wave 2 being on `main`.
2. **If starting Wave 3**: gated behind this wave's review, per standing instruction. Confirm the
   Wave 2 PR is merged into `main` first. Then follow the same process: `superpowers:writing-plans`
   to write Wave 3's detailed task plan (re-reading the real current `portfolio.json` producer/
   consumer code fresh — do not trust the original plan's 20-producer/32-consumer estimate,
   per this whole migration's established discipline, confirmed again this wave), then
   `superpowers:subagent-driven-development` to execute it in a fresh worktree.
3. **Wave-level conditional autonomy applies going forward** (per user instruction, formalized
   this wave): execute each wave end-to-end without per-task pause; two mandatory review points
   only (dry-run gate before any real write, and the exit report before PR); hard-stop conditions
   still apply in full (parity mismatch, unexplained row-count delta, new data shape without a
   test, a producer/consumer still on the old JSON path, a repository-layer bypass, new test
   failures, archive-readiness grep still finding real I/O, an archive step that would remove
   rollback capability, a permanent unexamined hybrid state). Produce a wave exit report +
   handoff + a fresh-session kickoff prompt for the next wave at the end of every wave, then stop
   for review.
4. **Background sub-agent session-limit risk**: this wave hit an API session limit mid-dispatch
   once, leaving a broken file in an orphaned worktree. If dispatching large batches of file
   rewires to background agents in Wave 3+, instruct them explicitly to commit after every single
   file (not batches), and independently verify — via direct test runs and grep, not by trusting
   the dispatch's self-report — before folding any orphaned worktree's work back in.
5. **Real data caveat**: `investment_screener/backend/data/domain_model.sqlite` now holds Wave
   0+1+2 data (95 investments, 14 pillars, 14 sub-strategies, 8 price-level sets, 50 price-level
   tiers, 73 investment notes, 203 alerts, plus Wave 1's 115 projection_version/345
   projection_scenario rows). It is gitignored — a fresh checkout needs `initialize_db()` +
   re-running both `migrate_projections_to_sqlite.py --write` (Wave 1) and
   `migrate_target_portfolio_to_sqlite.py --write` (Wave 2) to reconstruct it.
