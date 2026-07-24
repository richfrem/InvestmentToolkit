# Wave 5D Kickoff Prompt — Domain Data Model v3.2 Migration

Hand this whole file to a fresh Claude Code session (new context, no prior memory of this
migration) to start Wave 5D. The "Way of Working" section below is the reusable template —
copy it forward unchanged for Wave 5E; only the "This Wave's Scope" and "Starting State"
sections need updating per wave.

---

## Read These First, In Order

1. `docs/superpowers/specs/2026-07-19-domain-data-model-v3-implementation-design.md` — the
   overall spec: non-negotiable goal, target architecture, domain classification table, Hybrid
   Exit Criteria, §5 Validation Strategy, 9-item Definition of Done, retained-JSON rationale bar,
   stop conditions. See its "2.11 Predictions" section specifically.
2. `docs/superpowers/plans/2026-07-19-domain-data-model-v3-implementation-plan.md` — the
   overall wave roadmap and Global Constraints — **all of them**, including the three added
   2026-07-22/23 (main-checkout-only real writes; enumerate every path argument a migration
   script accepts, not just the obvious one; every wave plan must paste the spec's real
   Validation Strategy/Definition of Done/Hybrid Exit Criteria/Context Bundle Completion Bar
   verbatim, not a self-invented subset). See its "Wave 5D — Predictions" section.
3. `docs/superpowers/status/wave5c-daily-briefs-report.md` and
   `docs/superpowers/status/wave5c-handoff.md` — Wave 5C's full outcome: a real anti-bypass
   violation found and fixed (`query_ledger_brief.py`), a real consumer the design spec's own
   inventory missed (`dailybrief.ts`), a real backfill write (10 historical + 1 live run = 11
   rows) independently re-verified against both `intelligence.sqlite` and `observations.jsonl`, a
   byte-identical real-cycle parity diff, and a physically-executed rollback exercise. **Match
   this level of rigor, not less.**
4. `ADRs/029_persistence_domain_rationalization_and_retirement_gated_migration.md` — defines what
   "migrated" means and warns that prior status docs for this domain family have falsely claimed
   completion before. Wave 5B and Wave 5C both found their domain's "code wired but no real test
   exists" caveat to be **literally true** (0 real rows in main's DB despite dual-write/producer
   code existing) — not a false alarm, twice in a row. Assume the same is possible here until
   proven otherwise; do not assume it will resolve like Wave 5A's domain did (a dead-but-harmless
   code path, the one exception among four so far).
5. `ADRs/030_portfolio_totals_computed_not_stored.md` — the "store facts, calculate aggregates"
   principle. Not directly this wave's domain (predictions are individual claim/grade facts, not
   aggregates), but the architectural discipline of "computed values are what's displayed, an
   external figure is a validation check only" is the same reasoning `grade_predictions.py`'s
   accuracy math should already follow — confirm it does, don't introduce a stored/duplicated
   accuracy number as a side effect of this migration.
6. **New for this wave, read before planning:** the live `intelligence_event.event_type` CHECK
   constraint does **not** yet include `PREDICTION_CLAIM`/`PREDICTION_GRADED` — confirmed via
   direct query (see Starting State below). Every prior Wave 5 sub-wave (5A/5B/5C) migrated into
   an event type the constraint **already had**; this is the first sub-wave that requires an
   actual schema change (widening a `CHECK` constraint) to a live table that already holds 196
   real rows across three other event types. Plan the exact SQLite mechanics for this (SQLite
   doesn't support `ALTER TABLE ... ALTER CONSTRAINT` — this typically means rebuild-and-copy: new
   table with the widened constraint, copy all existing rows, drop old, rename) as its own
   sub-task with its own test, before touching any producer/consumer code.

## Way of Working (reusable every wave — do not skip steps)

### 1. Setup
- Confirm `main` is up to date (`git pull origin main`) and note the current HEAD commit —
  should include Wave 5C's merge (PR #97) and four unrelated-but-merged-in-between fixes (PRs
  #96, #98, #99, #100 — price-source badge, screener watchlist-badge default, TV watchlist cash
  symbol, PSU broker-alias root cause) — not part of this migration's wave sequence but will be
  in `main`'s history.
