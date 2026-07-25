# Wave 5E Kickoff Prompt — Domain Data Model v3.2 Migration

Hand this whole file to a fresh Claude Code session (new context, no prior memory of this
migration) to start Wave 5E. The "Way of Working" section below is the reusable template —
copy it forward unchanged for any future wave; only the "This Wave's Scope" and "Starting State"
sections need updating per wave.

---

## Read These First, In Order

1. `docs/superpowers/specs/2026-07-19-domain-data-model-v3-implementation-design.md` — the
   overall spec: non-negotiable goal, target architecture, domain classification table, Hybrid
   Exit Criteria, §5 Validation Strategy, 9-item Definition of Done, retained-JSON rationale bar,
   stop conditions. See its "2.14 Account/portfolio policy" section specifically.
2. `docs/superpowers/plans/2026-07-19-domain-data-model-v3-implementation-plan.md` — the
   overall wave roadmap and Global Constraints — **all of them**. See its "Wave 5E —
   Account/Portfolio Policy" section.
3. `docs/superpowers/status/wave5d-predictions-report.md` and
   `docs/superpowers/status/wave5d-handoff.md` — Wave 5D's full outcome, including two real
   findings a fresh session should not repeat: (a) a 7th real consumer the design spec's own
   inventory missed (`alert_manager.py`), found only via the archive-prerequisite grep — **run
   that grep for this wave's domain too, don't assume the spec's consumer list is complete**;
   (b) a Critical gap the final whole-branch review found that every earlier task-scoped review
   missed — a dual-write's default write path was never retired after archiving, which would have
   silently un-archived the file on the next real run. **Explicitly re-check this exact failure
   mode for Wave 5E**: if this wave's producer path is ever converted to write both the old file
   and the new SQLite table, confirm the old-file write is fully retired (not just "made
   redundant") before declaring the domain migrated.
4. `ADRs/029_persistence_domain_rationalization_and_retirement_gated_migration.md` — defines what
   "migrated" means. Wave 5B and 5C both found their domain's "code wired but no real test exists"
   caveat to be **literally true** — not a false alarm, twice. Wave 5D found a real, already-shipped
   data bug corrupting real backfilled rows, caught only by its real-cycle parity check, not any
   unit test. Assume nothing about this domain's real state until Task 0 verifies it directly.
5. **`docs/superpowers/status/wave5d-*` closeout note, read before planning:** this repo's git
   workflow has a hard, repeatedly-violated-then-corrected standing rule from the user: **always
   push a feature branch to `origin` before any worktree merge/removal step, and always get
   explicit user confirmation before a destructive worktree operation** (removing a worktree,
   deleting a branch) — self-verifying "the branch is already merged" is NOT a substitute for
   asking. This is saved as a permanent memory
   (`feedback_push_before_worktree_removal.md`) — read it, and follow it without exception this
   wave. A prior session violated this twice in the same closeout before the user caught it.
6. **Also read before planning, found during Wave 5D closeout, not part of Wave 5D's own scope
   but relevant to how this wave's real-write step should be handled:** a real, already-shipped
   `.gitignore` bug let 11 private `data/daily-briefs/*.json` files get committed and briefly
   pushed to `origin/main` via a routine `git add .`, because a blanket `!ARCHIVE/` negation
   pattern overrode the intended per-domain gitignore rules for archived copies of private data.
   This was fixed (commit `604ef8ee`) by adding explicit re-ignore rules for every known private
   domain's `ARCHIVE/` mirror. **`account_policy.json` is git-tracked, not gitignored** (confirmed
   below) — this specific bug class does not apply to this wave's own archive step — but if this
   wave's Task 0 discovers any gitignored file in its real scope, re-verify its `ARCHIVE/` mirror
   is actually re-ignored in `.gitignore`, don't assume the fix from commit `604ef8ee` already
   covers a domain it was never written for.

## Way of Working (reusable every wave — do not skip steps)

### 1. Setup
- Confirm `main` is up to date (`git pull origin main`) and note the current HEAD commit.
- Per this repo's CLAUDE.md rule #14, create an isolated worktree before any multi-file code
  change (plain `git worktree add -b <branch-name> .claude/worktrees/<name> main` is fine — do
  NOT rely on the `EnterWorktree` session tool if you anticipate needing a second worktree later
  in the same session, since it refuses to create a second one while already in one; Wave 5D hit
  this and had to mix tools, which made cleanup inconsistent).
