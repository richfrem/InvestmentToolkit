# JSON Discovery Audit

## Summary

| Category | Count |
|---|---:|
| JSON files discovered | 210 |
| JSONL files discovered | 2 |
| Files classified ALLOWED_AUTHORITATIVE_JSON | 5 |
| Files classified ALLOWED_CONFIGURATION_JSON | 35 |
| Files classified ALLOWED_MODEL_ARTIFACT_JSON | 82 |
| Files classified ALLOWED_SEPARATE_DOMAIN_LEDGER_JSONL | 2 |
| Files classified ALLOWED_TEST_FIXTURE_JSON | 64 |
| Files classified ALLOWED_GENERATED_CACHE_JSON | 3 |
| Files classified MIGRATE_TO_INTELLIGENCE_LEDGER | 1 |
| Files classified GENERATE_FROM_LEDGER_OR_SQLITE | 0 |
| Files classified ARCHIVE_LEGACY_READ_ONLY | 2 |
| Files classified DELETE_AFTER_VERIFIED_ARCHIVE | 0 |
| Files classified OUT_OF_SCOPE_FOR_THIS_PHASE | 16 |
| Files classified UNKNOWN_REQUIRES_REVIEW | 2 |

## High-Risk Findings

- **Nothing has been migrated to SQLite/the intelligence ledger yet.** Phase 3 (the tasks that would actually move JSON data into `intelligence.sqlite` and retire the JSON source) has not started. Every file classified `MIGRATE_TO_INTELLIGENCE_LEDGER` below is still the sole, authoritative copy of its data — none are safe to remove.
- **2 Vite dev-server cache file(s) are git-tracked and not gitignored** (e.g. `investment_screener/frontend/.vite/deps/_metadata.json`). This is a build tool artifact that should never be committed — worth adding to `.gitignore` and removing from git tracking (a separate, low-risk cleanup task, not part of this discovery pass).
- **No JSON/JSONL files currently exist under `temp/`** at audit time — the concern (durable data accidentally living in scratch space) does not apply right now, though `temp/` is gitignored so this can change between runs.
- **2 file(s) remain `UNKNOWN_REQUIRES_REVIEW`** after heuristic classification — see 'Files Requiring Human Review' below.

## Files That Should Legitimately Exist

| File | Classification | Why it stays JSON |
|---|---|---|
| `skills-lock.json` | ALLOWED_CONFIGURATION_JSON | Static configuration/manifest/schema/template — not durable observation data. |
| `plugin-sources.json` | ALLOWED_CONFIGURATION_JSON | Static configuration/manifest/schema/template — not durable observation data. |
| `symlinks.json` | ALLOWED_CONFIGURATION_JSON | Static configuration/manifest/schema/template — not durable observation data. |
| `context/events.jsonl` | ALLOWED_SEPARATE_DOMAIN_LEDGER_JSONL | Its own append-only ledger for a different domain (predictions, agent telemetry) — not merged into observations.jsonl without a separate ADR. |
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
| `investment_screener/backend/data/thesis_breaker_state.json` | ALLOWED_AUTHORITATIVE_JSON | Live portfolio/execution-domain state, outside the qualitative intelligence ledger's scope. |
| `investment_screener/backend/data/predictions.jsonl` | ALLOWED_SEPARATE_DOMAIN_LEDGER_JSONL | Its own append-only ledger for a different domain (predictions, agent telemetry) — not merged into observations.jsonl without a separate ADR. |
| `investment_screener/backend/data/tradingview_alerts_actual.json` | ALLOWED_AUTHORITATIVE_JSON | Live portfolio/execution-domain state, outside the qualitative intelligence ledger's scope. |
| `investment_screener/backend/data/watchlist.json` | ALLOWED_AUTHORITATIVE_JSON | Live portfolio/execution-domain state, outside the qualitative intelligence ledger's scope. |
| `investment_screener/backend/data/account_policy.json` | ALLOWED_AUTHORITATIVE_JSON | Live portfolio/execution-domain state, outside the qualitative intelligence ledger's scope. |
| `investment_screener/backend/data/theses/target-portfolio.json` | ALLOWED_AUTHORITATIVE_JSON | Live portfolio/execution-domain state, outside the qualitative intelligence ledger's scope. |
| `investment_screener/backend/data/projections/COHR.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/BW.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/ANET.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/RGTI.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/CRCL.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/FOTO.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/KRMN.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/VRT.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/ASML.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/PANW.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/CEG.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/AMD.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/LBRT.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/SHAZ.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/RDW.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/BITF.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/NBIS.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/KRC.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/PUMP.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/RKLB.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/HUT.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/CRSP.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/INTC.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/OKLO.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/WYFI.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/CRWD.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/VST.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/QBTS.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/ASTS.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/POET.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/LITE.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/ETHA.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/MSFT.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/CRWV.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/WQTM.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/TSLA.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/BE.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/LLY.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/DXYZ.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/TSM.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/BTDR.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/CACI.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/AAPL.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/APLD.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/SYM.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/PLTR.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/AMZN.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/MU.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/SNDK.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/CELH.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/KOID.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/EQT.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/NKE.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/IONQ.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/SEI.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/HUMN.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/CRM.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/IREN.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/CLSK.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/RIOT.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/GOOG.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/CAKE.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/CIFR.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/DRAM.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/AVGO.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/TEM.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/NOW.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/ZS.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/IBIT.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/CORZ.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/PSIX.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/TEAM.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/TSEM.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/ORCL.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/NVDA.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/COIN.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/EQIX.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/SKHY.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/ALAB.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/CBRS.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/META.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/data/projections/SPCX.json` | ALLOWED_MODEL_ARTIFACT_JSON | Versioned DCF/model output artifact, consumed directly by valuation workflows. |
| `investment_screener/backend/tests/fixtures/edgar_companyfacts_aapl.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `investment_screener/backend/tests/fixtures/target_portfolio.test.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `investment_screener/backend/tests/fixtures/BROKEN_projection.test.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `investment_screener/backend/tests/fixtures/portfolio_with_totals.test.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `investment_screener/backend/tests/fixtures/portfolio.test.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `docs/superpowers/audits/json-discovery-audit.json` | ALLOWED_GENERATED_CACHE_JSON | Regenerable cache — safe to exist as long as its generating source is known. |
| `docs/superpowers/audits/allowed-json-register.json` | ALLOWED_GENERATED_CACHE_JSON | Regenerable cache — safe to exist as long as its generating source is known. |
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
| `plugins/portfolio-advisor/skills/thesis-challenge-bundler/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/portfolio-advisor/skills/set-thesis-breakers/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/portfolio-advisor/skills/adversarial-review/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/portfolio-advisor/skills/daily-brief/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/portfolio-advisor/skills/calibrate-targets/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/portfolio-advisor/skills/norberts-gambit/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/portfolio-advisor/skills/daily-loop/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/portfolio-advisor/skills/x-news-sweep/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/portfolio-advisor/skills/update-portfolio-targets/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/portfolio-advisor/skills/update-portfolio-targets/assets/templates/target_portfolio_template.json` | ALLOWED_CONFIGURATION_JSON | Static configuration/manifest/schema/template — not durable observation data. |
| `plugins/portfolio-advisor/skills/ytd-return/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/portfolio-advisor/skills/ytd-return/assets/templates/ytd_performance_report_template.json` | ALLOWED_CONFIGURATION_JSON | Static configuration/manifest/schema/template — not durable observation data. |
| `plugins/portfolio-advisor/skills/13f-analyze/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/portfolio-advisor/agents/evals/weekly-review-agent.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/portfolio-advisor/agents/evals/thesis-review-agent.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/portfolio-advisor/agents/evals/risk-officer-agent.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/portfolio-advisor/agents/evals/portfolio-advisor-orchestrator.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/portfolio-advisor/agents/evals/single-stock-advisor.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/portfolio-advisor/agents/evals/data-quality-agent.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/portfolio-advisor/agents/evals/red-team-agent.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/portfolio-advisor/agents/evals/daily-loop-agent.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/stock-valuation/.claude-plugin/plugin.json` | ALLOWED_CONFIGURATION_JSON | Static configuration/manifest/schema/template — not durable observation data. |
| `plugins/stock-valuation/assets/templates/projection_template.json` | ALLOWED_CONFIGURATION_JSON | Static configuration/manifest/schema/template — not durable observation data. |
| `plugins/stock-valuation/skills/valuation-math-validation/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/stock-valuation/skills/stock_valuation/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/stock-valuation/skills/stock_valuation/assets/templates/projection_template.json` | ALLOWED_CONFIGURATION_JSON | Static configuration/manifest/schema/template — not durable observation data. |
| `plugins/stock-valuation/skills/stock_valuation/references/examples/example_NVDA_placeholder.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/stock-valuation/skills/stock_valuation/references/examples/example_NVDA_2026-05-02.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/stock-valuation/skills/stock_valuation/references/examples/example_GOOG_2026-05-02.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/stock-valuation/skills/stock_valuation/references/examples/example_PANW_2026-05-02.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/stock-valuation/skills/forward-valuation-challenge/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/stock-valuation/skills/stock-research/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/stock-valuation/scripts/cache/SKHY.json` | ALLOWED_GENERATED_CACHE_JSON | Regenerable cache — safe to exist as long as its generating source is known. |
| `plugins/toolkit-manager/.claude-plugin/plugin.json` | ALLOWED_CONFIGURATION_JSON | Static configuration/manifest/schema/template — not durable observation data. |
| `plugins/toolkit-manager/skills/run-screener/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/toolkit-manager/agents/evals/toolkit-onboarding-guide.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/tradingview/.claude-plugin/plugin.json` | ALLOWED_CONFIGURATION_JSON | Static configuration/manifest/schema/template — not durable observation data. |
| `plugins/tradingview/skills/pine-inject/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/tradingview/skills/tv-save-indicator/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/tradingview/skills/ta-red-team/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/tradingview/skills/chart-snapshot/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/tradingview/skills/modify-order/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/tradingview/skills/tv-add-indicator/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/tradingview/skills/cancel-order/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/tradingview/skills/ta-snapshot/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/tradingview/skills/tv-setup/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/tradingview/skills/tv-change-symbol/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/tradingview/skills/ta-daily-sweep/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/tradingview/skills/tv-change-type/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/tradingview/skills/alert-list/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/tradingview/skills/alert-sync/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/tradingview/skills/author-pine-script/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/tradingview/skills/tv-manage-watchlists/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/tradingview/skills/get-orders/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/tradingview/skills/tv-chart-setup/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/tradingview/skills/technical-analysis-expert/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/tradingview/skills/tv-portfolio-sync/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/tradingview/skills/price-refresh/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/tradingview/skills/place-order/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/tradingview/agents/evals/tradingview-onboarding.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/tradingview/agents/evals/ta-guide.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |
| `plugins/etf-analysis/assets/templates/etf_analysis_template.json` | ALLOWED_CONFIGURATION_JSON | Static configuration/manifest/schema/template — not durable observation data. |
| `plugins/etf-analysis/skills/etf_analysis/evals/evals.json` | ALLOWED_TEST_FIXTURE_JSON | Test/eval fixture or prompt reference example, not application state. |