- Per this repo's CLAUDE.md rule #14, create an isolated worktree before any multi-file code
  change (`EnterWorktree` if available; if it branches from a stale ref, `git merge --ff-only
  main` inside the worktree to bring in latest `main`, verified via `git log`).
- **Mandatory (CLAUDE.md pitfall #29):** immediately after creating the worktree, note that its
  `domain_model.sqlite` / `intelligence.sqlite` and any gitignored source data files are
  separate, unsynced copies from the main checkout's. This wave involves a real `--write` step
  (predictions data is git-tracked, not gitignored — confirm this hasn't changed — but the
  principle still applies: plan around the worktree/main split now, not at wave-exit time).
- After `npm install`/dependency setup in a fresh worktree, remember `mocha`/`pytest` won't be
  available until you run it — a fresh worktree has no `node_modules`.

### 2. Plan the wave (before touching code)
- Use `superpowers:writing-plans`.
- **Re-read the real, current code for every producer/consumer this wave touches — do not
  trust the overall plan's one-line file descriptions or the spec's original producer/consumer
  counts as ground truth.** Every wave except Wave 4 and Wave 5A found the plan's initial
  assumptions wrong once real code was read. Wave 5C found a real consumer (`dailybrief.ts`) the
  spec's own inventory table never named — check whether this wave's domain has the same gap
  (the spec names 6 consumers for predictions; re-verify that list against a fresh grep, don't
  assume it's complete).
- **Wave 5D's specific instruction from the overall plan:** the spec says `predictions.jsonl` had
  "2 lines today" when written — as of this kickoff prompt it has 87 (real data grows; don't
  treat the spec's stale count as a red flag, but do re-derive the real current count yourself).
  `predictions_graded.jsonl` is referenced by a `GRADED_PATH` constant in `prediction_ledger.py`
  but was "not yet present on disk" per the spec — confirm whether it exists now; if still absent,
  that's a real, current fact to build the plan around (no graded-claims backfill needed if there's
  nothing to backfill), not something to assume away.
- Write full TDD-ready detail for parts that are genuinely plannable now (the CHECK-constraint
  widening migration, repository functions with a fixed target schema). For consumer-rewiring
  tasks spanning many files, it's fine to NOT pre-script exact code — state the real file list,
  the available repository functions, and the instruction "read this file's actual current code
  before editing."
- Include a **hard approval gate before any real data migration runs** (dry-run report first,
  explicit user sign-off, THEN the real write) — this is non-negotiable, tied to a real data-loss
  incident from before this corrective effort began. This wave's dry-run must also report the
  planned schema change (old vs. new CHECK constraint text) alongside the row-migration plan,
  since this is the first Wave 5 sub-wave to touch the table's schema, not just insert rows.
- **Mandatory:** the plan's real-write task must explicitly state it runs against the
  **main checkout's** file paths (absolute or explicitly-flagged, never a script's
  worktree-relative default), and its verification step must query the **main checkout's**
  SQLite file directly — not the worktree's copy, even if the write itself was executed from
  within the worktree's Python environment for convenience.
- **Mandatory:** if the migration script writes to more than one store (ledger JSONL +
  SQLite — the shape every domain in this Intelligence Ledger family uses), enumerate every path
  parameter it accepts (grep its `argparse` definitions, don't assume from memory) and require the
  real-write task to pass explicit main-checkout absolute values for **all** of them, not just the
  SQLite one (Wave 5B's jsonl-path gap — resolved once already, don't repeat it).
- **Mandatory:** the wave plan document must include the design spec's actual required content
  **verbatim**, not a self-invented subset. Paste into the plan: (1) the design spec's "Hybrid
  Exit Criteria" section applied to this wave's domain, (2) the design spec's full §5 Validation
  Strategy checklist as literal checkboxes — including "run both paths in parallel for at least
  one full real-world cycle... and diff row-for-row" and "physically exercise rollback at least
  once per domain before declaring the wave done" (an executed exercise with evidence, not a
  prose description — see `wave5b-remediation-report.md` for exactly what "physically executed"
  looks like), (3) the design spec's 9-item Definition of Done verbatim
  (`docs/superpowers/plans/2026-07-19-domain-data-model-v3-implementation-plan.md`'s "Definition
  of Done (applies to every wave...)" section) — do not write a shorter wave-specific version,
  (4) a computed **Context Bundle Completion Bar** number (grep the domain's plugin/skill
  reference table from spec §4 for predictions-related skill/agent references — confirm zero
  stale filename references remain post-wave, report the count). The `writing-plans` skill's own
  "Spec coverage" self-review step must explicitly diff the plan's section list against this
  checklist before presenting the plan for review.
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
  re-run that verification query itself, in the main checkout, before accepting the claim.
- Use `superpowers:subagent-driven-development`: fresh implementer subagent per task, task
  briefs extracted via `scripts/task-brief`, review packages via `scripts/review-package`. For
  Critical/Important findings, dispatch a fix subagent, then re-review — don't self-fix as the
  controller.
- **Model choice for all subagent dispatches (implementer, task reviewer, final whole-branch
  reviewer, fix subagents): Sonnet or Haiku only. Never dispatch with Opus**, even where a skill's
  generic guidance suggests "use the most capable model" — this is a standing user instruction
  that overrides that skill text.
- **Background sub-agent session-limit risk**: has happened in Wave 2 and Wave 3. Instruct
  background dispatches to commit after every single file (not batches), and independently
  verify (direct test runs + grep) before folding any orphaned/interrupted worktree's work back
  in. **Also new this session (Wave 5C found it):** the Agent tool's `isolation: "worktree"`
  parameter creates its OWN separate worktree, ignoring an existing one you've already prepared —
  do not pass `isolation` when you want a subagent to work directly in a worktree you already set
  up; give it the path and instruct it not to create its own.
- **Never use bare `git stash`/`git stash pop`** — the stash stack is shared across all
  worktrees.
- **Never run `git mv`/`git rm`/any file-move operation directly against the main checkout's
  working tree** — even for a wave that also performs a real main-checkout data write. Only the
  actual database/ledger row write targets the main checkout directly; every file/code change,
  including archival, goes through the worktree → PR → merge flow, no exceptions.

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
   migration through Wave 5C; re-confirm still the only pre-existing failures here).
8. Archive-readiness grep still finds real runtime I/O to the old JSON path.
9. The archive step would remove rollback capability.
10. Context-bundler still requires retired files without explanation.
11. The wave would end in a permanent hybrid state.
12. The wave's exit report claims a real data migration write is verified, but that
    verification was never independently re-run against the main checkout's actual files (as
    opposed to a worktree's copy).
13. The wave's plan or exit report repeats a prior effort's unverified "wired, exercised in
    production" claim without independent re-confirmation.
14. A real migration write touches more than one store (ledger JSONL + SQLite) and the wave's
    verification only checked one of them.
15. The wave's plan document does not contain the design spec's actual Hybrid Exit Criteria /
    §5 Validation Strategy / 9-item Definition of Done / Context Bundle Completion Bar content
    verbatim — a self-invented or shortened version does not satisfy this gate.
16. **New for this wave:** the CHECK-constraint widening is done via a live, in-place mutation
    that risks the existing 196 rows (80 RESEARCH_IMPORT + 105 TECHNICAL_SWEEP + 11 REVIEW_DAILY)
    without a verified rebuild-and-copy pattern, tested against a fixture DB first, then verified
    row-for-row against main's real table before/after.

Before archiving anything, all of these must be independently confirmed true (not assumed):
producers cut over, all real consumers cut over, archive-readiness grep clean, repository-path
(anti-bypass) grep clean, tests pass at the documented baseline, rollback **physically exercised**
(not just described) with evidence, a real-cycle parity diff run and matched, a real-data
(non-fixture) test added and passing, AND the real write's row counts have been independently
re-verified against the main checkout's live SQLite file (and ledger file, if the domain uses
one), not just the worktree's.
Archive with `git mv <path> ARCHIVE/<mirrored path>` for git-tracked files — never `rm`.
`predictions.jsonl` is git-tracked (confirmed below), so its archive step is a real `git mv`, not
a local-only `mv` (unlike the daily-briefs domain Wave 5C just closed).

