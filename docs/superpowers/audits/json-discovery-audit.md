# JSON Discovery Audit

## Summary

| Category | Count |
|---|---:|
| JSON files discovered | 208 |
| JSONL files discovered | 2 |
| Files classified ALLOWED_AUTHORITATIVE_JSON | 2 |
| Files classified ALLOWED_CONFIGURATION_JSON | 11 |
| Files classified ALLOWED_MODEL_ARTIFACT_JSON | 82 |
| Files classified ALLOWED_SEPARATE_DOMAIN_LEDGER_JSONL | 2 |
| Files classified ALLOWED_TEST_FIXTURE_JSON | 5 |
| Files classified ALLOWED_GENERATED_CACHE_JSON | 0 |
| Files classified MIGRATE_TO_INTELLIGENCE_LEDGER | 1 |
| Files classified GENERATE_FROM_LEDGER_OR_SQLITE | 0 |
| Files classified ARCHIVE_LEGACY_READ_ONLY | 0 |
| Files classified DELETE_AFTER_VERIFIED_ARCHIVE | 0 |
| Files classified OUT_OF_SCOPE_FOR_THIS_PHASE | 0 |
| Files classified UNKNOWN_REQUIRES_REVIEW | 107 |

## Files Requiring Human Review

| File | Reason | Suggested next action |
|---|---|---|
| `plugin-sources.json` | No known heuristic match | INVESTIGATE |
| `schemas/market_data_response.schema.json` | No known heuristic match | INVESTIGATE |
| `schemas/prediction.schema.json` | No known heuristic match | INVESTIGATE |
| `.claude-plugin/marketplace.json` | No known heuristic match | INVESTIGATE |
| `investment_screener/frontend/tsconfig.node.json` | No known heuristic match | INVESTIGATE |
| `investment_screener/frontend/tsconfig.app.json` | No known heuristic match | INVESTIGATE |
| `investment_screener/backend/data/thesis_breaker_state.json` | No known heuristic match | INVESTIGATE |
| `investment_screener/backend/data/tradingview_alerts_actual.json` | No known heuristic match | INVESTIGATE |
| `investment_screener/backend/data/account_policy.json` | No known heuristic match | INVESTIGATE |
| `investment_screener/backend/data/13f/000204572425000002.json` | No known heuristic match | INVESTIGATE |
| `investment_screener/backend/data/13f/000204572425000008.json` | No known heuristic match | INVESTIGATE |
| `investment_screener/backend/data/13f/0002045724_index.json` | No known heuristic match | INVESTIGATE |
| `investment_screener/backend/data/13f/000204572426000008.json` | No known heuristic match | INVESTIGATE |
| `investment_screener/backend/data/13f/000204572425000006.json` | No known heuristic match | INVESTIGATE |
| `investment_screener/backend/data/13f/000204572426000002.json` | No known heuristic match | INVESTIGATE |
| `investment_screener/backend/data/13f/0002045724_diff.json` | No known heuristic match | INVESTIGATE |
| `investment_screener/backend/data/etf_analysis/FOTO.json` | No known heuristic match | INVESTIGATE |
| `investment_screener/backend/data/etf_analysis/ETHA.json` | No known heuristic match | INVESTIGATE |
| `investment_screener/backend/data/etf_analysis/WQTM.json` | No known heuristic match | INVESTIGATE |
| `investment_screener/backend/data/etf_analysis/DXYZ.json` | No known heuristic match | INVESTIGATE |
| `investment_screener/backend/data/etf_analysis/KOID.json` | No known heuristic match | INVESTIGATE |
| `investment_screener/backend/data/etf_analysis/HUMN.json` | No known heuristic match | INVESTIGATE |
| `investment_screener/backend/data/etf_analysis/DRAM.json` | No known heuristic match | INVESTIGATE |
| `investment_screener/backend/data/etf_analysis/IBIT.json` | No known heuristic match | INVESTIGATE |
| `investment_screener/frontend/.vite/deps/_metadata.json` | No known heuristic match | INVESTIGATE |
| `plugins/etf-analysis/plugin.json` | No known heuristic match | INVESTIGATE |
| `plugins/tradingview/plugin.json` | No known heuristic match | INVESTIGATE |
| `plugins/toolkit-manager/plugin.json` | No known heuristic match | INVESTIGATE |
| `plugins/stock-valuation/plugin.json` | No known heuristic match | INVESTIGATE |
| `plugins/portfolio-advisor/plugin.json` | No known heuristic match | INVESTIGATE |
| `plugins/portfolio-advisor/references/standing-decisions.json` | No known heuristic match | INVESTIGATE |
| `plugins/portfolio-advisor/.claude-plugin/plugin.json` | No known heuristic match | INVESTIGATE |
| `plugins/portfolio-advisor/assets/templates/target_portfolio_template.json` | No known heuristic match | INVESTIGATE |
| `plugins/portfolio-advisor/assets/templates/portfolio_analysis_recommendations_template.json` | No known heuristic match | INVESTIGATE |
| `plugins/portfolio-advisor/assets/templates/ytd_performance_report_template.json` | No known heuristic match | INVESTIGATE |
| `plugins/portfolio-advisor/skills/13f-tracker/evals/evals.json` | No known heuristic match | INVESTIGATE |
| `plugins/portfolio-advisor/skills/thesis-review/evals/evals.json` | No known heuristic match | INVESTIGATE |
| `plugins/portfolio-advisor/skills/thesis-review/assets/templates/target_portfolio_template.json` | No known heuristic match | INVESTIGATE |
| `plugins/portfolio-advisor/skills/strategic-review/evals/evals.json` | No known heuristic match | INVESTIGATE |
| `plugins/portfolio-advisor/skills/strategic-review/assets/templates/portfolio_analysis_recommendations_template.json` | No known heuristic match | INVESTIGATE |
| `plugins/portfolio-advisor/skills/portfolio-health/evals/evals.json` | No known heuristic match | INVESTIGATE |
| `plugins/portfolio-advisor/skills/rebalance-portfolio/evals/evals.json` | No known heuristic match | INVESTIGATE |
| `plugins/portfolio-advisor/skills/thesis-challenge-bundler/evals/evals.json` | No known heuristic match | INVESTIGATE |
| `plugins/portfolio-advisor/skills/set-thesis-breakers/evals/evals.json` | No known heuristic match | INVESTIGATE |
| `plugins/portfolio-advisor/skills/adversarial-review/evals/evals.json` | No known heuristic match | INVESTIGATE |
| `plugins/portfolio-advisor/skills/daily-brief/evals/evals.json` | No known heuristic match | INVESTIGATE |
| `plugins/portfolio-advisor/skills/calibrate-targets/evals/evals.json` | No known heuristic match | INVESTIGATE |
| `plugins/portfolio-advisor/skills/norberts-gambit/evals/evals.json` | No known heuristic match | INVESTIGATE |
| `plugins/portfolio-advisor/skills/daily-loop/evals/evals.json` | No known heuristic match | INVESTIGATE |
| `plugins/portfolio-advisor/skills/x-news-sweep/evals/evals.json` | No known heuristic match | INVESTIGATE |
| `plugins/portfolio-advisor/skills/update-portfolio-targets/evals/evals.json` | No known heuristic match | INVESTIGATE |
| `plugins/portfolio-advisor/skills/update-portfolio-targets/assets/templates/target_portfolio_template.json` | No known heuristic match | INVESTIGATE |
| `plugins/portfolio-advisor/skills/ytd-return/evals/evals.json` | No known heuristic match | INVESTIGATE |
| `plugins/portfolio-advisor/skills/ytd-return/assets/templates/ytd_performance_report_template.json` | No known heuristic match | INVESTIGATE |
| `plugins/portfolio-advisor/skills/13f-analyze/evals/evals.json` | No known heuristic match | INVESTIGATE |
| `plugins/portfolio-advisor/agents/evals/weekly-review-agent.json` | No known heuristic match | INVESTIGATE |
| `plugins/portfolio-advisor/agents/evals/thesis-review-agent.json` | No known heuristic match | INVESTIGATE |
| `plugins/portfolio-advisor/agents/evals/risk-officer-agent.json` | No known heuristic match | INVESTIGATE |
| `plugins/portfolio-advisor/agents/evals/portfolio-advisor-orchestrator.json` | No known heuristic match | INVESTIGATE |
| `plugins/portfolio-advisor/agents/evals/single-stock-advisor.json` | No known heuristic match | INVESTIGATE |
| `plugins/portfolio-advisor/agents/evals/data-quality-agent.json` | No known heuristic match | INVESTIGATE |
| `plugins/portfolio-advisor/agents/evals/red-team-agent.json` | No known heuristic match | INVESTIGATE |
| `plugins/portfolio-advisor/agents/evals/daily-loop-agent.json` | No known heuristic match | INVESTIGATE |
| `plugins/stock-valuation/.claude-plugin/plugin.json` | No known heuristic match | INVESTIGATE |
| `plugins/stock-valuation/assets/templates/projection_template.json` | No known heuristic match | INVESTIGATE |
| `plugins/stock-valuation/skills/valuation-math-validation/evals/evals.json` | No known heuristic match | INVESTIGATE |
| `plugins/stock-valuation/skills/stock_valuation/evals/evals.json` | No known heuristic match | INVESTIGATE |
| `plugins/stock-valuation/skills/stock_valuation/assets/templates/projection_template.json` | No known heuristic match | INVESTIGATE |
| `plugins/stock-valuation/skills/stock_valuation/references/examples/example_NVDA_placeholder.json` | No known heuristic match | INVESTIGATE |
| `plugins/stock-valuation/skills/stock_valuation/references/examples/example_NVDA_2026-05-02.json` | No known heuristic match | INVESTIGATE |
| `plugins/stock-valuation/skills/stock_valuation/references/examples/example_GOOG_2026-05-02.json` | No known heuristic match | INVESTIGATE |
| `plugins/stock-valuation/skills/stock_valuation/references/examples/example_PANW_2026-05-02.json` | No known heuristic match | INVESTIGATE |
| `plugins/stock-valuation/skills/forward-valuation-challenge/evals/evals.json` | No known heuristic match | INVESTIGATE |
| `plugins/stock-valuation/skills/stock-research/evals/evals.json` | No known heuristic match | INVESTIGATE |
| `plugins/stock-valuation/scripts/cache/SKHY.json` | No known heuristic match | INVESTIGATE |
| `plugins/toolkit-manager/.claude-plugin/plugin.json` | No known heuristic match | INVESTIGATE |
| `plugins/toolkit-manager/skills/run-screener/evals/evals.json` | No known heuristic match | INVESTIGATE |
| `plugins/toolkit-manager/agents/evals/toolkit-onboarding-guide.json` | No known heuristic match | INVESTIGATE |
| `plugins/tradingview/.claude-plugin/plugin.json` | No known heuristic match | INVESTIGATE |
| `plugins/tradingview/assets/pinescript-indicators/registry.json` | No known heuristic match | INVESTIGATE |
| `plugins/tradingview/skills/pine-inject/evals/evals.json` | No known heuristic match | INVESTIGATE |
| `plugins/tradingview/skills/tv-save-indicator/evals/evals.json` | No known heuristic match | INVESTIGATE |
| `plugins/tradingview/skills/ta-red-team/evals/evals.json` | No known heuristic match | INVESTIGATE |
| `plugins/tradingview/skills/chart-snapshot/evals/evals.json` | No known heuristic match | INVESTIGATE |
| `plugins/tradingview/skills/modify-order/evals/evals.json` | No known heuristic match | INVESTIGATE |
| `plugins/tradingview/skills/tv-add-indicator/evals/evals.json` | No known heuristic match | INVESTIGATE |
| `plugins/tradingview/skills/cancel-order/evals/evals.json` | No known heuristic match | INVESTIGATE |
| `plugins/tradingview/skills/ta-snapshot/evals/evals.json` | No known heuristic match | INVESTIGATE |
| `plugins/tradingview/skills/tv-setup/evals/evals.json` | No known heuristic match | INVESTIGATE |
| `plugins/tradingview/skills/tv-change-symbol/evals/evals.json` | No known heuristic match | INVESTIGATE |
| `plugins/tradingview/skills/ta-daily-sweep/evals/evals.json` | No known heuristic match | INVESTIGATE |
| `plugins/tradingview/skills/tv-change-type/evals/evals.json` | No known heuristic match | INVESTIGATE |
| `plugins/tradingview/skills/alert-list/evals/evals.json` | No known heuristic match | INVESTIGATE |
| `plugins/tradingview/skills/alert-sync/evals/evals.json` | No known heuristic match | INVESTIGATE |
| `plugins/tradingview/skills/author-pine-script/evals/evals.json` | No known heuristic match | INVESTIGATE |
| `plugins/tradingview/skills/tv-manage-watchlists/evals/evals.json` | No known heuristic match | INVESTIGATE |
| `plugins/tradingview/skills/get-orders/evals/evals.json` | No known heuristic match | INVESTIGATE |
| `plugins/tradingview/skills/tv-chart-setup/evals/evals.json` | No known heuristic match | INVESTIGATE |
| `plugins/tradingview/skills/technical-analysis-expert/evals/evals.json` | No known heuristic match | INVESTIGATE |
| `plugins/tradingview/skills/tv-portfolio-sync/evals/evals.json` | No known heuristic match | INVESTIGATE |
| `plugins/tradingview/skills/price-refresh/evals/evals.json` | No known heuristic match | INVESTIGATE |
| `plugins/tradingview/skills/place-order/evals/evals.json` | No known heuristic match | INVESTIGATE |
| `plugins/tradingview/agents/evals/tradingview-onboarding.json` | No known heuristic match | INVESTIGATE |
| `plugins/tradingview/agents/evals/ta-guide.json` | No known heuristic match | INVESTIGATE |
| `plugins/etf-analysis/assets/templates/etf_analysis_template.json` | No known heuristic match | INVESTIGATE |
| `plugins/etf-analysis/skills/etf_analysis/evals/evals.json` | No known heuristic match | INVESTIGATE |
| `plugins/etf-analysis/skills/etf_analysis/assets/templates/etf_analysis_template.json` | No known heuristic match | INVESTIGATE |