## Files That Likely Should Not Exist Long-Term

| File | Reason | Required next action |
|---|---|---|
| `investment_screener/backend/data/ta-sweep-results.json` | Durable observation data that belongs in the intelligence ledger once Phase 3 migration tooling runs. | NOT_MIGRATED — still the only copy of this data; do not remove |
| `investment_screener/frontend/.vite/deps/_metadata.json` | Build-tool cache artifact, checked into git by mistake. | Add to .gitignore, git rm --cached (separate low-risk task) |
| `investment_screener/frontend/.vite/deps/package.json` | Build-tool cache artifact, checked into git by mistake. | Add to .gitignore, git rm --cached (separate low-risk task) |

## Files Requiring Human Review

| File | Reason | Suggested next action |
|---|---|---|
| `plugins/portfolio-advisor/references/standing-decisions.json` | No known heuristic match | INVESTIGATE |
| `plugins/tradingview/assets/pinescript-indicators/registry.json` | No known heuristic match | INVESTIGATE |

## Temp Folder Analysis

No `.json`/`.jsonl` files currently exist under `temp/` (which is gitignored scratch space per `.gitignore`). Re-run this audit periodically if `temp/` is suspected of accumulating durable data over time — nothing to report as of 2026-07-18T23:17:17Z.

## Per-File Inventory

### skills-lock.json

**Classification:** ALLOWED_CONFIGURATION_JSON

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

### context/events.jsonl

**Classification:** ALLOWED_SEPARATE_DOMAIN_LEDGER_JSONL

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/py_services/evolution_events.py:9
- investment_screener/backend/tests/py_services/test_evolution_events_schema_round_trips_jsonl.py:108
- investment_screener/backend/tests/py_services/test_evolution_events_schema_round_trips_jsonl.py:124
- investment_screener/backend/tests/py_services/test_evolution_events_schema_round_trips_jsonl.py:148
- investment_screener/backend/tests/py_services/test_evolution_events_schema_round_trips_jsonl.py:152
- investment_screener/backend/tests/py_services/test_evolution_events_schema_round_trips_jsonl.py:175
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:34
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:40
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:47
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:50
- investment_screener/backend/tests/py_services/test_alert_metadata_round_trips_jsonl.py:7

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
- investment_screener/backend/py_services/prediction_ledger.py:58
- investment_screener/backend/py_services/prediction_ledger.py:160

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
- investment_screener/backend/py_services/audit_json_usage.py:401

### .claude-plugin/marketplace.json

**Classification:** ALLOWED_CONFIGURATION_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:125

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
- investment_screener/backend/py_services/audit_json_usage.py:401

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
- investment_screener/backend/py_services/audit_json_usage.py:402

### investment_screener/frontend/package.json

**Classification:** ALLOWED_CONFIGURATION_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- run_tests.py:17
- run_investment_toolkit.py:16
- investment_screener/backend/py_services/audit_json_usage.py:401

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
- investment_screener/backend/py_services/audit_json_usage.py:401

### investment_screener/backend/tsconfig.json

**Classification:** ALLOWED_CONFIGURATION_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/backend/data/thesis_breaker_state.json

**Classification:** ALLOWED_AUTHORITATIVE_JSON

**Known producers:**
- investment_screener/backend/tests/py_services/test_harvest_predictions.py:248
- investment_screener/backend/tests/py_services/test_rebalancer.py:475
- investment_screener/backend/tests/py_services/test_rebalancer.py:552

**Known consumers:**
- investment_screener/backend/py_services/order_risk_gates.py:40
- investment_screener/backend/py_services/order_risk_gates.py:49
- investment_screener/backend/py_services/order_risk_gates.py:132
- investment_screener/backend/py_services/order_risk_gates.py:173
- investment_screener/backend/py_services/order_risk_gates.py:460
- investment_screener/backend/py_services/order_risk_gates.py:473
- investment_screener/backend/py_services/order_risk_gates.py:485
- investment_screener/backend/py_services/order_risk_gates.py:506
- investment_screener/backend/py_services/rebalancer.py:61
- investment_screener/backend/py_services/rebalancer.py:514
- investment_screener/backend/py_services/rebalancer.py:659
- investment_screener/backend/py_services/rebalancer.py:704
- investment_screener/backend/py_services/harvest_predictions.py:9
- investment_screener/backend/py_services/harvest_predictions.py:157
- investment_screener/backend/py_services/harvest_predictions.py:219
- investment_screener/backend/py_services/thesis_breakers.py:12
- investment_screener/backend/py_services/thesis_breakers.py:19
- investment_screener/backend/py_services/thesis_breakers.py:56
- investment_screener/backend/py_services/thesis_breakers.py:315
- investment_screener/backend/py_services/thesis_breakers.py:428
- investment_screener/backend/py_services/thesis_breakers.py:437
- investment_screener/backend/py_services/risk_officer.py:10
- investment_screener/backend/tests/py_services/test_thesis_breakers.py:310
- investment_screener/backend/tests/py_services/test_thesis_breakers.py:366
- investment_screener/backend/tests/py_services/test_thesis_breakers.py:412
- investment_screener/backend/tests/py_services/test_harvest_predictions.py:247
- investment_screener/backend/tests/py_services/test_rebalancer.py:445
- investment_screener/backend/tests/py_services/test_order_risk_gates_checks_breaker_veto.py:3

### investment_screener/backend/data/predictions.jsonl

**Classification:** ALLOWED_SEPARATE_DOMAIN_LEDGER_JSONL

**Known producers:**
- investment_screener/backend/tests/py_services/test_harvest_predictions.py:36
- investment_screener/backend/tests/py_services/test_harvest_predictions.py:44
- investment_screener/backend/tests/py_services/test_harvest_predictions.py:53
- investment_screener/backend/tests/py_services/test_generate_track_record_report.py:48
- investment_screener/backend/tests/py_services/test_backtest_prediction_ledger_correlation.py:51

