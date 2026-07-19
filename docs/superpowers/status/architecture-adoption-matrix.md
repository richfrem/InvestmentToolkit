# Architecture Adoption Matrix

This document tracks the migration status of every consumer in the ecosystem, indicating which parts of the system use the new SQLite Intelligence Ledger read-model and shared data layer, which remain on legacy JSON, and what changes are required.

## Adoption Summary

| Status | Count | Description |
|---|---:|---|
| USES_LEDGER_REPOSITORY | 17 | Actively queries the new SQLite ledger repository layer. |
| USES_GENERATED_VIEW | 2 | Actively queries the generated views (like *.summary.md). |
| REMAINS_JSON_BY_DESIGN | 149 | Legitimate flat-file configuration/portfolio target JSON (including resolved unknowns). |
| MIGRATION_REQUIRED | 1 | Legitimate migration candidate that must be rewired. |
| OUT_OF_SCOPE | 1 | 13F and other domain data not in-scope for this phase. |
| UNKNOWN_REQUIRES_REVIEW | 0 | Requires review to determine correct taxonomy status. |
| **Total Consumers** | **170** | |

## Consumer Breakdown by Type

| Consumer Type | Count |
|---|---:|
| backend route | 11 |
| frontend component | 2 |
| plugin script | 86 |
| report generator | 13 |
| skill | 50 |
| sub-agent | 6 |
| workflow | 2 |

## Complete Architecture Adoption Matrix