### 4. Wave exit
- Produce `docs/superpowers/status/wave5d-predictions-report.md` — KPI table (JSON files
  before/after, files archived, reads/writes removed, producers/consumers migrated, plugin/
  skill/agent references updated, context-bundle files removed, remaining exceptions), producer/
  consumer cutover table, real bugs found and fixed (with evidence, not smoothed over),
  validation results (explicitly stating the real write was verified against `main`'s DB and
  ledger file, not a worktree's), archive evidence, rollback instructions (with evidence of
  physical execution, not just a plan), commit list. Match `wave5c-daily-briefs-report.md`'s
  depth.
- Ensure all wave commits are on the wave branch; push; open a PR to `main` (do not merge it
  yourself unless explicitly told to — this repo's standing policy is PR-review-then-merge for
  `origin/main`).
- Verify the remote branch matches local HEAD exactly before reporting the PR as ready.
- Produce `docs/superpowers/status/wave5d-handoff.md` (accomplishments, JSON reduction, files
  archived, remaining waves, open issues, KPI summary, exact branch/commit references,
  instructions for the next fresh session).
- **Stop. Do not start the next wave.** After the user reviews/merges the PR: follow
  `.agent/rules/git-operations.md`'s "End-of-Wave Closeout Playbook" exactly — fetch, fast-
  forward `main`, verify the merged commit is an ancestor, **re-run the real migration's
  row-count verification directly against the now-updated main checkout one more time** (both the
  SQLite table and the ledger JSONL file) before declaring the wave fully closed, remove the
  worktree, delete local AND remote feature branches, confirm clean `git worktree
  list`/`git branch --list` — then write Wave 5E's kickoff prompt using this same template before
  that next wave begins. **This step was skipped once already** (Wave 5C's own kickoff prompt for
  5D was not written until explicitly asked for, after PR review/merge and worktree cleanup had
  already happened) — do not repeat that gap.

