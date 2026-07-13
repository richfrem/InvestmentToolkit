# Phase 5 — TradingView/Pine Hardening Implementation Plan

**Spec:** `docs/superpowers/specs/2026-07-12-phase5-tradingview-pine-hardening-design.md`
**Date:** 2026-07-12
**Approach:** TDD via `superpowers:subagent-driven-development` in a fresh worktree

## Dependency check

- ✅ **TV CDP** available at `tradingview-cdp/` with working `cli.js` and Node.js harness
- ✅ **Pine Script** ecosystem: `ai-ta-levels.pine` exists, `plugins/tradingview/assets/pinescript-indicators/` directory ready
- ✅ **yfinance** available for price fetching
- ✅ **Questrade API** available for balance/cash checks (via `QuestradeDataEngine.py`)
- ✅ **Trade log** exists at `investment_screener/backend/data/trade-log.json`
- ✅ **E1 Risk Snapshot** available from prior risk analysis
- ✅ **B5 Thesis Breaker State** tracked in `target-portfolio.json`

## Task decomposition (8 TDD tasks per sub-spec)

### 5A: TV CDP Resilience (8 tasks)

#### Task 5A-1: Health Check Implementation
- [ ] Implement `health_check()` → {port_open: bool, chart_responsive: bool, chrome_version: str, last_error: str}
- [ ] Check port 9222 is open and responding
- [ ] Verify chart loads (chart symbol responds to `chart read` CLI)
- [ ] Return structured status dict
- [ ] Test: `test_tv_cdp_health_check_detects_stale_chrome.py`

#### Task 5A-2: Chrome Session Recovery
- [ ] Implement `ensure_healthy()` → restart Chrome if needed, re-bind port 9222
- [ ] Detect stale chrome (health_check returns false)
- [ ] Kill existing Chrome processes on port 9222
- [ ] Re-spawn TV CDP via `tv_cdp_health.run_tv_cdp_subprocess()`
- [ ] Wait for port ready
- [ ] Test: `test_ensure_healthy_restarts_chrome.py`

#### Task 5A-3: Retry with Exponential Backoff
- [ ] Implement `retry_with_backoff(fn, max_attempts=3, backoff_factor=2)` helper
- [ ] Exponential delay: attempt 1 → 1s, attempt 2 → 2s, attempt 3 → 4s
- [ ] Return result or raise after max_attempts
- [ ] Test: `test_retry_with_backoff_exponential.py`

#### Task 5A-4: Response Validation
- [ ] Implement `validate_tv_response(response, expected_schema)` → bool or raise
- [ ] Schema check: pydantic validation on response dict
- [ ] Handle missing keys gracefully (log warning, return None)
- [ ] Test: `test_validate_tv_response_catches_malformed_json.py`

#### Task 5A-5: Error Logging (JSONL)
- [ ] Implement append-only error logger to `data/tv_cdp_errors.jsonl`
- [ ] Log every `tv_call()` failure: timestamp, function, args, error, stack trace
- [ ] Non-blocking: failures log but don't raise (degrade gracefully)
- [ ] Test: `test_tv_cdp_error_logging_appends_jsonl.py`

#### Task 5A-6: Circuit Breaker Pattern
- [ ] Implement `circuit_breaker` class: tracks failures, switches to fallback on 3 failures
- [ ] States: healthy → unhealthy → fallback
- [ ] On fallback: return last-known-good cached response
- [ ] Reset on successful call
- [ ] Test: `test_circuit_breaker_fallback_on_failures.py`

#### Task 5A-7: Cache Last-Known-Good
- [ ] Implement local cache for TV CDP responses (TTL 5 min)
- [ ] Store every successful response to cache file
- [ ] On failure + circuit breaker, return cached data + warning log
- [ ] Test: `test_cache_fallback_on_circuit_break.py`

#### Task 5A-8: Integration into tv_client.py
- [ ] Wrap all `tv_call()` results with validation + retry + circuit breaker
- [ ] Update `tv_call()` signature to accept retry/fallback flags
- [ ] Log errors to JSONL on every failure
- [ ] Non-blocking: TV failures no longer stop order execution
- [ ] Test: `test_tv_client_wrapped_calls_survive_transient_errors.py`

