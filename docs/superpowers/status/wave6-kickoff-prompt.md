# Wave 6 Kickoff Prompt — Domain Data Model v3.2 Program Closure & Architecture Reconciliation

Hand this whole file to a fresh Claude Code session (new context, no prior memory of this
migration) to start Wave 6. **This is fundamentally different from Waves 0–5E: it is not a
code-migration wave.** It is the program's closing audit and documentation/agent-ecosystem
reconciliation pass, run only after every functional wave is complete and merged.

---

## Read These First, In Order

1. `docs/superpowers/specs/2026-07-19-domain-data-model-v3-implementation-design.md` — the
   overall spec: non-negotiable goal, target architecture, domain classification table, Hybrid
   Exit Criteria, Retained-JSON Rationale Bar, stop conditions.
2. `docs/superpowers/plans/2026-07-19-domain-data-model-v3-implementation-plan.md` — the overall
   wave roadmap. See its "### Wave 6 — Program Closure & Architecture Reconciliation" section
   (near the end of the file) for the 5-item scope this kickoff prompt expands on below, and its
   pre-written analysis of `target-portfolio.json`/`ThesisService.ts` (already done 2026-07-24,
   field-by-field) — read that analysis before assuming this domain "cannot be migrated without
   new schema," since that framing significantly overstated the real barrier.
3. `docs/superpowers/status/wave5d-predictions-report.md`, `wave5d-handoff.md`,
   `wave5e-account-policy-report.md`, `wave5e-handoff.md` — the final two functional waves'
   outcomes, both merged. Both found real, non-obvious gaps that only a rigorous, independently-
   verified process caught (Wave 5D: a 7th consumer the spec's own inventory missed, and a
   dual-write that was never retired, caught only by the *final* whole-branch review after every
   task-scoped review missed it; Wave 5E: a false-positive consumer the plan assumed was real).
   **Apply the same discipline to Wave 6's own claims** — this wave produces documentation and
   makes retention decisions, not code, but its conclusions are just as capable of being wrong if
   not independently re-verified against real, current code and data.
4. `ADRs/029_persistence_domain_rationalization_and_retirement_gated_migration.md` and
   `ADRs/030_portfolio_totals_computed_not_stored.md` — what "migrated" means, and the
   "store facts, compute aggregates" principle that should inform any remaining retention
   decisions this wave makes.
