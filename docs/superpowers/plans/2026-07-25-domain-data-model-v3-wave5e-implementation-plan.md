# Wave 5E — Account/Portfolio Policy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans / subagent-driven-development. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate `account_policy.json` into a singleton `portfolio_policy` row in `domain_model.sqlite`.

**Architecture:** New `portfolio_policy_repository.py` in `py_services/domain_model/`, mirroring `exchange_rate_repository.py`'s singleton-row pattern (id fixed at a constant, `INSERT ... ON CONFLICT DO UPDATE`). TS consumer (`ThesisService.ts`) reads via a new `PortfolioRepository.getPortfolioPolicy()` method.

## Global Constraints (copied verbatim from spec/plan)

- Producer writes SQLite + every real consumer reads SQLite + old file archived via `git mv` = migrated (ADR-029).
- No permanent hybrid. No script opens its own SQLite connection outside the owning repository.
- Real write must run against main checkout's actual files, independently re-verified by the controller.
- Push feature branch to origin before any worktree merge/removal; explicit user confirmation before any destructive worktree op — standing user rule, non-negotiable.

## Task 0 — Fresh Verification (performed at plan-authoring time, 2026-07-25)

- `account_policy.json`: git-tracked (`git check-ignore` returns nothing) — real `git mv` archive, not local-only.
- Real consumers, re-verified by grep, with false positives excluded:
  - `rebalancer.py` — reads all 4 fields (`accountPreferenceRules`, `psuFundingRule`, `riskBudgetCaps`, `bandConfig`) via `json.loads(Path(account_policy_path).read_text())`. Real, load-bearing.
  - `ThesisService.ts::getAccountPolicy()` (line ~181) — reads `ACCOUNT_POLICY_FILE`, validates with `AccountPolicySchema.parse(data)` (imported from `zod-schemas.ts`), uses `bandConfig` for drift-band computation (`computeBandPct`). Real, load-bearing. The zod schema is part of this same call site, not a separate consumer.
  - **False positive:** `order_risk_gates.py` declares `ACCOUNT_POLICY_PATH` as a constant but never opens/reads it anywhere in the file — real values are hardcoded elsewhere, the constant is dead. Confirmed via grep: only 1 match (the declaration), no `open`/`read_text` call using it.
  - **Out of scope, historical:** `migrations/remove_drift_threshold_fields.py` — one-time migration script, not a live producer.
- `target-portfolio.json`'s `globalSettings` (`rebalanceFrequency`, `portfolioValueUSD`) — **descoped from this wave's consumer-cutover, populated into SQLite as a value only, not cut over as a read path.** Real usage found: `zod-schemas.ts` (schema definition), `ThesisService.ts` line 625 (pure passthrough into an export payload, no decision logic against it). `ProjectionRepository.ts`'s `globalSettings` match is a **false positive** — a different concept (`{discountRate, timeHorizon}`, DCF assumptions per-projection), not this field. Since `target-portfolio.json` itself is Wave 2's already-approved retained-JSON exception (the whole file stays JSON for holdings/pillars), archiving or removing `globalSettings` from it is out of scope — the file remains JSON. This wave populates `portfolio_policy.rebalance_frequency`/`portfolio_value_usd_target` from it (the columns already exist, the values are trivial and useful for future consumers) but does **not** claim `globalSettings` as "migrated" per ADR-029's 3-part test, since the JSON field is not archived and the one real passthrough consumer is not cut over. This is recorded as a **Retained-JSON Rationale Bar** entry below, not silently worked around.
- `portfolio_policy` table: exists (Wave 0), 0 rows.
- No real producer today (manually maintained). This wave adds a small CLI (`update_portfolio_policy.py`) as the new write path, matching the pattern other manually-maintained domains in this migration use.

### Retained-JSON Rationale Bar — `target-portfolio.json`'s `globalSettings` sub-object

| Field | Answer |
|---|---|
| File / pattern | `target-portfolio.json: globalSettings` (`rebalanceFrequency`, `portfolioValueUSD`) |
| Why not SQLite? | It IS also written to SQLite (`portfolio_policy.rebalance_frequency`/`portfolio_value_usd_target`) — this bar concerns why the JSON field is *retained*, not why SQLite isn't used |
| Why not event model? | N/A — this is config, not an event |
| Why not generated from SQLite? | `target-portfolio.json` as a whole is Wave 2's approved retained-JSON exception (holdings/pillars still author there); regenerating just this sub-object would fragment that file's single-source editing story |
| Category | config (rides with Wave 2's already-approved exception for the whole file) |
| Who writes it? | Manual edit, same as the rest of `target-portfolio.json` |
| Who reads it? | `ThesisService.ts` line 625 (passthrough only, no decision logic) |
| What breaks if removed? | Nothing today (passthrough only) — but removing it without updating that call site would be a needless breaking change this wave doesn't need to make |
| User-approved exception? | Rides on Wave 2's existing approval for the file as a whole — not a new decision |
| Future migration trigger | If a future wave (5E follow-up or Wave 6) fully migrates `target-portfolio.json`'s remaining JSON surface (per Wave 6's own pre-analysis note), `globalSettings` retires with it then |