## Per-File Inventory

### skills-lock.json

**Classification:** ALLOWED_CONFIGURATION_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugin-sources.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### symlinks.json

**Classification:** ALLOWED_CONFIGURATION_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### context/events.jsonl

**Classification:** ALLOWED_SEPARATE_DOMAIN_LEDGER_JSONL

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### schemas/market_data_response.schema.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### schemas/prediction.schema.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

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
- (none detected)

### .claude-plugin/marketplace.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

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
- (none detected)

### investment_screener/frontend/tsconfig.node.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/frontend/tsconfig.app.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/frontend/package.json

**Classification:** ALLOWED_CONFIGURATION_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

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
- (none detected)

### investment_screener/backend/tsconfig.json

**Classification:** ALLOWED_CONFIGURATION_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/thesis_breaker_state.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/predictions.jsonl

**Classification:** ALLOWED_SEPARATE_DOMAIN_LEDGER_JSONL

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/tradingview_alerts_actual.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/watchlist.json

**Classification:** ALLOWED_AUTHORITATIVE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/ta-sweep-results.json

**Classification:** MIGRATE_TO_INTELLIGENCE_LEDGER

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/account_policy.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/theses/target-portfolio.json

**Classification:** ALLOWED_AUTHORITATIVE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/projections/COHR.json

