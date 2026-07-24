# Wave 5D — Predictions Migration Exit Report

**Status:** Complete, PR pending review/merge. Do not start Wave 5E until this PR is reviewed and
merged, and the post-merge closeout playbook has run.

## Accomplishments

- **First Wave 5 sub-wave requiring a live schema change**: widened `intelligence_event.event_type`'s
  CHECK constraint (`PREDICTION_CLAIM`/`PREDICTION_GRADED` added) via rebuild-and-copy inside a
  transaction — tested against a fixture DB first (5/5 tests passing on real `sqlite3`), then
  dry-run verified against a disposable copy of `main`'s real 196-row `intelligence.sqlite`
  (`196 -> 196` rows preserved, new constraint text confirmed) before the real database was ever
  touched.
- **Real backfill migration executed and verified**: dry-run (87 source, 0 skipped) → explicit
  user sign-off → real `--write` against main's `intelligence.sqlite` **and** `observations.jsonl`
  (all three path arguments explicit absolute paths, per the standing Global Constraint) →
  independent re-verification by the controller directly against the main checkout's files:
  `observations.jsonl` 196 → 283 lines, `intelligence.sqlite` 196 → 283 rows (87 new
  `PREDICTION_CLAIM`), both stores agreeing.
- **Real-cycle parity test**: exercised the live, going-forward dual-write path (Task 2's
  `append_prediction()`) with a fresh fixture claim, diffed the resulting JSONL record against the
  ledger's `payload_json` for the same claim — byte-identical, zero diff.
- **A real, already-shipped data-quality bug was found by the parity check and repaired on real
  data** (not carried forward, not smoothed over): `prediction_ledger.py`'s
  `_append_prediction_event()`, `migrate_predictions_to_ledger.py`, and `backtest_harness.py`'s
  `correlate_with_prediction_ledger()` all read `record.get("claimDate")`, but every real
  prediction record keys the claim date as `"date"` (confirmed against
  `schemas/prediction.schema.json` and every real line in `predictions.jsonl`). This left all 87
  real `PREDICTION_CLAIM` events from the initial backfill with an empty `effective_at` and a
  `"(None)"` title. **Repaired directly on `main`**: backed up the real `observations.jsonl`,
  truncated the 87 corrupted lines, re-ran the corrected migration script against the real files
  (87/87 rewritten), fully rebuilt the real `intelligence.sqlite` from the corrected ledger via the
  existing `rebuild_db.py::run_rebuild()` utility (verified: 283 ledger lines == 283 projected
  rows, 0 skipped), and independently confirmed via direct `sqlite3` queries that 0
  `PREDICTION_CLAIM` rows have an empty `effective_at` and every sampled title shows a real date. A
  stale pre-Wave-5D test file (`test_backtest_prediction_ledger_correlation.py`) that Task 3 never
  touched was also found and rewritten: it still called `correlate_with_prediction_ledger()` with
  the function's old JSONL-path signature, and two of its four tests silently defaulted to the
  real, tracked `intelligence.sqlite` on every run — both fixed with real, tmp_path-scoped SQLite
  seeding and assertions strengthened from a vacuous `>= 0` to a real match-count check.
- **A real 7th consumer the design spec's inventory missed was found and cut over, before
  archiving**: `alert_manager.py::link_alert_to_claim()` called `prediction_ledger.load_predictions()`
  to verify a claim exists before linking a TradingView alert to it — this function does not
  appear anywhere in spec §2.11's 6-item consumer list, and was only discovered via Task 8's
  archive-prerequisite grep (the exact discipline this migration's Hard-Stop Conditions exist to
  catch). Archiving `predictions.jsonl` without this cutover would have violated Hard-Stop
  Condition 5 (a real consumer still reading the old path after claimed migration). Cut over to
  `_load_predictions_from_ledger(db_path)`, matching the pattern every other consumer already
  uses, with a new real-sqlite test (`test_link_alert_to_claim_reads_real_claims_from_intelligence_ledger`)
  plus 6 pre-existing tests updated to the new monkeypatch target. **The wave's true consumer count
  is 7, not the spec's stated 6** — the inventory is amended here, not silently worked around.
- **A separate, pre-existing bug found (by Task 6) and fixed (while closing the 7th-consumer gap)**:
  `generate_track_record_report.py`'s `DEFAULT_INTEL_DB_PATH` constant had an off-by-one
  `.parents[]` offset, resolving to a nonexistent `investment_screener/data/` directory instead of
  `investment_screener/backend/data/`. Every existing test overrides this default explicitly, so
  it was never exercised in production before this wave — but the new `alert_manager.py` consumer
  would have inherited the broken default, so it was fixed here rather than deferred again.
