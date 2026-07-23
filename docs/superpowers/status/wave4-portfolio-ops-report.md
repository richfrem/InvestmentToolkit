# Wave 4 (Portfolio Operations — trade log, order executions, cash flows) — Report

Status: **Complete on branch `worktree-wave4-portfolio-ops`, pushed to `origin`, PR open, awaiting user review/merge.**

## What Wave 4 Accomplished

Migrated three gitignored, never-committed JSON/JSONL flat files into the v3.2 SQLite domain
model:

- `trade-log.json` (52 entries) → `trade_log_entry` table.
- `orders_executed.jsonl` (8 records) → `order_execution` table.
- `cash_flows.json` (3 flows + 1 global baseline) → `cash_flow` + `cash_flow_baseline` tables.

Every real producer and consumer of these three files was cut over to the SQLite repository
layer, and the JSON/JSONL files were archived (locally, since all three are gitignored private
data — see Archive Evidence).

## Wave KPI Table

| KPI | Value |
|---|---|
| JSON/JSONL files in scope | 3 real (+1 tracked `.example` template) |
| JSON/JSONL files archived | 4 (3 local-only `mv`, 1 `git mv`) |
| Real producers migrated | 3 / 3 (`order_risk_gates.py` write path, `trading.ts` write path, `cash_flow_cli.py` — new) |
| Real consumers migrated | 5 / 5 (`order_risk_gates.py` read, `execution_quality_scorecard.py`, `ytd_return.py`, `portfolio.ts` gate, `trading.ts` read) |
| New tables added | `trade_log_entry`, `order_execution`, `cash_flow`, `cash_flow_baseline` |
| New columns added (schema evolution) | `trade_log_entry.tv_order_id` (Task 11 finding) |
| Real bugs found & fixed | 2 (see below) |
| Real trade log rows migrated | 52 (verified 3x: dry-run, `--write`, direct `sqlite3` query) |
| Real order execution rows migrated | 8 (verified 3x) |
| Real cash flow rows migrated | 3 + 1 baseline ($37,426 CAD, 2026-01-01) (verified 3x) |
| Test regressions introduced (net) | 0 (128 backend TS tests passing, same 2 documented pre-existing baseline failures; 34/34 targeted Python tests passing across every module touched) |
| Commits this wave | 13 (7 pre-existing from prior session + 6 this session) |

## Real Migration Write — Verified Row Counts (Task 7)

