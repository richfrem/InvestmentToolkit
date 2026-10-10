# JSON Discovery Audit

## Summary

| Category | Count |
|---|---:|
| JSON files discovered | 159 |
| JSONL files discovered | 2 |
| Files classified RETIRED_PORTFOLIO_DATA | 1 |
| Files classified ALLOWED_CONFIGURATION_JSON | 37 |
| Files classified ALLOWED_MODEL_ARTIFACT_JSON | 22 |
| Files classified ALLOWED_SEPARATE_DOMAIN_LEDGER_JSONL | 0 |
| Files classified ALLOWED_TEST_FIXTURE_JSON | 73 |
| Files classified ALLOWED_GENERATED_CACHE_JSON | 2 |
| Files classified MIGRATE_TO_INTELLIGENCE_LEDGER | 0 |
| Files classified GENERATE_FROM_LEDGER_OR_SQLITE | 0 |
| Files classified ARCHIVE_LEGACY_READ_ONLY | 2 |
| Files classified DELETE_AFTER_VERIFIED_ARCHIVE | 0 |
| Files classified OUT_OF_SCOPE_FOR_THIS_PHASE | 16 |
| Files classified UNKNOWN_REQUIRES_REVIEW | 8 |

## High-Risk Findings

- **Nothing has been migrated to SQLite/the intelligence ledger yet.** Phase 3 (the tasks that would actually move JSON data into `intelligence.sqlite` and retire the JSON source) has not started. Every file classified `MIGRATE_TO_INTELLIGENCE_LEDGER` below is still the sole, authoritative copy of its data — none are safe to remove.
- **2 Vite dev-server cache file(s) are git-tracked and not gitignored** (e.g. `investment_screener/frontend/.vite/deps/_metadata.json`). This is a build tool artifact that should never be committed — worth adding to `.gitignore` and removing from git tracking (a separate, low-risk cleanup task, not part of this discovery pass).
- **No JSON/JSONL files currently exist under `temp/`** at audit time — the concern (durable data accidentally living in scratch space) does not apply right now, though `temp/` is gitignored so this can change between runs.
- **8 file(s) remain `UNKNOWN_REQUIRES_REVIEW`** after heuristic classification — see 'Files Requiring Human Review' below.

## Files That Should Legitimately Exist