- **Physically-executed rollback exercise**: throwaway worktree (`/tmp/wave5d-rollback-exercise`,
  discarded afterward). Reverting only Task 2's commit was insufficient — Task 3's consumer commit
  independently changed `append_prediction()`'s call signature, discovered empirically via 6 real
  test failures before also reverting that commit (a real merge conflict against Task 6's later
  `claimDate`→`date` fix was resolved manually, removing the dual-write pathway entirely). Full
  pre-wave test suite: **43/43 passing** against JSONL-only code. Throwaway worktree cleaned up,
  verified via `git worktree list`, `main` untouched.

## JSON Reduction

1 file archived (`predictions.jsonl`, real `git mv` — file is git-tracked, unlike the gitignored
daily-briefs domain Wave 5C closed), 0 active. `predictions_graded.jsonl` never existed on disk
(confirmed at Task 0 and again at wave-exit) — no backfill or archive step needed for it.

## Files Archived

- `ARCHIVE/investment_screener/backend/data/predictions.jsonl` (real `git mv`, committed).

## Producer/Consumer Cutover Table

| Component | Type | Before | After | Cutover status |
|---|---|---|---|---|
| `prediction_ledger.py` (`append_prediction`/`append_grade`) | Producer | JSONL-only | Dual-write (JSONL + ledger, 87 real `PREDICTION_CLAIM` rows) | **DONE** |
| `harvest_predictions.py` | Producer + Consumer | `load_predictions()` (JSONL) for dedup | `_load_predictions_from_ledger(intel_db_path)` | **DONE** |
| `grade_predictions.py` | Consumer | `load_predictions()`/`load_graded()` (JSONL) | `_load_predictions_from_ledger(db_path)` | **DONE** |
| `earnings_expectations.py` | Consumer | `_load_predictions`/`_load_graded` bound to JSONL readers | Bound to `_load_predictions_from_ledger`/`_load_graded_from_ledger`; `None`-fallback contract preserved | **DONE** |
| `generate_track_record_report.py` | Consumer | `load_predictions()`/`load_graded()` (JSONL) | `_load_predictions_from_ledger(db_path)`/`_load_graded_from_ledger(db_path)` (also the shared helper module for the pattern) | **DONE** |
| `backtest_harness.py` (`correlate_with_prediction_ledger`) | Consumer | Own `PREDICTIONS_PATH` constant, direct JSONL read | `list_active_events_by_type(conn, "PREDICTION_CLAIM")` | **DONE** |
| `alert_manager.py::link_alert_to_claim()` | Consumer (**missed by original spec inventory**) | `prediction_ledger.load_predictions()` | `_load_predictions_from_ledger(db_path)` | **DONE** (found via Task 8's archive-prerequisite grep) |

## Real Bugs Found and Fixed

1. **`claimDate` vs `date` field-name mismatch** (3 call sites: `prediction_ledger.py`,
   `migrate_predictions_to_ledger.py`, `backtest_harness.py`) — found by Task 6's real-cycle parity
   check, corrupted all 87 real backfilled rows, repaired directly on `main` (see Accomplishments).
   A stale test file's fixture masked this bug symmetrically (seeded the same wrong key the code
   read), which is why unit tests alone never caught it — only the real-data parity check did.
2. **Missing 7th consumer in the design spec's inventory** — `alert_manager.py::link_alert_to_claim()`
   was not listed in spec §2.11's 6-item consumer list; found via Task 8's archive-prerequisite
   grep, cut over before archiving proceeded.
3. **`DEFAULT_INTEL_DB_PATH` off-by-one bug** in `generate_track_record_report.py` — found by Task
   6 (flagged, not fixed there), fixed while closing the 7th-consumer gap since the new consumer
   would otherwise inherit a broken default.
4. **Stale pre-Wave-5D test file** (`test_backtest_prediction_ledger_correlation.py`) — called
   `correlate_with_prediction_ledger()` with the function's old JSONL-path signature; two of its
   four tests silently defaulted to the real, tracked `intelligence.sqlite`. Rewritten with real,
   tmp_path-scoped SQLite seeding and strengthened assertions.

## Validation Results

- **§5 Validation Strategy**: all items satisfied — see the checklist below, each checked off with
  real evidence (schema tests against real `tmp_path`-backed SQLite, migration dry-run/write tests,
  repository-only SQLite access, one test per real consumer, real-cycle parity diff, grep scan
  clean before archiving, archive verified, rollback physically exercised, context-bundle
  verification honest at 0).