**Known consumers:**
- investment_screener/backend/py_services/earnings_expectations.py:74
- investment_screener/backend/py_services/earnings_expectations.py:307
- investment_screener/backend/py_services/earnings_expectations.py:314
- investment_screener/backend/py_services/grade_predictions.py:10
- investment_screener/backend/py_services/grade_predictions.py:63
- investment_screener/backend/py_services/audit_json_usage.py:364
- investment_screener/backend/py_services/generate_track_record_report.py:8
- investment_screener/backend/py_services/prediction_ledger.py:9
- investment_screener/backend/py_services/prediction_ledger.py:56
- investment_screener/backend/py_services/prediction_ledger.py:92
- investment_screener/backend/py_services/backtest_harness.py:26
- investment_screener/backend/py_services/backtest_harness.py:74
- investment_screener/backend/py_services/backtest_harness.py:534
- investment_screener/backend/py_services/harvest_predictions.py:10
- investment_screener/backend/tests/py_services/test_earnings_expectation_claim_schema_round_trips_jsonl.py:5
- investment_screener/backend/tests/py_services/test_prediction_ledger.py:28
- investment_screener/backend/tests/py_services/test_prediction_ledger.py:35
- investment_screener/backend/tests/py_services/test_harvest_earnings_expectations_logs_consensus_change.py:7
- investment_screener/backend/tests/py_services/test_harvest_earnings_expectations_logs_consensus_change.py:72
- investment_screener/backend/tests/py_services/test_harvest_earnings_expectations_logs_consensus_change.py:123
- investment_screener/backend/tests/py_services/test_harvest_earnings_expectations_logs_consensus_change.py:194
- investment_screener/backend/tests/py_services/test_harvest_earnings_expectations_logs_consensus_change.py:236
- investment_screener/backend/tests/py_services/test_evolution_integration_with_e3_prediction_ledger.py:75
- investment_screener/backend/tests/py_services/test_harvest_earnings_expectations_path_isolation.py:2
- investment_screener/backend/tests/py_services/test_harvest_earnings_expectations_path_isolation.py:19
- investment_screener/backend/tests/py_services/test_harvest_earnings_expectations_path_isolation.py:29
- investment_screener/backend/tests/py_services/test_harvest_earnings_expectations_path_isolation.py:50
- investment_screener/backend/tests/py_services/test_harvest_earnings_expectations_path_isolation.py:57
- investment_screener/backend/tests/py_services/test_harvest_earnings_expectations_path_isolation.py:61
- investment_screener/backend/tests/py_services/test_harvest_earnings_expectations_null_consensus_degrades_gracefully.py:7
- investment_screener/backend/tests/py_services/test_harvest_earnings_expectations_null_consensus_degrades_gracefully.py:42
- investment_screener/backend/tests/py_services/test_harvest_earnings_expectations_null_consensus_degrades_gracefully.py:81
- investment_screener/backend/tests/py_services/test_harvest_earnings_expectations_null_consensus_degrades_gracefully.py:100
- investment_screener/backend/tests/py_services/test_harvest_earnings_expectations_null_consensus_degrades_gracefully.py:113
- investment_screener/backend/tests/py_services/test_harvest_earnings_expectations_null_consensus_degrades_gracefully.py:150
- investment_screener/backend/tests/py_services/test_harvest_earnings_expectations_null_consensus_degrades_gracefully.py:160
- investment_screener/backend/tests/py_services/test_harvest_earnings_expectations_null_consensus_degrades_gracefully.py:191
- investment_screener/backend/tests/py_services/test_harvest_earnings_expectations_null_consensus_degrades_gracefully.py:198
- investment_screener/backend/tests/py_services/test_harvest_earnings_expectations_null_consensus_degrades_gracefully.py:210
- investment_screener/backend/tests/py_services/test_harvest_earnings_expectations_null_consensus_degrades_gracefully.py:214
- investment_screener/backend/tests/py_services/test_harvest_earnings_expectations_dedup_on_unchanged_consensus.py:3
- investment_screener/backend/tests/py_services/test_harvest_earnings_expectations_dedup_on_unchanged_consensus.py:8
- investment_screener/backend/tests/py_services/test_harvest_earnings_expectations_dedup_on_unchanged_consensus.py:33
- investment_screener/backend/tests/py_services/test_harvest_earnings_expectations_dedup_on_unchanged_consensus.py:71
- investment_screener/backend/tests/py_services/test_harvest_earnings_expectations_dedup_on_unchanged_consensus.py:124
- investment_screener/backend/tests/py_services/test_harvest_earnings_expectations_dedup_on_unchanged_consensus.py:154
- investment_screener/backend/tests/py_services/test_harvest_earnings_expectations_dedup_on_unchanged_consensus.py:202
- investment_screener/backend/tests/py_services/test_harvest_earnings_expectations_dedup_on_unchanged_consensus.py:208
- investment_screener/backend/tests/py_services/test_harvest_earnings_expectations_dedup_on_unchanged_consensus.py:214
- investment_screener/backend/tests/py_services/test_harvest_earnings_expectations_dedup_on_unchanged_consensus.py:255
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:113
- investment_screener/backend/tests/py_services/test_harvest_predictions.py:42
- investment_screener/backend/tests/py_services/test_harvest_predictions.py:48
- investment_screener/backend/tests/py_services/test_harvest_predictions.py:126
- investment_screener/backend/tests/py_services/test_harvest_predictions.py:135
- investment_screener/backend/tests/py_services/test_harvest_predictions.py:142
- investment_screener/backend/tests/py_services/test_harvest_predictions.py:151
- investment_screener/backend/tests/py_services/test_harvest_predictions.py:168
- investment_screener/backend/tests/py_services/test_harvest_predictions.py:176
- investment_screener/backend/tests/py_services/test_harvest_predictions.py:236
- investment_screener/backend/tests/py_services/test_harvest_predictions.py:260
- investment_screener/backend/tests/py_services/test_generate_track_record_report.py:47
- investment_screener/backend/tests/py_services/test_prediction_ledger_validate.py:12
- investment_screener/backend/tests/py_services/test_grade_predictions.py:72
- investment_screener/backend/tests/py_services/test_grade_predictions.py:88
- investment_screener/backend/tests/py_services/test_backtest_prediction_ledger_correlation.py:50
- investment_screener/backend/tests/py_services/test_backtest_prediction_ledger_correlation.py:84
- investment_screener/backend/tests/py_services/test_earnings_expectation_claim_round_trips_ledger.py:36
- investment_screener/backend/tests/py_services/test_earnings_expectation_claim_round_trips_ledger.py:179
- investment_screener/backend/tests/py_services/test_link_alert_to_e3_claim.py:20

### investment_screener/backend/data/tradingview_alerts_actual.json

**Classification:** ALLOWED_AUTHORITATIVE_JSON

**Known producers:**
- plugins/tradingview/scripts/tv_list_alerts.py:74
- plugins/tradingview/skills/alert-list/scripts/tv_list_alerts.py:74

**Known consumers:**
- investment_screener/backend/py_services/audit_json_usage.py:386
- plugins/tradingview/tests/test_tv_list_alerts.py:20
- plugins/tradingview/scripts/tv_list_alerts.py:10
- plugins/tradingview/scripts/tv_list_alerts.py:38
- plugins/tradingview/skills/alert-list/scripts/tv_list_alerts.py:10
- plugins/tradingview/skills/alert-list/scripts/tv_list_alerts.py:38

### investment_screener/backend/data/watchlist.json

**Classification:** ALLOWED_AUTHORITATIVE_JSON

**Known producers:**
- investment_screener/backend/tests/py_services/test_overnight_gaps.py:48
- investment_screener/backend/tests/py_services/test_overnight_gaps.py:60
- investment_screener/backend/tests/py_services/test_overnight_gaps.py:71

**Known consumers:**
- investment_screener/backend/py_services/overnight_gaps.py:53
- investment_screener/backend/py_services/overnight_gaps.py:79
- investment_screener/backend/py_services/overnight_gaps.py:99
- investment_screener/backend/py_services/overnight_gaps.py:153
- investment_screener/backend/py_services/audit_json_usage.py:383
- investment_screener/backend/tests/py_services/test_overnight_gaps.py:47
- investment_screener/backend/tests/py_services/test_overnight_gaps.py:59
- investment_screener/backend/tests/py_services/test_overnight_gaps.py:70
- plugins/portfolio-advisor/scripts/weekly_review.py:32
- plugins/tradingview/scripts/watchlist_manager.py:7
- plugins/tradingview/scripts/watchlist_manager.py:15
- plugins/tradingview/scripts/watchlist_manager.py:31
- plugins/tradingview/scripts/watchlist_manager.py:68
- plugins/tradingview/scripts/watchlist_manager.py:110
- tradingview-cdp/cli.js:13
- tradingview-cdp/cli.js:70
- investment_screener/backend/src/utils/paths.ts:28
- investment_screener/backend/src/services/WatchlistService.ts:22
- investment_screener/backend/src/services/WatchlistService.ts:25

### investment_screener/backend/data/ta-sweep-results.json

**Classification:** MIGRATE_TO_INTELLIGENCE_LEDGER

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/py_services/compute_conviction_scores.py:67
- investment_screener/backend/py_services/compute_conviction_scores.py:283
- investment_screener/backend/py_services/daily_brief.py:37
- investment_screener/backend/py_services/daily_brief.py:48
- investment_screener/backend/py_services/daily_brief.py:407
- investment_screener/backend/py_services/audit_json_usage.py:278
- investment_screener/backend/py_services/audit_json_usage.py:376
- investment_screener/backend/py_services/evolution_events.py:31
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:52
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:101
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:118
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:144
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:158
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:161
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:183
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:203
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:209
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:221
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:223
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:228
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:240
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:246
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:257
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:263
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:275
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:277
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:281
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:291
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:296
- plugins/portfolio-advisor/scripts/daily_brief.py:37
- plugins/portfolio-advisor/scripts/daily_brief.py:48
- plugins/portfolio-advisor/scripts/daily_brief.py:407
- plugins/portfolio-advisor/skills/daily-brief/scripts/daily_brief.py:37
- plugins/portfolio-advisor/skills/daily-brief/scripts/daily_brief.py:48
- plugins/portfolio-advisor/skills/daily-brief/scripts/daily_brief.py:407
- plugins/tradingview/tests/test_ta_sweep_batch.py:134
- plugins/tradingview/tests/test_ta_sweep_batch.py:155
- plugins/tradingview/tests/test_ta_sweep_batch.py:159
- plugins/tradingview/tests/test_ta_sweep_batch.py:173
- plugins/tradingview/tests/test_ta_sweep_batch.py:177
- plugins/tradingview/scripts/ta_sweep_batch.py:40
- plugins/tradingview/skills/ta-daily-sweep/scripts/ta_sweep_batch.py:40

### investment_screener/backend/data/account_policy.json

**Classification:** ALLOWED_AUTHORITATIVE_JSON

**Known producers:**
- investment_screener/backend/tests/py_services/test_rebalancer.py:476

