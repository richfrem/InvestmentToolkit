# Phase 1 Implementation — InvestmentToolkit Test Suite

## Context for a New Session

You are working on **InvestmentToolkit**, a live-trading investment analysis toolkit on branch `feature/tv-data-abstraction-layer`. The project has:
- Node.js/Express backend (`investment_screener/backend/`)
- React 19 frontend (`investment_screener/frontend/`)
- Python bridge scripts in `py_services/` (spawned via `bridge.ts`)
- TradingView CDP automation (`plugins/tradingview/`)
- Zero automated tests currently

A full test suite vision has been designed, red-team reviewed twice (GPT-5.5 + Claude Opus), and is **ready for implementation**.

**Before writing any code, invoke:** `superpowers:test-driven-development`

The Iron Law: `NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST.`

---

## Key Files to Read First

| File | Why |
|------|-----|
| `docs/superpowers/specs/2026-05-17-test-suite-vision-design.md` | Full test suite spec — your implementation guide |
| `.agent/rules/test-driven-development.md` | TDD rule — read and follow exactly |
| `investment_screener/backend/py_services/portfolio_action.py` | Task 1: broken import |
| `investment_screener/backend/src/utils/helpers.ts` | Task 1: where `getPythonActions()` calls the broken script |
| `investment_screener/backend/src/services/bridge.ts` | Task 1: `spawnPythonScript()` path resolution |

---

## Phase 1 — 5 Tasks (~8 hours), In This Order

### Task 1: Fix `portfolio_action.py` import path (30 min)

**The bug:** `helpers.ts` calls `spawnPythonScript('portfolio_action.py')`. That resolves to `py_services/portfolio_action.py`, which is a **symlink** to `plugins/portfolio-advisor/scripts/portfolio_action.py`. The `__main__` block does:

```python
sys.path.insert(0, str(Path(__file__).parent))
from validate_weights import compute_current, compute_target
```

`Path(__file__).parent` on a symlink gives `py_services/` — but `validate_weights.py` lives in `plugins/portfolio-advisor/scripts/`. `getPythonActions()` catches the ImportError and silently returns `{}`, breaking all action labels in the screener.

**The fix:** Change to `Path(__file__).resolve().parent`. The `.resolve()` follows the symlink to the canonical location where `validate_weights.py` actually lives.

**The test (write first, watch it fail, THEN fix):**

```python
# tests/py_services/test_portfolio_action_import.py
import subprocess, json

FIXTURES_DIR = "investment_screener/backend/tests/fixtures"

def test_portfolio_action_via_symlink_path():
    """py_services/ symlink path must work — this is how bridge.ts calls it."""
    r = subprocess.run(
        ["python3", "investment_screener/backend/py_services/portfolio_action.py",
         "--all", "--portfolio", f"{FIXTURES_DIR}/portfolio.test.json",
         "--target", f"{FIXTURES_DIR}/target_portfolio.test.json"],
        capture_output=True, text=True
    )
    assert r.returncode == 0, f"FAILED: {r.stderr}"
    data = json.loads(r.stdout)
    assert len(data) > 0, "Expected non-empty action map"

def test_portfolio_action_via_canonical_path():
    """Canonical path must also work."""
    r = subprocess.run(
        ["python3", "plugins/portfolio-advisor/scripts/portfolio_action.py",
         "--all", "--portfolio", f"{FIXTURES_DIR}/portfolio.test.json",
         "--target", f"{FIXTURES_DIR}/target_portfolio.test.json"],
        capture_output=True, text=True
    )
    assert r.returncode == 0, f"FAILED: {r.stderr}"
    data = json.loads(r.stdout)
    assert len(data) > 0
```

You need small fixture files. Create minimal ones:
- `investment_screener/backend/tests/fixtures/portfolio.test.json` — 2–3 holdings with weights
- `investment_screener/backend/tests/fixtures/target_portfolio.test.json` — matching targets

Both tests must FAIL before the fix, PASS after. Both paths must work.

---

### Task 2: T0 Compile/Syntax Gate + T0.5 Bridge Smoke (1 hr)

Create `tests/run_tests.py` with a T0 section that runs:

```bash
# TypeScript compile
npm run build -w backend        # from investment_screener/
npm run build -w frontend

# Python syntax
python3 -m py_compile investment_screener/backend/py_services/place_order.py
python3 -m py_compile investment_screener/backend/py_services/portfolio_action.py
python3 -m py_compile plugins/tradingview/scripts/tv_cancel_order.py
python3 -m py_compile plugins/tradingview/scripts/tv_modify_order.py
python3 -m py_compile plugins/tradingview/scripts/tv_get_orders.py

# Node syntax
node --check plugins/tradingview/node/core/trading.js
node --check plugins/tradingview/node/core/broker_data.js
```

**T0.5** (add after syntax): Run the test from Task 1 as a gate. If `portfolio_action.py` subprocess returns empty or non-zero, abort before all other tiers.

All T0/T0.5 failures are CRITICAL — no other tier runs if any T0 check fails.

---

### Task 3: `validate_all_projections.py` (2 hrs)

Create `tests/validate_all_projections.py`. Run from repo root with no server needed.

