# Wave 4 (Portfolio Operations) — Handoff

Status: **Complete on branch `worktree-wave4-portfolio-ops`. Pushed to `origin`. PR open,
awaiting user review/merge. Do not start Wave 5A until the user has reviewed and merged.**

## What Wave 4 Accomplished

Migrated `trade-log.json` (52 real entries), `orders_executed.jsonl` (8 real records), and
`cash_flows.json` (3 flows + 1 baseline) — all gitignored, never-committed private data — into
the v3.2 SQLite domain model's `trade_log_entry`, `order_execution`, `cash_flow`, and
`cash_flow_baseline` tables. Every real producer and consumer was cut over (see the
producer/consumer table in `wave4-portfolio-ops-report.md`), and the three JSON/JSONL files were
archived. Full detail, KPI table, bugs found, and validation evidence:
`docs/superpowers/status/wave4-portfolio-ops-report.md`.

**3/3 real producers migrated, 5/5 real consumers migrated** — full parity with the plan's
scope, unlike Waves 1-3 where the plan's original inventory was significantly wrong. Task 0's
fresh-code-read (done in the prior session, per the kickoff prompt's discipline) confirmed the
plan's producer/consumer counts were accurate this time.

## Real Bugs Found and Fixed

1. `trading.ts`'s `writeLog()` opened `TradeLogRepository` before `InvestmentRepository`, which
   would have permanently locked a fresh database into a narrower `investment` table schema
   missing `lifecycle_status` and other columns — caught by TDD, fixed by reordering repository
   instantiation.
2. `tv_order_id` was about to be silently dropped on cutover (the original Task 1 repository
   design excluded it as "no corresponding column"), which would have broken `trading.ts`'s
   `/modify`, `/cancel`, and `/log/sync-from-tv` routes for every order logged after this wave.
   Fixed by adding a real `tv_order_id` column via the existing `SCHEMA_EVOLUTIONS` self-heal
   mechanism, then re-running the migration to backfill the 3 historical values.

Full detail on both in the report.

## JSON Reduction / Files Archived

| File | Status |
|---|---|
| `investment_screener/backend/data/trade-log.json` | Archived (local-only `mv`, gitignored private data, never was tracked) |
| `investment_screener/backend/data/orders_executed.jsonl` | Archived (local-only `mv`, same) |
| `investment_screener/backend/data/cash_flows.json` | Archived (local-only `mv`, same) |
| `investment_screener/backend/data/cash_flows.json.example` | Archived (`git mv`, was tracked) |

3 real private-data files + 1 tracked template, all moved to
`ARCHIVE/investment_screener/backend/data/`. Rollback instructions in the report.

## Open Issues / Known Gaps

- **Full 1,431-test `py_services` suite was not run to completion this session.** It ran
  impractically slowly (network/git-log-bound unrelated tests, e.g.
  `test_backtest_report_generator.py`) and `pytest-timeout` isn't installed (blocked by the
  no-manual-`pip install` rule mid-wave). Every file this wave touched was verified via targeted
  test runs (34/34 passing) plus the full backend TS suite (128/128 passing beyond the 2
  documented baseline failures) — but a full Python suite run is recommended as a fast follow,
  either before merge if the user wants that extra confidence, or shortly after.
- **`generate_track_record_report.py`'s stale `trade-log.json` docstring line was corrected**
  this wave (confirmed dead in Task 0, the function body never read it) — no functional change.
- **`apply_portfolio_updates.py`** — Wave 3's open item, carried forward and explicitly resolved
  during Wave 4 scoping (per the kickoff prompt's instruction): confirmed genuinely out of scope
  for Wave 4 (only touches `portfolio.json` + `account_investment`, Wave 3's domain, already
  migrated). Still unmigrated from Wave 3's perspective if it turns out to be a live producer —
  worth a final confirm-and-close pass whenever Wave 3's loose end is revisited, but it is NOT
  Wave 4's or Wave 5's responsibility per the domain boundaries established.
- **CLAUDE.md's "Initialize missing private data" rule** (rule #13, copies `.example` files for
  missing gitignored data) is now stale for `cash_flows.json` specifically — that workflow is
  retired; `cash_flow_cli.py --add` is the real replacement going forward. Worth a small doc
  update to CLAUDE.md itself at some point (not done this wave, out of scope for a migration
  wave to edit root instructions files).

