# InvestmentToolkit — Full Test Suite Vision
**Date:** 2026-05-17 (revised after Round 2 red-team review)  
**Branch:** feature/tv-data-abstraction-layer  
**Reviewers:** GPT-5.5, Claude Opus (Rounds 1 + 2)  
**Status:** Revised — ready for implementation

---

## Revision Notes (Round 2 additions)

Key additions from Round 2 feedback:

1. **T0.5 bridge smoke test** — `portfolio_action.py` subprocess via `py_services/` path must return non-empty JSON. Build-level concern added to T0 gate.
2. **Phase 1 Task 1 tightened** — `portfolio_action.py` fix must use `Path(__file__).resolve().parent` (symlink issue). Test BOTH invocation paths.
3. **`derive_valuation_signal()` must be created** — function doesn't exist yet; inline in `validate_all_projections.py` using `analysis_prompt.md` ±15% thresholds.
4. **`extractJson()` greedy regex bug** — `/\{[\s\S]+\}/` spans first `{` to last `}`. Test case added: two JSON objects → extracts last valid block.
5. **`_check_data_freshness()` dual-call** — explicit test assertions added for all three stale/ack combinations.
6. **`trading.ts` execute route** — exit code 4 must transition session to `DATA_STALE_BLOCKED`, not generic 422.
7. **`runPy()` timeout** — resolves with `exitCode: -1`, falls through to generic error. Handle `-1` as `TIMEOUT` specifically.
8. **Phase 2 reorder** — stdout fixtures captured during dry-run (task 9), not as a separate task after.
9. **Cancel/modify parity test** — both paths (place_order.py vs standalone script) must produce identical results.
10. **Weighted FV validation** — `validate_all_projections.py` must check stored `fairValue` vs recomputed weighted FV.
11. **Scenario weights sum validation** — must be exactly 1.0, FAIL hard (not warn).
12. **`bridge.ts` stale-cache tests** — `spawnPythonScript()` fallback to stale cache must set `stale=true` and populate `staleReason`.
13. **Mutation safety rule** — changes to order execution, valuation, or state machines require regression test + no reduction in critical-path coverage.
14. **TDD rule strengthened** — "Valid Failing Test" definition, no-mock list for runtime paths, three test categories, mutation safety rule added to `.agent/rules/test-driven-development.md`.
15. **Future ADR: `place_order.py` decomposition** tracked as tech debt.

---

## Revision Notes (Round 1 → Round 2)

Key changes from red-team feedback:

1. **T0 Build/Syntax Gate added** as new first tier
2. **Subprocess-first harness** — primary test path shells out, not direct import (Opus recommendation, adopted over original design)
3. **DOM selector smoke check** added as Section 0.5
4. **`_run_node()` extraction** added as prerequisite
5. **Live-test safety ledger + `--cleanup-orphans`** added to live mode
6. **`--i-understand-live-broker-test` flag** required alongside `--live`
7. **Valuation consistency tests** promoted from out-of-scope to T3
8. **Skill contract tests** added to T4 (not AI quality — structural safety section presence)
9. **`extractJson()` unit tests** added to T2
10. **Trade session illegal-transition tests** added to T2
11. **Audit date format bug** identified — `YYYYMMDD` vs `YYYY-MM-DD` in `trading.ts`
12. **`INVESTMENT_TOOLKIT_DATA_ROOT` env var** required before API fixture tests
13. **Severity tags** added to every test section
14. **Phase 1 scope narrowed** to 5 targeted items (was too broad)
15. **TDD rule** added at `.agent/rules/test-driven-development.md`, surfaced in all three AI context files

---

## 1. Problem Statement

The InvestmentToolkit has grown to:
- 7 Express route files / 50+ HTTP endpoints
- 20+ Python services
- 9 TypeScript services
- 5 plugins / 35+ skills
- TradingView CDP automation (place, modify, cancel, get-orders, portfolio sync)
- A live broker integration (Questrade via TradingView)

**There are currently zero automated tests.** Every change is manually verified. This is untenable — a regression can trigger unintended live orders with real financial consequences.

The core principle:

> **The primary test path must shell out via subprocess, matching the actual execution path of skills and the Express backend. Direct function imports are secondary, only for isolated pure-function tests.**

This principle was validated by the `portfolio_action.py` bug: an import path failure that only manifested through subprocess. Direct import would have hidden it entirely.

**Companion rule:** `.agent/rules/test-driven-development.md` — all implementation must be test-first. The Iron Law:
```
NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST.
```

---

## 2. Scope

