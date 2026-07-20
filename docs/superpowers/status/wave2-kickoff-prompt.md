# Wave 2 Kickoff Prompt — Domain Data Model v3.2 Migration

Hand this whole file to a fresh Claude Code session (new context, no prior memory of this
migration) to start Wave 2. The "Way of Working" section below is the reusable template —
copy it forward unchanged for Wave 3, 4, 5A–5E; only the "This Wave's Scope" and "Starting
State" sections need updating per wave.

---

## Read These First, In Order

1. `docs/superpowers/specs/2026-07-19-domain-data-model-v3-implementation-design.md` — the
   overall spec: non-negotiable goal (reduce JSON, not add SQLite beside it), target
   architecture, domain classification table, hybrid exit criteria, retained-JSON rationale
   bar, stop conditions.
2. `docs/superpowers/plans/2026-07-19-domain-data-model-v3-implementation-plan.md` — the
   overall wave roadmap (Wave 0 → 1 → 2 → 3 → 4 → 5A–5E), Global Constraints, Definition of
   Done, Wave KPI table template — all binding on every wave, not just Wave 1.
3. `docs/superpowers/status/wave1-projections-report.md` and
   `docs/superpowers/status/wave1-handoff.md` — the reference example of what "done" looks
   like for one wave: KPI table, producer/consumer cutover table, real bugs found and fixed
   with evidence, validation results, archive evidence, rollback instructions, commit list.
   **Match this level of rigor, not less.**
4. `docs/superpowers/plans/2026-07-19-domain-data-model-v3-wave1-projections-implementation-plan.md`
   — the detailed Wave 1 task plan itself, as a structural example of how a wave-level plan
   should read (Task 1 fully scripted where concretely plannable; later tasks deliberately
   NOT pre-scripted with exact code, because consumer rewiring requires reading each file
   fresh at execution time — this is the pattern to repeat for Wave 2's detailed plan, not a
   one-off).

## Way of Working (reusable every wave — do not skip steps)

### 1. Setup
- Confirm `main` is up to date (`git pull origin main`) and note the current HEAD commit.
- Per this repo's CLAUDE.md rule #14, create an isolated worktree before any multi-file code
  change (`EnterWorktree` if available; if it branches from a stale ref, `git merge --ff-only
  main` inside the worktree to bring in latest `main`, verified via `git log`).

### 2. Plan the wave (before touching code)
- Use `superpowers:writing-plans`.
- **Re-read the real, current code for every producer/consumer this wave touches — do not
  trust the overall plan's one-line file descriptions or the spec's original producer/
  consumer counts as ground truth.** Every wave so far has found the plan's initial
  assumptions wrong once real code was read (Wave 1 found: real file count was 82 not 144;
  `ProjectionService`'s upsert semantics were more complex than assumed; a real trading-
  signal-inversion bug the plan never anticipated; a schema-drift bug from an eager
  singleton). Budget real investigation time before writing task-level detail.
- Write full TDD-ready detail for parts that are genuinely plannable now (schema, repository
  functions with a fixed target schema). For consumer-rewiring tasks spanning many files,
  it's fine to NOT pre-script exact code — state the real file list, the available repository
  functions, and the instruction "read this file's actual current code before editing," per
  Wave 1's Task 7 pattern. This is honesty, not corner-cutting.
- Include a **hard approval gate before any real data migration runs** (dry-run report first,
  explicit user sign-off, THEN the real write) — this is non-negotiable, tied to a real data-
  loss incident from before this corrective effort began.
- Present the plan for user review before executing. Apply any requested revisions.

### 3. Execute the wave — wave-level autonomy (current standing instruction)
As of Wave 1, the user established this working mode for all future waves:
- **Do not stop after every individual task/subtask for approval.** Execute the approved wave
  plan end-to-end.
- **Do not run a separate full reviewer cycle after every small commit** unless a hard-stop
  condition (below) is triggered.
- Fix issues found along the way. Keep commits logical and reviewable (one task = one commit
  or a few, not one giant commit per wave).
- Still verify real claims against real evidence before trusting them — this repo's migration
  history includes reports that overclaimed completion (a real production database schema
  mutation was reported as "never happened" when it had). **Never trust a subagent's report at
  face value for anything consequential — a producer rewire, a migration write, an archive
  step.** Dispatch independent verification (a reviewer subagent, or your own direct queries
  against real data) for anything touching real data or a real cutover claim.
- Use `superpowers:subagent-driven-development`: fresh implementer subagent per task, task
  briefs extracted via `scripts/task-brief`, review packages via `scripts/review-package`. For
  Critical/Important findings, dispatch a fix subagent, then re-review — don't self-fix as the
  controller.
- **Never use bare `git stash`/`git stash pop`** — the stash stack is shared across all
  worktrees (Wave 1 hit this: a subagent's stray `git stash pop` conflicted with someone else's
  unrelated WIP; resolved safely by verifying "ours" matched `HEAD` exactly before restoring,
  and confirming the stash entry was left fully intact).

### Hard-Stop Conditions (stop immediately, report evidence, wait for user)
1. Source count and target row count do not reconcile.
2. Row/version/scenario count has an unexplained delta.
3. A new data shape is discovered without a test covering it.
4. A producer still writes the old JSON path as source of truth.
5. A real consumer still reads the old JSON path after claimed cutover.
6. Any script bypasses the approved repository/service layer and opens SQLite directly.
7. Tests fail in a new or migration-related way (not the documented pre-existing baseline).
8. Archive-readiness grep still finds real runtime I/O to the old JSON path.
9. The archive step would remove rollback capability.
10. Context-bundler still requires retired files without explanation.
11. The wave would end in a permanent hybrid state.