| Consumer | Type | Current Source | Target Source | Status | Migration Required | Test Coverage | Risk |
|---|---|---|---|---|---|---|---|
| `investment_screener/backend/py_services/evolution_events.py` | plugin script | events.jsonl, ta-sweep-results.json | intelligence.sqlite (ledger) | MIGRATION_REQUIRED | Yes | No | Medium |
| `investment_screener/backend/src/routes/thirteenf.ts` | backend route | 0002045724_diff.json, 0002045724_index.json | n/a | OUT_OF_SCOPE | No | n/a | Low |
| `investment_screener/backend/src/routes/screener.ts` | backend route | target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `investment_screener/backend/src/routes/stock.ts` | backend route | target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `investment_screener/backend/src/routes/theses.ts` | backend route | target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `investment_screener/backend/src/services/BrokerSyncService.ts` | backend route | target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `investment_screener/backend/src/services/ThesisService.ts` | backend route | account_policy.json | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `investment_screener/backend/src/services/WatchlistService.ts` | backend route | watchlist.json | n/a | REMAINS_JSON_BY_DESIGN | No | Yes | Low |
| `investment_screener/backend/src/utils/paths.ts` | backend route | target-portfolio.json, watchlist.json | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `investment_screener/backend/src/utils/zod-schemas.ts` | backend route | account_policy.json, target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | Yes | Low |
| `investment_screener/backend/py_services/apply_catalyst.py` | plugin script | target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `investment_screener/backend/py_services/audit_json_usage.py` | plugin script | allowed-json-register.json, json-discovery-audit.json, package.json etc. | n/a (false positive) | REMAINS_JSON_BY_DESIGN | No | Yes | Low |
| `investment_screener/backend/py_services/backtest_harness.py` | plugin script | predictions.jsonl, target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `investment_screener/backend/py_services/earnings_expectations.py` | plugin script | predictions.jsonl, target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `investment_screener/backend/py_services/generate_grok_prompt.py` | plugin script | target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `investment_screener/backend/py_services/generate_portfolio_blueprint.py` | plugin script | target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `investment_screener/backend/py_services/harvest_predictions.py` | plugin script | predictions.jsonl, target-portfolio.json, thesis_breaker_state.json | n/a | REMAINS_JSON_BY_DESIGN | No | Yes | Low |
| `investment_screener/backend/py_services/lock_and_normalize_targets.py` | plugin script | target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | Yes | Low |
| `investment_screener/backend/py_services/market_regime.py` | plugin script | target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | Yes | Low |
| `investment_screener/backend/py_services/migrations/remove_drift_threshold_fields.py` | plugin script | account_policy.json, target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | Yes | Low |
| `investment_screener/backend/py_services/order_risk_gates.py` | plugin script | account_policy.json, target-portfolio.json, thesis_breaker_state.json | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `investment_screener/backend/py_services/overnight_gaps.py` | plugin script | watchlist.json | n/a | REMAINS_JSON_BY_DESIGN | No | Yes | Low |
| `investment_screener/backend/py_services/pine_script_manager.py` | plugin script | registry.json | n/a | REMAINS_JSON_BY_DESIGN | No | Yes | Low |
| `investment_screener/backend/py_services/prediction_ledger.py` | plugin script | prediction.schema.json, predictions.jsonl | n/a | REMAINS_JSON_BY_DESIGN | No | Yes | Low |
| `investment_screener/backend/py_services/rebalancer.py` | plugin script | account_policy.json, target-portfolio.json, thesis_breaker_state.json | n/a | REMAINS_JSON_BY_DESIGN | No | Yes | Low |
| `investment_screener/backend/py_services/risk_engine.py` | plugin script | target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | Yes | Low |
| `investment_screener/backend/py_services/risk_officer.py` | plugin script | thesis_breaker_state.json | n/a | REMAINS_JSON_BY_DESIGN | No | Yes | Low |
| `investment_screener/backend/py_services/system_health.py` | plugin script | target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `investment_screener/backend/py_services/thesis_breakers.py` | plugin script | target-portfolio.json, thesis_breaker_state.json | n/a | REMAINS_JSON_BY_DESIGN | No | Yes | Low |
| `investment_screener/backend/py_services/update_thesis.py` | plugin script | target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `investment_screener/backend/py_services/verify_thesis_sync.py` | plugin script | target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | Yes | Low |
| `investment_screener/backend/tests/py_services/test_alert_metadata_round_trips_jsonl.py` | plugin script | events.jsonl | n/a | REMAINS_JSON_BY_DESIGN | No | Yes | Low |
| `investment_screener/backend/tests/py_services/test_audit_json_usage.py` | plugin script | allowed-json-register.json, json-discovery-audit.json, package.json etc. | n/a (false positive) | REMAINS_JSON_BY_DESIGN | No | Yes | Low |
| `investment_screener/backend/tests/py_services/test_backtest_extract_historical_targets.py` | plugin script | target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `investment_screener/backend/tests/py_services/test_backtest_prediction_ledger_correlation.py` | plugin script | predictions.jsonl | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `investment_screener/backend/tests/py_services/test_comps_valuation.py` | plugin script | AMD.json, AVGO.json, NVDA.json | n/a | REMAINS_JSON_BY_DESIGN | No | Yes | Low |
| `investment_screener/backend/tests/py_services/test_earnings_expectation_claim_round_trips_ledger.py` | plugin script | predictions.jsonl | n/a | REMAINS_JSON_BY_DESIGN | No | Yes | Low |
| `investment_screener/backend/tests/py_services/test_earnings_expectation_claim_schema_round_trips_jsonl.py` | plugin script | predictions.jsonl | n/a | REMAINS_JSON_BY_DESIGN | No | Yes | Low |
| `investment_screener/backend/tests/py_services/test_edgar_facts.py` | plugin script | edgar_companyfacts_aapl.json | n/a | REMAINS_JSON_BY_DESIGN | No | Yes | Low |
| `investment_screener/backend/tests/py_services/test_evolution_events_schema_round_trips_jsonl.py` | plugin script | events.jsonl | n/a | REMAINS_JSON_BY_DESIGN | No | Yes | Low |
| `investment_screener/backend/tests/py_services/test_evolution_integration_with_e3_prediction_ledger.py` | plugin script | predictions.jsonl | n/a | REMAINS_JSON_BY_DESIGN | No | Yes | Low |
| `investment_screener/backend/tests/py_services/test_get_earnings_context_returns_prior_beat_rate.py` | plugin script | target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | Yes | Low |
| `investment_screener/backend/tests/py_services/test_harvest_earnings_expectations_dedup_on_unchanged_consensus.py` | plugin script | predictions.jsonl, target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | Yes | Low |
| `investment_screener/backend/tests/py_services/test_harvest_earnings_expectations_logs_consensus_change.py` | plugin script | predictions.jsonl | n/a | REMAINS_JSON_BY_DESIGN | No | Yes | Low |
| `investment_screener/backend/tests/py_services/test_harvest_earnings_expectations_null_consensus_degrades_gracefully.py` | plugin script | predictions.jsonl | n/a | REMAINS_JSON_BY_DESIGN | No | Yes | Low |
| `investment_screener/backend/tests/py_services/test_harvest_earnings_expectations_path_isolation.py` | plugin script | predictions.jsonl | n/a | REMAINS_JSON_BY_DESIGN | No | Yes | Low |
| `investment_screener/backend/tests/py_services/test_harvest_predictions.py` | plugin script | ANET.json, CORZ.json, predictions.jsonl, target-portfolio.json, thesis_breaker_state.json | n/a | REMAINS_JSON_BY_DESIGN | No | Yes | Low |
| `investment_screener/backend/tests/py_services/test_link_alert_to_e3_claim.py` | plugin script | predictions.jsonl | n/a | REMAINS_JSON_BY_DESIGN | No | Yes | Low |
| `investment_screener/backend/tests/py_services/test_lock_and_normalize_targets.py` | plugin script | target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | Yes | Low |
| `investment_screener/backend/tests/py_services/test_market_data_schema.py` | plugin script | market_data_response.schema.json | n/a | REMAINS_JSON_BY_DESIGN | No | Yes | Low |
| `investment_screener/backend/tests/py_services/test_market_regime.py` | plugin script | target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | Yes | Low |
| `investment_screener/backend/tests/py_services/test_migrate_research_report_pointers.py` | plugin script | PLTR.json | n/a | REMAINS_JSON_BY_DESIGN | No | Yes | Low |
| `investment_screener/backend/tests/py_services/test_order_risk_gates_builds_portfolio_state.py` | plugin script | target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | Yes | Low |
| `investment_screener/backend/tests/py_services/test_order_risk_gates_checks_breaker_veto.py` | plugin script | target-portfolio.json, thesis_breaker_state.json | n/a | REMAINS_JSON_BY_DESIGN | No | Yes | Low |
| `investment_screener/backend/tests/py_services/test_overnight_gaps.py` | plugin script | watchlist.json | n/a | REMAINS_JSON_BY_DESIGN | No | Yes | Low |
| `investment_screener/backend/tests/py_services/test_pine_auto_discovery_registers_scripts.py` | plugin script | registry.json | n/a | REMAINS_JSON_BY_DESIGN | No | Yes | Low |
| `investment_screener/backend/tests/py_services/test_pine_injection_auto_clicks.py` | plugin script | registry.json | n/a | REMAINS_JSON_BY_DESIGN | No | Yes | Low |
| `investment_screener/backend/tests/py_services/test_pine_library_manages_multiple_scripts.py` | plugin script | registry.json | n/a | REMAINS_JSON_BY_DESIGN | No | Yes | Low |
| `investment_screener/backend/tests/py_services/test_pine_registry_reads_writes_json.py` | plugin script | registry.json | n/a | REMAINS_JSON_BY_DESIGN | No | Yes | Low |
| `investment_screener/backend/tests/py_services/test_pine_rollback_on_error.py` | plugin script | registry.json | n/a | REMAINS_JSON_BY_DESIGN | No | Yes | Low |
| `investment_screener/backend/tests/py_services/test_pine_version_history_from_git.py` | plugin script | registry.json | n/a | REMAINS_JSON_BY_DESIGN | No | Yes | Low |
| `investment_screener/backend/tests/py_services/test_portfolio_action_import.py` | plugin script | portfolio.test.json, target_portfolio.test.json | n/a | REMAINS_JSON_BY_DESIGN | No | Yes | Low |
| `investment_screener/backend/tests/py_services/test_portfolio_io.py` | plugin script | portfolio.test.json, portfolio_with_totals.test.json | n/a | REMAINS_JSON_BY_DESIGN | No | Yes | Low |
| `investment_screener/backend/tests/py_services/test_prediction_ledger.py` | plugin script | predictions.jsonl | n/a | REMAINS_JSON_BY_DESIGN | No | Yes | Low |
| `investment_screener/backend/tests/py_services/test_prediction_ledger_validate.py` | plugin script | predictions.jsonl | n/a | REMAINS_JSON_BY_DESIGN | No | Yes | Low |
| `investment_screener/backend/tests/py_services/test_rebalancer.py` | plugin script | account_policy.json, target-portfolio.json, thesis_breaker_state.json | n/a | REMAINS_JSON_BY_DESIGN | No | Yes | Low |
| `investment_screener/backend/tests/py_services/test_risk_engine.py` | plugin script | target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | Yes | Low |
| `investment_screener/backend/tests/py_services/test_thesis_breakers.py` | plugin script | target-portfolio.json, thesis_breaker_state.json | n/a | REMAINS_JSON_BY_DESIGN | No | Yes | Low |
| `investment_screener/backend/tests/py_services/test_update_price_levels.py` | plugin script | GOOG.json, target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | Yes | Low |
| `investment_screener/backend/tests/py_services/test_verify_thesis_sync.py` | plugin script | AAPL.json, IBIT.json, MSFT.json, TSLA.json, target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | Yes | Low |
| `investment_screener/backend/tests/utils/zod-schemas.spec.ts` | plugin script | target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `plugins/portfolio-advisor/scripts/apply_catalyst.py` | plugin script | target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `plugins/portfolio-advisor/scripts/generate_grok_prompt.py` | plugin script | target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `plugins/portfolio-advisor/scripts/generate_portfolio_blueprint.py` | plugin script | target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `plugins/portfolio-advisor/scripts/generate_sub_strategy_blocks.py` | plugin script | target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `plugins/portfolio-advisor/scripts/scan_opportunities.py` | plugin script | target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `plugins/portfolio-advisor/scripts/sync_portfolio_roles.py` | plugin script | target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `plugins/portfolio-advisor/scripts/update_price_levels.py` | plugin script | target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | Yes | Low |
| `plugins/portfolio-advisor/scripts/update_targets.py` | plugin script | target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `plugins/portfolio-advisor/scripts/update_thesis.py` | plugin script | target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `plugins/portfolio-advisor/scripts/validate_weights.py` | plugin script | target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `plugins/portfolio-advisor/scripts/verify_refresh.py` | plugin script | target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `plugins/portfolio-advisor/tests/test_consolidate_research.py` | plugin script | PLTR.json | n/a | REMAINS_JSON_BY_DESIGN | No | Yes | Low |
| `plugins/tradingview/scripts/tv_create_alerts.py` | plugin script | target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `plugins/tradingview/scripts/tv_list_alerts.py` | plugin script | tradingview_alerts_actual.json | n/a | REMAINS_JSON_BY_DESIGN | No | Yes | Low |
| `plugins/tradingview/scripts/watchlist_manager.py` | plugin script | watchlist.json | n/a | REMAINS_JSON_BY_DESIGN | No | Yes | Low |
| `plugins/tradingview/tests/test_tv_list_alerts.py` | plugin script | tradingview_alerts_actual.json | n/a | REMAINS_JSON_BY_DESIGN | No | Yes | Low |
| `tradingview-cdp/cli.js` | plugin script | watchlist.json | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `investment_screener/backend/py_services/brief_recommendations.py` | report generator | standing-decisions.json | n/a | REMAINS_JSON_BY_DESIGN | No | Yes | Low |
| `investment_screener/backend/py_services/generate_reports.py` | report generator | target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | Yes | Low |
| `investment_screener/backend/py_services/generate_review_json.py` | report generator | target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `investment_screener/backend/py_services/generate_track_record_report.py` | report generator | predictions.jsonl | n/a | REMAINS_JSON_BY_DESIGN | No | Yes | Low |
| `investment_screener/backend/py_services/grade_predictions.py` | report generator | predictions.jsonl | n/a | REMAINS_JSON_BY_DESIGN | No | Yes | Low |
| `investment_screener/backend/tests/py_services/test_generate_track_record_report.py` | report generator | predictions.jsonl | n/a | REMAINS_JSON_BY_DESIGN | No | Yes | Low |
| `investment_screener/backend/tests/py_services/test_grade_predictions.py` | report generator | predictions.jsonl | n/a | REMAINS_JSON_BY_DESIGN | No | Yes | Low |
| `plugins/portfolio-advisor/scripts/generate_reports.py` | report generator | target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | Yes | Low |
| `plugins/portfolio-advisor/scripts/generate_review.py` | report generator | target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `plugins/portfolio-advisor/scripts/generate_review_json.py` | report generator | target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `plugins/portfolio-advisor/scripts/weekly_review.py` | report generator | target-portfolio.json, watchlist.json | n/a | REMAINS_JSON_BY_DESIGN | No | Yes | Low |
| `plugins/portfolio-advisor/skills/13f-analyze/scripts/generate_review_json.py` | skill | target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `plugins/portfolio-advisor/skills/13f-analyze/scripts/update_targets.py` | skill | target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `plugins/portfolio-advisor/skills/13f-analyze/scripts/verify_refresh.py` | skill | target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `plugins/portfolio-advisor/skills/calibrate-targets/scripts/generate_review_json.py` | skill | target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `plugins/portfolio-advisor/skills/calibrate-targets/scripts/update_targets.py` | skill | target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `plugins/portfolio-advisor/skills/calibrate-targets/scripts/update_thesis.py` | skill | target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `plugins/portfolio-advisor/skills/calibrate-targets/scripts/validate_weights.py` | skill | target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `plugins/portfolio-advisor/skills/calibrate-targets/scripts/verify_refresh.py` | skill | target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `plugins/portfolio-advisor/skills/daily-loop/scripts/generate_reports.py` | skill | target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | Yes | Low |
| `plugins/portfolio-advisor/skills/portfolio-health/SKILL.md` | skill | n/a | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `plugins/portfolio-advisor/skills/portfolio-health/scripts/apply_catalyst.py` | skill | target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `plugins/portfolio-advisor/skills/portfolio-health/scripts/generate_portfolio_blueprint.py` | skill | target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `plugins/portfolio-advisor/skills/portfolio-health/scripts/generate_review.py` | skill | target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `plugins/portfolio-advisor/skills/portfolio-health/scripts/generate_review_json.py` | skill | target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `plugins/portfolio-advisor/skills/portfolio-health/scripts/scan_opportunities.py` | skill | target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `plugins/portfolio-advisor/skills/portfolio-health/scripts/validate_weights.py` | skill | target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `plugins/portfolio-advisor/skills/portfolio-health/scripts/verify_refresh.py` | skill | target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `plugins/portfolio-advisor/skills/rebalance-portfolio/SKILL.md` | skill | n/a | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `plugins/portfolio-advisor/skills/rebalance-portfolio/scripts/update_targets.py` | skill | target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `plugins/portfolio-advisor/skills/rebalance-portfolio/scripts/validate_weights.py` | skill | target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `plugins/portfolio-advisor/skills/strategic-review/SKILL.md` | skill | n/a | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `plugins/portfolio-advisor/skills/strategic-review/scripts/apply_catalyst.py` | skill | target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `plugins/portfolio-advisor/skills/strategic-review/scripts/generate_portfolio_blueprint.py` | skill | target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `plugins/portfolio-advisor/skills/strategic-review/scripts/generate_review.py` | skill | target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `plugins/portfolio-advisor/skills/strategic-review/scripts/generate_review_json.py` | skill | target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `plugins/portfolio-advisor/skills/strategic-review/scripts/scan_opportunities.py` | skill | target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `plugins/portfolio-advisor/skills/strategic-review/scripts/update_targets.py` | skill | target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `plugins/portfolio-advisor/skills/strategic-review/scripts/validate_weights.py` | skill | target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `plugins/portfolio-advisor/skills/strategic-review/scripts/verify_refresh.py` | skill | target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `plugins/portfolio-advisor/skills/thesis-review/scripts/generate_portfolio_blueprint.py` | skill | target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `plugins/portfolio-advisor/skills/thesis-review/scripts/update_targets.py` | skill | target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `plugins/portfolio-advisor/skills/thesis-review/scripts/validate_weights.py` | skill | target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `plugins/portfolio-advisor/skills/update-portfolio-targets/scripts/update_targets.py` | skill | target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `plugins/portfolio-advisor/skills/update-portfolio-targets/scripts/update_thesis.py` | skill | target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `plugins/portfolio-advisor/skills/update-portfolio-targets/scripts/validate_weights.py` | skill | target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `plugins/portfolio-advisor/skills/update-portfolio-targets/scripts/verify_refresh.py` | skill | target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `plugins/portfolio-advisor/skills/x-news-sweep/scripts/apply_catalyst.py` | skill | target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `plugins/portfolio-advisor/skills/x-news-sweep/scripts/generate_grok_prompt.py` | skill | target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `plugins/portfolio-advisor/skills/x-news-sweep/scripts/generate_portfolio_blueprint.py` | skill | target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `plugins/portfolio-advisor/skills/x-news-sweep/scripts/generate_review_json.py` | skill | target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `plugins/portfolio-advisor/skills/x-news-sweep/scripts/update_targets.py` | skill | target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `plugins/portfolio-advisor/skills/x-news-sweep/scripts/validate_weights.py` | skill | target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `plugins/portfolio-advisor/skills/x-news-sweep/scripts/verify_refresh.py` | skill | target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `plugins/tradingview/skills/alert-list/scripts/tv_list_alerts.py` | skill | tradingview_alerts_actual.json | n/a | REMAINS_JSON_BY_DESIGN | No | Yes | Low |
| `plugins/tradingview/skills/alert-sync/scripts/tv_create_alerts.py` | skill | target-portfolio.json | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `plugins/portfolio-advisor/agents/data-quality-agent.md` | sub-agent | n/a | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `plugins/portfolio-advisor/agents/red-team-agent.md` | sub-agent | n/a | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `plugins/portfolio-advisor/agents/risk-officer-agent.md` | sub-agent | n/a | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `plugins/portfolio-advisor/agents/single-stock-advisor.md` | sub-agent | n/a | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `plugins/portfolio-advisor/agents/weekly-review-agent.md` | sub-agent | n/a | n/a | REMAINS_JSON_BY_DESIGN | No | No | Low |
| `run_investment_toolkit.py` | workflow | package.json | n/a | REMAINS_JSON_BY_DESIGN | No | Yes | Low |
| `run_tests.py` | workflow | package.json, portfolio.test.json, symlinks.json, target_portfolio.test.json | n/a | REMAINS_JSON_BY_DESIGN | No | Yes | Low |
| `investment_screener/frontend/src/components/ResearchReportViewer.tsx` | frontend component | n/a | Markdown View files (*.summary.md) | USES_GENERATED_VIEW | No | Yes | Low |
| `investment_screener/frontend/src/views/Dashboard.tsx` | frontend component | n/a | Markdown View files (*.summary.md) | USES_GENERATED_VIEW | No | Yes | Low |
| `investment_screener/backend/src/routes/dailybrief.ts` | backend route | n/a | intelligence.sqlite (ledger) | USES_LEDGER_REPOSITORY | No | Yes | Low |
| `investment_screener/backend/src/routes/docs.ts` | backend route | n/a | intelligence.sqlite (ledger) | USES_LEDGER_REPOSITORY | No | Yes | Low |
| `investment_screener/backend/py_services/compute_conviction_scores.py` | plugin script | n/a | intelligence.sqlite (ledger) | USES_LEDGER_REPOSITORY | No | Yes | Low |
| `investment_screener/backend/tests/api/dailybrief.spec.ts` | plugin script | n/a | intelligence.sqlite (ledger) | USES_LEDGER_REPOSITORY | No | Yes | Low |
| `investment_screener/backend/tests/api/docs.research.spec.ts` | plugin script | n/a | intelligence.sqlite (ledger) | USES_LEDGER_REPOSITORY | No | Yes | Low |
| `investment_screener/backend/tests/py_services/test_compute_conviction_scores.py` | plugin script | n/a | intelligence.sqlite (ledger) | USES_LEDGER_REPOSITORY | No | Yes | Low |
| `investment_screener/backend/tests/py_services/test_daily_brief_ta_sweep_delegates.py` | plugin script | n/a | intelligence.sqlite (ledger) | USES_LEDGER_REPOSITORY | No | Yes | Low |
| `plugins/tradingview/scripts/ta_sweep_batch.py` | plugin script | n/a | intelligence.sqlite (ledger) | USES_LEDGER_REPOSITORY | No | Yes | Low |
| `plugins/tradingview/tests/test_ta_sweep_batch.py` | plugin script | n/a | intelligence.sqlite (ledger) | USES_LEDGER_REPOSITORY | No | Yes | Low |
| `investment_screener/backend/py_services/daily_brief.py` | report generator | n/a | intelligence.sqlite (ledger) | USES_LEDGER_REPOSITORY | No | Yes | Low |
| `plugins/portfolio-advisor/scripts/daily_brief.py` | report generator | n/a | intelligence.sqlite (ledger) | USES_LEDGER_REPOSITORY | No | Yes | Low |
| `plugins/portfolio-advisor/skills/daily-brief/scripts/daily_brief.py` | skill | n/a | intelligence.sqlite (ledger) | USES_LEDGER_REPOSITORY | No | Yes | Low |
| `plugins/portfolio-advisor/skills/daily-loop/SKILL.md` | skill | n/a | intelligence.sqlite (ledger) | USES_LEDGER_REPOSITORY | No | Yes | Low |
| `plugins/stock-valuation/skills/stock-research/SKILL.md` | skill | n/a | intelligence.sqlite (ledger) | USES_LEDGER_REPOSITORY | No | Yes | Low |
| `plugins/stock-valuation/skills/stock_valuation/SKILL.md` | skill | n/a | intelligence.sqlite (ledger) | USES_LEDGER_REPOSITORY | No | Yes | Low |
| `plugins/tradingview/skills/ta-daily-sweep/scripts/ta_sweep_batch.py` | skill | n/a | intelligence.sqlite (ledger) | USES_LEDGER_REPOSITORY | No | Yes | Low |
| `plugins/portfolio-advisor/agents/daily-loop-agent.md` | sub-agent | n/a | intelligence.sqlite (ledger) | USES_LEDGER_REPOSITORY | No | Yes | Low |