Six tiers, ordered by when to implement:

| Tier | Name | What | Requires |
|------|------|------|----------|
| T0 | Build/Syntax Gate | Compile + syntax check all entry points | Python venv, Node |
| T1 | TV CDP Harness | TradingView Desktop automation | TV running + broker connected |
| T2 | Backend API Suite | Express HTTP endpoints | Backend server + test data root |
| T3 | Python Service Suite | py_services scripts + plugin scripts | Python venv |
| T4 | Plugin/Skill Contracts | Structural safety checks on SKILL.md files | Python venv |
| T5 | Frontend Smoke Tests | Page-level UI smoke (Playwright) | Full stack running |

**Phase 1 (current):** T0 + T3 partial (projection consistency + place_order gates) + T1 prereqs  
**Phase 2:** T1 full dry-run + live harness foundation  
**Phase 3:** T2 (requires `INVESTMENT_TOOLKIT_DATA_ROOT`) + T4  
**Phase 4:** T5

---

## 3. Tier 0 — Build/Syntax Gate

Run before any other tier. If T0 fails, stop everything.

```bash
# TypeScript compile
npm run build -w backend
npm run build -w frontend

# Python syntax
python3 -m py_compile investment_screener/backend/py_services/place_order.py
python3 -m py_compile plugins/tradingview/scripts/tv_cancel_order.py
python3 -m py_compile plugins/tradingview/scripts/tv_modify_order.py
python3 -m py_compile plugins/tradingview/scripts/tv_get_orders.py
python3 -m py_compile investment_screener/backend/py_services/portfolio_action.py

# Node syntax
node --check plugins/tradingview/node/core/trading.js
node --check plugins/tradingview/node/core/broker_data.js
```

**Severity: CRITICAL for all.** T0 failure blocks all other tiers.

### T0.5 — Bridge Smoke Test [CRITICAL]

```python
# Must pass BEFORE any other tier runs.
# If this fails, screener shows empty action badges for every row.
result = subprocess.run(
    ["python3", "investment_screener/backend/py_services/portfolio_action.py",
     "--all",
     "--portfolio", "investment_screener/backend/tests/fixtures/portfolio.test.json",
     "--target", "investment_screener/backend/tests/fixtures/target_portfolio.test.json"],
    capture_output=True, text=True
)
assert result.returncode == 0, f"portfolio_action.py failed: {result.stderr}"
data = json.loads(result.stdout)
assert len(data) > 0, "Expected non-empty action map — bridge path is broken"
```

This validates that `bridge.ts`'s `spawnPythonScript('portfolio_action.py')` will work at runtime. The TypeScript refactor that caused the original bug wouldn't have triggered the TDD rule globs (it was a `.ts` change with no `.py` change) — this smoke test catches that class of failure.

**Also test canonical path:**
```bash
python3 plugins/portfolio-advisor/scripts/portfolio_action.py --all \
  --portfolio investment_screener/backend/tests/fixtures/portfolio.test.json \
  --target investment_screener/backend/tests/fixtures/target_portfolio.test.json
```
Both must return non-empty JSON. If either fails, the Phase 1 Task 1 symlink fix is incomplete.

---

## 4. Tier 1 — TradingView CDP Test Harness

### 4.1 Prerequisites

**Before building the harness, complete these:**

1. **Extract `_run_node()` to shared module** — currently duplicated in `place_order.py`, `tv_cancel_order.py`, `tv_modify_order.py`, `tv_get_orders.py` with different timeouts and error handling. Fix once:
   ```
   plugins/tradingview/scripts/tv_node_runner.py
   def run_node(js: str, timeout: int = 30, cwd: str = TV_NODE_DIR) -> dict
   ```
   All four scripts import from one place. Fixes silently divergent error handling.

2. **Verify $0.01 Questrade acceptance** — manually place a $0.01 limit buy in TradingView and check if Questrade accepts it. If rejected (minimum order value rule), use:
   ```python
   safe_price = max(0.01, round(current_price * 0.01, 2))  # 1% of market price
   ```

### 4.2 Design Principles

1. **Subprocess-first.** Primary harness shells out to scripts exactly as skills do:
   ```python
   result = subprocess.run(
       ["python3", TV_CANCEL_SCRIPT, "--order-id", oid, "--json"],
       capture_output=True, text=True, timeout=15
   )
   assert json.loads(result.stdout)["cancelled"] is True
   ```
   Direct imports (`from tv_cancel_order import cancel_order`) are secondary — only used for isolated pure-function tests where subprocess overhead is prohibitive.

