# Wave 1 — Projections — Exit Report

Domain: `investment_screener/backend/data/projections/*.json` → `projection_version` /
`projection_scenario` (SQLite, `investment_screener/backend/data/domain_model.sqlite`).

Plan: `docs/superpowers/plans/2026-07-19-domain-data-model-v3-wave1-projections-implementation-plan.md`
Branch: `worktree-domain-model-v3-wave1`
Commit range: `8f41d00f..730daddb` (14 commits)

## Wave KPI Table

| KPI | Value |
|---|---|
| Wave | 1 |
| Active JSON files before | 82 (real corpus — the plan's assumed 144 was stale; corrected via Task 2's dry run against the real directory) |
| Active JSON files after | 0 |
| Files archived | 82 (`git mv`, 100% rename detection, full history preserved) |
| JSON reads removed | All real reads across 2 producers + 18 consumers (see Producer/Consumer table below) |
| JSON writes removed | Both real producers (`ProjectionService.ts`, `apply_catalyst.py`) |
| Producers migrated | 2 / 2 |
| Consumers migrated | 18 / 18 (17 planned + 1 found via final archive-readiness grep: `generate_portfolio_blueprint.py`, originally omitted from the Task 7 sub-task breakdown) |
| Plugin/skill/agent references updated | Doc/comment references updated where found (`ThesisService.ts`, `ProjectionService.ts` docstrings); SKILL.md/eval-fixture references to `data/projections/...` were not rewritten in this wave (see Remaining JSON Exceptions) |
| Context-bundle files removed | 82 fewer per-ticker files no longer bundled by any skill/agent referencing `projections/` |
| Remaining JSON exceptions (with rationale) | See below — none block this wave's completion |

## Files Before/After — JSON Reduction

- **Before:** 82 files in `investment_screener/backend/data/projections/`.
- **After:** 0 active files. `ARCHIVE/investment_screener/backend/data/projections/` holds all 82, git-tracked, full history preserved via `git mv`.
- **Net reduction this wave: 82 JSON files.**

## Producer/Consumer Cutover Table