## Skill Audit

This section documents the classification of all relevant `SKILL.md` orchestrators in the toolkit:

| Skill Path | Purpose | Status | Intended Source | Rationale |
|---|---|---|---|---|
| `plugins/stock-valuation/skills/stock_valuation/SKILL.md` | Single stock DCF evaluation | USES_LEDGER_REPOSITORY | intelligence.sqlite | Wired via PR #77 to call ledger CLI |
| `plugins/stock-valuation/skills/stock-research/SKILL.md` | Qualitative catalyst sweep | USES_LEDGER_REPOSITORY | intelligence.sqlite | Wired via PR #77 to call ledger CLI |
| `plugins/portfolio-advisor/skills/daily-loop/SKILL.md` | Interactive daily brief and triage | USES_LEDGER_REPOSITORY | intelligence.sqlite (ledger) | Instructs to run and read daily brief and TA sweeps via SQLite ledger queries |
| `plugins/portfolio-advisor/skills/portfolio-health/SKILL.md` | Conviction score and targets verify | REMAINS_JSON_BY_DESIGN | n/a | Uses only target-portfolio.json, target weight math is out-of-scope for the ledger |
| `plugins/portfolio-advisor/skills/rebalance-portfolio/SKILL.md` | Valuation-gated rebalancer | REMAINS_JSON_BY_DESIGN | n/a | Uses target-portfolio.json and account policy JSON, out-of-scope |
| `plugins/portfolio-advisor/skills/strategic-review/SKILL.md` | Conviction target weighting session | REMAINS_JSON_BY_DESIGN | n/a | Uses target-portfolio.json, out-of-scope |