2. **Dry-run by default, `--live` opt-in.** Live mode additionally requires `--i-understand-live-broker-test`.

3. **DOM selector smoke check first.** Section 0.5 verifies key CSS selectors exist before any functional test. TV ships DOM updates 2–4 times/year. Missing selector → abort with diagnostic, not mysterious form-fill failure.

4. **Severity gates.** If any CRITICAL test fails, suite aborts. Never run live broker tests on a broken foundation.

5. **Live-test safety ledger.** Every live test writes a JSON ledger before placing anything. `--cleanup-orphans` scans the ledger and attempts cancellation for any incomplete live test orders.

### 4.3 File Layout

```
plugins/tradingview/
  scripts/
    tv_node_runner.py        ← NEW: shared _run_node() (prerequisite)
  tests/
    tv_test_harness.py       ← main orchestrator
    live_test_ledger.py      ← orphan order tracking
    README.md
```

### 4.4 Live-Test Order Safety Spec

When `--live --i-understand-live-broker-test` is passed, live test orders MUST be:
- Limit order only (never market, never stop, never stop-limit)
- Buy only (unless explicitly testing sell logic)
- 1 share only
- Limit price ≤ min($1.00, 1% of current market price)
- Only in the account specified by `--account` (default: TFSA test account)

### 4.5 Live-Test Safety Ledger

Before any live order is placed, write:
```json
{
  "testRunId": "2026-05-17T14-30-00Z-a1b2c3",
  "ticker": "AAPL",
  "account": "TFSA",
  "intendedOrder": "BUY 1 LIMIT 0.01",
  "state": "PLACE_ATTEMPTED",
  "tvOrderId": null,
  "createdAt": "2026-05-17T14:30:00Z"
}
```
States: `PLACE_ATTEMPTED` → `ORDER_ID_CAPTURED` → `MODIFY_ATTEMPTED` → `CANCEL_ATTEMPTED` → `CANCEL_VERIFIED` | `ORPHAN_CHECK_REQUIRED`

```bash
python3 plugins/tradingview/tests/tv_test_harness.py --cleanup-orphans
```

### 4.6 Test Cases

```
SECTION 0: Prerequisites  [CRITICAL]
  [0.1] TV reachable (port 9222)
  [0.2] Broker connected (Questrade)
  [0.3] Account readable (TFSA or RRSP visible)
  [0.4] Buying power readable (> 0)

SECTION 0.5: DOM Selector Smoke Check  [CRITICAL — abort suite on any failure]
  [0.5.1] [class*="buyButton"] — Buy overlay button
  [0.5.2] [class*="sellButton"] — Sell overlay button
  [0.5.3] [class*="dropdownButton"] — Account dropdown
  [0.5.4] [class*="brokerBlock"] — Broker panel
  → ABORT with list of missing selectors if any fail (TV may have updated DOM)

SECTION 1: Preflight (subprocess, no dialog opened)  [HIGH]
  [1.1] Market buy preflight — AAPL, 1 share, TFSA → exit 0, card has ticker
  [1.2] Limit buy preflight — AAPL, 1 share, $1.00, TFSA → exit 0, priceDisplay shows limit
  [1.3] Limit sell preflight — AAPL, 1 share, $999.00, TFSA → exit 0
  [1.4] RRSP account preflight → accountType RRSP in card
  [1.5] Missing --ticker → exit non-zero
  [1.6] Limit order missing --limit-price → exit non-zero
  [1.7] Stale portfolio.json (>60 min) → exit 4, DATA_STALE_BLOCKED
  [1.8] Stale + --ack-stale → exit 0

SECTION 2: Form Fill (subprocess, dry-run, fills dialog, takes screenshot, does NOT submit)  [CRITICAL]
  [2.1] Market order form fill → screenshot captured, dialog state open
  [2.2] Limit order form fill → price field populated
  [2.3] Stop order form fill
  [2.4] Stop-limit order form fill (both price fields)
  [2.5] Form verification mismatch → form rejected before screenshot

SECTION 3: Get Orders (subprocess, read-only)  [MEDIUM]
  [3.1] Get orders no filter → JSON with orders array
  [3.2] Get orders --ticker AAPL → filters to AAPL rows
  [3.3] orderId fields are UUID format (or null if no orders)
  [3.4] --json flag outputs parseable JSON

SECTION 4: Live Round-Trip (--live --i-understand-live-broker-test required)  [CRITICAL]
  [4.1] Ledger written before place → state: PLACE_ATTEMPTED
  [4.2] Place limit buy at safe_price → orderId captured, ledger: ORDER_ID_CAPTURED
  [4.3] Verify order in get-orders → matches returned orderId
  [4.4] Modify to safe_price + 0.01 → brokerVerification.priceMatch
  [4.5] Cancel → cancelled: true, verified: true
  [4.6] Verify gone from get-orders
  [4.7] Ledger final state: CANCEL_VERIFIED
  [4.8] finally block cancels even on test crash

SECTION 5: Error Paths  [HIGH]
  [5.1] TV not running → RuntimeError, clear message
  [5.2] Cancel non-existent UUID → cancelled: false
  [5.3] Modify non-existent UUID → modified: false
  [5.4] --cleanup-orphans with no ledger → exits cleanly
  [5.5] Cancel via place_order.py --cancel produces same result as tv_cancel_order.py
        for same orderId (parity test — run after _run_node() extraction in Phase 2)
```