**Known consumers:**
- investment_screener/backend/py_services/order_risk_gates.py:128
- investment_screener/backend/py_services/order_risk_gates.py:172
- investment_screener/backend/py_services/order_risk_gates.py:327
- investment_screener/backend/py_services/order_risk_gates.py:425
- investment_screener/backend/py_services/rebalancer.py:62
- investment_screener/backend/py_services/rebalancer.py:314
- investment_screener/backend/py_services/rebalancer.py:464
- investment_screener/backend/py_services/rebalancer.py:660
- investment_screener/backend/py_services/audit_json_usage.py:385
- investment_screener/backend/tests/py_services/test_rebalancer.py:446
- investment_screener/backend/py_services/migrations/remove_drift_threshold_fields.py:9
- investment_screener/backend/py_services/migrations/remove_drift_threshold_fields.py:55
- investment_screener/backend/src/utils/zod-schemas.ts:231
- investment_screener/backend/src/services/ThesisService.ts:40
- investment_screener/backend/src/services/ThesisService.ts:59
- investment_screener/backend/src/services/ThesisService.ts:127

### investment_screener/backend/data/theses/target-portfolio.json

**Classification:** ALLOWED_AUTHORITATIVE_JSON

**Known producers:**
- investment_screener/backend/tests/py_services/test_market_regime.py:97
- investment_screener/backend/tests/py_services/test_market_regime.py:111
- investment_screener/backend/tests/py_services/test_market_regime.py:119
- investment_screener/backend/tests/py_services/test_market_regime.py:310
- investment_screener/backend/tests/py_services/test_verify_thesis_sync.py:33
- investment_screener/backend/tests/py_services/test_verify_thesis_sync.py:59
- investment_screener/backend/tests/py_services/test_verify_thesis_sync.py:84
- investment_screener/backend/tests/py_services/test_verify_thesis_sync.py:110
- investment_screener/backend/tests/py_services/test_verify_thesis_sync.py:137
- investment_screener/backend/tests/py_services/test_lock_and_normalize_targets.py:32
- investment_screener/backend/tests/py_services/test_harvest_predictions.py:253
- investment_screener/backend/tests/py_services/test_rebalancer.py:450
- investment_screener/backend/tests/py_services/test_rebalancer.py:510
- investment_screener/backend/tests/py_services/test_update_price_levels.py:125
- plugins/portfolio-advisor/scripts/sync_portfolio_roles.py:124