| File | Classification | Why it stays JSON |
|---|---|---|
| `plugin-sources.json` | ALLOWED_CONFIGURATION_JSON | Static configuration/manifest/schema/template — not durable observation data. |
| `symlinks.json` | ALLOWED_CONFIGURATION_JSON | Static configuration/manifest/schema/template — not durable observation data. |
| `schemas/market_data_response.schema.json` | ALLOWED_CONFIGURATION_JSON | Static configuration/manifest/schema/template — not durable observation data. |
| `schemas/prediction.schema.json` | ALLOWED_CONFIGURATION_JSON | Static configuration/manifest/schema/template — not durable observation data. |
| `investment_screener/package-lock.json` | ALLOWED_CONFIGURATION_JSON | Static configuration/manifest/schema/template — not durable observation data. |
| `investment_screener/package.json` | ALLOWED_CONFIGURATION_JSON | Static configuration/manifest/schema/template — not durable observation data. |
| `.claude-plugin/marketplace.json` | ALLOWED_CONFIGURATION_JSON | Static configuration/manifest/schema/template — not durable observation data. |
| `tradingview-cdp/package-lock.json` | ALLOWED_CONFIGURATION_JSON | Static configuration/manifest/schema/template — not durable observation data. |
| `tradingview-cdp/package.json` | ALLOWED_CONFIGURATION_JSON | Static configuration/manifest/schema/template — not durable observation data. |
| `investment_screener/frontend/tsconfig.node.json` | ALLOWED_CONFIGURATION_JSON | Static configuration/manifest/schema/template — not durable observation data. |
| `investment_screener/frontend/tsconfig.app.json` | ALLOWED_CONFIGURATION_JSON | Static configuration/manifest/schema/template — not durable observation data. |
| `investment_screener/frontend/package.json` | ALLOWED_CONFIGURATION_JSON | Static configuration/manifest/schema/template — not durable observation data. |
| `investment_screener/frontend/tsconfig.json` | ALLOWED_CONFIGURATION_JSON | Static configuration/manifest/schema/template — not durable observation data. |
| `investment_screener/backend/package.json` | ALLOWED_CONFIGURATION_JSON | Static configuration/manifest/schema/template — not durable observation data. |
| `investment_screener/backend/tsconfig.json` | ALLOWED_CONFIGURATION_JSON | Static configuration/manifest/schema/template — not durable observation data. |
| `investment_screener/backend/data/projections/PANW.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/SHAZ.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/NBIS.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/CRWV.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/BE.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/TSM.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/BTDR.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/APLD.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/PLTR.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/MU.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/SNDK.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/AMAT.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/IREN.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/RIOT.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/GOOG.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/ZS.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/CORZ.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/MP.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/STM.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/SKHY.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/CBRS.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/SPCX.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/tests/fixtures/edgar_companyfacts_aapl.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `investment_screener/backend/tests/fixtures/BROKEN_projection.test.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `docs/architecture/json-discovery-audit.json` | ALLOWED_GENERATED_CACHE_JSON | Regenerable cache — safe to exist as long as its generating source is known. |
| `docs/architecture/allowed-json-register.json` | ALLOWED_GENERATED_CACHE_JSON | Regenerable cache — safe to exist as long as its generating source is known. |
| `plugins/etf-analysis/plugin.json` | ALLOWED_CONFIGURATION_JSON | Static configuration/manifest/schema/template — not durable observation data. |
| `plugins/tradingview/plugin.json` | ALLOWED_CONFIGURATION_JSON | Static configuration/manifest/schema/template — not durable observation data. |
| `plugins/toolkit-manager/plugin.json` | ALLOWED_CONFIGURATION_JSON | Static configuration/manifest/schema/template — not durable observation data. |
| `plugins/stock-valuation/plugin.json` | ALLOWED_CONFIGURATION_JSON | Static configuration/manifest/schema/template — not durable observation data. |
| `plugins/portfolio-advisor/plugin.json` | ALLOWED_CONFIGURATION_JSON | Static configuration/manifest/schema/template — not durable observation data. |
| `plugins/portfolio-advisor/.claude-plugin/plugin.json` | ALLOWED_CONFIGURATION_JSON | Static configuration/manifest/schema/template — not durable observation data. |
| `plugins/portfolio-advisor/assets/templates/target_portfolio_template.json` | ALLOWED_CONFIGURATION_JSON | Static configuration/manifest/schema/template — not durable observation data. |
| `plugins/portfolio-advisor/assets/templates/portfolio_analysis_recommendations_template.json` | ALLOWED_CONFIGURATION_JSON | Static configuration/manifest/schema/template — not durable observation data. |
| `plugins/portfolio-advisor/assets/templates/ytd_performance_report_template.json` | ALLOWED_CONFIGURATION_JSON | Static configuration/manifest/schema/template — not durable observation data. |
| `plugins/portfolio-advisor/skills/13f-tracker/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/portfolio-advisor/skills/thesis-review/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/portfolio-advisor/skills/thesis-review/assets/templates/target_portfolio_template.json` | ALLOWED_CONFIGURATION_JSON | Static configuration/manifest/schema/template — not durable observation data. |
| `plugins/portfolio-advisor/skills/strategic-review/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/portfolio-advisor/skills/strategic-review/assets/templates/portfolio_analysis_recommendations_template.json` | ALLOWED_CONFIGURATION_JSON | Static configuration/manifest/schema/template — not durable observation data. |
| `plugins/portfolio-advisor/skills/portfolio-health/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/portfolio-advisor/skills/rebalance-portfolio/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/portfolio-advisor/skills/data-quality-audit/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/portfolio-advisor/skills/external-review/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/portfolio-advisor/skills/stock-intake/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/portfolio-advisor/skills/set-thesis-breakers/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/portfolio-advisor/skills/adversarial-review/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/portfolio-advisor/skills/calibrate-targets/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/portfolio-advisor/skills/norberts-gambit/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/portfolio-advisor/skills/daily-loop/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/portfolio-advisor/skills/daily-loop/evals/playbook-evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/portfolio-advisor/skills/screener-integrity-audit/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/portfolio-advisor/skills/weekly-review/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/portfolio-advisor/skills/pre-trade-analysis/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/portfolio-advisor/skills/news-sweep/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/portfolio-advisor/skills/update-portfolio-targets/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/portfolio-advisor/skills/update-portfolio-targets/assets/templates/target_portfolio_template.json` | ALLOWED_CONFIGURATION_JSON | Static configuration/manifest/schema/template — not durable observation data. |
| `plugins/portfolio-advisor/skills/portfolio-coverage-audit/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/portfolio-advisor/skills/ytd-return/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/portfolio-advisor/skills/ytd-return/assets/templates/ytd_performance_report_template.json` | ALLOWED_CONFIGURATION_JSON | Static configuration/manifest/schema/template — not durable observation data. |
| `plugins/portfolio-advisor/skills/13f-analyze/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/portfolio-advisor/agents/evals/thesis-review-agent.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/portfolio-advisor/agents/evals/risk-officer-agent.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/portfolio-advisor/agents/evals/portfolio-advisor-orchestrator.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/portfolio-advisor/agents/evals/red-team-agent.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/stock-valuation/.claude-plugin/plugin.json` | ALLOWED_CONFIGURATION_JSON | Static configuration/manifest/schema/template — not durable observation data. |
| `plugins/stock-valuation/assets/templates/projection_template.json` | ALLOWED_CONFIGURATION_JSON | Static configuration/manifest/schema/template — not durable observation data. |
| `plugins/stock-valuation/skills/valuation-math-validation/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/stock-valuation/skills/forward-valuation-challenge/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/stock-valuation/skills/update-stock-analysis/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/stock-valuation/skills/update-stock-analysis/assets/templates/projection_template.json` | ALLOWED_CONFIGURATION_JSON | Static configuration/manifest/schema/template — not durable observation data. |
| `plugins/stock-valuation/skills/stock-research/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/stock-valuation/tests/fixtures/forward-valuation/BE_inputs.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/stock-valuation/tests/fixtures/forward-valuation/MU_inputs.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/toolkit-manager/.claude-plugin/plugin.json` | ALLOWED_CONFIGURATION_JSON | Static configuration/manifest/schema/template — not durable observation data. |
| `plugins/toolkit-manager/skills/toolkit-onboarding/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/toolkit-manager/skills/sqlite-admin/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/toolkit-manager/skills/run-screener/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/tradingview/.claude-plugin/plugin.json` | ALLOWED_CONFIGURATION_JSON | Static configuration/manifest/schema/template — not durable observation data. |
| `plugins/tradingview/skills/tv-draw/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/tradingview/skills/tv-thesis-overlay/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/tradingview/skills/tv-get-orders/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/tradingview/skills/tv-author-pine-script/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/tradingview/skills/tv-chart-snapshot/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/tradingview/skills/tv-alert-sync/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/tradingview/skills/tv-save-indicator/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/tradingview/skills/tv-place-order/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/tradingview/skills/tv-add-indicator/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/tradingview/skills/tv-alert-list/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/tradingview/skills/tv-alert-reconcile/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/tradingview/skills/tv-setup/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/tradingview/skills/tv-change-symbol/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/tradingview/skills/tv-pine-inject/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/tradingview/skills/tv-change-type/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/tradingview/skills/tv-price-refresh/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/tradingview/skills/tv-technical-analysis-expert/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/tradingview/skills/tv-ta-daily-sweep/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/tradingview/skills/tv-ta-snapshot/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/tradingview/skills/tv-modify-order/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/tradingview/skills/tv-manage-watchlists/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/tradingview/skills/tv-onboarding/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/tradingview/skills/tv-chart-setup/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/tradingview/skills/tv-manage-indicators/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/tradingview/skills/tv-ta-red-team/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/tradingview/skills/tv-cancel-order/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/tradingview/skills/tv-portfolio-sync/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/tradingview/agents/evals/ta-guide.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/questrade/.claude-plugin/plugin.json` | ALLOWED_CONFIGURATION_JSON | Static configuration/manifest/schema/template — not durable observation data. |
| `plugins/questrade/skills/questrade-activities/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/questrade/skills/questrade-get-positions/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/questrade/skills/questrade-get-balances/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/questrade/skills/questrade-sync-portfolio/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/questrade/skills/questrade-order-draft/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/questrade/skills/questrade-refresh-prices/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/questrade/skills/questrade-setup/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/etf-analysis/.claude-plugin/plugin.json` | ALLOWED_CONFIGURATION_JSON | Static configuration/manifest/schema/template — not durable observation data. |
| `plugins/etf-analysis/assets/templates/etf_analysis_template.json` | ALLOWED_CONFIGURATION_JSON | Static configuration/manifest/schema/template — not durable observation data. |
| `plugins/etf-analysis/skills/etf-analysis/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/etf-analysis/skills/etf-analysis/assets/templates/etf_analysis_template.json` | ALLOWED_CONFIGURATION_JSON | Static configuration/manifest/schema/template — not durable observation data. |