## This Wave's Scope (Wave 5D)

Per the overall plan/spec (§ "Wave 5D — Predictions" / "2.11 Predictions"): migrate
`predictions.jsonl`/`predictions_graded.jsonl` → `intelligence_event` (new event types
`PREDICTION_CLAIM`/`PREDICTION_GRADED`, **widening the live `event_type` CHECK constraint** — this
value does not exist in the constraint today, unlike every domain Waves 5A–5C migrated into).

**Specific things Task 0 must check against real, current code, not the spec's summary:**
- Real current producers (spec claims 3: `harvest_predictions.py`, `prediction_ledger.py`,
  `grade_predictions.py`) and real current consumers (spec claims 6, including
  `earnings_expectations.py`, `generate_track_record_report.py`, `backtest_harness.py`) — re-verify
  every one against a fresh grep/read, per this migration's standing discipline that plan-inventory
  counts have been wrong in every wave except Wave 4 and Wave 5A.
- Whether `predictions_graded.jsonl` exists on disk yet (per spec: "referenced by a `GRADED_PATH`
  constant... not yet present on disk" as of spec-writing time) — if still absent, there is no
  graded-claims backfill to perform, only a producer/consumer cutover for the code path that would
  write it going forward.
- The spec's own "known false positive" note: `audit_json_usage.py`/`test_audit_json_usage.py`
  showed as `MIGRATION_REQUIRED` in a prior audit but are a pattern-string self-reference, not real
  I/O — confirm this is still true, don't silently re-trust a prior wave's finding without a fresh
  check (the standing discipline every wave has followed).
- The exact SQLite mechanics for widening the `event_type` CHECK constraint on a live table that
  already holds 196 real rows (80 RESEARCH_IMPORT + 105 TECHNICAL_SWEEP + 11 REVIEW_DAILY as of
  this kickoff prompt) without data loss — SQLite has no `ALTER CONSTRAINT`; the real path is
  typically: create a new table with the widened constraint, copy all existing rows verified
  row-for-row, drop the old table, rename the new one into place — inside a transaction, with a
  fixture-DB test proving it before it ever touches main's real file.

**Known false-positive risk, per the pattern in every prior wave except Wave 4 and Wave 5A:**
treat any producer/consumer count in the overall plan/spec as unverified until Task 0
re-confirms it against real current code.

## Starting State (as of this handoff)

- `main` @ `1eacf69a` (Waves 0–5C all merged — PR #97 for Wave 5C; PRs #96, #98, #99, #100,
  unrelated to this migration sequence, are also in `main`'s history by this point: a
  price-source-badge label fix, a screener watchlist-badge default fix, a TradingView-sync
  cash-symbol filter fix, and the root-cause fix for a PSU broker-ticker-alias duplicate-position
  bug — the last of which also required a real, one-time live-data cleanup in `domain_model.sqlite`
  directly on `main`, done outside any wave/PR since it was a data fix, not a code change).
- `investment_screener/backend/data/predictions.jsonl` exists in the main checkout — **87 real
  lines** as of this handoff (spec said "2 lines today" when written; re-derive the real current
  count yourself, don't trust either number blindly). **This file is git-tracked, not gitignored**
  (confirmed via `git check-ignore` returning nothing) — unlike the daily-briefs domain Wave 5C
  just closed, this domain's real-write task's archive step (once ready) is a genuine `git mv`,
  not a local-only `mv`.
- `investment_screener/backend/data/predictions_graded.jsonl` — **does not exist on disk** as of
  this handoff (confirmed via direct `ls`/ ile-not-found), consistent with the spec's own note.
  Confirm this is still true when Wave 5D starts; if a real backfill target has appeared since,
  that's new information to plan around.
- `intelligence_event` table (`intelligence.sqlite`): confirmed via direct query, `PREDICTION_CLAIM`
  and `PREDICTION_GRADED` are **NOT** currently valid values in the live `event_type` CHECK
  constraint (only `RESEARCH_IMPORT, NEWS_SWEEP, EARNINGS, VALUATION_UPDATE, TECHNICAL_SWEEP,
  PORTFOLIO_DECISION, THESIS_UPDATE, MACRO_EVENT, REVIEW_DAILY, REVIEW_WEEKLY` are valid today).
  This is the first Wave 5 sub-wave that requires a real schema change, not just new rows under an
  already-blessed event type. Current real row counts by type: `RESEARCH_IMPORT` 80,
  `TECHNICAL_SWEEP` 105, `REVIEW_DAILY` 11 — 196 total rows this wave's schema migration must not
  lose or corrupt.
- `observations.jsonl` (the append-only ledger `intelligence.sqlite` is replayed from) — confirmed
  consistent with `intelligence.sqlite`'s 196 total rows as of this handoff (196 = 80 + 105 + 11).
  Any real write this wave performs must target **both** files explicitly on the main checkout.
- No worktree currently checked out for this migration — start fresh per the Setup step above.

## Do Not

- Do not start implementation before the wave plan is written and reviewed.
- Do not skip the fresh-code-read step and copy assumptions from the overall plan/spec — and
  specifically do not assume the CHECK-constraint widening is a trivial one-line change; SQLite's
  lack of `ALTER CONSTRAINT` makes this a real rebuild-and-copy operation on a live table with 196
  existing rows across three other event types.
- Do not run a real data migration without the dry-run-then-approval gate.
- **Do not run or verify a real data migration write anywhere other than the main checkout's
  actual files and actual SQLite/ledger files** — a worktree's copies are not a substitute, even
  for verification only. If the migration script writes to both `observations.jsonl` and
  `intelligence.sqlite`, verify both against main, not just the DB.
- Do not archive anything before every gate in the Hard-Stop Conditions section is
  independently confirmed, including the physically-executed rollback exercise and real-cycle
  parity diff — not just written descriptions of them.
- Do not merge to `main` yourself without being told to.
- Do not dispatch any subagent (implementer, reviewer, fix) with the Opus model — Sonnet or
  Haiku only, per standing user instruction.
- Do not pass `isolation: "worktree"` to the Agent tool when dispatching implementers into a
  worktree you've already prepared — it silently creates a second, separate worktree instead of
  using the one you gave it (a real mistake made and corrected during Wave 5C).
- Do not run any `git mv`/file-move operation directly against the main checkout — even the
  archive step goes through the worktree → PR → merge flow. Only the SQLite/ledger row write
  itself (and, if genuinely necessary, a live-data correction unrelated to this wave's code)
  targets the main checkout directly.
- Do not write a wave plan with a self-invented, shortened Definition of Done — paste the design
  spec's real 9-item one, its Hybrid Exit Criteria section, its §5 Validation Strategy checklist,
  and a computed Context Bundle Completion Bar number, verbatim.
- Do not start Wave 5E after this wave's exit — stop and wait for review, same as every prior
  wave. **Do write Wave 5E's kickoff prompt before ending the session**, once the PR is merged and
  closeout is complete — this step was missed once already after Wave 5C and should not be skipped
  again.
