# Wave 5C Kickoff Prompt — Domain Data Model v3.2 Migration

Hand this whole file to a fresh Claude Code session (new context, no prior memory of this
migration) to start Wave 5C. The "Way of Working" section below is the reusable template —
copy it forward unchanged for Wave 5D–5E; only the "This Wave's Scope" and "Starting State"
sections need updating per wave.

---

## Read These First, In Order

1. `docs/superpowers/specs/2026-07-19-domain-data-model-v3-implementation-design.md` — the
   overall spec: non-negotiable goal, target architecture, domain classification table, Hybrid
   Exit Criteria, §5 Validation Strategy, 9-item Definition of Done, retained-JSON rationale bar,
   stop conditions. See its "2.13 Daily briefs" section specifically.
2. `docs/superpowers/plans/2026-07-19-domain-data-model-v3-implementation-plan.md` — the
   overall wave roadmap and Global Constraints — **all of them, including the three added
   2026-07-22/23** (main-checkout-only real writes; enumerate every path argument a migration
   script accepts, not just the obvious one; every wave plan must paste the spec's real
   Validation Strategy/Definition of Done/Hybrid Exit Criteria/Context Bundle Completion Bar
   verbatim, not a self-invented subset). See its "Wave 5C — Daily Briefs" section.
3. `docs/superpowers/status/wave5b-ta-sweep-results-report.md`,
   `docs/superpowers/status/wave5b-handoff.md`, and
   `docs/superpowers/status/wave5b-remediation-report.md` — Wave 5B's full outcome including a
   real post-merge correction (see item 4 below) and a remediation pass that closed a real gap in
   the wave's own plan. **Match this level of rigor, not less — read the remediation report
   especially carefully, it explains exactly what "the spec's real bar" means in practice** (a
   physically-executed rollback exercise with evidence, a real-cycle parity diff, a real-data
   non-fixture test, a computed Context Bundle number — not prose descriptions of any of these).