## Files That Likely Should Not Exist Long-Term

| File | Reason | Required next action |
|---|---|---|
| `investment_screener/frontend/.vite/deps/_metadata.json` | Build-tool cache artifact, checked into git by mistake. | Add to .gitignore, git rm --cached (separate low-risk task) |
| `investment_screener/frontend/.vite/deps/package.json` | Build-tool cache artifact, checked into git by mistake. | Add to .gitignore, git rm --cached (separate low-risk task) |

## Files Requiring Human Review

| File | Reason | Suggested next action |
|---|---|---|
| `plugin-retention.json` | No known heuristic match | INVESTIGATE |
| `.mcp.json` | No known heuristic match | INVESTIGATE |
| `.agent/learning/traces/cycle_manifests.jsonl` | No known heuristic match | INVESTIGATE |
| `plugins/questrade/.mcp.json` | No known heuristic match | INVESTIGATE |
| `plugins/portfolio-advisor/references/standing-decisions.json` | No known heuristic match | INVESTIGATE |
| `plugins/stock-valuation/references/forward-valuation-reviews/2026-10-06/BE/valuation.json` | No known heuristic match | INVESTIGATE |
| `plugins/stock-valuation/references/forward-valuation-reviews/2026-10-06/MU/valuation.json` | No known heuristic match | INVESTIGATE |
| `plugins/tradingview/audit/orders-2026-10-09.jsonl` | No known heuristic match | INVESTIGATE |

## Temp Folder Analysis

No `.json`/`.jsonl` files currently exist under `temp/` (which is gitignored scratch space per `.gitignore`). Re-run this audit periodically if `temp/` is suspected of accumulating durable data over time — nothing to report as of 2026-10-10T01:49:44Z.

