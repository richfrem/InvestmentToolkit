# Phase 3, Sub-Spec 1 — Portfolio Risk Engine (E1) Design

_Date: 2026-07-05_
_Status: Approved_
_Follows: Phase 2b (Fundamental Analyst + Local TA Engine)_
_Source: `temp/bundles/full-bundle/reviews/fable5-ELEVATION_GUIDE.md` §6 (Workstream E: E1) and §9 (Phase 3)_

## Goal

Give the toolkit a real portfolio risk profile — correlation, volatility, beta,
marginal risk contribution, concentration, pillar-level cluster exposure, historical
stress replay, and VaR/CVaR — computed from actual current holdings and weights.
Informational only in this pass (no gating): output feeds a compact `RISK:` line in
`/daily`'s morning brief. Rendering it in a dedicated `Risk.tsx` frontend page is an
explicit fast-follow, not part of this spec.

This is sub-spec 1 of 5 decomposing Phase 3 (Risk & Rebalancer). Build order agreed
with the user: **E1 (this spec) → C2 regime classifier → B5 thesis breakers → E2
rebalancer v2 → G2 risk-officer/red-team agents.** Later specs (E2, G2) will consume
`risk_snapshot.json` as a data contract; this spec defines that contract.

## Scope

One new script, one wiring change, no schema/gate changes:

```
investment_screener/backend/py_services/
└── risk_engine.py   (E1) — portfolio risk snapshot: correlation, vol/beta, MRC,
                             concentration, cluster exposure, stress replay, VaR/CVaR

plugins/portfolio-advisor/scripts/daily_brief.py  — import compute_risk_snapshot(),
                                                      attach to brief dict, print RISK line
```

`risk_engine.py` is a **real file directly in `py_services/`**, not a plugin-owned
symlink — same precedent as `macro_regime.py`, `framework_score.py`, `technicals.py`:
cross-cutting portfolio-level analytics with no single plugin owner. (Contrast with
`daily_brief.py`/`portfolio_action.py`, which are owned by the portfolio-advisor plugin
and symlinked in.)

## Data sources (all existing, zero new fetch logic)