**Known consumers:**
- investment_screener/backend/py_services/compute_conviction_scores.py:26
- investment_screener/backend/py_services/compute_conviction_scores.py:69
- investment_screener/backend/py_services/compute_conviction_scores.py:344
- investment_screener/backend/py_services/compute_conviction_scores.py:349
- investment_screener/backend/py_services/generate_reports.py:16
- investment_screener/backend/py_services/market_regime.py:67
- investment_screener/backend/py_services/market_regime.py:164
- investment_screener/backend/py_services/market_regime.py:168
- investment_screener/backend/py_services/market_regime.py:176
- investment_screener/backend/py_services/market_regime.py:523
- investment_screener/backend/py_services/order_risk_gates.py:10
- investment_screener/backend/py_services/order_risk_gates.py:41
- investment_screener/backend/py_services/order_risk_gates.py:134
- investment_screener/backend/py_services/order_risk_gates.py:135
- investment_screener/backend/py_services/order_risk_gates.py:174
- investment_screener/backend/py_services/order_risk_gates.py:232
- investment_screener/backend/py_services/order_risk_gates.py:238
- investment_screener/backend/py_services/order_risk_gates.py:419
- investment_screener/backend/py_services/order_risk_gates.py:420
- investment_screener/backend/py_services/order_risk_gates.py:486
- investment_screener/backend/py_services/daily_brief.py:38
- investment_screener/backend/py_services/daily_brief.py:109
- investment_screener/backend/py_services/daily_brief.py:460
- investment_screener/backend/py_services/update_thesis.py:57
- investment_screener/backend/py_services/update_thesis.py:74
- investment_screener/backend/py_services/update_thesis.py:205
- investment_screener/backend/py_services/update_thesis.py:238
- investment_screener/backend/py_services/earnings_expectations.py:312
- investment_screener/backend/py_services/earnings_expectations.py:334
- investment_screener/backend/py_services/earnings_expectations.py:339
- investment_screener/backend/py_services/earnings_expectations.py:340
- investment_screener/backend/py_services/earnings_expectations.py:627
- investment_screener/backend/py_services/earnings_expectations.py:628
- investment_screener/backend/py_services/generate_review_json.py:33
- investment_screener/backend/py_services/generate_review_json.py:51
- investment_screener/backend/py_services/generate_review_json.py:123
- investment_screener/backend/py_services/lock_and_normalize_targets.py:17
- investment_screener/backend/py_services/lock_and_normalize_targets.py:87
- investment_screener/backend/py_services/lock_and_normalize_targets.py:172
- investment_screener/backend/py_services/rebalancer.py:58
- investment_screener/backend/py_services/rebalancer.py:82
- investment_screener/backend/py_services/rebalancer.py:160
- investment_screener/backend/py_services/rebalancer.py:315
- investment_screener/backend/py_services/rebalancer.py:465
- investment_screener/backend/py_services/rebalancer.py:551
- investment_screener/backend/py_services/rebalancer.py:656
- investment_screener/backend/py_services/audit_json_usage.py:384
- investment_screener/backend/py_services/risk_engine.py:59
- investment_screener/backend/py_services/risk_engine.py:271
- investment_screener/backend/py_services/risk_engine.py:278
- investment_screener/backend/py_services/risk_engine.py:454
- investment_screener/backend/py_services/generate_portfolio_blueprint.py:8
- investment_screener/backend/py_services/generate_portfolio_blueprint.py:21
- investment_screener/backend/py_services/generate_portfolio_blueprint.py:41
- investment_screener/backend/py_services/generate_portfolio_blueprint.py:160
- investment_screener/backend/py_services/generate_portfolio_blueprint.py:403
- investment_screener/backend/py_services/verify_thesis_sync.py:9
- investment_screener/backend/py_services/verify_thesis_sync.py:46
- investment_screener/backend/py_services/verify_thesis_sync.py:55
- investment_screener/backend/py_services/verify_thesis_sync.py:85
- investment_screener/backend/py_services/verify_thesis_sync.py:86
- investment_screener/backend/py_services/verify_thesis_sync.py:88
- investment_screener/backend/py_services/verify_thesis_sync.py:94
- investment_screener/backend/py_services/verify_thesis_sync.py:96
- investment_screener/backend/py_services/generate_grok_prompt.py:32
- investment_screener/backend/py_services/generate_grok_prompt.py:100
- investment_screener/backend/py_services/backtest_harness.py:23
- investment_screener/backend/py_services/backtest_harness.py:24
- investment_screener/backend/py_services/backtest_harness.py:102
- investment_screener/backend/py_services/backtest_harness.py:114
- investment_screener/backend/py_services/backtest_harness.py:118
- investment_screener/backend/py_services/apply_catalyst.py:44
- investment_screener/backend/py_services/apply_catalyst.py:249
- investment_screener/backend/py_services/apply_catalyst.py:258
- investment_screener/backend/py_services/system_health.py:89
- investment_screener/backend/py_services/system_health.py:101
- investment_screener/backend/py_services/system_health.py:103
- investment_screener/backend/py_services/system_health.py:105
- investment_screener/backend/py_services/system_health.py:114
- investment_screener/backend/py_services/system_health.py:118
- investment_screener/backend/py_services/harvest_predictions.py:158
- investment_screener/backend/py_services/thesis_breakers.py:8
- investment_screener/backend/py_services/thesis_breakers.py:11
- investment_screener/backend/py_services/thesis_breakers.py:55
- investment_screener/backend/py_services/thesis_breakers.py:116
- investment_screener/backend/py_services/thesis_breakers.py:178
- investment_screener/backend/py_services/thesis_breakers.py:260
- investment_screener/backend/py_services/thesis_breakers.py:314
- investment_screener/backend/py_services/thesis_breakers.py:389
- investment_screener/backend/py_services/thesis_breakers.py:433
- investment_screener/backend/py_services/thesis_breakers.py:436
- investment_screener/backend/py_services/thesis_breakers.py:448
- investment_screener/backend/py_services/thesis_breakers.py:501
- investment_screener/backend/tests/py_services/test_market_regime.py:96
- investment_screener/backend/tests/py_services/test_market_regime.py:110
- investment_screener/backend/tests/py_services/test_market_regime.py:118
- investment_screener/backend/tests/py_services/test_market_regime.py:309
- investment_screener/backend/tests/py_services/test_risk_engine.py:371
- investment_screener/backend/tests/py_services/test_risk_engine.py:414
- investment_screener/backend/tests/py_services/test_thesis_breakers.py:309
- investment_screener/backend/tests/py_services/test_thesis_breakers.py:365
- investment_screener/backend/tests/py_services/test_thesis_breakers.py:411
- investment_screener/backend/tests/py_services/test_thesis_breakers.py:443
- investment_screener/backend/tests/py_services/test_thesis_breakers.py:453
- investment_screener/backend/tests/py_services/test_thesis_breakers.py:463
- investment_screener/backend/tests/py_services/test_verify_thesis_sync.py:25
- investment_screener/backend/tests/py_services/test_verify_thesis_sync.py:32
- investment_screener/backend/tests/py_services/test_verify_thesis_sync.py:58
- investment_screener/backend/tests/py_services/test_verify_thesis_sync.py:83
- investment_screener/backend/tests/py_services/test_verify_thesis_sync.py:109
- investment_screener/backend/tests/py_services/test_verify_thesis_sync.py:136
- investment_screener/backend/tests/py_services/test_harvest_earnings_expectations_dedup_on_unchanged_consensus.py:220
- investment_screener/backend/tests/py_services/test_lock_and_normalize_targets.py:22
- investment_screener/backend/tests/py_services/test_lock_and_normalize_targets.py:31
- investment_screener/backend/tests/py_services/test_lock_and_normalize_targets.py:54
- investment_screener/backend/tests/py_services/test_harvest_predictions.py:252
- investment_screener/backend/tests/py_services/test_order_risk_gates_builds_portfolio_state.py:5
- investment_screener/backend/tests/py_services/test_order_risk_gates_builds_portfolio_state.py:31
- investment_screener/backend/tests/py_services/test_order_risk_gates_builds_portfolio_state.py:44
- investment_screener/backend/tests/py_services/test_order_risk_gates_builds_portfolio_state.py:45
- investment_screener/backend/tests/py_services/test_order_risk_gates_builds_portfolio_state.py:57
- investment_screener/backend/tests/py_services/test_order_risk_gates_builds_portfolio_state.py:84
- investment_screener/backend/tests/py_services/test_order_risk_gates_builds_portfolio_state.py:97
- investment_screener/backend/tests/py_services/test_order_risk_gates_builds_portfolio_state.py:99
- investment_screener/backend/tests/py_services/test_rebalancer.py:442
- investment_screener/backend/tests/py_services/test_get_earnings_context_returns_prior_beat_rate.py:175
- investment_screener/backend/tests/py_services/test_update_price_levels.py:9
- investment_screener/backend/tests/py_services/test_update_price_levels.py:68
- investment_screener/backend/tests/py_services/test_update_price_levels.py:124
- investment_screener/backend/tests/py_services/test_update_price_levels.py:344
- investment_screener/backend/tests/py_services/test_update_price_levels.py:452
- investment_screener/backend/tests/py_services/test_order_risk_gates_checks_breaker_veto.py:4
- investment_screener/backend/tests/py_services/test_backtest_extract_historical_targets.py:44
- investment_screener/backend/py_services/migrations/remove_drift_threshold_fields.py:8
- investment_screener/backend/py_services/migrations/remove_drift_threshold_fields.py:32
- plugins/portfolio-advisor/scripts/update_targets.py:3
- plugins/portfolio-advisor/scripts/update_targets.py:38
- plugins/portfolio-advisor/scripts/update_targets.py:48
- plugins/portfolio-advisor/scripts/update_targets.py:258
- plugins/portfolio-advisor/scripts/update_targets.py:295
- plugins/portfolio-advisor/scripts/generate_review.py:27
- plugins/portfolio-advisor/scripts/generate_reports.py:16
- plugins/portfolio-advisor/scripts/daily_brief.py:38
- plugins/portfolio-advisor/scripts/daily_brief.py:109
- plugins/portfolio-advisor/scripts/daily_brief.py:460
- plugins/portfolio-advisor/scripts/update_thesis.py:57
- plugins/portfolio-advisor/scripts/update_thesis.py:74
- plugins/portfolio-advisor/scripts/update_thesis.py:205
- plugins/portfolio-advisor/scripts/update_thesis.py:238
- plugins/portfolio-advisor/scripts/generate_review_json.py:33
- plugins/portfolio-advisor/scripts/generate_review_json.py:51
- plugins/portfolio-advisor/scripts/generate_review_json.py:123
- plugins/portfolio-advisor/scripts/validate_weights.py:9
- plugins/portfolio-advisor/scripts/validate_weights.py:14
- plugins/portfolio-advisor/scripts/validate_weights.py:21
- plugins/portfolio-advisor/scripts/validate_weights.py:31
- plugins/portfolio-advisor/scripts/validate_weights.py:69
- plugins/portfolio-advisor/scripts/validate_weights.py:115
- plugins/portfolio-advisor/scripts/scan_opportunities.py:36
- plugins/portfolio-advisor/scripts/verify_refresh.py:6
- plugins/portfolio-advisor/scripts/verify_refresh.py:22
- plugins/portfolio-advisor/scripts/verify_refresh.py:47
- plugins/portfolio-advisor/scripts/verify_refresh.py:48
- plugins/portfolio-advisor/scripts/update_price_levels.py:6
- plugins/portfolio-advisor/scripts/update_price_levels.py:32
- plugins/portfolio-advisor/scripts/update_price_levels.py:226
- plugins/portfolio-advisor/scripts/update_price_levels.py:281
- plugins/portfolio-advisor/scripts/update_price_levels.py:285
- plugins/portfolio-advisor/scripts/weekly_review.py:30
- plugins/portfolio-advisor/scripts/generate_sub_strategy_blocks.py:26
- plugins/portfolio-advisor/scripts/generate_portfolio_blueprint.py:8
- plugins/portfolio-advisor/scripts/generate_portfolio_blueprint.py:21
- plugins/portfolio-advisor/scripts/generate_portfolio_blueprint.py:41
- plugins/portfolio-advisor/scripts/generate_portfolio_blueprint.py:160
- plugins/portfolio-advisor/scripts/generate_portfolio_blueprint.py:403
- plugins/portfolio-advisor/scripts/generate_grok_prompt.py:32
- plugins/portfolio-advisor/scripts/generate_grok_prompt.py:100
- plugins/portfolio-advisor/scripts/sync_portfolio_roles.py:1
- plugins/portfolio-advisor/scripts/sync_portfolio_roles.py:16
- plugins/portfolio-advisor/scripts/sync_portfolio_roles.py:84
- plugins/portfolio-advisor/scripts/sync_portfolio_roles.py:125
- plugins/portfolio-advisor/scripts/apply_catalyst.py:44
- plugins/portfolio-advisor/scripts/apply_catalyst.py:249
- plugins/portfolio-advisor/scripts/apply_catalyst.py:258
- plugins/portfolio-advisor/skills/thesis-review/scripts/update_targets.py:3
- plugins/portfolio-advisor/skills/thesis-review/scripts/update_targets.py:38
- plugins/portfolio-advisor/skills/thesis-review/scripts/update_targets.py:48
- plugins/portfolio-advisor/skills/thesis-review/scripts/update_targets.py:258
- plugins/portfolio-advisor/skills/thesis-review/scripts/update_targets.py:295
- plugins/portfolio-advisor/skills/thesis-review/scripts/validate_weights.py:9
- plugins/portfolio-advisor/skills/thesis-review/scripts/validate_weights.py:14
- plugins/portfolio-advisor/skills/thesis-review/scripts/validate_weights.py:21
- plugins/portfolio-advisor/skills/thesis-review/scripts/validate_weights.py:31
- plugins/portfolio-advisor/skills/thesis-review/scripts/validate_weights.py:69
- plugins/portfolio-advisor/skills/thesis-review/scripts/validate_weights.py:115
- plugins/portfolio-advisor/skills/thesis-review/scripts/generate_portfolio_blueprint.py:8
- plugins/portfolio-advisor/skills/thesis-review/scripts/generate_portfolio_blueprint.py:21
- plugins/portfolio-advisor/skills/thesis-review/scripts/generate_portfolio_blueprint.py:41
- plugins/portfolio-advisor/skills/thesis-review/scripts/generate_portfolio_blueprint.py:160
- plugins/portfolio-advisor/skills/thesis-review/scripts/generate_portfolio_blueprint.py:403
- plugins/portfolio-advisor/skills/strategic-review/scripts/update_targets.py:3
- plugins/portfolio-advisor/skills/strategic-review/scripts/update_targets.py:38
- plugins/portfolio-advisor/skills/strategic-review/scripts/update_targets.py:48
- plugins/portfolio-advisor/skills/strategic-review/scripts/update_targets.py:258
- plugins/portfolio-advisor/skills/strategic-review/scripts/update_targets.py:295
- plugins/portfolio-advisor/skills/strategic-review/scripts/generate_review.py:27
- plugins/portfolio-advisor/skills/strategic-review/scripts/generate_review_json.py:33
- plugins/portfolio-advisor/skills/strategic-review/scripts/generate_review_json.py:51
- plugins/portfolio-advisor/skills/strategic-review/scripts/generate_review_json.py:123
- plugins/portfolio-advisor/skills/strategic-review/scripts/validate_weights.py:9
- plugins/portfolio-advisor/skills/strategic-review/scripts/validate_weights.py:14
- plugins/portfolio-advisor/skills/strategic-review/scripts/validate_weights.py:21
- plugins/portfolio-advisor/skills/strategic-review/scripts/validate_weights.py:31
- plugins/portfolio-advisor/skills/strategic-review/scripts/validate_weights.py:69
- plugins/portfolio-advisor/skills/strategic-review/scripts/validate_weights.py:115
- plugins/portfolio-advisor/skills/strategic-review/scripts/scan_opportunities.py:36
- plugins/portfolio-advisor/skills/strategic-review/scripts/verify_refresh.py:6
- plugins/portfolio-advisor/skills/strategic-review/scripts/verify_refresh.py:22
- plugins/portfolio-advisor/skills/strategic-review/scripts/verify_refresh.py:47
- plugins/portfolio-advisor/skills/strategic-review/scripts/verify_refresh.py:48
- plugins/portfolio-advisor/skills/strategic-review/scripts/generate_portfolio_blueprint.py:8
- plugins/portfolio-advisor/skills/strategic-review/scripts/generate_portfolio_blueprint.py:21
- plugins/portfolio-advisor/skills/strategic-review/scripts/generate_portfolio_blueprint.py:41
- plugins/portfolio-advisor/skills/strategic-review/scripts/generate_portfolio_blueprint.py:160
- plugins/portfolio-advisor/skills/strategic-review/scripts/generate_portfolio_blueprint.py:403
- plugins/portfolio-advisor/skills/strategic-review/scripts/apply_catalyst.py:44
- plugins/portfolio-advisor/skills/strategic-review/scripts/apply_catalyst.py:249
- plugins/portfolio-advisor/skills/strategic-review/scripts/apply_catalyst.py:258
- plugins/portfolio-advisor/skills/portfolio-health/scripts/generate_review.py:27
- plugins/portfolio-advisor/skills/portfolio-health/scripts/generate_review_json.py:33
- plugins/portfolio-advisor/skills/portfolio-health/scripts/generate_review_json.py:51
- plugins/portfolio-advisor/skills/portfolio-health/scripts/generate_review_json.py:123
- plugins/portfolio-advisor/skills/portfolio-health/scripts/validate_weights.py:9
- plugins/portfolio-advisor/skills/portfolio-health/scripts/validate_weights.py:14
- plugins/portfolio-advisor/skills/portfolio-health/scripts/validate_weights.py:21
- plugins/portfolio-advisor/skills/portfolio-health/scripts/validate_weights.py:31
- plugins/portfolio-advisor/skills/portfolio-health/scripts/validate_weights.py:69
- plugins/portfolio-advisor/skills/portfolio-health/scripts/validate_weights.py:115
- plugins/portfolio-advisor/skills/portfolio-health/scripts/scan_opportunities.py:36
- plugins/portfolio-advisor/skills/portfolio-health/scripts/verify_refresh.py:6
- plugins/portfolio-advisor/skills/portfolio-health/scripts/verify_refresh.py:22
- plugins/portfolio-advisor/skills/portfolio-health/scripts/verify_refresh.py:47
- plugins/portfolio-advisor/skills/portfolio-health/scripts/verify_refresh.py:48
- plugins/portfolio-advisor/skills/portfolio-health/scripts/generate_portfolio_blueprint.py:8
- plugins/portfolio-advisor/skills/portfolio-health/scripts/generate_portfolio_blueprint.py:21
- plugins/portfolio-advisor/skills/portfolio-health/scripts/generate_portfolio_blueprint.py:41
- plugins/portfolio-advisor/skills/portfolio-health/scripts/generate_portfolio_blueprint.py:160
- plugins/portfolio-advisor/skills/portfolio-health/scripts/generate_portfolio_blueprint.py:403
- plugins/portfolio-advisor/skills/portfolio-health/scripts/apply_catalyst.py:44
- plugins/portfolio-advisor/skills/portfolio-health/scripts/apply_catalyst.py:249
- plugins/portfolio-advisor/skills/portfolio-health/scripts/apply_catalyst.py:258
- plugins/portfolio-advisor/skills/rebalance-portfolio/scripts/update_targets.py:3
- plugins/portfolio-advisor/skills/rebalance-portfolio/scripts/update_targets.py:38
- plugins/portfolio-advisor/skills/rebalance-portfolio/scripts/update_targets.py:48
- plugins/portfolio-advisor/skills/rebalance-portfolio/scripts/update_targets.py:258
- plugins/portfolio-advisor/skills/rebalance-portfolio/scripts/update_targets.py:295
- plugins/portfolio-advisor/skills/rebalance-portfolio/scripts/validate_weights.py:9
- plugins/portfolio-advisor/skills/rebalance-portfolio/scripts/validate_weights.py:14
- plugins/portfolio-advisor/skills/rebalance-portfolio/scripts/validate_weights.py:21
- plugins/portfolio-advisor/skills/rebalance-portfolio/scripts/validate_weights.py:31
- plugins/portfolio-advisor/skills/rebalance-portfolio/scripts/validate_weights.py:69
- plugins/portfolio-advisor/skills/rebalance-portfolio/scripts/validate_weights.py:115
- plugins/portfolio-advisor/skills/daily-brief/scripts/daily_brief.py:38
- plugins/portfolio-advisor/skills/daily-brief/scripts/daily_brief.py:109
- plugins/portfolio-advisor/skills/daily-brief/scripts/daily_brief.py:460
- plugins/portfolio-advisor/skills/calibrate-targets/scripts/update_targets.py:3
- plugins/portfolio-advisor/skills/calibrate-targets/scripts/update_targets.py:38
- plugins/portfolio-advisor/skills/calibrate-targets/scripts/update_targets.py:48
- plugins/portfolio-advisor/skills/calibrate-targets/scripts/update_targets.py:258
- plugins/portfolio-advisor/skills/calibrate-targets/scripts/update_targets.py:295
- plugins/portfolio-advisor/skills/calibrate-targets/scripts/update_thesis.py:57
- plugins/portfolio-advisor/skills/calibrate-targets/scripts/update_thesis.py:74
- plugins/portfolio-advisor/skills/calibrate-targets/scripts/update_thesis.py:205
- plugins/portfolio-advisor/skills/calibrate-targets/scripts/update_thesis.py:238
- plugins/portfolio-advisor/skills/calibrate-targets/scripts/generate_review_json.py:33
- plugins/portfolio-advisor/skills/calibrate-targets/scripts/generate_review_json.py:51
- plugins/portfolio-advisor/skills/calibrate-targets/scripts/generate_review_json.py:123
- plugins/portfolio-advisor/skills/calibrate-targets/scripts/validate_weights.py:9
- plugins/portfolio-advisor/skills/calibrate-targets/scripts/validate_weights.py:14
- plugins/portfolio-advisor/skills/calibrate-targets/scripts/validate_weights.py:21
- plugins/portfolio-advisor/skills/calibrate-targets/scripts/validate_weights.py:31
- plugins/portfolio-advisor/skills/calibrate-targets/scripts/validate_weights.py:69
- plugins/portfolio-advisor/skills/calibrate-targets/scripts/validate_weights.py:115
- plugins/portfolio-advisor/skills/calibrate-targets/scripts/verify_refresh.py:6
- plugins/portfolio-advisor/skills/calibrate-targets/scripts/verify_refresh.py:22
- plugins/portfolio-advisor/skills/calibrate-targets/scripts/verify_refresh.py:47
- plugins/portfolio-advisor/skills/calibrate-targets/scripts/verify_refresh.py:48
- plugins/portfolio-advisor/skills/daily-loop/scripts/generate_reports.py:16
- plugins/portfolio-advisor/skills/x-news-sweep/scripts/update_targets.py:3
- plugins/portfolio-advisor/skills/x-news-sweep/scripts/update_targets.py:38
- plugins/portfolio-advisor/skills/x-news-sweep/scripts/update_targets.py:48
- plugins/portfolio-advisor/skills/x-news-sweep/scripts/update_targets.py:258
- plugins/portfolio-advisor/skills/x-news-sweep/scripts/update_targets.py:295
- plugins/portfolio-advisor/skills/x-news-sweep/scripts/generate_review_json.py:33
- plugins/portfolio-advisor/skills/x-news-sweep/scripts/generate_review_json.py:51
- plugins/portfolio-advisor/skills/x-news-sweep/scripts/generate_review_json.py:123
- plugins/portfolio-advisor/skills/x-news-sweep/scripts/validate_weights.py:9
- plugins/portfolio-advisor/skills/x-news-sweep/scripts/validate_weights.py:14
- plugins/portfolio-advisor/skills/x-news-sweep/scripts/validate_weights.py:21
- plugins/portfolio-advisor/skills/x-news-sweep/scripts/validate_weights.py:31
- plugins/portfolio-advisor/skills/x-news-sweep/scripts/validate_weights.py:69
- plugins/portfolio-advisor/skills/x-news-sweep/scripts/validate_weights.py:115
- plugins/portfolio-advisor/skills/x-news-sweep/scripts/verify_refresh.py:6
- plugins/portfolio-advisor/skills/x-news-sweep/scripts/verify_refresh.py:22
- plugins/portfolio-advisor/skills/x-news-sweep/scripts/verify_refresh.py:47
- plugins/portfolio-advisor/skills/x-news-sweep/scripts/verify_refresh.py:48
- plugins/portfolio-advisor/skills/x-news-sweep/scripts/generate_portfolio_blueprint.py:8
- plugins/portfolio-advisor/skills/x-news-sweep/scripts/generate_portfolio_blueprint.py:21
- plugins/portfolio-advisor/skills/x-news-sweep/scripts/generate_portfolio_blueprint.py:41
- plugins/portfolio-advisor/skills/x-news-sweep/scripts/generate_portfolio_blueprint.py:160
- plugins/portfolio-advisor/skills/x-news-sweep/scripts/generate_portfolio_blueprint.py:403
- plugins/portfolio-advisor/skills/x-news-sweep/scripts/generate_grok_prompt.py:32
- plugins/portfolio-advisor/skills/x-news-sweep/scripts/generate_grok_prompt.py:100
- plugins/portfolio-advisor/skills/x-news-sweep/scripts/apply_catalyst.py:44
- plugins/portfolio-advisor/skills/x-news-sweep/scripts/apply_catalyst.py:249
- plugins/portfolio-advisor/skills/x-news-sweep/scripts/apply_catalyst.py:258
- plugins/portfolio-advisor/skills/update-portfolio-targets/scripts/update_targets.py:3
- plugins/portfolio-advisor/skills/update-portfolio-targets/scripts/update_targets.py:38
- plugins/portfolio-advisor/skills/update-portfolio-targets/scripts/update_targets.py:48
- plugins/portfolio-advisor/skills/update-portfolio-targets/scripts/update_targets.py:258
- plugins/portfolio-advisor/skills/update-portfolio-targets/scripts/update_targets.py:295
- plugins/portfolio-advisor/skills/update-portfolio-targets/scripts/update_thesis.py:57
- plugins/portfolio-advisor/skills/update-portfolio-targets/scripts/update_thesis.py:74
- plugins/portfolio-advisor/skills/update-portfolio-targets/scripts/update_thesis.py:205
- plugins/portfolio-advisor/skills/update-portfolio-targets/scripts/update_thesis.py:238
- plugins/portfolio-advisor/skills/update-portfolio-targets/scripts/validate_weights.py:9
- plugins/portfolio-advisor/skills/update-portfolio-targets/scripts/validate_weights.py:14
- plugins/portfolio-advisor/skills/update-portfolio-targets/scripts/validate_weights.py:21
- plugins/portfolio-advisor/skills/update-portfolio-targets/scripts/validate_weights.py:31
- plugins/portfolio-advisor/skills/update-portfolio-targets/scripts/validate_weights.py:69
- plugins/portfolio-advisor/skills/update-portfolio-targets/scripts/validate_weights.py:115
- plugins/portfolio-advisor/skills/update-portfolio-targets/scripts/verify_refresh.py:6
- plugins/portfolio-advisor/skills/update-portfolio-targets/scripts/verify_refresh.py:22
- plugins/portfolio-advisor/skills/update-portfolio-targets/scripts/verify_refresh.py:47
- plugins/portfolio-advisor/skills/update-portfolio-targets/scripts/verify_refresh.py:48
- plugins/portfolio-advisor/skills/13f-analyze/scripts/update_targets.py:3
- plugins/portfolio-advisor/skills/13f-analyze/scripts/update_targets.py:38
- plugins/portfolio-advisor/skills/13f-analyze/scripts/update_targets.py:48
- plugins/portfolio-advisor/skills/13f-analyze/scripts/update_targets.py:258
- plugins/portfolio-advisor/skills/13f-analyze/scripts/update_targets.py:295
- plugins/portfolio-advisor/skills/13f-analyze/scripts/generate_review_json.py:33
- plugins/portfolio-advisor/skills/13f-analyze/scripts/generate_review_json.py:51
- plugins/portfolio-advisor/skills/13f-analyze/scripts/generate_review_json.py:123
- plugins/portfolio-advisor/skills/13f-analyze/scripts/verify_refresh.py:6
- plugins/portfolio-advisor/skills/13f-analyze/scripts/verify_refresh.py:22
- plugins/portfolio-advisor/skills/13f-analyze/scripts/verify_refresh.py:47
- plugins/portfolio-advisor/skills/13f-analyze/scripts/verify_refresh.py:48
- plugins/tradingview/scripts/tv_create_alerts.py:40
- plugins/tradingview/scripts/tv_create_alerts.py:97
- plugins/tradingview/scripts/tv_create_alerts.py:175
- plugins/tradingview/scripts/tv_create_alerts.py:178
- plugins/tradingview/scripts/tv_create_alerts.py:245
- plugins/tradingview/scripts/tv_create_alerts.py:249
- plugins/tradingview/scripts/ta_sweep_batch.py:9
- plugins/tradingview/scripts/ta_sweep_batch.py:16
- plugins/tradingview/scripts/ta_sweep_batch.py:35
- plugins/tradingview/scripts/ta_sweep_batch.py:62
- plugins/tradingview/skills/ta-daily-sweep/scripts/ta_sweep_batch.py:9
- plugins/tradingview/skills/ta-daily-sweep/scripts/ta_sweep_batch.py:16
- plugins/tradingview/skills/ta-daily-sweep/scripts/ta_sweep_batch.py:35
- plugins/tradingview/skills/ta-daily-sweep/scripts/ta_sweep_batch.py:62
- plugins/tradingview/skills/alert-sync/scripts/tv_create_alerts.py:40
- plugins/tradingview/skills/alert-sync/scripts/tv_create_alerts.py:97
- plugins/tradingview/skills/alert-sync/scripts/tv_create_alerts.py:175
- plugins/tradingview/skills/alert-sync/scripts/tv_create_alerts.py:178
- plugins/tradingview/skills/alert-sync/scripts/tv_create_alerts.py:245
- plugins/tradingview/skills/alert-sync/scripts/tv_create_alerts.py:249
- investment_screener/backend/src/utils/zod-schemas.ts:5
- investment_screener/backend/src/utils/zod-schemas.ts:187
- investment_screener/backend/src/utils/paths.ts:20
- investment_screener/backend/src/utils/paths.ts:21
- investment_screener/backend/src/routes/stock.ts:18
- investment_screener/backend/src/routes/theses.ts:33
- investment_screener/backend/src/routes/docs.ts:22
- investment_screener/backend/src/routes/screener.ts:19
- investment_screener/backend/src/services/BrokerSyncService.ts:14
- investment_screener/backend/tests/utils/zod-schemas.spec.ts:7
- investment_screener/backend/tests/utils/zod-schemas.spec.ts:8

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
- investment_screener/backend/tests/py_services/test_harvest_predictions.py:29
- investment_screener/backend/tests/py_services/test_harvest_predictions.py:30

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
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:149

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
- investment_screener/backend/tests/py_services/test_comps_valuation.py:99

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
- investment_screener/backend/tests/py_services/test_verify_thesis_sync.py:43
- investment_screener/backend/tests/py_services/test_verify_thesis_sync.py:67
- investment_screener/backend/tests/py_services/test_verify_thesis_sync.py:118

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
- investment_screener/backend/tests/py_services/test_verify_thesis_sync.py:93

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
- investment_screener/backend/tests/py_services/test_verify_thesis_sync.py:42
- investment_screener/backend/tests/py_services/test_verify_thesis_sync.py:66
- investment_screener/backend/tests/py_services/test_verify_thesis_sync.py:92
- investment_screener/backend/tests/py_services/test_verify_thesis_sync.py:117
- investment_screener/backend/tests/py_services/test_verify_thesis_sync.py:144

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
- investment_screener/backend/tests/py_services/test_migrate_research_report_pointers.py:16