## Sub-Agent Audit

Classification of specialized agent instructions:

| Agent | Purpose | Status | Rationale |
|---|---|---|---|
| `plugins/portfolio-advisor/agents/daily-loop-agent.md` | Interactive daily workflow engine | USES_LEDGER_REPOSITORY | Instructs to check latest TECHNICAL_SWEEP and REVIEW_DAILY entries in ledger |
| `plugins/portfolio-advisor/agents/weekly-review-agent.md` | Weekend review loop agent | REMAINS_JSON_BY_DESIGN | Reads only portfolio target weight files |
| `plugins/portfolio-advisor/agents/single-stock-advisor.md` | Single-equity analyst helper | REMAINS_JSON_BY_DESIGN | Focuses on DCF projections JSON and target sizing |
| `plugins/portfolio-advisor/agents/risk-officer-agent.md` | Risk gating advisor | REMAINS_JSON_BY_DESIGN | Validates target sizes and policies |
| `plugins/portfolio-advisor/agents/red-team-agent.md` | Adversarial thesis reviewer | REMAINS_JSON_BY_DESIGN | Challenges valuation projections |
| `plugins/portfolio-advisor/agents/data-quality-agent.md` | Data consistency advisor | REMAINS_JSON_BY_DESIGN | Reviews structural formats |

