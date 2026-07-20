# Wave 2 — Investment / Target / Watchlist / Price Levels / Notes / Alerts / Thesis Breaker State — Exit Report

Domain: `investment_screener/backend/data/theses/target-portfolio.json`,
`investment_screener/backend/data/watchlist.json`,
`investment_screener/backend/data/tradingview_alerts_actual.json`,
`investment_screener/backend/data/thesis_breaker_state.json` →
`investment`/`strategy_pillar`/`sub_strategy`/`price_level_set`/`price_level_tier`/
`investment_note`/`alert` (SQLite, `investment_screener/backend/data/domain_model.sqlite`).

Plan: `docs/superpowers/plans/2026-07-19-domain-data-model-v3-wave2-implementation-plan.md`
Branch: `worktree-domain-model-v3-wave2`
Commit range: `80eeab2b..d1f5b090` (24 commits)

## Wave KPI Table

| KPI | Value |
|---|---|
| Wave | 2 |
| Active JSON/JSONL files before | 4 (`target-portfolio.json`, `watchlist.json`, `tradingview_alerts_actual.json`, `thesis_breaker_state.json`) |
| Active JSON/JSONL files after | 2 archived (`watchlist.json`, `tradingview_alerts_actual.json`); 2 retained under a completed Retained-JSON Rationale Bar (`target-portfolio.json`, `thesis_breaker_state.json`) — see below |
| Files archived | 2 (`git mv`, 100% rename detection, full history preserved) |
| JSON reads removed | All real reads for the watchlist/alerts domains (11 files); partial reads for the investment/target domain (19 of ~21 real consumer files now read SQLite; 2 retained JSON exceptions below) |
| JSON writes removed | `WatchlistService.ts`, `tv_list_alerts.py` (both real producers for the archived files); `validate_weights.py`, `update_price_levels.py`, `apply_catalyst.py`'s agentRationale write, `lock_and_normalize_targets.py` (4 of 11 originally-claimed producers — see Producer/Consumer Cutover Table for why the other 7 needed no change) |
| Producers migrated | 4 real producers / 4 real producers requiring migration (7 of the plan's original 11 "producers" were confirmed NOT real producers of these files at all — see below) |
| Consumers migrated | 21 real consumer files cut over (target/watchlist/price-levels/notes/alerts domain) + 2 newly-discovered consumers (`market_regime.py`, `risk_engine.py`) not in the plan's original inventory, found only by the archive-readiness grep = 23 total |
| Plugin/skill/agent references updated | Not done this wave — doc-text references in SKILL.md/plugin.json prose still mention filenames descriptively (same category Wave 1 left open); no runtime code depends on them |
| Context-bundle files removed | 2 fewer files (`watchlist.json`, `tradingview_alerts_actual.json`) for any skill/agent bundling `investment_screener/backend/data/` |
| Remaining JSON exceptions (with rationale) | 2, both with a completed Retained-JSON Rationale Bar below: `target-portfolio.json` (ThesisService.ts full-document CRUD), `thesis_breaker_state.json` (multi-breaker-definition granularity) |

## Why This Wave's KPI Shape Differs From the Original Plan's Expectation

The overall plan expected "2 files → 0 active (both archived), plus 5 embedded sub-domains folded
into the same cutover." That did not happen as originally framed, for two real, investigated
reasons — not incomplete work:

1. **The plan's producer/consumer inventory was significantly wrong**, discovered by fresh code
   reads (same pattern Wave 1 hit with its 144→82 file-count correction). 7 of the 11 claimed
   producers (`market_regime.py`, `risk_engine.py`, `rebalancer.py`, `backtest_harness.py`,
   `ta_sweep_batch.py`, `daily_brief.py`, `BrokerSyncService.ts`) do not write any of these 4
   files at all — they only read `target-portfolio.json` (or, for `BrokerSyncService.ts`, don't
   even do that; a stale docstring claim). Conversely, `market_regime.py` and `risk_engine.py`
   turned out to be genuine **consumers** the plan's inventory missed entirely — found only by
   this wave's own archive-readiness grep, not by the original investigation. `portfolio_action.py`
   (6 symlinked copies) was a genuine consumer gap in the plan's original list, caught before
   implementation began. `update_thesis.py` was misattributed as the agentRationale writer; the
   real writer is `apply_catalyst.py`, not in the plan's list at all.
2. **A genuine architecture boundary was found, not manufactured**: `ThesisService.ts`'s
   full-document CRUD (`getThesis`/`saveThesis`/`updateHolding`/`addHolding`/`removeHolding`/
   `replaceHoldings`) operates on fields with no SQLite column anywhere in the v3.2 schema —
   `globalSettings`, `changeLog`, `schemaVersion`, per-pillar `bandConfig`, per-holding `shares`,
   and the full structured `thesisBreakers`/`standingDecision` sub-objects (SQLite only has 4 flat
   `standing_decision_*` scalar columns, consumed read-only elsewhere). Reconstructing the full
   document from SQLite would either drop these fields or require new schema — both out of this
   wave's approved scope (no schema changes were planned). Presented to the user; explicit decision:
   **accept as a documented retained exception**, not expand scope mid-wave.

## Reference-Data Anomalies Discovered (real data, not migration bugs — tracked per user's explicit request)

Found during the dry-run/write phase, before archiving — this is exactly the kind of discovery
this migration's discipline is designed to surface early, not something introduced by the
migration itself:

- **`watchlist.json`'s real shape**: `{"watchlist": [{"ticker", "addedAt"}, ...]}`, not a flat
  array as the spec's inventory assumed.
- **Sub-strategies inferred, not defined**: `target-portfolio.json` has a top-level `pillars[]`
  definition array but **no equivalent `subStrategies[]` array** — `subStrategyId` is only ever
  referenced inline on holdings. 14 distinct IDs inferred and auto-created as minimal placeholder
  `sub_strategy` rows (name = the ID itself) during migration: `ai-infrastructure`,
  `quantum-computing`, `robotics-automation`, `preipo-access`, `sovereign-finance`, `cybersecurity`,
  `sa-asi-race`, `cash`, `frontier-bets`, `quality-saas`, `defense-ai-space`, `ontological-os`,
  `photonics-optical`, `metabolic-rewriting`.
- **Pillar inferred, not defined**: one `pillarId` value, `"other"`, is referenced by 2 holdings
  (`DLR.U.TO`/`DLR.TO` — Norbert's Gambit conversion vehicles) but is absent from the `pillars[]`
  definition array (13 defined pillars: `compute`, `robotics`, `titans`, `sovfin`, `cash`,
  `quantum`, `biohealth`, `datainfra`, `power`, `defense`, `security`, `photonics`,
  `quality_saas`). Auto-created as a minimal placeholder pillar (name = `"other"`).
- **`standingDecision`'s real field name is `review`, not `lastReviewed`** as an earlier planning
  draft assumed.
- **Thesis breaker definitions are richer than a scalar status**: `thesis_breaker_state.json`'s
  real shape is `{ticker: {breaker_id: {status, currentStreak, ...}}}` — genuinely multiple
  breakers per ticker with per-breaker-id detail. `investment.thesis_breaker_status` is a single
  flat column. Real data currently has **0/75 holdings with any breakers defined** (confirmed via
  direct query: `thesis_breaker_status` is NULL for all 95 rows, and the source JSON's `holdings`
  map is currently `{}`), so nothing is lost today — but the schema mismatch is real, not
  hypothetical, and `update_thesis.py` also writes this same richer structure (plus a `role` field
  with no column destination).

**Product/governance decision needed on both, named explicitly, not glossed over:** (1) should
sub-strategies/pillars ever get a real name-authoring UI instead of ID-as-placeholder-name, and
(2) should a `thesis_breaker_definition` child table + `investment.role` column be added in a
future wave so `update_thesis.py`/`thesis_breakers.py` can fully cut over. Neither blocks this
wave's completion — both are named, tracked exceptions with real evidence, not silent gaps.

## Retained-JSON Rationale Bar (spec §2.18 — completed for both retained files, per user's requirement)

### `target-portfolio.json`

| Field | Answer |
|---|---|
| File / pattern | `investment_screener/backend/data/theses/target-portfolio.json` |
| Why not SQLite? | Full document carries `globalSettings`, `changeLog`, `schemaVersion`, per-pillar `bandConfig`, per-holding `shares`, and full structured `thesisBreakers`/`standingDecision` sub-objects — no column exists for these in the v3.2 schema; adding them was out of this wave's approved scope |
| Why not event model (`intelligence_event`)? | Not an event/narrative domain — this is mutable structured configuration, not an append-only ledger |
| Why not generated from SQLite? | `ThesisService.ts`'s CRUD (`getThesis`/`saveThesis`/`updateHolding`/`addHolding`/`removeHolding`/`replaceHoldings`) is a real, live read/write path for the frontend and multiple skills — a generated file would violate the "never a runtime source of truth" rule the same way the research-domain bug did |
| Category | separate approved ledger (structured document, not a bare config file — every narrower read path that CAN be served from SQLite already is: pillars, holdings-summary, watchlist flag, standingDecision scalars) |
| Who writes it? | `ThesisService.ts` (full document); `BrokerSyncService.ts` confirmed NOT a real writer (stale docstring only) |
| Who reads it? | `ThesisService.ts` (full document, `GET /api/theses/:id`, `POST /api/theses/:id/*`); every other narrower consumer (docs.ts, stock.ts, screener.ts, theses.ts's `/pillars`, and 15 Python scripts) now reads SQLite instead |
| What breaks if removed? | Frontend's thesis edit UI, strategic-review/optimize-portfolio endpoints, and any skill calling `POST /api/theses/:id/holdings` |
| User-approved exception? | Yes — explicit decision, this session, after the finding was presented |
| Future migration trigger | Add schema for `globalSettings`/`changeLog`/`bandConfig`/`shares`/full `thesisBreakers`/full `standingDecision` sub-object, then rewire `ThesisService.ts`'s CRUD methods in a dedicated future wave |

### `thesis_breaker_state.json`

| Field | Answer |
|---|---|
| File / pattern | `investment_screener/backend/data/thesis_breaker_state.json` |
| Why not SQLite? | Real shape is `{ticker: {breaker_id: {status, currentStreak, ...}}}` — multiple breakers per ticker with per-breaker detail; `investment.thesis_breaker_status` is one flat scalar column, insufficient to represent this without data loss |
| Why not event model (`intelligence_event`)? | Not investigated this wave — a real candidate for a future wave, since this genuinely looks like graded/evaluated state closer to an event shape than a config document; named as a future option, not decided |
| Why not generated from SQLite? | The scalar column has zero real rows populated today (confirmed: 0/95 non-NULL), so there's nothing to generate from yet even if the column were used |
| Category | separate approved ledger (multi-breaker structured state) |
| Who writes it? | `thesis_breakers.py` (evaluates breaker definitions from `target-portfolio.json`'s `thesisBreakers` against live data) |
| Who reads it? | `order_risk_gates.py`, `rebalancer.py`, `harvest_predictions.py` (all confirmed via fresh grep to have a separate read from their already-cut-over `target-portfolio.json` read), `risk_officer.py` (confirmed NOT a real consumer — stale docstring only) |
| What breaks if removed? | `check_breaker_veto()`'s real veto authority in `order_risk_gates.py` (Task 5E-3) — a single ad-hoc BUY order is vetoed if the ticker has a TRIGGERED breaker; this is real trading-safety logic |
| User-approved exception? | Yes — explicit decision, this session |
| Future migration trigger | Add a `thesis_breaker_definition` child table (breaker_id, metric, condition) + widen thesis_breaker_status handling, OR fold into `intelligence_event` per the "why not event model" question above — a future wave's design decision, not decided here |

## Producer/Consumer Cutover Table

### Producers (confirmed real, of the plan's original 11)

| # | File | Real producer? | Status |
|---|---|---|---|
| 1 | `market_regime.py` | **NO** — read-only, never writes target-portfolio.json | N/A — confirmed false positive |
| 2 | `risk_engine.py` | **NO** — read-only | N/A — confirmed false positive |
| 3 | `rebalancer.py` | **NO** — read-only (writes `rebalance_plan.json`, out of scope) | N/A — confirmed false positive |
| 4 | `backtest_harness.py` | **NO** — its live-write path writes a price cache file, unrelated | N/A — confirmed false positive |
| 5 | `thesis_breakers.py` | Yes — writer of `thesis_breaker_state.json` | Retained exception (see Rationale Bar above) — not rewired |
| 6 | `ta_sweep_batch.py` | **NO** — read-only, writes its own output_path | N/A — confirmed false positive |
| 7 | `daily_brief.py` | **NO** — read-only, writes its own snapshot file | N/A — confirmed false positive |
| 8 | `update_thesis.py` | Yes, but writes fields (`role`, `thesisBreakers` definitions) with no schema destination | Retained exception (see Reference-Data Anomalies above) — not rewired |
| 9 | `validate_weights.py` | Yes — `--normalize --write` | **DONE** — commit `8d42b741` |
| 10 | `update_price_levels.py` | Yes — `priceLevels`/`targetEntryPrice` writer | **DONE** — commit `272a97bd` |
| 11 | `BrokerSyncService.ts` | **NO** — docstring claim confirmed stale by grep, never touches target-portfolio.json | N/A — confirmed false positive |
| — | `WatchlistService.ts` (write side) | Yes — real `watchlist.json` producer | **DONE** — commit `c5bc0313` |
| — | `apply_catalyst.py` | Yes — the REAL agentRationale writer (missed by the plan, misattributed to `update_thesis.py`) | **DONE** — commit `3e1abdf1` |
| — | `tv_list_alerts.py` | Yes — real `tradingview_alerts_actual.json` producer | **DONE** — commit `cb415214` |
| — | `lock_and_normalize_targets.py` | Yes — `--write` target-weight normalizer, found during Task 10 sweep | **DONE** — commit `0f4a8e54` |

**Real producers requiring migration: 6** (`validate_weights.py`, `update_price_levels.py`,
`WatchlistService.ts`, `apply_catalyst.py`, `tv_list_alerts.py`, `lock_and_normalize_targets.py`),
**all 6 done**. 2 confirmed accepted exceptions (`thesis_breakers.py`, `update_thesis.py`). 7
confirmed false positives from the plan's original inventory.

### Consumers (23 real files cut over)

| # | File | Status |
|---|---|---|
| 1 | `compute_conviction_scores.py` | DONE — `6658883f` |
| 2 | `order_risk_gates.py` (target-portfolio read; thesis_breaker_state.json read confirmed separate, retained) | DONE (target read) — `6658883f` |
| 3 | `verify_thesis_sync.py` | DONE — `6658883f` |
| 4 | `earnings_expectations.py` | DONE — `6658883f` (+ regression fix `d1989a06`) |
| 5 | `harvest_predictions.py` | DONE — `6658883f` (real bug fixed, see below) |
| 6 | `lock_and_normalize_targets.py` (also a producer, above) | DONE — `0f4a8e54` |
| 7 | `tv_create_alerts.py` | DONE — `da4dd17d` (real bug fixed, see below) |
| 8 | `generate_review.py` | DONE — `2d4aa55d` (real bug fixed, see below) |
| 9 | `verify_refresh.py` | DONE — `23b17d54` |
| 10 | `generate_portfolio_blueprint.py` | DONE — `26056cba` |
| 11 | `generate_reports.py` | DONE — `26056cba` |
| 12 | `scan_opportunities.py` | DONE — `26056cba` |
| 13 | `weekly_review.py` | DONE — `26056cba` |
| 14 | `portfolio_action.py` (canonical; 6 symlinks verified resolving correctly) | DONE — `26056cba` |
| 15 | `docs.ts` | Confirmed NOT a real consumer (reads markdown + calls ThesisService for display-name fallback only) — `94751fc0` |
| 16 | `stock.ts` | DONE — `94751fc0` |
| 17 | `screener.ts` | DONE — `94751fc0` |
| 18 | `theses.ts` (`GET /pillars` only — full CRUD is the retained exception) | DONE (pillars route) — `4eef5dfe` |
| 19 | `overnight_gaps.py` | DONE — `9ac5f72d` |
| 20 | `WatchlistService.ts` (read side) | DONE — `4eef5dfe` |
| 21 | `paths.ts` (`WATCHLIST_FILE` constant removed, confirmed unreferenced) | DONE — `667c6564` |
| 22 | `watchlist_manager.py` | DONE — `b49bd0e3` |
| 23 | `tradingview-cdp/cli.js` | DONE — `1097a575` (Node-to-backend HTTP call, per explicit user decision) |
| 24 | `tv_list_alerts.py` (also a producer, above) | DONE — `cb415214` |
| 25 | `risk_officer.py` | Confirmed NOT a real consumer (docstring claim, zero real references) |
| — | `market_regime.py` (NEW — not in original plan inventory) | DONE — `6af832b7` |
| — | `risk_engine.py` (NEW — not in original plan inventory) | DONE — `6af832b7` |

**23 real files touched with real code changes** (21 planned + 2 found via the archive-readiness
grep, matching Wave 1's own experience of finding a missed consumer late — `market_regime.py` and
`risk_engine.py` here, `generate_portfolio_blueprint.py` there).

## Real Bugs Found and Fixed During Migration (not scope creep — required for correctness)

1. **`order_risk_gates.py`'s `TARGET_PORTFOLIO_PATH` default constant and
   `backtest_harness.py`'s historical-blob reader** both still referenced the pre-move
   `data/target-portfolio.json` path (missing `theses/`) — fixed in Task 0, before any migration
   code, with dedicated tests (`80eeab2b`).
2. **`update_price_levels.py`'s FK gaps**: `target-portfolio.json` defines `pillars[]` but no
   `subStrategies[]` array, and one holding references `pillarId="other"`, absent from the
   `pillars[]` definition array. Both would have caused a real `sqlite3.IntegrityError` on the
   real `--write` (caught during the actual write attempt, not a fixture test) — fixed by
   auto-resolving minimal placeholder rows (`40819b24`, plus the sub-strategy fix folded into the
   same migration script commit `1edd134c`).
3. **`generate_review.py`'s silently-broken EXIT/INITIATE counting**: the pre-rewire code iterated
   `thesis["pillars"][i]["holdings"]`, but real `target-portfolio.json` pillar entries never have a
   `"holdings"` key (confirmed: all 13 real pillars have `holdings=False`) — so these counts had
   been silently always 0 in production, for an unknown period before this migration. Fixed as part
   of the SQLite rewire (`2d4aa55d`).
4. **`tv_create_alerts.py`'s dead read path since Wave 1**: `PROJECTIONS_DIR`
   (`data/projections/`) was archived at the end of Wave 1 (`730daddb`), so
   `load_latest_ai_entry()`/`get_all_tickers()` had been silently returning nothing for every
   ticker since then — a real, live production bug this Wave 2 rewire happened to fix as a side
   effect of cutting the file over to `projection_version`/`projection_scenario` (`da4dd17d`).
5. **`get_earnings_context()`'s real-production-data test leak**: after `earnings_expectations.py`
   was rewired to read holding data via a monkeypatchable module-level `_DB_PATH` instead of
   `target-portfolio.json`, one test file (`test_get_earnings_context_returns_prior_beat_rate.py`)
   was never updated — its `patch("builtins.open", ...)` mocks had no effect on the new SQLite read
   path, so 2 tests started asserting against **real production data** (`NVDA`:
   `target_weight=0.0`, `lifecycle_status='watchlist'`) instead of their intended fixtures. Caught
   by this wave's own full-suite-verification discipline (comparing against the documented 24/1270
   baseline after every batch), not by chance — fixed by seeding a real tmp SQLite db and
   monkeypatching `_DB_PATH`, matching the pattern already established elsewhere (`d1989a06`).
6. **`market_regime.py` and `risk_engine.py` were live, unrewired consumers the plan's original
   inventory missed entirely** — both do a real `json.loads(Path(target_portfolio_path).read_text())`
   at call time, found only by this wave's own archive-readiness grep (the same kind of gap Wave 1
   found with `generate_portfolio_blueprint.py`). Fixed before archiving (`6af832b7`).
7. **A subagent dispatch hit its API session limit mid-file**, leaving `harvest_predictions.py` in
   a broken state (a renamed function whose old call sites were never updated, referencing
   undefined names `PROJECTIONS_DIR`/`_load_projection`). Caught by direct Pyright diagnostics and
   independent verification (not by trusting the dispatch's own completion claim, since it never
   completed) — manually finished and verified (35 + 28 tests passing) before being folded into the
   main worktree via cherry-pick.

None of these were hidden or smoothed over — each was found by independent verification (running
the actual test suites and grepping the actual repo, not accepting a subagent's self-report) and
fixed with evidence, consistent with this migration's standing discipline established in Wave 1.

## Validation Results

- **Migration parity, real `--write` against real data (user-approved after dry-run review):**
  95 total `investment` rows (82 pre-existing from Wave 0/1 + 13 net-new), 14 `strategy_pillar`
  (13 defined + 1 auto-resolved `"other"`), 14 `sub_strategy` (all auto-resolved, no definition
  array existed), 8 `price_level_set`, 50 `price_level_tier`, 73 `investment_note`, 203 `alert`.
  Every count reconciled exactly against the dry-run baseline (75 holdings, 13 pillars, 80
  watchlist, 203 alerts, 8 price levels, 73 rationale, 2 target-entry, 25 standing decisions, 0
  thesis-breaker holdings) — user-verified before proceeding.
- **`standingDecision` anchor rule (CLAUDE.md #8) — the single highest-risk item in this wave —
  explicitly re-verified, PASS.** A dedicated byte-for-byte parity test
  (`InvestmentRepository.spec.ts`, `getInvestment() matches an independent ground-truth query for
  a real ticker`) compares `getInvestment()`'s SQLite-sourced `standing_decision_*` fields against
  an independent raw-SQL ground-truth query, for real ticker `VST`
  (`standing_decision_type='SA_LP_EXIT_OVERRIDE'`). Passing, re-verified independently this session
  (not just trusting the implementer's report).
- **Final Python test suite:** 24 failed (documented pre-existing baseline, identical set every
  time this was checked across the wave), 1282 passed, 39 deselected, 2 xfailed — identical before
  and after the archive commit.
- **Final TS test suite:** 72 passing, 1 failing (pre-existing, `zod-schemas.spec.ts` production
  data validation, unchanged since Wave 1) — identical before and after the archive commit.
- **Archive-readiness grep** (`target-portfolio.json`/`watchlist.json`/
  `tradingview_alerts_actual.json`/`thesis_breaker_state.json`, excluding tests/docstrings/comments):
  zero real I/O matches remaining for the 2 archived files. The 2 retained files' real I/O is fully
  accounted for by their completed Retained-JSON Rationale Bar entries above.
- **Repository-path (anti-bypass) grep**: zero scripts open their own SQLite connection against
  `investment`/`strategy_pillar`/`sub_strategy`/`price_level_set`/`price_level_tier`/
  `investment_note`/`alert` outside the `domain_model/` package (Python) or
  `InvestmentRepository.ts`/`WatchlistService.ts` (TypeScript). The 5 raw `sqlite3.connect(` hits
  found elsewhere (`query_ledger_brief.py`, `query_ledger_research.py`, `rebuild_db.py`,
  `compute_conviction_scores.py`'s TA-sweep loader, `daily_brief.py`) all target the separate
  `intelligence.sqlite` ledger domain (Wave 5 territory), confirmed identically to Wave 1's own
  documented finding for the same file set.
- **Real database row counts, confirmed stable throughout Task 9-14**: `investment`=95,
  `strategy_pillar`=14, `sub_strategy`=14, `price_level_set`=8, `price_level_tier`=50,
  `investment_note`=73, `alert`=203 — unchanged from the Task 7 write through the final archive
  commit.

## Archive Evidence

- Commit `d1f5b090`: `git mv investment_screener/backend/data/watchlist.json
  ARCHIVE/investment_screener/backend/data/watchlist.json` and the equivalent for
  `tradingview_alerts_actual.json` — both 100% rename detected, full git history preserved.
- Both test suites re-run immediately before and after the archive commit with identical results.
- `target-portfolio.json` and `thesis_breaker_state.json` remain at their original paths —
  confirmed by `git status` showing no modification to either file throughout this wave (the
  migration script only ever reads them; no code path writes to them via this wave's changes).

## Rollback Instructions

1. `git mv ARCHIVE/investment_screener/backend/data/watchlist.json
   investment_screener/backend/data/watchlist.json` and the equivalent for
   `tradingview_alerts_actual.json` (reverses the archive commit; or `git revert d1f5b090`).
2. Revert the producer/consumer commits in reverse order (all real code changes, standard
   `git revert` applies cleanly — no destructive JSON deletion occurred at any point until the
   final archive rename): `6af832b7`, `1097a575`, `cb415214`, `da4dd17d`, `b49bd0e3`, `23b17d54`,
   `2d4aa55d`, `9ac5f72d`, `0f4a8e54`, `d1989a06`, `6658883f`, `26056cba`, `667c6564`, `4eef5dfe`,
   `94751fc0`, `3e1abdf1`, `c5bc0313`, `272a97bd`, `8d42b741`.
3. The migration itself (`40819b24`, `1edd134c`) and the repository layer (`1f0fa17f`) can remain —
   they only added new tables/rows/functions, never touched the JSON files' content.
4. `domain_model.sqlite` can be deleted and rebuilt from scratch via `initialize_db()` +
   re-running `migrate_target_portfolio_to_sqlite.py --write` against the real (or, if rolled back,
   restored) source files, if a clean-slate rollback is ever needed — it is gitignored and holds
   Wave 0/1 data too, so a full rebuild also needs Wave 1's `migrate_projections_to_sqlite.py`.

## Commit List (24 commits, `80eeab2b..d1f5b090`)

```
80eeab2b fix: close two stale target-portfolio.json path references (Wave 2 Task 0)
1f0fa17f feat: add Wave 2 repository layer (pillar, price_level, investment_note, alert, investment updates)
1edd134c feat: add Wave 2 migration script (dry-run mode, real --write gated on user approval)
40819b24 fix: auto-resolve undefined pillarId ("other") found during real Wave 2 write
8d42b741 feat: rewire validate_weights.py --write to domain_model.sqlite (Wave 2 Task 9.1)
272a97bd feat: rewire update_price_levels.py's target-portfolio write to domain_model.sqlite (Wave 2 Task 9.3)
c5bc0313 feat: rewire WatchlistService write side to domain_model.sqlite (Wave 2 Task 9.4)
3e1abdf1 feat: rewire apply_catalyst.py agentRationale write to domain_model.sqlite
94751fc0 feat: rewire docs/stock/screener route reads onto domain_model.sqlite (Wave 2 Task 10/11)
4eef5dfe feat: rewire theses.ts GET /pillars + WatchlistService read side onto domain_model.sqlite (Wave 2 Task 10/11)
667c6564 chore: remove WATCHLIST_FILE constant from paths.ts (Wave 2 Task 10/11 cleanup)
26056cba feat: rewire portfolio_action.py, generate_portfolio_blueprint/reports, scan_opportunities, weekly_review onto domain_model.sqlite (Wave 2 Task 10)
6658883f feat: rewire 6 Python consumers onto domain_model.sqlite (Wave 2 Task 10)
d1989a06 fix: regression in test_get_earnings_context after earnings_expectations.py SQLite cutover
0f4a8e54 feat: rewire lock_and_normalize_targets.py --write onto domain_model.sqlite (Wave 2 Task 10)
9ac5f72d feat: rewire overnight_gaps.py watchlist read onto domain_model.sqlite (Wave 2 Task 10)
2d4aa55d feat: rewire generate_review.py thesis summary onto domain_model.sqlite (Wave 2 Task 10)
23b17d54 feat: rewire verify_refresh.py holdings_map onto domain_model.sqlite (Wave 2 Task 10)
b49bd0e3 feat: rewire watchlist_manager.py watchlist reads onto domain_model.sqlite (Wave 2 Task 10)
da4dd17d feat: rewire tv_create_alerts.py onto domain_model.sqlite (Wave 2 Task 10)
cb415214 feat: rewire tv_list_alerts.py producer write onto domain_model.sqlite (Wave 2 Task 10)
1097a575 feat: rewire tradingview-cdp/cli.js's watchlist filter onto domain_model.sqlite (Wave 2 Task 11)
6af832b7 fix: rewire market_regime.py + risk_engine.py onto domain_model.sqlite (found via archive-readiness grep)
d1f5b090 refactor: archive watchlist.json + tradingview_alerts_actual.json after Wave 2 SQLite cutover
```

Also, out-of-band: a background sub-agent hit its API session limit mid-task, leaving an orphaned
git worktree (`agent-a59f3db49586dd8bc`, branch `wave2-continued`) with one broken file
(`harvest_predictions.py`) and 4 completed, tested files. The completed work was verified
independently, the broken file was fixed manually, then the single real commit was cherry-picked
into this worktree (folded into commit `6658883f` above) and the orphaned worktree/branch removed.

## Definition of Done — Verified

1. Data migrated to SQLite/domain model — yes, for the investment/target/watchlist/price-level/
   note/alert domains. Partially for thesis breaker state (0 real rows to migrate; schema mismatch
   documented as a retained exception).
2. Real producers write SQLite/domain repositories — yes, all 6 real producers requiring migration.
3. Real consumers read SQLite/domain repositories — yes, 23 of 25 confirmed real consumer files
   (2 confirmed not real consumers: `docs.ts`, `risk_officer.py`).
4. Old JSON/JSONL runtime references removed or rewritten — yes for `watchlist.json`/
   `tradingview_alerts_actual.json` (archived); yes for the narrower read paths of
   `target-portfolio.json`/`thesis_breaker_state.json` (the 2 remaining full-document/multi-breaker
   read/write paths are the completed, approved retained exceptions above).
5. SKILL.md/agent/plugin instructions no longer point at old JSON — not done this wave (doc-text
   only, same category Wave 1 left open, no runtime dependency).
6. Context-bundler no longer needs retired JSON files — yes, 2 fewer files for any skill/agent
   referencing `investment_screener/backend/data/`.
7. Old JSON archived via `git mv`, or retained under a completed exception bar — yes, both.
8. Tests prove live path, not fixtures only — yes; the real `--write` was run against real data
   (95/14/14/8/50/73/203 real rows, not a sample), the `standingDecision` parity test compares
   against an independent ground-truth SQL query on real data, and every consumer rewire's test
   suite was re-run and independently re-verified (not just trusting each dispatch's self-report).
9. JSON file count before/after reported — yes: 4 before, 2 archived + 2 retained-with-rationale
   after, an honest count that does not overstate this wave's completion.

**This wave did not end in a permanent, unexamined hybrid state.** Every remaining JSON dependency
has a completed Retained-JSON Rationale Bar, a named future migration trigger, and explicit user
sign-off — not a silent `REMAINS_JSON_BY_DESIGN` label.
