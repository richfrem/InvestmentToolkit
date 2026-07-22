# Wave 4 Kickoff Prompt — Domain Data Model v3.2 Migration

Hand this whole file to a fresh Claude Code session (new context, no prior memory of this
migration) to start Wave 4. The "Way of Working" section below is the reusable template —
copy it forward unchanged for Wave 5A–5E; only the "This Wave's Scope" and "Starting State"
sections need updating per wave.

---

## Read These First, In Order

1. `docs/superpowers/specs/2026-07-19-domain-data-model-v3-implementation-design.md` — the
   overall spec: non-negotiable goal (reduce JSON, not add SQLite beside it), target
   architecture, domain classification table, hybrid exit criteria, retained-JSON rationale
   bar, stop conditions.
2. `docs/superpowers/plans/2026-07-19-domain-data-model-v3-implementation-plan.md` — the
   overall wave roadmap (Wave 0 → 1 → 2 → 3 → 4 → 5A–5E), Global Constraints, Definition of
   Done, Wave KPI table template — all binding on every wave, not just Wave 1.
3. `docs/superpowers/status/wave3-handoff.md` and `docs/superpowers/status/wave3-report.md` —
   the most recent wave's outcome: KPI table, producer/consumer cutover results, real bugs
   found and fixed, live broker-sync validation evidence, open issues (including the still-
   unmigrated `apply_portfolio_updates.py` — confirm during Wave 4 scoping whether it's dead
   code or a genuine 5th producer). **Match this level of rigor, not less.**
4. `ADRs/030_portfolio_totals_computed_not_stored.md` — Wave 3's design decision on computed-
   vs-stored totals; the same "store facts, calculate aggregates" principle applies to trade
   log / order execution / cash flow data (e.g. account balances after a trade are calculated,
   not stored; the trade itself — price, quantity, timestamp — is the fact).
5. `docs/superpowers/plans/2026-07-20-domain-data-model-v3-wave3-implementation-plan.md` — the
   detailed Wave 3 task plan itself, as a structural example (Task 0's fresh-verification sweep
   found only 5 of the plan's claimed 20 producers were real — the same discipline is required
   again this wave; do not assume the roadmap's original estimate for trade-log/order-execution/
   cash-flow producer and consumer counts is accurate).

## Way of Working (reusable every wave — do not skip steps)

### 1. Setup
- Confirm `main` is up to date (`git pull origin main`) and note the current HEAD commit —
  should include Wave 3's merge commit `28398419`.
- Per this repo's CLAUDE.md rule #14, create an isolated worktree before any multi-file code
  change (`EnterWorktree` if available; if it branches from a stale ref, `git merge --ff-only
  main` inside the worktree to bring in latest `main`, verified via `git log`).

### 2. Plan the wave (before touching code)
- Use `superpowers:writing-plans`.
- **Re-read the real, current code for every producer/consumer this wave touches — do not
  trust the overall plan's one-line file descriptions or the spec's original producer/consumer
  counts as ground truth.** Every wave so far has found the plan's initial assumptions wrong
  once real code was read (Wave 1: real file count 82 not 144; Wave 2: 7 of 11 claimed
  producers were never real writers; Wave 3: only 5 of 20 claimed producers were real, plus 2
  real touchpoints missing from the plan entirely). Budget real investigation time before
  writing task-level detail.
- Write full TDD-ready detail for parts that are genuinely plannable now (schema, repository
  functions with a fixed target schema). For consumer-rewiring tasks spanning many files, it's
  fine to NOT pre-script exact code — state the real file list, the available repository
  functions, and the instruction "read this file's actual current code before editing."
- Include a **hard approval gate before any real data migration runs** (dry-run report first,
  explicit user sign-off, THEN the real write) — this is non-negotiable, tied to a real data-
  loss incident from before this corrective effort began.
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
  touching real data or a real cutover claim.
- Use `superpowers:subagent-driven-development`: fresh implementer subagent per task, task
  briefs extracted via `scripts/task-brief`, review packages via `scripts/review-package`. For
  Critical/Important findings, dispatch a fix subagent, then re-review — don't self-fix as the
  controller.
- **Background sub-agent session-limit risk**: this has now happened in both Wave 2 and Wave 3
  — a dispatched background agent ran out of session budget mid-task. Instruct background
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
   currently one known pre-existing `zod-schemas.spec.ts` failure, confirmed unrelated to this
   migration in Wave 3).
8. Archive-readiness grep still finds real runtime I/O to the old JSON path.
9. The archive step would remove rollback capability.
10. Context-bundler still requires retired files without explanation.
11. The wave would end in a permanent hybrid state.

Before archiving anything, all of these must be independently confirmed true (not assumed):
producers cut over, all real consumers cut over, archive-readiness grep clean, repository-path
(anti-bypass) grep clean, tests pass at the documented baseline, rollback remains possible.
Archive with `git mv <path> ARCHIVE/<mirrored path>` — never `rm`. If the file is gitignored
private data (like `portfolio.json` was), archive is a **local-only `mv`**, never `git mv`.