**Classification:** ALLOWED_MODEL_ARTIFACT_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/projections/BW.json

**Classification:** ALLOWED_MODEL_ARTIFACT_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/projections/ANET.json

**Classification:** ALLOWED_MODEL_ARTIFACT_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/projections/RGTI.json

**Classification:** ALLOWED_MODEL_ARTIFACT_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/projections/CRCL.json

**Classification:** ALLOWED_MODEL_ARTIFACT_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/projections/FOTO.json

**Classification:** ALLOWED_MODEL_ARTIFACT_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/projections/KRMN.json

**Classification:** ALLOWED_MODEL_ARTIFACT_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/projections/VRT.json

**Classification:** ALLOWED_MODEL_ARTIFACT_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/projections/ASML.json

**Classification:** ALLOWED_MODEL_ARTIFACT_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/projections/PANW.json

**Classification:** ALLOWED_MODEL_ARTIFACT_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/projections/CEG.json

**Classification:** ALLOWED_MODEL_ARTIFACT_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/projections/AMD.json

**Classification:** ALLOWED_MODEL_ARTIFACT_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/projections/LBRT.json

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

### investment_screener/backend/data/projections/RDW.json

**Classification:** ALLOWED_MODEL_ARTIFACT_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/projections/BITF.json

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

### investment_screener/backend/data/projections/KRC.json