### 4.7 CLI Interface

```bash
# Prerequisites + DOM check only (safe, read-only)
python3 plugins/tradingview/tests/tv_test_harness.py --suite prereqs

# Full dry-run (default — forms filled, screenshots taken, nothing submitted)
python3 plugins/tradingview/tests/tv_test_harness.py

# Specific suite
python3 plugins/tradingview/tests/tv_test_harness.py --suite preflight
python3 plugins/tradingview/tests/tv_test_harness.py --suite orders

# Live round-trip (places + cancels a real order — BOTH flags required)
python3 plugins/tradingview/tests/tv_test_harness.py \
    --live --i-understand-live-broker-test \
    --ticker AAPL --account tfsa

# Orphan cleanup (reads ledger, cancels incomplete live-test orders)
python3 plugins/tradingview/tests/tv_test_harness.py --cleanup-orphans

# JSON output (for CI/scripting)
python3 plugins/tradingview/tests/tv_test_harness.py --json
```

### 4.8 Future TV Test Sections

| Future capability | Section |
|---|---|
| DOM Parser unit tests (jsdom, no TV needed) | Section 6 |
| `analyze-chart` / OHLCV read | Section 7 |
| `create-alerts` | Section 8 |
| `ta-snapshot` | Section 9 |
| Multi-account routing | Section 4 extension |

**Technical debt note:** `trading.js` contains ~600 lines with DOM parsing logic embedded in stringified JS passed to CDP. Long-term, extract to `core/dom-parsers.js` for jsdom unit testing. Not Phase 1, but mark as a known testing gap.

---

## 5. Tier 2 — Backend API Test Suite

### 5.1 Prerequisites

**`INVESTMENT_TOOLKIT_DATA_ROOT` env var must exist before any API fixture work.** Without it, tests will read/write personal `portfolio.json` and `trade-log.json`.

Add to `investment_screener/backend/src/utils/paths.ts`:
```typescript
export const DATA_ROOT =
  process.env.INVESTMENT_TOOLKIT_DATA_ROOT
    ? path.resolve(process.env.INVESTMENT_TOOLKIT_DATA_ROOT)
    : path.join(__dirname, '../../data');
```

Then all file paths use `DATA_ROOT` as base. Tests run with:
```bash
INVESTMENT_TOOLKIT_DATA_ROOT=/tmp/itk-test-data npm run start -w backend
```

**Also fix audit date format before writing tests.** `trading.ts` generates:
```typescript
const today = new Date().toISOString().slice(0, 10).replace(/-/g, '');
// → orders-20260517.jsonl  ← WRONG
```
But audit files are written as `orders-YYYY-MM-DD.jsonl`. Remove the `.replace(/-/g, '')`.

### 5.2 File Layout

```
investment_screener/backend/tests/
  api/
    test_portfolio_routes.py
    test_trading_routes.py       ← state machine transitions
    test_trading_extract_json.py ← extractJson() unit tests
    test_stock_routes.py
    test_projections_routes.py
    test_theses_routes.py
    test_screener_routes.py
    test_docs_routes.py
  fixtures/
    portfolio.test.json
    trade_log.test.json
    target_portfolio.test.json
  conftest.py
  run_api_tests.py
```

### 5.3 `extractJson()` Unit Tests (high priority)

`extractJson()` in `trading.ts` is the translation layer between Python subprocess output and Express route responses. Three-strategy parser — if it fails, the frontend gets garbage silently.