**Known consumers:**
- investment_screener/backend/tests/py_services/test_migrate_research_report_pointers.py:25
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:107
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:355
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:364
- plugins/portfolio-advisor/tests/test_consolidate_research.py:30

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
- investment_screener/backend/tests/py_services/test_update_price_levels.py:119

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
- investment_screener/backend/tests/py_services/test_comps_valuation.py:103

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
- investment_screener/backend/tests/py_services/test_verify_thesis_sync.py:145

### investment_screener/backend/data/projections/CORZ.json

**Classification:** ALLOWED_MODEL_ARTIFACT_JSON

**Known producers:**
- investment_screener/backend/tests/py_services/test_harvest_predictions.py:161

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
- investment_screener/backend/tests/py_services/test_comps_valuation.py:95

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
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:150
- investment_screener/backend/src/routes/thirteenf.ts:30

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
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:149

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
- investment_screener/backend/tests/py_services/test_verify_thesis_sync.py:145

### investment_screener/backend/tests/fixtures/edgar_companyfacts_aapl.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_edgar_facts.py:15

### investment_screener/backend/tests/fixtures/target_portfolio.test.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- run_tests.py:219
- investment_screener/backend/tests/py_services/test_portfolio_action_import.py:23

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
- investment_screener/backend/tests/py_services/test_portfolio_io.py:26
- investment_screener/backend/tests/py_services/test_portfolio_io.py:56