## Per-File Inventory

### plugin-retention.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### .mcp.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugin-sources.json

**Classification:** ALLOWED_CONFIGURATION_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### symlinks.json

**Classification:** ALLOWED_CONFIGURATION_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- run_tests.py:18
- plugins/portfolio-advisor/tests/test_recommendation_coherence_contract.py:4
- plugins/portfolio-advisor/tests/test_recommendation_coherence_contract.py:27
- plugins/stock-valuation/tests/test_ai_forward_skill_contract.py:33
- plugins/questrade/scripts/scaffold_skill.py:36

### schemas/market_data_response.schema.json

**Classification:** ALLOWED_CONFIGURATION_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_market_data_schema.py:14

### schemas/prediction.schema.json

**Classification:** ALLOWED_CONFIGURATION_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/py_services/prediction_ledger.py:67
- investment_screener/backend/py_services/prediction_ledger.py:121
- investment_screener/backend/py_services/prediction_ledger.py:261
- investment_screener/backend/py_services/backtest_harness.py:592
- investment_screener/backend/py_services/migrate_predictions_to_ledger.py:82

### investment_screener/package-lock.json

**Classification:** ALLOWED_CONFIGURATION_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/package.json

**Classification:** ALLOWED_CONFIGURATION_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- run_tests.py:17
- run_investment_toolkit.py:16
- investment_screener/backend/py_services/audit_json_usage.py:432

### .claude-plugin/marketplace.json

**Classification:** ALLOWED_CONFIGURATION_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:128

### tradingview-cdp/package-lock.json

**Classification:** ALLOWED_CONFIGURATION_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### tradingview-cdp/package.json

**Classification:** ALLOWED_CONFIGURATION_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- run_tests.py:17
- run_investment_toolkit.py:16
- investment_screener/backend/py_services/audit_json_usage.py:432

### .agent/learning/traces/cycle_manifests.jsonl

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/frontend/tsconfig.node.json

**Classification:** ALLOWED_CONFIGURATION_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/frontend/tsconfig.app.json

**Classification:** ALLOWED_CONFIGURATION_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/py_services/audit_json_usage.py:433

### investment_screener/frontend/package.json

**Classification:** ALLOWED_CONFIGURATION_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- run_tests.py:17
- run_investment_toolkit.py:16
- investment_screener/backend/py_services/audit_json_usage.py:432

### investment_screener/frontend/tsconfig.json

**Classification:** ALLOWED_CONFIGURATION_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/package.json

**Classification:** ALLOWED_CONFIGURATION_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- run_tests.py:17
- run_investment_toolkit.py:16
- investment_screener/backend/py_services/audit_json_usage.py:432

### investment_screener/backend/tsconfig.json

**Classification:** ALLOWED_CONFIGURATION_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/thesis_breaker_state.json

**Classification:** RETIRED_PORTFOLIO_DATA

**Known producers:**
- investment_screener/backend/tests/py_services/test_canonical_recommendation_consumers.py:247

**Known consumers:**
- investment_screener/backend/py_services/audit_json_usage.py:104
- investment_screener/backend/tests/py_services/test_thesis_breakers.py:390
- investment_screener/backend/tests/py_services/test_thesis_breakers.py:393
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:361
- investment_screener/backend/tests/py_services/test_order_risk_gates_checks_breaker_veto.py:135
- plugins/toolkit-manager/scripts/audit_sqlite_usage.py:78

### investment_screener/backend/data/projections/PANW.json

**Classification:** ALLOWED_MODEL_ARTIFACT_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/projections/SHAZ.json

**Classification:** ALLOWED_MODEL_ARTIFACT_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/projections/NBIS.json

**Classification:** ALLOWED_MODEL_ARTIFACT_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/projections/CRWV.json

**Classification:** ALLOWED_MODEL_ARTIFACT_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/projections/BE.json

**Classification:** ALLOWED_MODEL_ARTIFACT_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/projections/TSM.json

**Classification:** ALLOWED_MODEL_ARTIFACT_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/projections/BTDR.json

**Classification:** ALLOWED_MODEL_ARTIFACT_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/projections/APLD.json

**Classification:** ALLOWED_MODEL_ARTIFACT_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/projections/PLTR.json

**Classification:** ALLOWED_MODEL_ARTIFACT_JSON

**Known producers:**
- investment_screener/backend/tests/py_services/test_migrate_research_report_pointers.py:16

**Known consumers:**
- investment_screener/backend/tests/py_services/test_migrate_research_report_pointers.py:25
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:107
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:345
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:354

### investment_screener/backend/data/projections/MU.json

**Classification:** ALLOWED_MODEL_ARTIFACT_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/projections/SNDK.json

**Classification:** ALLOWED_MODEL_ARTIFACT_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/projections/AMAT.json

**Classification:** ALLOWED_MODEL_ARTIFACT_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/projections/IREN.json

**Classification:** ALLOWED_MODEL_ARTIFACT_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/projections/RIOT.json

