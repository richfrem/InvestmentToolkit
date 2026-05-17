# ADR 023 — TradingView CDP Test Harness

**Date:** 2026-05-17  
**Status:** Proposed  
**Deciders:** richfrem  
**Branch:** feature/tv-data-abstraction-layer

---

## Context

The TradingView CDP automation layer (place-order, modify-order, cancel-order, get-orders, portfolio-sync) is now the primary broker integration path. All order execution flows through:

```
Skill (SKILL.md)
  → plugins/tradingview/scripts/tv_*.py  (or place_order.py for compound flows)
    → plugins/tradingview/node/core/trading.js
      → Chrome DevTools Protocol (port 9222)
        → TradingView Desktop → Questrade broker panel
```

This stack has no automated tests. Verifying correctness requires manually:
1. Launching TradingView Desktop with `--remote-debugging-port=9222`
2. Logging into Questrade in TV's broker panel
3. Running each skill/script by hand
4. Visually inspecting the TV UI for the correct outcome

This is slow, error-prone, and impossible to run in a headless environment.

Additionally, the `investment_screener` Express backend wraps these scripts via `place_order.py`. A regression in a script silently breaks the HTTP API and the frontend modal without any alert.

---

## Decision

Create a single-file Python test harness at `plugins/tradingview/tests/tv_test_harness.py` that:

1. **Imports the same Python functions the skills invoke** — not subprocess calls, not HTTP calls to the Express server. The import chain is identical to what the skills use.

2. **Covers all current TV automation functions** as independent, named test cases.

3. **Operates in two modes:**
   - `--dry-run` (default): verifies everything through form-fill + screenshot, stops before broker submission.
   - `--live`: performs a full round-trip (place limit order at safe price → modify → cancel) against the real broker.

4. **Checks prerequisites** (TV reachable, broker connected) before any test runs, with clear human-readable failures.

5. **Produces a PASS/FAIL table** with per-test timing. Exits non-zero on any failure.

---

## Alternatives Considered

### A: pytest suite with one test file per function
**Rejected.** CDP tests are inherently stateful: cancel-order needs an existing order ID to cancel. Pytest's isolation model (each test is independent) fights this. Fixtures can share state but add complexity. The harness's sequential design is simpler and matches how the skills actually operate.

### B: Shell scripts calling the CLI entry points
**Rejected.** Would test the CLI wrappers but not the underlying Python functions. Any bug between `tv_cancel_order.py::main()` and `cancel_order()` would be invisible. Output parsing in shell is fragile.

### C: Express API integration tests
**Rejected** as the primary TV test layer (though it is Tier 2 in the full test suite). Express routes call `place_order.py` via subprocess. A test that calls `POST /api/trading/cancel` proves the route works but doesn't prove `cancelOrder()` in `trading.js` works — the subprocess result is opaque. The harness tests the lowest testable layer.

### D: No tests, rely on manual verification
**Rejected.** The broker integration is high-stakes. A regression that submits a wrong order, fails to cancel, or modifies the wrong price is a real financial risk.

---

## Consequences

### Positive
- Any broken TV function is caught before it reaches the app or a live order
- The same test that validates `cancel_order()` validates the cancel skill and the Express `/api/trading/cancel` route — one truth
- New TV functions (chart analysis, alert creation, TA snapshots) slot into new test sections by convention
- Dry-run mode is safe to run at any time during development without touching the broker

### Negative
- Tests require TradingView Desktop running and broker authenticated — cannot run headless in standard CI
- Live mode tests place real limit orders (at safe prices) and must cancel them; if the harness crashes mid-test an orphan order could remain in TV
- Test output is human-readable terminal output, not a standard test report format (xUnit/TAP) until JSON mode is implemented

### Mitigations
- Live mode is opt-in (`--live` flag), dry-run is the default
- Live mode always cancels in a `finally` block to clean up orphan orders
- JSON output mode (`--json`) enables future CI integration when a self-hosted runner with TradingView is available

---

## Implementation

**File:** `plugins/tradingview/tests/tv_test_harness.py`

**Import path (same as skills):**
```python
import sys, os
PLUGIN_SCRIPTS = os.path.join(os.path.dirname(__file__), '..', 'scripts')
sys.path.insert(0, os.path.abspath(PLUGIN_SCRIPTS))

from tv_cancel_order import cancel_order
from tv_modify_order import modify_order
from tv_get_orders import get_orders
from place_order import preflight, execute_order, submit_order
```

**Place_order.py lives in `py_services/`** — the harness imports it from there directly (not via bridge.ts). This means the harness tests the same module the Express route calls.

**Test sections:**
```
Section 0: Prerequisites (TV port, broker, account, buying power)
Section 1: Preflight (market buy, limit buy, limit sell, RRSP, stale-data flag)
Section 2: Form Fill (market, limit, stop, stop-limit, verification)
Section 3: Get Orders (no filter, filtered, result structure)
Section 4: Live Round-Trip (--live only: place → verify → modify → cancel → verify gone)
Section 5: Error Paths (TV offline, bad order IDs)
```

---

## Related

- ADR 010 — Testing Approach (original, pre-broker-automation)
- ADR 021 — Direct Plugin Execution
- `docs/superpowers/specs/2026-05-17-test-suite-vision-design.md` — Full test suite vision
- `investment_screener/backend/py_services/place_order.py` — TV order wrapper
- `plugins/tradingview/node/core/trading.js` — CDP automation core