- **Mandatory (CLAUDE.md pitfall #29):** immediately after creating the worktree, note that its
  `domain_model.sqlite`/`intelligence.sqlite` and any gitignored source data files are separate,
  unsynced copies from the main checkout's. `account_policy.json` is git-tracked (confirmed
  below), so the worktree DOES get a real copy of it via git — but `domain_model.sqlite` (where
  `portfolio_policy` lives) is gitignored and will need `--db`/explicit-path overrides pointing at
  the main checkout's real file for any check against real data, same pattern Wave 5D used
  throughout.
- After `npm install`/dependency setup in a fresh worktree, remember `mocha`/`pytest` won't be
  available until you run it. Wave 5D's worktree also needed, beyond the root `npm install`:
  `npm ci` in `tradingview-cdp/` (separate workspace), copying the entirely-gitignored `.agents/`
  directory from the main checkout (needed for `run_tests.py`'s T0 map-debt gate), and
  initializing `portfolio.json`/`portfolio-config.json` from their `.example` files per CLAUDE.md
  rule 13 — all one-time environment setup a fresh worktree needs, not part of any wave's actual
  code diff. Do this early, before running `python3 run_tests.py` for the first time.

### 2. Plan the wave (before touching code)
- Use `superpowers:writing-plans`.
- **Re-read the real, current code for every producer/consumer this wave touches — do not
  trust the overall plan's one-line file descriptions or the spec's original producer/consumer
  counts as ground truth.** Every Wave 5 sub-wave except 5A found the plan's initial assumptions
  wrong once real code was read; Wave 5D found a whole 7th consumer via a grep the earlier task
  reviews never ran. Do the same grep for this wave's domain BEFORE writing the task list, not
  only right before archiving.
- Write full TDD-ready detail for parts that are genuinely plannable now. For consumer-rewiring
  tasks spanning many files, it's fine to NOT pre-script exact code — state the real file list,
  the available repository functions, and the instruction "read this file's actual current code
  before editing."
- Include a **hard approval gate before any real data migration runs** (dry-run report first,
  explicit user sign-off, THEN the real write) — non-negotiable, tied to a real data-loss incident
  from before this corrective effort began.
- **Mandatory:** the plan's real-write task must explicitly state it runs against the
  **main checkout's** file paths (absolute or explicitly-flagged), and its verification step must
  query the **main checkout's** SQLite file directly.
- **Mandatory:** the wave plan document must include the design spec's actual required content
  **verbatim**: (1) the design spec's "Hybrid Exit Criteria" section applied to this wave's
  domain, (2) the design spec's full §5 Validation Strategy checklist as literal checkboxes, (3)
  the design spec's 9-item Definition of Done verbatim, (4) a computed **Context Bundle
  Completion Bar** number.
- **New this wave, add explicitly to the plan's own checklist:** a task (or an explicit step
  inside an existing task) that verifies, AFTER the producer cutover, that any dual-write's
  legacy-file write path is fully retired once all consumers are confirmed migrated — do not wait
  for a final whole-branch review to catch this the way Wave 5D's did. Write the negative-case
  test ("the old file is not recreated by a real producer call using its default arguments")
  as part of the producer-cutover task itself, not as an afterthought.
- Present the plan for user review before executing. Apply any requested revisions.

### 3. Execute the wave — wave-level autonomy (current standing instruction)
- **Do not stop after every individual task/subtask for approval.** Execute the approved wave
  plan end-to-end.
- **Do not run a separate full reviewer cycle after every small commit** unless a hard-stop
  condition (below) is triggered.
- Fix issues found along the way. Keep commits logical and reviewable.
- **Never trust a subagent's report at face value for anything consequential.** Dispatch
  independent verification for anything touching real data or a real cutover claim. If a subagent
  reports "ran the real write and verified N rows," the controller must independently re-run that
  verification query itself, in the main checkout, before accepting the claim.