## Task 1: `portfolio_policy_repository.py`

**Files:**
- Create: `investment_screener/backend/py_services/domain_model/portfolio_policy_repository.py`
- Test: `investment_screener/backend/tests/py_services/test_portfolio_policy_repository.py`

**Interfaces:**
- `upsert_portfolio_policy(conn, **fields) -> None` — singleton row, `policy_id` fixed at `'default'`, `ON CONFLICT DO UPDATE`, `updated_at` auto-set.
- `get_portfolio_policy(conn) -> dict | None`

- [ ] Write failing tests: round-trip upsert+get, idempotent re-upsert (no duplicate row), partial-field update preserves other fields, returns `None` on empty table.
- [ ] Implement, mirroring `exchange_rate_repository.py`'s singleton pattern.
- [ ] Run tests, confirm pass.
- [ ] Commit.

## Task 2: TS-side `PortfolioRepository.getPortfolioPolicy()`

**Files:**
- Modify: `investment_screener/backend/src/services/PortfolioRepository.ts`
- Test: add to `investment_screener/backend/tests/PortfolioRepository.spec.ts`

**Interfaces:**
- `getPortfolioPolicy(): PortfolioPolicy | null` — mirrors `getExchangeRate()`'s pattern (read-only from TS side; TS never writes this table, only Python's CLI does).
- The `portfolio_policy` table's `CREATE TABLE IF NOT EXISTS` must also exist in `PortfolioRepository.ts`'s own schema-ensure block (check whether it's already there from Wave 0's TS-side schema mirror; add if missing, matching the Python DDL exactly).

- [ ] Write failing test: seed a row via raw SQL (matching the Python schema), confirm `getPortfolioPolicy()` reads it back correctly; returns `null` on empty table.
- [ ] Implement.
- [ ] Run tests, confirm pass.
- [ ] Commit.

## Task 3: Real migration script + real write

**Files:**
- Create: `investment_screener/backend/py_services/migrate_account_policy_to_sqlite.py`
- Test: `investment_screener/backend/tests/py_services/test_migrate_account_policy_to_sqlite.py`

**Interfaces:**
- `migrate(account_policy_path, global_settings_source_path, db_path, dry_run=True) -> dict` — returns `{"fields_migrated": [...], "skipped": [...]}`. Reads `account_policy.json`'s 4 fields + `target-portfolio.json`'s `globalSettings` sub-object, writes one singleton row via `upsert_portfolio_policy`.
- CLI: `--account-policy-path`, `--target-portfolio-path`, `--db-path`, `--dry-run`/`--write` (mutually exclusive, required) — mirrors Wave 5D's `migrate_predictions_to_ledger.py` argparse shape.

- [ ] Write failing tests: dry-run reports fields without writing; write path upserts correctly (both numeric columns + 2 JSON-blob columns); idempotent re-run.
- [ ] Implement.
- [ ] Run tests, confirm pass.
- [ ] Commit (script only).
- [ ] **Dry-run against the real main-checkout files** (`--account-policy-path`, `--target-portfolio-path`, `--db-path` all explicit main-checkout absolute paths). Present dry-run output to user, get explicit sign-off.
- [ ] **Real write against the main checkout**, explicit absolute paths for all 3 path args.
- [ ] Independently re-verify: `sqlite3 <main's domain_model.sqlite> "SELECT * FROM portfolio_policy;"` shows the real values matching `account_policy.json`'s real content.
- [ ] Commit the real-data write directly to `main` (not the worktree) — separate commit, per this migration's established pattern for real writes (`domain_model.sqlite` itself is gitignored so nothing to commit there beyond confirming the write landed; no JSONL/ledger involved for this domain, single-store write).

## Task 4: Consumer cutover — `rebalancer.py` + `ThesisService.ts`

**Files:**
- Modify: `investment_screener/backend/py_services/rebalancer.py`
- Modify: `investment_screener/backend/src/services/ThesisService.ts`
- Tests: existing test files for both, add SQLite-backed test cases