Test with captured real stdout from each `place_order.py` mode:
```
Input: clean JSON only → parses correctly
Input: ASCII card + \n + JSON → extracts JSON after card
Input: warning lines + JSON + trailing newline → extracts JSON
Input: empty stdout → returns null
Input: Python traceback, no JSON → returns null
Input: multiple JSON blocks → extracts LAST valid block (greedy regex bug)
Input: valid JSON with trailing text → parses first valid block
```
Capture real stdout to `tests/fixtures/stdout_samples/` and use as test fixtures.

**Known bug:** The brute-force fallback regex `/\{[\s\S]+\}/` is greedy — it matches from the first `{` to the last `}`. If stdout contains two JSON objects separated by plain text (e.g., a stale warning + final result object), `JSON.parse()` will fail on the merged span and `extractJson()` returns null. The "multiple JSON blocks" test case above must catch this. Consider a reverse-scan implementation:
```typescript
let depth = 0, end = -1, start = -1;
for (let i = trimmed.length - 1; i >= 0; i--) {
    if (trimmed[i] === '}') { if (end === -1) end = i; depth++; }
    if (trimmed[i] === '{') { depth--; if (depth === 0) { start = i; break; } }
}
```

### 5.4 Trade Session State Machine Tests [HIGH]

```
POST /api/trading/submit without session → 404
POST /api/trading/execute from DRAFT → 409
POST /api/trading/execute from DATA_STALE_BLOCKED → 409
POST /api/trading/submit from PREFLIGHT_PASSED (not FORM_FILLED) → 409
POST /api/trading/submit from FORM_FILLED → allowed
POST /api/trading/preflight with stale portfolio → 422 DATA_STALE_BLOCKED
POST /api/trading/execute after preflight with portfolio that went stale → 422, state=DATA_STALE_BLOCKED (not generic "Execute failed")
POST /api/trading/cancel with entryId only, no tvOrderId → logCancelled true, tvCancelled false
GET /api/trading/audit/today → reads orders-YYYY-MM-DD.jsonl (not YYYYMMDD)
POST /api/trading/preflight missing ticker → 400
POST /api/trading/cancel with tvOrderId (TV offline) → tvCancelled false, log still updated
POST /api/trading/preflight with hanging script → timeout → specific timeout error (not generic "Preflight failed")
```

**Bug fix required (Phase 3):** `trading.ts` `runPy()` timeout handler calls `resolve({ exitCode: -1 })`. Exit code `-1` is not in the known code set (0, 3, 4) so the route falls through to a generic 422. Handle `-1` as `TIMEOUT_BLOCKED` explicitly.

**Bug fix required (Phase 3):** `trading.ts` execute route does not catch exit code 4 specifically. A stale-data block during execute should transition session to `DATA_STALE_BLOCKED`:
```typescript
if (exitCode === 4) {
    patchSession(sessionId, { state: 'DATA_STALE_BLOCKED' });
    res.status(422).json({ error: 'Portfolio data went stale since preflight', state: 'DATA_STALE_BLOCKED' });
    return;
}
```

**`bridge.ts` stale-cache test:** `spawnPythonScript()` falls back to stale cached data on subprocess failure. Test:
```
First call: subprocess succeeds → result cached
Second call: subprocess fails/hangs → stale cached result returned
Response has stale=true AND staleReason populated
```

**Session persistence gap:** Trade sessions are in-memory (`Map<string, TradeSession>`). Backend restart between preflight and execute = 404. Backend restart after form-fill = session lost, TV dialog orphaned. Document and add test:
```
Backend restart between preflight and execute → 404 (expected — document recovery path)
Two concurrent sessions for same ticker → unique IDs, no collision
```

### 5.5 Key Test Cases (other routes)

**Portfolio routes:**
- GET /api/portfolio → 200, array
- GET /api/portfolio/summary → totalValue, unrealizedGain present
- GET /api/portfolio/weights → percentages sum to ~100
- GET /api/portfolio/holdings/UNKNOWN → 404
- POST /api/portfolio/sync (TV offline) → returns cache, not 500

**Stock routes:**
- GET /api/stock/stock/AAPL → 200, has ticker, price
- GET /api/stock/market/quotes?tickers=AAPL,MSFT → 200, two entries
- GET /api/stock/market/quotes?tickers= (empty) → 400 or empty array

**Projections:**
- GET /api/projections/NVDA → 200, non-empty array
- GET /api/projections/FAKEXYZ → 200, empty array (not 404)

**Screener:**
- GET /api/screener/all-holdings → has `action` field per ticker (not empty object — portfolio_action fix must be in)

---

## 6. Tier 3 — Python Service Tests

