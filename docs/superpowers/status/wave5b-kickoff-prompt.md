# Wave 5B Kickoff Prompt — Domain Data Model v3.2 Migration

Hand this whole file to a fresh Claude Code session (new context, no prior memory of this
migration) to start Wave 5B. The "Way of Working" section below is the reusable template —
copy it forward unchanged for Wave 5C–5E; only the "This Wave's Scope" and "Starting State"
sections need updating per wave.

---

## Read These First, In Order

1. `docs/superpowers/specs/2026-07-19-domain-data-model-v3-implementation-design.md` — the
   overall spec: non-negotiable goal (reduce JSON, not add SQLite beside it), target
   architecture, domain classification table, hybrid exit criteria, retained-JSON rationale
   bar, stop conditions.
2. `docs/superpowers/plans/2026-07-19-domain-data-model-v3-implementation-plan.md` — the
   overall wave roadmap (Wave 0 → 1 → 2 → 3 → 4 → 5A–5E), Global Constraints (including the
   2026-07-22 addition on where real migration writes must run), Definition of Done, Wave KPI
   table template — all binding on every wave, not just Wave 1. See its "Wave 5B — TA Sweep
   Results" section specifically.
3. `docs/superpowers/status/wave5a-generated-research-views-report.md` and
   `docs/superpowers/status/wave5a-handoff.md` — the most recent wave's outcome: KPI table,
   producer/consumer cutover results, real bugs found and fixed (none this time — the risk was
   latent, not active), validation evidence, open issues. **Match this level of rigor, not
   less.** Note Wave 5A made **no real data-migration write** (the domain's data was already
   SQLite-resident; the gap was purely a dead code path) — Wave 5B is different: `ta-sweep-
   results.json` is a real file that will need migrating, so the worktree-vs-main DB discipline
   below is fully live again for this wave.
