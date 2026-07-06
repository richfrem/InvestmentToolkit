# Map Debt Registry

This registry tracks technical debt, process friction, and workarounds.
Entries must be resolved, aged, or escalated. 
Do not delete resolved items; set `Status: RESOLVED` to maintain history.

---

### Entry: test_math_parity.py — PROJECT_ROOT resolves 2 levels short of repo root

- Logged: 2026-07-05
- Cycle/Session: Phase 3 E1 (risk-engine) — discovered during baseline test run before Task 1 dispatch
- Artifact affected: `investment_screener/backend/tests/py_services/test_math_parity.py:6`
- Friction observed: `PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))` only walks up 2 directories from `tests/py_services/test_math_parity.py`, landing at `tests/` instead of the repo root. The subsequent `subprocess.run([...os.path.join(PROJECT_ROOT, "investment_screener/backend/py_services/dcf_scenarios.py")...])` call then looks for the script at a doubled, nonexistent path and fails with `No such file or directory`.
- Why it was not fixed now: unrelated to the Phase 3 risk-engine task in progress; fixing it would be an undeclared scope addition mid-task (violates "one logical fix at a time").
- Recommended fix: use `Path(__file__).resolve().parents[4]` (matching the convention already used consistently elsewhere in this test directory, e.g. `test_framework_score.py`, `test_risk_engine.py`) instead of two `os.path.dirname()` calls.
- Evidence: `python3 -m pytest tests/py_services/test_math_parity.py -v` → `Exception: Python math failed`; captured stdout shows `can't open file '.../tests/investment_screener/backend/py_services/dcf_scenarios.py'`.
- Severity: S
- Repeat: NO (isolated to this one file)
- Status: OPEN

### Entry: test_place_order_gates.py — 3 tests coupled to real-world weekday/market-hours state

- Logged: 2026-07-05
- Cycle/Session: Phase 3 E1 (risk-engine) — discovered during baseline test run before Task 1 dispatch
- Artifact affected: `investment_screener/backend/tests/py_services/test_place_order_gates.py` — `test_stale_portfolio_exits_4`, `test_fresh_portfolio_exits_0`, `test_size_cap_exits_3`
- Friction observed: these tests invoke the real `place_order.py --preflight` CLI, which checks live NYSE market-hours state before evaluating the gate under test (stale-data, fresh-portfolio, size-cap). When run on a weekend (as today, 2026-07-05 is a Sunday), the market-closed gate fires first and returns exit code 5 with "🚫 Weekend — NYSE is closed" instead of the expected gate-specific exit code (4, 0, 3 respectively) — the tests are not isolated from wall-clock/calendar state.
- Why it was not fixed now: unrelated to the Phase 3 risk-engine task in progress; the real fix (mocking/injecting market-hours state so these gate-order tests are calendar-independent) is a test-harness change outside this task's scope.
- Recommended fix: add a way to override/mock the market-hours check in `place_order.py`'s preflight path (e.g. an env var or `--skip-market-hours-check` test-only flag) so these three tests assert the gate they name regardless of what day they run.
- Evidence: `python3 -m pytest tests/py_services/test_place_order_gates.py -v` on 2026-07-05 (Sunday) → all 3 fail with returncode 5 / "Weekend — NYSE is closed" instead of their expected returncodes.
- Severity: S
- Repeat: YES — will recur every Saturday/Sunday (and likely market holidays) until fixed
- Status: OPEN