### 6.1 `validate_all_projections.py` — highest value, no infrastructure [MEDIUM]

Scan all 70+ projection JSONs for valuation/action consistency. Catches the INTC HOLD-vs-$67-FV bug class. Runs without TV, without backend, without any setup.

**IMPORTANT — `derive_valuation_signal()` must be created as part of this task.** It does not exist anywhere in the codebase. Use the `analysis_prompt.md` thresholds (NOT `apply_catalyst.py` bands — these are two different classification systems applied to the same `aiThesis.action` field):

```python
def derive_valuation_signal(upside_pct: float) -> str:
    """Pure DCF valuation signal — NOT portfolio action (ACCUMULATE/TRIM/etc)."""
    if upside_pct >= 15: return "BUY"
    if upside_pct >= -15: return "HOLD"
    return "SELL"
```

Place inline in `tests/validate_all_projections.py`. It is a test utility, not production code.

```python
def test_projection_consistency(proj_file):
    proj = json.load(open(proj_file))
    scenarios = proj.get("scenarios", {})
    if not all(s in scenarios for s in ("bear", "base", "bull")):
        return "SKIP"  # incomplete projection

    weights = [scenarios[s]["weight"] for s in ("bear", "base", "bull")]

    # Validation 1: scenario weights must sum to exactly 1.0 [FAIL hard]
    weight_sum = sum(weights)
    if abs(weight_sum - 1.0) > 0.001:
        return f"FAIL weights sum to {weight_sum:.4f} (must be 1.000)"

    weighted_fv = sum(
        scenarios[s]["weight"] * scenarios[s]["scenarioPrice"]
        for s in ("bear", "base", "bull")
    )
    price = proj["snapshot"]["price"]
    upside = (weighted_fv - price) / price * 100

    # Validation 2: stored action vs computed signal
    expected = derive_valuation_signal(upside)
    stored = proj.get("aiThesis", {}).get("action")
    if expected != stored:
        return f"FAIL stored={stored} computed={expected} upside={upside:+.1f}%"

    # Validation 3: stored fairValue vs recomputed weighted FV [FAIL hard]
    stored_fv = proj.get("aiThesis", {}).get("fairValue")
    if stored_fv is not None and abs(stored_fv - weighted_fv) > 0.50:
        return f"FAIL stored fairValue={stored_fv:.2f} vs recomputed={weighted_fv:.2f}"

    return "PASS"
```

Output example:
```
INTC: FAIL — stored HOLD, computed SELL (FV $67 vs $109, -38.5%)
NVDA: PASS — stored BUY (FV $445 vs $198, +124.3%)
...
37/38 PASS, 1 FAIL
```

**Location:** `tests/validate_all_projections.py` (runs from repo root, no server needed)

### 6.2 `test_place_order_gates.py` — CLI gate tests via subprocess [HIGH]

No TV required. Tests the full subprocess execution path:

```
--preflight missing --ticker → non-zero exit
--execute missing --account → non-zero exit
--cancel missing --order-id → non-zero exit
--modify missing --new-price → non-zero exit
--limit order missing --limit-price → non-zero exit
portfolio.json missing → exit 4 DATA_STALE_BLOCKED (before CDP call)
portfolio.json older than 60 min → exit 4 (mocked mtime)
--ack-stale with stale portfolio → preflight proceeds past gate
order cost > max-order-value → exit 3 SIZE_CAP_BLOCKED
```

**Key:** the stale-data gate fires before CDP is called in `place_order.py`. Test is valid offline. Assert the three freshness scenarios explicitly:
```
stale + no --ack-stale → exit 4 BEFORE CDP is called (TV not required — this is the key assertion)
stale + --ack-stale → exit 0, card JSON contains "_freshnessWarning" key
fresh → exit 0, no "_freshnessWarning" in card
```
Note: `_check_data_freshness()` is called twice in the `--preflight` path. The first call blocks (exit 4) before CDP. The second call only populates display fields and never blocks if `--ack-stale` is passed. The test for "stale blocks before CDP" is the critical one — it does not require TradingView running.

### 6.3 Other T3 Tests

```
test_portfolio_action.py     → derive_action() all branches (pure function, no I/O)
test_ticker_aliases.py       → normalization round-trips
test_sector_overrides.py     → lookup correctness
test_validate_weights.py     → compute_current, compute_target with fixtures
test_dcf_constraints.py      → scenario weights sum to 1.0, WACC range, FV between bear/bull
test_file_lock.py            → lock acquisition/release (pure Python, no broker)
```

---

## 7. Tier 4 — Plugin/Skill Contract Tests