4. `.agent/map-debt.md` — read the Wave 4 entry ("Wave 4 real migration write ran against the
   worktree's DB, not main's live DB") in full. This is not optional background reading — it
   describes a real gap that reached a merged PR undetected, and Step 3's new sub-step below
   exists specifically to prevent a repeat. This applies directly to Wave 5B since it involves a
   real data write, unlike Wave 5A.
5. `ADRs/029_persistence_domain_rationalization_and_retirement_gated_migration.md` — the
   ADR that defines what "migrated" means (producer writes SQLite + every real consumer reads
   SQLite + old file archived) and explicitly warns that prior status docs for this exact
   research/TA/briefs domain family have falsely claimed completion before ("migration complete"
   claimed while the live app never queried SQLite at runtime). Wave 5B's scope note below
   repeats this warning for a reason — take it literally.
6. `ADRs/030_portfolio_totals_computed_not_stored.md` — Wave 3's design decision on computed-
   vs-stored totals; the same "store facts, calculate aggregates" principle applies wherever
   Wave 5B's domain has a derivable aggregate vs. a genuine external fact.

## Way of Working (reusable every wave — do not skip steps)

### 1. Setup
- Confirm `main` is up to date (`git pull origin main`) and note the current HEAD commit —
  should include Wave 5A's merge commit `0438e970`.
- Per this repo's CLAUDE.md rule #14, create an isolated worktree before any multi-file code
  change (`EnterWorktree` if available; if it branches from a stale ref, `git merge --ff-only
  main` inside the worktree to bring in latest `main`, verified via `git log`).
- **Mandatory (CLAUDE.md pitfall #29):** immediately after creating the worktree, note that its
  `domain_model.sqlite` / `intelligence.sqlite` and any gitignored source data files are
  separate, unsynced copies from the main checkout's. This matters for every later step that
  reads or writes real data — plan around it now rather than discovering it at wave-exit time
  again. This is directly relevant this wave: `ta-sweep-results.json` migration will involve a
  real `--write` step.

### 2. Plan the wave (before touching code)
- Use `superpowers:writing-plans`.
- **Re-read the real, current code for every producer/consumer this wave touches — do not
  trust the overall plan's one-line file descriptions or the spec's original producer/consumer
  counts as ground truth.** Waves 1-3 each found the plan's initial assumptions wrong once real
  code was read (Wave 1: real file count 82 not 144; Wave 2: 7 of 11 claimed producers were
  never real writers; Wave 3: only 5 of 20 claimed producers were real). Wave 4 was the only
  wave where the plan's original counts turned out fully accurate — do not treat that as license
  to skip re-verification. **Wave 5B's specific instruction from the overall plan:** the prior
  effort's status docs describe this domain as "code wired, never exercised." Do not trust that
  claim — re-verify producer/consumer/archive from scratch against the Definition of Done, the
  same way ADR-029 was triggered by exactly this kind of false "migrated" claim for the
  neighboring research-report domain.
- Write full TDD-ready detail for parts that are genuinely plannable now (schema, repository
  functions with a fixed target schema). For consumer-rewiring tasks spanning many files, it's
  fine to NOT pre-script exact code — state the real file list, the available repository
  functions, and the instruction "read this file's actual current code before editing."
- Include a **hard approval gate before any real data migration runs** (dry-run report first,
  explicit user sign-off, THEN the real write) — this is non-negotiable, tied to a real data-
  loss incident from before this corrective effort began.
- **Mandatory:** the plan's real-write task must explicitly state it runs against the
  **main checkout's** file paths (absolute or explicitly-flagged, never a script's
  worktree-relative default), and its verification step must query the **main checkout's**
  SQLite file directly — not the worktree's copy, even if the write itself was executed from
  within the worktree's Python environment for convenience. State this distinction explicitly
  in the task, don't assume the implementer will infer it.
- **Mandatory, added after Wave 5B's own plan skipped this (Map Debt entry, 2026-07-22):** the
  wave plan document must include the design spec's actual required content **verbatim**, not a
  self-invented subset. Specifically, paste into the plan: (1) the design spec's "Hybrid Exit
  Criteria" section applied to this wave's domain, (2) the design spec's full §5 Validation
  Strategy checklist as literal checkboxes — including "run both paths in parallel for at least
  one full real-world cycle... and diff row-for-row" and "physically exercise rollback at least
  once per domain before declaring the wave done" (an executed exercise with evidence, not a
  prose description of what rollback *would* involve), (3) the design spec's 9-item Definition of
  Done verbatim (`docs/superpowers/plans/2026-07-19-domain-data-model-v3-implementation-plan.md`'s
  "Definition of Done (applies to every wave...)" section) — do not write a shorter wave-specific
  version, (4) a computed **Context Bundle Completion Bar** number (grep the domain's plugin/skill
  reference table from spec §4, confirm zero stale filename references remain post-wave, report
  the count). Wave 5B's task-level and final whole-branch reviews all came back clean because they
  correctly checked the diff against the plan as written — the plan itself had silently narrowed
  the bar. The `writing-plans` skill's "Spec coverage" self-review must diff the plan's section
  list against this checklist, not just re-read the plan's own text for internal consistency.
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
- **Model choice for all subagent dispatches (implementer, task reviewer, final whole-branch
  reviewer, fix subagents): Sonnet or Haiku only. Never dispatch with Opus**, even where a skill's
  generic guidance suggests "use the most capable model" for architecture-level or final reviews —
  this is a standing user instruction that overrides that skill text.
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
   migration through Wave 5A).
8. Archive-readiness grep still finds real runtime I/O to the old JSON path.
9. The archive step would remove rollback capability.
10. Context-bundler still requires retired files without explanation.
11. The wave would end in a permanent hybrid state.
12. The wave's exit report claims a real data migration write is verified, but that
    verification was never independently re-run against the main checkout's actual files (as
    opposed to a worktree's copy).
13. **New, specific to this wave's warning:** the wave's plan or exit report repeats the prior
    effort's unverified "code wired, exercised in production" claim for `ta-sweep-results.json`
    without independent re-confirmation — this is the exact failure pattern ADR-029 was written
    to correct for the neighboring research-report domain.

Before archiving anything, all of these must be independently confirmed true (not assumed):
producers cut over, all real consumers cut over, archive-readiness grep clean, repository-path
(anti-bypass) grep clean, tests pass at the documented baseline, rollback remains possible, AND
the real write's row counts have been independently re-verified against the main checkout's live
SQLite file, not just the worktree's.
Archive with `git mv <path> ARCHIVE/<mirrored path>` — never `rm`. If the file is gitignored
private data, archive is a **local-only `mv`**, never `git mv`.

