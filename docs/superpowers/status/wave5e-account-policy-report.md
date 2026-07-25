# Wave 5E — Account/Portfolio Policy Migration Exit Report

**Status:** Complete, PR pending review/merge. Do not start Wave 6 until this PR is reviewed and
merged, and the post-merge closeout playbook has run.

## Accomplishments

- Migrated `account_policy.json` (4 fields: `accountPreferenceRules`, `psuFundingRule`,
  `riskBudgetCaps`, `bandConfig`) into a singleton `portfolio_policy` row in
  `domain_model.sqlite`, plus populated `rebalance_frequency`/`portfolio_value_usd_target` from
  `target-portfolio.json`'s `globalSettings` sub-object (value-only backfill, not a claimed
  consumer cutover — see Retained-JSON Rationale Bar below).
- **Real scope correction found during Task 0, before any code was written**: the plan's
  originally-assumed 4th consumer, `order_risk_gates.py`, is a false positive — it declares
  `ACCOUNT_POLICY_PATH` as a module constant but never opens/reads the file anywhere; the real
  values are hardcoded elsewhere in that file. Confirmed real consumers: `rebalancer.py` and
  `ThesisService.ts::getAccountPolicy()` — 2, not 4.
- New repository layer: `portfolio_policy_repository.py` (Python) and
  `PortfolioRepository.getPortfolioPolicy()` (TS), both singleton-row, mirroring
  `exchange_rate_repository.py`'s established pattern.
- **Real migration script + real write**: dry-run (9/9 fields, 0 skipped) → explicit user
  sign-off → real `--write` against `main`'s actual `account_policy.json`,
  `target-portfolio.json`, and `domain_model.sqlite` (all 3 path args explicit absolute paths) →
  independently re-verified: real row content matches `account_policy.json` byte-for-byte
  (`accountPreferenceRules`/`psuFundingRule` JSON, all 5 numeric caps/bands) and
  `target-portfolio.json`'s `globalSettings` (`quarterly`/`30797`).
- Both real consumers cut over with real-sqlite (not mocked) tests proving the SQLite read path
  specifically (not just that the function still returns *a* value): `rebalancer.py`'s new test
  points `account_policy_path` at a nonexistent file and confirms the plan still computes
  correctly from SQLite alone; `ThesisService.ts`'s new test confirms the same with no sibling
  `account_policy.json` present.