### investment_screener/backend/tests/fixtures/portfolio.test.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- run_tests.py:218
- investment_screener/backend/tests/py_services/test_portfolio_io.py:27
- investment_screener/backend/tests/py_services/test_portfolio_action_import.py:22

### investment_screener/frontend/.vite/deps/_metadata.json

**Classification:** ARCHIVE_LEGACY_READ_ONLY

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/py_services/audit_json_usage.py:485
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:139

### investment_screener/frontend/.vite/deps/package.json

**Classification:** ARCHIVE_LEGACY_READ_ONLY

**Known producers:**
- (none detected)

**Known consumers:**
- run_tests.py:17
- run_investment_toolkit.py:16
- investment_screener/backend/py_services/audit_json_usage.py:401

### docs/superpowers/audits/json-discovery-audit.json

**Classification:** ALLOWED_GENERATED_CACHE_JSON

**Known producers:**
- investment_screener/backend/py_services/audit_json_usage.py:628
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:66
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:83

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:33
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:39
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:63
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:82
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:94
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:205
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:242
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:259
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:326
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:339
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:344

### docs/superpowers/audits/allowed-json-register.json

**Classification:** ALLOWED_GENERATED_CACHE_JSON

**Known producers:**
- investment_screener/backend/py_services/audit_json_usage.py:645

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:328
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:361

### plugins/etf-analysis/plugin.json