Before archiving anything, all of these must be independently confirmed true (not assumed):
producers cut over, all real consumers cut over, archive-readiness grep clean, repository-path
(anti-bypass) grep clean, tests pass at the documented baseline, rollback remains possible.
Archive with `git mv <path> ARCHIVE/<mirrored path>` — never `rm`.

### 4. Wave exit
- Produce `docs/superpowers/status/wave<N>-<domain>-report.md` — KPI table (JSON files
  before/after, files archived, reads/writes removed, producers/consumers migrated,
  plugin/skill/agent references updated, context-bundle files removed, remaining exceptions),
  producer/consumer cutover table, real bugs found and fixed (with evidence, not smoothed
  over), validation results, archive evidence, rollback instructions, commit list. Match
  `wave1-projections-report.md`'s depth.
- Ensure all wave commits are on the wave branch; push; open a PR to `main` (do not merge it
  yourself unless explicitly told to — this repo's standing policy is PR-review-then-merge for
  `origin/main`).
- Verify the remote branch matches local HEAD exactly before reporting the PR as ready.
- Produce `docs/superpowers/status/wave<N>-handoff.md` (accomplishments, JSON reduction,
  files archived, remaining waves, open issues, KPI summary, exact branch/commit references,
  instructions for the next fresh session) — match `wave1-handoff.md`'s structure.
- **Stop. Do not start the next wave.** After the user reviews/merges the PR: sync local
  `main` (`git pull origin main`, verify the merge commit landed), clean up the worktree
  (`ExitWorktree` with `action: "remove"` — safe once confirmed merged), and write the next
  wave's kickoff prompt using this same template before that next wave begins.

## This Wave's Scope (Wave 2)

Per the overall plan, Wave 2 covers: **Investment / target-portfolio / watchlist / price
levels / investment notes / TradingView alerts / thesis breaker state** — all folding into the
v3.2 `investment` table (already exists, minimally seeded by Wave 0's backfill and partially
populated by Wave 1's projection migration) plus `price_level_set`/`price_level_tier`,
`investment_note`, `alert`.

**Source files in scope:**
- `investment_screener/backend/data/theses/target-portfolio.json` — note the real path
  includes a `theses/` subdirectory; confirmed by direct code read in Wave 1
  (`apply_catalyst.py`'s `THESIS_JSON` constant, `compute_conviction_scores.py`'s
  `TARGET_PATH` constant) — do not assume the bare `target-portfolio.json` path some earlier
  docs use.
- `watchlist.json`
- Embedded within `target-portfolio.json`: `holdings[].priceLevels` (buy tiers),
  `holdings[].targetEntryPrice` (scalar, maps to `tier_kind='TARGET_ENTRY'`),
  `holdings[].agentRationale` (→ `investment_note`, currently a single field with dated
  entries manually concatenated — a real un-queryable-history problem the new table fixes).
- `tradingview_alerts_actual.json` (203 entries) → `alert` table.
- `thesis_breaker_state.json` → folds directly into `investment.thesis_breaker_status`
  (already a column — this is NOT its own separate table).

**Known real producers/consumers** (per the original plan's §2.1 — but re-verify against
current code before trusting the count, per the Way of Working section above): 11 producers,
18+6 consumers for the target-portfolio/watchlist domain. This is the largest consumer surface
attempted so far — Wave 1 had 2 producers/18 consumers; this one has more producers and a
comparable-or-larger consumer count. Budget accordingly; consider whether sub-waves (like
Wave 1's 7A/7B/7C) make sense for the consumer-rewiring portion.

**Highest-risk item, called out explicitly in both the spec and the original plan:** the
`standingDecision` anchor rule (CLAUDE.md rule #8 — never flip BUY→SELL on <15% variance) must
be re-verified against the new read path specifically before this wave is declared done. This
is the single most safety-critical piece of logic touching this file — treat it with at least
the same scrutiny Wave 1 gave the `BW` trading-signal-inversion bug.

**Also real, confirmed in the spec's Response-to-Review analysis:** `role` (lifecycle_status),
`action` (target_action), and `is_watchlisted` genuinely disagree on the same holding in real
data (e.g. `DRAM`: `role='initiate'`, `action='WATCHLIST'`) — do not collapse these into one
field. `watchlist.json`'s 80 tickers and `role='watchlist'`'s 33 tickers overlap by only 20 —
two different populations tracking two different questions.

## Starting State (as of this handoff)

- `main` @ `cca58fd2` (Wave 0 + Wave 1 both merged: PR #84, PR #85).
- `investment` table exists with 82 real rows (identity fields only — symbol, asset_class,
  currency — populated by Wave 0's backfill; `lifecycle_status`/`target_weight`/
  `standing_decision_*`/etc. are still NULL, waiting for this wave).
- `domain_model.sqlite` also has 115 real `projection_version` rows / 345 `projection_scenario`
  rows from Wave 1 (gitignored, not in git — rebuildable via `initialize_db()` +
  `migrate_projections_to_sqlite.py --write` if a fresh checkout needs it).
- `investment_screener/backend/data/projections/` no longer exists — archived to
  `ARCHIVE/investment_screener/backend/data/projections/` (Wave 1).
- No worktree currently checked out for this migration — start fresh per the Setup step above.

## Do Not

- Do not start implementation before the wave plan is written and reviewed.
- Do not skip the fresh-code-read step and copy assumptions from the overall plan/spec.
- Do not run a real data migration without the dry-run-then-approval gate.
- Do not archive anything before every gate in the Hard-Stop Conditions section is
  independently confirmed.
- Do not merge to `main` yourself without being told to.
- Do not start Wave 3 after this wave's exit — stop and wait for review, same as Wave 1.
