# Phase 4, Sub-Spec 4 — E4 Backtest Harness

**Status:** Draft, pending user review
**Phase:** Fable5 elevation guide, Phase 4 ("Track Record")
**Sub-spec order:** After G4 (Structured Evolution Events) — Final sub-spec of Phase 4

## 1. Problem

E3 records predictions and grades them, B4 tracks earnings forecasts, G4 logs portfolio events.
But **none of them answer: what if we had executed differently?**

When we trim a position on earnings beat, how much return did we leave on the table (or protect)?
When a rebalance fills and the next day reverses, was it bad timing or good risk management?
When we override a thesis breaker and the stock reverses, was the override justified or a mistake?

E4 formalizes counterfactual analysis: given a historical sequence of target weights and rebalance
decisions (all captured in `target-portfolio.json` version history), simulate alternative executions
and compute returns under different thresholds, timing, and decision rules. This is the feedback
loop that closes the system: predictions → grades → correlations → **counterfactual analysis → agent reward**.

## 2. Scope

**In scope (this sub-spec):**
- A backtesting engine that replays historical rebalance decisions from `target-portfolio.json` commits
- Price-based simulation (fetch historical prices, compute fill prices at rebalance dates)
- Counterfactual order generation: what if we had rebalanced 1 day earlier / later, or at different thresholds?
- Returns analysis: executed vs. counterfactual, by holding, by execution timing, by thesis state
- A simple replay dashboard: "Portfolio Decision Quality Report" with execution analysis
- Integration into `/weekly-review` Phase (non-blocking, informational only)

**Out of scope (deferred):**
- Agent retraining on backtest results — pure analysis, no model updates
- Real-time strategy optimization — backtests are historical analysis only
- Multi-account accounting in backtests — simulate as single account, note limitations
- Transaction costs/slippage modeling — assume execution at OHLC (conservative mid-price)
- Survivorship bias analysis (stocks that delisted, etc.) — use available data, note gaps
- Statistical significance testing (Sharpe ratios, drawdown analysis) — correlation-grade precision only
- Alternative order types (stop-loss, iceberg, VWAP) — limit orders only, day or GTC

## 3. Current-state findings

- **`target-portfolio.json` version history** — Git history contains every rebalance target weight
  decision (commits updating `globalSettings.driftThresholdPct`, `account_policy.json`, or holdings
  `targetWeight` fields). Each commit represents a user or agent decision point.
- **Trade log** (`data/trade-log.json`) — Structured records of actual fills (ticker, date, shares,
  price, account). Can be matched to rebalance dates to find execution prices.
- **Historical prices** — yfinance provides OHLCV for any stock any date (gaps exist for IPOs,
  tickers that changed). Can fetch retrospectively.
- **Prediction ledger (E3)** — Records claims made (action ratings, fair values). Can correlate
  claims with rebalance decisions (was this rebalance a BUY or TRIM signal?).
- **Rebalance plan (E2)** — `data/rebalance_plan.json` contains the proposed orders + rationale.
  Historical plans are not archived; only current plan on disk. Will need to reconstruct from
  diffs if available.

## 4. Architecture

### Three main components

#### 1. Historical Target Weight Extractor
**`extract_historical_targets(commit_hash)`** → dict of {ticker: target_weight} at that commit

- Clones repo at target commit, reads `target-portfolio.json`
- Returns holdings with targetWeight field at that point in time
- Errors gracefully if commit is corrupted or file missing

#### 2. Backtest Engine
**`simulate_rebalance(targets_before, targets_after, prices_at_date)`** → {holdings, orders, returns}

- Inputs: old target weights, new target weights, OHLCV prices for all holdings at rebalance date
- Simulates execution (limit orders filled at mid-price or better)
- Returns: executed orders, new holdings, P&L on executed trades
- Counterfactuals: re-run with different execution prices (open, close, high, low)

#### 3. Analysis Report Generator
**`generate_backtest_report(start_date, end_date, counterfactual_params)`** → JSON summary

- Scans git commits in date range for target weight changes
- For each rebalance decision, fetches prices, simulates execution
- Computes: actual returns vs. counterfactual (1d delay, 5d delay, 10% tighter thresholds)
- Aggregates: average execution quality (% vs. VWAP), drift detection rate, over/underweighting
- Formats for `/weekly-review` display

### Data Flow