### 4. Wave exit
- Produce `docs/superpowers/status/wave4-<domain>-report.md` — KPI table (JSON files
  before/after, files archived, reads/writes removed, producers/consumers migrated, plugin/
  skill/agent references updated, context-bundle files removed, remaining exceptions),
  producer/consumer cutover table, real bugs found and fixed (with evidence, not smoothed over),
  validation results, archive evidence, rollback instructions, commit list. Match
  `wave3-handoff.md`'s depth.
- Ensure all wave commits are on the wave branch; push; open a PR to `main` (do not merge it
  yourself unless explicitly told to — this repo's standing policy is PR-review-then-merge for
  `origin/main`).
- Verify the remote branch matches local HEAD exactly before reporting the PR as ready.
- Produce `docs/superpowers/status/wave4-handoff.md` (accomplishments, JSON reduction, files
  archived, remaining waves, open issues, KPI summary, exact branch/commit references,
  instructions for the next fresh session).
- **Stop. Do not start the next wave.** After the user reviews/merges the PR: follow
  `.agent/rules/git-operations.md`'s "End-of-Wave Closeout Playbook" exactly — fetch, fast-
  forward `main`, verify the merged commit is an ancestor, remove the worktree, delete local
  AND remote feature branches, confirm clean `git worktree list`/`git branch --list` — then
  write the next wave's kickoff prompt using this same template before that next wave begins.

## This Wave's Scope (Wave 4)

Per the overall plan, Wave 4 covers: **Portfolio operations — trade log, order executions, cash
flows.**

**Source files in scope (per the original plan's estimate — re-verify all of this fresh, per
the discipline above, before trusting it):**
- `investment_screener/backend/data/trade-log.json` (JSON list) → `trade_log_entry` table.
  Original plan estimate: 4 real consumers.
- `orders_executed.jsonl` → `order_execution` table. Original plan estimate: 2 real consumers.
- `cash_flows.json` → `cash_flow` + `cash_flow_baseline` tables. Original plan estimate: 3 real
  consumers.

**Known false-positive risk, per the pattern in every prior wave:** treat every one of these
counts as unverified until Task 0 re-confirms them against real current code. Waves 1-3 each
found the plan's original inventory significantly wrong (Wave 1: 144 claimed files → 82 real;
Wave 2: 7 of 11 claimed producers were never real; Wave 3: 15 of 20 claimed producers were never
real, plus 2 real touchpoints entirely missing from the plan). Assume the same is true here.

**Carry-forward open item from Wave 3:** confirm whether `apply_portfolio_updates.py` (still
writing `portfolio.json` directly, no confirmed call site found in Wave 3's audit) is dead code
or a live producer that should have been Wave 3's 5th cutover — resolve this before Wave 4's own
scope locks in, since it may belong to either wave's domain depending on what it actually does
(it "writes rebalance order updates back to data files" per its own docstring — likely belongs
partly to Wave 4's trade-log/order-execution domain, not purely Wave 3's holdings domain).

**Design principle carried forward from ADR-030:** account balances, position quantities, and
running totals derived from trade/order history are always computed live from the ledger of
individual trade/order facts — never stored as their own denormalized column, except a genuine
broker-reported fact that cannot be recomputed (same exception class as Wave 3's
`broker_exchange_rate`/`broker_reported_total`).

## Starting State (as of this handoff)

- `main` @ `28398419` (Wave 0, 1, 2, and 3 all merged: PR #84, PR #85, PR #86/#87, and Wave 3's
  direct merge to `main`).
- `investment` table now has `sector`/`industry` columns (Wave 3, real yfinance data).
- `account`, `account_investment`, `investment_price` tables are populated with real live
  broker-synced data (gitignored, not in git — a fresh checkout needs a real broker sync via
  `fetch_broker_data.py --snapshot` or the app's normal sync flow to reconstruct this data; there
  is no offline migration script to "replay" it from an archived JSON file, since `portfolio.json`
  itself is gitignored private data, never committed even pre-migration).
- `broker_exchange_rate` and `broker_reported_total` singleton tables exist and are populated
  from the most recent broker sync.
- `domain_model.sqlite` overall now holds Wave 0+1+2+3 data (gitignored, rebuildable via
  `initialize_db()` + re-running each wave's migration script in order for the static domains;
  Wave 3's holdings data specifically requires a live re-sync, not a replay).
- No worktree currently checked out for this migration — start fresh per the Setup step above.

## Do Not

- Do not start implementation before the wave plan is written and reviewed.
- Do not skip the fresh-code-read step and copy assumptions from the overall plan/spec.
- Do not run a real data migration without the dry-run-then-approval gate.
- Do not archive anything before every gate in the Hard-Stop Conditions section is
  independently confirmed.
- Do not merge to `main` yourself without being told to.
- Do not start Wave 5A after this wave's exit — stop and wait for review, same as every prior
  wave.
