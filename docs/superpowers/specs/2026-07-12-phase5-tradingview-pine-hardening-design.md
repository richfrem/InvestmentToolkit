# Phase 5 — TradingView/Pine Hardening

**Status:** Draft, pending user review
**Phase:** Fable5 elevation guide, Phase 5 ("TradingView/Pine Execution")
**Sub-spec order:** After Phase 4 (Track Record) — First sub-spec of Phase 5

## 1. Problem

Phases 1-4 built the analytical backbone: data layer, valuation, risk engine, prediction ledger,
earnings tracking, portfolio evolution audit, and historical backtest analysis. But **execution is
still brittle**: TV CDP connection is sensitive to UI changes, Pine Script management is manual,
alerts don't auto-sync, data-window extraction is fragile, order placement lacks validation gates.

Phase 5 hardens the execution layer: robust TV CDP bridging, automated Pine Script deployment,
reliable alert synchronization, data validation before orders, and comprehensive risk gates on every
trade. This is the **production safety layer** — making the system resilient to TV API changes, user
interruptions, market volatility, and concurrent operations.

## 2. Scope

**In scope (this sub-spec, 5 sub-specs planned):**

### 5A: TV CDP Resilience & Error Recovery
- Implement retry logic for TV CDP connections (exponential backoff, circuit breakers)
- Detect and recover from stale Chrome sessions (auto-restart, port re-binding)
- Add health-check endpoints (port 9222 alive?, chart responsive?)
- Graceful degradation: fallback to cached data on CDP failure
- Validate every CDP response (schema checking, not just parsing)

### 5B: Pine Script Manager
- Centralized Pine Script registry (scripts/ directory with versioning)
- Auto-inject indicators into TV charts (no manual "Add to Chart" clicks)
- Script validation before inject (lint, AST check)
- Version control for Pine library (`ai-ta-levels.pine` and other custom libs)
- Rollback mechanism (revert to prior version on syntax error)

### 5C: Alert & Signal Sync
- Auto-create price/TA alerts in TV when `/daily` generates signals
- Sync TV alert state back to portfolio (e.g., "alert fired" → order execution)
- Alert metadata: linked to E3 claims, thesis breakers, rebalance thresholds
- Prevent duplicate alerts (dedup on symbol+price+direction)
- Webhook receiver for TV alert notifications (optional: real-time integration)

### 5D: Data Window Extraction & Validation
- Robust data-window read (handle Monaco editor variations, lag-tolerant)
- Extract: candle OHLCV, volume, bid/ask spreads, indicator values (RSI, MACD, etc.)
- Validate extraction (sanity checks: O ≤ H, H ≥ L, L ≤ C, volume > 0)
- Cache locally to avoid repeated fetches
- Graceful fail: return last-known-good data + warning

### 5E: Order Execution & Risk Gates
- Pre-flight checks before order placement: size limits, concentration limits, TradingView balance check
- Real-time risk gates: MRC limit (from E1), thesis-breaker veto (from B5), liquidity check
- Order fill confirmation: await trade-log sync before declaring "order done"
- Post-trade validation: verify shares in holdings match order confirmation
- Audit trail: every order attempt logged with decision rationale (from E3/E2 claims)

**Out of scope (deferred):**
- Advanced order types (iceberg, VWAP, TWAP) — limit orders only
- Multi-leg execution (spreads, collars) — single-ticker orders only
- Margin trading or derivatives — cash/equity only
- International brokers beyond Questrade — local broker automation only
- TV strategy automation (Strategy Tester) — manual chart-based execution only
- Custom TV alerting UI — use TV's native alert system

## 3. Current-state findings

