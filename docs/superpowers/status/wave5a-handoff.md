# Wave 5A Handoff — Generated Research Views

**Status:** Complete, PR pending review/merge. Do not start Wave 5B until this PR is reviewed and
merged, and the post-merge closeout playbook has run (see below).

## Accomplishments

- Removed the last piece of ADR-029's root-cause debt in the research-report domain: `docs.ts`'s
  `GET /research/:filename` route no longer falls back to a legacy filesystem read for dated
  research filenames. It queries `intelligence_event` unconditionally via a newly extracted,
  directly-testable `getResearchReport()` function.
- Confirmed (not assumed) that the producer side of this domain was already fully live —
  `stock-research` skill → `intelligence.event_store` — no producer work was needed this wave.
- Confirmed the fs-fallback was already fully dead in practice (0 dated-shape files remain on
  disk), meaning this wave closed a latent risk (stale-content-serving / infra-error-masking), not
  an active production bug.
- Added 5 new unit tests, including a regression test that specifically proves a stale on-disk
  file with no matching ledger row is never served.
- Full backend suite: 133 passing / 2 failing, matching the pre-existing documented baseline
  exactly. No regressions.

## JSON Reduction

None this wave — this domain's data was already SQLite-resident before Wave 5A began; the gap was
purely in the read-path code, not the data layer. 0 JSON/JSONL files touched or archived.

## Files Archived

None. No archival was applicable to this wave's scope.

## Remaining Waves

Per `docs/superpowers/plans/2026-07-19-domain-data-model-v3-implementation-plan.md`:

- **Wave 5B — TA Sweep Results** (`ta-sweep-results.json` → `intelligence_event`
  `TECHNICAL_SWEEP`). Plan explicitly warns: prior effort's status docs claim "code wired, never
  exercised" — do not trust that claim, re-verify producer/consumer/archive from scratch.
- **Wave 5C — Daily Briefs** (`data/daily-briefs/*.json` → `intelligence_event` `REVIEW_DAILY`).
  Same re-verification requirement; "code wired but no real test exists" per prior effort's own
  status doc — write the missing real test before claiming done.
- **Wave 5D — Predictions** (`predictions.jsonl`, `predictions_graded.jsonl` →
  `intelligence_event` `PREDICTION_CLAIM`/`PREDICTION_GRADED`, widening the existing live CHECK
  constraint with 80 existing rows intact).
- **Wave 5E — Account/Portfolio Policy** (`account_policy.json` → `portfolio_policy`, 4 numeric +
  2 JSON rule-blob columns, pre-approved exception).
- **Wave 6 — Program Closure & Architecture Reconciliation** (after all functional waves merge).

## Open Issues

None blocking. One Minor code-quality note surfaced and fixed during this wave (stale log-message
wording, commit `51b40c8e`) — no open follow-up needed.

## KPI Summary

See the full table in `docs/superpowers/status/wave5a-generated-research-views-report.md`. Headline:
1 dead fallback branch removed, 1 consumer now reads SQLite unconditionally, 5 new tests, 0 new
test regressions.

## Exact Branch/Commit References

- Branch: `worktree-wave5a-generated-research-views`
- Base: `main` @ `e49de1ec`
- Commits: `9117dc3c`, `51b40c8e`
- Worktree path (local only, not portable): `.claude/worktrees/wave5a-generated-research-views`

## Instructions for the Next Fresh Session

1. **Do not start Wave 5B work yet.** Wait for this wave's PR to be reviewed and merged by the
   user.
2. Once merged, follow `.agent/rules/git-operations.md`'s "End-of-Wave Closeout Playbook":
   `git fetch origin`, fast-forward local `main`, verify the merged commit is an ancestor of
   `main`, remove this worktree, delete the local and remote feature branch, confirm clean
   `git worktree list` / `git branch --list`. **Note for this wave specifically:** there is no
   real-data-migration row-count re-verification step to run post-merge (this wave made no data
   writes) — skip that sub-step, it does not apply here, unlike Wave 3/4's closeout.
3. Then write Wave 5B's kickoff prompt using the same reusable template as
   `docs/superpowers/status/wave5a-kickoff-prompt.md`, updating only "This Wave's Scope" and
   "Starting State" — and hand it to a fresh session to begin Wave 5B.
