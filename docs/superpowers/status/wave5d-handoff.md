# Wave 5D — Predictions Migration Handoff

## Accomplishments

Predictions domain fully migrated per ADR-029's 3-part definition: producer writes SQLite +
every real consumer reads SQLite + old file archived via `git mv`. See
`wave5d-predictions-report.md` for full evidence. Highlights:

- CHECK-constraint widening (first Wave 5 sub-wave requiring one), tested rebuild-and-copy, no
  data loss to the pre-existing 196 rows.
- 87-row real backfill, independently verified against `main` twice (once before, once after a
  real bug repair).
- **A real data-quality bug found and repaired on real, already-committed data**: `claimDate` vs
  `date` field mismatch corrupted all 87 backfilled rows' `effective_at`/title; found by the
  real-cycle parity check, fixed at the source (3 code sites) and repaired on `main` directly.
- **A 7th real consumer the design spec's inventory missed** (`alert_manager.py::link_alert_to_claim()`)
  was found via the archive-prerequisite grep and cut over before archiving proceeded — the exact
  discipline Hard-Stop Condition 9 exists to enforce.
- Physically-executed rollback exercise (2 commits reverted, not 1 — Task 3 independently changed
  a producer signature Task 2 introduced).

## JSON Reduction

1 file archived (`predictions.jsonl`), 0 active JSON/JSONL for this domain going forward.

## Remaining Waves

Per `docs/superpowers/plans/2026-07-19-domain-data-model-v3-implementation-plan.md`:

- **Wave 5E — Account/Portfolio Policy**: `account_policy.json` → `portfolio_policy` (4 numeric
  columns + 2 JSON rule-blob columns, already-justified exception per spec §2.14/§2.17).
- **Wave 6 — Program Closure & Architecture Reconciliation**: runs only after Wave 5E merges.
  Architecture documentation reconciliation, agent/onboarding reconciliation, retained-JSON
  reassessment (including the `target-portfolio.json`/`ThesisService.ts` pre-analysis already done
  2026-07-24, ahead of Wave 6 starting), final migration audit, architecture simplification review.

## Open Issues / Carry-Forward Notes for Wave 5E

- **Test baseline is wider than any wave plan has stated.** The full `py_services` suite currently
  shows **45 failing tests**, all independently confirmed unrelated to Wave 5D (order-execution,
  place-order, portfolio_action, ta-sweep-real-data domains; plus the already-documented
  `mock_date` NameErrors and one beat-rate logic bug). Wave 5E's plan should state this real number
  as its baseline, not the stale "2 known failures" figure this migration's docs have repeated
  since Wave 5A. Two additionally-confirmed-hanging test files
  (`test_backtest_report_generator.py`, `test_backtest_round_trips_json.py`) should be excluded
  from any full-suite run via `--deselect`, not investigated as part of Wave 5E's own scope.
- **A fresh worktree for this migration needs more environment setup than CLAUDE.md's checklist
  currently states.** This wave's worktree required, beyond `npm install` for `investment_screener/`:
  (1) `npm ci` in `tradingview-cdp/` (a separate workspace, not covered by the root `npm install`);
  (2) copying the entirely-gitignored `.agents/` directory from the main checkout (it holds the
  self-evolution/map-debt tooling `run_tests.py`'s T0 gate depends on — no worktree has ever synced
  it via git, since it was never committed); (3) initializing `portfolio.json`/`portfolio-config.json`
  from their `.example` files per CLAUDE.md rule 13. None of these are Wave 5D code changes — they
  are one-time environment setup this specific worktree needed before `python3 run_tests.py` could
  pass. Recommend either documenting this in CLAUDE.md's fresh-worktree checklist or a small setup
  script, so Wave 5E's kickoff doesn't rediscover the same gaps from scratch.
- The `DEFAULT_INTEL_DB_PATH` off-by-one bug fixed in `generate_track_record_report.py` this wave
  was a real, if narrowly-scoped, lesson: any new `py_services/` file computing its own repo-root-
  relative default path should cross-check against an already-correct sibling constant (e.g.
  `backtest_harness.py`'s `DATA_DIR`) rather than re-deriving the `.parents[]` offset from scratch.

## KPI Summary

| KPI | Value |
|---|---|
| JSON/JSONL files before this wave | 1 |
| JSON/JSONL files after this wave | 0 |
| Files archived | 1 |
| Producers migrated | 1/1 |
| Consumers migrated | 7/7 (design spec's stated 6 + 1 found this wave) |
| Real data rows migrated | 87 |
| Real bugs found and fixed | 4 (see exit report) |

## Exact Branch/Commit References

- Wave branch: `worktree-wave5d-predictions`, based on `main` @ `08c51479`.
- Wave code commits: `e4481287` through `6d384f2b` (16 commits, see exit report's Commit List).
- Real-data commits (directly on `main`, separate from the wave branch): `37fc909c` (initial
  backfill), `f6b2b2f1` (repair of the `claimDate`/`date` bug).
- PR: opened against `main` from `worktree-wave5d-predictions` — **not merged by this session**,
  awaiting user review per standing policy.

## Instructions for the Next Fresh Session

1. **Do not start Wave 5E work until this PR is reviewed and merged by the user.**
2. Once merged: follow `.agent/rules/git-operations.md`'s End-of-Wave Closeout Playbook — fetch,
   fast-forward local `main` to `origin/main`, verify the merged commit is an ancestor, **re-run
   the row-count verification one more time** (`observations.jsonl` line count, `intelligence.sqlite`
   `PREDICTION_CLAIM` count, both should read 283 total / 87 `PREDICTION_CLAIM` against the
   now-updated main checkout), remove the `wave5d-predictions` worktree, delete both the local and
   remote `worktree-wave5d-predictions` branch, confirm clean `git worktree list`/`git branch --list`.
3. Only then write Wave 5E's kickoff prompt, using this same template
   (`docs/superpowers/status/wave5d-kickoff-prompt.md` as the structural reference) with Wave 5E's
   own scope (`account_policy.json` → `portfolio_policy`) and this handoff's Open Issues section
   folded into its Starting State.
4. Carry forward the wider real test baseline (45 failures, itemized above) into Wave 5E's plan
   document, rather than repeating the stale "2 known failures" figure.