- **TV CDP** (`tradingview-cdp/`) works but is fragile:
  - UI class selectors break on TV updates (pitfall #23)
  - Chrome session stales without restart
  - No health checks; failures silent until order fails
  - Port 9222 binding can conflict if not cleaned up
- **Pine Script** management is manual:
  - `ai-ta-levels.pine` exists but is hand-injected
  - No version control or rollback
  - No syntax validation before inject
- **Alerts** are created manually in TV:
  - `/daily` suggests alerts but doesn't create them
  - No sync from TV alerts back to portfolio
  - Alert metadata (linked claims, thresholds) not captured
- **Data Window** extraction works but is brittle:
  - `[data-test-id-value-title]` selector is fragile
  - No validation of extracted OHLCV
  - No caching; repeated fetches can lag
- **Order Execution** lacks gates:
  - `place_order.py` does basic checks but no real-time risk gates
  - No MRC/cluster-variance enforcement (E1 data exists, not used)
  - No thesis-breaker veto (B5 data exists, not used)
  - No post-trade validation against trade log

## 4. Architecture

### 5A: TV CDP Resilience

**New module:** `py_services/tv_cdp_health.py`
- `health_check()` → {port_open: bool, chart_responsive: bool, chrome_version: str, last_error: str}
- `ensure_healthy()` → restart Chrome if needed, re-bind port 9222
- `retry_with_backoff(fn, max_attempts=3, backoff_factor=2)` → exponential retry
- Cache last-known response (fallback on failure)

**Changes to `tv_client.py`:**
- Wrap all `tv_call()` results with validation (schema check, not just parse)
- Log every API error + stack trace to `data/tv_cdp_errors.jsonl` (append-only)
- Implement circuit breaker: 3 failures → fallback mode (cached data only)

### 5B: Pine Script Manager

**New module:** `py_services/pine_script_manager.py`
- Registry: `plugins/tradingview/assets/pinescript-indicators/registry.json`
  ```json
  {
    "ai-ta-levels": {
      "path": "ai-ta-levels.pine",
      "version": "1.2.0",
      "description": "Multi-EMA (21/50/200) + volume bias",
      "last_injected": "2026-07-12T14:30:00Z"
    }
  }
  ```
- `validate_pine_script(file_path)` → lint check, AST parse, no syntax errors
- `inject_pine_script(script_name, chart_symbol)` → auto-click, verify injection, await confirmation
- `rollback_pine_script(script_name, to_version)` → revert to prior version on error

### 5C: Alert & Signal Sync

**New module:** `py_services/alert_manager.py`
- `create_price_alert(ticker, price, direction)` → TV API call, dedup on (ticker, price, direction)
- `sync_alert_state()` → poll TV alerts, check if fired, log to `data/alerts_state.jsonl`
- `link_alert_to_claim(alert_id, claim_id_from_e3)` → cross-reference for audit trail
- Optional webhook receiver: `FastAPI` endpoint on port 5001 for TV alert notifications

**Alert metadata schema:**
```json
{
  "id": "uuid",
  "ticker": "NVDA",
  "price": 876.50,
  "direction": "above|below",
  "type": "price|ta_signal",
  "linked_claim_id": "e3-claim-uuid",
  "created_at": "2026-07-12T14:30:00Z",
  "fired_at": null,
  "state": "pending|fired|expired"
}
```

### 5D: Data Window Extraction & Validation

**New module:** `py_services/data_window_validator.py`
- `extract_data_window(ticker, timeframe)` → OHLCV + indicators from TV data window
- `validate_ohlcv(candle)` → O ≤ H, H ≥ L, L ≤ C, volume > 0, spreads reasonable
- `cache_data_window(key, data)` → local cache with TTL (5 min default)
- `get_cached_or_fetch(key, fetch_fn, ttl=300)` → hit cache first, fallback to fetch

**Validation rules:**
- Volume > 0 (no dead candles)
- Spread < 2% (no stale quotes)
- OHLCV integers/floats only (no garbage)
- Indicators within expected ranges (RSI 0-100, MACD finite)

### 5E: Order Execution & Risk Gates

**New module:** `py_services/order_risk_gates.py`
- `check_risk_gates(order, portfolio_state, e1_risk_snapshot, b5_breaker_state)` → {passed: bool, reasons: []}
- MRC gate: order doesn't push any holding MRC > 25%
- Cluster-variance gate: order doesn't push cluster variance > 60%
- Thesis-breaker gate: order doesn't buy into a TRIGGERED breaker (unless override logged)
- Size gate: order size < threshold (configurable, default 10% of daily volume)
- Balance gate: Questrade available cash >= order cost

**Post-trade validation:**
- Poll trade-log until order appears (with timeout)
- Verify shares in holdings match order confirmation
- Log to `data/orders_executed.jsonl` with gate passage status + decision rationale

## 5. Test Coverage (TDD)

- **5A Tests:** `test_tv_cdp_health_check_detects_stale_chrome.py`, `test_retry_with_backoff_exponential.py`, `test_circuit_breaker_fallback_on_failures.py`
- **5B Tests:** `test_pine_script_validation_catches_syntax_errors.py`, `test_pine_injection_auto_clicks.py`, `test_pine_rollback_on_error.py`
- **5C Tests:** `test_create_price_alert_dedup_on_same_signal.py`, `test_sync_alert_state_from_tv.py`, `test_link_alert_to_e3_claim.py`
- **5D Tests:** `test_data_window_validation_rejects_invalid_ohlcv.py`, `test_data_window_cache_hit_rate.py`, `test_extract_data_window_handles_lag.py`
- **5E Tests:** `test_order_risk_gates_checks_mrc_limit.py`, `test_order_risk_gates_checks_breaker_veto.py`, `test_post_trade_validation_matches_shares.py`

Total: 15+ test files, 60+ tests, all sub-specs.

## 6. Known Limitations & Trade-offs

1. **TV UI fragility** — Selectors may break on TV updates. Mitigation: use `__reactFiber` traversal
   (more stable) instead of CSS classes; monitor and update quarterly.
2. **Pine Script versioning** — Registry is JSON; no full git history per script. Acceptable: scripts
   are small, versioning via registry metadata + git commits of `registry.json` is sufficient.
3. **Alert dedup race condition** — If alerts created in rapid succession, dedup may miss duplicates
   created in parallel. Acceptable: race is extremely rare; fallback is duplicate alert in TV (user
   can manually delete).
4. **Data window lag** — Extraction may lag behind live price. Acceptable: cache + fresh fetch mitigates;
   5-min TTL is conservative for TA use.
5. **Order confirmation timeout** — Trade-log sync may lag (rare: 30-60 sec). Acceptable: timeout
   returns uncertain status; operator must check manually.

## 7. Acceptance Criteria

- All 5 sub-specs implemented and tested (5A-5E)
- TV CDP health checks operational and fallback to cached data on failure
- Pine Script manager validates and injects scripts with rollback on error
- Alerts auto-created for `/daily` signals, synced back to portfolio, linked to E3 claims
- Data window extraction validates OHLCV, caches results, gracefully handles lag
- Order execution passes all risk gates (MRC, cluster variance, breaker veto, size, balance)
- Post-trade validation confirms fills in trade-log and holdings
- All 60+ TDD tests passing
- Full integration: `/daily` → alerts created → orders placed → trades logged → post-trade validated
- Full test suite: 760+ passing (Phase 4 + Phase 5 regression)
- Phase 5 ready to merge to main

## 8. Metrics & Future Use

Phase 5 enables **production execution**:
- TV CDP failures no longer cascade to halted trading (fallback + recovery)
- Pine Script updates are versioned, validated, rollback-safe
- Alerts are actionable (auto-created, synced, auditable)
- Every order is risk-gated and post-trade validated
- Audit trail complete: signal → alert → gate decision → order → fill → settlement

This closes the loop between Phase 4's analysis and the market: the system can now execute with
confidence that safety gates are in place and every decision is auditable.
