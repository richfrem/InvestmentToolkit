# Plan: SQLite as the single source of truth

**Status:** Proposed. **Date:** 2026-10-09. **Companion docs:** [spec](sqlite-single-source-of-truth-spec.md), [implementation prompt](sqlite-single-source-of-truth-implementation-prompt.md).

## 1. Decision

1. **Portfolio data is SQLite only.** Holdings, targets, thesis fields, standing decisions, price levels, trades, cash flows, alerts, projections and thesis breakers live in `investment_screener/backend/data/domain_model.sqlite`. No JSON file, no JSON fallback, no "retained exception" for any of it. (Owner, 2026-10-09.)
2. **Research and analysis go into one store too:** the append-only ledger `intelligence.sqlite`. JSON, JSONL and markdown copies become generated exports, never a source. (Owner, 2026-10-09: "go with your one store loading all that data in".)
3. **A retirement is only done when a guard test proves it.** Every earlier retirement was done script by script from grep lists, and nothing enforced "zero readers left".

## 2. Research and findings

### 2.1 What is already in SQLite (verified against the real database, 2026-10-09)

| Capability | Where | Evidence |
|---|---|---|
| Positions per account, cash | `account_investment` (+ `account`, `investment_price`) | TFSA 27 rows, RRSP 27, CASH 1; 26 equities |
| Total value | computed from the above; `broker_reported_total` for audit | equities $30,240.68 + cash $3,473.78 = $33,714.46 vs broker $33,735.62 |
| Target weights, roles, pillars, thesis text, rationale | `investment`, `strategy_pillar`, `sub_strategy` | 27 tickers with target > 0 sum to exactly 100.0%; 13 pillars sum to 100% |
| Standing decisions | `investment.standing_decision_*` | 80 of 95 populated |
| Price levels, target entry, stop loss | `price_level_set`, `price_level_tier` | 82 sets, 471 tiers |
| Trades, executions, cash flows | `trade_log_entry`, `order_execution`, `cash_flow`, `cash_flow_baseline` | 244 trades (JSON file had 52); 8 = 8 executions; 3 = 3 flows |
| Valuations | `projection_version`, `projection_scenario` | 290 versions across 91 tickers (JSON folder had 22 files) |
| Alerts, watchlist, policy | `alert`, `investment.is_watchlisted`, `portfolio_policy` | 347 alerts; 95 flags; 1 policy row |

The retained JSON copies are **stale subsets** of SQLite, so retiring them loses nothing.

### 2.2 What is not in SQLite (the real gaps)

1. **Thesis breakers.** No schema for definitions or evaluated state; `investment.thesis_breaker_status` is empty for all 95. State lives in `thesis_breaker_state.json` (0 holdings tracked). `README.md` admits "`thesisBreakers` still has no SQLite schema".
2. **Change log.** `portfolio_change_log` exists with 0 rows and no caller writes to it, so target-edit history is not recorded anywhere.
3. **Role vocabulary.** `update_thesis.py --role` accepts `core/hedge/reserve/speculative`; the database uses `accumulate/trim/exit/initiate/watchlist`.

### 2.3 Types of gap where the refactor stopped short

