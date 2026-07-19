# SQLite Intelligence Ledger — Wave 1 Implementation Design

This document provides the technical design and step-by-step instructions for rewiring the Wave 1 consumers to use the SQLite Intelligence Ledger. It acts as a detailed, production-grade specification for any agent to execute the integration work without ambiguity.

---

## Architectural Decisions Reference

1. **Dailybrief API Route (`dailybrief.ts`)**: Confirmed to use the Python repository bridge via `bridge.ts` (`spawnPythonScript`) invoking a database helper command (e.g., `python3 rebuild_db.py --query-latest-brief`). Direct SQLite access from the Node.js Express process is strictly prohibited.
2. **Docs API Route (`docs.ts`)**: Will transition to fetching qualitative report records from the SQLite database matching `event_type = 'RESEARCH_IMPORT'` via the repository layer, serving as the source of truth instead of readdir and readFile over dated filesystem Markdown.
3. **Telemetry Logs (`evolution_events.py`)**: Confirmed to remain outside the investment intelligence ledger scope. Telemetry tracking for agent self-evolution will continue to reside in its own dedicated, append-only domain log (`context/events.jsonl`) per ADR-028.

---

## Prerequisite Repository Methods (To Be Built First)

Before rewiring any consumers, the following helper methods must be added to the shared Python repository layer in `investment_screener/backend/py_services/intelligence/event_repository.py`. Currently, only `insert_event`, `search_fts`, and `list_active_events_for_ticker` exist.

### Method 1: `get_latest_event_by_type(conn, event_type: str) -> dict | None`
- **Purpose**: Retrieves the single most recent active event of a given type. Required for fetching the latest daily brief (`REVIEW_DAILY`).
- **SQL Query**:
  ```sql
  SELECT event_id, event_sequence, instrument_id, event_type, effective_at, observed_at, ingested_at, status, title, body_markdown, payload_json, content_hash
  FROM intelligence_event
  WHERE event_type = ? AND status = 'ACTIVE'
  ORDER BY effective_at DESC, ingested_at DESC LIMIT 1;
  ```

### Method 2: `get_latest_event_by_type_and_ticker(conn, event_type: str, ticker: str) -> dict | None`
- **Purpose**: Retrieves the most recent active event of a given type for a specific ticker. Required for fetching the latest `TECHNICAL_SWEEP` for a ticker.
- **SQL Query**:
  ```sql
  SELECT ie.*
  FROM intelligence_event ie
  JOIN instrument i ON i.instrument_id = ie.instrument_id
  WHERE ie.event_type = ? AND i.ticker = ? AND ie.status = 'ACTIVE'
  ORDER BY ie.effective_at DESC, ie.ingested_at DESC LIMIT 1;
  ```

---

## Wave 1 Consumer-by-Consumer Implementation Sequence

### Item 1: `ta_sweep_batch.py` (Persistence Layer Update)
- **Current Code Path**: `plugins/tradingview/scripts/ta_sweep_batch.py` (and symlinked at `investment_screener/backend/py_services/ta_sweep_batch.py`)
- **Current Inputs**: Data Window indicators extracted from TradingView CDP (RSI, Squeeze state, Vol Bias %, etc.)
- **Current Outputs**: Writes sweep results directly to `investment_screener/backend/data/ta-sweep-results.json`
- **JSON/Markdown Dependencies**: `ta-sweep-results.json` (being replaced)
- **Exact Repository Methods to Call**:
  - `instrument_repository.resolve_instrument(conn, ticker)` to ensure instrument exists.
  - `event_repository.insert_event(conn, event_dict)` to save the indicators.
- **Exact SQLite Tables/Views Required**: `instrument`, `intelligence_event`
- **Exact Files That Must Change**:
  - `plugins/tradingview/scripts/ta_sweep_batch.py`
- **Test Files Affected**:
  - `plugins/tradingview/tests/test_ta_sweep_batch.py`
- **Validation Strategy**: Execute `python3 plugins/tradingview/scripts/ta_sweep_batch.py --ticker MSFT --dry-run` and verify that a database insert call is logged, then run a query on `intelligence_event` for `event_type = 'TECHNICAL_SWEEP'` to assert fields populate correctly.
- **Rollback Strategy**: Retain a `--legacy-json` flag in the script to fall back to writing directly to `ta-sweep-results.json` if SQLite writes fail.

### Item 2: `daily_brief.py`
- **Current Code Path**: `plugins/portfolio-advisor/scripts/daily_brief.py` (and symlinked at `investment_screener/backend/py_services/daily_brief.py`)
- **Current Inputs**: Reads conviction bands from `ta-sweep-results.json` and target weights from `target-portfolio.json`.
- **Current Outputs**: Writes daily briefs to `investment_screener/backend/data/daily-briefs/YYYY-MM-DD.json`
- **JSON/Markdown Dependencies**: `ta-sweep-results.json` (reads), `target-portfolio.json` (reads - remains JSON)
- **Exact Repository Methods to Call**:
  - `event_repository.get_latest_event_by_type_and_ticker(conn, 'TECHNICAL_SWEEP', ticker)` to replace the JSON sweep read.
  - `event_repository.insert_event(conn, event_dict)` to save the generated brief.
- **Exact SQLite Tables/Views Required**: `intelligence_event`
- **Exact Files That Must Change**:
  - `plugins/portfolio-advisor/scripts/daily_brief.py`
- **Test Files Affected**:
  - `investment_screener/backend/tests/py_services/test_daily_brief.py`