```
git history
   ↓
extract_historical_targets() → {ticker: weight} per commit
   ↓
match to rebalance date
   ↓
fetch_prices(date, tickers) → OHLCV
   ↓
simulate_rebalance(before, after, prices) → orders, P&L
   ↓
generate_counterfactuals(orders) → [+1d delay, -1d early, threshold ±5%]
   ↓
analyze_returns() → report JSON
   ↓
/weekly-review display
```

### Output Schema: `data/backtest_report.json`

```json
{
  "report_date": "2026-07-12",
  "backtest_period": {
    "start": "2026-01-01",
    "end": "2026-07-12"
  },
  "rebalances_analyzed": 12,
  "decisions": [
    {
      "decision_date": "2026-07-01",
      "holdings_affected": ["NVDA", "PANW"],
      "executed": {
        "nvda_orders": {"shares": -5, "price": 876.50, "pnl": 450},
        "panw_orders": {"shares": +3, "price": 185.20, "pnl": -120}
      },
      "counterfactuals": {
        "1d_delay": {"pnl": -200, "reason": "prices fell 2.1%"},
        "1d_early": {"pnl": +350, "reason": "prices rose 1.8%"},
        "threshold_+5pct": {"orders_generated": 1, "pnl": 120, "reason": "fewer rebalances"}
      }
    }
  ],
  "summary": {
    "total_executed_pnl": 2850,
    "avg_counterfactual_gap": -45,
    "execution_quality_vs_vwap": 0.98,
    "drift_detection_rate": 0.92,
    "optimal_threshold": "20%_relative"
  }
}
```

## 5. Test Coverage (TDD)

- **`test_extract_historical_targets_at_commit.py`** — Correctly reads target-portfolio.json at specific git commit
- **`test_simulate_rebalance_calculates_orders.py`** — Generates correct buy/sell orders given before/after weights
- **`test_simulate_rebalance_execution_price.py`** — Uses mid-price or better for fills
- **`test_simulate_rebalance_handles_new_positions.py`** — Positions added mid-year handled correctly
- **`test_generate_counterfactuals_1d_delay.py`** — Re-simulates order with prices 1d later
- **`test_generate_counterfactuals_threshold_variation.py`** — Generates counterfactuals at ±5% drift threshold
- **`test_backtest_report_aggregates_decisions.py`** — Weekly report correctly sums execution quality metrics
- **`test_backtest_correlates_with_prediction_ledger.py`** — Links rebalance decisions to E3 claims
- **`test_backtest_round_trips_json.py`** — Report round-trips to/from JSON without loss

## 6. Known Limitations & Trade-offs

1. **No transaction costs** — Simulates at mid-price; ignores commissions, slippage, market impact.
  Acceptable: conservative, order-of-magnitude correct, sufficient for decision quality analysis.

2. **Single account simulation** — Backtests treat portfolio as monolithic; doesn't model per-account
  tax effects or separate cash pools. Acceptable: macro-level timing analysis is decoupled from
  micro-level account structure.

3. **No futures/options** — Only equity holdings. Acceptable: portfolio is equity-heavy, futures
  are marginal.

4. **Survivorship bias** — Tickers that delisted or changed symbols are skipped. Acceptable: rare,
  and gap is noted in report.

5. **Historical target-portfolio commits only** — Backtests assume target weights exist in git history.
  In-between states (manual user overrides) not captured. Acceptable: commit history is authoritative;
  manual tweaks are tracked in evolution_events.jsonl if logged.

6. **No adaptive thresholds** — Counterfactuals use fixed ±5% threshold. Acceptable: one-shot analysis
  per period; multiple thresholds can be tried offline.

## 7. Acceptance Criteria

- Extract historical target weights at any git commit
- Simulate rebalance orders given before/after weights and prices
- Generate counterfactuals (1d delay, threshold variation)
- Analyze execution quality vs. counterfactual strategies
- Aggregate weekly backtest report with decision-level and portfolio-level metrics
- All 9 TDD test cases pass
- Report round-trips to/from JSON without data loss
- Integration into `/weekly-review` (informational Phase, non-blocking)
- Full test suite: 550+ tests pass (including E3/B4/G4 regression)

## 8. Metrics & Future Use

E4 enables **execution quality audit**:
- "Are we rebalancing too frequently or too infrequently?"
- "Do we execute at good prices (vs. daily VWAP)?"
- "Would waiting 1-2 days have been better or worse?"
- "Do our drift thresholds match actual market behavior?"

The counterfactual analysis is the bridge between E3's predictions (what did we claim?) and
actual outcome (what happened?). It closes the feedback loop: prediction → execution → outcome
→ reward signal for future decisions.