**Classification:** ALLOWED_MODEL_ARTIFACT_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/projections/PUMP.json

**Classification:** ALLOWED_MODEL_ARTIFACT_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/projections/RKLB.json

**Classification:** ALLOWED_MODEL_ARTIFACT_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/projections/HUT.json

**Classification:** ALLOWED_MODEL_ARTIFACT_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/projections/CRSP.json

**Classification:** ALLOWED_MODEL_ARTIFACT_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/projections/INTC.json

**Classification:** ALLOWED_MODEL_ARTIFACT_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/projections/OKLO.json

**Classification:** ALLOWED_MODEL_ARTIFACT_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/projections/WYFI.json

**Classification:** ALLOWED_MODEL_ARTIFACT_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/projections/CRWD.json

**Classification:** ALLOWED_MODEL_ARTIFACT_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/projections/VST.json

**Classification:** ALLOWED_MODEL_ARTIFACT_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/projections/QBTS.json

**Classification:** ALLOWED_MODEL_ARTIFACT_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/projections/ASTS.json

**Classification:** ALLOWED_MODEL_ARTIFACT_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/projections/POET.json

**Classification:** ALLOWED_MODEL_ARTIFACT_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/projections/LITE.json

**Classification:** ALLOWED_MODEL_ARTIFACT_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/projections/ETHA.json