- Use `superpowers:subagent-driven-development`: fresh implementer subagent per task, task
  briefs extracted via `scripts/task-brief`, review packages via `scripts/review-package`. For
  Critical/Important findings, dispatch a fix subagent, then re-review — don't self-fix as the
  controller for anything routine; the controller may fix directly only for a genuinely urgent,
  narrowly-scoped correction found late (e.g. Wave 5D's own final-review Critical fix), and should
  still get it independently re-reviewed afterward.
- **Model choice for all subagent dispatches: Sonnet or Haiku only. Never dispatch with Opus**,
  even where a skill's generic guidance suggests "use the most capable model."
- **Never use bare `git stash`/`git stash pop`** — the stash stack is shared across all
  worktrees. If you must stash (e.g. to clear pre-existing uncommitted files blocking a rebase),
  use `git stash push -u -m '<unique-tag>'`, capture the SHA immediately, restore with
  `git stash apply <sha>` (not `pop`), then drop only that specific entry by re-finding it by tag.
- **Never run `git mv`/`git rm`/any file-move operation directly against the main checkout's
  working tree** — even for a wave that also performs a real main-checkout data write. Only the
  actual database/ledger row write targets the main checkout directly; every file/code change,
  including archival, goes through the worktree → PR → merge flow, no exceptions.
- **Standing user rule, non-negotiable this wave (see item 5 above):** push the feature branch to
  `origin` before any worktree merge/removal step, and get explicit user confirmation before any
  destructive worktree operation. Do not substitute your own `git merge-base --is-ancestor`
  verification for the user's explicit go-ahead — do both, in that order (verify, THEN ask, THEN
  act), never verify-then-act without asking.