| # | Type | Examples |
|---|---|---|
| 1 | Tools whose only data store is a retired file | `update_thesis.py` (reads and writes `target-portfolio.json`), `validate_weights.py --mode target`, `lock_and_normalize_targets.py --target-file` |
| 2 | **Silent no-ops behind `exists()` guards** | `update_price_levels.derive_and_write_all()` returns `[]`; `harvest_predictions` skips breaker claims; `generate_review.py` builds the dossier with an empty thesis (`{}`) |
| 3 | Safety and health gates keyed on a retired file | `place_order.py` data-freshness gate (file mtime); three `system_health.py` checks |
| 4 | "SQLite first, JSON fallback" never cut over | `routes/portfolio.ts` (7 routes call `readPortfolio()`, 3 more use `?? readPortfolio()`), `screener.ts`, `stock.ts`, `ThesisService.ts`, `BrokerSyncService.ts` (serves a "cached portfolio" from a 3-holding stub when TradingView is down) |
| 5 | Writers to files nothing reads | `POST /api/portfolio` (UI manual position editor) writes `portfolio.json`; `Settings.tsx` tells the user to "edit portfolio.json directly" |
| 6 | Other consumers | `tradingview-cdp/cli.js alert list --filter` builds its holdings list from `portfolio.json`; `fetch_broker_data.py --compare` |
| 7 | Features with no SQLite home | the three gaps above |
| 8 | Vestigial code | 5 ignored `PORTFOLIO_PATH` parameters (`rebalancer`, `risk_engine`, `order_risk_gates`, `sync_portfolio_roles`, `ta_sweep_batch`); 6 unused path constants |
| 9 | Documentation drift | 146 doc lines call the retired files current (`architecture.md` says `portfolio.json` is "source of truth… retained exception"; `README.md` says fully retired); 4 lines tell agents to run broken tools |
| 10 | Stale governance | `audit_json_usage.py` / `allowed-json-register` label `target-portfolio.json` `ALLOWED_AUTHORITATIVE_JSON`; `run_tests.py` has no guard |
| 11 | Tests that hide it | 49 test files use the retired files as fixtures, so code that reads JSON stays green |
| 12 | Duplicate implementations | `investment_price` is written in 4 places (`PortfolioRepository.ts`, `investment_price_repository.py`, `manage_watchlist.py`, `fix_psu_alias_and_cash_price.py`), against AGENTS.md rule 22 |

### 2.4 How it was missed

The history shows one-off commits ("migrate daily_brief.py and ta_sweep_batch.py off retired target-portfolio.json", "stop gating price_level_tier writes on retired file"), each fixing whatever someone's grep found. `paths.ts` shows the same process for TypeScript constants ("confirmed via grep returning zero hits"). Nothing enforced completeness, tests used temp-file fixtures, and the JSON audit tool classified the files as allowed.

### 2.5 Research storage today

- `intelligence.sqlite` already has `intelligence_event` (1,044 rows, with an FTS5 full-text index): TECHNICAL_SWEEP 830, RESEARCH_IMPORT 88, PREDICTION_CLAIM 81, REVIEW_DAILY 41, THESIS_UPDATE 2, NEWS_SWEEP 2. `persist_research.py` publishes reports to it.
- Still on disk as copies or parallel stores: `research/` (232 top-level `.md`, 312 including subfolders), `observations.jsonl` (645 lines, 6.4 MB), `intelligence_events.jsonl` (71), `daily-briefs/*.json` (15), `etf_analysis/*.json` (8), `projections/*.json` (22).
- Migration scripts already exist and must be reused, not rewritten: `migrate_research_to_ledger.py`, `migrate_daily_briefs_to_ledger.py`, `migrate_predictions_to_ledger.py`, `migrate_ta_sweep_to_ledger.py`.
- **Not verified:** whether all 232 research files and the JSONL lines are already in the ledger. WS5 starts by measuring this.

### 2.6 Audit method and its limits

A read-only AST audit (`temp/evaluations/audit_sqlite_usage.py`, 25-case self-test) found **106 references in 31 files; 31 are live I/O in 14 files**, 4 of them migration tools. It covers Python only; TypeScript and docs were scanned with regexes. It is a heuristic, so WS0 turns it into a tested guard.

## 3. Target architecture

| Data | Store |
|---|---|
| Holdings, targets, thesis state, breakers, trades, cash, price levels, alerts, valuations, policy | `domain_model.sqlite` |
| Research, analysis, events, predictions, daily briefs | `intelligence.sqlite` (text + JSON payload columns, FTS5) |
| Markdown, JSONL | generated exports only; never read as a source |
| Screenshots, logs, caches | files; never a source of truth |
| Config, test fixtures | JSON/YAML is fine |