- **Validation Strategy**: Run the script and query SQLite to verify the `REVIEW_DAILY` event matches the structure of the legacy daily brief JSON outputs.
- **Rollback Strategy**: Run with `--legacy-json` flag to write to the legacy `daily-briefs/` file directory.

### Item 3: `compute_conviction_scores.py`
- **Current Code Path**: `investment_screener/backend/py_services/compute_conviction_scores.py`
- **Current Inputs**: `ta-sweep-results.json`, `target-portfolio.json`
- **Current Outputs**: Evaluates and outputs raw conviction scores to terminal stdout.
- **JSON/Markdown Dependencies**: `ta-sweep-results.json` (reads), `target-portfolio.json` (reads)
- **Exact Repository Methods to Call**:
  - `event_repository.get_latest_event_by_type_and_ticker(conn, 'TECHNICAL_SWEEP', ticker)` for each holding.
- **Exact SQLite Tables/Views Required**: `intelligence_event`, `instrument`
- **Exact Files That Must Change**:
  - `investment_screener/backend/py_services/compute_conviction_scores.py`
- **Test Files Affected**:
  - `investment_screener/backend/tests/py_services/test_compute_conviction_scores.py`
- **Validation Strategy**: Assert conviction values returned from repository queries match scores calculated using legacy flat-file JSON formats.
- **Rollback Strategy**: Use conditional logic block checking `--legacy-json` command line flags to toggle back to file reads.

### Item 4: `dailybrief.ts` (API Route)
- **Current Code Path**: `investment_screener/backend/src/routes/dailybrief.ts`
- **Current Inputs**: Reads latest JSON file from `data/daily-briefs/` on disk.
- **Current Outputs**: Express JSON HTTP response `/api/daily-brief/latest`
- **JSON/Markdown Dependencies**: Latest daily brief JSON snapshot file.
- **Exact Repository Methods to Call**:
  - bridge utility `python3 rebuild_db.py --query-latest-brief` (which internally calls `event_repository.get_latest_event_by_type(conn, 'REVIEW_DAILY')`).
- **Exact SQLite Tables/Views Required**: `intelligence_event`
- **Exact Files That Must Change**:
  - `investment_screener/backend/src/routes/dailybrief.ts`
- **Test Files Affected**:
  - `investment_screener/backend/tests/api/portfolio.spec.ts` (Express endpoint test)
- **Validation Strategy**: Verify GET `/api/daily-brief/latest` returns structured metrics matching legacy JSON fields (e.g. macro_regime, conviction_scores).
- **Rollback Strategy**: Try-catch block falling back to reading raw files in `data/daily-briefs/` if bridge execution returns empty string or throws error.

### Item 5: `daily-loop/SKILL.md`
- **Current Code Path**: `plugins/portfolio-advisor/skills/daily-loop/SKILL.md` (and symlinked in `.agents/skills/daily-loop/SKILL.md`)
- **Current Inputs**: Instructs agent to check file statuses on disk.
- **Current Outputs**: Execution sequence instructions.
- **JSON/Markdown Dependencies**: Legacy checklist files.
- **Exact Repository Methods to Call**: None (calls `rebuild_db.py` CLI).
- **Exact SQLite Tables/Views Required**: None (checks database status command).
- **Exact Files That Must Change**:
  - `plugins/portfolio-advisor/skills/daily-loop/SKILL.md`
- **Test Files Affected**: None (Markdown only).
- **Validation Strategy**: Verify daily-loop orchestration executes smoothly.
- **Rollback Strategy**: Revert Markdown file changes using Git.

### Item 6: `daily-loop-agent.md`
- **Current Code Path**: `plugins/portfolio-advisor/agents/daily-loop-agent.md` (and symlinked in `.agents/agents/daily-loop-agent.md`)
- **Current Inputs**: Directs sub-agent to find daily brief JSON files on disk.
- **Current Outputs**: Chat dialog directives.
- **JSON/Markdown Dependencies**: Markdown prompt instructions.
- **Exact Repository Methods to Call**: None (directs agent to query ledger commands).
- **Exact SQLite Tables/Views Required**: None.
- **Exact Files That Must Change**:
  - `plugins/portfolio-advisor/agents/daily-loop-agent.md`
- **Test Files Affected**: None.
- **Validation Strategy**: Prompt daily-loop-agent in a test chat to run daily loop and verify it references database commands rather than filesystem directory checks.
- **Rollback Strategy**: Revert system instruction prompt changes using Git.

---

## Estimated PR & Commit Boundaries

1. **Commit 1 (Prerequisite)**: Implement prerequisite event repository query helpers in `event_repository.py` and write unit tests verifying their accuracy.
2. **Commit 2 (Sweep & Conviction Score persistence)**: Rewrite `ta_sweep_batch.py` and `compute_conviction_scores.py` with tests.
3. **Commit 3 (Daily Brief generation)**: Rewrite `daily_brief.py` to fetch sweeps and persist briefs to the database.
4. **Commit 4 (API Endpoints & Orchestration)**: Rewire backend Express route `dailybrief.ts`, update `daily-loop/SKILL.md`, and update `daily-loop-agent.md` system prompts.

---

## Test & Validation Gate Checklists

### Required Test Additions BEFORE Code Changes (TDD)
- [ ] Add `test_get_latest_event_by_type` test inside `test_audit_json_usage.py` or event tests.
- [ ] Add `test_get_latest_event_by_type_and_ticker` verifying limit 1 ordering.
- [ ] Write failing test in `test_ta_sweep_batch.py` checking event insertion logic.

### Required Validation BEFORE Cutover
- [ ] Verify database WAL file size is healthy.
- [ ] Smoke test API endpoint with double-writes to verify idempotency checks don't block inserts.
