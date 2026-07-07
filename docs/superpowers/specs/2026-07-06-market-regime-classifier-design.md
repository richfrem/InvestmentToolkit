# Phase 3, Sub-Spec 2 — Market Regime Classifier (C2) Design

_Date: 2026-07-06_
_Status: Approved_
_Follows: Phase 3 Sub-Spec 1 (E1 Portfolio Risk Engine)_
_Source: `temp/bundles/full-bundle/reviews/fable5-ELEVATION_GUIDE.md` §9 (Phase 3)_

## Goal

Extend the existing 3-signal macro classifier (`macro_regime.py`: VIX/SPY-200d/HYG-LQD,
RISK-ON/NEUTRAL/RISK-OFF only) into a 4-tier composite (RISK_ON/NEUTRAL/RISK_OFF/STRESS)
with three added macro inputs — term-slope (IEF/SHY), breadth (% of active holdings
above their own 200d SMA), and USD strength (UUP) — plus a new per-ticker regime layer:
trend (above/below × rising/falling 200d SMA), momentum percentile (12-1M return vs.
own 2yr history), and volatility state (ATR% percentile vs. own 2yr history).

Informational only in this pass (no gating). Output feeds a `REGIME:` line in `/daily`'s
morning brief, replacing the current `MACRO:` line. Per-ticker regime data is computed
and persisted but not yet rendered per-ticker in the brief — that consumption belongs to
the rebalancer (E2) and triage, which are explicitly out of scope here.

This is sub-spec 2 of 5 decomposing Phase 3 (Risk & Rebalancer). Build order agreed with
the user: E1 (done) → **C2 (this spec)** → B5 thesis breakers → E2 rebalancer v2 → G2
risk-officer/red-team agents. E2 will consume this spec's `market_regime.json` (and E1's
`risk_snapshot.json`) as data contracts.

## Scope

One new script, one wiring change, `macro_regime.py` untouched:

```
investment_screener/backend/py_services/
└── market_regime.py   (C2) — composite 4-tier regime + per-ticker regime layer,
                              wraps macro_regime.py's existing classifiers (no duplication)

plugins/portfolio-advisor/scripts/daily_brief.py  — import swapped from
                                                     macro_regime.get_macro_regime()
                                                     to market_regime.get_market_regime(),
                                                     MACRO line replaced with REGIME line
```

`market_regime.py` **wraps, not replaces** `macro_regime.py`: it imports and reuses
`_classify_vix`, `_classify_spy`, `_classify_credit`, and `get_macro_regime()` directly
for the 3 existing macro signals, layering the 3 new macro signals and the per-ticker
layer on top. `macro_regime.py` stays a real, independently-callable file — same
reuse-over-duplication precedent as `peer_bench.py` reusing
`framework_score.compute_raw_metrics()` in Phase 2b. Real file directly in
`py_services/`, not a plugin-owned symlink — same precedent as `risk_engine.py`,
`macro_regime.py`, `technicals.py`: cross-cutting analytics with no single plugin owner.

## Data sources

**Macro layer (6 signals, all yfinance ETF/index closes, 5-day history — same pattern
as the existing 3):**

| Signal | Source | Reused or new |
|---|---|---|
| VIX | `^VIX` | Reused (`macro_regime._classify_vix`) |
| SPY vs 200d | `SPY` 1y history | Reused (`macro_regime._classify_spy`) |
| Credit (HYG/LQD) | `HYG`, `LQD` | Reused (`macro_regime._classify_credit`) |
| Term-slope | `IEF`/`SHY` price ratio | New — same ETF-ratio pattern as HYG/LQD; falling ratio = curve flattening/inversion |
| Breadth | % active holdings above own 200d SMA | New — computed from the per-ticker layer's own price fetch, not a separate call |
| USD strength | `UUP` vs its own 200d SMA | New — same ABOVE/NEAR/BELOW shape as the SPY signal |

**Per-ticker layer:**