- `portfolio_io.load_portfolio_state()` + `portfolio_io.compute_weights()` — current
  **actual** weight % per ticker, computed against the broker-authoritative
  `totalEquityUSDCombined`, never re-derived from raw shares×price (standing rule,
  `CLAUDE.md` pitfall #27).
- `target-portfolio.json` — `holdings[].pillarId` + `pillars[]` for cluster grouping.
  Reuses the existing curated taxonomy rather than deriving clusters algorithmically
  from the correlation matrix.
- `market_data.get_prices(tickers + ["SPY"], period="2y", interval="1d")` — daily
  closes for correlation, vol, beta, MRC, VaR/CVaR.
- `market_data.get_prices(tickers + ["SPY"], period="5y", interval="1d")` — **separate
  fetch**, stress-replay only. A 2y trailing window from today doesn't reach the 2022
  rate-shock scenario the guide names; 5y does. Correlation/vol/beta/VaR stay on the 2y
  window as specified.
- Benchmark: **SPY only** (matches `macro_regime.py` and `technicals.py`'s existing
  relative-strength benchmark — no QQQ dual-beta in this pass).

Returns are daily % change, aligned on calendar date via inner join before any
cross-ticker math — same alignment-safety pattern `technicals.py` already uses for
relative strength, to avoid positional misalignment when a holding has a shorter
history than SPY (recent IPOs, etc.).

## Metrics — `compute_*` functions, each independently testable

| Function | Output | Formula / approach |
|---|---|---|
| `compute_correlation_matrix(returns)` | ticker×ticker corr dict | pandas `.corr()` across aligned daily returns |
| `compute_portfolio_vol_beta(returns, weights, benchmark_returns)` | `{vol, beta}` | annualized vol from weighted covariance (`sqrt(w^T Σ w) * sqrt(252)`); beta = `cov(portfolio, SPY) / var(SPY)` |
| `compute_marginal_risk_contribution(weights, cov_matrix)` | `{ticker: pct}` | `MRC_i = w_i · (Σw)_i`, normalized so contributions sum to portfolio vol |
| `compute_concentration(weights)` | `{hhi, top3Weight, effectiveN}` | HHI = `Σw_i²`; top-3 = sum of 3 largest weights; effective N = `1/HHI` |
| `compute_cluster_exposure(weights, pillar_map, mrc)` | list per pillar | group by `pillarId`: weight-sum + sum of member MRCs as `varianceContributionPct` |
| `compute_stress_replay(returns_5y, weights)` | list of scenarios | fixed window `2022_rate_shock` (2022-01-03 → 2022-10-14) + worst-drawdown window found in the 5y data; portfolio return computed with **current weights held static** (explicit simplifying assumption — true historical weights aren't tracked anywhere in the system) |
| `compute_var_cvar(portfolio_returns, confidence=[0.95, 0.99])` | `{var, cvar}` | parametric (normal-distribution assumption: `mean + z*std`) and historical (empirical quantile) at both confidence levels, 1-day horizon; CVaR = average of returns beyond the VaR cutoff |
| `compute_risk_snapshot()` | full dict | orchestrator — same role as `technicals.compute_technical_snapshot()`: loads state, fetches both price windows, builds returns, calls each `compute_*`, assembles output, writes `data/risk_snapshot.json` |

### Missing-data handling

A holding with insufficient price history (recent IPO, fetch failure, calendar
mismatch) is **excluded** from the weight-normalized calcs and logged to a `warnings`
array — never zero-filled, never crashed on. Same pattern as `framework_score.py`'s
reweighting: visible in the output, not silent.

## Output — `data/risk_snapshot.json`

```json
{
  "asOf": "2026-07-05",
  "benchmark": "SPY",
  "portfolioVol": 0.28,
  "portfolioBeta": 1.4,
  "correlationMatrix": {"NVDA": {"PANW": 0.61, "CRWV": 0.72}, "PANW": {"NVDA": 0.61, "CRWV": 0.55}},
  "marginalRiskContribution": {"NVDA": 0.18, "PANW": 0.09},
  "concentration": {"hhi": 0.14, "top3Weight": 0.42, "effectiveN": 7.1},
  "clusterExposure": [
    {"pillarId": "ai_infra", "weight": 0.61, "varianceContributionPct": 72.0}
  ],
  "stressReplay": [
    {"scenario": "2022_rate_shock", "window": ["2022-01-03", "2022-10-14"], "portfolioReturnPct": -31.2}
  ],
  "var": {"parametric": {"p95": -0.021, "p99": -0.034}, "historical": {"p95": -0.019, "p99": -0.041}, "horizonDays": 1, "estimate": true},
  "cvar": {"parametric": {"p95": -0.028, "p99": -0.041}, "historical": {"p95": -0.026, "p99": -0.049}, "estimate": true},
  "warnings": ["CBRS excluded from correlation matrix: only 45 trading days of history"]
}
```

`estimate: true` on `var`/`cvar` per the guide's explicit instruction to label them as
estimates, not precise figures.

## Daily-brief wiring

`daily_brief.py` imports `compute_risk_snapshot` the same way it already imports
`get_macro_regime` (line 173 pattern), calls it once, attaches
`brief["risk_snapshot"] = snapshot`, and prints one compact line:

```
RISK: vol 28% · beta 1.4 · top cluster 61% · MRC leader: NVDA 18%
```

Purely additive — does not touch the existing macro-regime gate logic. These are
different concepts: macro regime = market environment (VIX/SPY/credit), risk snapshot
= this portfolio's own risk profile (correlation/concentration/VaR). Both blocks
coexist in the brief independently.

## Testing (TDD, per repo's non-negotiable rule 1)

- Golden-fixture unit tests per `compute_*` function: small hand-built return series
  with known correlation/HHI/VaR values (no live network).
- Property tests: correlation matrix diagonal = 1.0 and symmetric; MRC values sum to
  portfolio vol; CVaR ≤ VaR at the same confidence level; HHI ∈ (0, 1]; weights sum to
  ~100% pre-exclusion.
- Integration test: `compute_risk_snapshot()` against a 3–4 ticker fixture portfolio
  (fixture prices + fixture `target-portfolio.json`/`portfolio.json`), validating the
  full JSON shape including a deliberately short-history ticker to exercise the
  exclusion/warning path.
- `market_data.get_prices` mocked/fixture-backed in all tests — no live network,
  matching the existing test suite's pattern (`test_technicals.py`,
  `test_framework_score.py`).

All new/changed Python files follow `.agent/rules/coding-conventions.md`: file header +
dual-layer docs on every non-trivial function, full type hints, snake_case, refactor at
50+ lines or 3+ nesting levels.

## Non-goals (explicitly out of scope this spec)

- `Risk.tsx` frontend page — fast-follow spec once the JSON shape is proven in real use
  via the daily brief.
- QQQ dual-beta — SPY-only benchmark this pass.
- Any gating behavior (e.g. blocking ACCUMULATE on high MRC) — informational only,
  same non-gating stance as Phase 2b's framework/peerBench/technicals additions.
- Rebalancer risk-budget consumption (E2) and risk-officer agent (G2) — later sub-specs
  in this phase; they will consume `risk_snapshot.json` as a stable data contract once
  this spec ships.