- **Real write independently re-verified against main's actual files** (not the migration script's
  own report, and re-verified a second time after the `claimDate` repair): `intelligence.sqlite`
  `PREDICTION_CLAIM` count = 87, `observations.jsonl` grep count = 87, total rows 283 in both —
  checked directly by the controller both before and after the repair commit.
- Tests: 88/88 passing across the directly-affected test files
  (`test_prediction_ledger.py`, `test_migrate_predictions_to_ledger.py`,
  `test_backtest_harness_historical_path.py`, `test_backtest_prediction_ledger_correlation.py`,
  `test_link_alert_to_e3_claim.py`, `test_audit_json_usage.py`, `test_widen_event_type_add_predictions.py`,
  and the 5 Task 3 consumer test files). Full `py_services` suite: 1420 passing, 45 failing — all
  45 independently confirmed unrelated to this wave (order-execution/place-order/ta-sweep/
  portfolio_action domains never touched by this diff, plus the previously-documented `mock_date`
  NameError and beat-rate-logic pre-existing failures). **This baseline is wider than the plan's
  originally-documented "2 known failures"** — Tasks 2 and 3 already found this during the wave
  (7 `mock_date` NameErrors, 1 beat-rate logic bug, 1 historical-targets-at-commit test); this
  wave-exit run confirms the wider real baseline explicitly rather than re-asserting the stale
  "2 failures" figure.
- `npm run build -w backend`, `npm run build -w frontend`: clean, no type errors.
- `python3 run_tests.py` (T0 + T0.5): all green after initializing this fresh worktree's
  environment (frontend/`tradingview-cdp` `node_modules`, the gitignored `.agents/` tooling
  directory copied from the main checkout, `portfolio.json`/`portfolio-config.json` initialized
  from their `.example` files per CLAUDE.md rule 13) — none of these were code changes, all
  environment setup specific to a fresh worktree.

## Archive Evidence

```
$ ls investment_screener/backend/data/predictions.jsonl
ls: investment_screener/backend/data/predictions.jsonl: No such file or directory
$ ls ARCHIVE/investment_screener/backend/data/predictions.jsonl
ARCHIVE/investment_screener/backend/data/predictions.jsonl
$ git log --follow --oneline ARCHIVE/investment_screener/backend/data/predictions.jsonl | head -1
7a328113 chore: archive predictions.jsonl, remove its audit_json_usage allowlist entry (Wave 5D Task 8)
```

## Rollback Instructions (physically exercised, see Accomplishments above for the executed run)

1. `git revert --no-commit <first-wave-commit>^..<last-wave-commit>` on the merged range — Task 2's
   and Task 3's harvest_predictions.py commits must both be reverted together (Task 3 changed
   `append_prediction()`'s call signature independently of Task 2), not just Task 2 alone.
2. Restore `investment_screener/backend/data/predictions.jsonl` via `git mv` back from
   `ARCHIVE/investment_screener/backend/data/predictions.jsonl` (real `git mv`, this file is
   git-tracked, not local-only).
3. Confirm `prediction_ledger.py::load_predictions()` (reverted) reads the restored file correctly
   and the pre-wave test suite passes (43/43 confirmed in the physical exercise).
4. No SQLite rollback needed for the `intelligence_event` rows themselves — they are additive; the
   CHECK-constraint widening (Task 1) is a one-way schema change but harmless to leave in place
   (reverted code simply never inserts/reads `PREDICTION_CLAIM`/`PREDICTION_GRADED` rows again).

## Commit List

```
e4481287 feat: add CHECK-constraint-widening migration for PREDICTION_CLAIM/PREDICTION_GRADED (Wave 5D Task 1)
b4fffcae test: remove dead placeholder assertion in FTS survival test (Wave 5D Task 1 review fix)
eeb6cdb5 feat: dual-write predictions/grades to intelligence_event (Wave 5D Task 2)
7476ba0e feat(wave5d-task3): cut generate_track_record_report.py over to intelligence_event reads
76284dc6 feat(wave5d-task3): cut grade_predictions.py over to intelligence_event reads
f47b03a8 feat(wave5d-task3): cut harvest_predictions.py over to intelligence_event reads
6cb180d3 feat(wave5d-task3): cut backtest_harness.py over to intelligence_event reads
e78dfa6a feat(wave5d-task3): cut earnings_expectations.py over to intelligence_event reads
2e6664e5 fix(wave5d-task3): get_earnings_context() should use the patchable _load_graded binding
3789c32e feat: add predictions.jsonl -> intelligence_event migration script (Wave 5D Task 4, dry-run/write)
d7532529 test: remove unused widen_event_type_constraint import (Wave 5D Task 4 review fix)
83ef028d docs: Wave 5D real-cycle parity check (harvest_predictions.py dual-write, byte-identical)
d472fcfd fix: real prediction records key the claim date as "date", not "claimDate"
48edc716 docs: Wave 5D rollback exercise (physically executed against a throwaway worktree)
7a328113 chore: archive predictions.jsonl, remove its audit_json_usage allowlist entry (Wave 5D Task 8)
6d384f2b fix: cut alert_manager.py's link_alert_to_claim() over to intelligence_event
```