## Backend Audit

Classification of Express backend routes and core services:

| Path | Status | Intended Source | Rationale |
|---|---|---|---|
| `investment_screener/backend/src/routes/docs.ts` | USES_LEDGER_REPOSITORY | intelligence.sqlite | Active queries SQLite ledger via python bridge wrapper query_ledger_research.py |
| `investment_screener/backend/src/routes/dailybrief.ts` | USES_LEDGER_REPOSITORY | intelligence.sqlite | Active queries SQLite ledger via python bridge wrapper query_ledger_brief.py |
| `investment_screener/backend/src/routes/screener.ts` | REMAINS_JSON_BY_DESIGN | n/a | Reads target-portfolio.json, out-of-scope |
| `investment_screener/backend/src/routes/stock.ts` | REMAINS_JSON_BY_DESIGN | n/a | Serves projections/watchlist JSON, out-of-scope |
| `investment_screener/backend/src/routes/theses.ts` | REMAINS_JSON_BY_DESIGN | n/a | Reads target portfolio and active portfolio JSON, out-of-scope |
| `investment_screener/backend/src/routes/thirteenf.ts` | OUT_OF_SCOPE | n/a | Parses SEC filings separate from ledger domain |
| `investment_screener/backend/src/services/BrokerSyncService.ts` | REMAINS_JSON_BY_DESIGN | n/a | Live brokerage/target integration service, out-of-scope |
| `investment_screener/backend/src/services/ThesisService.ts` | REMAINS_JSON_BY_DESIGN | n/a | Handles account target policies, out-of-scope |
| `investment_screener/backend/src/services/WatchlistService.ts` | REMAINS_JSON_BY_DESIGN | n/a | Manages flat-file watchlist data, out-of-scope |
| `investment_screener/backend/src/utils/paths.ts` | REMAINS_JSON_BY_DESIGN | n/a | Helper containing static folder pathways, out-of-scope |
| `investment_screener/backend/src/utils/zod-schemas.ts` | REMAINS_JSON_BY_DESIGN | n/a | Zod schema validation constructs, out-of-scope |