Dry-run (re-confirmed at start of this session, matching the prior session's numbers exactly):

```json
{
  "trade_log_entries_count": 52, "trade_log_entries_would_insert_count": 52,
  "order_executions_count": 8, "order_executions_would_insert_count": 8,
  "cash_flows_count": 3, "cash_flows_would_insert_count": 3,
  "cash_flow_baseline_present": true, "warnings": []
}
```

`--write` run: identical counts inserted (`trade_log_entries_inserted: 52`,
`order_executions_inserted: 8`, `cash_flows_inserted: 3`, `cash_flow_baseline_written: true`).
No delta between dry-run and real write — Hard-Stop Conditions 1/2 clear.

Independently verified via direct `sqlite3` query against `domain_model.sqlite` (not trusting the
script's own printed summary):

```
sqlite3 data/domain_model.sqlite "SELECT count(*) FROM trade_log_entry;"       -> 52
sqlite3 data/domain_model.sqlite "SELECT count(*) FROM order_execution;"       -> 8
sqlite3 data/domain_model.sqlite "SELECT count(*) FROM cash_flow;"             -> 3
sqlite3 data/domain_model.sqlite "SELECT * FROM cash_flow_baseline;"           -> ALL|37426.0|2026-01-01
```

The migration was re-run once more (Task 11) after adding the `tv_order_id` column, to backfill
the 3 historical entries that had a real `tvOrderId` value — still exactly 52 rows (idempotent
upsert, no duplication), now 3 rows carry `tv_order_id`.

## Producer/Consumer Cutover Table

| File | Function(s) | Old path | New path | Verified |
|---|---|---|---|---|
| `investment_screener/backend/py_services/order_risk_gates.py:1004` | `get_trade_log_entries()` | `trade-log.json` (read) | `trade_log_entry_repository.list_trade_log_entries()` | 6/6 targeted tests, direct CLI read of real DB (52 entries) |
| `investment_screener/backend/py_services/order_risk_gates.py:1239` | `log_order_execution()` | `orders_executed.jsonl` (append) | `order_execution_repository.insert_order_execution()` | 6/6 targeted tests |
| `investment_screener/backend/py_services/execution_quality_scorecard.py:52` | `load_orders_executed()` / `build_report()` | `orders_executed.jsonl` (read) | `order_execution_repository.list_order_executions()` | 11/11 targeted tests, real CLI run against migrated data (8 executions, correct decision breakdown) |
| `plugins/portfolio-advisor/scripts/ytd_return.py` (canonical; symlinked into `investment_screener/backend/py_services/ytd_return.py` and `plugins/portfolio-advisor/skills/ytd-return/scripts/ytd_return.py`) | new `load_cash_flows()`, wired into `calculate_twr()` | `cash_flows.json` (read) | `cash_flow_repository.list_cash_flows()` / `get_cash_flow_baseline()` | 4/4 targeted tests, real CLI run against migrated data (3 flows, $37,426 baseline, correct TWR sub-periods) |
| `investment_screener/backend/src/routes/portfolio.ts:80` | `loadYtdPerformanceReport()` | `fs.existsSync(cash_flows.json)` gate | removed — `ytd_return.py`'s own error exit + `spawnPythonScript`'s existing non-zero-exit → `null` rejection path now performs the gate | TS build clean, 128/128 non-baseline backend tests passing |
| `investment_screener/backend/src/routes/trading.ts:260-345` | `readLog()` / `writeLog()`, all 6 route handlers (`/log`, `/log/suggest`, `PATCH /log/:id`, `/modify`, `/cancel`, `/log/sync-from-tv`) | `trade-log.json` (read/write) | `TradeLogRepository` (+ `InvestmentRepository` for ticker resolution, `PortfolioRepository` for account upsert) | 6/6 new route-level tests + 7/7 `TradeLogRepository` unit tests, TS build clean, real `dist/routes/trading.js` read of production DB (52 entries, correct shape) |
| `investment_screener/backend/py_services/cash_flow_cli.py` (new) | `--add` / `--list` | (no prior producer — `cash_flows.json` was hand-edited) | `cash_flow_repository.insert_cash_flow()` | Existing tests from prior session (Task 5), unchanged this session |

## Real Bugs Found and Fixed (not scope creep)

1. **`TradeLogRepository` opened before `InvestmentRepository` in `writeLog()` would permanently
   lock a fresh DB into a narrower `investment` table schema.** `TradeLogRepository.ts`'s own
   minimal `CREATE TABLE IF NOT EXISTS investment` (needed only for its FK) would win the race on
   a brand-new file, since `CREATE TABLE IF NOT EXISTS` is a no-op once any repository creates the
   table first, and only `sector`/`industry` are in `db_client.py`'s `SCHEMA_EVOLUTIONS` self-heal
   list — `lifecycle_status` and other `InvestmentRepository`-only columns would be silently
   missing. Caught by the new test `"writeLog() then readLog() round-trips an entry"` failing with
   `SqliteError: no such column: lifecycle_status`. Fixed by opening `InvestmentRepository` first
   in `writeLog()` (`investment_screener/backend/src/routes/trading.ts`).
2. **`tvOrderId` would have been silently dropped going forward.** The original Task 1
   `trade_log_entry_repository.py` intentionally excluded `tvOrderId` ("no corresponding DDL
   column"), reasonable in isolation, but `trading.ts`'s `/modify`, `/cancel`, and
   `/log/sync-from-tv` routes actively match live TradingView orders against a logged entry's
   `tvOrderId` — dropping it on cutover would have silently broken that reconciliation for every
   entry logged from this point forward (3 of the 52 real historical entries already carry a
   non-null value, all `status: cancelled` so not live-order-critical historically, but the *code
   path* is live and would have broken on the next real order). Fixed by adding a `tv_order_id`
   column via `db_client.py`'s existing `SCHEMA_EVOLUTIONS` self-heal mechanism (additive
   `ALTER TABLE`, no data loss, mirrored in `TradeLogRepository.ts` and
   `trade_log_entry_repository.py`), then re-running the migration (idempotent upsert) to backfill
   the 3 historical values.

## Test Results

- **Backend TS suite** (`npm test -w backend`): 128 passing (up from 121 baseline — 7 net-new
  tests this wave), 2 failing — both the documented pre-existing baseline failures
  (`InvestmentRepository` real-sqlite parity test requiring a live broker DB;
  `zod-schemas.spec.ts`'s production `target-portfolio.json` validation, confirmed unrelated to
  this migration in Wave 3). Zero new failures.
- **TS build** (`npm run build -w backend`): clean, no errors.
- **Targeted Python tests** across every file touched this wave: 34/34 passing
  (`test_order_risk_gates_trade_log_sqlite.py`, `test_trade_log_entry_repository.py`,
  `test_execution_quality_scorecard.py`, `test_ytd_return.py`,
  `test_ytd_return_cash_flow_sqlite.py`, `test_migrate_wave4_to_sqlite.py`,
  `test_cash_flow_repository.py`, `test_order_execution_repository.py`).
- **`order_risk_gates.py`'s wider test surface**: 96/98 passing when filtered to
  `order_risk_gates`/`trade_log_entry_repository`/`order_execution_repository`/`place_order`
  keywords. The 2 failures (`test_place_order_gates.py::test_fresh_portfolio_exits_0`,
  `::test_size_cap_exits_3`) are environmental — `chrome-remote-interface` npm package missing /
  TradingView CDP unreachable in this worktree (confirmed via the `ERR_MODULE_NOT_FOUND` in the
  traceback), unrelated to the SQLite cutover.
- **Full 1,431-test `py_services` suite**: attempted twice, did not complete within the session's
  practical time budget — several unrelated tests (e.g. `test_backtest_report_generator.py`) run
  real `git log`/network-bound operations that made a full run impractically slow, and
  `pytest-timeout` is not installed (CLAUDE.md's no-manual-`pip install` rule blocks adding it
  ad hoc mid-wave). **Not run to completion — flagged, not silently skipped.** The targeted
  regression testing above (every file this wave touched, plus the full backend TS suite) is the
  real evidence for "no new failures"; a full Python suite run is recommended as a fast follow
  before or shortly after merge.

## Archive Evidence

`git check-ignore` + `git log --all -- <path>` confirmed all three real data files were **never
committed** (all three gitignored, empty git history):

- `investment_screener/backend/data/trade-log.json` → **local-only `mv`** to
  `ARCHIVE/investment_screener/backend/data/trade-log.json` (not `git mv`, not added to git —
  matches its pre-migration status of never being tracked).
- `investment_screener/backend/data/orders_executed.jsonl` → same, local-only `mv`.
- `investment_screener/backend/data/cash_flows.json` → same, local-only `mv`.
- `investment_screener/backend/data/cash_flows.json.example` (the one tracked, non-private
  template) → `git mv` to `ARCHIVE/investment_screener/backend/data/cash_flows.json.example`,
  committed.

Archive-readiness grep (Hard-Stop Conditions 4, 5, 6, 8) confirmed clean: no remaining runtime
read/write against the three old paths in `.py`/`.ts`/`.tsx` files (only docstrings, test
fixtures, and the migration script's own source-path defaults reference the filenames now — all
expected). No ad-hoc SQLite connection against `trade_log_entry`/`order_execution`/`cash_flow`
tables outside the designated repository modules (`trade_log_entry_repository.py`,
`order_execution_repository.py`, `cash_flow_repository.py`, `TradeLogRepository.ts`).

## Rollback Instructions

1. SQLite data is intact: `investment_screener/backend/data/domain_model.sqlite` (gitignored,
   real file on disk) still holds all migrated rows.
2. Archived JSON files are intact on disk: `ARCHIVE/investment_screener/backend/data/{trade-log.json,orders_executed.jsonl,cash_flows.json}`
   (local-only, not in git — copy back to `investment_screener/backend/data/` to restore).
3. To revert code: `git revert` the 6 commits from `050cec72` (order_risk_gates cutover) through
   `6d17c96e` (archive), in reverse order, or simply check out `main`'s pre-Wave-4 state — no
   destructive schema changes were made (new tables/columns only, additive `ALTER TABLE`).
4. No `rm` was ever used — every archive step was `mv`/`git mv`.

## Full Commit List (this wave, chronological)

Prior session (verified present, unchanged this session):
1. `bb797348` — `feat(wave4): add trade_log_entry_repository.py`
2. `23b4d4f5` — `feat(wave4): add order_execution_repository.py`
3. `2b221de9` — `feat(wave4): add TradeLogRepository.ts`
4. `c8910078` — `feat(wave4): add cash_flow_repository.py`
5. `1cef5127` — `feat(wave4): add cash_flow_cli.py write path`
6. `4b0a7996` — `feat(wave4): add migrate_wave4_to_sqlite.py`
7. `d9dc7967` — `docs(wave4): add Wave 4 portfolio-ops implementation plan`

This session:
8. `050cec72` — `feat(wave4): cut order_risk_gates.py over to SQLite repositories` (Task 8; Task 7's real migration write has no git-trackable artifact, `domain_model.sqlite` is gitignored)
9. `7cff0e82` — `feat(wave4): cut execution_quality_scorecard.py over to SQLite` (Task 9)
10. `93d0946a` — `feat(wave4): cut ytd_return.py + portfolio.ts cash-flow gate over to SQLite` (Task 10)
11. `2fe6eb58` — `feat(wave4): cut trading.ts trade-log routes over to SQLite` (Task 11, includes the `tv_order_id` schema fix)
12. `51d61d57` — `chore(wave4): archive-readiness cleanup — remove dead JSON-path references` (Task 12 prep)
13. `6d17c96e` — `chore(wave4): archive migrated JSON/JSONL files` (Task 12)
