# Phase 4, Sub-Spec 4 — E4 Backtest Harness Implementation Plan

**Spec:** `docs/superpowers/specs/2026-07-12-phase4-e4-backtest-harness-design.md`
**Date:** 2026-07-12
**Approach:** TDD via `superpowers:subagent-driven-development` in a fresh worktree

## Dependency check

- ✅ **Git history** available with target-portfolio.json commits
- ✅ **Trade log** exists at `data/trade-log.json` with execution records
- ✅ **yfinance** available for historical price fetches
- ✅ **E3 Prediction Ledger** live for claim correlation
- ✅ **G4 Evolution Events** live for decision logging

## Task decomposition (9 TDD tasks)

### Task 1: Historical target extractor
- [ ] Implement `extract_historical_targets(commit_hash)` helper
- [ ] Clone repo at target commit, read target-portfolio.json
- [ ] Return {ticker: target_weight} dict at that point
- [ ] Graceful error handling for missing/corrupt files
- [ ] Test: `test_extract_historical_targets_at_commit.py`

### Task 2: Price fetcher for backtesting
- [ ] Implement `fetch_backtest_prices(tickers, date)` helper
- [ ] Fetch OHLCV from yfinance for date
- [ ] Handle missing tickers (IPOs, delistings) gracefully
- [ ] Cache prices locally to avoid repeated yfinance calls
- [ ] Test: `test_fetch_backtest_prices_handles_gaps.py`

### Task 3: Rebalance order simulator
- [ ] Implement `simulate_rebalance(targets_before, targets_after, prices)` function
- [ ] Generate buy/sell orders to move from before → after weights
- [ ] Use mid-price for execution (or configurable)
- [ ] Calculate P&L on each trade
- [ ] Test: `test_simulate_rebalance_calculates_orders.py`

### Task 4: Execution quality analyzer
- [ ] Implement `analyze_execution_quality(orders, prices)` helper
- [ ] Compare fill prices vs. VWAP for the day
- [ ] Score quality (% of VWAP, best-case vs. actual)
- [ ] Test: `test_simulate_rebalance_execution_price.py`

### Task 5: Counterfactual generator (timing)
- [ ] Implement `generate_timing_counterfactuals(orders, dates)` function
- [ ] Re-simulate with 1d earlier, 1d later, 5d later prices
- [ ] Calculate alternative P&L for each scenario
- [ ] Test: `test_generate_counterfactuals_1d_delay.py`

### Task 6: Counterfactual generator (threshold)
- [ ] Implement `generate_threshold_counterfactuals(before_weights, orders, prices)` function
- [ ] Re-simulate with ±5% drift thresholds instead of actual
- [ ] Calculate which orders would/wouldn't trigger
- [ ] Test: `test_generate_counterfactuals_threshold_variation.py`

### Task 7: Backtest report generator
- [ ] Implement `generate_backtest_report(start_date, end_date, params)` function
- [ ] Scan git commits in date range for target weight changes
- [ ] For each, simulate rebalance + counterfactuals
- [ ] Aggregate metrics (execution quality, decision count, drift detection)
- [ ] Output to backtest_report.json
- [ ] Test: `test_backtest_report_aggregates_decisions.py`

### Task 8: Prediction ledger correlation
- [ ] Implement `correlate_with_prediction_ledger(backtest_report, predictions)` helper
- [ ] Link each rebalance decision to E3 claims (action rating, fair value)
- [ ] Calculate correlation: did predictions match executed decision quality?
- [ ] Test: `test_backtest_correlates_with_prediction_ledger.py`

### Task 9: Integration into /weekly-review
- [ ] Wire `generate_backtest_report()` into weekly_review.py (new Phase)
- [ ] Add backtest summary to weekly brief output
- [ ] Display decision quality metrics and counterfactual insights
- [ ] Non-blocking: report generation doesn't delay brief output
- [ ] Test: `test_backtest_round_trips_json.py` (full round-trip validation)

## Execution strategy

1. **Worktree setup:** `git worktree add .worktrees/feature-fable5-phase4-e4-backtest-harness`
2. **Task dispatch order:** 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 (sequential, dependencies)
   - Tasks 1-2: Data fetchers (foundation)
   - Tasks 3-4: Execution simulation
   - Tasks 5-6: Counterfactuals (timing + threshold)
   - Task 7: Report aggregation (depends on 1-6)
   - Task 8: Correlation (depends on E3 + Task 7)
   - Task 9: Integration (final wiring)
3. **Review gates:**
   - After Task 1: Verify git commit parsing
   - After Task 2: Verify price fetching (yfinance API)
   - After Task 4: Verify execution simulation accuracy
   - After Task 7: Verify report aggregation
   - After Task 9: Whole-branch review (architecture, integration)
4. **Merge strategy:** Fast-forward to local `main` → push to `origin/main`

## Acceptance gates

- [ ] All 9 TDD tasks complete with passing tests
- [ ] Historical target weights extracted correctly from git
- [ ] Rebalance orders simulated accurately (before → after weights match orders)
- [ ] Execution quality scored vs. VWAP (or configurable benchmark)
- [ ] Counterfactuals generated for timing (1d early/late) and thresholds (±5%)
- [ ] Backtest report aggregates decision-level and portfolio-level metrics
- [ ] Predictions correlated with execution quality (E3 integration)
- [ ] Integration into `/weekly-review` non-blocking and informational
- [ ] All backtest data round-trips to/from JSON without loss
- [ ] Full test suite: 560+ passing (including E3/B4/G4/E4 regression)
- [ ] Whole-branch review returns "Ready to merge"
- [ ] Push to `origin/main`

## Risks & mitigations

| Risk | Mitigation |
|------|-----------|
| Git commit parsing fails (corrupt history) | Task 1 tests with known commits; graceful error on missing files |
| yfinance API rate limits on historical data | Task 2 caches prices locally; batches requests |
| Price gaps (delistings, IPOs) | Gracefully skip; flag in report summary |
| Counterfactual explosion (too many scenarios) | Fixed scenarios: 1d early/late, ±5% threshold (not combinatorial) |
| Backtest report is compute-heavy | Report runs only weekly (not daily); async generation acceptable |
| Correlation with E3 is noisy (many confounding factors) | Pure correlation, no causality; for insight only |

## Timeline estimate

- Tasks 1-2 (data fetchers): 45 min
- Tasks 3-4 (execution simulation): 60 min
- Tasks 5-6 (counterfactuals): 45 min
- Task 7 (aggregation): 30 min
- Task 8 (E3 correlation): 30 min
- Task 9 (integration + final review): 45 min
- **Total (no re-work):** ~4.5 hours
- **With one fix round per 3 tasks:** ~5.5 hours

## Post-completion

- Monitor backtest report quality for first 2-3 weeks
- Gather counterfactual statistics once 20+ decisions analyzed
- Consider expanding counterfactual scenarios if insights warrant
- Future: use backtest insights to tune drift thresholds or execution timing

## Notes

- E4 is the final sub-spec of Phase 4; after this, Phase 4 is fully closed
- Phase 5 (TradingView/Pine hardening) begins after E4 ships
- Backtest insights feed potential Phase 6 work (agent reward modeling)