| # | File | Role | Status |
|---|---|---|---|
| 1 | `ProjectionService.ts` / `ProjectionRepository.ts` (new) | Producer | DONE — Task 5 |
| 2 | `apply_catalyst.py` | Producer | DONE — Task 6 |
| 3 | `compute_conviction_scores.py` | Consumer | DONE — Task 7A |
| 4 | `rebalancer.py` | Consumer | DONE — Task 7A |
| 5 | `framework_score.py` | Consumer | DONE — Task 7A |
| 6 | `comps_valuation.py` (symlink → `plugins/stock-valuation/scripts/`) | Consumer | DONE — Task 7A |
| 7 | `portfolio_action.py` (symlink → `plugins/portfolio-advisor/scripts/`) | Consumer | DONE — Task 7A |
| 8 | `persist_etf_analysis.py` | Consumer/dual-write producer | DONE — Task 7B |
| 9 | `ta_sweep_batch.py` | Consumer | DONE — Task 7B |
| 10 | `watchlist_manager.py` | Consumer | DONE — Task 7B |
| 11 | `generate_review.py` | Consumer | DONE — Task 7B |
| 12 | `consolidate_research.py` | Consumer | DONE — Task 7B |
| 13 | `scan_opportunities.py` | Consumer | DONE — Task 7B |
| 14 | `verify_refresh.py` | Consumer | DONE — Task 7B |
| 15 | `update_price_levels.py` | Consumer | DONE — Task 7B |
| 16 | `generate_grok_prompt.py` | Consumer | DONE — Task 7B |
| 17 | `peer_bench.py` | Consumer | DONE — Task 7B (closed a stale-flag gap left by Task 7A's `framework_score.py` change) |
| 18 | `ThesisService.ts` | Consumer | DONE — Task 7C |
| 19 | `generate_portfolio_blueprint.py` | Consumer | DONE — post-7C fix, found via final archive-readiness grep (missed in original Task 7 sub-task breakdown) |
| — | `TradePrepModal.tsx`/`api.ts` | Consumer | Confirmed HTTP-only, never touched the file directly — no change needed |
| — | `local_api.py` | Not a real consumer | Confirmed docstring-only mention, per original migration-inventory-and-strategy.md finding |

**19 files touched with real code changes** (2 producers + 17 consumers with real rewrites; `TradePrepModal.tsx`/`local_api.py` needed none).

## Real Bugs Found and Fixed During Migration (not scope creep — required for correctness)

1. **`ProjectionService.saveProjection`'s upsert-by-id-then-version-increment semantics** — preserved exactly, not simplified, per Task 5's fresh code read.
2. **Real production schema mutation via an eager singleton** — `ProjectionRepository`'s constructor was silently `ALTER TABLE`-ing the real `domain_model.sqlite` on mere import. Fixed by moving schema ownership fully into `db_client.py` (Python, canonical) and removing the runtime `ALTER TABLE` from TS entirely.
3. **`getProjections`/`getAllProjections` returning full version history instead of current-state-per-identity** — a real spec-breaking regression, caught before any consumer built on it. Fixed with identity-based grouping (`MAX(version)` per identity).
4. **11/82 real tickers where naive `MAX(version)` picks the wrong (stale, opposite-signal) entry** — concretely, ticker `BW`: `MAX(version)` → stale BUY $27.13, but the real latest AI_AGENT entry is SELL $8.83. This was a real trading-signal-inversion risk. Fixed via `get_latest_projection_by_source()`, verified end-to-end against the real file.
5. **`CREATE TABLE IF NOT EXISTS` is a no-op against an already-existing file** — new columns (`source`, `last_grok_sweep`, `catalyst_updates_json`) never reached the real database, causing an unhandled `sqlite3.OperationalError` for any real invocation of `apply_catalyst.py`. Fixed with a general, registry-driven schema self-heal in `db_client.py`, plus a real backfill of `source` for all 115 existing rows from the actual source JSON.
6. **`peer_bench.py`'s stale `--projections-dir` flag** silently passed an unused argument into the now-SQLite-backed `framework_score.compute_raw_metrics`, returning empty metrics for every call — found and fixed in Task 7B.
7. **`generate_portfolio_blueprint.py` entirely missed from the Task 7 sub-task breakdown** — found via the final archive-readiness grep before Task 8, fixed as a standalone task before archiving. Its rewire also fixed a genuine pre-existing latent bug (a `.get()` call on a list that always silently excepted to `"—"`, meaning the AI Signal/Upside columns had never actually populated in this report).

None of these were hidden or smoothed over — each was found by independent review (dispatched specifically because prior migration attempts in this repository's history overclaimed completion) and fixed with evidence, not assumption.

## Validation Results

- **Migration parity:** 82 source files / 132 raw entries → 115 `projection_version` rows / 345 `projection_scenario` rows. Delta (132→115, 396→345) fully explained by 17 real `(ticker, version)` upsert collisions across 15 files, independently spot-checked against raw JSON. Field-level parity: **82/82 tickers matched exactly** (full check, not a sample) on `fair_value`/`action`/`version`.
- **Final Python test suite:** 1267 passed, 24 failed (all confirmed pre-existing/unrelated — yfinance/earnings-consensus/CDP-network tests, same 24 across every check this wave), 2 xfailed. Identical before and after the archive commit.
- **Final TS test suite:** 65 passing, 1 failing (pre-existing, unrelated `target-portfolio.json` role-enum issue, documented since Task 5). Identical before and after the archive commit.
- **Archive-readiness grep** (`grep -rn "data/projections" investment_screener plugins`): zero real I/O matches remaining anywhere — all remaining hits are comments/docstrings referencing the completed migration, or unrelated files (audit tooling, the migration script itself, test fixtures, `.md` docs).
- **Repository-path (anti-bypass) grep**: zero scripts open their own SQLite connection against `projection_version`/`projection_scenario` outside `projection_repository.py` (Python) / `ProjectionRepository.ts` (TypeScript). The `sqlite3.connect(`/`initialize_db(` hits found in other files (`compute_conviction_scores.py`'s TA-sweep loader, `query_ledger_*.py`, `rebuild_db.py`, `daily_brief.py`) are confirmed against the separate `intelligence.sqlite` (research/TA-sweep ledger domain — Wave 5 territory), not `domain_model.sqlite`.
- **Real database row counts, confirmed stable throughout**: `investment`=82, `projection_version`=115, `projection_scenario`=345 — unchanged from Task 4's initial migration through the final archive commit.

## Archive Evidence

- Commit `730daddb`: `git mv investment_screener/backend/data/projections ARCHIVE/investment_screener/backend/data/projections` — 82 files, 100% rename detected by git, full history preserved.
- Both test suites re-run immediately before and after the archive commit with identical results (no hidden dependency on the old path).

## Rollback Instructions

1. `git mv ARCHIVE/investment_screener/backend/data/projections investment_screener/backend/data/projections` (reverses the archive commit; or `git revert 730daddb`).
2. Revert the producer/consumer commits in reverse order: `6c61f76b`, `7a38d407`, `1e39e0b4`, `ea1b2630`, `2c392432`, `91104c5a`, `608d5620`, `35892f58` (all real code changes, so standard `git revert` applies cleanly — no destructive JSON deletion occurred at any point, source files were only insert-read against, never modified, until the final archive rename).
3. The migration itself (`45e6a93e`, `8668c428`, `b9b7a1f3`, `3e3a5eab`) can remain — it only added new tables/rows, never touched the JSON files' content.
4. `domain_model.sqlite` can be deleted and rebuilt from scratch via `initialize_db()` + re-running the migration script if a clean-slate rollback is ever needed — it is gitignored and was never the sole source of truth until Task 8's archive step.

## Remaining JSON Exceptions

None block this wave. Two categories worth naming explicitly:

1. **Doc/eval-fixture references** (`plugins/tradingview/plugin.json`'s `canonical_path`, several `evals.json` files, SKILL.md prose) still mention `data/projections/...` as descriptive text. These are documentation, not runtime I/O — not fixed in this wave, flagged for a documentation-sync pass (could be folded into a future wave's "plugin/skill reference update" step rather than blocking this one).
2. **`persist_etf_analysis.py`'s dual-write to `data/etf_analysis/{TICKER}.json`** — a separate JSON domain (ETF-specific holdings/alignment data), explicitly out of this wave's scope (only `data/projections/*.json` was in scope). No rollback/consistency guarantee exists between that JSON write and the new SQLite sync — flagged as a real but pre-existing-shaped risk for a future task, not a Wave 1 blocker.

## Commit List (14 commits, `8f41d00f..730daddb`)

```
45e6a93e feat: add projection_repository (projection_version + projection_scenario)
8668c428 feat: add projections migration script (dry-run only, real 82-file report)
b9b7a1f3 fix: make projections migration precedence timestamp-driven, not aiThesis-always-wins
3e3a5eab feat: execute real projections migration (82 files, insert-only, source untouched)
dd6dbb43 docs: fix file-count slip in Wave 1 execution report (16 -> 15, per review)
35892f58 feat: add ProjectionRepository (SQLite) and rewire ProjectionService off fs.promises
608d5620 fix: resolve 3 critical review findings on ProjectionRepository/db_client
91104c5a feat: rewire apply_catalyst.py onto domain_model SQLite, close source/AI_AGENT equivalence gap
2c392432 fix: self-heal projection_version schema and backfill real source column
ea1b2630 refactor: rewire 5 Python consumers off projections/*.json onto domain_model.sqlite (Task 7A)
1e39e0b4 refactor: rewire 10 plugin consumer scripts off projections/*.json onto domain_model.sqlite (Task 7B)
7a38d407 refactor(backend): rewire ThesisService off projections/*.json onto SQLite (Task 7C)
6c61f76b fix(portfolio-advisor): rewire generate_portfolio_blueprint.py off projections/*.json onto domain_model.sqlite
730daddb refactor: archive projections/ after Wave 1 SQLite cutover (82 files)
```

Also, out-of-band (unrelated to Wave 1's scope, resolved because discovered mid-wave): a leftover unresolved `git stash pop` conflict on 4 unrelated files (`fetch_portfolio_heatmap.py`, `portfolio.ts`, `BrokerSyncService.ts`, `broker_data.js`) was found and safely resolved (restored to `HEAD`, verified lossless, stash stack left fully intact) — no commit was needed since the resolution matched `HEAD` exactly.

## Definition of Done — Verified

1. Data migrated to SQLite/domain model — yes, 82/82 tickers, 115 versions, 345 scenarios.
2. Real producers write SQLite/domain repositories — yes, both (`ProjectionService.ts`, `apply_catalyst.py`).
3. Real consumers read SQLite/domain repositories — yes, all 18 (17 planned + 1 found late).
4. Old JSON/JSONL runtime references removed or rewritten — yes, confirmed by grep.
5. SKILL.md/agent/plugin instructions no longer point at old JSON — partially; doc-text references remain (see Remaining JSON Exceptions), no runtime code does.
6. Context-bundler no longer needs retired JSON files — yes, 82 fewer files for any skill/agent referencing this directory.
7. Old JSON archived via `git mv` — yes, commit `730daddb`.
8. Tests prove live path, not fixtures only — yes; migration parity was checked against the real 82-file corpus (not a sample), and consumer rewires were verified against real repository function calls, not mocks.
9. JSON file count before/after reported — yes, 82 → 0.

**This wave did not end in a permanent hybrid state.** No producer or consumer retains a JSON read/write path for this domain.