**Does NOT test AI output quality.** Tests structural presence of safety sections in SKILL.md files.

For every trading-related SKILL.md (`place-order`, `cancel-order`, `modify-order`, `tv-portfolio-sync`), assert:
```
"CONFIRM" or "confirm" present (HITL gate)
data freshness gate mentioned
broker connected check mentioned  
audit trail mentioned
phase separation present (preflight / execute / submit)
```

For external-content skills (`x-news-sweep`):
```
prompt injection guardrails mentioned
external content marked untrusted
gates before any mutation
verify_refresh.py mentioned (or equivalent)
```

For all skills:
```
referenced scripts exist on disk (no dead references)
referenced commands are syntactically valid Python/shell
```

**Location:** `plugins/tests/skills_contract_test.py`

---

## 8. Tier 5 — Frontend Smoke Tests

Playwright. Run after full stack confirms healthy.

```
test_dashboard.spec.ts        → loads, no console errors, heatmap renders, TV badge correct
test_trade_log.spec.ts        → tabs work, Buy opens TradePrepModal, modal dismisses
test_screener.spec.ts         → table renders > 0 rows, sort works, action badges visible
test_portfolio_table.spec.ts  → positions load, Buy/Sell disabled when TV offline
test_valuation_mismatch.spec.ts → mismatch banner appears for bad fixture (added per Opus)
```

---

## 9. Shared Test Infrastructure

### 9.1 Root Runner

```bash
python3 tests/run_tests.py [--tier T0|T1|T2|T3|T4|T5] [--live] [--fast] [--json]
```

- `--fast`: skip `@slow` (network) tests
- `--live`: enable live broker round-trips (T1 only)
- `--i-understand-live-broker-test`: required alongside `--live`
- `--json`: machine-readable output for CI

### 9.2 Complete Directory Layout

```
tests/                                    ← repo root runner + T3 cross-cutting
  run_tests.py
  validate_all_projections.py             ← T3: projection consistency scanner
  README.md

plugins/tradingview/tests/                ← T1
  tv_test_harness.py
  live_test_ledger.py
  conftest.py
  README.md

investment_screener/backend/tests/        ← T2 + T3
  api/
    test_trading_routes.py
    test_trading_extract_json.py
    test_portfolio_routes.py
    test_stock_routes.py
    test_projections_routes.py
    test_screener_routes.py
    test_docs_routes.py
  py_services/
    test_place_order_gates.py
    test_portfolio_action.py
    test_ticker_aliases.py
    test_dcf_constraints.py
    test_file_lock.py
  fixtures/
    portfolio.test.json
    trade_log.test.json
    target_portfolio.test.json
    stdout_samples/                       ← captured place_order.py stdout for extractJson tests
      preflight_output.txt
      preflight_stale_output.txt
      execute_output.txt
      submit_output.txt
  conftest.py

plugins/portfolio-advisor/tests/
  test_validate_weights.py

plugins/tests/
  skills_contract_test.py                 ← T4

investment_screener/frontend/tests/       ← T5
  test_dashboard.spec.ts
  test_trade_log.spec.ts
  test_screener.spec.ts
  test_portfolio_table.spec.ts
```

---

## 10. Implementation Plan

### Phase 1 (current sprint) — 5 tasks, ~8 hours

| # | Task | File | Time | Value |
|---|------|------|------|-------|
| 1 | Fix `portfolio_action.py` import path | `py_services/portfolio_action.py` | 30 min | Production bug fix |
| 2 | T0 compile/syntax gate | `tests/run_tests.py` (T0 section) | 1 hr | Catch build breaks |
| 3 | `validate_all_projections.py` | `tests/validate_all_projections.py` | 2 hrs | INTC bug class across all 70+ tickers |
| 4 | `test_place_order_gates.py` (subprocess) | `backend/tests/py_services/` | 2 hrs | CLI arg + runtime gate validation, no TV |
| 5 | TV prereqs + DOM selector smoke check | `plugins/tradingview/tests/tv_test_harness.py` (Sections 0, 0.5) | 2 hrs | Validate harness preconditions |

**Phase 1 gate: Do NOT implement live round-trip until Phase 2.**

### Phase 2 — Live harness + API foundation (~14 hours)