5. **Read before doing anything, found during Wave 5D/5E closeout (2026-07-24/25), not part of
   any wave's own scope but directly relevant to how this wave should be run:**
   - **Standing user rule, repeatedly violated then corrected, now saved as a permanent memory
     (`feedback_push_before_worktree_removal.md`):** always push a feature branch to `origin`
     before any worktree merge/removal step, and always get explicit user confirmation before a
     destructive worktree operation (removing a worktree, deleting a branch). Self-verifying "the
     branch is already merged" is NOT a substitute for asking. Follow this without exception.
   - **A real `.gitignore` privacy bug** (commit `604ef8ee`) let 11 private `daily-briefs` JSON
     files get briefly committed and pushed to `origin/main`, because a blanket `!ARCHIVE/`
     negation overrode intended per-domain gitignore rules. **This was later reversed entirely**
     (commit `52f354cb`, 2026-07-25): `ARCHIVE/` is now fully gitignored going forward (no more
     `!ARCHIVE/` negation, no per-domain re-ignore rules needed) — this means every wave's
     archived files from Wave 5D onward (`predictions.jsonl`, `account_policy.json`) remain
     git-tracked from when they were committed, but **any future archive step in this program
     will NOT be git-tracked** unless `.gitignore` is deliberately overridden for that specific
     path. If Wave 6's "final migration audit" (item 4 below) expects every wave's `ARCHIVE/`
     mirror to be git-tracked and durable, **that assumption is no longer true for anything
     archived after 2026-07-25** — verify this explicitly rather than assuming the pattern still
     holds.
   - **`docs/superpowers/` itself is now gitignored going forward** (same commit `52f354cb`) —
     existing files (including this one, and everything referenced in item 3 above) remain
     git-tracked since gitignore doesn't retroactively untrack existing files, but any NEW status
     report / kickoff prompt / plan this wave writes will NOT be committed to git unless you
     explicitly `git add -f` it. **Decide explicitly at the start of this wave whether Wave 6's
     own exit report/handoff should be force-added (breaking the new convention for a
     program-closing document) or left local-only** — don't silently assume either way.
   - **A real bug in `verify_thesis_sync.py`** (fixed in PR #105) excluded pure-watchlist tickers
     from the thesis-documentation requirement — if this wave's architecture-documentation
     reconciliation touches thesis/portfolio sync tooling, confirm this fix is still correct
     against current real data, don't assume it's permanently settled.
   - **A real bug in Portfolio Summary's exchange-rate/timestamp logic** (fixed in PR #103) was
     unrelated to this migration but found during the same session — if Wave 6's architecture
     docs cover the frontend's SQLite-read paths, confirm this fix is reflected accurately.

## What Makes Wave 6 Different From Every Prior Wave

- **No new SQLite tables, no consumer cutovers, no real data migration write** (unless item 3's
  retained-JSON reassessment concludes a small addition — e.g. `thesisBreakers`/`changeLog`
  schema — is worth doing now; if so, that sub-piece follows the normal TDD/worktree/dry-run/
  approval-gate discipline every functional wave used, scoped as its own mini-task within Wave 6,
  not exempted from any of it).
- **Its deliverables are documents and decisions**, not code: refreshed architecture docs, updated
  agent/onboarding instructions, a completed Retained-JSON Rationale Bar for every remaining
  exception, a program-level KPI rollup, and a dead-code/duplicate-path cleanup pass.
- **Still requires the same rigor discipline**: every claim in its own output ("the schema doc now
  matches reality," "no stale JSON references remain in any skill") must be independently
  verified against real, current code — not asserted from memory of what earlier waves reported.

## Way of Working

### 1. Setup
- Confirm `main` is up to date and note current HEAD.
- Create an isolated worktree for this wave's actual doc/code edits (`git worktree add -b
  wave6-program-closure .claude/worktrees/wave6-program-closure main`) — even though this wave is
  mostly documentation, CLAUDE.md rule #14 still applies to any multi-file change, and this wave
  touches many files (architecture docs, agent instructions, multiple SKILL.md files).
- Remember this worktree needs the same one-time environment setup prior waves needed (frontend +
  `tradingview-cdp` `node_modules`, copying the gitignored `.agents/` directory from the main
  checkout if `run_tests.py`'s T0 gate is needed, `portfolio.json`/`portfolio-config.json` from
  their `.example` files) — none of this is wave-specific work, just fresh-worktree hygiene.

### 2. Task 1 — Architecture Documentation Reconciliation
- Export the complete final SQLite DDL (both `domain_model.sqlite` and `intelligence.sqlite`)
  directly from the real schema, not from memory of what any wave's plan said the schema should
  be — `db_client.py`'s own `initialize_db()` functions are the source of truth; diff against
  `docs/architecture/domain-data-model.md` and `docs/architecture/
  supplementary-domain-schemas.md` and correct any drift found.
- Refresh the Mermaid ERD in the design spec (§3) to match the real, final table set — including
  `portfolio_policy` (Wave 5E) and every `intelligence_event` type added across Waves 5A–5D.
- Regenerate the physical schema docs / data dictionary.
- Verify all of it against the actual shipped schema — run a real query, don't trust a prior
  wave's report of what the schema contains.

### 3. Task 2 — Agent & Onboarding Reconciliation
- Review and update `toolkit-onboarding-guide` (skill).
- Validate startup/bootstrap instructions, coordinator-agent routing logic, and the TradingView
  onboarding path against the real, current SQLite-first architecture.
- **Grep every SKILL.md/agent markdown file across `plugins/` for every filename this whole
  program archived** (`predictions.jsonl`, `ta-sweep-results.json`, `data/daily-briefs/*.json`,
  `account_policy.json`, plus Wave 1's `projections/*.json` and Wave 2/3's `target-portfolio.json`/
  `portfolio.json` references that are still accurate since those files are retained exceptions)
  — do not assume prior waves' own "Context Bundle Completion Bar" claims were complete; Wave 5D
  found stale references at its own wave-exit that an earlier grep in the same wave had missed.
  Fix anything found that still points at an archived file's old filename/field shape.

### 4. Task 3 — Retained-JSON Reassessment
Revisit every exemption approved along the way. At minimum:
- `target-portfolio.json` / `ThesisService.ts` — the pre-analysis already done 2026-07-24 (see
  the overall plan, and item 2 in "Read These First" above) found the real barrier to retiring
  this file is smaller than Wave 2 originally assumed: only `thesisBreakers` and `changeLog`
  genuinely need new schema (`bandConfig` turned out to belong to `account_policy.json`, already
  migrated in Wave 5E; `standingDecision` is already solved, just not wired into
  `ThesisService.ts`'s read path; `shares` is a stale data-quality bug, not a migration target,
  recommend deleting the field from the document rather than adding schema for it). **Re-verify
  this analysis against real, current data before acting on it** — it was correct as of
  2026-07-24, but `target-portfolio.json` has been edited since (real thesis-content commits
  landed 2026-07-25, `ea6e995c`).
- `thesis_breaker_state.json` — Wave 2 folded this domain's target schema
  (`investment.thesis_breaker_status`) in already; confirm whether the JSON file itself was ever
  actually archived, or whether it's still a live read/write path for some consumer. Real
  consumers as of this kickoff prompt (re-verify): `order_risk_gates.py`, `rebalancer.py`,
  `harvest_predictions.py`, `thesis_breakers.py`, `risk_officer.py`.
- `account_policy.json`'s two retained JSON-blob columns
  (`account_preference_rules_json`/`psu_funding_rule_json` inside `portfolio_policy`) — already
  justified per spec §2.14/§2.17, confirm this reasoning still holds, no new decision needed.
- `target-portfolio.json`'s `globalSettings` sub-object — Wave 5E's own Retained-JSON Rationale
  Bar (see `wave5e-account-policy-report.md`) explicitly deferred full resolution of this to
  whichever wave fully migrates `target-portfolio.json`'s remaining JSON surface — if this wave
  does that (see above), close out that rationale bar's "Future migration trigger" row.
- For each: confirm the exemption is still justified, evaluate whether a schema change would now
  eliminate it, and decide migrate / redesign / formally retain with documented rationale — using
  the spec's completed Retained-JSON Rationale Bar table format (§2.18), not a shortened version.

### 5. Task 4 — Final Migration Audit
- JSON/JSONL file counts before vs. after across the whole program (Wave 0 baseline vs. now).
- Remaining runtime JSON producers/consumers — should be zero outside approved exceptions.
- Full SQLite table/repository/service inventory (`py_services/domain_model/`,
  `py_services/intelligence/`, and their TS mirrors).
- A program-level Wave KPI rollup, aggregating every wave's own KPI table
  (`wave0` through `wave5e` status reports) into one final table.
- **Re-verify the real test baseline fresh** — Wave 5D's wave-exit baseline was 44 failing tests
  in the full `py_services` suite (up from an originally-documented "2 known failures" that was
  stale since Wave 5A); confirm this number is still accurate or has changed, don't carry forward
  either the stale "2" or the "44" without checking.

### 6. Task 5 — Architecture Simplification Review
- Remove temporary compatibility layers, migration-only code, dead adapters, and duplicate access
  paths left behind by incremental wave-by-wave cutover. Known candidates, confirm each still
  applies before removing:
  - `rebalancer.py`'s deprecated-but-kept `account_policy_path`/`ACCOUNT_POLICY_PATH` (Wave 5E,
    flagged by its final review as a small cleanup opportunity, deliberately not removed then
    because 6 test call sites still passed it by name).
  - `order_risk_gates.py`'s dead `ACCOUNT_POLICY_PATH` constant (never read, confirmed at Wave
    5E's Task 0 — left in place then as out of scope).
  - Any `prediction_ledger.py` JSONL-writing code paths that survived Wave 5D's dual-write
    retirement fix as unused primitives (`_append_jsonl`, `load_predictions`, `load_graded` were
    deliberately KEPT for `--validate` CLI utility — confirm this CLI is still a real, wanted
    capability before removing, don't delete it reflexively).
- Confirm the final architecture actually matches the SQLite-pivot objective stated at the top of
  the overall implementation plan, not a permanent hybrid — this is the single most important
  check in the whole wave, since it's the entire reason this corrective effort (ADR-029) exists.

### 7. Wave Exit
- Produce `docs/superpowers/status/wave6-program-closure-report.md` with the program-level KPI
  rollup, retained-JSON rationale bars for every remaining exception, and evidence for each of the
  5 tasks above.
- **Decide and state explicitly whether this report (and any other Wave 6 output) is force-added
  to git** (`git add -f`) given `docs/superpowers/` is now gitignored by default — this is a real
  decision Wave 6 must make consciously, not by default.
- Push the branch to `origin` (or, if outputs are intentionally local-only per the decision above,
  state that explicitly instead of silently having nothing to push).
- Open a PR if there's a code component (schema doc regeneration, agent-instruction fixes,
  simplification-review code deletions); confirm with the user whether a PR is even the right
  mechanism if the output is mostly gitignored documentation.
- **Get explicit user confirmation before any worktree/branch cleanup**, same as every prior wave.

## Do Not
- Do not assume any prior wave's self-reported claim is still accurate without re-verifying
  against real, current code/data — this discipline applies to Wave 6's own conclusions just as
  much as to what it inherits.
- Do not silently assume `docs/superpowers/` outputs will be committed the way every prior wave's
  were — the gitignore rule changed after Wave 5E closed; decide explicitly.
- Do not silently assume future `ARCHIVE/` mirrors will be git-tracked the way Wave 5D's/5E's
  were — the `!ARCHIVE/` negation was removed; decide explicitly per file if durability matters.
- Do not remove any "dead code" candidate without confirming it's genuinely unused by a real
  current caller, not just unused by the specific consumer that was cut over in the wave that
  flagged it as a cleanup candidate.
- Do not skip the physically-executed verification discipline just because this wave's output is
  "mostly documentation" — a wrong architecture doc or a stale agent instruction is a real defect
  with real consequences for whoever reads it next.
- Do not merge to `main` yourself without being told to, if a PR is opened.
- Do not dispatch any subagent with the Opus model — Sonnet or Haiku only.
- **Do not delete, remove, or merge-clean-up any worktree or branch without both pushing it to
  origin first AND getting explicit user confirmation for the deletion itself.**