**Classification:** ALLOWED_MODEL_ARTIFACT_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/projections/GOOG.json

**Classification:** ALLOWED_MODEL_ARTIFACT_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/projections/ZS.json

**Classification:** ALLOWED_MODEL_ARTIFACT_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/projections/CORZ.json

**Classification:** ALLOWED_MODEL_ARTIFACT_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/projections/MP.json

**Classification:** ALLOWED_MODEL_ARTIFACT_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/projections/STM.json

**Classification:** ALLOWED_MODEL_ARTIFACT_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/projections/SKHY.json

**Classification:** ALLOWED_MODEL_ARTIFACT_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/projections/CBRS.json

**Classification:** ALLOWED_MODEL_ARTIFACT_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/projections/SPCX.json

**Classification:** ALLOWED_MODEL_ARTIFACT_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/13f/000204572425000002.json

**Classification:** OUT_OF_SCOPE_FOR_THIS_PHASE

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/13f/000204572425000008.json

**Classification:** OUT_OF_SCOPE_FOR_THIS_PHASE

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/13f/0002045724_index.json

**Classification:** OUT_OF_SCOPE_FOR_THIS_PHASE

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:153
- investment_screener/backend/src/routes/thirteenf.ts:30

### investment_screener/backend/data/13f/000093583626000418.json

**Classification:** OUT_OF_SCOPE_FOR_THIS_PHASE

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/13f/000204572426000008.json

**Classification:** OUT_OF_SCOPE_FOR_THIS_PHASE

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/13f/000204572425000006.json

**Classification:** OUT_OF_SCOPE_FOR_THIS_PHASE

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/13f/000204572426000002.json

**Classification:** OUT_OF_SCOPE_FOR_THIS_PHASE

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/13f/0002045724_diff.json

**Classification:** OUT_OF_SCOPE_FOR_THIS_PHASE

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/src/routes/thirteenf.ts:31

### investment_screener/backend/data/etf_analysis/FOTO.json

**Classification:** OUT_OF_SCOPE_FOR_THIS_PHASE

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:152

### investment_screener/backend/data/etf_analysis/ETHA.json

**Classification:** OUT_OF_SCOPE_FOR_THIS_PHASE

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/etf_analysis/WQTM.json

**Classification:** OUT_OF_SCOPE_FOR_THIS_PHASE

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/etf_analysis/DXYZ.json

**Classification:** OUT_OF_SCOPE_FOR_THIS_PHASE

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/etf_analysis/KOID.json

**Classification:** OUT_OF_SCOPE_FOR_THIS_PHASE

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/etf_analysis/HUMN.json

**Classification:** OUT_OF_SCOPE_FOR_THIS_PHASE

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/etf_analysis/DRAM.json

**Classification:** OUT_OF_SCOPE_FOR_THIS_PHASE

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/etf_analysis/IBIT.json

**Classification:** OUT_OF_SCOPE_FOR_THIS_PHASE

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/tests/fixtures/edgar_companyfacts_aapl.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_edgar_facts.py:15

### investment_screener/backend/tests/fixtures/BROKEN_projection.test.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/frontend/.vite/deps/_metadata.json

**Classification:** ARCHIVE_LEGACY_READ_ONLY

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/py_services/audit_json_usage.py:516
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:142

### investment_screener/frontend/.vite/deps/package.json

**Classification:** ARCHIVE_LEGACY_READ_ONLY

**Known producers:**
- (none detected)

**Known consumers:**
- run_tests.py:17
- run_investment_toolkit.py:16
- investment_screener/backend/py_services/audit_json_usage.py:432

### docs/architecture/json-discovery-audit.json

**Classification:** ALLOWED_GENERATED_CACHE_JSON

**Known producers:**
- investment_screener/backend/py_services/audit_json_usage.py:659
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:66
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:83

**Known consumers:**
- investment_screener/backend/py_services/audit_json_usage.py:387
- investment_screener/backend/py_services/build_consumer_inventory.py:5
- investment_screener/backend/py_services/build_consumer_inventory.py:16
- investment_screener/backend/py_services/build_consumer_inventory.py:23
- investment_screener/backend/py_services/build_consumer_inventory.py:99
- investment_screener/backend/py_services/build_consumer_inventory.py:153
- investment_screener/backend/py_services/build_consumer_inventory.py:210
- investment_screener/backend/tests/py_services/test_build_consumer_inventory.py:116
- investment_screener/backend/tests/py_services/test_build_consumer_inventory.py:117
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:33
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:39
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:63
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:82
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:94
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:115
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:161
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:206
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:208
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:224
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:243
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:245
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:260
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:262
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:278
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:316
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:329
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:334
- plugins/toolkit-manager/scripts/audit_sqlite_usage.py:553

### docs/architecture/allowed-json-register.json

**Classification:** ALLOWED_GENERATED_CACHE_JSON

**Known producers:**
- investment_screener/backend/py_services/audit_json_usage.py:676

