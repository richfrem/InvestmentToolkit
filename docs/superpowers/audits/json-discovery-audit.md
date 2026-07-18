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

No `.json`/`.jsonl` files currently exist under `temp/` (which is gitignored scratch space per `.gitignore`). Re-run this audit periodically if `temp/` is suspected of accumulating durable data over time — nothing to report as of 2026-07-18T22:59:32Z.

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
- (none detected)

### context/events.jsonl

**Classification:** ALLOWED_SEPARATE_DOMAIN_LEDGER_JSONL

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### schemas/market_data_response.schema.json

**Classification:** ALLOWED_CONFIGURATION_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### schemas/prediction.schema.json

**Classification:** ALLOWED_CONFIGURATION_JSON

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

**Classification:** ALLOWED_CONFIGURATION_JSON

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

**Classification:** ALLOWED_AUTHORITATIVE_JSON

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

**Classification:** ALLOWED_AUTHORITATIVE_JSON

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

**Classification:** ALLOWED_AUTHORITATIVE_JSON

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
- (none detected)

### investment_screener/backend/data/etf_analysis/FOTO.json

**Classification:** OUT_OF_SCOPE_FOR_THIS_PHASE

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

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

**Classification:** ARCHIVE_LEGACY_READ_ONLY

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### investment_screener/frontend/.vite/deps/package.json

**Classification:** ARCHIVE_LEGACY_READ_ONLY

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### docs/superpowers/audits/json-discovery-audit.json

**Classification:** ALLOWED_GENERATED_CACHE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### docs/superpowers/audits/allowed-json-register.json

**Classification:** ALLOWED_GENERATED_CACHE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/etf-analysis/plugin.json

**Classification:** ALLOWED_CONFIGURATION_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/tradingview/plugin.json

**Classification:** ALLOWED_CONFIGURATION_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/toolkit-manager/plugin.json

**Classification:** ALLOWED_CONFIGURATION_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/stock-valuation/plugin.json

**Classification:** ALLOWED_CONFIGURATION_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/portfolio-advisor/plugin.json

**Classification:** ALLOWED_CONFIGURATION_JSON

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

**Classification:** ALLOWED_CONFIGURATION_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/portfolio-advisor/assets/templates/target_portfolio_template.json

**Classification:** ALLOWED_CONFIGURATION_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

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
- (none detected)

### plugins/portfolio-advisor/skills/thesis-review/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/portfolio-advisor/skills/thesis-review/assets/templates/target_portfolio_template.json

**Classification:** ALLOWED_CONFIGURATION_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/portfolio-advisor/skills/strategic-review/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

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
- (none detected)

### plugins/portfolio-advisor/skills/rebalance-portfolio/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/portfolio-advisor/skills/thesis-challenge-bundler/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/portfolio-advisor/skills/set-thesis-breakers/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/portfolio-advisor/skills/adversarial-review/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/portfolio-advisor/skills/daily-brief/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/portfolio-advisor/skills/calibrate-targets/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/portfolio-advisor/skills/norberts-gambit/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/portfolio-advisor/skills/daily-loop/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/portfolio-advisor/skills/x-news-sweep/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/portfolio-advisor/skills/update-portfolio-targets/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/portfolio-advisor/skills/update-portfolio-targets/assets/templates/target_portfolio_template.json

**Classification:** ALLOWED_CONFIGURATION_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/portfolio-advisor/skills/ytd-return/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

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
- (none detected)

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
- (none detected)

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
- (none detected)

### plugins/stock-valuation/skills/stock_valuation/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

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
- (none detected)

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
- (none detected)

### plugins/stock-valuation/skills/stock-research/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

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
- (none detected)

### plugins/toolkit-manager/skills/run-screener/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

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
- (none detected)

### plugins/tradingview/assets/pinescript-indicators/registry.json

**Classification:** UNKNOWN_REQUIRES_REVIEW

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/tradingview/skills/pine-inject/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/tradingview/skills/tv-save-indicator/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/tradingview/skills/ta-red-team/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/tradingview/skills/chart-snapshot/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/tradingview/skills/modify-order/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/tradingview/skills/tv-add-indicator/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/tradingview/skills/cancel-order/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/tradingview/skills/ta-snapshot/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/tradingview/skills/tv-setup/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/tradingview/skills/tv-change-symbol/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/tradingview/skills/ta-daily-sweep/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/tradingview/skills/tv-change-type/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/tradingview/skills/alert-list/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/tradingview/skills/alert-sync/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/tradingview/skills/author-pine-script/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/tradingview/skills/tv-manage-watchlists/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/tradingview/skills/get-orders/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/tradingview/skills/tv-chart-setup/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/tradingview/skills/technical-analysis-expert/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/tradingview/skills/tv-portfolio-sync/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/tradingview/skills/price-refresh/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

### plugins/tradingview/skills/place-order/evals/evals.json

**Classification:** ALLOWED_TEST_FIXTURE_JSON

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

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
- (none detected)

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
- (none detected)

### plugins/etf-analysis/skills/etf_analysis/assets/templates/etf_analysis_template.json

**Classification:** OUT_OF_SCOPE_FOR_THIS_PHASE

**Known producers:**
- (none detected)

**Known consumers:**
- (none detected)

