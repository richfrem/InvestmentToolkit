# Wave 6 — Program Closure & Architecture Reconciliation Report

Status: All 5 tasks complete (2026-07-25). See "Open Items Not Resolved This Wave" below for
deliberate deferrals — this wave closes the program's functional migration scope but does not
claim zero remaining work.

## Task 1 — Architecture Documentation Reconciliation (COMPLETE)

Diffed `docs/architecture/domain-data-model.md` and `docs/architecture/supplementary-domain-schemas.md`
against the real, live SQLite schema (`.schema` dump against `domain_model.sqlite`/`intelligence.sqlite`
confirmed to exactly match both `db_client.py` files' `CREATE TABLE`/`SCHEMA_EVOLUTIONS` declarations).

Drift found and fixed:
- `investment`: added `sector`/`industry` (Wave 3 post-hoc) to ERD + column-level SQL.
- `projection_version`: added `raw_json`, `legacy_id`, `source`, `last_grok_sweep`,
  `catalyst_updates_json` (Wave 1 Task 5/6 post-hoc).
- `trade_log_entry`: added `tv_order_id` (Wave 4) to ERD.
- ERD: added missing `PORTFOLIO_POLICY` (Wave 5E), `BROKER_EXCHANGE_RATE`, `BROKER_REPORTED_TOTAL`
  (Wave 3) entity blocks — previously defined only in the SQL section, absent from the diagram.
- `supplementary-domain-schemas.md`: renamed stale `instrument_id`→`investment_id` in
  `trade_log_entry`/`order_execution` (this doc's pre-implementation sketch predated the v3
  `INVESTMENT` consolidation); added the previously wholly-undocumented `ledger_checkpoint` table,
  full `intelligence_event` column list, and `intelligence_event_fts` + its 3 sync triggers.

Open design questions flagged, deliberately NOT resolved (schema transcription, not redesign):
1. `trade_log_entry.account_id` (typed FK to `account`) vs. `cash_flow.account` (plain TEXT, no FK)
   — same conceptual field modeled two different ways across two tables.
2. `portfolio_policy`'s DDL citation in the Wave 6 kickoff brief points at a `domain-data-model.md`
   section heading ("Missing top-level PORTFOLIO/config entity") that does not exist verbatim in
   the file — a citation-accuracy gap, not a schema-content problem.

## Task 2 — Agent & Onboarding Reconciliation (COMPLETE)

Reviewed `toolkit-onboarding-guide`, startup/bootstrap instructions, coordinator-agent routing,
TradingView onboarding path, and grepped all `plugins/**/*.md` (130 files) for stale references
to archived filenames (`predictions.jsonl`, `ta-sweep-results.json`, `daily-briefs`,
`account_policy.json`).

**Fixed:** `plugins/toolkit-manager/agents/toolkit-onboarding-guide.md` — its "Data architecture
note" claimed a SQLite-backed model was "in active design, not yet implemented," which was badly
stale (Waves 0-5E already shipped and populated `domain_model.sqlite`/`intelligence.sqlite`).
Rewrote to state the toolkit is SQLite-first today, name both real databases, and correctly scope
the remaining retained-JSON exceptions.

**Checked, already accurate:** `tradingview-onboarding.md`; `rebalance-portfolio/SKILL.md`
(correctly describes `account_policy.json` as archived, `portfolio_policy` table as the real
route); the three `toolkit-manager/references/data-architecture/*.md` files (references to
archived filenames are historical/rationale, correctly labeled).

**Flagged, not fixed (out of this task's `plugins/`-only scope):** `daily-brief/SKILL.md`
accurately documents that `daily_brief.py` still dual-writes a legacy `data/daily-briefs/*.json`
snapshot alongside the SQLite `REVIEW_DAILY` event — doc matches code, but the dual-write itself
looks like an un-retired pattern similar to Wave 5D's — worth a look under Task 5 (see below;
Task 5's sweep did not independently re-confirm this, so it remains an open item for a future
pass, not resolved this wave). Also `.agents/agents/portfolio-advisor-daily-loop-agent.md` is a
stale literal copy of the (already-fixed) `plugins/portfolio-advisor/agents/daily-loop-agent.md`,
still referencing `ta-sweep-results.json` and old review-folder paths — outside `plugins/` scope,
flagged for awareness only.

## Task 3 — Retained-JSON Reassessment (this session's own re-verification, 2026-07-25)

**Re-verification note:** the implementation plan's pre-analysis of `target-portfolio.json` was
dated 2026-07-24. Real thesis-content commits landed 2026-07-25 (`ea6e995c`) after that analysis.
Re-checked every field below directly against the current file on disk — `ea6e995c` only edited
`shares` values and `updatedAt`/prose fields, not the fields this reassessment concerns.

### `target-portfolio.json` / `ThesisService.ts`

| Field | Required answer |
|---|---|
| File / pattern | `investment_screener/backend/data/theses/target-portfolio.json` |
| Why not SQLite? | Most fields already ARE in SQLite (`standing_decision_*` columns) or are trivial scalars (`globalSettings`, `schemaVersion`/`version`) — the barrier is `ThesisService.ts`'s CRUD path not reading/writing SQLite yet, not a schema gap, for those fields. |
| Why not event model? | `changeLog` (version-history array) is event-shaped and could map to `intelligence_event` (type `THESIS_UPDATE` already exists in the CHECK constraint) instead of a bespoke child table — worth considering before adding new schema. |
| Why not generated from SQLite? | N/A — this file is the authored source, not a derived cache. |
| Category | config (thesis/target authoring surface) |
| Who writes it? | User via `/thesis-review`, `/calibrate-targets`; agents via `update_targets.py` |
| Who reads it? | `ThesisService.ts`, `rebalancer.py`, `daily-loop-agent`, `strategic-review` skill, many others |
| What breaks if removed today? | Everything — this is still the live, actively-edited (7/25 commit) authoring surface. Not a candidate for removal without the migration work below. |
| User-approved exception? | Partially — `globalSettings`/scalars/`standingDecision` have no remaining technical barrier (verified below); `thesisBreakers`/`changeLog` still need small new schema. |
| Future migration trigger | Re-verified field-by-field below; see per-field notes. |

Field-by-field re-verification against real, current data (2026-07-25):
- **`globalSettings`** (`rebalanceFrequency`, `portfolioValueUSD`) — confirmed still just 2 scalar
  fields (`{'rebalanceFrequency': 'quarterly', 'portfolioValueUSD': 30797}`). Trivial, not a
  blocker. Unchanged from pre-analysis.
- **`bandConfig`** — confirmed **absent from `target-portfolio.json` entirely** as of this
  re-check (not merely "belongs elsewhere" as the pre-analysis said — it's actually gone from the
  document). The file's own `changeLog` entry (v10.8, 2026-07-10) states: *"E2 migration: removed
  globalSettings.driftThresholdPct, criticalDriftPct — drift-band config now lives in
  account_policy.json's bandConfig."* Pre-analysis's claim confirmed and now doubly verified: this
  is fully resolved, not a Wave 6 concern.
- **`standingDecision`** — re-verified on `VST`: real, current `investment` table row has
  `standing_decision_type='SA_LP_EXIT_OVERRIDE'`, with reason/source/review columns populated,
  matching the JSON document's `standingDecision` object structurally. Confirmed still solved at
  the schema level; `ThesisService.ts` still doesn't read/write via SQLite for this field (not
  re-checked in this pass — Task 2's agent/onboarding grep may surface this, otherwise flag as a
  follow-up code task outside Wave 6's own scope, which is docs/decisions only).
- **`thesisBreakers`** — **zero instances found anywhere in the current real file** (grep + full
  JSON walk, confirmed empty). The field is a real, defined optional Zod schema field
  (`zod-schemas.ts:180`/`:206`, `z.array(z.string().max(500)).max(5).optional()`) but **no current
  holding or pillar actually populates it**. Correction to the pre-analysis: schema support may
  still be worth adding for when it IS used, but there is currently zero real data to migrate —
  this is a "provision for future use," not an urgent migration target with real data at stake.
- **`changeLog`** — confirmed present, 3 real entries as of this check (unchanged count from
  2026-07-24 pre-analysis; the 2026-07-25 commit did not add a new changeLog entry despite editing
  `shares` values). Real, growing version-history array — genuine migration candidate, either a
  small child table (as pre-analysis suggested) or as `intelligence_event` rows (type
  `THESIS_UPDATE` already exists in the schema's CHECK constraint) — the event-model option was not
  considered in the original pre-analysis and is worth weighing before committing to a new
  bespoke table.
- **`shares`** — re-verified against real, current `account_investment`: `PSU-U.TO` shows `20` in
  JSON vs. `23` real (`RRSP: 3` + `TFSA: 20` from `account_investment`) — **same drift the
  pre-analysis found on 2026-07-24, unchanged by the 2026-07-25 edits** (those edits changed
  `shares` on 21 *other* tickers, e.g. `VST` 38→42, `MSFT`... but did not touch `PSU-U.TO`'s stale
  value). Confirms the pre-analysis conclusion still holds: this is a live data-quality bug (stale
  duplicate of `account_investment`), not a migration target. Recommend deleting the field from the
  document rather than adding schema for it, per the original recommendation — still correct.

**Net effect (re-confirmed, with one correction and one new consideration vs. the 2026-07-24
pre-analysis):** `changeLog` remains the one field genuinely requiring new persistence (schema or
event-model); `thesisBreakers` needs no urgent action since it holds no real data today;
`shares` should be deleted rather than migrated; `bandConfig`/`globalSettings`/`standingDecision`
require no new schema at all.

### `thesis_breaker_state.json`

| Field | Required answer |
|---|---|
| File / pattern | `investment_screener/backend/data/thesis_breaker_state.json` |
| Why not SQLite? | `investment.thesis_breaker_status` column exists (Wave 2) but only stores current status per investment, not this file's full *evaluated state* shape (breaker definitions + evaluation history) — confirmed by reading `thesis_breakers.py`'s own module docstring, which states this module "owns the evaluated state file." |
| Why not event model? | Breaker evaluations are event-shaped (a `THESIS_UPDATE` or dedicated event type could represent each evaluation) but not attempted in any prior wave; out of this wave's scope to redesign. |
| Why not generated from SQLite? | Not derivable — it's the primary write target of the evaluation logic itself. |
| Category | cache / evaluated-state (not a pure ledger, not pure config) |
| Who writes it? | `thesis_breakers.py`'s evaluation logic |
| Who reads it? | Re-verified via grep, all 5 real, current consumers confirmed still present: `order_risk_gates.py`, `rebalancer.py`, `harvest_predictions.py`, `thesis_breakers.py`, `risk_officer.py` (plus `audit_json_usage.py` and `migrate_target_portfolio_to_sqlite.py`, not in the original consumer list). |
| What breaks if removed? | Thesis-breaker gating in `order_risk_gates.py`/`risk_officer.py` and rebalance recommendations in `rebalancer.py` — all 3 are live enforcement paths. |
| User-approved exception? | Not formally documented anywhere found in this program's specs/ADRs — **this is a gap**: Wave 2's plan said this file's "target schema was folded in already," but the file itself was never actually archived and is still a live read/write path. This needs an explicit decision, not a carried-forward assumption. |
| Future migration trigger | If Wave 2's `investment.thesis_breaker_status` column is ever extended to carry the full evaluated-state shape (definitions + evaluation timestamps/history), this file could retire. Not attempted this wave — flagged as a real gap for a future wave, not resolved here (Wave 6 makes retention *decisions*, and the decision here is: **formally retain for now, undocumented exception closed by this rationale bar**). |

### `account_policy.json`'s two retained JSON-blob columns

Per spec §2.14/§2.17, already justified; re-confirmed this wave — `portfolio_policy.
account_preference_rules_json` and `portfolio_policy.psu_funding_rule_json` still exist exactly as
designed in the real, live schema (confirmed via `.schema` dump in Task 1). No new decision needed;
reasoning still holds.

### `target-portfolio.json`'s `globalSettings` sub-object — Wave 5E rationale-bar closeout

Wave 5E's own Retained-JSON Rationale Bar (`wave5e-account-policy-report.md`) deferred full
resolution of `globalSettings` to whichever wave migrates `target-portfolio.json`'s remaining
JSON surface. Per the field-by-field re-verification above, `globalSettings` is 2 trivial scalars
with no technical barrier — **closing this rationale bar's "Future migration trigger" row now**:
trigger condition is simply "whenever `changeLog` is migrated, move these 2 scalars into the same
migration pass" (they don't justify a dedicated migration on their own).

## Task 4 — Final Migration Audit

### 1. JSON/JSONL file counts before vs. after

| Scope | Count |
|---|---|
| `investment_screener/backend/data/**/*.json{,l}` — raw, this worktree | 21 |
| Same, excluding `data/cache/`, `data/13f/`, `data/etf_analysis/` (fetch caches) | 6 |
| `./ARCHIVE/**/*.json{,l}` (files actually migrated away) | 88 |
| Wave 0 repo-wide baseline (`wave0-schema-foundation-report.md`) | 212 |

The 6 domain-only files present in this worktree are exactly the approved retained set:
`portfolio.json`, `thesis_breaker_state.json`, `observations.jsonl`, `watchlist.json`,
`portfolio-config.json`, `theses/target-portfolio.json`. Six other "retained exception" files
named in the task brief — `cash_flows.json`, `trade-log.json`, `orders_executed.jsonl`,
`tv_cdp_errors.jsonl`, `tv_cdp_responses_cache.jsonl`, `ytd_performance_report.json`,
`projections/*.json` — are **absent from this worktree's disk**, not migrated away: they are
gitignored, per-worktree data (CLAUDE.md rule #29), so this worktree simply never had them
seeded. Their presence/liveness in the main checkout was not re-verified here (out of scope —
would require touching the main checkout, which this task's instructions forbid). Note
`watchlist.json` also shows as archived in `ARCHIVE/` (Wave 2) — confirmed below this is real:
`WatchlistService.ts` now reads SQLite (`InvestmentRepository.ts`), and the on-disk
`watchlist.json` present in this worktree is a stray/local copy, not a live producer target
(no runtime code writes or reads it — see §2).

The 88 archived files break down as 82 per-ticker projections (Wave 1) + `account_policy.json`
(Wave 5E) + `evals.json` + `predictions.jsonl` (Wave 5D) + `ta-sweep-results.json` (Wave 5B) +
`tradingview_alerts_actual.json` + `watchlist.json` (both Wave 2) = 88.

### 2. Remaining runtime JSON producers/consumers for migrated domains

Grepped `py_services/domain_model/`, `py_services/intelligence/`, and `src/services/` (not just
`plugins/`) for every archived filename. Findings, file by file:

- `account_policy.json` — hits in `rebalancer.py`, `ThesisService.ts` are **dead/deprecated
  code paths only**: `rebalancer.py` line 76 defines `ACCOUNT_POLICY_PATH` explicitly marked
  `# DEPRECATED, unused` (confirmed accurate — Task 5 above independently re-verified this),
  and `ThesisService.ts`'s hits are docstring prose ("formerly ... account_policy.json"), not
  code. `migrate_account_policy_to_sqlite.py` and `portfolio_policy_repository.py` are the
  (intentional, one-time) migration script and its real repository — not runtime JSON I/O.
- `watchlist.json` — `WatchlistService.ts`'s only hit is a docstring citation; the real reads
  route through `InvestmentRepository.ts` per its own comment. `paths.ts` still exports a path
  constant but nothing in `src/routes/docs.ts` calls it for reads (confirmed no `readFile`/
  `fs.` reference at that line). No live runtime producer/consumer left.
- `predictions.jsonl` — 8 files hit, all legitimate: `prediction_ledger.py`'s JSONL primitives
  are kept **on purpose** for the `--validate` CLI flag only (re-confirmed in Task 5 above with
  line numbers); `harvest_predictions.py`/`grade_predictions.py`/`alert_manager.py`/
  `earnings_expectations.py`/`generate_track_record_report.py`/`backtest_harness.py` all call
  into `prediction_ledger`'s SQLite-backed API, not the raw file, per Wave 5D's report
  (7/7 consumers migrated). `migrate_predictions_to_ledger.py` is the one-time migration script.
- `ta-sweep-results.json` — `compute_conviction_scores.py`, `evolution_events.py` read via the
  SQLite-backed helper per Wave 5B's report (3/3 consumers on SQLite, no fallback);
  `migrate_ta_sweep_to_ledger.py` is the one-time backfill; `audit_json_usage.py` is the
  audit tool itself (expected to reference every archived name).
- `tradingview_alerts_actual.json` — only hits are `audit_json_usage.py` (the audit tool) and
  `migrate_target_portfolio_to_sqlite.py` (one-time migration script). No runtime producer/consumer.
- `evals.json` — zero hits in `py_services/` or `src/`.
- Per-ticker projection files (`AAPL.json` etc., 82 files) — all hits (`compute_conviction_scores.py`,
  `rebalancer.py`, `system_health.py`, `harvest_predictions.py`, `ProjectionService.ts`,
  `ThesisService.ts`, etc.) resolve to the SQLite-backed `projection_repository.py` /
  `ProjectionRepository.ts` per Wave 1's report (18/18 consumers, 2/2 producers migrated);
  `migrate_projections_to_sqlite.py` is the one-time migration script; `db_client.py`'s hit is
  its own `projection_version`/`projection_scenario` table DDL comment, not file I/O.

**Conclusion:** zero live runtime JSON read/write paths found for any Wave 0–5E migrated domain
outside the approved retained exceptions. Every code-level hit on an archived filename is either
a deprecated/dead constant, a docstring citation, a one-time migration script, or the audit
tool itself.

### 3. Full SQLite table / repository / service inventory

`domain_model.sqlite` (20 tables, from `db_client.py`'s `CREATE TABLE` statements):

| Table | Repository (Python) | TS mirror |
|---|---|---|
| `account` | `account_repository.py` | — |
| `strategy_pillar` | `pillar_repository.py` | — |
| `sub_strategy` | `pillar_repository.py` | — |
| `investment` | `investment_repository.py` | `InvestmentRepository.ts` |
| `investment_price` | `investment_price_repository.py` | — |
| `account_investment` | `account_investment_repository.py` | `PortfolioRepository.ts` |
| `price_level_set` | `price_level_repository.py` | — |
| `price_level_tier` | `price_level_repository.py` | — |
| `alert` | `alert_repository.py` | — |
| `investment_note` | `investment_note_repository.py` | — |
| `projection_version` | `projection_repository.py` | `ProjectionRepository.ts` |
| `projection_scenario` | `projection_repository.py` | `ProjectionRepository.ts` |
| `trade_log_entry` | `trade_log_entry_repository.py` | `TradeLogRepository.ts` |
| `order_execution` | `order_execution_repository.py` | — |
| `cash_flow` | `cash_flow_repository.py` | — |
| `cash_flow_baseline` | `cash_flow_repository.py` | — |
| `portfolio_policy` | `portfolio_policy_repository.py` | — |
| `broker_exchange_rate` | `exchange_rate_repository.py` | — |
| `broker_reported_total` | `broker_reported_total_repository.py` | — |

`portfolio_repository.py` is a cross-table read helper (`account_investment` joins for
portfolio-value aggregation), not a distinct table's owner.

`intelligence.sqlite` (3 tables):

| Table | Repository |
|---|---|
| `instrument` | `instrument_repository.py` |
| `ledger_checkpoint` | `event_repository.py` / `event_store.py` |
| `intelligence_event` | `event_repository.py` / `event_store.py` |

**No dead schema found** (every table has an identifiable repository) and **no dead repository
found** (every `*_repository.py`/`.ts` file backs a real table above). `migrate_*.py` and
`backfill_*.py`/`seed_*.py` files in `domain_model/` are one-time scripts, not repositories, and
were excluded from this inventory on that basis.

### 4. Program-level Wave KPI rollup

| Wave | Domain | JSON files before → after | Files archived | Producers migrated | Consumers migrated | New tables |
|---|---|---|---|---|---|---|
| 0 | Schema/repo foundation | 212 → 212 (unchanged) | 0 | 0/0 | 0/0 | (all 20 domain_model tables created) |
| 1 | Projections | 82 → 0 | 82 | 2/2 | 18/18 | `projection_version`, `projection_scenario` |
| 2 | Target-portfolio/watchlist | 4 → 2 archived + 2 retained | 2 | 4/4 real | 23 (21 planned + 2 found) | (uses existing `investment` cols) |
| 3 | CAD exchange rate | (see `wave3-report.md` — no KPI table found; see note below) | — | — | — | `broker_exchange_rate`, `broker_reported_total`, `investment.sector`/`industry` |
| 4 | Portfolio ops (trade log/orders/cash flow) | 3 real (+1 `.example`) → 0 | 4 | 3/3 | 5/5 | `trade_log_entry`, `order_execution`, `cash_flow`, `cash_flow_baseline` |
| 5A | Research views | 0 → 0 (code-path fix only, no file migration) | 0 | 1/1 (unchanged) | 1 newly unconditional | — |
| 5B | TA sweep results | 1 → 0 | 1 | 1/1 | 3/3 | (uses existing tables via ledger) |
| 5C | Daily briefs | dual-write → ledger-only consumers | 0 this wave (dual-write retained for producer) | 1/1 (dual-write) | 5/5 ledger-only | — |
| 5D | Predictions | 1 → 0 | 1 | 1/1 | 7/7 | — |
| 5E | Account/portfolio policy | 1 → 0 | 1 | 1/1 | 2/2 | `portfolio_policy` |

Wave 3's own report (`wave3-report.md`) contains no `| KPI | Value |` table in the same format as
the others — its scope (CAD exchange rate + `investment.sector`/`industry` columns) is
documented narratively and in `wave3-cad-exchange-rate-retained-json.md` instead. Not fabricating
numbers for the missing row; flagging as a rollup-table gap rather than filling it with invented
values.

**Rollup total (files):** 212 (Wave 0 baseline) → 88 real files archived across Waves 1–5E → 6
domain-JSON files retained under explicit, documented exceptions (plus the gitignored-per-worktree
files noted in §1, whose main-checkout status this task did not re-verify).

### 5. Fresh test baseline (re-run this session, 2026-07-25)

Ran `cd investment_screener/backend && python3 -m pytest tests/py_services/` fresh. The full,
unfiltered run makes real live network calls (confirmed via `lsof` — an open HTTPS connection to
`e1.ycpi.vip.swb.yahoo.com`, i.e. real yfinance traffic) inside `test_backtest_report_generator.py`
and siblings under `test_backtest_*`; those tests fetch real historical prices for a rolling
30-day window and are slow enough (confirmed still running after 200s+ for a single file) that a
full unfiltered run is impractical to complete in this session.

Ran with `--ignore-glob='*backtest*'` (10 files, real network/git-history dependent, excluded)
to get a clean, reproducible number for the remaining 1,446 (of 1,488 total) tests:

**41 failed, 1,400 passed, 3 skipped, 2 xfailed, 1 warning in 65.73s**

This does not match either number cited in the kickoff prompt (44 failing / a stale "2 known
failures" since Wave 5A) — it is a third, freshly-measured number, and the backtest-suite (10
files) tests remain unaccounted for pass/fail (excluded for runtime, not because they're assumed
passing). Spot-verified 3 of the 41 failures are real, non-environmental regressions, not
sandbox/network artifacts:

- `test_order_execution_audit_trail.py` (11 failures) — `TypeError: log_order_execution() got an
  unexpected keyword argument 'orders_executed_path'`. The test suite calls a parameter name the
  real function signature no longer has — a genuine test/implementation drift, not flakiness.
- `test_fetch_consensus_for_ticker_returns_dict_or_none.py` (12 failures) — e.g.
  `assert result["consensus_eps"] == 1.05` fails with `8.26 == 1.05`; a mocked-`yfinance` test
  whose fixture data no longer matches the real parsing logic's field mapping — a real bug, not
  a network flake (the test mocks `yfinance` entirely via `patch.dict("sys.modules", ...)`).
- `test_portfolio_action_import.py::test_portfolio_action_reads_target_weight_from_sqlite_not_json`
  — expects `AAPL` action `TRIM`, gets `INITIATE`; a real logic/fixture mismatch in the
  SQLite-backed portfolio-action path.

The remaining ~18 failures (`test_earnings_expectation_claim_round_trips_ledger.py`,
`test_grade_earnings_expectations_classifies_beat_meet_miss.py`,
`test_harvest_earnings_expectations_path_isolation.py`,
`test_evolution_event_correlation_report_generates_summary.py`,
`test_evolution_integration_with_e3_prediction_ledger.py`,
`test_get_earnings_context_returns_prior_beat_rate.py`,
`test_audit_json_usage.py`, `test_daily_brief_ta_sweep_delegates.py`,
`test_post_trade_validation_matches_shares.py`) were not individually root-caused given this
task's time budget — flagging as unverified rather than assuming they're environmental.

**Bottom line:** neither the kickoff prompt's "44 failing" nor the older "2 known failures" number
is confirmed correct as of 2026-07-25. The real, fresh, reproducible number for 1,446 of 1,488
tests is **41 failed / 1,400 passed**; the 10 backtest files (42 tests) are unaccounted for due to
real network-call runtime, not skipped by choice.

## Task 5 — Architecture Simplification Review (COMPLETE)

Re-checked all three Wave 5E cleanup candidates against current code before touching anything.

1. **`rebalancer.py`'s `account_policy_path`/`ACCOUNT_POLICY_PATH`** — still genuinely needed.
   `tests/py_services/test_rebalancer.py` (lines 624, 647, 661, 681, 692, 709) still passes
   `account_policy_path=` by name to `compute_rebalance_plan()`, including a dedicated test
   confirming the parameter is accepted-but-unused via a nonexistent-file path. Left untouched —
   deleting it would break 6 live test call sites, not just a doc mention.

2. **`order_risk_gates.py`'s dead `ACCOUNT_POLICY_PATH` constant** — re-confirmed unread. Grepped
   all callers of `order_risk_gates` across the repo (`place_order.py` import, ~15 test files) —
   none reference `ACCOUNT_POLICY_PATH`. **Deleted** the constant (was line 184, between
   `RISK_SNAPSHOT_PATH` and `THESIS_BREAKER_STATE_PATH`). Ran the two most relevant test files
   (`test_order_risk_gates_composite_check.py`, `test_order_risk_gates_target_path_constant.py`):
   12 passed, 0 failed.

3. **`prediction_ledger.py`'s JSONL primitives** (`_append_jsonl`, `load_predictions`,
   `load_graded`) — confirmed still real and wanted. The module's own docstring (lines 16-44)
   states they're kept solely for `_validate_all()` behind the `--validate` CLI flag (line 287,
   `python3 prediction_ledger.py --validate`), and `load_predictions`/`load_graded` are actively
   called at lines 265/271 inside that validation path. `prediction_ledger` is imported by 5
   sibling `py_services` scripts and covered by `test_prediction_ledger.py` and
   `test_prediction_ledger_validate.py`. Kept as-is — no dead code here.

**Final sanity sweep** (per ADR-029's "pivot not addition" goal — SQLite must be the primary store,
no permanent JSON+SQLite hybrid): grepped `py_services/domain_model/`, `py_services/intelligence/`,
and `src/services/` for deprecated markers, dual-write comments, and JSON-fallback language. Only
hit: `BrokerSyncService.ts` lines 263 and 380, both referencing "Wave 3 Task 8 (final dual-write
reduction): this is now the SOLE write in..." — this is a historical comment documenting that
dual-write was already *removed*, not a leftover shim itself. No other stray migration-only
compatibility adapters, dead dual-read paths, or duplicate JSON+SQLite readers were found in the
three directories searched.

**Net change this task:** 1 line deleted (`order_risk_gates.py` dead constant). No other edits.
Not committed — left unstaged per instructions.

## Wave KPI Rollup

See Task 4 §4 above for the full per-wave rollup table (Waves 0–5E). Summary: 212 JSON files at
Wave 0 baseline → 88 archived across Waves 1–5E → 6 domain-JSON files remain as documented,
approved retained exceptions. All 20 `domain_model.sqlite` tables and 3 `intelligence.sqlite`
tables have identifiable, real repositories (no dead schema, no orphan repository). Zero live
runtime JSON producers/consumers remain for any migrated domain outside the approved exceptions.

## Open Items Not Resolved This Wave (deliberately, not oversights)

1. **`changeLog` and `thesisBreakers`** in `target-portfolio.json` still need new SQLite schema
   (or an `intelligence_event`-based design) before `target-portfolio.json` can be fully retired —
   scoped as a candidate for a dedicated future wave, not attempted here (Wave 6 makes retention
   *decisions*, this one's decision is "formally retain, migration path identified").
2. **`thesis_breaker_state.json`** has no formally documented retention decision anywhere prior to
   this wave despite being a real, live 5-consumer read/write path — this report's Task 3 section
   closes that documentation gap by formally retaining it with a stated future migration trigger.
3. **`daily_brief.py`'s dual-write** to legacy `data/daily-briefs/*.json` alongside the SQLite
   `REVIEW_DAILY` event (flagged in Task 2, not independently re-confirmed in Task 5's sweep) —
   an open item for a future pass, not resolved this wave.
4. **18 of the 41 real test failures** found in Task 4's fresh baseline were not individually
   root-caused (time budget) — flagged as unverified, not assumed environmental or pre-existing.
5. **`.agents/agents/portfolio-advisor-daily-loop-agent.md`** is a stale copy of an already-fixed
   `plugins/` source file (Task 2) — outside this wave's `plugins/`-scoped grep, flagged only.
6. **Two open schema-design questions** from Task 1 (`trade_log_entry.account_id` vs.
   `cash_flow.account` FK inconsistency; `portfolio_policy`'s citation-accuracy gap) — deliberately
   left as flagged questions, not resolved, per Task 1's brief (transcription, not redesign).
