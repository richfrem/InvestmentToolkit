# Wave 5C Handoff — Daily Briefs

**Status:** Complete, PR pending review/merge. Do not start Wave 5D until this PR is reviewed and
merged, and the post-merge closeout playbook has run (see below).

## Accomplishments

- Closed ADR-029's debt for the `data/daily-briefs/*.json` domain — genuinely, not just
  code-relocated: producer's dual-write already existed but had never landed real rows (0 in
  main's `intelligence.sqlite`); backfilled 10 real historical snapshots + 1 real live run = 11
  rows, independently re-verified in both `intelligence.sqlite` and `observations.jsonl`. All 2
  real consumers (`dailybrief.ts`, `generate_reports.py`) cut over, fallback branches removed,
  file archived (local-only `mv`, gitignored).
- **Real data migration executed and verified**, matching Wave 5B's discipline: dry-run → explicit
  user sign-off → real write (10/10 rows, both stores) → independent re-verification against
  main's actual `intelligence.sqlite`/`observations.jsonl` (fresh queries, not the script's own
  report) → confirmed both real consumers read the populated ledger correctly.
- **A real anti-bypass violation was found and fixed** (not carried forward): `query_ledger_brief.py`
  had raw `sqlite3.connect()` + inline SQL for 2 of its 3 modes. Closed by adding
  `list_active_events_by_type()` to `event_repository.py`.
- **A real consumer the design spec's own inventory missed was found and cut over**:
  `dailybrief.ts` (3 route handlers) — spec §4 only listed `generate_reports.py`. This is the
  inverse of Wave 5B's `evolution_events.py` false-positive finding (a real consumer the inventory
  missed, not a claimed one that wasn't real) — both directions of inventory error are now on
  record for this migration.
- Real-cycle parity test: one live `daily_brief.py` run, byte-identical diff between the JSON
  export and the ledger's `payload_json` for the same date.
- Physically-executed rollback exercise (throwaway worktree, discarded): clean `git revert`, zero
  conflicts, restored files correctly re-read by reverted code, 21/21 pre-wave tests passing.
- Final whole-branch review: zero Critical/Important findings, 3 known Minor items (cosmetic,
  non-blocking).
- Process note for future waves: unrelated to this wave's plan, a real UI bug (`PriceSourceBadge.tsx`
  mislabeling the SQLite-backed `price_source` as "yfinance") was found and fixed mid-session in
  its own separate branch/PR (#96) — kept fully out of this wave's branch/plan/scope, per the
  worktree-isolation discipline. Also handled several ad-hoc watchlist removal requests
  (`is_watchlisted` flips in `domain_model.sqlite`) directly against main, outside any worktree,
  since those are data edits, not code changes.

## JSON Reduction

11 files archived (`data/daily-briefs/*.json`, local-only `mv`), 0 active.

## Files Archived

- `ARCHIVE/investment_screener/backend/data/daily-briefs/*.json` (11 files, local `mv`, main
  checkout only, never staged/committed — gitignored source).

## Remaining Waves

Per `docs/superpowers/plans/2026-07-19-domain-data-model-v3-implementation-plan.md`:

- **Wave 5D — Predictions** (`predictions.jsonl`, `predictions_graded.jsonl` →
  `intelligence_event` `PREDICTION_CLAIM`/`PREDICTION_GRADED`, widening the existing live CHECK
  constraint with the existing 80 rows intact). Given this wave's and Wave 5B's experience (both
  domains claimed "code wired but no real test" and both turned out to need a real backfill write),
  budget for a real data migration task in the plan from the start rather than treating it as an
  open question.
- **Wave 5E — Account/Portfolio Policy** (`account_policy.json` → `portfolio_policy`).
- **Wave 6 — Program Closure & Architecture Reconciliation** (after all functional waves merge).

## Open Issues

None blocking. 3 Minor/cosmetic notes from the final review not actioned (inline-import repetition
in `query_ledger_brief.py`, minor test duplication in `test_daily_brief_review_daily_dual_write.py`,
an imprecise docstring phrase in `daily_brief.py::_load_yesterday()`) — low priority, safe to pick
up opportunistically in a future wave touching those files.

## KPI Summary

See the full table in `docs/superpowers/status/wave5c-daily-briefs-report.md`. Headline: 11 JSON
files archived, 0→11 real `REVIEW_DAILY` rows in main's DB (10 backfilled + 1 real live run), 2 of
2 real consumers now ledger-only (including one the design spec's own inventory had missed), 1
anti-bypass violation found and fixed, 8 commits, all task reviews and the final whole-branch
review clean.

## Exact Branch/Commit References

- Branch: `worktree-wave5c-daily-briefs`
- Base: `main` @ `c342013c`
- Commits: `bc60aa92`, `aebdd2ec`, `641d56a5`, `26c04bda`, `9349c2ec`, `9b309d2e`, `8f42b00e`,
  `fdb4178e`
- Worktree path (local only, not portable): `.claude/worktrees/wave5c-daily-briefs`

## Instructions for the Next Fresh Session

1. **Do not start Wave 5D work yet.** Wait for this wave's PR to be reviewed and merged by the
   user. Also note PR #96 (`fix-price-source-badge`, unrelated to this migration sequence) may
   still be open — check both before assuming `main` is fully current.
2. Once merged, follow `.agent/rules/git-operations.md`'s "End-of-Wave Closeout Playbook":
   `git fetch origin`, fast-forward local `main`, verify the merged commit is an ancestor,
   **re-run the real migration's row-count verification directly against the now-updated main
   checkout one more time** (`SELECT COUNT(*) FROM intelligence_event WHERE
   event_type='REVIEW_DAILY' AND status='ACTIVE'` — expect 11, and `grep -c '"event_type":
   "REVIEW_DAILY"' investment_screener/backend/data/observations.jsonl` — expect 11, unless a
   real `daily_brief.py` run has happened in the interim, in which case expect more and confirm it
   reconciles), remove this worktree, delete the local and remote feature branch, confirm clean
   `git worktree list` / `git branch --list`.
3. Then write Wave 5D's kickoff prompt using the same reusable template as
   `docs/superpowers/status/wave5c-kickoff-prompt.md`, updating "This Wave's Scope" and "Starting
   State" — and hand it to a fresh session to begin Wave 5D.