**IMPORTANT — create `derive_valuation_signal()` inline in this file (it doesn't exist anywhere):**
```python
def derive_valuation_signal(upside_pct: float) -> str:
    """Pure DCF valuation signal using analysis_prompt.md thresholds (NOT apply_catalyst.py bands)."""
    if upside_pct >= 15: return "BUY"
    if upside_pct >= -15: return "HOLD"
    return "SELL"
```

**Three validations per projection file (all FAIL hard, not warn):**

1. **Scenario weights sum to 1.0** — `abs(sum(weights) - 1.0) > 0.001` → FAIL
2. **Stored action vs computed signal** — `derive_valuation_signal(upside)` must match `aiThesis.action` for BUY/HOLD/SELL entries (skip ACCUMULATE/TRIM/etc — those are portfolio-action vocab, not DCF signals)
3. **Stored fairValue vs recomputed weighted FV** — `abs(stored_fv - computed_fv) > 0.50` → FAIL

Write the test first. Feed it a projection you know is broken (e.g., INTC if present — HOLD with -38% upside). Watch it fail. Then run against all projections in `investment_screener/backend/data/projections/`.

---

### Task 4: `test_place_order_gates.py` (2 hrs)

Create `investment_screener/backend/tests/py_services/test_place_order_gates.py`.

**No TV required.** Tests via subprocess. Write each test first, watch it fail (or confirm it passes if the gate already works), then document:

```python
# Required tests:
def test_preflight_missing_ticker()       # non-zero exit
def test_execute_missing_account()        # non-zero exit
def test_cancel_missing_order_id()        # non-zero exit
def test_modify_missing_new_price()       # non-zero exit
def test_limit_order_missing_limit_price()# non-zero exit
def test_stale_portfolio_exits_4()        # create old temp portfolio.json, exit code 4
def test_stale_with_ack_stale_proceeds()  # exit 0, card has _freshnessWarning
def test_fresh_portfolio_exits_0()        # exit 0, no warning
def test_size_cap_exits_3()               # order cost > max-order-value, exit 3
```

**Critical assertion for stale test:** exit 4 must happen BEFORE any CDP call. The test doesn't need TradingView running. If the test requires TV to be running, the implementation is wrong.

---

### Task 5: TV Prereqs + DOM Selector Smoke Check (2 hrs)

Create `plugins/tradingview/tests/tv_test_harness.py` — just Sections 0 and 0.5.

**Section 0 — Prerequisites:**
```
[0.1] TV reachable (port 9222) — CDP connect
[0.2] Broker connected (Questrade visible)
[0.3] Account readable (TFSA or RRSP visible)
[0.4] Buying power > 0
```

**Section 0.5 — DOM Selector Smoke Check (CRITICAL — abort suite on any failure):**
```
[0.5.1] [class*="buyButton"] — Buy overlay button
[0.5.2] [class*="sellButton"] — Sell overlay button
[0.5.3] [class*="dropdownButton"] — Account dropdown
[0.5.4] [class*="brokerBlock"] — Broker panel
```
If any selector is missing, abort with a diagnostic message listing which ones failed. TV ships DOM updates 2–4 times/year — a missing selector here means all subsequent tests would fail with cryptic form-fill errors.

CLI:
```bash
python3 plugins/tradingview/tests/tv_test_harness.py --suite prereqs
```

---

## Phase 1 Gate

**Do NOT start Phase 2 until all Phase 1 tasks pass.**  
**Do NOT implement the live round-trip (Section 4) until Phase 2.**

Phase 2 begins with extracting `_run_node()` to a shared `tv_node_runner.py` — see the spec for full Phase 2 plan.

---

## Important Constraints

1. **Subprocess-first always.** The primary test harness must shell out via subprocess, not import Python functions directly. See `.agent/rules/test-driven-development.md` — "Critical Runtime Paths Must Not Be Mocked."

2. **Fixture files, not real personal data.** Never read `investment_screener/backend/data/portfolio.json` or `trade-log.json` in tests. Always use test fixtures in `tests/fixtures/`.

3. **`portfolio_action.py` symlink fix:** The file is a symlink. `Path(__file__).parent` gives the wrong directory. Must be `Path(__file__).resolve().parent`. Test both invocation paths.

4. **`derive_valuation_signal()` doesn't exist anywhere.** Create it inline in the test file using ±15% thresholds from `analysis_prompt.md`. Do NOT use `apply_catalyst.py` action bands — those are different classification systems.

5. **Test categories (from TDD rule):**
   - Tasks 1–4: Category B (runtime integration) — subprocess-first, no subprocess mocking
   - Task 5: Category A + Category C prerequisite check (read-only CDP, no orders)

6. **gitignored data files are sacred.** Never overwrite `portfolio.json`, `trade-log.json`, or any gitignored file without explicit user approval.

---

## Where Tests Live

| Test file | Location |
|-----------|---------|
| `test_portfolio_action_import.py` | `investment_screener/backend/tests/py_services/` |
| `run_tests.py` (T0/T0.5) | `tests/` (repo root) |
| `validate_all_projections.py` | `tests/` (repo root) |
| `test_place_order_gates.py` | `investment_screener/backend/tests/py_services/` |
| `tv_test_harness.py` | `plugins/tradingview/tests/` |
| Test fixtures | `investment_screener/backend/tests/fixtures/` |

---

## Full spec + TDD rule:
- `docs/superpowers/specs/2026-05-17-test-suite-vision-design.md`
- `.agent/rules/test-driven-development.md`