4. `.agent/map-debt.md` — read the two Wave 5B entries in full: (a) the jsonl-path gap ("Wave 5B's
   real `--write` correctly targeted main's `intelligence.sqlite`... but omitted `--jsonl-path`"),
   (b) the plan-scope gap ("Wave 5B — plan omitted the spec's real Validation Strategy and
   Definition of Done"). Both are RESOLVED but exist specifically so Wave 5C doesn't repeat them.
5. `ADRs/029_persistence_domain_rationalization_and_retirement_gated_migration.md` — defines what
   "migrated" means and warns that prior status docs for this domain family (research/TA/daily
   briefs) have falsely claimed completion before. This wave's domain (daily briefs) carries the
   exact same "code wired but no real test exists for this path" caveat the prior effort left
   for TA sweep results — which Wave 5B found to be **true** (0 real rows in main's DB despite
   dual-write code existing), not a false alarm. Assume the same is possible here until proven
   otherwise.
6. `ADRs/030_portfolio_totals_computed_not_stored.md` — the "store facts, calculate aggregates"
   principle, applicable wherever this wave's domain has a derivable aggregate vs. a genuine
   external fact. **Also read `feedback_portfolio_total_validation.md` in agent memory (or ask
   about it) if this wave's work touches any totals/aggregation logic** — a real, separate
   production bug (dashboard total off by ~$3k USD) was found and fixed 2026-07-23 in the
   *portfolio* domain (PR #95), rooted in exactly this "computed vs. authoritative" tension; the
   settled rule is: computed values are what's displayed, an external authoritative figure is a
   validation check only, never a silent override. Not directly this wave's domain, but the
   architectural principle transfers.

## Way of Working (reusable every wave — do not skip steps)

### 1. Setup
- Confirm `main` is up to date (`git pull origin main`) and note the current HEAD commit —
  should include Wave 5B's merge (PR #93), its remediation (PR #94), and the portfolio-total fix
  (PR #95, a different domain, merged in between — not part of this migration's wave sequence but
  will be in `main`'s history).
- Per this repo's CLAUDE.md rule #14, create an isolated worktree before any multi-file code
  change (`EnterWorktree` if available; if it branches from a stale ref, `git merge --ff-only
  main` inside the worktree to bring in latest `main`, verified via `git log`).
- **Mandatory (CLAUDE.md pitfall #29):** immediately after creating the worktree, note that its
  `domain_model.sqlite` / `intelligence.sqlite` and any gitignored source data files are
  separate, unsynced copies from the main checkout's. This wave involves a real `--write` step
  (daily-briefs data is gitignored, real, and needs migrating) — plan around the worktree/main
  split now rather than discovering it at wave-exit time again.
- After `npm install`/dependency setup in a fresh worktree, remember `mocha`/`pytest` won't be
  available until you run it — a fresh worktree has no `node_modules` (Wave 5B hit this; not a
  bug, just don't waste a cycle debugging a missing-binary error before installing).

### 2. Plan the wave (before touching code)
- Use `superpowers:writing-plans`.
- **Re-read the real, current code for every producer/consumer this wave touches — do not
  trust the overall plan's one-line file descriptions or the spec's original producer/consumer
  counts as ground truth.** Every wave except Wave 4 and Wave 5A found the plan's initial
  assumptions wrong once real code was read (Wave 1: real file count 82 not 144; Wave 2: 7 of 11
  claimed producers were never real writers; Wave 3: only 5 of 20 claimed producers were real;
  Wave 5B: the domain's SQLite side had genuinely never been exercised, unlike Wave 5A's
  equivalent-looking claim which turned out to be a dead-but-harmless code path). Do not assume
  which category this wave falls into — check.
- **Wave 5C's specific instruction from the overall plan:** the prior effort's status docs
  describe `data/daily-briefs/*.json`'s ledger migration as "code wired but no real test exists
  for this path." Do not trust that claim either way — re-verify producer/consumer/archive from
  scratch. Specifically check: does `intelligence.sqlite` have any real `REVIEW_DAILY` rows today
  (as of this kickoff prompt, it has zero), and does `daily_brief.py` actually dual-write to the
  ledger on a real run, or does it only write `data/daily-briefs/*.json`?
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
- **Mandatory:** if the migration script writes to more than one store (e.g. an event-ledger
  JSONL file AND a SQLite read-model, the shape every domain in this "Intelligence Ledger" family
  uses), enumerate every path parameter it accepts (grep its `argparse` definitions, don't assume
  from memory) and require the real-write task to pass explicit main-checkout absolute values for
  **all** of them, not just the SQLite one. Wave 5B's real write correctly targeted
  `intelligence.sqlite` via `--db-path` but silently defaulted `--jsonl-path` to the worktree's
  own ledger file, splitting the audit trail from the DB state for one full remediation cycle
  before it was caught.
- **Mandatory:** the wave plan document must include the design spec's actual required content
  **verbatim**, not a self-invented subset. Paste into the plan: (1) the design spec's "Hybrid
  Exit Criteria" section applied to this wave's domain, (2) the design spec's full §5 Validation
  Strategy checklist as literal checkboxes — including "run both paths in parallel for at least
  one full real-world cycle... and diff row-for-row" and "physically exercise rollback at least
  once per domain before declaring the wave done" (an executed exercise with evidence, not a
  prose description of what rollback *would* involve — see `wave5b-remediation-report.md` for
  exactly what "physically executed" looks like: a throwaway worktree, a real `git revert`, real
  old-code-path re-verification against the restored file, then discarded), (3) the design spec's
  9-item Definition of Done verbatim (`docs/superpowers/plans/2026-07-19-domain-data-model-v3-
  implementation-plan.md`'s "Definition of Done (applies to every wave...)" section) — do not
  write a shorter wave-specific version, (4) a computed **Context Bundle Completion Bar** number
  (grep the domain's plugin/skill reference table from spec §4 — for daily briefs, check
  `daily-brief` skill/agent references — confirm zero stale filename references remain post-wave,
  report the count). The `writing-plans` skill's own "Spec coverage" self-review step must
  explicitly diff the plan's section list against this checklist before presenting the plan for
  review — this is what Wave 5B's own plan skipped, caught only after merge.
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
- **Never run `git mv`/`git rm`/any file-move operation directly against the main checkout's
  working tree** — even for a wave that also performs a real main-checkout data write. Wave 5B's
  Task 5 briefly did this by mistake (an archive `git mv` run in the main checkout instead of the
  worktree); caught and reverted before committing, but the discipline is: **only the actual
  database/ledger row write targets the main checkout directly; every file/code change, including
  archival, goes through the worktree → PR → merge flow, no exceptions.**

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
   migration through Wave 5B).
8. Archive-readiness grep still finds real runtime I/O to the old JSON path.
9. The archive step would remove rollback capability.
10. Context-bundler still requires retired files without explanation.
11. The wave would end in a permanent hybrid state.
12. The wave's exit report claims a real data migration write is verified, but that
    verification was never independently re-run against the main checkout's actual files (as
    opposed to a worktree's copy).
13. The wave's plan or exit report repeats the prior effort's unverified "wired, exercised in
    production" claim for `data/daily-briefs/*.json` without independent re-confirmation.
14. **New (from Wave 5B's jsonl-path gap):** a real migration write touches more than one store
    (ledger JSONL + SQLite) and the wave's verification only checked one of them.
15. **New (from Wave 5B's plan-scope gap):** the wave's plan document does not contain the design
    spec's actual Hybrid Exit Criteria / §5 Validation Strategy / 9-item Definition of Done /
    Context Bundle Completion Bar content verbatim — a self-invented or shortened version does
    not satisfy this gate.

Before archiving anything, all of these must be independently confirmed true (not assumed):
producers cut over, all real consumers cut over, archive-readiness grep clean, repository-path
(anti-bypass) grep clean, tests pass at the documented baseline, rollback **physically exercised**
(not just described) with evidence, a real-cycle parity diff run and matched, a real-data
(non-fixture) test added and passing, AND the real write's row counts have been independently
re-verified against the main checkout's live SQLite file (and ledger file, if the domain uses
one), not just the worktree's.
Archive with `git mv <path> ARCHIVE/<mirrored path>` for git-tracked files — never `rm`. If the
file is gitignored private data (daily-briefs data is gitignored, confirmed below), archive is a
**local-only `mv`**, never `git mv`.

### 4. Wave exit
- Produce `docs/superpowers/status/wave5c-<domain>-report.md` — KPI table (JSON files
  before/after, files archived, reads/writes removed, producers/consumers migrated, plugin/
  skill/agent references updated, context-bundle files removed, remaining exceptions), producer/
  consumer cutover table, real bugs found and fixed (with evidence, not smoothed over),
  validation results (explicitly stating the real write was verified against `main`'s DB and
  ledger file, not a worktree's), archive evidence, rollback instructions (with evidence of
  physical execution, not just a plan), commit list. Match `wave5b-ta-sweep-results-report.md`'s
  depth — that report is now the bar, not `wave5a`'s (which, in hindsight, undersold what full
  compliance requires).
- Ensure all wave commits are on the wave branch; push; open a PR to `main` (do not merge it
  yourself unless explicitly told to — this repo's standing policy is PR-review-then-merge for
  `origin/main`).
- Verify the remote branch matches local HEAD exactly before reporting the PR as ready.
- Produce `docs/superpowers/status/wave5c-handoff.md` (accomplishments, JSON reduction, files
  archived, remaining waves, open issues, KPI summary, exact branch/commit references,
  instructions for the next fresh session).
- **Stop. Do not start the next wave.** After the user reviews/merges the PR: follow
  `.agent/rules/git-operations.md`'s "End-of-Wave Closeout Playbook" exactly — fetch, fast-
  forward `main`, verify the merged commit is an ancestor, **re-run the real migration's
  row-count verification directly against the now-updated main checkout one more time** (both the
  SQLite table and the ledger JSONL file, if this domain uses one) before declaring the wave fully
  closed, remove the worktree, delete local AND remote feature branches, confirm clean
  `git worktree list`/`git branch --list` — then write the next wave's kickoff prompt using this
  same template before that next wave begins.

## This Wave's Scope (Wave 5C)

Per the overall plan/spec (§ "Wave 5C — Daily Briefs" / "2.13 Daily briefs"): migrate
`data/daily-briefs/*.json` → `intelligence_event` (event type `REVIEW_DAILY`, already present in
the live CHECK constraint, 0 rows today — confirmed below).

**Explicit instruction from the plan, repeated here because it is this wave's central risk:** the
prior effort's status docs describe this domain as "code wired but no real test exists for this
path." **Do not trust that claim either way.** Wave 5B investigated the near-identical claim for
TA sweep results and found it was **accurate** (the domain's SQLite side had never actually been
exercised, despite dual-write code existing) — do not assume Wave 5C's domain will turn out to be
the Wave 5A case (claim proven false/harmless) just because that's the more recent precedent.
Verify from scratch.

**Specific things Task 0 must check against real, current code, not the spec's summary:**
- Does `daily_brief.py` write to the Intelligence Ledger (`intelligence.event_store.append_event`
  with `event_type='TECHNICAL_SWEEP'`... no — `event_type='REVIEW_DAILY'`) at all today, or only
  to `data/daily-briefs/*.json`?
- The spec says the real consumer is `generate_reports.py` (globs `*.json`) plus `daily_brief.py`
  itself (reads prior snapshots for its delta-vs-yesterday calculation). Confirm both are real,
  current call sites — and check for any others a fresh grep turns up that the spec's inventory
  might have missed (Wave 5B found a spec-listed "consumer," `evolution_events.py`, was actually
  only a stale docstring mention, not real code — the inverse can also be true: a real consumer
  the spec's inventory missed).
- The delta-vs-yesterday calculation ("read prior snapshots... sort") is exactly the kind of glob
  + sort logic the target design replaces with a real SQL query (`ORDER BY effective_at DESC
  LIMIT 2`) — confirm this rewire doesn't change the actual delta values computed, not just that
  it compiles/runs.

**Known false-positive risk, per the pattern in every prior wave except Wave 4 and Wave 5A:**
treat any producer/consumer count in the overall plan/spec as unverified until Task 0
re-confirms it against real current code.

## Starting State (as of this handoff)

- `main` @ `5f82bc9a` (Waves 0-5B all merged — PR #93 for Wave 5B, PR #94 for its remediation;
  PR #95, unrelated to this migration sequence, fixed a separate portfolio-total display bug in
  between and is also in `main`'s history by this point).
- `investment_screener/backend/data/daily-briefs/*.json` exists in the main checkout — 10 real
  snapshot files as of this handoff, dated `2026-06-10` through `2026-07-18` (sizes ranging
  ~28KB–193KB) — **has not yet been inspected for real producer/consumer code as part of this
  migration effort; that is this wave's Task 0 job, not something to assume from the file count
  matching the spec's "10 snapshots" claim.** This directory **is gitignored**
  (`investment_screener/.gitignore:119`) — archive convention for this wave is **local-only
  `mv`**, never `git mv`, same as `portfolio.json`/`cash_flows.json`.
- `intelligence_event` table: confirmed via direct query, `REVIEW_DAILY` is already a valid value
  in the live `event_type` CHECK constraint, currently **0 rows**. `RESEARCH_IMPORT` (80 rows,
  Wave 5A) and `TECHNICAL_SWEEP` (105 rows: 26 backfilled + 79 from a real live sweep, Wave 5B)
  are the only event types with real data in this table today.
- `domain_model.sqlite` overall now holds Wave 0+1+2+3+4 data (gitignored, rebuildable via
  `initialize_db()` + re-running each wave's migration script in order for the static domains;
  Wave 3's holdings data specifically requires a live broker re-sync, Wave 4's requires the
  archived local JSON copies if starting from scratch on a machine that still has them). Note:
  `domain_model.sqlite` is a **separate file** from `intelligence.sqlite` — this wave's
  `REVIEW_DAILY` events go into `intelligence.sqlite`, same file Waves 5A/5B used, not
  `domain_model.sqlite`.
- `observations.jsonl` (the append-only ledger `intelligence.sqlite` is replayed from) currently
  has 185 real events (80 `RESEARCH_IMPORT` + 105 `TECHNICAL_SWEEP`) — confirmed consistent with
  `intelligence.sqlite`'s row counts as of this handoff. Any real write this wave performs must
  target **both** files explicitly on the main checkout (see the new Global Constraint on
  enumerating every path argument).
- No worktree currently checked out for this migration — start fresh per the Setup step above.

## Do Not

- Do not start implementation before the wave plan is written and reviewed.
- Do not skip the fresh-code-read step and copy assumptions from the overall plan/spec — and
  specifically do not assume this wave's "code wired but untested" claim resolves the same way
  Wave 5A's or Wave 5B's did just because one of those precedents exists.
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
- Do not run any `git mv`/file-move operation directly against the main checkout — even the
  archive step goes through the worktree → PR → merge flow. Only the SQLite/ledger row write
  itself targets the main checkout directly.
- Do not write a wave plan with a self-invented, shortened Definition of Done — paste the design
  spec's real 9-item one, its Hybrid Exit Criteria section, its §5 Validation Strategy checklist,
  and a computed Context Bundle Completion Bar number, verbatim.
- Do not start Wave 5D after this wave's exit — stop and wait for review, same as every prior
  wave.