### 5B: Pine Script Manager (8 tasks)

#### Task 5B-1: Registry Schema & Storage
- [ ] Create `plugins/tradingview/assets/pinescript-indicators/registry.json`
- [ ] Schema: {script_name: {path, version, description, last_injected, hash}}
- [ ] Read/write via pydantic model `PineScriptRegistry`
- [ ] Test: `test_pine_registry_reads_writes_json.py`

#### Task 5B-2: Script Validation (Lint)
- [ ] Implement `validate_pine_script(file_path)` → {valid: bool, errors: []}
- [ ] Run linter (existing `pine_linter.py` or write wrapper)
- [ ] Check syntax via AST parsing
- [ ] Return structured error list
- [ ] Test: `test_pine_script_validation_catches_syntax_errors.py`

#### Task 5B-3: Script Injection
- [ ] Implement `inject_pine_script(script_name, chart_symbol)` → success: bool
- [ ] Read script from registry path
- [ ] Call TV CDP `pine inject --content <script>`
- [ ] Await confirmation via chart state
- [ ] Update registry.last_injected timestamp
- [ ] Test: `test_pine_injection_auto_clicks.py`

#### Task 5B-4: Version Control
- [ ] Implement `list_script_versions(script_name)` → [version_info, ...]
- [ ] Read from git history of registry.json
- [ ] Return version + hash + timestamp
- [ ] Test: `test_pine_version_history_from_git.py`

#### Task 5B-5: Rollback Mechanism
- [ ] Implement `rollback_pine_script(script_name, to_version)` function
- [ ] Restore script file from git history
- [ ] Re-inject (calls inject_pine_script internally)
- [ ] Update registry to new version
- [ ] Test: `test_pine_rollback_on_error.py`

#### Task 5B-6: Script Library Management
- [ ] Centralize `ai-ta-levels.pine` + any new custom libs in registry
- [ ] Support multiple versions in `/versions/` subdirectories
- [ ] Tag scripts with category (level, trend-follower, mean-reversion, etc.)
- [ ] Test: `test_pine_library_manages_multiple_scripts.py`

#### Task 5B-7: Auto-Discovery
- [ ] Scan `plugins/tradingview/assets/pinescript-indicators/` for .pine files
- [ ] Auto-register discovered scripts (if not in registry already)
- [ ] Set version to git commit hash of first addition
- [ ] Test: `test_pine_auto_discovery_registers_scripts.py`

#### Task 5B-8: Integration into /daily
- [ ] Wire into `/daily` workflow: on new signals, auto-inject relevant Pine scripts
- [ ] Example: moving-average signal → inject multi-EMA script
- [ ] Graceful error: skip injection on validation failure, log warning
- [ ] Test: `test_pine_daily_workflow_injects_signals.py`

### 5C: Alert & Signal Sync (8 tasks)

#### Task 5C-1: Alert Creation
- [ ] Implement `create_price_alert(ticker, price, direction)` → alert_id: str
- [ ] Call TV CDP to create alert (via API or CLI)
- [ ] Return TV alert ID
- [ ] Handle errors (rate limits, invalid ticker)
- [ ] Test: `test_create_price_alert_returns_id.py`

#### Task 5C-2: Deduplication
- [ ] Implement `dedup_alerts(ticker, price, direction)` → existing_alert_id or None
- [ ] Check existing alerts for (ticker, price, direction) triple
- [ ] Skip creation if duplicate exists
- [ ] Test: `test_create_price_alert_dedup_on_same_signal.py`

#### Task 5C-3: Alert State Sync
- [ ] Implement `sync_alert_state()` → updated_alerts: []
- [ ] Poll TV for all open alerts
- [ ] Check if any fired (compare to current price)
- [ ] Update state: pending → fired or expired
- [ ] Test: `test_sync_alert_state_from_tv.py`

#### Task 5C-4: Alert Metadata Schema
- [ ] Create schema: `{id, ticker, price, direction, type, linked_claim_id, created_at, fired_at, state}`
- [ ] Store to `data/alerts_state.jsonl` (append-only)
- [ ] Pydantic validation
- [ ] Test: `test_alert_metadata_round_trips_jsonl.py`