### Hard-Stop Conditions (stop immediately, report evidence, wait for user)
1. Source count and target row count do not reconcile.
2. Row/version/scenario count has an unexplained delta.
3. A new data shape is discovered without a test covering it.
4. A producer still writes the old JSON path as source of truth.
5. A real consumer still reads the old JSON path after claimed cutover.
6. Any script bypasses the approved repository/service layer and opens SQLite directly.
7. Tests fail in a new or migration-related way. **Wave 5D's real baseline at wave-exit was 44
   failing tests** (not the "2 known failures" this migration's docs repeated since Wave 5A) —
   re-confirm the current real baseline yourself at Task 0, don't trust either number blindly.
8. Archive-readiness grep still finds real runtime I/O to the old JSON path.
9. **A consumer is discovered that wasn't in this document's inventory** — amend the inventory,
   don't silently work around it. Wave 5D found a 7th consumer this exact way; run the same grep
   for this wave's domain before, not just at, the archive step.
10. Context-bundler still requires retired files without explanation.
11. **The wave would end in a permanent hybrid state** — including a dual-write whose legacy-file
    write path was never retired even after every consumer is confirmed migrated. This is exactly
    what Wave 5D's final whole-branch review caught after every earlier task review missed it —
    check for it explicitly and early this wave, don't rely on the final review alone to catch it.
12. The real write's verification was never independently re-run against the main checkout's
    actual files.
13. The plan or exit report repeats a prior effort's unverified claim without re-confirmation.
14. A real migration write touches more than one store and verification only checked one.
15. The wave's plan document does not contain the verbatim required spec sections.
16. A schema change to a live, populated table is done via in-place mutation without a verified
    rebuild-and-copy pattern (only relevant if this wave's `portfolio_policy` insert requires any
    schema change beyond the already-existing empty table — confirm at Task 0 whether it does).
17. **A worktree or branch is deleted without both (a) confirming the branch is pushed to origin
    and merged, and (b) explicit user confirmation of the deletion itself.**

Before archiving anything, all of these must be independently confirmed true (not assumed):
producers cut over, all real consumers cut over, archive-readiness grep clean, repository-path
(anti-bypass) grep clean, tests pass at the documented baseline, rollback **physically exercised**
(not just described) with evidence, a real-cycle parity diff run and matched, a real-data
(non-fixture) test added and passing, AND the real write's row counts have been independently
re-verified against the main checkout's live SQLite file, not just the worktree's.

### 4. Wave exit
- Produce `docs/superpowers/status/wave5e-account-policy-report.md` — KPI table, producer/
  consumer cutover table, real bugs found and fixed, validation results, archive evidence,
  rollback instructions with evidence, commit list. Match `wave5d-predictions-report.md`'s depth.
- Ensure all wave commits are on the wave branch; **push it to origin**; open a PR to `main` (do
  not merge it yourself unless explicitly told to).
- Verify the remote branch matches local HEAD exactly before reporting the PR as ready.
- Dispatch a final whole-branch review (Sonnet, not Opus) before declaring the wave done — Wave
  5D's own final review found a real Critical gap every task-scoped review missed; do not skip
  this step or treat it as a formality.
- Produce `docs/superpowers/status/wave5e-handoff.md`.
- **Stop. Do not start Wave 6 (Program Closure).** After the user reviews/merges the PR: **first
  confirm with the user before any worktree/branch cleanup, per item 5 above** — then follow
  `.agent/rules/git-operations.md`'s "End-of-Wave Closeout Playbook": fetch, sync local `main` to
  `origin/main` (check for other in-progress/unpushed local-main-only commits first — Wave 5D's
  own real-data commits sat unpushed on local `main` for the whole wave and were nearly lost to
  worktree cleanup before being caught), verify the merged commit is an ancestor, **re-run the
  real migration's row-count verification directly against the now-updated main checkout one more
  time**, remove the worktree, delete local AND remote feature branches, confirm clean
  `git worktree list`/`git branch --list` — then check whether Wave 6's prerequisites are met
  (all of Waves 0–5E merged) before writing anything for it; Wave 6 is the program's closing audit,
  not a normal migration wave, and may warrant its own separate kickoff-prompt-writing pass rather
  than reusing this template verbatim.

## This Wave's Scope (Wave 5E)

Per the overall plan/spec (§ "Wave 5E — Account/Portfolio Policy" / "2.14 Account/portfolio
policy"): migrate `account_policy.json` **and** `target-portfolio.json`'s `globalSettings`
sub-object → `portfolio_policy` (4 numeric columns + 2 JSON rule-blob columns — the JSON columns
are the approved exception, already justified in spec §2.14/§2.17, not a new decision needed at
implementation time).

**Real current state, verified fresh 2026-07-25 (re-verify again at Task 0, don't trust this
verbatim without a fresh check — same discipline every prior wave has followed):**

- `account_policy.json` (git-tracked, confirmed via `git check-ignore` returning nothing —
  **archiving this file is a real `git mv`, not a local-only `mv`**, unlike the daily-briefs
  domain Wave 5C closed):
  ```json
  {
    "accountPreferenceRules": [
      { "match": "usDividendPayer", "prefer": "RRSP", "reason": "treaty withholding exemption" },
      { "match": "highGrowthEquity", "prefer": "TFSA", "reason": "tax-free compounding" },
      { "match": "default", "prefer": "TFSA" }
    ],
    "psuFundingRule": { "ticker": "PSU-U.TO", "sameAccountOnly": true, "sharesFormula": "ceil(N * price / 100)" },
    "riskBudgetCaps": { "maxMarginalRiskContributionPct": 25, "maxClusterVarianceContributionPct": 60 },
    "bandConfig": { "relativePct": 20, "absolutePct": 1.5, "criticalMultiplier": 2.0 }
  }
  ```
- **Real consumers of `account_policy.json`'s fields, re-verified via fresh grep (4, matching the
  spec's own count exactly):** `order_risk_gates.py`, `rebalancer.py`,
  `investment_screener/backend/src/utils/zod-schemas.ts`,
  `investment_screener/backend/src/services/ThesisService.ts`. **Known false positives, confirmed
  not real I/O:** `audit_json_usage.py` (its own classification self-reference, same pattern as
  Wave 5D's `predictions.jsonl` false positive), `InvestmentRepository.ts` (a docstring comment
  mentioning "bandConfig," not a real field read), `migrations/remove_drift_threshold_fields.py`
  (a one-time historical migration script, not a live producer or consumer).
- **`target-portfolio.json`'s `globalSettings` — a separate real sub-scope within this same wave,
  confirmed present and real:**
  ```json
  { "rebalanceFrequency": "quarterly", "portfolioValueUSD": 30797 }
  ```
  These map to `portfolio_policy.rebalance_frequency`/`portfolio_value_usd_target`. **Real
  consumers, re-verified via fresh grep:** `zod-schemas.ts`, `ProjectionRepository.ts`,
  `ThesisService.ts`. `migrate_target_portfolio_to_sqlite.py` also references these fields but is
  Wave 2's own historical migration script, not a live consumer needing cutover.
  **`globalSettings` is embedded inside `target-portfolio.json`, which is itself the retained-JSON
  exception domain from Wave 2 (per Wave 6's own pre-analysis note already on file — see
  `docs/superpowers/plans/2026-07-19-domain-data-model-v3-implementation-plan.md`'s Wave 6
  section) — confirm at Task 0 whether cutting `globalSettings` alone out of that file (while the
  rest of `target-portfolio.json` remains JSON, per Wave 2's approved exception) is coherent, or
  whether it needs its own explicit Retained-JSON Rationale Bar entry distinguishing "this one
  sub-object migrates now" from "the rest of the file stays JSON for now, per Wave 2/Wave 6."**
  This is a real scoping question the plan's one-line Wave 5E summary doesn't resolve — surface it
  to the user during planning, don't assume either direction.
- **`portfolio_policy` table:** already exists in `domain_model.sqlite` (created by Wave 0's
  schema foundation), currently **0 rows** — this wave is the first to actually populate it.
- **No real producer today** — both `account_policy.json` and `target-portfolio.json`'s
  `globalSettings` are manually maintained; the only historical mutation is
  `remove_drift_threshold_fields.py` (a one-time migration script, not a live producer). Per spec
  §2.14, this wave does not need to build new producer surface (unlike Wave 4's `cash_flows.json`,
  which needed a genuinely new write path) — confirm this is still accurate at Task 0, and decide
  how manual edits to the SQLite-backed policy should work going forward (a small CLI, matching
  the pattern other manually-maintained domains in this migration have used, or direct SQL with a
  documented procedure — a real design decision this wave's plan must make explicitly, not leave
  implicit).

**Known false-positive risk, per the pattern in every prior wave except Wave 4 and Wave 5A:**
treat any producer/consumer count above as unverified until Task 0 re-confirms it against real
current code — this document's own counts were gathered fresh 2026-07-25, but code may have
changed since, and Wave 5D proved the spec's own inventory can still be wrong even after multiple
prior "confirmed" passes.

## Starting State (as of this handoff)

- `main` @ `604ef8ee` (Waves 0–5D fully merged and closed out; PR #103, #104, #105 all merged —
  the last three PRs before this handoff, covering a portfolio-summary refresh/exchange-rate bug
  fix, Wave 5D itself, and a thesis-sync watchlist-filter bug fix, none part of this migration's
  wave sequence but all in `main`'s history by this point). A `.gitignore` fix (commit `604ef8ee`
  itself) also landed after Wave 5D closed, correcting a real privacy bug where `ARCHIVE/` mirrors
  of gitignored domains were briefly committed — re-verify this fix still holds if this wave's
  Task 0 finds any gitignored file in its real scope (it currently should not — both
  `account_policy.json` and `target-portfolio.json` are git-tracked).
- No worktree currently checked out for this migration — start fresh per the Setup step above.

## Do Not

- Do not start implementation before the wave plan is written and reviewed.
- Do not skip the fresh-code-read step and copy assumptions from the overall plan/spec or from
  this kickoff prompt's own "verified 2026-07-25" numbers without re-confirming them.
- Do not run a real data migration without the dry-run-then-approval gate.
- **Do not run or verify a real data migration write anywhere other than the main checkout's
  actual files.**
- Do not archive anything before every Hard-Stop Condition is independently confirmed, including
  a physically-executed rollback exercise and (if applicable) a real-cycle parity diff.
- Do not merge to `main` yourself without being told to.
- Do not dispatch any subagent with the Opus model — Sonnet or Haiku only.
- Do not pass `isolation: "worktree"` to the Agent tool when dispatching implementers into a
  worktree you've already prepared.
- Do not run any `git mv`/file-move operation directly against the main checkout.
- Do not write a wave plan with a self-invented, shortened Definition of Done.
- **Do not delete, remove, or merge-clean-up any worktree or branch without both pushing it to
  origin first AND getting explicit user confirmation for the deletion itself** — this is a
  standing, repeatedly-enforced user rule, not a per-wave judgment call.
- Do not declare a dual-write's legacy-file path "retired" without a negative-case test proving a
  real producer call with default arguments no longer creates the old file.
- Do not start Wave 6 after this wave's exit — stop and wait for review, same as every prior
  wave. Write Wave 6's own kickoff material only after confirming all of Waves 0–5E are actually
  merged, and treat it as a distinct closing-audit pass, not a mechanical copy of this template.