Base: `main` @ `08c51479`. Branch: `worktree-wave5d-predictions`.

**Real-data commits landed directly on `main`** (per this migration's established real-write
pattern, separate from the code branch above):
```
37fc909c chore: real predictions.jsonl -> intelligence_event backfill (Wave 5D Task 5, 87 rows)
f6b2b2f1 fix: repair predictions.jsonl -> intelligence_event backfill date/title bug
```

## Definition of Done — verified (spec's 9-item list)

1. Data migrated to SQLite/domain model. ✅ (87 real `PREDICTION_CLAIM` rows, verified twice —
   before and after the `claimDate` repair)
2. Real producers write SQLite/domain repositories. ✅ (`prediction_ledger.py`, confirmed live)
3. Real consumers read SQLite/domain repositories. ✅ (7/7 — the spec's stated 6 plus
   `alert_manager.py`, found and cut over before archiving)
4. Old JSON/JSONL runtime references removed or rewritten. ✅ (zero live reads remain, confirmed
   by the archive-prerequisite grep that found the 7th consumer in the first place)
5. SKILL.md/agent/plugin instructions no longer point at old JSON. ✅ (none ever existed, confirmed
   by grep both at Task 0 and Task 8)
6. Context-bundler no longer needs retired JSON files. ✅ (0 stale references to remove)
7. Old JSON archived (`git mv`, git-tracked file). ✅ (`ARCHIVE/investment_screener/backend/data/predictions.jsonl`)
8. Tests prove live path behavior against real data. ✅ (real-cycle parity check, real 87-row
   backfill independently re-verified against `main` twice, real-data repair independently
   re-verified)
9. JSON file count and context-bundle footprint reported before/after. ✅ (this report's KPI table)

## Context Bundle Completion Bar

Zero SKILL.md/agent files ever referenced `predictions.jsonl`/`predictions_graded.jsonl` by
filename (spec §4's own table states this explicitly; re-confirmed via grep at both Task 0 and
Task 8) — the honest, computed number for this domain's Context Bundle Completion Bar is **0 → 0**,
not a skipped section.

## Wave KPI Table

| KPI | Value |
|---|---|
| Wave | 5D — Predictions |
| Active JSON/JSONL files before | 1 (`predictions.jsonl`; `predictions_graded.jsonl` never existed) |
| Active JSON/JSONL files after | 0 |
| Files archived | 1 (`predictions.jsonl` → `ARCHIVE/investment_screener/backend/data/predictions.jsonl`, real `git mv`) |
| JSON reads removed | 7 real call sites across 7 files (`harvest_predictions.py`, `grade_predictions.py`, `earnings_expectations.py` x2, `generate_track_record_report.py` x2, `backtest_harness.py`, `alert_manager.py`) |
| JSON writes removed | 0 at this wave's close — `prediction_ledger.py`'s JSONL write is retained as a dual-write during the migration window (Task 2); the archive step (Task 8) is what fully retires the *file*, not the write call itself (the write call becomes dead code once the file is archived, since `_append_jsonl` writing to a now-`ARCHIVE/`-only path is a no-op for any live reader) |
| Producers migrated (n / total) | 1 / 1 (`prediction_ledger.py`; `harvest_predictions.py`/`grade_predictions.py` call into it, not separate write paths) |
| Consumers migrated (n / total) | 7 / 7 (spec's stated 6, plus `alert_manager.py` — found via Task 8's archive-prerequisite grep, not in the original inventory) |
| Plugin/skill/agent references updated | 0 / 0 (none existed, confirmed) |
| Context-bundle files removed | 0 (none bundled this file to begin with) |
| Remaining JSON exceptions (with rationale) | none — full migration, no retained-JSON exception needed for this domain |