**Known consumers:**
- investment_screener/backend/py_services/audit_json_usage.py:388
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:318
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:351
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:373
- plugins/toolkit-manager/scripts/audit_sqlite_usage.py:554

### plugins/etf-analysis/plugin.json

**Classification:** ALLOWED_CONFIGURATION_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/py_services/audit_json_usage.py:422
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:126
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:127

### plugins/questrade/.mcp.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/tradingview/plugin.json

**Classification:** ALLOWED_CONFIGURATION_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/py_services/audit_json_usage.py:422
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:126
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:127

### plugins/toolkit-manager/plugin.json

**Classification:** ALLOWED_CONFIGURATION_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/py_services/audit_json_usage.py:422
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:126
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:127

### plugins/stock-valuation/plugin.json

**Classification:** ALLOWED_CONFIGURATION_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/py_services/audit_json_usage.py:422
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:126
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:127

### plugins/portfolio-advisor/plugin.json

**Classification:** ALLOWED_CONFIGURATION_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/py_services/audit_json_usage.py:422
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:126
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:127

### plugins/portfolio-advisor/references/standing-decisions.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/py_services/brief_recommendations.py:55

### plugins/portfolio-advisor/.claude-plugin/plugin.json

**Classification:** ALLOWED_CONFIGURATION_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/py_services/audit_json_usage.py:422
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:126
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:127

### plugins/portfolio-advisor/assets/templates/target_portfolio_template.json

**Classification:** ALLOWED_CONFIGURATION_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:137

### plugins/portfolio-advisor/assets/templates/portfolio_analysis_recommendations_template.json

**Classification:** ALLOWED_CONFIGURATION_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/portfolio-advisor/assets/templates/ytd_performance_report_template.json

**Classification:** ALLOWED_CONFIGURATION_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/portfolio-advisor/skills/13f-tracker/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:132
- plugins/stock-valuation/tests/test_ai_forward_skill_contract.py:35

### plugins/portfolio-advisor/skills/thesis-review/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:132
- plugins/stock-valuation/tests/test_ai_forward_skill_contract.py:35

### plugins/portfolio-advisor/skills/thesis-review/assets/templates/target_portfolio_template.json

**Classification:** ALLOWED_CONFIGURATION_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:137

### plugins/portfolio-advisor/skills/strategic-review/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:132
- plugins/stock-valuation/tests/test_ai_forward_skill_contract.py:35

### plugins/portfolio-advisor/skills/strategic-review/assets/templates/portfolio_analysis_recommendations_template.json

**Classification:** ALLOWED_CONFIGURATION_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/portfolio-advisor/skills/portfolio-health/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:132
- plugins/stock-valuation/tests/test_ai_forward_skill_contract.py:35

### plugins/portfolio-advisor/skills/rebalance-portfolio/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:132
- plugins/stock-valuation/tests/test_ai_forward_skill_contract.py:35

### plugins/portfolio-advisor/skills/data-quality-audit/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:132
- plugins/stock-valuation/tests/test_ai_forward_skill_contract.py:35

### plugins/portfolio-advisor/skills/external-review/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:132
- plugins/stock-valuation/tests/test_ai_forward_skill_contract.py:35

### plugins/portfolio-advisor/skills/stock-intake/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:132
- plugins/stock-valuation/tests/test_ai_forward_skill_contract.py:35

### plugins/portfolio-advisor/skills/set-thesis-breakers/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:132
- plugins/stock-valuation/tests/test_ai_forward_skill_contract.py:35

### plugins/portfolio-advisor/skills/adversarial-review/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:132
- plugins/stock-valuation/tests/test_ai_forward_skill_contract.py:35

### plugins/portfolio-advisor/skills/calibrate-targets/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:132
- plugins/stock-valuation/tests/test_ai_forward_skill_contract.py:35

### plugins/portfolio-advisor/skills/norberts-gambit/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:132
- plugins/stock-valuation/tests/test_ai_forward_skill_contract.py:35

### plugins/portfolio-advisor/skills/daily-loop/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:132
- plugins/stock-valuation/tests/test_ai_forward_skill_contract.py:35

### plugins/portfolio-advisor/skills/daily-loop/evals/playbook-evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/portfolio-advisor/skills/screener-integrity-audit/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:132
- plugins/stock-valuation/tests/test_ai_forward_skill_contract.py:35

### plugins/portfolio-advisor/skills/weekly-review/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:132
- plugins/stock-valuation/tests/test_ai_forward_skill_contract.py:35

### plugins/portfolio-advisor/skills/pre-trade-analysis/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:132
- plugins/stock-valuation/tests/test_ai_forward_skill_contract.py:35

### plugins/portfolio-advisor/skills/news-sweep/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:132
- plugins/stock-valuation/tests/test_ai_forward_skill_contract.py:35

### plugins/portfolio-advisor/skills/update-portfolio-targets/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:132
- plugins/stock-valuation/tests/test_ai_forward_skill_contract.py:35

### plugins/portfolio-advisor/skills/update-portfolio-targets/assets/templates/target_portfolio_template.json

**Classification:** ALLOWED_CONFIGURATION_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:137