- New manual-edit write path (`update_portfolio_policy.py`), since `account_policy.json` had no
  code producer — this domain was manually maintained, and the migration explicitly could not
  redirect an existing producer (matches spec §2.14's documented constraint).
- Physically-executed rollback exercise: reverted both consumer-cutover commits in a throwaway
  worktree, confirmed 45/45 Python + 6/6 TS tests pass against the reverted, JSON-only code.
  Cleaned up, `main` untouched.
- `account_policy.json` archived via real `git mv` (git-tracked file, not gitignored). Its
  `audit_json_usage.py` allowlist entry removed.

## Retained-JSON Rationale Bar — `target-portfolio.json`'s `globalSettings` sub-object

| Field | Answer |
|---|---|
| File / pattern | `target-portfolio.json: globalSettings` (`rebalanceFrequency`, `portfolioValueUSD`) |
| Why not SQLite? | It IS also written to SQLite (`portfolio_policy.rebalance_frequency`/`portfolio_value_usd_target`) — this bar concerns why the JSON field is *retained*, not why SQLite isn't used |
| Why not event model? | N/A — config, not an event |
| Why not generated from SQLite? | `target-portfolio.json` as a whole is Wave 2's approved retained-JSON exception; regenerating just this sub-object would fragment that file's single-source editing story |
| Category | config (rides on Wave 2's already-approved exception for the whole file) |
| Who writes it? | Manual edit, same as the rest of `target-portfolio.json` |
| Who reads it? | `ThesisService.ts` line 625 (pure passthrough into an export payload, no decision logic) — NOT cut over this wave |
| What breaks if removed? | Nothing today (passthrough only) — but removing it without updating that call site would be a needless breaking change this wave doesn't need to make |
| User-approved exception? | Rides on Wave 2's existing approval for the file as a whole — not a new decision |
| Future migration trigger | If a future wave fully migrates `target-portfolio.json`'s remaining JSON surface, `globalSettings` retires with it then |

## JSON Reduction

1 file archived (`account_policy.json`, real `git mv`), 0 active for this domain. Note:
`target-portfolio.json` itself is unaffected (stays JSON per Wave 2's exception, see rationale
bar above) — this wave's JSON reduction is scoped to `account_policy.json` alone.

## Producer/Consumer Cutover Table

| Component | Type | Before | After | Cutover status |
|---|---|---|---|---|
| `rebalancer.py::compute_rebalance_plan()` | Consumer | `json.loads(account_policy_path)` | `_load_account_policy_from_db(db_path)` via `portfolio_policy_repository` | **DONE** |
| `ThesisService.ts::getAccountPolicy()` | Consumer | `fs.readFileSync(ACCOUNT_POLICY_FILE)` + zod parse | `PortfolioRepository.getPortfolioPolicy()` reshaped + zod parse | **DONE** |
| `order_risk_gates.py` | (false positive, not a real consumer) | Declared `ACCOUNT_POLICY_PATH`, never read | N/A — dead constant, left as-is (out of scope, harmless) | N/A |
| (no producer) | Producer | Manually maintained JSON | `update_portfolio_policy.py` CLI (new write path) | **DONE** |

## Real Bugs / Scope Findings

1. **`order_risk_gates.py` false-positive consumer** — the design spec implicitly assumed 4
   consumers per its own inventory language; direct code inspection at Task 0 found this file
   never actually reads `account_policy.json`, only declares a dead path constant. Corrected the
   plan before any implementation started, matching the standing discipline every wave in this
   migration follows.
2. No other real bugs found this wave (unlike Wave 5D, which found 3). This domain's smaller
   scope (2 real consumers, no live producer, no event-sourced ledger involved) had fewer moving
   parts for a bug to hide in.

## Validation Results

- Directly-affected tests: 84/84 Python passing (`test_portfolio_policy_repository.py`,
  `test_migrate_account_policy_to_sqlite.py`, `test_update_portfolio_policy.py`,
  `test_rebalancer.py`, `test_audit_json_usage.py`), 19/19 TS passing
  (`PortfolioRepository.spec.ts`, `ThesisService.spec.ts`).
- `npm run build -w backend` — clean, no type errors.
- Real write independently re-verified against `main`'s actual `domain_model.sqlite`: row content
  matches `account_policy.json`/`target-portfolio.json`'s `globalSettings` exactly.
- Archive-prerequisite grep: zero remaining real-I/O matches for `account_policy.json` outside
  test files and the migration script's own (legitimate, one-time) source read.
- Rollback physically exercised (see `wave5e-rollback-exercise-report.md`).

## Archive Evidence

```
$ ls investment_screener/backend/data/account_policy.json
ls: investment_screener/backend/data/account_policy.json: No such file or directory
$ ls ARCHIVE/investment_screener/backend/data/account_policy.json
ARCHIVE/investment_screener/backend/data/account_policy.json
```

## Rollback Instructions (physically exercised — see `wave5e-rollback-exercise-report.md`)

1. `git revert --no-commit` the two consumer-cutover commits (`31f44075`, `25f639a8`).
2. Restore `investment_screener/backend/data/account_policy.json` via `git mv` back from
   `ARCHIVE/investment_screener/backend/data/account_policy.json` (real `git mv`, git-tracked).
3. Confirm `rebalancer.py`/`ThesisService.ts` (reverted) read the restored file correctly and the
   pre-wave test suite passes (45/45 Python + 6/6 TS confirmed in the physical exercise).
4. No SQLite rollback needed for the `portfolio_policy` row — additive, harmless to leave in
   place (reverted code simply stops reading it).

## Commit List

```
c2db1c2a feat: add portfolio_policy_repository (Wave 5E Task 1)
597a6d0a feat: add PortfolioRepository.getPortfolioPolicy() (Wave 5E Task 2)
1003b72f feat: add account_policy.json -> portfolio_policy migration script (Wave 5E Task 3, dry-run/write)
25f639a8 feat: cut rebalancer.py over to portfolio_policy reads (Wave 5E Task 4a)
31f44075 feat: cut ThesisService.getAccountPolicy() over to portfolio_policy reads (Wave 5E Task 4b)
8ceaffc3 feat: add update_portfolio_policy.py CLI, the new manual-edit write path (Wave 5E Task 5)
980179f4 docs: Wave 5E rollback exercise report (physically executed)
cf53516f chore: archive account_policy.json, remove its audit_json_usage allowlist entry (Wave 5E Task 7)
26a2b55f chore: remove account_policy.json from audit_json_usage allowlist (Wave 5E Task 7 follow-up)
```

Base: `main` @ `07ad08f1`. Branch: `wave5e-account-policy`.

## Definition of Done — verified (spec's 9-item list)

1. Data migrated to SQLite/domain model. ✅ (real row, independently verified against `main`)
2. Real producers write SQLite/domain repositories. ✅ (`update_portfolio_policy.py`, new)
3. Real consumers read SQLite/domain repositories. ✅ (`rebalancer.py`, `ThesisService.ts` — 2/2)
4. Old JSON/JSONL runtime references removed or rewritten. ✅ (zero live reads remain)
5. SKILL.md/agent/plugin instructions no longer point at old JSON. ✅ (1 stale reference found
   and fixed — see Context Bundle Completion Bar below)
6. Context-bundler no longer needs retired JSON files. ✅ (same fix)
7. Old JSON archived (`git mv`, git-tracked file). ✅
8. Tests prove live path behavior against real data, not only fixture behavior. ✅ (both
   consumers' new tests point at a nonexistent JSON file to prove SQLite-only operation; real
   write independently re-verified against `main`)
9. JSON file count and context-bundle footprint reported before/after. ✅ (this report)

## Context Bundle Completion Bar

1 stale reference found and fixed: `plugins/portfolio-advisor/skills/rebalance-portfolio/SKILL.md`
(2 mentions — account-routing explanation, buy-account resolution explanation) told agents to
"Edit account_policy.json directly" and referenced the archived file's field names. Updated to
reference `portfolio_policy` and `update_portfolio_policy.py --write` instead. No other
plugins/skills reference `account_policy.json` (grep confirmed: `grep -rln "account_policy\.json"
plugins/ --include="*.md"` returns only this one file).

## Wave KPI Table

| KPI | Value |
|---|---|
| Wave | 5E — Account/Portfolio Policy |
| Active JSON/JSONL files before | 1 (`account_policy.json`) |
| Active JSON/JSONL files after | 0 |
| Files archived | 1 (`account_policy.json` → `ARCHIVE/investment_screener/backend/data/account_policy.json`) |
| JSON reads removed | 2 (`rebalancer.py`, `ThesisService.ts::getAccountPolicy()`) |
| JSON writes removed | 0 — there was never a live JSON writer for this domain (manually maintained); a new write path (`update_portfolio_policy.py`) was added instead |
| Producers migrated (n / total) | 1 / 1 (new write path, no prior producer to redirect) |
| Consumers migrated (n / total) | 2 / 2 (spec's assumed 4th, `order_risk_gates.py`, confirmed a false positive at Task 0) |
| Plugin/skill/agent references updated | 1 / 1 (`rebalance-portfolio/SKILL.md`) |
| Context-bundle files removed | 1 (`account_policy.json` no longer needs bundling by any skill) |
| Remaining JSON exceptions (with rationale) | `target-portfolio.json`'s `globalSettings` sub-object — see Retained-JSON Rationale Bar above |
