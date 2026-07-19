# Cleanup Execution Report — SQLite Intelligence Ledger Migration

Final report for the Cleanup Readiness and Retirement Phase, executed on `main` after PR #82
merged. See `cleanup-execution-plan.md` for the full retirement inventory and classification
rationale this report follows.

## Retired Assets

**None.** The retirement inventory (`cleanup-execution-plan.md`) classified every asset this
migration touches; zero items qualified as `SAFE TO RETIRE`. Nothing was moved to `ARCHIVE/` and
nothing was deleted. This is the correct, evidence-based outcome of the dual-write/fallback
architecture this effort has deliberately preserved at every phase — not a shortfall in the
review.

## Retained Assets

| Asset | Classification | Rationale |
|---|---|---|
| `observations.jsonl` | RETAIN AS AUTHORITATIVE SOURCE | Sole source of truth; every future ledger event appends here |
| `research/archive/*.md` (80 files) | RETAIN AS AUTHORITATIVE SOURCE | Doubles as the documented rollback anchor |
| `research/{TICKER}.summary.md`/`.timeline.md` (144 files) | RETAIN FOR COMPATIBILITY | `docs.ts` reads these from disk directly today; removing them reproduces the exact 404 bug fixed this session |
| `research/{TICKER}.md` (72 bare files) | RETAIN FOR COMPATIBILITY | Only content for tickers outside ledger coverage; pre-existing, unrelated to this migration |
| Dual-write JSON paths (`ta_sweep_batch.py`, `compute_conviction_scores.py`, `daily_brief.py`, `dailybrief.ts`, `docs.ts`) | RETAIN FOR COMPATIBILITY | Explicitly protected safety net, standing instruction across every phase |
| Migration/rebuild tooling (`rebuild_db.py`, `migrate_research_to_ledger.py`, `migrate_research_report_pointers.py`, `render_all_ticker_views.py`) | RETAIN AS AUTHORITATIVE TOOLING | Required to re-run the physically-exercised rollback/rebuild procedure |
| `PANW`/`SKHY`/`INTC_DEBUG.md` pointers | RETAIN FOR BUSINESS DECISION | Pre-existing, predate this migration; disposition documented, not fixed |
| `evolution_events.py` | RETAIN FOR BUSINESS DECISION | Needs its own ADR before migration; explicitly out of scope |

## Rationale Summary

Cleanup readiness was proven (rebuild, rollback, fallback correctness, data durability — all
with evidence, not assertion), but *readiness* to clean up and *having something ready to clean
up* are different questions. This phase answered the second question honestly: within this
migration's actual footprint, nothing has been fully superseded in a way that makes removing it
safe. The generated view files and dual-write paths are still load-bearing for the live
application today; retiring either would reintroduce bugs already fixed this session, not remove
dead weight.

## Validation Results

Run fresh, in the `main` checkout (not a worktree), after the retirement inventory concluded
there was nothing to execute — confirming no regression was introduced by any commit in this
phase (the `.gitignore`/`ARCHIVE/` tracking fix, the retirement inventory doc):

- **`run_tests.py`** (T0/T0.5 gate): all gates passed, including map-debt audit, stale-path
  regression, and CWD/symlink invariance checks.
- **Ledger rebuild, from a genuinely empty state**: `main`'s checkout had never had a real
  `intelligence.sqlite` built in it before this check (it's correctly gitignored, so it never
  travels via `git merge` — only the now-committed `observations.jsonl` does). Ran
  `rebuild_db.run_rebuild()` from nothing: `{'ledger_valid_lines': 80, 'projected_rows': 80,
  'skipped': 0, 'verified': True}`. Compared every row against `observations.jsonl` directly by
  `(ticker, effective_at) → body_markdown`: **0 content differences** across all 80 events. This
  is a stronger proof than earlier rebuild checks this session, since there was no pre-existing
  local artifact to fall back on — a true cold-start reconstruction.
- **Research retrieval — Python bridge**: `query_ledger_research.py --get AAPL_2026-05-02.md` →
  real content, 3840 chars.
- **Research retrieval — `docs.ts` layer**: rebuilt `dist/`, then exercised both paths for real:
  the ledger primary path (`queryLatestResearchFromLedger`) for `AAPL_2026-05-02.md` and
  `OKLO_2026-05-02.md` — both returned real content; the disk-fallback path (this session's fix)
  for `AAPL.summary.md`, `OKLO.summary.md`, `PLTR.summary.md` — all three read successfully.
- **Full Python test suite**: 1214 passed, 24 failed, 2 xfailed. This is 2 more failures than
  the previously-confirmed-stable 22 — investigated individually, not waved away:
  - `test_order_execution_audit_trail.py::test_log_order_execution_does_not_touch_real_orders_executed_file`
    — asserts a specific file doesn't exist on disk; it does, because this is a live checkout
    with real trading history (`data/orders_executed.jsonl` from actual toolkit use). An
    environment assumption the test makes, unrelated to anything this session touched.
  - `test_place_order_gates.py::test_size_cap_exits_3` — gated on `TV_AVAILABLE`
    (`@pytest.mark.skipif`); not skipped because TradingView Desktop is actually reachable on
    this machine right now, so the test ran against real, live account state and hit a real
    insufficient-balance gate before the size-cap gate it's testing for. Depends entirely on
    live account balance, unrelated to this migration.
  - Neither test touches any file or code path this session's commits modified. The remaining
    22 failures are the same earnings/yfinance-network tests confirmed pre-existing and unrelated
    throughout this entire session.
  - **Migration/intelligence-specific subset, run in isolation**: 31/31 passed.
- **TS suite**: same single pre-existing, unrelated `zod-schemas.spec.ts` failure confirmed
  throughout this session; no new TS failures.

## Rollback Approach

Unchanged and unaffected by this phase, since nothing was retired. The physically-exercised
procedure documented in `rollback-exercise-report.md` remains valid: restore `projections/` to
the pre-migration commit, move `research/archive/*.md` back to `research/`, remove the generated
views, remove `observations.jsonl` and `intelligence.sqlite`. All source files that procedure
depends on (`research/archive/`, the migration/rebuild scripts) are retained per this report.

## Final Repository State

- `main` is at the head of PR #82 plus this phase's 2 commits (`.gitignore`/`ARCHIVE/` tracking
  fix, `cleanup-execution-plan.md`) — both pushed and verified on `origin/main`.
- No assets retired, moved, or deleted.
- `observations.jsonl`, `research/archive/`, and now `ARCHIVE/` (previously local-only) are all
  durably git-tracked.
- Rebuild, rollback, and fallback correctness re-confirmed with fresh evidence in this checkout,
  not re-asserted from prior runs.

## Conclusion

The migration is complete, certified, and merged. This cleanup phase found nothing safe to
retire — an honest outcome given the dual-write/fallback architecture is still intentionally
load-bearing, not a stopping point that was skipped. The two new test failures encountered
during validation were investigated individually and confirmed unrelated to this work before
being excluded from the pass/fail verdict, per the requirement not to wave away unexpected
results.