### plugins/portfolio-advisor/skills/portfolio-coverage-audit/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:132
- plugins/stock-valuation/tests/test_ai_forward_skill_contract.py:35

### plugins/portfolio-advisor/skills/ytd-return/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:132
- plugins/stock-valuation/tests/test_ai_forward_skill_contract.py:35

### plugins/portfolio-advisor/skills/ytd-return/assets/templates/ytd_performance_report_template.json

**Classification:** ALLOWED_CONFIGURATION_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/portfolio-advisor/skills/13f-analyze/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:132
- plugins/stock-valuation/tests/test_ai_forward_skill_contract.py:35

### plugins/portfolio-advisor/agents/evals/thesis-review-agent.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/portfolio-advisor/agents/evals/risk-officer-agent.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/portfolio-advisor/agents/evals/portfolio-advisor-orchestrator.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/portfolio-advisor/agents/evals/red-team-agent.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/stock-valuation/.claude-plugin/plugin.json

**Classification:** ALLOWED_CONFIGURATION_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/py_services/audit_json_usage.py:422
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:126
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:127

### plugins/stock-valuation/assets/templates/projection_template.json

**Classification:** ALLOWED_CONFIGURATION_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- plugins/stock-valuation/scripts/validate_projection.py:131
- plugins/stock-valuation/skills/update-stock-analysis/scripts/validate_projection.py:131

### plugins/stock-valuation/skills/valuation-math-validation/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:132
- plugins/stock-valuation/tests/test_ai_forward_skill_contract.py:35

### plugins/stock-valuation/skills/forward-valuation-challenge/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:132
- plugins/stock-valuation/tests/test_ai_forward_skill_contract.py:35

### plugins/stock-valuation/skills/update-stock-analysis/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:132
- plugins/stock-valuation/tests/test_ai_forward_skill_contract.py:35

### plugins/stock-valuation/skills/update-stock-analysis/assets/templates/projection_template.json

**Classification:** ALLOWED_CONFIGURATION_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- plugins/stock-valuation/scripts/validate_projection.py:131
- plugins/stock-valuation/skills/update-stock-analysis/scripts/validate_projection.py:131

### plugins/stock-valuation/skills/stock-research/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:132
- plugins/stock-valuation/tests/test_ai_forward_skill_contract.py:35

### plugins/stock-valuation/tests/fixtures/forward-valuation/BE_inputs.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- plugins/stock-valuation/tests/test_forward_recalculation.py:52
- plugins/stock-valuation/tests/test_forward_recalculation.py:53

### plugins/stock-valuation/tests/fixtures/forward-valuation/MU_inputs.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/stock-valuation/references/forward-valuation-reviews/2026-10-06/BE/valuation.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- plugins/stock-valuation/tests/test_forward_recalculation.py:22
- plugins/stock-valuation/tests/test_forward_recalculation.py:26
- plugins/stock-valuation/tests/test_forward_recalculation.py:64

### plugins/stock-valuation/references/forward-valuation-reviews/2026-10-06/MU/valuation.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- plugins/stock-valuation/tests/test_forward_recalculation.py:22
- plugins/stock-valuation/tests/test_forward_recalculation.py:26
- plugins/stock-valuation/tests/test_forward_recalculation.py:64

### plugins/toolkit-manager/.claude-plugin/plugin.json

**Classification:** ALLOWED_CONFIGURATION_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/py_services/audit_json_usage.py:422
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:126
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:127

### plugins/toolkit-manager/skills/toolkit-onboarding/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:132
- plugins/stock-valuation/tests/test_ai_forward_skill_contract.py:35

### plugins/toolkit-manager/skills/sqlite-admin/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:132
- plugins/stock-valuation/tests/test_ai_forward_skill_contract.py:35

### plugins/toolkit-manager/skills/run-screener/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:132
- plugins/stock-valuation/tests/test_ai_forward_skill_contract.py:35

### plugins/tradingview/audit/orders-2026-10-09.jsonl

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/tradingview/.claude-plugin/plugin.json

**Classification:** ALLOWED_CONFIGURATION_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/py_services/audit_json_usage.py:422
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:126
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:127

### plugins/tradingview/skills/tv-draw/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:132
- plugins/stock-valuation/tests/test_ai_forward_skill_contract.py:35

### plugins/tradingview/skills/tv-thesis-overlay/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:132
- plugins/stock-valuation/tests/test_ai_forward_skill_contract.py:35

### plugins/tradingview/skills/tv-get-orders/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:132
- plugins/stock-valuation/tests/test_ai_forward_skill_contract.py:35

### plugins/tradingview/skills/tv-author-pine-script/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:132
- plugins/stock-valuation/tests/test_ai_forward_skill_contract.py:35

### plugins/tradingview/skills/tv-chart-snapshot/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:132
- plugins/stock-valuation/tests/test_ai_forward_skill_contract.py:35

### plugins/tradingview/skills/tv-alert-sync/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:132
- plugins/stock-valuation/tests/test_ai_forward_skill_contract.py:35

