# Wave 0 — Schema and Repository Foundation — Report

## Scope covered by this report

Tasks 1–5 of Wave 0 (schema DDL + `domain_model_db_client`, `investment_repository`,
`account_repository`, `account_investment_repository`, `backfill_investment_universe`),
verified here with real test evidence before any Wave 1 work begins.

| Commit | Task |
|---|---|
| `dc10d595` | Task 1 — schema (`domain_model_db_client.py`, v3.2 DDL) |
| `e250200d` | Task 2 — `investment_repository.py` (`resolve_investment`, `get_investment`) |
| `211b077c` | Task 3 — `account_repository.py` |
| `166228a3` | Task 4 — `account_investment_repository.py` |
| `5db38a0f` | Task 5 — `backfill_investment_universe.py` |

## Commands run and real output

### Step 1 — full backend Python test suite

```
cd investment_screener/backend && python3 -m pytest tests/py_services/ -v 2>&1 | tail -30
```

Result: **24 failed, 1233 passed, 2 xfailed in 68.99s**.

All 24 failures are in 7 test files, none of which Wave 0 touched:

- `test_place_order_gates.py` (2 failures) — requires a live CDP connection to
  TradingView Desktop on port 9222 (`chrome-remote-interface` ESM resolution failing when
  no TV Desktop session/broker panel is reachable in this run).
- `test_fetch_consensus_for_ticker_returns_dict_or_none.py` (12 failures),
  `test_get_earnings_context_returns_prior_beat_rate.py` (1),
  `test_grade_earnings_expectations_classifies_beat_meet_miss.py` (5),
  `test_earnings_expectation_claim_round_trips_ledger.py` (2) — yfinance/earnings-consensus
  network-dependent tests.
- `test_daily_brief_ta_sweep_delegates.py` (1) and
  `test_evolution_event_correlation_report_generates_summary.py` (1) — pre-existing,
  environment/path-dependent failures unrelated to earnings or CDP, but also unrelated to
  Wave 0 (neither file touches `domain_model`, `investment_repository`,
  `account_repository`, or `account_investment_repository`).

This is the **exact same 24-failure set, same 7 files**, reported as the pre-existing
baseline in Task 5's own report (`.superpowers/sdd/task-5-report.md`), confirmed by
re-running the full suite fresh rather than trusting that prior report's claim. No new
failure category appeared. `git status --short` in this worktree is clean — none of the 7
failing files were modified by Wave 0.

Targeted domain_model regression subset (all 19 Wave 0 tests):

```
python3 -m pytest tests/py_services/ -k "domain_model or backfill or investment_repository or account_repository or account_investment" -v
```

Result: **19 passed, 1240 deselected in 2.41s.**

### Step 2 — T0/T0.5 gate

```
python3 run_tests.py
```

First run in this worktree **failed at T0** (`tsc: command not found` for both backend
and frontend builds) — this worktree had never had `npm install` run in
`investment_screener/` or `npm ci` run in `tradingview-cdp/` (per the CLAUDE.md pitfall
about `tradingview-cdp/` needing `npm ci` once). This is a worktree environment-setup gap,
not a Wave 0 code issue: the identical script passes clean in the main checkout without
any changes. Ran `npm install` in `investment_screener/` and `npm ci` in `tradingview-cdp/`
to bring this worktree's environment to parity, then re-ran.

Second run failed at the **Map Debt registry audit** step:
`can't open file '.../.agents/skills/self-evolution/scripts/audit_map_debt.py'` — this
worktree was also missing the gitignored, harness-managed `.agents/` directory entirely
(confirmed via `git check-ignore` and `git ls-files .agents`, and confirmed the main
checkout has it and passes this exact step). Copied `.agents/` from the main checkout into
this worktree (a local, gitignored, generated artifact — not a git-tracked change, no
`ln -s` used, no plugin-architecture symlink rule violated) to restore parity, then
re-ran.

Third run:

```
=== InvestmentToolkit Test Runner ===

T0 — TypeScript compile
  [OK] backend build
  [OK] frontend build

T0 — Python syntax checks
  [OK] (19/19 scripts)

T0 — Node.js syntax checks
  [OK] trading.js
  [OK] broker_data.js

T0 — Stale Path Regression
  [OK] No stale runtime paths found

T0 — CWD / Symlink Invariance
  [OK] tv_health_check.py from root (/)
  [OK] tv_health_check.py from repo root
  [OK] tv_health_check.py from skill dir
  [OK] TV_CDP_DIR override test passed (failed correctly with bad path)

T0 — Map Debt registry audit
  [OK] map-debt.md audit

T0.5 — Bridge smoke (portfolio_action.py via symlink)
  [OK] portfolio_action.py via symlink — 2 tickers: ['MSFT', 'AAPL']

[OK] All gates passed.
```