## Frontend Audit

Key UI views and components to rewire once backend routes transition:

| Component | Type | Current Source | Status | Intended Source |
|---|---|---|---|---|
| `investment_screener/frontend/src/views/Dashboard.tsx` | View | GET /api/daily-brief/latest | USES_GENERATED_VIEW | Backend route backed by SQLite |
| `investment_screener/frontend/src/components/ResearchReportViewer.tsx` | Component | GET /api/research/:filename | USES_GENERATED_VIEW | Backend route serving View files |

## Gap Analysis

### 1. What uses the new architecture today?
- No runtime scripts or backend routes actively read or write live data via the SQLite ledger today.
- Two skills (`stock_valuation` and `stock-research`) have been updated in their Markdown orchestrators to call the ledger command-line tool, but the actual execution of those skills happens during manual runs.

### 2. What still uses legacy JSON?
- `daily_brief.py`, `ta_sweep_batch.py`, and `compute_conviction_scores.py` read and write `ta-sweep-results.json` directly.
- The Express backend (`dailybrief.ts`) reads historical daily brief JSON files directly from disk.

### 3. What still uses legacy Markdown?
- Research reports (`data/research/*.md`) are written to disk as dated markdown files by the valuation/research scripts, and read directly from disk by `docs.ts` route.

### 4. What must be migrated before a real cutover?
- Run the actual migration scripts (`migrate_research_to_ledger.py`, `migrate_research_report_pointers.py`) to build `observations.jsonl` and `intelligence.sqlite` from real dated Markdown files.
- Rewire wave 1 scripts (`daily_brief.py`, `ta_sweep_batch.py`, `compute_conviction_scores.py`) to read/write from `intelligence.sqlite` via the Python shared repository layer (`py_services/intelligence/`).
- Rewire `docs.ts` and `dailybrief.ts` Express routes to query the ledger database / generated view files instead of reading from disk files directly.

### 5. What would break if migration ran tomorrow?
- **Nothing** would break immediately since the migration itself is purely additive and non-destructive. Dated Markdown files and legacy JSON files are not modified or deleted during the migration.

### 6. What would break if cleanup ran tomorrow?
- **Everything** related to research reports and daily briefs would break.
- The research report lists in the UI would go blank (since `docs.ts` readdir of `data/research/` would find nothing).
- Daily brief dashboard metrics would fail (since `/api/daily-brief/latest` would find no JSON brief files).
- Conviction scores and TA sweep results would crash in `daily_brief.py` and `compute_conviction_scores.py`.

