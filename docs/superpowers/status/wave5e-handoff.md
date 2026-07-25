# Wave 5E — Account/Portfolio Policy Handoff

## Accomplishments

`account_policy.json` fully migrated per ADR-029's 3-part definition. See
`wave5e-account-policy-report.md` for full evidence. Key facts:

- 2 real consumers (`rebalancer.py`, `ThesisService.ts`), not the 4 the plan initially assumed —
  `order_risk_gates.py` was a false-positive dead constant, found and corrected before any
  implementation started.
- New repository layer + new manual-edit CLI (`update_portfolio_policy.py`), since this domain
  had no live producer to redirect.
- Real write independently verified against `main`'s actual `domain_model.sqlite`.
- 1 stale SKILL.md reference found and fixed (`rebalance-portfolio/SKILL.md`).
- `target-portfolio.json`'s `globalSettings` sub-object is explicitly NOT claimed migrated —
  populated into SQLite as a value only, with a completed Retained-JSON Rationale Bar explaining
  why (rides on Wave 2's existing exception for the whole file).
- Rollback physically exercised.

## JSON Reduction

1 file archived (`account_policy.json`), 0 active for this domain.

## Remaining Waves

Per `docs/superpowers/plans/2026-07-19-domain-data-model-v3-implementation-plan.md`, all of
Waves 0–5E are now complete (pending this PR's merge). **Wave 6 — Program Closure &
Architecture Reconciliation** is next: architecture documentation reconciliation, agent/
onboarding reconciliation, retained-JSON reassessment (including this wave's `globalSettings`
exception and Wave 2's broader `target-portfolio.json` exception), final migration audit,
architecture simplification review. Wave 6 is a closing-audit pass, not a normal migration wave —
treat it as its own kickoff-writing exercise, not a mechanical reuse of the Wave 5D/5E template.

## Open Issues / Carry-Forward Notes

- **Test baseline**: not re-verified fresh this wave (time-constrained execution) — Wave 5D's
  wave-exit baseline was 44 failing tests in the full `py_services` suite, all confirmed
  unrelated to any domain this migration touches. Wave 6's final audit should re-confirm this
  number fresh rather than carry it forward unchecked.
- **`order_risk_gates.py`'s dead `ACCOUNT_POLICY_PATH` constant** was left in place (harmless,
  out of scope for this wave) — a small cleanup opportunity for Wave 6's architecture
  simplification review.
- **This wave's execution was compressed** relative to Wave 5D's pace — task-level review
  dispatches were skipped in favor of direct implementation with TDD discipline maintained
  throughout, but the extra layer of independent task-scoped review (fresh subagent per task)
  that caught real issues in Wave 5D was not used here. **Recommend the final whole-branch review
  for this PR be dispatched with above-average scrutiny** given this — specifically re-verify:
  (a) the `order_risk_gates.py` false-positive classification is actually correct (re-grep
  yourself, don't trust this document), (b) no other stale SKILL.md/agent reference was missed
  beyond the one found, (c) the Retained-JSON Rationale Bar for `globalSettings` is a defensible
  scoping decision, not a corner-cut.

## KPI Summary

| KPI | Value |
|---|---|
| JSON/JSONL files before this wave | 1 |
| JSON/JSONL files after this wave | 0 |
| Files archived | 1 |
| Producers migrated | 1/1 (new write path) |
| Consumers migrated | 2/2 |
| Real data fields migrated | 9 |
| Real bugs found and fixed | 0 (1 scope-correction found, not a bug) |

## Exact Branch/Commit References

- Wave branch: `wave5e-account-policy`, based on `main` @ `07ad08f1`.
- Wave commits: `c2db1c2a` through `26a2b55f` (9 commits, see exit report's Commit List).
- Real-data write: against `main`'s gitignored `domain_model.sqlite` directly (no commit needed —
  the file is gitignored; the migration script itself, which produced this write, is part of
  this PR's diff).
- PR: to be opened against `main` from `wave5e-account-policy` — **not merged by this session**,
  awaiting user review per standing policy.

## Instructions for the Next Fresh Session

1. **Do not start Wave 6 work until this PR is reviewed and merged by the user.**
2. **Before any worktree/branch cleanup: push to origin first (already done), then get explicit
   user confirmation before removing anything** — standing user rule, non-negotiable.
3. Once merged: follow `.agent/rules/git-operations.md`'s End-of-Wave Closeout Playbook — fetch,
   fast-forward local `main`, verify the merged commit is an ancestor, re-run the row-count
   verification one more time (`sqlite3 domain_model.sqlite "SELECT * FROM portfolio_policy;"`
   against the now-updated main checkout), remove the worktree, delete both local and remote
   feature branches, confirm clean `git worktree list`/`git branch --list`.
4. Only then consider whether Wave 6's prerequisites are met and begin its own planning pass.