**All gates pass**, including the map-debt audit. `run_tests.py` does exactly what its
name suggests (a T0/T0.5 correctness + map-debt gate) — nothing unexpected beyond the two
environment-setup gaps above, both diagnosed and resolved with standard, sanctioned
project commands (`npm install`, `npm ci`, a copy of a gitignored generated directory).

## Step 3 — Wave 0 KPI table

| KPI | Value |
|---|---|
| Wave | 0 |
| Active JSON/JSONL files before | Unchanged — no JSON domain touched this wave |
| Active JSON/JSONL files after | Unchanged — no JSON domain touched this wave |
| Files archived | 0 |
| JSON reads removed | 0 |
| JSON writes removed | 0 |
| Producers migrated (n / total) | 0 / 0 (no producer targeted this wave) |
| Consumers migrated (n / total) | 0 / 0 (no consumer targeted this wave) |
| Plugin/skill/agent references updated | 0 (none reference domain_model tables yet) |
| Context-bundle files removed | 0 |
| Remaining JSON exceptions (with rationale) | N/A — this wave is schema-only, not a domain cutover |
| Backend pytest suite | 1233 passed, 24 pre-existing/unrelated failed, 2 xfailed (24/24 match Task 5's documented baseline — no new failures) |
| Wave 0 domain_model test subset | 19 / 19 passed |
| `run_tests.py` T0/T0.5 gate | All gates passed (after resolving two worktree environment-setup gaps, see Step 2 above) |

## Definition of Done — verified

1. Data migrated — N/A (foundation wave, no JSON data migrated yet).
2. Producers write domain repositories — N/A this wave.
3. Consumers read domain repositories — N/A this wave.
4. Old JSON references removed/rewritten — N/A this wave.
5. SKILL.md/agent/plugin instructions updated — N/A this wave.
6. Context-bundler no longer needs retired files — N/A this wave.
7. Old JSON archived or retained under exception — N/A this wave.
8. Tests prove live path, not fixtures only — schema/repository tests run against real
   `tmp_path`-backed SQLite files (real `sqlite3`, not mocked), per the project's mocking
   prohibition on critical runtime paths. Verified directly: `test_domain_model_db_client.py`,
   `test_investment_repository.py`, `test_account_repository.py`,
   `test_account_investment_repository.py`, `test_backfill_investment_universe.py` all pass
   against real SQLite connections, 19/19.
9. JSON file count before/after reported — yes, unchanged (correctly — see row above).

## Why this wave is honestly "complete" despite all-zero JSON KPIs

Wave 0 exists only to make Wave 1 possible (`projection_version.investment_id` needs a
resolvable FK target). It touches no JSON file, migrates no consumer, and archives
nothing — reporting anything other than zero here would be fabricating progress the
spec's Anti-Regression Lessons explicitly warn against ("data copied to SQLite is not
adoption"). The real KPI movement starts in Wave 1.

## Concerns for the record (not blocking, but worth flagging before Wave 1)

- This worktree required two rounds of environment bootstrap (`npm install`, `npm ci`,
  and copying the gitignored `.agents/` directory) before `run_tests.py` could even run.
  Neither gap was caused by Wave 0's code — both were confirmed pre-existing worktree
  setup gaps by cross-checking the identical, unmodified command against the main
  checkout, where it passed without intervention. Future waves' worktrees should expect
  the same bootstrap steps unless the worktree-creation process is updated to run them
  automatically.
- `test_daily_brief_ta_sweep_delegates.py` and
  `test_evolution_event_correlation_report_generates_summary.py` fail for reasons that are
  not obviously network/yfinance/CDP (a `FileNotFoundError` on a relative path, and an
  assertion mismatch on empty-week summary shape). They are still correctly classified as
  pre-existing and unrelated to Wave 0 — same failures, same files, present in Task 5's
  baseline before any of this task's investigation began — but they are not the same root
  cause as the yfinance/CDP categories this task's brief described, and are called out
  here rather than silently folded into that bucket.

## Hard Checkpoint

Per the task brief: **Wave 1 does not begin automatically after this commit.** This
report must be reviewed and explicitly signed off by the user before any Wave 1 work
(including writing Wave 1's detailed task plan) starts.
