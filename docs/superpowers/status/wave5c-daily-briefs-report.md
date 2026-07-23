# Wave 5C — Daily Briefs Migration Exit Report

**Status:** Complete, PR pending review/merge. Do not start Wave 5D until this PR is reviewed and
merged, and the post-merge closeout playbook has run.

## Accomplishments

- Closed ADR-029's debt for the `data/daily-briefs/*.json` domain: producer already dual-wrote to
  the Intelligence Ledger before this wave began, but the ledger had **0** real `REVIEW_DAILY`
  rows in main's `intelligence.sqlite`. Task 0 investigation found the gap was expected new-code
  lag (the dual-write block landed 2026-07-18, all 10 pre-existing real snapshots predate/coincide
  with that commit, no bug), not a silent failure.
- **Real backfill migration executed and verified**: dry-run (10 source, 0 skipped) → explicit user
  sign-off → real `--write` against main's `intelligence.sqlite` **and** `observations.jsonl` (both
  explicit paths, per the standing Global Constraint on multi-store migration writes) → independent
  re-verification of both stores by the controller (not the script's own report): `10/10` in each.
- **Real-cycle parity test**: ran one live `daily_brief.py --json` cycle against the user's real
  TradingView/broker session (10 real TA-swept tickers already fresh; 79 holdings scanned this
  run). Diffed the resulting `2026-07-23.json` snapshot against the ledger's `payload_json` for the
  same `effective_at` date — **byte-identical, zero diff**. Post-run row counts independently
  re-verified: `11/11` in both `intelligence.sqlite` and `observations.jsonl`.
- **A real, pre-existing anti-bypass violation was found and fixed** (Task 0/1), not carried
  forward: `query_ledger_brief.py`'s `--history` and `--conviction` branches opened their own raw
  `sqlite3.connect()` and ran inline SQL against `intelligence_event`, instead of going through
  `py_services/intelligence/event_repository.py`. Fixed by adding
  `list_active_events_by_type(conn, event_type)` to the repository module and routing both
  branches through it — closes Hard-Stop Condition #6 for this domain.
- **A real consumer the design spec's inventory missed was found and cut over**:
  `investment_screener/backend/src/routes/dailybrief.ts` (3 route handlers) — the spec's §4 table
  only listed `generate_reports.py`. The route already had ledger-first code with a JSON fallback
  (which, with 0 real ledger rows, was silently serving 100% of real traffic from the fallback
  branch until this wave's backfill). Fallback branches removed once real data existed.
- **Physically-executed rollback exercise**: throwaway worktree (`wave5c-rollback-exercise-
  throwaway`, discarded afterward), `git revert --no-commit` of all 8 wave commits — clean, zero
  conflicts. Restored the archived JSON files from `ARCHIVE/`, ran the reverted (pre-wave)
  `generate_reports.py::load_latest_brief()` against them — correctly read the real restored
  2026-07-23 snapshot. Full pre-wave test suite: **21/21 passing** against the reverted state.
- Final whole-branch review: zero Critical/Important findings, 3 known Minor items confirmed
  non-blocking (inline-import repetition in `query_ledger_brief.py`; test duplication in
  `test_daily_brief_review_daily_dual_write.py`; a docstring saying "LIMIT 2" where the actual
  query has no literal `LIMIT` clause — functionally correct either way).

## JSON Reduction

11 files archived (`data/daily-briefs/*.json`, local-only `mv` since the directory is gitignored —
never `git mv`), 0 active.

## Files Archived

- `ARCHIVE/investment_screener/backend/data/daily-briefs/*.json` (11 files, local-only `mv`,
  main checkout only — never staged/committed, matching the same convention as
  `portfolio.json`/`cash_flows.json`).

## Producer/Consumer Cutover Table

| Component | Type | Before | After | Cutover status |
|---|---|---|---|---|
| `daily_brief.py` | Producer | Dual-write (JSON + ledger, 0 real ledger rows) | Dual-write (JSON legacy export + ledger, 11 real rows) | **DONE** — ledger write confirmed live and correct via real-cycle parity |
| `dailybrief.ts` (`/latest`, `/history`, `/conviction/:ticker`) | Consumer | Ledger-first with JSON fallback (fallback always taken — 0 real ledger rows) | Ledger-only, fallback branches removed | **DONE** |
| `generate_reports.py::load_latest_brief()` | Consumer | `glob.glob(DAILY_BRIEFS_DIR/*.json)`, latest mtime | `list_active_events_by_type(conn, "REVIEW_DAILY")`, newest-first | **DONE** |
| `daily_brief.py::_load_yesterday()` | Consumer | `sorted(DAILY_BRIEFS_DIR.glob("*.json"), reverse=True)`, skip today | Real SQL-backed query via `list_active_events_by_type`, skip today preserved | **DONE** |
| `query_ledger_brief.py` (`--history`/`--conviction`) | Internal (backs the route consumer) | Raw `sqlite3.connect()` + inline SQL | Routed through `event_repository.list_active_events_by_type` | **DONE** (anti-bypass fix) |

## Real Bugs Found and Fixed

1. **Anti-bypass violation** in `query_ledger_brief.py` (pre-existing, found in Task 0) — fixed in
   Task 1. See `list_active_events_by_type` addition to `event_repository.py`.
2. **Missing consumer in the design spec's inventory** — `dailybrief.ts` was not listed in spec §4's
   producer/consumer mapping table for this domain; found via direct code read in Task 0, added to
   this wave's cutover table, and cut over in Task 7.
3. **Missing test for the producer's dual-write block** (the exact "no real test exists for this
   path" gap the prior effort's status doc flagged) — added in Task 2, both new tests passed on
   first run (no bug in the dual-write machinery itself — `append_event`/`replay_events_to_db` were
   already correct, just untested for this event type).

## Validation Results

- **§5 Validation Strategy**: all items satisfied — see the plan document's checklist, now checked
  off with real evidence per item (migration dry-run/write against real data, repository tests,
  consumer tests, real-cycle parity, live-path curl check against the real running backend, grep
  scan clean, archive verified, rollback physically exercised, context-bundle reference corrected).
- **Real write independently re-verified against main's actual files** (not the migration script's
  own report): `intelligence.sqlite` `REVIEW_DAILY` count = 11, `observations.jsonl` grep count =
  11 — both checked directly by the controller, both matching.
- **Live-path check**: `GET /api/daily-brief/latest` and `/history` against the real running
  backend (main checkout, port 3001, real bearer token) returned real data sourced from the real
  ledger rows (date `2026-07-18` before the live run, later confirmed `2026-07-23` present after).
- Tests: 31/31 Python (`py_services`, daily_brief/generate_reports/migrate/event_repository
  suites), 5/5 mocha (`dailybrief.spec.ts`), `tsc --noEmit` clean.
- Pre-existing baseline unaffected: no new or migration-related test failures introduced.

## Archive Evidence

```
$ ls investment_screener/backend/data/daily-briefs/
(empty)
$ ls ARCHIVE/investment_screener/backend/data/daily-briefs/ | wc -l
11
```

## Rollback Instructions (physically exercised, see Accomplishments above for the executed run)

1. `git revert --no-commit <first-wave-commit>^..<last-wave-commit>` on the merged range.
2. Restore `investment_screener/backend/data/daily-briefs/*.json` from
   `ARCHIVE/investment_screener/backend/data/daily-briefs/` (local `cp`, not `git mv` — the
   archive was never git-tracked).
3. Confirm `generate_reports.py::load_latest_brief()` (reverted) reads the restored files
   correctly and the pre-wave test suite passes.
4. No SQLite rollback needed for the `intelligence_event` rows themselves — they are additive and
   harmless to leave in place (the CHECK constraint already had `REVIEW_DAILY` as a valid value
   before this wave; the rows are simply unread by reverted code).

## Commit List

```
bc60aa92 fix(query_ledger_brief): route --history/--conviction through event_repository, close anti-bypass gap
aebdd2ec docs: add Wave 5C implementation plan
641d56a5 test(daily_brief): add missing real test for REVIEW_DAILY dual-write block
26c04bda feat(migrate_daily_briefs_to_ledger): add dry-run/write backfill script for REVIEW_DAILY
9349c2ec feat(generate_reports): cut load_latest_brief() over to intelligence_event ledger
9b309d2e feat(daily_brief): cut _load_yesterday() over to a real SQL query against intelligence_event
8f42b00e refactor(dailybrief.ts): remove JSON fallback branches, ledger-only after Wave 5C cutover
fdb4178e docs(daily-brief SKILL.md): correct stale daily-briefs JSON reference post Wave 5C
```

Base: `main` @ `c342013c`. Branch: `worktree-wave5c-daily-briefs`.

## Definition of Done — verified (spec's 9-item list)

1. Data migrated to SQLite/domain model. ✅ (11 real `REVIEW_DAILY` rows)
2. Real producers write SQLite/domain repositories. ✅ (`daily_brief.py`, confirmed live)
3. Real consumers read SQLite/domain repositories. ✅ (`dailybrief.ts`, `generate_reports.py`)
4. Old JSON/JSONL runtime references removed or rewritten. ✅ (zero live reads remain)
5. SKILL.md/agent/plugin instructions no longer point at old JSON. ✅ (`daily-brief/SKILL.md`)
6. Context-bundler no longer needs retired JSON files. ✅ (1 stale reference → 0)
7. Old JSON archived (local-only `mv`, gitignored). ✅ (11 files in `ARCHIVE/`)
8. Tests prove live path behavior against real data. ✅ (real-cycle parity, real-data write
   verification, real running-backend live-path check)
9. JSON file count and context-bundle footprint reported before/after. ✅ (this table)

## Context Bundle Completion Bar

`daily-brief/SKILL.md`: 1 stale reference (JSON output path, sole-source description) → 0 (now
describes the ledger write, with the legacy JSON export noted as non-authoritative).