**Classification:** ALLOWED_CONFIGURATION_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/py_services/audit_json_usage.py:391
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:123
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:124

### plugins/tradingview/plugin.json

**Classification:** ALLOWED_CONFIGURATION_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/py_services/audit_json_usage.py:391
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:123
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:124

### plugins/toolkit-manager/plugin.json

**Classification:** ALLOWED_CONFIGURATION_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/py_services/audit_json_usage.py:391
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:123
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:124

### plugins/stock-valuation/plugin.json

**Classification:** ALLOWED_CONFIGURATION_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/py_services/audit_json_usage.py:391
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:123
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:124

### plugins/portfolio-advisor/plugin.json

**Classification:** ALLOWED_CONFIGURATION_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/py_services/audit_json_usage.py:391
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:123
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:124

### plugins/portfolio-advisor/references/standing-decisions.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/py_services/brief_recommendations.py:51

### plugins/portfolio-advisor/.claude-plugin/plugin.json

**Classification:** ALLOWED_CONFIGURATION_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/py_services/audit_json_usage.py:391
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:123
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:124

### plugins/portfolio-advisor/assets/templates/target_portfolio_template.json

**Classification:** ALLOWED_CONFIGURATION_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:134

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
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:129

### plugins/portfolio-advisor/skills/thesis-review/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:129

### plugins/portfolio-advisor/skills/thesis-review/assets/templates/target_portfolio_template.json

**Classification:** ALLOWED_CONFIGURATION_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:134

### plugins/portfolio-advisor/skills/strategic-review/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:129

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
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:129

### plugins/portfolio-advisor/skills/rebalance-portfolio/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:129

### plugins/portfolio-advisor/skills/thesis-challenge-bundler/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:129

### plugins/portfolio-advisor/skills/set-thesis-breakers/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:129

### plugins/portfolio-advisor/skills/adversarial-review/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:129

### plugins/portfolio-advisor/skills/daily-brief/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:129

### plugins/portfolio-advisor/skills/calibrate-targets/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:129

### plugins/portfolio-advisor/skills/norberts-gambit/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:129

### plugins/portfolio-advisor/skills/daily-loop/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:129

### plugins/portfolio-advisor/skills/x-news-sweep/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:129

### plugins/portfolio-advisor/skills/update-portfolio-targets/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:129

### plugins/portfolio-advisor/skills/update-portfolio-targets/assets/templates/target_portfolio_template.json

**Classification:** ALLOWED_CONFIGURATION_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:134

### plugins/portfolio-advisor/skills/ytd-return/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:129

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
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:129

### plugins/portfolio-advisor/agents/evals/weekly-review-agent.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

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

### plugins/portfolio-advisor/agents/evals/single-stock-advisor.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/portfolio-advisor/agents/evals/data-quality-agent.json

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

### plugins/portfolio-advisor/agents/evals/daily-loop-agent.json

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
- investment_screener/backend/py_services/audit_json_usage.py:391
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:123
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:124

### plugins/stock-valuation/assets/templates/projection_template.json

**Classification:** ALLOWED_CONFIGURATION_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/stock-valuation/skills/valuation-math-validation/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:129

### plugins/stock-valuation/skills/stock_valuation/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:129

### plugins/stock-valuation/skills/stock_valuation/assets/templates/projection_template.json

**Classification:** ALLOWED_CONFIGURATION_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/stock-valuation/skills/stock_valuation/references/examples/example_NVDA_placeholder.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/stock-valuation/skills/stock_valuation/references/examples/example_NVDA_2026-05-02.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:135

### plugins/stock-valuation/skills/stock_valuation/references/examples/example_GOOG_2026-05-02.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/stock-valuation/skills/stock_valuation/references/examples/example_PANW_2026-05-02.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/stock-valuation/skills/forward-valuation-challenge/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:129

### plugins/stock-valuation/skills/stock-research/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:129

### plugins/stock-valuation/scripts/cache/SKHY.json

**Classification:** ALLOWED_GENERATED_CACHE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/toolkit-manager/.claude-plugin/plugin.json

**Classification:** ALLOWED_CONFIGURATION_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/py_services/audit_json_usage.py:391
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:123
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:124

### plugins/toolkit-manager/skills/run-screener/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:129

### plugins/toolkit-manager/agents/evals/toolkit-onboarding-guide.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/tradingview/.claude-plugin/plugin.json

**Classification:** ALLOWED_CONFIGURATION_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/py_services/audit_json_usage.py:391
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:123
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:124

### plugins/tradingview/assets/pinescript-indicators/registry.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- investment_screener/backend/tests/py_services/test_pine_version_history_from_git.py:75
- investment_screener/backend/tests/py_services/test_pine_version_history_from_git.py:198
- investment_screener/backend/tests/py_services/test_pine_version_history_from_git.py:214
- investment_screener/backend/tests/py_services/test_pine_rollback_on_error.py:115

**Known consumers:**
- investment_screener/backend/py_services/pine_script_manager.py:14
- investment_screener/backend/py_services/pine_script_manager.py:17
- investment_screener/backend/py_services/pine_script_manager.py:55
- investment_screener/backend/py_services/pine_script_manager.py:112
- investment_screener/backend/py_services/pine_script_manager.py:543
- investment_screener/backend/py_services/pine_script_manager.py:563
- investment_screener/backend/py_services/pine_script_manager.py:679
- investment_screener/backend/py_services/pine_script_manager.py:708
- investment_screener/backend/tests/py_services/test_pine_version_history_from_git.py:5
- investment_screener/backend/tests/py_services/test_pine_version_history_from_git.py:14
- investment_screener/backend/tests/py_services/test_pine_version_history_from_git.py:82
- investment_screener/backend/tests/py_services/test_pine_version_history_from_git.py:85
- investment_screener/backend/tests/py_services/test_pine_version_history_from_git.py:186
- investment_screener/backend/tests/py_services/test_pine_version_history_from_git.py:192
- investment_screener/backend/tests/py_services/test_pine_version_history_from_git.py:213
- investment_screener/backend/tests/py_services/test_pine_version_history_from_git.py:268
- investment_screener/backend/tests/py_services/test_pine_auto_discovery_registers_scripts.py:18
- investment_screener/backend/tests/py_services/test_pine_auto_discovery_registers_scripts.py:101
- investment_screener/backend/tests/py_services/test_pine_auto_discovery_registers_scripts.py:106
- investment_screener/backend/tests/py_services/test_pine_auto_discovery_registers_scripts.py:205
- investment_screener/backend/tests/py_services/test_pine_auto_discovery_registers_scripts.py:239
- investment_screener/backend/tests/py_services/test_pine_rollback_on_error.py:98
- investment_screener/backend/tests/py_services/test_pine_rollback_on_error.py:123
- investment_screener/backend/tests/py_services/test_pine_rollback_on_error.py:126
- investment_screener/backend/tests/py_services/test_pine_rollback_on_error.py:164
- investment_screener/backend/tests/py_services/test_pine_library_manages_multiple_scripts.py:51
- investment_screener/backend/tests/py_services/test_pine_registry_reads_writes_json.py:12
- investment_screener/backend/tests/py_services/test_pine_registry_reads_writes_json.py:38
- investment_screener/backend/tests/py_services/test_pine_registry_reads_writes_json.py:59
- investment_screener/backend/tests/py_services/test_pine_registry_reads_writes_json.py:192
- investment_screener/backend/tests/py_services/test_pine_registry_reads_writes_json.py:200
- investment_screener/backend/tests/py_services/test_pine_injection_auto_clicks.py:52

### plugins/tradingview/skills/pine-inject/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:129

### plugins/tradingview/skills/tv-save-indicator/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:129

### plugins/tradingview/skills/ta-red-team/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:129

### plugins/tradingview/skills/chart-snapshot/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:129

### plugins/tradingview/skills/modify-order/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:129

### plugins/tradingview/skills/tv-add-indicator/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:129

### plugins/tradingview/skills/cancel-order/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:129

### plugins/tradingview/skills/ta-snapshot/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:129

### plugins/tradingview/skills/tv-setup/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:129

### plugins/tradingview/skills/tv-change-symbol/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:129

### plugins/tradingview/skills/ta-daily-sweep/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:129

### plugins/tradingview/skills/tv-change-type/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:129

### plugins/tradingview/skills/alert-list/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:129

### plugins/tradingview/skills/alert-sync/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:129

### plugins/tradingview/skills/author-pine-script/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:129

### plugins/tradingview/skills/tv-manage-watchlists/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:129

### plugins/tradingview/skills/get-orders/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:129

### plugins/tradingview/skills/tv-chart-setup/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:129

### plugins/tradingview/skills/technical-analysis-expert/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:129

### plugins/tradingview/skills/tv-portfolio-sync/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:129

### plugins/tradingview/skills/price-refresh/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:129

### plugins/tradingview/skills/place-order/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:129

### plugins/tradingview/agents/evals/tradingview-onboarding.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/tradingview/agents/evals/ta-guide.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:130

### plugins/etf-analysis/assets/templates/etf_analysis_template.json

**Classification:** ALLOWED_CONFIGURATION_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/etf-analysis/skills/etf_analysis/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- investment_screener/backend/tests/py_services/test_audit_json_usage.py:129

### plugins/etf-analysis/skills/etf_analysis/assets/templates/etf_analysis_template.json

**Classification:** OUT_OF_SCOPE_FOR_THIS_PHASE

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

