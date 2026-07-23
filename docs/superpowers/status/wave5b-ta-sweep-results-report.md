# Wave 5B — TA Sweep Results: Exit Report

**Branch:** `worktree-wave5b-ta-sweep-results`
**Base:** `main` @ `aef42684`
**Commits:** `2921e34c`, `ca22c1d3`, `7cb1a816`, `4995275a`, `59e710cc`, `f88b6af8`, `08b0b6fc`

## Scope

Per the overall plan (§ Wave 5B) and ADR-029: migrate `ta-sweep-results.json` →
`intelligence_event` (`TECHNICAL_SWEEP`). Unlike Wave 5A, the overall plan's warning that this
domain is "code wired, never exercised" was confirmed **accurate** — main's `intelligence.sqlite`
had zero `TECHNICAL_SWEEP` rows despite existing dual-write producer code, so this wave required a
real data migration, not just a code-path fix.

A user-requested scope addition (Task 0) was folded in mid-planning: the TA sweep only scanned
portfolio holdings (26 tickers), never the watchlist. Expanded to holdings ∪ watchlist (82 unique
tickers combined as of 2026-07-22).

## Pre-Implementation Findings (re-verified against real code/data, not the plan's one-liner)

- `ta-sweep-results.json` is **git-tracked**, not gitignored (unlike Wave 5A's domain) —
  archived via `git mv`, not local-only `mv`.
- Main checkout's `intelligence.sqlite` had **zero** `TECHNICAL_SWEEP` rows pre-wave, confirming
  the plan's "code wired, never exercised" warning was accurate for this domain.
- Three real consumer call sites, re-verified by reading each: `compute_conviction_scores.py::
  _load_ta()` and `daily_brief.py::_ta_age_hours()` (both DB-first/JSON-fallback, fallback
  untested), and `daily_brief.py::run()` (the one real consumer that never touched SQLite at all
  — re-read the JSON file the just-run subprocess wrote).
- Docs (`SKILL.md`, `README.md`) and code comments falsely claimed a `/api/ta-sweep/results`
  backend route consumed the file — confirmed false via grep, zero hits in `backend/src/routes/`
  or the frontend.
- `overnight_gaps.py::_load_tickers()` already had the exact holdings-union-watchlist pattern
  needed for Task 0 — mirrored rather than reinvented.

## Wave KPI Table

| Metric | Before | After |
|---|---|---|
| JSON files in this domain | 1 (`ta-sweep-results.json`, git-tracked) | 0 (archived to `ARCHIVE/`) |
| `TECHNICAL_SWEEP` rows in main's `intelligence.sqlite` | 0 | 26 (real backfilled historical data; next real sweep adds the expanded ~78-ticker universe) |
| Sweep scan universe | 26 tickers (portfolio holdings only) | Holdings ∪ watchlist — 82 unique combined (29 held, 80 watchlisted) minus `DEFAULT_SKIP` |
| Producers writing SQLite as default/unconditional path | 1 (wired but JSON was still the relied-upon default) | 1 (JSON now opt-in `--save-results` export only) |
| Real consumers reading SQLite unconditionally, no fallback | 0 of 3 | 3 of 3 |
| Dead/untested fallback branches removed | 2 | 0 |
| Stale doc/comment references to a nonexistent backend route | 4 | 0 |
| New scripts | — | `migrate_ta_sweep_to_ledger.py` (one-time backfill, dry-run/write) |

## Producer/Consumer Cutover Table

| Component | Pre-wave | Post-wave |
|---|---|---|
| Producer: `ta_sweep_batch.py::save_sweep_results()` | JSON write unconditional (default); SQLite write also always ran but never exercised in production | SQLite write unconditional (source of truth); JSON write opt-in only via `--save-results` |
| Consumer: `compute_conviction_scores.py::_load_ta()` | DB-first, untested JSON fallback | SQLite-only, no fallback |
| Consumer: `daily_brief.py::_ta_age_hours()` | DB-first, untested JSON fallback | SQLite-only, no fallback |
| Consumer: `daily_brief.py::run()` | Re-opened the JSON file the subprocess just wrote | Queries SQLite directly via new `_load_latest_ta_sweep_count()` |
| Scan universe (`ta_sweep_batch.py::main()`) | Holdings only | Holdings ∪ watchlist |

## Real Bugs Found and Fixed

1. **Latent risk, now closed:** two consumer functions had untested JSON-fallback branches that
   would have silently served stale/wrong data (or masked infra errors as "no data") had they
   ever fired against a populated-then-emptied JSON file. Removed in Task 3.
2. **Stale documentation:** `SKILL.md`, `README.md`, and two code comments claimed a backend
   route consumed this file — that route never existed. Corrected in Task 4.
3. **Scan-universe gap:** the sweep never covered watchlisted (not-yet-held) tickers, contrary to
   its evident purpose. Fixed in Task 0.
4. **Review-flagged robustness gap:** `_load_latest_ta_sweep_count()` (new in Task 2) lacked the
   same `os.path.exists()`/try-except guard its sibling `_ta_age_hours()` has — would have raised
   `sqlite3.OperationalError` uncaught instead of degrading gracefully. Fixed post-final-review
   in `08b0b6fc`.

## Validation Results

- All 6 task-level reviews: spec compliance ✅, task quality Approved (one cosmetic-only nitpick
  on Task 4, no action needed).
- Final whole-branch review: **Ready to merge — Yes.** No Critical findings. One Important
  finding (defensive-guard gap, above) — fixed and independently diff-verified. Two Minor/cosmetic
  notes, not actioned (docstring wording, an existing test-isolation sentinel worth a comment).
- Targeted test suites, all passing:
  - `test_migrate_ta_sweep_to_ledger.py` + `test_compute_conviction_scores.py` +
    `test_daily_brief_ta_sweep_delegates.py` (run from repo root — one file has a known
    pre-existing relative-path dependency): **32/32 passing**, plus the post-review fix's
    re-verification: **5/5 passing** for the daily_brief file alone.
  - `test_ta_sweep_batch.py`: **23/23 passing**.
- Full Node backend suite (`npm run test -w backend`): **133 passing / 2 failing**, matching the
  documented pre-existing baseline exactly (`zod-schemas.spec.ts`, `InvestmentRepository`
  real-sqlite parity test) — confirmed unrelated, no new regressions.
- The full repo-wide `py_services` pytest suite was attempted but did not complete within a
  9-minute background budget (likely an unrelated slow/network-bound test elsewhere in that
  directory, not in any file this wave touched) — not run to completion; relying instead on the
  targeted suites above, which cover every file this wave modified, all passing.

## Real Data Migration — Full Evidence Trail

1. **Dry-run** against main checkout's real files: `{"source_count": 26, "written_count": 0,
   "skipped": []}`.
2. **User sign-off obtained explicitly** before the real write.
3. **Real write**: `{"source_count": 26, "written_count": 26, "skipped": []}`.
4. **Independent re-verification** (fresh, separate query against main's actual
   `intelligence.sqlite`, not the script's own reported output): `TECHNICAL_SWEEP` ACTIVE rows =
   26, matching the source file's `count` field exactly. Hard-Stop Condition #1 (count
   reconciliation) clear.
5. **Real consumer confirmed reading the populated DB**: `compute_conviction_scores.py::_load_ta()`
   called directly against main's DB, returned all 26 tickers.
6. **Known, accepted data artifact:** the backfilled events' `ingested_at` is the migration run
   time (2026-07-22), not the original scan date (2026-07-10), so `_load_ta()`'s staleness
   calculation reads `0` days rather than the true `~12` for these rows. This is a one-time
   artifact of historical backfill (real-time sweeps always have `ingested_at` ≈ `effective_at`,
   so this gap self-corrects the moment the next real TradingView-driven sweep runs). Not a
   defect, not blocking.

## Archive Evidence

`git mv investment_screener/backend/data/ta-sweep-results.json
ARCHIVE/investment_screener/backend/data/ta-sweep-results.json` (commit `f88b6af8`) — file is
git-tracked, correct convention per the plan (unlike Wave 5A's/Wave 3's gitignored-domain
exception).

**Process note:** the archive `git mv` was first, mistakenly, run directly against the main
checkout's working tree outside the worktree/PR flow. Caught immediately, fully reverted
(`git restore --staged` + file moved back, verified byte-identical via `ls`/`git status`), and
redone correctly on the worktree branch so it lands in this PR's diff instead. No lasting effect
on `main` — confirmed clean before proceeding.

## Rollback Instructions

`git revert 08b0b6fc f88b6af8 59e710cc 4995275a 7cb1a816 ca22c1d3 2921e34c` (in that order, newest
first) restores the pre-wave code state. **Data rollback:** the 26 `TECHNICAL_SWEEP` rows written
to main's `intelligence.sqlite` are additive (idempotency-keyed, non-destructive) — to fully
roll back, delete rows where `event_type = 'TECHNICAL_SWEEP' AND source_id =
'wave5b-migration-backfill'` and restore `ta-sweep-results.json` from `ARCHIVE/` via `git mv`
back to its original path.

## Commit List

- `2921e34c` — feat(ta_sweep_batch.py): scan holdings UNION watchlist, not holdings only
- `ca22c1d3` — feat(wave5b): add ta-sweep-results.json ledger backfill migration script
- `7cb1a816` — fix(daily_brief.py): read post-sweep TA count from SQLite, not ta-sweep-results.json
- `4995275a` — fix(wave5b): remove dead JSON-fallback branches in _load_ta/_ta_age_hours
- `59e710cc` — fix(ta_sweep_batch.py): JSON export opt-in only, SQLite/ledger write is default
- `f88b6af8` — chore(wave5b): archive ta-sweep-results.json after verified TECHNICAL_SWEEP migration
- `08b0b6fc` — fix(daily_brief.py): guard _load_latest_ta_sweep_count() with try/except (review fix)

## Remaining Exceptions

None new. Pre-existing test-suite baseline exceptions unchanged.
