# Wave 5A Kickoff Prompt — Domain Data Model v3.2 Migration

Hand this whole file to a fresh Claude Code session (new context, no prior memory of this
migration) to start Wave 5A. The "Way of Working" section below is the reusable template —
copy it forward unchanged for Wave 5B–5E; only the "This Wave's Scope" and "Starting State"
sections need updating per wave.

---

## Read These First, In Order

1. `docs/superpowers/specs/2026-07-19-domain-data-model-v3-implementation-design.md` — the
   overall spec: non-negotiable goal (reduce JSON, not add SQLite beside it), target
   architecture, domain classification table, hybrid exit criteria, retained-JSON rationale
   bar, stop conditions.
2. `docs/superpowers/plans/2026-07-19-domain-data-model-v3-implementation-plan.md` — the
   overall wave roadmap (Wave 0 → 1 → 2 → 3 → 4 → 5A–5E), Global Constraints (including the
   2026-07-22 addition on where real migration writes must run — read it, it is the direct
   cause of this kickoff prompt's new Setup step below), Definition of Done, Wave KPI table
   template — all binding on every wave, not just Wave 1.
3. `docs/superpowers/status/wave4-handoff.md` and `docs/superpowers/status/wave4-portfolio-ops-report.md` —
   the most recent wave's outcome: KPI table, producer/consumer cutover results, real bugs
   found and fixed, validation evidence, open issues. **Match this level of rigor, not less.**
4. `.agent/map-debt.md` — read the Wave 4 entry ("Wave 4 real migration write ran against the
   worktree's DB, not main's live DB") in full. This is not optional background reading — it
   describes a real gap that reached a merged PR undetected, and Step 3's new sub-step below
   exists specifically to prevent a repeat.
5. `ADRs/030_portfolio_totals_computed_not_stored.md` — Wave 3's design decision on computed-
   vs-stored totals; the same "store facts, calculate aggregates" principle applies wherever
   Wave 5A's domain has a derivable aggregate vs. a genuine external fact.

## Way of Working (reusable every wave — do not skip steps)

### 1. Setup
- Confirm `main` is up to date (`git pull origin main`) and note the current HEAD commit —
  should include Wave 4's merge commit `c7fdad6f` and the follow-up fix commit `d1ebd33a`.
- Per this repo's CLAUDE.md rule #14, create an isolated worktree before any multi-file code
  change (`EnterWorktree` if available; if it branches from a stale ref, `git merge --ff-only
  main` inside the worktree to bring in latest `main`, verified via `git log`).
- **New, mandatory (CLAUDE.md pitfall #29):** immediately after creating the worktree, note
  that its `domain_model.sqlite` and any gitignored source data files are separate, unsynced
  copies from the main checkout's. This matters for every later step that reads or writes real
  data — plan around it now rather than discovering it at wave-exit time again.

### 2. Plan the wave (before touching code)
- Use `superpowers:writing-plans`.
- **Re-read the real, current code for every producer/consumer this wave touches — do not
  trust the overall plan's one-line file descriptions or the spec's original producer/consumer
  counts as ground truth.** Waves 1-3 each found the plan's initial assumptions wrong once real
  code was read (Wave 1: real file count 82 not 144; Wave 2: 7 of 11 claimed producers were
  never real writers; Wave 3: only 5 of 20 claimed producers were real). Wave 4 was the first
  wave where the plan's original counts turned out fully accurate (3/3 producers, 5/5
  consumers) — do not treat that as license to skip re-verification this wave; treat it as the
  exception, not the new norm.
- Write full TDD-ready detail for parts that are genuinely plannable now (schema, repository
  functions with a fixed target schema). For consumer-rewiring tasks spanning many files, it's
  fine to NOT pre-script exact code — state the real file list, the available repository
  functions, and the instruction "read this file's actual current code before editing."
- Include a **hard approval gate before any real data migration runs** (dry-run report first,
  explicit user sign-off, THEN the real write) — this is non-negotiable, tied to a real data-
  loss incident from before this corrective effort began.
- **New, mandatory:** the plan's real-write task must explicitly state it runs against the
  **main checkout's** file paths (absolute or explicitly-flagged, never a script's
  worktree-relative default), and its verification step must query the **main checkout's**
  `domain_model.sqlite` directly — not the worktree's copy, even if the write itself was
  executed from within the worktree's Python environment for convenience. State this
  distinction explicitly in the task, don't assume the implementer will infer it.
- Present the plan for user review before executing. Apply any requested revisions.

### 3. Execute the wave — wave-level autonomy (current standing instruction)
- **Do not stop after every individual task/subtask for approval.** Execute the approved wave
  plan end-to-end.
- **Do not run a separate full reviewer cycle after every small commit** unless a hard-stop
  condition (below) is triggered.
- Fix issues found along the way. Keep commits logical and reviewable (one task = one commit or
  a few, not one giant commit per wave).
- **Never trust a subagent's report at face value for anything consequential** — a producer
  rewire, a migration write, an archive step, a live-data validation claim. Dispatch independent
  verification (a reviewer subagent, or your own direct queries against real data) for anything
  touching real data or a real cutover claim. **Specifically:** if a subagent (background or
  otherwise) reports "ran the real write and verified N rows," the controller must independently
  re-run that verification query itself, in the main checkout, before accepting the claim — not
  just re-read the subagent's own transcript of doing so inside a worktree.
- Use `superpowers:subagent-driven-development`: fresh implementer subagent per task, task
  briefs extracted via `scripts/task-brief`, review packages via `scripts/review-package`. For
  Critical/Important findings, dispatch a fix subagent, then re-review — don't self-fix as the
  controller.
- **Background sub-agent session-limit risk**: this has happened in Wave 2 and Wave 3 — a
  dispatched background agent ran out of session budget mid-task. Instruct background
  dispatches to commit after every single file (not batches), and independently verify (direct
  test runs + grep) before folding any orphaned/interrupted worktree's work back in.
- **Never use bare `git stash`/`git stash pop`** — the stash stack is shared across all
  worktrees.

### Hard-Stop Conditions (stop immediately, report evidence, wait for user)
1. Source count and target row count do not reconcile.
2. Row/version/scenario count has an unexplained delta.
3. A new data shape is discovered without a test covering it.
4. A producer still writes the old JSON path as source of truth.
5. A real consumer still reads the old JSON path after claimed cutover.
6. Any script bypasses the approved repository/service layer and opens SQLite directly.
7. Tests fail in a new or migration-related way (not the documented pre-existing baseline —
   currently two known pre-existing failures: `zod-schemas.spec.ts` and an `InvestmentRepository`
   real-sqlite parity test needing a live broker-synced DB — confirmed unrelated to this
   migration as of Wave 4).
8. Archive-readiness grep still finds real runtime I/O to the old JSON path.
9. The archive step would remove rollback capability.
10. Context-bundler still requires retired files without explanation.
11. The wave would end in a permanent hybrid state.
12. **New:** the wave's exit report claims a real data migration write is verified, but that
    verification was never independently re-run against the main checkout's actual files (as
    opposed to a worktree's copy).

Before archiving anything, all of these must be independently confirmed true (not assumed):
producers cut over, all real consumers cut over, archive-readiness grep clean, repository-path
(anti-bypass) grep clean, tests pass at the documented baseline, rollback remains possible, AND
(new) the real write's row counts have been independently re-verified against the main
checkout's live `domain_model.sqlite`, not just the worktree's.
Archive with `git mv <path> ARCHIVE/<mirrored path>` — never `rm`. If the file is gitignored
private data (like `portfolio.json`/`cash_flows.json` were), archive is a **local-only `mv`**,
never `git mv`.

### 4. Wave exit
- Produce `docs/superpowers/status/wave5a-<domain>-report.md` — KPI table (JSON files
  before/after, files archived, reads/writes removed, producers/consumers migrated, plugin/
  skill/agent references updated, context-bundle files removed, remaining exceptions), producer/
  consumer cutover table, real bugs found and fixed (with evidence, not smoothed over),
  validation results (explicitly stating the real write was verified against `main`'s DB, not a
  worktree's), archive evidence, rollback instructions, commit list. Match `wave4-handoff.md`'s
  depth.
- Ensure all wave commits are on the wave branch; push; open a PR to `main` (do not merge it
  yourself unless explicitly told to — this repo's standing policy is PR-review-then-merge for
  `origin/main`).
- Verify the remote branch matches local HEAD exactly before reporting the PR as ready.
- Produce `docs/superpowers/status/wave5a-handoff.md` (accomplishments, JSON reduction, files
  archived, remaining waves, open issues, KPI summary, exact branch/commit references,
  instructions for the next fresh session).
- **Stop. Do not start the next wave.** After the user reviews/merges the PR: follow
  `.agent/rules/git-operations.md`'s "End-of-Wave Closeout Playbook" exactly — fetch, fast-
  forward `main`, verify the merged commit is an ancestor, **re-run the real migration's
  row-count verification directly against the now-updated main checkout one more time** before
  declaring the wave fully closed, remove the worktree, delete local AND remote feature
  branches, confirm clean `git worktree list`/`git branch --list` — then write the next wave's
  kickoff prompt using this same template before that next wave begins.

## This Wave's Scope (Wave 5A)

Per the overall plan, Wave 5A covers: **Generated Research Views** (closing root-cause debt from
the prior effort — see `docs/superpowers/plans/2026-07-19-domain-data-model-v3-implementation-plan.md`'s
"Waves 1 Through 5E — Roadmap" section for whatever detail exists there today; it was explicitly
marked "detailed task breakdown written immediately before each wave starts," so do not expect
a fully fleshed-out task list yet — that is this wave's Step 2 job, not something to assume is
already done).

**Known false-positive risk, per the pattern in every prior wave except Wave 4:** treat any
producer/consumer count in the overall plan/spec as unverified until Task 0 re-confirms it
against real current code. Wave 4 was the first wave where the original estimate held up
exactly — do not assume Wave 5A will be equally clean.

## Starting State (as of this handoff)

- `main` @ `d1ebd33a` (Waves 0-4 all merged: PR #91 for Wave 4, plus a same-day follow-up commit
  fixing the worktree-vs-main DB gap described above).
- `trade_log_entry`, `order_execution`, `cash_flow`, `cash_flow_baseline` tables now populated
  with real data (52/8/3+1 rows) in the **main checkout's** `domain_model.sqlite` — confirmed via
  direct query on 2026-07-22, after the Wave 4 PR merge exposed the gap this file's Setup/Step 2/
  Hard-Stop sections above were updated to prevent.
- `investment_screener/backend/data/{trade-log.json,orders_executed.jsonl,cash_flows.json}` are
  archived locally (gitignored, never committed — a fresh checkout will not have them; there is
  no offline replay script, same caveat as Wave 3's `portfolio.json`).
- `domain_model.sqlite` overall now holds Wave 0+1+2+3+4 data (gitignored, rebuildable via
  `initialize_db()` + re-running each wave's migration script in order for the static domains;
  Wave 3's holdings data specifically requires a live broker re-sync, Wave 4's requires the
  archived local JSON copies if starting from scratch on a machine that still has them).
- No worktree currently checked out for this migration — start fresh per the Setup step above.

## Do Not

- Do not start implementation before the wave plan is written and reviewed.
- Do not skip the fresh-code-read step and copy assumptions from the overall plan/spec.
- Do not run a real data migration without the dry-run-then-approval gate.
- **Do not run or verify a real data migration write anywhere other than the main checkout's
  actual files and actual `domain_model.sqlite`** — a worktree's copies are not a substitute,
  even for verification only.
- Do not archive anything before every gate in the Hard-Stop Conditions section is
  independently confirmed.
- Do not merge to `main` yourself without being told to.
- Do not start Wave 5B after this wave's exit — stop and wait for review, same as every prior
  wave.