#### Task 5C-5: E3 Claim Linking
- [ ] Implement `link_alert_to_claim(alert_id, claim_id_from_e3)` → linked: bool
- [ ] Read E3 claim (from `data/predictions.jsonl`)
- [ ] Create link in alert metadata
- [ ] For audit: "was this alert based on this claim?"
- [ ] Test: `test_link_alert_to_e3_claim.py`

#### Task 5C-6: Webhook Receiver (Optional)
- [ ] Implement FastAPI endpoint on port 5001: `POST /alert-fired`
- [ ] Accept TV alert webhook payload
- [ ] Validate signature (if TV provides one)
- [ ] Update alert state in real-time
- [ ] Non-blocking: if webhook fails, polling fallback continues
- [ ] Test: `test_alert_webhook_receiver_updates_state.py`

#### Task 5C-7: Alert Correlation
- [ ] Implement `get_alerts_for_ticker(ticker)` → active_alerts: []
- [ ] For each active alert, check if it matches a TA signal
- [ ] Score correlation (how close is current price to alert price?)
- [ ] Test: `test_alert_correlation_with_ta_signals.py`

#### Task 5C-8: Integration into /daily
- [ ] Wire into `/daily` workflow: for each signal, auto-create alert
- [ ] Sync alert state at start and end of loop
- [ ] Display fired alerts in brief
- [ ] Test: `test_daily_workflow_creates_and_syncs_alerts.py`

### 5D: Data Window Extraction & Validation (8 tasks)

#### Task 5D-1: Data Window Reader
- [ ] Implement `extract_data_window(ticker, timeframe)` → candle_ohlcv: dict
- [ ] Use TV CDP data-window read (Monaco editor)
- [ ] Extract: open, high, low, close, volume
- [ ] Handle lag (retry with backoff)
- [ ] Test: `test_data_window_extraction_reads_ohlcv.py`

#### Task 5D-2: OHLCV Validation
- [ ] Implement `validate_ohlcv(candle)` → {valid: bool, errors: []}
- [ ] Check: O ≤ H, H ≥ L, L ≤ C, volume > 0
- [ ] Check: spreads < 2% (stale quote detection)
- [ ] Check: types are floats/ints (no NaN, inf)
- [ ] Test: `test_data_window_validation_rejects_invalid_ohlcv.py`

#### Task 5D-3: Indicator Extraction
- [ ] Implement `extract_indicators(timeframe)` → {rsi, macd, bb_upper, bb_lower, ...}
- [ ] Read from TV data window (custom fields)
- [ ] Validate indicator ranges (RSI 0-100, MACD finite, etc.)
- [ ] Graceful fail: return None for missing indicators
- [ ] Test: `test_extract_indicators_validates_ranges.py`

#### Task 5D-4: Local Caching
- [ ] Implement `cache_data_window(key, data, ttl=300)` → cached: bool
- [ ] Store to `data/data_window_cache.jsonl` (rolling window)
- [ ] TTL: 5 min by default (configurable)
- [ ] Use file-based cache (fast, no Redis)
- [ ] Test: `test_data_window_cache_ttl_expiry.py`

#### Task 5D-5: Cache Hit Logic
- [ ] Implement `get_cached_or_fetch(key, fetch_fn, ttl=300)` → data: dict
- [ ] Check cache first (if key exists and not expired)
- [ ] If cache miss, call fetch_fn (async if possible)
- [ ] Update cache on successful fetch
- [ ] Return data (cached or fresh)
- [ ] Test: `test_data_window_cache_hit_rate.py`