**Classification:** ALLOWED_MODEL_ARTIFACT_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/projections/MSFT.json

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

### investment_screener/backend/data/projections/WQTM.json

**Classification:** ALLOWED_MODEL_ARTIFACT_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/projections/TSLA.json

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

### investment_screener/backend/data/projections/LLY.json

**Classification:** ALLOWED_MODEL_ARTIFACT_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/projections/DXYZ.json

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

### investment_screener/backend/data/projections/CACI.json

**Classification:** ALLOWED_MODEL_ARTIFACT_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/projections/AAPL.json

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

### investment_screener/backend/data/projections/SYM.json

**Classification:** ALLOWED_MODEL_ARTIFACT_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/projections/PLTR.json

**Classification:** ALLOWED_MODEL_ARTIFACT_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/projections/AMZN.json

**Classification:** ALLOWED_MODEL_ARTIFACT_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

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

### investment_screener/backend/data/projections/CELH.json

**Classification:** ALLOWED_MODEL_ARTIFACT_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/projections/KOID.json

**Classification:** ALLOWED_MODEL_ARTIFACT_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/projections/EQT.json

**Classification:** ALLOWED_MODEL_ARTIFACT_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/projections/NKE.json

**Classification:** ALLOWED_MODEL_ARTIFACT_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/projections/IONQ.json