Two files because their lifecycles differ (mutable state with strict integrity vs append-only, large, rebuildable). Each fact still lives in exactly one place.

## 4. Decisions

| # | Decision | Status |
|---|---|---|
| D1 | Portfolio data is SQLite only | **Decided** (owner) |
| D2 | Research lives in the ledger; files are exports | **Decided** (owner) |
| D3 | New `thesis_breaker` + `thesis_breaker_state` tables for breakers | **Default: yes.** Owner has not answered; override at the start of implementation |
| D4 | Role vocabulary is the SQLite statuses; drop `core/hedge/reserve/speculative` | **Default: yes** |
| D5 | Remove the UI manual position editor (positions come from the broker sync only) | **Default: yes** |
| D6 | Move retired JSON files to `ARCHIVE/` only with the owner's explicit OK **per file** | **Required** |

## 5. Workstreams

Each workstream is one PR (or a few), finished and verified before the next starts. Every code change is test-first (failing test, then fix) in a worktree.

| WS | Goal | Depends on |
|---|---|---|
| **WS0 Guard and governance** | Promote the audit into the repo as a tested guard wired into `run_tests.py`; rewrite `allowed-json-register` and `audit_json_usage` classification; write ADR-038 | none |
| **WS1 Schema** | Migration `0002`: `thesis_breaker`, `thesis_breaker_state`; change-log writes; role enum constant; loaders expose `thesisBreakers` | WS0 |
| **WS2 Python tools** | Port each broken tool to SQLite loaders (see spec §5); remove vestigial parameters and unused constants | WS1 |
| **WS3 Express and React** | Delete `readPortfolio()` and every file fallback; fix `POST /api/portfolio` per D5; `BrokerSyncService` cached path reads SQLite; `Settings.tsx` text | WS0 |
| **WS4 CDP CLI** | `alert list --filter` takes holdings from the SQLite-backed endpoint (same pattern the watchlist already uses); remove the stray `DEBUG:` line | WS3 |
| **WS5 Research consolidation** | Measure parity; run the existing migrators (dry run, approval, write); build exporters; retire the `--jsonl` dual-write | WS0 |
| **WS6 Docs and instructions** | Fix the 146 stale doc lines, `architecture.md`, README, AGENTS.md, skills, agent docs | WS2, WS3 |
| **WS7 Retire files** | Move retired JSON/JSONL to `ARCHIVE/`, per file, with approval; update `.gitignore` | all |

## 6. Verification and definition of done

- Guard test green: zero live readers/writers of retired files outside a frozen migration-tool allow-list.
- "Move the files aside" smoke test in a worktree: rename `portfolio.json`, `trade-log.json`, `cash_flows.json`, `thesis_breaker_state.json` and the JSONL files, run the Python and Express suites, start the backend, hit the portfolio endpoints. Everything still works.
- Every documented command in skills and agent docs runs.
- Research parity report: every file/line either present in the ledger or explicitly listed as intentionally dropped.
- Real-data checks happen in the **main checkout's** database, not a worktree copy (AGENTS.md pitfall 29).

## 7. Data safety

Gitignored data is the owner's personal data. Back up (`db_backup.py`) before any write. Every migration is dry-run by default and needs an approved report before `--write`. Nothing is deleted; retirement means moving to `ARCHIVE/` with approval. Tests run in worktrees, never the main checkout.

## 8. Risks

- Porting `update_thesis.py` changes behavior (role names, breaker storage); D3/D4 must be settled first.
- Removing the UI editor (D5) is a product change.
- Research parity is unmeasured; WS5 may find content only on disk.
- TypeScript audit coverage is regex-based and may miss cases the Python AST audit would catch.

## 9. Not verified

Whether anything still reads `projections/*.json`; whether `harvest_predictions` copes with a missing target file beyond the `exists()` guard; whether all research files are in the ledger.