### 4. Wave exit
- Produce `docs/superpowers/status/wave5b-<domain>-report.md` — KPI table (JSON files
  before/after, files archived, reads/writes removed, producers/consumers migrated, plugin/
  skill/agent references updated, context-bundle files removed, remaining exceptions), producer/
  consumer cutover table, real bugs found and fixed (with evidence, not smoothed over),
  validation results (explicitly stating the real write was verified against `main`'s DB, not a
  worktree's), archive evidence, rollback instructions, commit list. Match `wave5a-generated-
  research-views-report.md`'s depth.
- Ensure all wave commits are on the wave branch; push; open a PR to `main` (do not merge it
  yourself unless explicitly told to — this repo's standing policy is PR-review-then-merge for
  `origin/main`).
- Verify the remote branch matches local HEAD exactly before reporting the PR as ready.
- Produce `docs/superpowers/status/wave5b-handoff.md` (accomplishments, JSON reduction, files
  archived, remaining waves, open issues, KPI summary, exact branch/commit references,
  instructions for the next fresh session).
- **Stop. Do not start the next wave.** After the user reviews/merges the PR: follow
  `.agent/rules/git-operations.md`'s "End-of-Wave Closeout Playbook" exactly — fetch, fast-
  forward `main`, verify the merged commit is an ancestor, **re-run the real migration's
  row-count verification directly against the now-updated main checkout one more time** before
  declaring the wave fully closed, remove the worktree, delete local AND remote feature
  branches, confirm clean `git worktree list`/`git branch --list` — then write the next wave's
  kickoff prompt using this same template before that next wave begins.

## This Wave's Scope (Wave 5B)

Per the overall plan (`docs/superpowers/plans/2026-07-19-domain-data-model-v3-implementation-plan.md`
§ "Wave 5B — TA Sweep Results"): migrate `ta-sweep-results.json` → `intelligence_event`
(event type `TECHNICAL_SWEEP`).

**Explicit instruction from the plan, repeated here because it is this wave's central risk:** the
prior effort's status docs describe this migration as "code wired, never exercised." **Do not
trust that claim.** Re-verify producer/consumer/archive from scratch against the Definition of
Done (producer writes SQLite + every real consumer reads SQLite + old file archived via `git mv`
— table existence, data copying, or a passing fixture test do not count, per ADR-029 §1). This is
the exact same failure pattern ADR-029 was written to correct after it happened once already for
the research-report domain (which Wave 5A just finished closing) — treat this wave's producer and
consumer claims as unverified until Task 0 re-confirms each one against real, current code, not
against what any status doc says.

**Known false-positive risk, per the pattern in every prior wave except Wave 4:** treat any
producer/consumer count in the overall plan/spec as unverified until Task 0 re-confirms it
against real current code.

## Starting State (as of this handoff)

- `main` @ `0438e970` (Waves 0-5A all merged: PR #92 for Wave 5A, no follow-up commit needed —
  Wave 5A made no real data-migration write, so the worktree-vs-main DB gap that affected Wave 4
  does not apply retroactively to it).
- `investment_screener/backend/data/ta-sweep-results.json` exists in the main checkout
  (14,152 bytes as of the last commit touching it, `265556b6`) — **has not yet been inspected
  for real producer/consumer code as part of this migration effort; that is this wave's Task 0
  job, not something to assume from this file's presence or size.**
- `intelligence_event` table exists and is live (Wave 5A confirmed 80 `RESEARCH_IMPORT` /
  `ACTIVE` rows in the main checkout's `investment_screener/backend/data/intelligence.sqlite`) —
  the `TECHNICAL_SWEEP` event type this wave targets is a new type to be added to that same
  table/CHECK constraint, per the plan, not a new table.
- `domain_model.sqlite` overall now holds Wave 0+1+2+3+4 data (gitignored, rebuildable via
  `initialize_db()` + re-running each wave's migration script in order for the static domains;
  Wave 3's holdings data specifically requires a live broker re-sync, Wave 4's requires the
  archived local JSON copies if starting from scratch on a machine that still has them).
  `intelligence.sqlite` (a separate file from `domain_model.sqlite`) holds Wave 5A's ledger data
  and is the file this wave's `TECHNICAL_SWEEP` events will also live in.
- No worktree currently checked out for this migration — start fresh per the Setup step above.

## Do Not

- Do not start implementation before the wave plan is written and reviewed.
- Do not skip the fresh-code-read step and copy assumptions from the overall plan/spec — and
  specifically do not repeat the prior effort's unverified "code wired, exercised" claim without
  independently re-confirming it against real code, per this wave's central warning above.
- Do not run a real data migration without the dry-run-then-approval gate.
- **Do not run or verify a real data migration write anywhere other than the main checkout's
  actual files and actual SQLite database** — a worktree's copies are not a substitute, even for
  verification only.
- Do not archive anything before every gate in the Hard-Stop Conditions section is
  independently confirmed.
- Do not merge to `main` yourself without being told to.
- Do not dispatch any subagent (implementer, reviewer, fix) with the Opus model — Sonnet or
  Haiku only, per standing user instruction.
- Do not start Wave 5C after this wave's exit — stop and wait for review, same as every prior
  wave.