**Classification:** ALLOWED_MODEL_ARTIFACT_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/projections/SEI.json

**Classification:** ALLOWED_MODEL_ARTIFACT_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/projections/HUMN.json

**Classification:** ALLOWED_MODEL_ARTIFACT_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/projections/CRM.json

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

### investment_screener/backend/data/projections/CLSK.json

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

### investment_screener/backend/data/projections/CAKE.json

**Classification:** ALLOWED_MODEL_ARTIFACT_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/projections/CIFR.json

**Classification:** ALLOWED_MODEL_ARTIFACT_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/projections/DRAM.json

**Classification:** ALLOWED_MODEL_ARTIFACT_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/projections/AVGO.json

**Classification:** ALLOWED_MODEL_ARTIFACT_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/projections/TEM.json

**Classification:** ALLOWED_MODEL_ARTIFACT_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/projections/NOW.json

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

### investment_screener/backend/data/projections/IBIT.json

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

### investment_screener/backend/data/projections/PSIX.json

**Classification:** ALLOWED_MODEL_ARTIFACT_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/projections/TEAM.json

**Classification:** ALLOWED_MODEL_ARTIFACT_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/projections/TSEM.json

**Classification:** ALLOWED_MODEL_ARTIFACT_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/projections/ORCL.json

**Classification:** ALLOWED_MODEL_ARTIFACT_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/projections/NVDA.json

**Classification:** ALLOWED_MODEL_ARTIFACT_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/projections/COIN.json

**Classification:** ALLOWED_MODEL_ARTIFACT_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/projections/EQIX.json

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

### investment_screener/backend/data/projections/ALAB.json

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

### investment_screener/backend/data/projections/META.json

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

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/13f/000204572425000008.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/13f/0002045724_index.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/13f/000204572426000008.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/13f/000204572425000006.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/13f/000204572426000002.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/13f/0002045724_diff.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/etf_analysis/FOTO.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/etf_analysis/ETHA.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/etf_analysis/WQTM.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/etf_analysis/DXYZ.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/etf_analysis/KOID.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/etf_analysis/HUMN.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/etf_analysis/DRAM.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/etf_analysis/IBIT.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/tests/fixtures/edgar_companyfacts_aapl.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/tests/fixtures/target_portfolio.test.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/tests/fixtures/BROKEN_projection.test.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/tests/fixtures/portfolio_with_totals.test.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/tests/fixtures/portfolio.test.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/frontend/.vite/deps/_metadata.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/frontend/.vite/deps/package.json

