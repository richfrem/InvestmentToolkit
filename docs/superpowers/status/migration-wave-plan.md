# SQLite Intelligence Ledger Migration — Wave Plan

This document establishes the execution and cutover plan for the SQLite Intelligence Ledger. It sequences consumers into logical migration waves to isolate risk, ensure clean rollback procedures, and identify the minimum scope required to unlock the business value of the new read-model database.

---

## Metric Breakdown & Questions

### 1. How many consumers currently use the new architecture?
**2 consumers**. The orchestrators of the stock valuation and stock research skills ([stock_valuation/SKILL.md](file:///Users/richardfremmerlid/Projects/InvestmentToolkit/plugins/stock-valuation/skills/stock_valuation/SKILL.md) and [stock-research/SKILL.md](file:///Users/richardfremmerlid/Projects/InvestmentToolkit/plugins/stock-valuation/skills/stock-research/SKILL.md)) have been updated to call the ledger CLI (`rebuild_db.py`). However, no runtime code or backend routes query the live SQLite database in production yet.

### 2. How many consumers must still migrate?
**13 consumers**. These are the code objects currently flagged as `MIGRATION_REQUIRED` in the [Architecture Adoption Matrix](file:///Users/richardfremmerlid/Projects/InvestmentToolkit/.worktrees/worktree-phase4a-audit/docs/superpowers/status/architecture-adoption-matrix.md).

### 3. What percentage of migration scope remains?
**86.7% remaining**. Out of the 15 total migration candidates (2 currently using + 13 requiring migration), 13 candidates remain unmigrated.
*(Note: 151 other files in the consumer inventory are classified as `REMAINS_JSON_BY_DESIGN` or `OUT_OF_SCOPE` per ADR-028 scope boundaries and do not count toward migration scope).*

### 4. What is the minimum set of consumers that must migrate before a real data migration provides business value?
The **Wave 1 consumers** represent the minimum set:
1. `daily_brief.py`
2. `ta_sweep_batch.py`
3. `compute_conviction_scores.py`
4. `dailybrief.ts` (Express Route)
5. `daily-loop/SKILL.md`
6. `daily-loop-agent.md` (Sub-agent)

**Why**: If a real data migration were executed tomorrow, but Wave 1 was not rewired, the live dashboard metrics, morning brief conviction scoring, and daily action triage would continue to query stale flat-file JSON and dated markdown files on disk. The new SQLite ledger remains a dark backup database with zero operational utility until Wave 1 connects to it.

### 5. After Wave 1, what business capabilities would actually be using the ledger?
- **Macro Regime & Conviction Scoring**: Daily macro regime calculations and conviction scores will be persisted to and queried from the central SQLite ledger via the repository layer, allowing trend analysis across historical days.
- **Technical Analysis Sweep Cache**: Batch technical indicators (RSI, Squeeze setups, volume metrics) will be recorded in the ledger rather than raw flat-file JSON.
- **Morning Brief Persistence**: The daily loop agent and the Express API will serve the current day's structured conviction details directly from SQLite tables.

---

## Wave 1 — Highest Value (Core Advisor Loop)

This wave rewires the core daily advisor loop. It moves daily brief generation, technical indicator caching, and conviction calculations off `ta-sweep-results.json` and onto the SQLite database.

### 1. `daily_brief.py`
- **Current Source**: Reads `ta-sweep-results.json` / writes `daily-briefs/YYYY-MM-DD.json`.
- **Target Source**: Reads technical indicators from SQLite; writes daily brief observations into `intelligence.sqlite` via `EventRepository`.
- **Estimated Files Impacted**: 1 (`py_services/daily_brief.py`)
- **Tests to Update**: `test_daily_brief.py`
- **Migration Risk**: High. Core morning brief pipeline. Stale records could stall the daily loop.
- **Rollback Approach**: Retain old file-write logic behind a `--legacy-json` flag. Keep legacy `.json` output generation active in parallel during validation.

### 2. `ta_sweep_batch.py`
- **Current Source**: Writes raw sweep indicators directly to `ta-sweep-results.json`.
- **Target Source**: Writes technical indicators to SQLite `intelligence_event` table via `EventStore`.
- **Estimated Files Impacted**: 2 (plugin script + wrapper skill script)
- **Tests to Update**: `test_ta_sweep_batch.py`
- **Migration Risk**: High. Relies on active TradingView CDP quote scanning. Double-writing could lock the WAL.
- **Rollback Approach**: Fall back to raw JSON caching by enabling the existing local write routine.

### 3. `compute_conviction_scores.py`
- **Current Source**: Reads `ta-sweep-results.json` and `target-portfolio.json`.
- **Target Source**: Queries SQLite database via `InstrumentRepository` and `EventRepository`.
- **Estimated Files Impacted**: 1 (`py_services/compute_conviction_scores.py`)
- **Tests to Update**: `test_compute_conviction_scores.py`
- **Migration Risk**: Medium. Relies on math formulas remaining consistent between JSON keys and SQLite column views.
- **Rollback Approach**: Compare output dataframe diffs against a cached JSON run before applying target changes.

### 4. `dailybrief.ts` (Express Route)
- **Current Source**: Reads the latest JSON file inside `data/daily-briefs/` from disk.
- **Target Source**: Spawns Python bridge query or reads `daily_brief` database views.
- **Estimated Files Impacted**: 1 (`backend/src/routes/dailybrief.ts`)
- **Tests to Update**: None (smoke tested via endpoint integration checks).
- **Migration Risk**: Medium. UI Dashboard is populated by this endpoint. Malformed JSON returns will crash the web app.
- **Rollback Approach**: Fall back to readdir of `data/daily-briefs/` if database connection times out or returns empty records.

### 5. `daily-loop/SKILL.md` (Orchestrator)
- **Current Source**: Guides agent to check filesystem states and python script returns.
- **Target Source**: Instructs agent to run database health sweeps and query the CLI.
- **Estimated Files Impacted**: 1 (`plugins/portfolio-advisor/skills/daily-loop/SKILL.md`)
- **Tests to Update**: None (orchestrator markdown).
- **Migration Risk**: Low.
- **Rollback Approach**: Revert markdown file to main branch.

### 6. `daily-loop-agent.md` (Sub-agent)
- **Current Source**: Directs LLM context to verify file existence on disk.
- **Target Source**: Directs LLM to run ledger diagnostic commands.
- **Estimated Files Impacted**: 1 (`plugins/portfolio-advisor/agents/daily-loop-agent.md`)
- **Tests to Update**: None.
- **Migration Risk**: Medium. Prompt instructions could cause hallucinations if the CLI tools fail.
- **Rollback Approach**: Restore pre-ledger system instructions.

---

## Wave 2 — Research & Report Delivery

This wave migrates qualitative research reports and timeline pointers off disk Markdown storage and onto SQLite.

| Consumer | Current Source | Target Source | Status | Action | Risk |
|---|---|---|---|---|---|
| `investment_screener/backend/src/routes/docs.ts` | `data/research/*.md` | SQLite `/research` views | MIGRATION_REQUIRED | Query `intelligence.sqlite` FTS5 table instead of FS read | Medium |
| `investment_screener/backend/py_services/evolution_events.py` | `context/events.jsonl` | `intelligence_event` table | MIGRATION_REQUIRED | Persist timeline event entries to database | Medium |
| `plugins/portfolio-advisor/scripts/daily_brief.py` | `ta-sweep-results.json` | `intelligence.sqlite` | MIGRATION_REQUIRED | Rewire scripts in plugins sub-directories to match py_services | Low |
| `plugins/portfolio-advisor/skills/daily-brief/scripts/daily_brief.py` | `ta-sweep-results.json` | `intelligence.sqlite` | MIGRATION_REQUIRED | Rewire skill scripts | Low |
| `plugins/portfolio-advisor/skills/daily-loop/scripts/generate_reports.py` | `target-portfolio.json` | `intelligence.sqlite` | MIGRATION_REQUIRED | Persist reports to database | Low |

---

## Wave 3 — Resolved Scope Review

No consumers remain in Wave 3. All **10** previous `UNKNOWN_REQUIRES_REVIEW` files have been successfully validated as configuration, tooling, or runner files that remain JSON/JSONL by design.

| Consumer | Resolved Status | Final Rationale |
|---|---|---|
| `investment_screener/backend/py_services/brief_recommendations.py` | REMAINS_JSON_BY_DESIGN | Reads target guidelines inside standing-decisions.json |
| `investment_screener/backend/py_services/pine_script_manager.py` | REMAINS_JSON_BY_DESIGN | Config manager for TV Pine script registration |
| `investment_screener/backend/tests/py_services/test_pine_*` (6 files) | REMAINS_JSON_BY_DESIGN | Tests targeting Pine registry configuration logic |
| `run_investment_toolkit.py` | REMAINS_JSON_BY_DESIGN | Tooling script verifying static package.json configuration |
| `run_tests.py` | REMAINS_JSON_BY_DESIGN | Tooling script parsing static symlink rules |
