# SQLite Intelligence Ledger — Wave 1 Implementation Plan

This document serves as the exact blueprint for rewiring the Wave 1 consumers to use the SQLite Intelligence Ledger. It resolves architectural ambiguities, defines interface specs, and outlines the precise sequence of operations.

---

## Architectural Decisions & Justifications

### 1. Dailybrief Express Route (`dailybrief.ts`) Architecture
**Decision**: The Express backend route ([dailybrief.ts](file:///Users/richardfremmerlid/Projects/InvestmentToolkit/investment_screener/backend/src/routes/dailybrief.ts)) will query the Python shared repository layer (`py_services/intelligence/event_repository.py`) by spawning a bridge execution via `bridge.ts` (`spawnPythonScript`).
**Justification**:
- **DRY Principle**: Persisting SQL queries and schema models solely within the Python shared repository layer avoids schema knowledge duplication in TypeScript.
- **Dynamic State**: Prevents visual lag or stale states caused by relying on static Markdown or JSON view files, while leveraging the robust `bridge.ts` pattern already implemented for analytical execution.

### 2. Domain Placement of Evolution Events (`evolution_events.py`)
**Decision**: `evolution_events.py` (telemetry/agent operations logging) will **remain a separate ledger** and is excluded from the investment intelligence ledger migration scope.
**Justification**:
- **Domain Separation**: The investment ledger exists for qualitative financial observations (valutations, broker syncs, price thresholds). Developer logs and agent self-evolution runtimes belong in a dedicated DevOps telemetry loop to prevent investment data pollution.
- **Scale Isolation**: Operations logs generate high-frequency writes that would bloat the qualitative database.

---

## Operational Adoption Metrics

- **Runtime Adoption**: **13.3%** (2 out of 15 migration candidates actively query the ledger command-line tool).
- **Business Workflow Adoption**: **0.0%** (no live business workflows or UI views read from the ledger yet).
- **Ledger-Enabled Consumers**: `stock_valuation` skill, `stock-research` skill.
- **Remaining Migration Candidates**: **13 files** (Wave 1: 6, Wave 2: 7).

---

## Wave 1 Consumer Specifications

### 1. `daily_brief.py`
- **Current Inputs**: `investment_screener/backend/data/ta-sweep-results.json`
- **Current Outputs**: `investment_screener/backend/data/daily-briefs/YYYY-MM-DD.json`
- **Target Repository Methods**:
  - `EventRepository.get_latest_observations(ticker)` to fetch TA indicators.
  - `EventRepository.add_event(event)` to write daily brief summary.
- **Target Tables/Views**: `intelligence_event`
- **Exact Files to Modify**: `investment_screener/backend/py_services/daily_brief.py`
- **Tests Impacted**: `investment_screener/backend/tests/py_services/test_daily_brief.py`
- **Validation Methodology**: Verify that a generated brief contains exactly the same fields and is saved directly to the database.
- **Rollback Methodology**: Run script with `--legacy-json` flag to read/write disk JSON files.
- **Dependencies**: Replay layer verification.
- **Migration Sequence**: Run first after database init.

### 2. `ta_sweep_batch.py`
- **Current Inputs**: TradingView CDP DOM Data Window readings
- **Current Outputs**: Writes indicators to `ta-sweep-results.json`
- **Target Repository Methods**:
  - `EventStore.append(event)` to write new indicators.
- **Target Tables/Views**: `intelligence_event`
- **Exact Files to Modify**: `plugins/tradingview/scripts/ta_sweep_batch.py`
- **Tests Impacted**: `plugins/tradingview/tests/test_ta_sweep_batch.py`
- **Validation Methodology**: Run sweep for one ticker and query SQLite to verify values are updated in table.
- **Rollback Methodology**: Comment out repo-write lines and uncomment json-write lines.
- **Dependencies**: TradingView CDP port 9222.
- **Migration Sequence**: Run concurrently with daily loop.

### 3. `compute_conviction_scores.py`
- **Current Inputs**: `ta-sweep-results.json`, `target-portfolio.json`
- **Current Outputs**: Conviction score dataframe matrix
- **Target Repository Methods**:
  - `EventRepository.get_latest_observations()`
- **Target Tables/Views**: `intelligence_event`, `instrument_view`
- **Exact Files to Modify**: `investment_screener/backend/py_services/compute_conviction_scores.py`
- **Tests Impacted**: `investment_screener/backend/tests/py_services/test_compute_conviction_scores.py`
- **Validation Methodology**: Assert conviction scores computed match those calculated using the JSON fallback.
- **Rollback Methodology**: Revert to JSON-based read block via code flags.
- **Dependencies**: `daily_brief.py` updates.
- **Migration Sequence**: Executed after `daily_brief.py`.

### 4. `dailybrief.ts`
- **Current Inputs**: `data/daily-briefs/YYYY-MM-DD.json`
- **Current Outputs**: Express JSON HTTP response
- **Target Repository Methods**: Queries database via Python CLI bridge `python3 rebuild_db.py --query-latest-brief`.
- **Target Tables/Views**: `intelligence_event` table query.
- **Exact Files to Modify**: `investment_screener/backend/src/routes/dailybrief.ts`
- **Tests Impacted**: Express integration tests.
- **Validation Methodology**: GET `/api/daily-brief/latest` returns correct fields.
- **Rollback Methodology**: Fall back to disk readdir of JSON files if command returns empty.
- **Dependencies**: `daily_brief.py` database writes.
- **Migration Sequence**: Backend API cutover.

### 5. `daily-loop/SKILL.md`
- **Current Inputs**: Prose check commands.
- **Current Outputs**: Orchestrates script execution order.
- **Target Repository Methods**: CLI triggers.
- **Target Tables/Views**: SQLite DB file path.
- **Exact Files to Modify**: `plugins/portfolio-advisor/skills/daily-loop/SKILL.md`
- **Tests Impacted**: None (Markdown orchestration).
- **Validation Methodology**: Manual dry run of `/daily` loops.
- **Rollback Methodology**: Git revert.
- **Dependencies**: Wave 1 scripts.
- **Migration Sequence**: Executed when scripts are ready.

### 6. `daily-loop-agent.md`
- **Current Inputs**: Disk environment paths.
- **Current Outputs**: System prompt directives.
- **Target Repository Methods**: SQLite diagnostics prompt.
- **Target Tables/Views**: SQLite status checks.
- **Exact Files to Modify**: `plugins/portfolio-advisor/agents/daily-loop-agent.md`
- **Tests Impacted**: None.
- **Validation Methodology**: Verify sub-agent executes daily loop without seeking JSON files.
- **Rollback Methodology**: Git checkout main.
- **Dependencies**: All Wave 1 components.
- **Migration Sequence**: Final Wave 1 step.