## Wave KPI Summary

See the full table in `wave4-portfolio-ops-report.md`. Headline: 3/3 producers, 5/5 consumers,
2 real bugs found and fixed, 52+8+3+1 rows migrated and independently verified 3 separate ways,
0 net test regressions.

## Remaining Migration Waves (from the approved overall implementation plan)

Per `docs/superpowers/plans/2026-07-19-domain-data-model-v3-implementation-plan.md`:

- **Wave 5A** — Generated Research Views (closes root-cause debt from the prior effort). Not started.
- **Wave 5B** — TA Sweep Results. Not started.
- **Wave 5C** — Daily Briefs. Not started.
- **Wave 5D** — Predictions. Not started.
- **Wave 5E** — Account/Portfolio Policy. Not started.

## Exact Branch/Commit References

- Branch: `worktree-wave4-portfolio-ops` (based on `main` @ `f6e82860`)
- Local `HEAD`: `6d17c96e` — `chore(wave4): archive migrated JSON/JSONL files`
- Pushed to `origin/worktree-wave4-portfolio-ops` — verify with
  `git rev-parse HEAD` vs. `git ls-remote origin worktree-wave4-portfolio-ops` before trusting
  this is current (verified matching at time of this handoff — see final report message).
- PR: opened against `main`, **not merged** — awaiting user review per this repo's standing
  PR-review-then-merge-by-user policy (CLAUDE.md rule #15).
- Base (Wave 3 merge point): `28398419` on `main`.

## Instructions for the Next Fresh Session

1. **Do not start Wave 5A** until the user has reviewed and merged this wave's PR.
2. **After the user says the PR is merged**: follow `.agent/rules/git-operations.md`'s
   "End-of-Wave Closeout Playbook" exactly, per CLAUDE.md rule #15 — `git fetch origin`, fast-
   forward local `main`, verify the merge commit is an ancestor
   (`git merge-base --is-ancestor <branch-tip> main`), remove this worktree
   (`ExitWorktree action: "remove"`), delete both the local and remote feature branch
   (`worktree-wave4-portfolio-ops`), confirm clean `git worktree list`/`git branch --list`. This
   step is mandatory completion, not optional cleanup — do not skip it and do not start Wave 5A
   before it's done.
3. **If starting Wave 5A** (only after step 2 is complete): follow the same reusable "Way of
   Working" template from `docs/superpowers/status/wave4-kickoff-prompt.md` — re-read the real
   current code for generated research views' producers/consumers fresh (do not trust the overall
   plan's original estimates; every wave so far has found them wrong to some degree, though Wave 4
   was the first wave where they turned out accurate). Write a fresh
   `docs/superpowers/status/wave5a-kickoff-prompt.md` before starting, mirroring Wave 4's kickoff
   prompt structure.
4. **Real data caveat carried forward**: `domain_model.sqlite` is gitignored — a fresh checkout
   needs `initialize_db()` + re-running the Wave 1/2/3/4 migration scripts in order (Wave 3's
   holdings data specifically needs a live broker re-sync, not a replay — no offline migration
   script exists for it, same caveat as Wave 3's own handoff noted).
5. **Full Python test suite recommendation carried forward from this wave's Open Issues**: if a
   future session has more time budget, run the full `py_services` suite to completion (possibly
   with `pytest -x --timeout` after adding `pytest-timeout` via the proper
   `requirements.in` → `pip-compile` flow) to close the gap this wave left open.