- Ticker universe: active holdings only (`role not in {"exit", "avoid"}` — the real
  enum values, per `update_thesis.py`'s validation) read directly from
  `target-portfolio.json`'s `holdings[]` list, same direct-read pattern
  `risk_engine.py` already uses for its `pillar_map`. **Not**
  `portfolio_io.load_portfolio_state()` — that loader reads `portfolio.json` (actual
  broker shares/prices) and has no `role` field at all; role lives only in
  `target-portfolio.json`.
- `market_data.get_prices(tickers, period="2y", interval="1d")` — one batched, cached
  fetch covers trend, momentum percentile, and ATR% percentile for every ticker, and
  doubles as the breadth calculation's data source.

## Metrics — `compute_*` functions, each independently testable

| Function | Output | Formula / approach |
|---|---|---|
| `_classify_term_slope(ratio)` | `(signal, pts)` | IEF/SHY ratio: rising → `STEEPENING` (+1), flat → `NEUTRAL` (0), falling → `FLATTENING` (-1) |
| `_classify_breadth(pct)` | `(signal, pts)` | `>60% → HEALTHY (+1)`, `40-60% → NEUTRAL (0)`, `<40% → WEAK (-1)` |
| `_classify_dxy(pct_vs_200d)` | `(signal, pts)` | mirrors `_classify_spy` thresholds, inverted sense (strong USD is a risk-off tell for this portfolio's international/rate-sensitive names) |
| `_classify_regime_v2(score, unavailable)` | `(regime, degraded)` | additive across all 6 signals: `score >= 3 → RISK_ON`, `score >= 0 → NEUTRAL`, `score >= -3 → RISK_OFF`, else `STRESS`; **3+ of 6 signals unavailable → forced STRESS** (fail-safe, stricter than E1-era 2-of-3→RISK-OFF since STRESS is now the more severe floor) |
| `compute_breadth(prices_by_ticker)` | `float` | % of tickers whose latest close > their own trailing 200d SMA |
| `classify_ticker_trend(closes)` | `{position, slope}` | `ABOVE`/`BELOW` vs. 200d SMA; `RISING`/`FALLING` from the SMA's own 20d slope — 4 combined states (`UPTREND`, `DOWNTREND`, `WEAKENING`, `BASING`) |
| `compute_momentum_percentile(closes)` | `float` | 12-1M total return (skip most recent month, standard momentum convention) ranked as a percentile against the same rolling metric computed at every trading day in the ticker's own 2yr window |
| `compute_volatility_percentile(highs, lows, closes)` | `float` | ATR% at each day in the 2yr window, current value ranked as a percentile against that same-ticker history. `technicals.py`'s `compute_atr()` only returns the latest scalar, so this reuses its internal `_true_range`/`_wilder_smooth` helpers (imported directly, not duplicated) to get the full ATR series, then divides by close and ranks the last value against the series |
| `compute_market_regime()` | full dict | orchestrator — loads state, fetches macro signals + per-ticker prices, computes breadth, classifies composite regime, classifies each ticker, assembles output, writes `data/market_regime.json` |

### Missing-data handling

- Macro signals: same per-signal try/except as `macro_regime.py` today — a failure
  contributes 0 score and an `UNAVAILABLE` label, counted toward the 3-of-6 fail-safe.
- Per-ticker: a ticker with insufficient history (recent IPO, <2yr of data, fetch
  failure) is **excluded** from breadth and gets a `null` trend/momentum/volatility
  entry with a `warnings` note — never zero-filled, never crashes the snapshot. Same
  pattern as `risk_engine.py`'s exclusion handling.

## Output — `data/market_regime.json`

```json
{
  "asOf": "2026-07-06",
  "regime": "RISK_ON",
  "score": 4,
  "degraded": false,
  "signals": {
    "vix": {"value": 14.2, "signal": "LOW"},
    "spy200d": {"value": 3.1, "signal": "ABOVE"},
    "credit": {"value": 0.64, "signal": "HEALTHY"},
    "termSlope": {"value": 1.02, "signal": "STEEPENING"},
    "breadth": {"value": 71.4, "signal": "HEALTHY"},
    "dxy": {"value": -1.8, "signal": "ABOVE"}
  },
  "tickerRegimes": [
    {
      "ticker": "NVDA",
      "trend": {"position": "ABOVE", "slope": "RISING", "state": "UPTREND"},
      "momentumPercentile": 82.0,
      "volatilityPercentile": 41.0
    }
  ],
  "warnings": ["CBRS excluded from breadth/trend: only 45 trading days of history"]
}
```

## Daily-brief wiring

`daily_brief.py` swaps its import from `macro_regime.get_macro_regime` to
`market_regime.get_market_regime` (same call-site pattern, same
try/except-with-stderr-breadcrumb error handling as E1's risk-snapshot wiring), and the
existing `MACRO:` line is replaced with:

```
REGIME: RISK_ON · breadth 71% · term-slope +1.0 · degraded: no
```

Per-ticker `tickerRegimes` are persisted to `market_regime.json` and available to
`brief["market_regime"]` in the JSON snapshot, but not rendered per-ticker in the
terminal brief this pass — E2/triage render and act on them later.

## Testing (TDD, per repo's non-negotiable rule 1)

- Golden-fixture unit tests per new `_classify_*`/`compute_*` function: hand-built
  inputs with known expected signal/score/percentile outputs, no live network.
- Regression test for the 3-of-6-unavailable → forced STRESS fail-safe, mirroring
  `macro_regime.py`'s existing degraded-fail-safe test structure.
- Per-ticker function tests against synthetic price series: monotonically rising series
  → `UPTREND`; flat-then-spike series → known ATR% percentile; a short/insufficient
  series → excluded with warning, not a crash.
- Integration test: `compute_market_regime()` against a fixture portfolio (3-4 tickers,
  fixture prices + fixture `target-portfolio.json`), validating the full JSON shape
  including one deliberately short-history ticker to exercise the exclusion/warning path.
- `market_data.get_prices` mocked/fixture-backed in all tests — no live network, matching
  `test_risk_engine.py`/`test_macro_regime.py`.

All new/changed Python files follow `.agent/rules/coding-conventions.md`: file header +
dual-layer docs on every non-trivial function, full type hints, snake_case, refactor at
50+ lines or 3+ nesting levels.

## Non-goals (explicitly out of scope this spec)

- Rendering per-ticker regime in the daily brief or dashboard — E2/triage consume it.
- Any gating behavior (e.g. blocking ACCUMULATE in STRESS, half-sizing in RISK_OFF) —
  that logic belongs to E2 and B5, which will consume `market_regime.json` as a stable
  data contract once this spec ships.
- Replacing or deprecating `macro_regime.py` — it remains a real, independently-callable
  file; `market_regime.py` wraps it.
- Broad-market breadth (sector ETFs, S&P constituents) — breadth is scoped to this
  portfolio's active holdings only.
- Direct Treasury yield series (`^TNX`/`^IRX`) — term-slope uses the IEF/SHY ETF-ratio
  proxy, consistent with the existing HYG/LQD pattern.