**Interfaces:**
- `rebalancer.py`: replace `json.loads(Path(account_policy_path).read_text())` with a new `_load_account_policy_from_db(db_path) -> dict` helper (via `portfolio_policy_repository.get_portfolio_policy`, reshaping the row back into the same dict shape `accountPreferenceRules`/`psuFundingRule`/`riskBudgetCaps`/`bandConfig` the rest of the function expects — so downstream code needs no changes).
- `ThesisService.ts::getAccountPolicy()`: replace the `fs.readFileSync(ACCOUNT_POLICY_FILE)` + `AccountPolicySchema.parse()` with `PortfolioRepository.getPortfolioPolicy()`, reshaped into the same `AccountPolicy` TS type.

- [ ] Write failing tests for both (real sqlite3/tmp_path-scoped, not mocked) proving the SQLite read path.
- [ ] Implement both cutovers.
- [ ] Run both test suites, confirm pass, confirm no regression in existing tests.
- [ ] Commit (one commit per file).

## Task 5: Real-cycle check + manual-edit CLI

**Files:**
- Create: `investment_screener/backend/py_services/update_portfolio_policy.py` (the new write path for manual edits, replacing hand-editing the JSON file)
- Test: `investment_screener/backend/tests/py_services/test_update_portfolio_policy.py`

**Interfaces:**
- CLI: `--set-risk-budget-cap KEY=VALUE`, `--set-band-config KEY=VALUE`, `--write` (dry-run by default, matching `update_targets.py`'s existing `--set-entry`/`--write` convention already used elsewhere in this codebase).

- [ ] Write failing tests: dry-run reports the change without writing; `--write` actually updates the singleton row; unknown key rejected.
- [ ] Implement.
- [ ] Run tests, confirm pass.
- [ ] Commit.

## Task 6: Physically-executed rollback exercise

- [ ] Throwaway worktree, revert Task 3's real-write commit's corresponding code commits (Tasks 1-2), confirm `rebalancer.py`/`ThesisService.ts` (reverted) still work against `account_policy.json` directly, full pre-wave test suite passes.
- [ ] Clean up throwaway worktree, verify via `git worktree list`.
- [ ] Write evidence doc `docs/superpowers/status/wave5e-rollback-exercise-report.md` with real command output.
- [ ] Commit.

## Task 7: Archive `account_policy.json`

- [ ] Grep for zero remaining real-I/O reads of `account_policy.json`/`ACCOUNT_POLICY_PATH`/`ACCOUNT_POLICY_FILE` outside test files.
- [ ] `git mv account_policy.json ARCHIVE/investment_screener/backend/data/account_policy.json`.
- [ ] Confirm `.gitignore` doesn't need a new re-ignore rule (this file is git-tracked, not gitignored, so the `604ef8ee` bug class doesn't apply — but double-check the `ARCHIVE/` mirror isn't accidentally caught by any *other* stale ignore rule).
- [ ] Commit.

## Task 8: Wave exit — report, PR, push

- [ ] Full test suite run, T0/T0.5 gate.
- [ ] Write `docs/superpowers/status/wave5e-account-policy-report.md` (KPI table, cutover table, Definition of Done, Hybrid Exit Criteria, §5 Validation Strategy, Context Bundle Bar, Retained-JSON Rationale Bar for `globalSettings` verbatim from Task 0 above).
- [ ] **Push the branch to origin.**
- [ ] Dispatch one final whole-branch review (Sonnet, not Opus).
- [ ] Open PR to `main`. Do not merge.
- [ ] Verify remote branch matches local HEAD exactly.
- [ ] Write `docs/superpowers/status/wave5e-handoff.md`.
- [ ] Stop. Do not clean up the worktree/branch without explicit user confirmation, even after merge is confirmed.

## Definition of Done (spec's 9-item list, verbatim)

1. Data migrated to SQLite/domain model.
2. Real producers write SQLite/domain repositories.
3. Real consumers read SQLite/domain repositories.
4. Old JSON/JSONL runtime references removed or rewritten.
5. SKILL.md/agent/plugin instructions no longer point at old JSON.
6. Context-bundler no longer needs retired JSON files.
7. Old JSON archived (`git mv`).
8. Tests prove live path behavior against real data.
9. JSON file count and context-bundle footprint reported before/after.

## Hybrid Exit Criteria

Not `JSON + SQLite` forever. `account_policy.json` stops being authoritative once both real
consumers (`rebalancer.py`, `ThesisService.ts`) read SQLite and the file is archived. `globalSettings`
is explicitly NOT claimed migrated this wave (see Retained-JSON Rationale Bar) — no hybrid-state
violation since it's a named, justified exception riding on Wave 2's existing approval, not a
silent gap.