### plugins/tradingview/skills/tv-save-indicator/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:132
- plugins/stock-valuation/tests/test_ai_forward_skill_contract.py:35

### plugins/tradingview/skills/tv-place-order/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:132
- plugins/stock-valuation/tests/test_ai_forward_skill_contract.py:35

### plugins/tradingview/skills/tv-add-indicator/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:132
- plugins/stock-valuation/tests/test_ai_forward_skill_contract.py:35

### plugins/tradingview/skills/tv-alert-list/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:132
- plugins/stock-valuation/tests/test_ai_forward_skill_contract.py:35

### plugins/tradingview/skills/tv-alert-reconcile/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:132
- plugins/stock-valuation/tests/test_ai_forward_skill_contract.py:35

### plugins/tradingview/skills/tv-setup/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:132
- plugins/stock-valuation/tests/test_ai_forward_skill_contract.py:35

### plugins/tradingview/skills/tv-change-symbol/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:132
- plugins/stock-valuation/tests/test_ai_forward_skill_contract.py:35

### plugins/tradingview/skills/tv-pine-inject/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:132
- plugins/stock-valuation/tests/test_ai_forward_skill_contract.py:35

### plugins/tradingview/skills/tv-change-type/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:132
- plugins/stock-valuation/tests/test_ai_forward_skill_contract.py:35

### plugins/tradingview/skills/tv-price-refresh/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:132
- plugins/stock-valuation/tests/test_ai_forward_skill_contract.py:35

### plugins/tradingview/skills/tv-technical-analysis-expert/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:132
- plugins/stock-valuation/tests/test_ai_forward_skill_contract.py:35

### plugins/tradingview/skills/tv-ta-daily-sweep/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:132
- plugins/stock-valuation/tests/test_ai_forward_skill_contract.py:35

### plugins/tradingview/skills/tv-ta-snapshot/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:132
- plugins/stock-valuation/tests/test_ai_forward_skill_contract.py:35

### plugins/tradingview/skills/tv-modify-order/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:132
- plugins/stock-valuation/tests/test_ai_forward_skill_contract.py:35

### plugins/tradingview/skills/tv-manage-watchlists/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:132
- plugins/stock-valuation/tests/test_ai_forward_skill_contract.py:35

### plugins/tradingview/skills/tv-onboarding/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:132
- plugins/stock-valuation/tests/test_ai_forward_skill_contract.py:35

### plugins/tradingview/skills/tv-chart-setup/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:132
- plugins/stock-valuation/tests/test_ai_forward_skill_contract.py:35

### plugins/tradingview/skills/tv-manage-indicators/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:132
- plugins/stock-valuation/tests/test_ai_forward_skill_contract.py:35

### plugins/tradingview/skills/tv-ta-red-team/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:132
- plugins/stock-valuation/tests/test_ai_forward_skill_contract.py:35

### plugins/tradingview/skills/tv-cancel-order/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:132
- plugins/stock-valuation/tests/test_ai_forward_skill_contract.py:35

### plugins/tradingview/skills/tv-portfolio-sync/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:132
- plugins/stock-valuation/tests/test_ai_forward_skill_contract.py:35

### plugins/tradingview/agents/evals/ta-guide.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:133

### plugins/questrade/.claude-plugin/plugin.json

**Classification:** ALLOWED_CONFIGURATION_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/py_services/audit_json_usage.py:422
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:126
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:127

### plugins/questrade/skills/questrade-activities/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:132
- plugins/stock-valuation/tests/test_ai_forward_skill_contract.py:35

### plugins/questrade/skills/questrade-get-positions/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:132
- plugins/stock-valuation/tests/test_ai_forward_skill_contract.py:35

### plugins/questrade/skills/questrade-get-balances/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:132
- plugins/stock-valuation/tests/test_ai_forward_skill_contract.py:35

### plugins/questrade/skills/questrade-sync-portfolio/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:132
- plugins/stock-valuation/tests/test_ai_forward_skill_contract.py:35

### plugins/questrade/skills/questrade-order-draft/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:132
- plugins/stock-valuation/tests/test_ai_forward_skill_contract.py:35

### plugins/questrade/skills/questrade-refresh-prices/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:132
- plugins/stock-valuation/tests/test_ai_forward_skill_contract.py:35

### plugins/questrade/skills/questrade-setup/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:132
- plugins/stock-valuation/tests/test_ai_forward_skill_contract.py:35

### plugins/etf-analysis/.claude-plugin/plugin.json

**Classification:** ALLOWED_CONFIGURATION_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/py_services/audit_json_usage.py:422
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:126
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:127

### plugins/etf-analysis/assets/templates/etf_analysis_template.json

**Classification:** ALLOWED_CONFIGURATION_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/etf-analysis/skills/etf-analysis/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:132
- plugins/stock-valuation/tests/test_ai_forward_skill_contract.py:35

### plugins/etf-analysis/skills/etf-analysis/assets/templates/etf_analysis_template.json

**Classification:** ALLOWED_CONFIGURATION_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