**Classification:** ALLOWED_CONFIGURATION_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/etf-analysis/plugin.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/tradingview/plugin.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/toolkit-manager/plugin.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/stock-valuation/plugin.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/portfolio-advisor/plugin.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/portfolio-advisor/references/standing-decisions.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/portfolio-advisor/.claude-plugin/plugin.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/portfolio-advisor/assets/templates/target_portfolio_template.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/portfolio-advisor/assets/templates/portfolio_analysis_recommendations_template.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/portfolio-advisor/assets/templates/ytd_performance_report_template.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/portfolio-advisor/skills/13f-tracker/evals/evals.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/portfolio-advisor/skills/thesis-review/evals/evals.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/portfolio-advisor/skills/thesis-review/assets/templates/target_portfolio_template.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/portfolio-advisor/skills/strategic-review/evals/evals.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/portfolio-advisor/skills/strategic-review/assets/templates/portfolio_analysis_recommendations_template.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/portfolio-advisor/skills/portfolio-health/evals/evals.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/portfolio-advisor/skills/rebalance-portfolio/evals/evals.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/portfolio-advisor/skills/thesis-challenge-bundler/evals/evals.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/portfolio-advisor/skills/set-thesis-breakers/evals/evals.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/portfolio-advisor/skills/adversarial-review/evals/evals.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/portfolio-advisor/skills/daily-brief/evals/evals.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/portfolio-advisor/skills/calibrate-targets/evals/evals.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/portfolio-advisor/skills/norberts-gambit/evals/evals.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/portfolio-advisor/skills/daily-loop/evals/evals.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/portfolio-advisor/skills/x-news-sweep/evals/evals.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/portfolio-advisor/skills/update-portfolio-targets/evals/evals.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/portfolio-advisor/skills/update-portfolio-targets/assets/templates/target_portfolio_template.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/portfolio-advisor/skills/ytd-return/evals/evals.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/portfolio-advisor/skills/ytd-return/assets/templates/ytd_performance_report_template.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/portfolio-advisor/skills/13f-analyze/evals/evals.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/portfolio-advisor/agents/evals/weekly-review-agent.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/portfolio-advisor/agents/evals/thesis-review-agent.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/portfolio-advisor/agents/evals/risk-officer-agent.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/portfolio-advisor/agents/evals/portfolio-advisor-orchestrator.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/portfolio-advisor/agents/evals/single-stock-advisor.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/portfolio-advisor/agents/evals/data-quality-agent.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/portfolio-advisor/agents/evals/red-team-agent.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/portfolio-advisor/agents/evals/daily-loop-agent.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/stock-valuation/.claude-plugin/plugin.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/stock-valuation/assets/templates/projection_template.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/stock-valuation/skills/valuation-math-validation/evals/evals.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/stock-valuation/skills/stock_valuation/evals/evals.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/stock-valuation/skills/stock_valuation/assets/templates/projection_template.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/stock-valuation/skills/stock_valuation/references/examples/example_NVDA_placeholder.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/stock-valuation/skills/stock_valuation/references/examples/example_NVDA_2026-05-02.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/stock-valuation/skills/stock_valuation/references/examples/example_GOOG_2026-05-02.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/stock-valuation/skills/stock_valuation/references/examples/example_PANW_2026-05-02.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/stock-valuation/skills/forward-valuation-challenge/evals/evals.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/stock-valuation/skills/stock-research/evals/evals.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/stock-valuation/scripts/cache/SKHY.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/toolkit-manager/.claude-plugin/plugin.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/toolkit-manager/skills/run-screener/evals/evals.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/toolkit-manager/agents/evals/toolkit-onboarding-guide.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/tradingview/.claude-plugin/plugin.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/tradingview/assets/pinescript-indicators/registry.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/tradingview/skills/pine-inject/evals/evals.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/tradingview/skills/tv-save-indicator/evals/evals.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/tradingview/skills/ta-red-team/evals/evals.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/tradingview/skills/chart-snapshot/evals/evals.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/tradingview/skills/modify-order/evals/evals.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/tradingview/skills/tv-add-indicator/evals/evals.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/tradingview/skills/cancel-order/evals/evals.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/tradingview/skills/ta-snapshot/evals/evals.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/tradingview/skills/tv-setup/evals/evals.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/tradingview/skills/tv-change-symbol/evals/evals.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/tradingview/skills/ta-daily-sweep/evals/evals.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/tradingview/skills/tv-change-type/evals/evals.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/tradingview/skills/alert-list/evals/evals.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/tradingview/skills/alert-sync/evals/evals.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/tradingview/skills/author-pine-script/evals/evals.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/tradingview/skills/tv-manage-watchlists/evals/evals.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/tradingview/skills/get-orders/evals/evals.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/tradingview/skills/tv-chart-setup/evals/evals.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/tradingview/skills/technical-analysis-expert/evals/evals.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/tradingview/skills/tv-portfolio-sync/evals/evals.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/tradingview/skills/price-refresh/evals/evals.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/tradingview/skills/place-order/evals/evals.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/tradingview/agents/evals/tradingview-onboarding.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/tradingview/agents/evals/ta-guide.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/etf-analysis/assets/templates/etf_analysis_template.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/etf-analysis/skills/etf_analysis/evals/evals.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/etf-analysis/skills/etf_analysis/assets/templates/etf_analysis_template.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