#### Task 5D-6: Lag-Tolerant Extraction
- [ ] Implement retry logic with exponential backoff (5 attempts)
- [ ] On stale data (price hasn't moved in 60s), retry
- [ ] Return last-known-good on timeout
- [ ] Log warning: "Data window lagged by Xs"
- [ ] Test: `test_extract_data_window_handles_lag.py`

#### Task 5D-7: Data Window Validation Harness
- [ ] Implement full validation chain: extract → validate OHLCV → validate indicators
- [ ] Return structured result: {valid: bool, candle: dict, indicators: dict, warnings: []}
- [ ] Graceful fail: return partial data + warnings (not exceptions)
- [ ] Test: `test_data_window_validation_chain.py`

#### Task 5D-8: Integration into Order Execution
- [ ] Wire into order_risk_gates.py: extract fresh OHLCV before each order
- [ ] Use extracted data to compute liquidity score (bid/ask spread analysis)
- [ ] Use indicators to veto orders on extreme conditions (RSI > 80 = overbought veto)
- [ ] Test: `test_data_window_integration_with_order_gates.py`

### 5E: Order Execution & Risk Gates (8 tasks)

#### Task 5E-1: MRC Risk Gate
- [ ] Implement `check_mrc_limit(order, portfolio_state)` → passed: bool, reason: str
- [ ] Fetch MRC limit from E1 risk snapshot (default 25%)
- [ ] Check: does this order push any holding MRC > limit?
- [ ] Return {passed: bool, holdings_flagged: []}
- [ ] Test: `test_order_risk_gates_checks_mrc_limit.py`

#### Task 5E-2: Cluster Variance Gate
- [ ] Implement `check_cluster_variance(order, portfolio_state)` → passed: bool, reason: str
- [ ] Check: does this order push cluster variance > 60%?
- [ ] Use existing cluster calculation from portfolio state
- [ ] Return {passed: bool, new_variance: float}
- [ ] Test: `test_order_risk_gates_checks_cluster_variance.py`

#### Task 5E-3: Thesis Breaker Veto
- [ ] Implement `check_breaker_veto(order, b5_breaker_state)` → passed: bool, reason: str
- [ ] Fetch breaker state from `target-portfolio.json`
- [ ] If breaker is TRIGGERED and order is BUY → veto
- [ ] Return {passed: bool, breaker: str or None}
- [ ] Test: `test_order_risk_gates_checks_breaker_veto.py`

#### Task 5E-4: Size Gate
- [ ] Implement `check_order_size(order, daily_volume)` → passed: bool, reason: str
- [ ] Fetch daily volume from yfinance
- [ ] Check: order size < 10% of daily volume (configurable)
- [ ] Return {passed: bool, size_pct_of_volume: float}
- [ ] Test: `test_order_risk_gates_checks_size_limit.py`

#### Task 5E-5: Balance Gate
- [ ] Implement `check_available_balance(order, questrade_cash)` → passed: bool, reason: str
- [ ] Fetch available cash from Questrade API (or cached snapshot)
- [ ] Check: cash >= order cost
- [ ] Return {passed: bool, cash_required: float, cash_available: float}
- [ ] Test: `test_order_risk_gates_checks_balance.py`

#### Task 5E-6: Composite Gate Check
- [ ] Implement `check_risk_gates(order, portfolio_state, e1_snapshot, b5_breaker_state)` → {passed: bool, gates: [], reasons: []}
- [ ] Run all 5 gates (MRC, cluster, breaker, size, balance)
- [ ] Aggregate results
- [ ] Return detailed reasons for each failing gate
- [ ] Test: `test_order_risk_gates_composite_check.py`

#### Task 5E-7: Post-Trade Validation
- [ ] Implement `validate_trade_execution(order, trade_log_entry)` → {matched: bool, shares_delta: float}
- [ ] Wait for order to appear in trade log (poll with timeout: 60s)
- [ ] Compare: order shares vs. trade log shares
- [ ] Compare: order price vs. executed price (flag if slippage > 2%)
- [ ] Return {matched: bool, slippage_pct: float}
- [ ] Test: `test_post_trade_validation_matches_shares.py`

#### Task 5E-8: Order Execution Audit Trail
- [ ] Implement logging to `data/orders_executed.jsonl` (append-only)
- [ ] Log every order attempt: {timestamp, ticker, side, shares, price, risk_gates_passed, risk_gates_failed, rationale_from_e3_claim, trade_log_match}
- [ ] Non-blocking: failures log but don't prevent next order
- [ ] Test: `test_order_audit_trail_round_trips_jsonl.py`

## Execution strategy

1. **Worktree setup:** `git worktree add .worktrees/feature-fable5-phase5-tradingview-pine-hardening`
2. **Sub-spec dispatch order:**
   - 5A (TV CDP Resilience) → Tasks 5A-1 through 5A-8 (sequential, dependencies)
   - 5B (Pine Script Manager) → Tasks 5B-1 through 5B-8 (sequential, dependencies)
   - 5C (Alert & Signal Sync) → Tasks 5C-1 through 5C-8 (sequential, dependencies)
   - 5D (Data Window Extraction) → Tasks 5D-1 through 5D-8 (sequential, dependencies)
   - 5E (Order Execution & Risk Gates) → Tasks 5E-1 through 5E-8 (sequential, dependencies)
3. **Review gates:**
   - After each Task: Task reviewer confirms spec ✅ and quality approved
   - After each Sub-Spec (8 tasks): Whole-spec review confirms integration
   - Final: Whole-branch review (all 5 sub-specs)
4. **Merge strategy:** Fast-forward to local `main` → push to `origin/main`

## Acceptance gates

- [ ] All 40 TDD tasks complete with passing tests
- [ ] TV CDP resilience: health checks, recovery, retry logic, circuit breaker, fallback all operational
- [ ] Pine Script manager: registry, validation, injection, rollback, auto-discovery all working
- [ ] Alert sync: creation, dedup, state sync, metadata, E3 linking all working
- [ ] Data window: extraction, validation (OHLCV + indicators), caching, lag tolerance all working
- [ ] Order execution: all 5 risk gates (MRC, cluster, breaker, size, balance) enforced + post-trade validation + audit trail
- [ ] All 40+ TDD test cases passing
- [ ] Integration tests: /daily workflow creates alerts, gates orders, logs trades
- [ ] Full test suite: 800+ passing (Phase 4 + Phase 5 regression)
- [ ] All Phase 5 code pushed to `origin/main`
- [ ] start_here.md updated with Phase 5 completion
- [ ] Phase 5 ready to merge

## Risks & mitigations

| Risk | Mitigation |
|------|-----------|
| TV UI selectors break on TV updates | Use `__reactFiber` traversal (more stable); monitor quarterly |
| Chrome session stales mid-execution | Auto-restart in ensure_healthy(); circuit breaker as fallback |
| Pine Script injection latency | Cache scripts; validate before inject; rollback on error |
| Alert dedup race (parallel creation) | Lock file or atomic check-then-create (rare collision acceptable) |
| Data window lag (live price stale) | Cache + fresh fetch with exponential backoff; 5-min TTL conservative |
| Order confirmation timeout (trade log lag) | Timeout returns uncertain; operator must check manually (acceptable rare case) |
| Risk gate conflicts (one veto, one pass) | All gates must pass (AND logic); log each veto reason; user can override |

## Timeline estimate

- Sub-spec 5A (TV CDP Resilience): 8 tasks × 30 min = 4 hours
- Sub-spec 5B (Pine Script Manager): 8 tasks × 25 min = 3.5 hours
- Sub-spec 5C (Alert & Signal Sync): 8 tasks × 30 min = 4 hours
- Sub-spec 5D (Data Window Extraction): 8 tasks × 25 min = 3.5 hours
- Sub-spec 5E (Order Execution & Risk Gates): 8 tasks × 35 min = 4.5 hours
- Final review + merge: 1 hour
- **Total (no re-work):** ~20 hours
- **With one fix round per 10 tasks:** ~24 hours (realistic)

## Post-completion

- Monitor TV CDP resilience metrics for 2 weeks (error rate, fallback triggers)
- Validate Pine Script injection success rate on live charts
- Gather alert firing statistics (true positive rate)
- Review order gate veto reasons (which gate triggers most often?)
- Consider Phase 6 work: agent reward modeling on execution quality

## Notes

- Phase 5 is the **production safety layer** — without it, execution is brittle
- All 5 sub-specs ship together (no partial Phase 5)
- Phase 5 enables the `/daily` workflow to execute orders with confidence
- Phase 6 (future) will use Phase 5's audit trails to train reward models
