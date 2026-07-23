# Domain Data Model v3.2 — Wave 4 (Portfolio Operations) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate trade-log, order-execution, and cash-flow data from JSON/JSONL flat files to the existing `trade_log_entry`, `order_execution`, `cash_flow`, and `cash_flow_baseline` SQLite tables (already defined in `db_client.py`'s DDL, currently unused), then cut over every real producer/consumer, and archive the retired JSON files.

**Architecture:** Follow the exact Wave 2/3 pattern already established in this repo: a Python repository module per table under `investment_screener/backend/py_services/domain_model/`, plus a TypeScript mirror repository (via `better-sqlite3`) only where a TS route is a real producer/consumer (trading.ts is; portfolio.ts/ytd_return.py's cash-flow path is Python-only). One writer per table. Migration runs dry-run first with an explicit approval gate before any real write.

**Tech Stack:** Python 3 stdlib `sqlite3`, `better-sqlite3` (TS), existing `domain_model.sqlite`.

## Global Constraints

- One writer per table (ADR-029 "one writer per table" rule, restated in `PortfolioRepository.ts`'s own docstring).
- No script may open its own ad-hoc SQLite connection against these tables outside the designated repository module (Hard-Stop Condition 6 in the Wave 4 kickoff prompt).
- Account balances / running totals are always computed live from ledger facts, never stored as a denormalized column (ADR-030 principle, explicitly carried forward into Wave 4 scope by the kickoff prompt) — `cash_flow_baseline.starting_balance_cad` is the one allowed exception (a genuine external fact: the balance on the day tracking started, not derivable from the ledger itself).
- Real data migration requires: dry-run report generated first → explicit user sign-off → then the real write. **Never skip this gate.**
- Archive with `git mv path ARCHIVE/<mirrored path>` — never `rm` — and only after all Hard-Stop Conditions in the kickoff prompt are independently confirmed true.
- `generate_track_record_report.py`'s docstring claims trade-log.json as an input, but its actual code (`build_report(predictions_path, graded_path)`) never reads or references trade-log.json anywhere in the file body — confirmed dead/stale docstring text during Task 0 investigation. Do not build a cutover task for it; optionally correct the docstring in Task 8.
- `apply_portfolio_updates.py` is confirmed OUT OF SCOPE for Wave 4 (Task 0 finding): it only reads/writes `portfolio.json` + `account_investment` rows (Wave 3's domain, already migrated), never touches any of this wave's three files.
- `trading.ts`'s `GET /audit/today` route reads `plugins/tradingview/audit/orders-{date}.jsonl` — a **different, date-sharded file**, not `orders_executed.jsonl`. Do not treat it as a second `orders_executed.jsonl` consumer.

---

## Task 0 Findings (already complete — do not re-investigate, verified against real current code)

**`trade-log.json`** — Producer: `investment_screener/backend/src/routes/trading.ts` `writeLog()`/`readLog()` (lines ~260-267), a read-modify-write JSON file, called from 6 route handlers (`POST /log`, `POST /log/suggest`, `PATCH /log/:id`, `POST /modify`, `POST /cancel`, `POST /log/sync-from-tv`). Consumers: `GET /log` route → frontend (`TradeLog.tsx`, `TradeLogModal.tsx`, `TradePrepModal.tsx` via `fetchTradeLog()`), and `investment_screener/backend/py_services/order_risk_gates.py` (`get_trade_log_entries()` line 1001, `find_matching_trade_log_entry()` line 1025, `wait_for_trade_log_entry()` line 1082), called from `plugins/tradingview/scripts/place_order.py:660-664` (symlinked as `investment_screener/backend/py_services/place_order.py`) during post-trade reconciliation.

**`orders_executed.jsonl`** — Producer: `order_risk_gates.py::log_order_execution()` (lines 1209-1263, append-only), called from `place_order.py:536,540,668`. Consumer: `execution_quality_scorecard.py::load_orders_executed()` (lines 41-48), invoked from `plugins/portfolio-advisor/agents/weekly-review-agent.md:39`. Exactly one producer chain, one consumer — no dead code.

**`cash_flows.json`** — **No code producer at all** — it's hand-maintained by the user directly (only `cash_flows.json.example` exists as a template). Sole consumer: `plugins/portfolio-advisor/scripts/ytd_return.py` (symlinked as `investment_screener/backend/py_services/ytd_return.py`), reading `CASH_FLOWS_PATH` at line 188, using `flows_data.get("cash_flows", [])` at line 199. `investment_screener/backend/src/routes/portfolio.ts::loadYtdPerformanceReport()` (lines 85-99) only checks `fs.existsSync()` as a gate, then spawns `ytd_return.py --json` and reads its *output* file — it never reads `cash_flows.json` contents directly, so it is not a second content-consumer, just an orchestration wrapper.

---

## Task 1: Python `trade_log_entry_repository.py`

**Files:**
- Create: `investment_screener/backend/py_services/domain_model/trade_log_entry_repository.py`
- Test: `investment_screener/backend/tests/py_services/domain_model/test_trade_log_entry_repository.py`

**Interfaces:**
- Produces: `upsert_trade_log_entry(conn, entry: dict) -> None` (keyed by `entry_id`; dict keys match trade-log.json's existing field names — read 3 real sample entries from `investment_screener/backend/data/trade-log.json` first to confirm exact field names before writing this function), `list_trade_log_entries(conn, account_id: str | None = None) -> list[dict]`, `get_trade_log_entry(conn, entry_id: str) -> dict | None`, `delete_trade_log_entry(conn, entry_id: str) -> None` (trading.ts's `PATCH`/`cancel` flows mutate/delete individual entries, not just append).
- Consumes: `investment_screener/backend/py_services/domain_model/db_client.py`'s `get_connection()`/`initialize_db()` (read this file's existing repository modules, e.g. `alert_repository.py`, for the exact connection-acquisition pattern to mirror — do not invent a new one).

- [ ] Read `investment_screener/backend/data/trade-log.json` and `alert_repository.py` in full before writing code.
- [ ] Write failing tests for upsert/list/get/delete against a `tmp_path` SQLite file (mirror `test_account_investment_repository.py`'s fixture pattern if it exists — check `investment_screener/backend/tests/py_services/domain_model/` for the exact existing test fixture style first).
- [ ] Run tests, confirm they fail with `ModuleNotFoundError`.
- [ ] Implement `trade_log_entry_repository.py` against the real `trade_log_entry` DDL (`db_client.py` lines 388-404).
- [ ] Run tests, confirm pass.
- [ ] Commit: `feat(wave4): add trade_log_entry_repository.py`

## Task 2: TS `TradeLogRepository.ts`

**Files:**
- Create: `investment_screener/backend/src/services/TradeLogRepository.ts`
- Test: `investment_screener/backend/tests/services/TradeLogRepository.test.ts` (check actual test dir name/pattern used by `InvestmentRepository.ts`'s own tests first)

**Interfaces:**
- Produces: `upsertTradeLogEntry(entry)`, `listTradeLogEntries(accountId?)`, `getTradeLogEntry(entryId)`, `deleteTradeLogEntry(entryId)`, `ensureSchema()` (mirrors `PortfolioRepository.ts`'s own `ensureSchema()` pattern verbatim — transcribe the same `trade_log_entry` DDL as `db_client.py`, per that file's own docstring convention).
- Consumes: `better-sqlite3` `Database` — read `PortfolioRepository.ts` in full first and copy its class-construction/connection pattern exactly (same DB path resolution, same `ensureSchema()` idempotency).

- [ ] Read `PortfolioRepository.ts` and `InvestmentRepository.ts` in full first.
- [ ] Write failing tests for each method against a temp SQLite file.
- [ ] Run tests, confirm fail.
- [ ] Implement `TradeLogRepository.ts`.
- [ ] Run tests, confirm pass.
- [ ] Commit: `feat(wave4): add TradeLogRepository.ts`

## Task 3: Python `order_execution_repository.py`

**Files:**
- Create: `investment_screener/backend/py_services/domain_model/order_execution_repository.py`
- Test: `investment_screener/backend/tests/py_services/domain_model/test_order_execution_repository.py`

**Interfaces:**
- Produces: `insert_order_execution(conn, execution: dict) -> None` (append-only semantics matching the JSONL source — no update/delete needed, mirror `order_risk_gates.py::log_order_execution()`'s exact record shape, read that function's full body first), `list_order_executions(conn, investment_id: str | None = None) -> list[dict]`.
- Consumes: same `db_client.py` connection pattern as Task 1.

- [ ] Read `order_risk_gates.py` lines 1180-1270 (`log_order_execution` and its record construction) in full first.
- [ ] Write failing tests.
- [ ] Run, confirm fail.
- [ ] Implement against `order_execution` DDL (`db_client.py` lines 408-418).
- [ ] Run, confirm pass.
- [ ] Commit: `feat(wave4): add order_execution_repository.py`

## Task 4: Python `cash_flow_repository.py`

**Files:**
- Create: `investment_screener/backend/py_services/domain_model/cash_flow_repository.py`
- Test: `investment_screener/backend/tests/py_services/domain_model/test_cash_flow_repository.py`

**Interfaces:**
- Produces: `insert_cash_flow(conn, flow: dict) -> None`, `list_cash_flows(conn, account: str | None = None) -> list[dict]`, `get_cash_flow_baseline(conn, account: str) -> dict | None`, `upsert_cash_flow_baseline(conn, account: str, starting_balance_cad: float, starting_date: str) -> None`.
- Consumes: same `db_client.py` connection pattern.

- [ ] Read `cash_flows.json.example` and `ytd_return.py` lines 180-210 in full first to confirm exact field names/shape (including the baseline concept — check whether `ytd_return.py` currently has its own hardcoded starting-balance logic that should move into `cash_flow_baseline`).
- [ ] Write failing tests.
- [ ] Run, confirm fail.
- [ ] Implement against `cash_flow`/`cash_flow_baseline` DDL (`db_client.py` lines 421-437).
- [ ] Run, confirm pass.
- [ ] Commit: `feat(wave4): add cash_flow_repository.py`

## Task 5: Cash-flow write path (CLI, since no producer existed before)

**Files:**
- Create: `investment_screener/backend/py_services/cash_flow_cli.py`
- Test: `investment_screener/backend/tests/py_services/test_cash_flow_cli.py`

**Interfaces:**
- Consumes: Task 4's `cash_flow_repository.py`.
- Produces: a `--add` CLI (date, type, amount_cad, account, portfolio_value_before_flow_cad) so the user has a real replacement for hand-editing `cash_flows.json`, plus `--list`.

- [ ] Write failing test for `--add` writing a row via the repository.
- [ ] Run, confirm fail.
- [ ] Implement CLI (argparse, mirror an existing simple CLI script's argument style, e.g. `update_targets.py`).
- [ ] Run, confirm pass.
- [ ] Commit: `feat(wave4): add cash_flow_cli.py write path`

## Task 6: Migration script — dry run + gated real write

**Files:**
- Create: `investment_screener/backend/py_services/domain_model/migrate_wave4_to_sqlite.py`
- Test: `investment_screener/backend/tests/py_services/domain_model/test_migrate_wave4_to_sqlite.py`

**Interfaces:**
- Consumes: Tasks 1, 3, 4's repositories; reads `trade-log.json`, `orders_executed.jsonl`, `cash_flows.json` directly.
- Produces: `--dry-run` (default) prints per-file source count vs. would-be-inserted-row count, no writes; `--write` performs the real migration (idempotent upserts where the table supports it, since re-running must not duplicate rows).

- [ ] Write failing test: dry-run mode produces correct counts against a fixture JSON file, writes zero rows.
- [ ] Run, confirm fail.
- [ ] Implement, mirroring `migrate_portfolio_to_sqlite.py`'s or `migrate_target_portfolio_to_sqlite.py`'s existing dry-run/write flag pattern (read one of those files first).
- [ ] Run, confirm pass.
- [ ] Commit: `feat(wave4): add migrate_wave4_to_sqlite.py`
- [ ] **STOP HERE.** Run `python3 investment_screener/backend/py_services/domain_model/migrate_wave4_to_sqlite.py --dry-run` against the real data files, capture the report, and present it for explicit user sign-off before Task 7 runs `--write`. This is the plan's hard non-negotiable gate — do not proceed past this step autonomously.

## Task 7: Real migration write (gated — only after Task 6's explicit sign-off)

- [ ] Run `python3 .../migrate_wave4_to_sqlite.py --write` against real data.
- [ ] Verify row counts match the dry-run report exactly (Hard-Stop Condition 1/2 — any unexplained delta stops here).
- [ ] Commit: `feat(wave4): migrate trade-log/orders-executed/cash-flows to SQLite (data)` — note in the commit body that JSON files are untouched (still source of truth) until cutover completes.

## Task 8: Cutover `order_risk_gates.py` (Python side — trade-log read + order-execution write)

**Files:**
- Modify: `investment_screener/backend/py_services/order_risk_gates.py` (`get_trade_log_entries`, `log_order_execution`)

- [ ] Read the full current function bodies first.
- [ ] Update existing tests for these functions (if any exist under `investment_screener/backend/tests/py_services/test_order_risk_gates.py`) to assert against the repository instead of the JSON/JSONL file; if no such tests exist, write them first (TDD).
- [ ] Replace JSON/JSONL I/O with calls into `trade_log_entry_repository.py` (read-only here) and `order_execution_repository.py` (write).
- [ ] Run full test suite for this file, confirm pass.
- [ ] Commit: `feat(wave4): cut order_risk_gates.py over to SQLite repositories`

## Task 9: Cutover `execution_quality_scorecard.py`

**Files:**
- Modify: `investment_screener/backend/py_services/execution_quality_scorecard.py` (`load_orders_executed`)

- [ ] Read full current function body first.
- [ ] Update/write tests asserting the function now reads via `order_execution_repository.list_order_executions()`.
- [ ] Implement, run tests, confirm pass.
- [ ] Commit: `feat(wave4): cut execution_quality_scorecard.py over to SQLite`

## Task 10: Cutover `ytd_return.py` + `portfolio.ts`

**Files:**
- Modify: `investment_screener/backend/py_services/ytd_return.py` (cash-flow load), `investment_screener/backend/src/routes/portfolio.ts` (`loadYtdPerformanceReport`'s existence-check gate)

- [ ] Read both files' full current logic first.
- [ ] Update/write tests for `ytd_return.py`'s cash-flow loading against `cash_flow_repository.py`.
- [ ] Implement, run tests, confirm pass.
- [ ] Update `portfolio.ts`'s gate check to reflect SQLite-backed data (e.g. check `cash_flow` table has rows, not `fs.existsSync(cashFlowsFile)`) — confirm whether Node needs a minimal read via a spawned Python check or a lightweight `CashFlowRepository.ts` read-only class; prefer reusing `cash_flow_cli.py --list` via existing `spawnPythonScript` helper already used one line above, to avoid adding a redundant TS repository for a gate-only check.
- [ ] Commit: `feat(wave4): cut ytd_return.py + portfolio.ts cash-flow gate over to SQLite`

## Task 11: Cutover `trading.ts` (trade-log read/write)

**Files:**
- Modify: `investment_screener/backend/src/routes/trading.ts` (`readLog`, `writeLog`, and every route calling them)

- [ ] Read the full current route file first (all 6+ handlers).
- [ ] Update/write route-level tests asserting SQLite-backed behavior (check `investment_screener/backend/tests/api/` for existing trading route test coverage first).
- [ ] Replace `readLog()`/`writeLog()` internals with `TradeLogRepository.ts` calls, preserving every route's existing external API contract (response shape must not change — frontend components are unmodified).
- [ ] Run full test suite, confirm pass.
- [ ] Commit: `feat(wave4): cut trading.ts trade-log routes over to SQLite`

## Task 12: Archive-readiness verification and archive

- [ ] Grep-verify (Hard-Stop Conditions 4, 5, 6, 8): no remaining runtime code path reads/writes `trade-log.json`, `orders_executed.jsonl`, or `cash_flows.json` (docs/plans references are fine, runtime code is not).
- [ ] Run the full test suite (frontend + backend + py_services) and confirm no new failures vs. the documented pre-existing `zod-schemas.spec.ts` baseline failure.
- [ ] Confirm rollback remains possible (SQLite data + archived JSON both still present, nothing deleted).
- [ ] `git mv investment_screener/backend/data/trade-log.json ARCHIVE/investment_screener/backend/data/trade-log.json`, same for `orders_executed.jsonl`, `cash_flows.json`, `cash_flows.json.example` (confirm gitignore status of each individually first — `cash_flows.json` itself may be gitignored private data per Task 0's earlier finding that only `.example` is tracked; if so, that file must be a **local-only `mv`, never `git mv`**, per this repo's private-data archive rule).
- [ ] Commit: `chore(wave4): archive migrated JSON/JSONL files`

## Task 13: Wave exit artifacts

- [ ] Write `docs/superpowers/status/wave4-portfolio-ops-report.md` — KPI table, producer/consumer cutover table, real bugs found, validation evidence, archive evidence, rollback instructions, commit list.
- [ ] Write `docs/superpowers/status/wave4-handoff.md`.
- [ ] Push branch, open PR to `main` (do not merge).
- [ ] Verify remote branch matches local HEAD exactly.

---

## Self-Review Notes

- Task 0 findings are load-bearing for every later task's file-list — do not let a later task re-derive different assumptions.
- `generate_track_record_report.py` and `apply_portfolio_updates.py` are explicitly out of scope — flagged in Global Constraints so no task accidentally touches them.
- Hard gate before real data write is isolated to Task 6→7 boundary, not diffused across the plan.