| # | Task | Notes |
|---|------|-------|
| 6 | Extract `_run_node()` to `tv_node_runner.py` | Prerequisite for reliable harness |
| 7 | Verify $0.01 Questrade acceptance manually | Before coding live round-trip |
| 8 | Live-test orphan ledger (`live_test_ledger.py`) | Safety net before any live orders |
| 9 | T1 Sections 1–3 (dry-run preflight, form-fill, get-orders) | subprocess-first; **capture stdout fixtures during this task** |
| 10 | `extractJson()` unit tests | `test_trading_extract_json.py` — uses stdout fixtures from task 9 |
| 11 | Trade session state machine tests | `test_trading_routes.py` |
| 12 | `INVESTMENT_TOOLKIT_DATA_ROOT` in `paths.ts` | API test prerequisite |
| 13 | T1 Section 4 (live round-trip) | `--live --i-understand-live-broker-test` — LAST, after all above pass |

**Note on Phase 2 ordering:** Task 9 dry-run tests naturally produce the exact stdout needed for `extractJson()` tests. Don't make stdout capture a separate task — capture during the dry-run and feed directly into task 10.

### Phase 3 — Full API + Skill contracts (~12 hours)

| # | Task | Notes |
|---|------|-------|
| 15 | Fix audit date format bug in `trading.ts` | `YYYYMMDD` → `YYYY-MM-DD` |
| 16 | T2 full API suite | All route tests with test fixtures |
| 17 | Skill contract tests (`skills_contract_test.py`) | T4 |
| 18 | T3 remaining (validate_weights, dcf, ticker_aliases) | |

### Phase 4 — Frontend (~8 hours)

| # | Task | Notes |
|---|------|-------|
| 19 | Playwright install + config | `investment_screener/frontend/` |
| 20 | T5 smoke test suite | All 5 specs |

---

## 11. Key Decisions & Rationale

| Decision | Original | Revised | Rationale |
|----------|----------|---------|-----------|
| Subprocess vs. direct import | Direct import primary | **Subprocess primary** | The `portfolio_action.py` bug only manifests through subprocess — direct import hides it |
| $0.01 live test price | Hardcoded $0.01 | **Verify first; use `max(0.01, price*0.01)`** | Questrade may reject far-below-market limits |
| Live mode flag | `--live` only | **`--live` + `--i-understand-live-broker-test`** | Prevents accidental autocomplete/script invocation |
| Valuation consistency | Out of scope | **T3, in scope** | INTC HOLD bug is deterministic math, not AI quality |
| Skill tests | Out of scope | **T4: structural contract, not quality** | SKILL.md safety section presence is testable without LLM |
| API data isolation | "Use fixtures" | **`INVESTMENT_TOOLKIT_DATA_ROOT` env var required** | Without env var override, "fixtures" is aspirational |

---

## 12. Known Gaps and Technical Debt

| Item | Tier | Priority | Notes |
|------|------|----------|-------|
| `trading.js` DOM parsing in inline JS strings (~600 lines) | T1 future | Low | Long-term: extract to `dom-parsers.js` for jsdom unit tests |
| In-memory trade sessions don't survive backend restart | T2 | Medium | Document recovery path; consider JSONL persistence |
| `_run_node()` duplicated x4 | T1 prerequisite | **High — Phase 2** | Extract to `tv_node_runner.py` before harness build |
| Audit date format mismatch (`YYYYMMDD` vs `YYYY-MM-DD`) | T2 | **High — Phase 3** | Fix in `trading.ts` + add test |
| `extractJson()` no tests + greedy regex bug | T2 | **High — Phase 2** | Greedy `/\{[\s\S]+\}/` fails when stdout has two JSON objects; fix with reverse-scan |
| `trading.ts` execute route: exit code 4 → generic 422 | T2 | **High — Phase 3** | Should transition session to `DATA_STALE_BLOCKED` + specific error |
| `trading.ts` `runPy()` timeout → exit code -1 → generic error | T2 | **High — Phase 3** | Handle -1 as `TIMEOUT_BLOCKED` explicitly |
| Session cleanup (30-min stale sessions) | T2 | Low | Add to backlog |
| `place_order.py` God Script (11 responsibilities in one file) | T3 | Low — Future ADR | Future: split into `order_preflight.py`, `order_execute.py`, `order_cancel.py`, etc. Decomposition tracked as formal tech debt |
| `bridge.ts` stale-cache: silent fallback to stale data | T2 | Medium | `spawnPythonScript()` returns stale cache on failure; test `stale=true` + `staleReason` |

---

## 13. Out of Scope

- AI skill quality tests (output correctness for `/strategic-review`, `/evaluate-stock`) — these require LLM evaluation, not deterministic assertions
- Performance/load testing
- TradingView UI visual regression
- Questrade REST API mock server
