# Market Regime Classifier (C2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `market_regime.py` — a 4-tier composite market regime classifier
(RISK_ON/NEUTRAL/RISK_OFF/STRESS) that wraps the existing 3-signal `macro_regime.py`
and adds term-slope, breadth, and USD-strength signals, plus a per-ticker layer
(trend, momentum percentile, volatility percentile) for every active portfolio
holding — then wire it additively into `/daily`'s morning brief.

**Architecture:** One new file, `investment_screener/backend/py_services/market_regime.py`,
built bottom-up as pure, independently-testable functions (composite classifiers →
breadth/ticker-universe loading → per-ticker trend/momentum/volatility → orchestrator),
then a small additive change to `daily_brief.py`. `macro_regime.py` is never modified.

**Tech Stack:** Python 3, pandas, pytest. Reuses `market_data.get_prices()` (cached
yfinance fetch), `macro_regime._classify_vix/_classify_spy/_classify_credit` and
`get_macro_regime()`, and `technicals._true_range/_wilder_smooth`.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-07-06-market-regime-classifier-design.md` — read
  it once before starting; every task below implements a piece of it.
- `macro_regime.py` is never modified — `market_regime.py` imports from it only.
- No new yfinance/network calls beyond what `market_data.get_prices()` and
  `macro_regime.get_macro_regime()` already make — no raw `yf.Ticker`/`yf.download`
  calls inside `market_regime.py` itself.
- Ticker field is always `ticker`, never `symbol`, when reading `target-portfolio.json`
  (CLAUDE.md rule 10).
- Active holdings = `role not in {"exit", "avoid"}` — real enum values, not `"exited"`.
- All new/changed Python files: file header + Google-style docstrings on every
  non-trivial function, full type hints, snake_case, refactor at 50+ lines or 3+
  nesting levels (`.agent/rules/coding-conventions.md`).
- TDD: every function gets its failing test written first (repo's non-negotiable
  rule 1). No live network calls in tests — `market_data.get_prices` is
  monkeypatched/fixture-backed throughout, same pattern as `test_risk_engine.py`.
- Commit after every task.

---

## Task 1: Composite classifiers — term-slope, breadth, DXY, 4-tier regime

**Files:**
- Create: `investment_screener/backend/py_services/market_regime.py`
- Test: `investment_screener/backend/tests/py_services/test_market_regime.py`

**Interfaces:**
- Produces: `_classify_term_slope(ratio: float) -> tuple[str, int]`,
  `_classify_breadth(pct: float) -> tuple[str, int]`,
  `_classify_dxy(pct_vs_200d: float) -> tuple[str, int]`,
  `_classify_regime_v2(score: int, unavailable: int) -> tuple[str, bool]`

- [ ] **Step 1: Write the failing tests**

```python
"""Tests for market_regime.py — 4-tier composite regime classifier (Phase 3, C2)."""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
PY_SERVICES = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(PY_SERVICES))

from market_regime import (  # noqa: E402
    _classify_term_slope,
    _classify_breadth,
    _classify_dxy,
    _classify_regime_v2,
)


class TestClassifyTermSlope:
    def test_rising_ratio_is_steepening(self):
        assert _classify_term_slope(1.05) == ("STEEPENING", 1)

    def test_flat_ratio_is_neutral(self):
        assert _classify_term_slope(1.0) == ("NEUTRAL", 0)

    def test_falling_ratio_is_flattening(self):
        assert _classify_term_slope(0.95) == ("FLATTENING", -1)


class TestClassifyBreadth:
    def test_high_breadth_is_healthy(self):
        assert _classify_breadth(71.4) == ("HEALTHY", 1)

    def test_mid_breadth_is_neutral(self):
        assert _classify_breadth(50.0) == ("NEUTRAL", 0)

    def test_low_breadth_is_weak(self):
        assert _classify_breadth(25.0) == ("WEAK", -1)


class TestClassifyDxy:
    def test_dxy_above_200d_is_above(self):
        assert _classify_dxy(3.0) == ("ABOVE", 1)

    def test_dxy_near_200d_is_near(self):
        assert _classify_dxy(0.0) == ("NEAR", 0)

    def test_dxy_below_200d_is_below(self):
        assert _classify_dxy(-3.0) == ("BELOW", -1)


class TestClassifyRegimeV2:
    def test_score_three_is_risk_on(self):
        assert _classify_regime_v2(3, unavailable=0) == ("RISK_ON", False)

    def test_score_zero_is_neutral(self):
        assert _classify_regime_v2(0, unavailable=0) == ("NEUTRAL", False)

    def test_score_negative_three_is_risk_off(self):
        assert _classify_regime_v2(-3, unavailable=0) == ("RISK_OFF", False)

    def test_score_below_negative_three_is_stress(self):
        assert _classify_regime_v2(-4, unavailable=0) == ("STRESS", False)

    def test_two_of_six_unavailable_tolerated(self):
        assert _classify_regime_v2(3, unavailable=2) == ("RISK_ON", False)

    def test_three_of_six_unavailable_forces_stress(self):
        assert _classify_regime_v2(0, unavailable=3) == ("STRESS", True)

    def test_all_six_unavailable_forces_stress(self):
        assert _classify_regime_v2(1, unavailable=6) == ("STRESS", True)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest investment_screener/backend/tests/py_services/test_market_regime.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'market_regime'`

- [ ] **Step 3: Write minimal implementation**

```python
#!/usr/bin/env python3
"""
market_regime.py (Python Service)
=====================================

Purpose:
    4-tier market regime classifier (RISK_ON/NEUTRAL/RISK_OFF/STRESS) that
    wraps macro_regime.py's existing 3-signal composite (VIX, SPY vs 200d,
    HYG/LQD credit) and adds term-slope (IEF/SHY), breadth (% of active
    portfolio holdings above their own 200d SMA), and USD strength (UUP vs
    its own 200d) — 6 signals total. Also produces a per-ticker regime
    layer (trend, momentum percentile, volatility percentile) for every
    active holding. Informational only — does not gate any action. See
    docs/superpowers/specs/2026-07-06-market-regime-classifier-design.md.

    macro_regime.py is never modified; this module imports and reuses its
    classifiers directly rather than duplicating them.

Layer: Backend / Python Services / Regime

Usage:
    python3 market_regime.py --pretty
    python3 market_regime.py --no-save --pretty
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = REPO_ROOT / "investment_screener/backend/data"
TARGET_PATH = DATA_DIR / "theses/target-portfolio.json"
MARKET_REGIME_PATH = DATA_DIR / "market_regime.json"

INACTIVE_ROLES = {"exit", "avoid"}


def _classify_term_slope(ratio: float) -> tuple[str, int]:
    """Classify the IEF/SHY (10yr/1-3yr Treasury ETF) price ratio trend.

    A rising ratio means long-duration bonds are outperforming short-duration
    ones — the curve is steepening. A falling ratio means the opposite —
    flattening or inverting, a classic recession-risk tell. Same ETF-ratio
    pattern as macro_regime.py's existing HYG/LQD credit proxy.

    Args:
        ratio: IEF close / SHY close.

    Returns:
        Tuple of (signal_label, score_pts).
    """
    if ratio > 1.02:
        return "STEEPENING", 1
    if ratio >= 0.98:
        return "NEUTRAL", 0
    return "FLATTENING", -1


def _classify_breadth(pct: float) -> tuple[str, int]:
    """Classify the % of active portfolio holdings trading above their own 200d SMA.

    Args:
        pct: Percentage (0-100) of active holdings above their own 200d SMA.

    Returns:
        Tuple of (signal_label, score_pts).
    """
    if pct > 60:
        return "HEALTHY", 1
    if pct >= 40:
        return "NEUTRAL", 0
    return "WEAK", -1


def _classify_dxy(pct_vs_200d: float) -> tuple[str, int]:
    """Classify USD strength (UUP vs its own 200d SMA).

    A strong, rising dollar is a risk-off tell for this portfolio's
    international and rate-sensitive names — mirrors _classify_spy's
    ABOVE/NEAR/BELOW shape but the same direction (ABOVE = risk-on points),
    since dollar strength here is being used as one input among six, not
    as a standalone directional call.

    Args:
        pct_vs_200d: Percentage UUP is above (positive) or below (negative)
            its 200D SMA.

    Returns:
        Tuple of (signal_label, score_pts).
    """
    if pct_vs_200d > 2:
        return "ABOVE", 1
    if pct_vs_200d > -2:
        return "NEAR", 0
    return "BELOW", -1


def _classify_regime_v2(score: int, unavailable: int) -> tuple[str, bool]:
    """Map the 6-signal composite score to a 4-tier regime, with a
    degraded-data fail-safe stricter than macro_regime.py's 3-signal version.

    With 3+ of 6 signals unavailable, half the classifier's inputs are dark —
    forced STRESS (the most severe tier) rather than the fail-safe RISK-OFF
    macro_regime.py uses for its 2-of-3 threshold, since STRESS is now the
    floor and losing half the inputs deserves the harshest label, not a
    milder one.

    Args:
        score: Sum of all 6 signals' point contributions.
        unavailable: How many of the 6 component signals failed to fetch.

    Returns:
        Tuple of (regime_label, degraded_flag).
    """
    if unavailable >= 3:
        return "STRESS", True
    if score >= 3:
        return "RISK_ON", False
    if score >= 0:
        return "NEUTRAL", False
    if score >= -3:
        return "RISK_OFF", False
    return "STRESS", False


def main() -> None:
    parser = argparse.ArgumentParser(description="Market regime classifier")
    parser.add_argument("--pretty", action="store_true")
    parser.add_argument("--no-save", action="store_true", help="Print only, skip writing market_regime.json")
    args = parser.parse_args()
    print("market_regime.py: orchestrator not yet implemented (see Task 6)", file=sys.stderr)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest investment_screener/backend/tests/py_services/test_market_regime.py -v`
Expected: PASS (13 tests)

- [ ] **Step 5: Commit**

```bash
git add investment_screener/backend/py_services/market_regime.py investment_screener/backend/tests/py_services/test_market_regime.py
git commit -m "feat: add market_regime.py 4-tier composite classifiers (C2 task 1)"
```

---

## Task 2: Active ticker loader + breadth computation

**Files:**
- Modify: `investment_screener/backend/py_services/market_regime.py`
- Test: `investment_screener/backend/tests/py_services/test_market_regime.py`

**Interfaces:**
- Consumes: `INACTIVE_ROLES` (Task 1), `TARGET_PATH` (Task 1)
- Produces: `_load_active_tickers(target_portfolio_path: Path) -> list[str]`,
  `_sma(closes: pd.Series, period: int) -> pd.Series`,
  `compute_breadth(prices_by_ticker: dict[str, dict]) -> tuple[float | None, list[str]]`

- [ ] **Step 1: Write the failing tests**

Append to `test_market_regime.py`:

```python
import json

import pandas as pd
import pytest

from market_regime import (  # noqa: E402
    _load_active_tickers,
    _sma,
    compute_breadth,
)


def _price_rows(closes: list[float], start_day: int = 1) -> list[dict]:
    return [
        {"date": f"2024-01-{start_day + i:02d}", "open": c, "high": c, "low": c,
         "close": c, "volume": 1000.0}
        for i, c in enumerate(closes)
    ]


class TestLoadActiveTickers:
    def test_excludes_exit_and_avoid_roles(self, tmp_path):
        target = {"holdings": [
            {"ticker": "NVDA", "role": "accumulate"},
            {"ticker": "OLD1", "role": "exit"},
            {"ticker": "OLD2", "role": "avoid"},
            {"ticker": "CBRS", "role": "watchlist"},
        ]}
        path = tmp_path / "target-portfolio.json"
        path.write_text(json.dumps(target))

        tickers = _load_active_tickers(path)

        assert set(tickers) == {"NVDA", "CBRS"}

    def test_empty_holdings_returns_empty_list(self, tmp_path):
        path = tmp_path / "target-portfolio.json"
        path.write_text(json.dumps({"holdings": []}))
        assert _load_active_tickers(path) == []


class TestSma:
    def test_sma_matches_manual_average(self):
        closes = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        result = _sma(closes, period=3)
        assert result.iloc[-1] == pytest.approx(4.0)  # mean(3,4,5)

    def test_sma_is_nan_before_period(self):
        closes = pd.Series([1.0, 2.0])
        result = _sma(closes, period=3)
        assert pd.isna(result.iloc[-1])


class TestComputeBreadth:
    def test_all_above_200d_is_100_pct(self):
        # 210 rising closes -> last close is above its own 200d SMA
        rising = list(range(1, 211))
        prices = {
            "A": {"data": _price_rows([float(c) for c in rising])},
            "B": {"data": _price_rows([float(c) for c in rising])},
        }
        breadth, excluded = compute_breadth(prices)
        assert breadth == pytest.approx(100.0)
        assert excluded == []

    def test_one_below_200d_is_50_pct(self):
        rising = [float(c) for c in range(1, 211)]
        falling = [float(c) for c in range(210, 0, -1)]
        prices = {
            "A": {"data": _price_rows(rising)},
            "B": {"data": _price_rows(falling)},
        }
        breadth, excluded = compute_breadth(prices)
        assert breadth == pytest.approx(50.0)
        assert excluded == []

    def test_short_history_ticker_excluded_not_crashed(self):
        rising = [float(c) for c in range(1, 211)]
        short = [100.0, 101.0, 99.0]
        prices = {
            "A": {"data": _price_rows(rising)},
            "SHORT": {"data": _price_rows(short)},
        }
        breadth, excluded = compute_breadth(prices)
        assert excluded == ["SHORT"]
        assert breadth == pytest.approx(100.0)  # only A counted

    def test_no_eligible_tickers_returns_none(self):
        prices = {"SHORT": {"data": _price_rows([100.0, 101.0])}}
        breadth, excluded = compute_breadth(prices)
        assert breadth is None
        assert excluded == ["SHORT"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest investment_screener/backend/tests/py_services/test_market_regime.py -v`
Expected: FAIL with `ImportError: cannot import name '_load_active_tickers'`

- [ ] **Step 3: Write minimal implementation**

Add to `market_regime.py` (below the classifiers from Task 1, above `main()`):

```python
def _load_active_tickers(target_portfolio_path: Path) -> list[str]:
    """Read target-portfolio.json and return active-holding tickers.

    Active = role not in INACTIVE_ROLES ({"exit", "avoid"}) — the real role
    enum values validated by update_thesis.py. Not portfolio_io.load_portfolio_state():
    that loader reads portfolio.json (broker shares/prices) and has no role field.

    Args:
        target_portfolio_path: Path to target-portfolio.json.

    Returns:
        List of ticker strings (uses the "ticker" key, never "symbol" —
        CLAUDE.md rule 10).
    """
    data = json.loads(Path(target_portfolio_path).read_text())
    return [
        h["ticker"] for h in data.get("holdings", [])
        if h.get("role") not in INACTIVE_ROLES
    ]


def _sma(closes: pd.Series, period: int) -> pd.Series:
    """Simple moving average, full series (not just the latest value).

    Args:
        closes: Close prices, oldest first.
        period: SMA window length.

    Returns:
        A pandas Series of the same length as `closes`, with NaN for the
        first `period - 1` bars (insufficient data to seed the average).
    """
    return closes.rolling(window=period).mean()


def compute_breadth(prices_by_ticker: dict[str, dict]) -> tuple[float | None, list[str]]:
    """% of tickers whose latest close is above their own 200d SMA.

    Args:
        prices_by_ticker: market_data.get_prices() output, {ticker: {"data": [...]}}.

    Returns:
        (breadth_pct, excluded_tickers) — breadth_pct is None if no ticker
        has enough history (200+ rows) to compute a 200d SMA. Excluded
        tickers are never zero-filled into the denominator.
    """
    above = 0
    eligible = 0
    excluded: list[str] = []
    for ticker, payload in prices_by_ticker.items():
        rows = payload.get("data", [])
        if len(rows) < 200:
            excluded.append(ticker)
            continue
        closes = pd.DataFrame(rows)["close"]
        sma200 = _sma(closes, 200).iloc[-1]
        eligible += 1
        if closes.iloc[-1] > sma200:
            above += 1

    if eligible == 0:
        return None, excluded
    return round(above / eligible * 100, 2), excluded
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest investment_screener/backend/tests/py_services/test_market_regime.py -v`
Expected: PASS (all tests from Task 1 + 8 new tests)

- [ ] **Step 5: Commit**

```bash
git add investment_screener/backend/py_services/market_regime.py investment_screener/backend/tests/py_services/test_market_regime.py
git commit -m "feat: add active-ticker loader and breadth computation (C2 task 2)"
```

---

## Task 3: Per-ticker trend classifier

**Files:**
- Modify: `investment_screener/backend/py_services/market_regime.py`
- Test: `investment_screener/backend/tests/py_services/test_market_regime.py`

**Interfaces:**
- Consumes: `_sma()` (Task 2)
- Produces: `classify_ticker_trend(closes: pd.Series) -> dict[str, str] | None`

- [ ] **Step 1: Write the failing tests**

Append to `test_market_regime.py`:

```python
from market_regime import classify_ticker_trend  # noqa: E402


class TestClassifyTickerTrend:
    def test_monotonically_rising_series_is_uptrend(self):
        closes = pd.Series([float(c) for c in range(1, 231)])  # 230 days, steadily up
        result = classify_ticker_trend(closes)
        assert result == {"position": "ABOVE", "slope": "RISING", "state": "UPTREND"}

    def test_monotonically_falling_series_is_downtrend(self):
        closes = pd.Series([float(c) for c in range(230, 0, -1)])
        result = classify_ticker_trend(closes)
        assert result == {"position": "BELOW", "slope": "FALLING", "state": "DOWNTREND"}

    def test_above_sma_but_falling_slope_is_weakening(self):
        # Rise for 210 days to build an ABOVE position, then a recent downturn
        # in the SMA's own slope while price is still above the (now-falling) SMA.
        rising = [float(c) for c in range(1, 211)]
        recent_pullback_but_still_above = [210.0 - 0.05 * i for i in range(1, 21)]
        closes = pd.Series(rising + recent_pullback_but_still_above)
        result = classify_ticker_trend(closes)
        assert result["slope"] == "FALLING"

    def test_insufficient_history_returns_none(self):
        closes = pd.Series([100.0, 101.0, 99.0])
        assert classify_ticker_trend(closes) is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest investment_screener/backend/tests/py_services/test_market_regime.py -v`
Expected: FAIL with `ImportError: cannot import name 'classify_ticker_trend'`

- [ ] **Step 3: Write minimal implementation**

Add to `market_regime.py`:

```python
def classify_ticker_trend(closes: pd.Series) -> dict[str, str] | None:
    """Classify a ticker's trend: position vs. its 200d SMA, and that SMA's
    own rising/falling slope over the trailing 20 days.

    Combines into 4 states: UPTREND (above + rising), DOWNTREND (below +
    falling), WEAKENING (above + falling — losing momentum but not yet
    broken down), BASING (below + rising — recovering but not yet reclaimed).

    Args:
        closes: Close prices, oldest first.

    Returns:
        {"position": "ABOVE"|"BELOW", "slope": "RISING"|"FALLING",
        "state": "UPTREND"|"DOWNTREND"|"WEAKENING"|"BASING"}, or None if
        fewer than 220 bars (200 for the SMA + 20 for the slope lookback).
    """
    if len(closes) < 220:
        return None

    sma200 = _sma(closes, 200)
    position = "ABOVE" if closes.iloc[-1] > sma200.iloc[-1] else "BELOW"
    slope = "RISING" if sma200.iloc[-1] > sma200.iloc[-21] else "FALLING"

    state = {
        ("ABOVE", "RISING"): "UPTREND",
        ("ABOVE", "FALLING"): "WEAKENING",
        ("BELOW", "RISING"): "BASING",
        ("BELOW", "FALLING"): "DOWNTREND",
    }[(position, slope)]

    return {"position": position, "slope": slope, "state": state}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest investment_screener/backend/tests/py_services/test_market_regime.py -v`
Expected: PASS (all prior tests + 4 new tests)

- [ ] **Step 5: Commit**

```bash
git add investment_screener/backend/py_services/market_regime.py investment_screener/backend/tests/py_services/test_market_regime.py
git commit -m "feat: add per-ticker trend classifier (C2 task 3)"
```

---

## Task 4: Momentum percentile

**Files:**
- Modify: `investment_screener/backend/py_services/market_regime.py`
- Test: `investment_screener/backend/tests/py_services/test_market_regime.py`

**Interfaces:**
- Produces: `compute_momentum_percentile(closes: pd.Series) -> float | None`

- [ ] **Step 1: Write the failing tests**

Append to `test_market_regime.py`:

```python
from market_regime import compute_momentum_percentile  # noqa: E402


class TestComputeMomentumPercentile:
    def test_insufficient_history_returns_none(self):
        closes = pd.Series([100.0] * 200)  # need 252+21+1 = 274 minimum
        assert compute_momentum_percentile(closes) is None

    def test_strongest_recent_momentum_is_100th_percentile(self):
        # A steadily accelerating series: the most recent 12-1M momentum
        # reading is the largest the series has ever produced.
        closes = pd.Series([100.0 * (1.001 ** i) ** 1.02 for i in range(300)])
        result = compute_momentum_percentile(closes)
        assert result == pytest.approx(100.0)

    def test_flat_series_momentum_percentile_is_defined(self):
        closes = pd.Series([100.0] * 300)
        result = compute_momentum_percentile(closes)
        assert result is not None
        assert 0.0 <= result <= 100.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest investment_screener/backend/tests/py_services/test_market_regime.py -v`
Expected: FAIL with `ImportError: cannot import name 'compute_momentum_percentile'`

- [ ] **Step 3: Write minimal implementation**

Add to `market_regime.py`:

```python
def compute_momentum_percentile(closes: pd.Series) -> float | None:
    """12-1 month momentum (skip the most recent month, standard momentum
    convention), ranked as a percentile against that same metric computed at
    every trading day in the ticker's own history.

    momentum_t = close[t-21] / close[t-252] - 1, for every t where both
    indices exist. The current (last) momentum reading is ranked against
    the full historical distribution of that same rolling metric — i.e.
    "is today's 12-1M return stronger than X% of this ticker's own past
    12-1M readings."

    Args:
        closes: Close prices, oldest first.

    Returns:
        Percentile (0-100) of the latest momentum reading vs. its own
        history, or None if fewer than 274 bars (252 + 21 + 1) are
        available to compute at least one momentum value.
    """
    if len(closes) < 252 + 21 + 1:
        return None

    momentum = closes.shift(21) / closes.shift(252) - 1
    momentum = momentum.dropna()
    if momentum.empty:
        return None

    current = momentum.iloc[-1]
    percentile = (momentum <= current).sum() / len(momentum) * 100
    return round(float(percentile), 2)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest investment_screener/backend/tests/py_services/test_market_regime.py -v`
Expected: PASS (all prior tests + 3 new tests)

- [ ] **Step 5: Commit**

```bash
git add investment_screener/backend/py_services/market_regime.py investment_screener/backend/tests/py_services/test_market_regime.py
git commit -m "feat: add per-ticker momentum percentile (C2 task 4)"
```

---

## Task 5: Volatility percentile (reuses technicals.py's ATR internals)

**Files:**
- Modify: `investment_screener/backend/py_services/market_regime.py`
- Test: `investment_screener/backend/tests/py_services/test_market_regime.py`

**Interfaces:**
- Consumes: `technicals._true_range(highs, lows, closes) -> pd.Series`,
  `technicals._wilder_smooth(series, period) -> pd.Series` (both pre-existing,
  imported not duplicated)
- Produces: `compute_volatility_percentile(highs: pd.Series, lows: pd.Series, closes: pd.Series) -> float | None`

- [ ] **Step 1: Write the failing tests**

Append to `test_market_regime.py`:

```python
from market_regime import compute_volatility_percentile  # noqa: E402


def _ohlc(n: int, base: float = 100.0, spread: float = 1.0) -> tuple[pd.Series, pd.Series, pd.Series]:
    closes = pd.Series([base] * n)
    highs = closes + spread
    lows = closes - spread
    return highs, lows, closes


class TestComputeVolatilityPercentile:
    def test_insufficient_history_returns_none(self):
        highs, lows, closes = _ohlc(10)
        assert compute_volatility_percentile(highs, lows, closes) is None

    def test_constant_range_percentile_is_defined(self):
        highs, lows, closes = _ohlc(60)
        result = compute_volatility_percentile(highs, lows, closes)
        assert result is not None
        assert 0.0 <= result <= 100.0

    def test_recent_spike_ranks_high_percentile(self):
        highs, lows, closes = _ohlc(60, spread=1.0)
        # Blow out the range on the most recent 5 bars only.
        highs.iloc[-5:] = closes.iloc[-5:] + 10.0
        lows.iloc[-5:] = closes.iloc[-5:] - 10.0
        result = compute_volatility_percentile(highs, lows, closes)
        assert result >= 90.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest investment_screener/backend/tests/py_services/test_market_regime.py -v`
Expected: FAIL with `ImportError: cannot import name 'compute_volatility_percentile'`

- [ ] **Step 3: Write minimal implementation**

Add near the top of `market_regime.py`, alongside the other imports:

```python
from technicals import _true_range, _wilder_smooth  # noqa: E402
```

Add the function to `market_regime.py`:

```python
def compute_volatility_percentile(
    highs: pd.Series, lows: pd.Series, closes: pd.Series, period: int = 14
) -> float | None:
    """ATR% (ATR / close) at every day in the supplied history, current
    value ranked as a percentile against that same-ticker history.

    technicals.py's compute_atr() only returns the latest scalar value, so
    this reuses its internal _true_range/_wilder_smooth series helpers
    directly (not duplicated) to build the full ATR series first.

    Args:
        highs: High prices, oldest first.
        lows: Low prices, oldest first.
        closes: Close prices, oldest first.
        period: ATR lookback period, default 14 (matches technicals.py).

    Returns:
        Percentile (0-100) of the latest ATR% reading vs. its own history,
        or None if fewer than period+2 bars are available.
    """
    if len(closes) < period + 2:
        return None

    tr = _true_range(highs, lows, closes).dropna()
    atr_series = _wilder_smooth(tr, period).dropna()
    if atr_series.empty:
        return None

    atr_pct = atr_series / closes.loc[atr_series.index]
    current = atr_pct.iloc[-1]
    percentile = (atr_pct <= current).sum() / len(atr_pct) * 100
    return round(float(percentile), 2)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest investment_screener/backend/tests/py_services/test_market_regime.py -v`
Expected: PASS (all prior tests + 3 new tests)

- [ ] **Step 5: Commit**

```bash
git add investment_screener/backend/py_services/market_regime.py investment_screener/backend/tests/py_services/test_market_regime.py
git commit -m "feat: add per-ticker volatility percentile (C2 task 5)"
```

---

## Task 6: Orchestrator, CLI, and integration test

**Files:**
- Modify: `investment_screener/backend/py_services/market_regime.py`
- Test: `investment_screener/backend/tests/py_services/test_market_regime.py`

**Interfaces:**
- Consumes: everything from Tasks 1-5, plus `market_data.get_prices()` and
  `macro_regime.get_macro_regime()` / `_classify_vix` / `_classify_spy` /
  `_classify_credit` (all pre-existing)
- Produces: `compute_market_regime(target_portfolio_path: Path = TARGET_PATH) -> dict[str, Any]`

This task also replaces the placeholder `main()` from Task 1.

- [ ] **Step 1: Write the failing integration test**

Append to `test_market_regime.py`:

```python
from unittest.mock import patch

from market_regime import compute_market_regime  # noqa: E402


FIXTURE_TARGET = {
    "holdings": [
        {"ticker": "NVDA", "role": "accumulate"},
        {"ticker": "PANW", "role": "maintain"},
        {"ticker": "CBRS", "role": "watchlist"},
        {"ticker": "OLD", "role": "exit"},
    ]
}


def _fixture_prices(n: int, base: float, spread: float = 1.0) -> dict:
    closes = [base + i * 0.05 for i in range(n)]
    return {
        "data": [
            {"date": f"2024-{1 + i // 28:02d}-{1 + i % 28:02d}",
             "open": c, "high": c + spread, "low": c - spread, "close": c,
             "volume": 1000.0}
            for i, c in enumerate(closes)
        ]
    }


class TestComputeMarketRegime:
    def test_full_snapshot_shape(self, tmp_path):
        target_path = tmp_path / "target-portfolio.json"
        target_path.write_text(json.dumps(FIXTURE_TARGET))

        macro_result = type("M", (), {
            "regime": "RISK-ON", "score": 2, "vix": 14.0, "vix_signal": "LOW",
            "spy_vs_200d": 3.0, "spy_signal": "ABOVE", "hyg_lqd_ratio": 0.64,
            "credit_signal": "HEALTHY", "details": [], "degraded": False,
        })()

        def fake_get_prices(tickers, period, interval="1d"):
            result = {}
            for t in tickers:
                if t == "CBRS":
                    result[t] = {"data": _fixture_prices(30, base=100.0)["data"]}
                else:
                    result[t] = _fixture_prices(300, base=100.0)
            return result

        with patch("market_regime.get_macro_regime", return_value=macro_result), \
             patch("market_regime.get_prices", side_effect=fake_get_prices), \
             patch("market_regime._fetch_ratio", return_value=1.05), \
             patch("market_regime._fetch_dxy_vs_200d", return_value=3.0):
            result = compute_market_regime(target_portfolio_path=target_path)

        assert result["regime"] in {"RISK_ON", "NEUTRAL", "RISK_OFF", "STRESS"}
        assert "signals" in result
        assert set(result["signals"].keys()) == {
            "vix", "spy200d", "credit", "termSlope", "breadth", "dxy",
        }
        tickers_seen = {t["ticker"] for t in result["tickerRegimes"]}
        assert tickers_seen == {"NVDA", "PANW", "CBRS"}
        cbrs = next(t for t in result["tickerRegimes"] if t["ticker"] == "CBRS")
        assert cbrs["trend"] is None  # insufficient history
        assert any("CBRS" in w for w in result["warnings"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest investment_screener/backend/tests/py_services/test_market_regime.py::TestComputeMarketRegime -v`
Expected: FAIL with `ImportError: cannot import name 'compute_market_regime'`

- [ ] **Step 3: Write minimal implementation**

Replace `market_regime.py`'s imports section and `main()` with the following (keep
everything from Tasks 1-5 in between, unchanged):

```python
import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd
import yfinance as yf

sys.path.insert(0, str(Path(__file__).resolve().parent))

from market_data import get_prices  # noqa: E402
from macro_regime import (  # noqa: E402
    get_macro_regime, _classify_vix, _classify_spy, _classify_credit,
)
from technicals import _true_range, _wilder_smooth  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = REPO_ROOT / "investment_screener/backend/data"
TARGET_PATH = DATA_DIR / "theses/target-portfolio.json"
MARKET_REGIME_PATH = DATA_DIR / "market_regime.json"

INACTIVE_ROLES = {"exit", "avoid"}
```

(This moves `get_prices`/`get_macro_regime`/`_true_range`/`_wilder_smooth` imports to
the top of the file where Tasks 1-5's code already expects them at module scope —
Task 5 added the `technicals` import inline; Task 6 consolidates all imports to the
top in one place. Delete the Task-5-inline `from technicals import ...` line since
it's now redundant with the top-of-file import above.)

Add two small fetch helpers and the orchestrator, replacing the old placeholder `main()`:

```python
def _fetch_ratio(numerator: str, denominator: str) -> float | None:
    """Fetch two tickers' latest closes and return numerator/denominator.

    Used for the IEF/SHY term-slope proxy — same ETF-ratio-via-yfinance
    pattern as macro_regime.py's HYG/LQD credit signal.

    Args:
        numerator: Ticker whose close is the ratio's numerator.
        denominator: Ticker whose close is the ratio's denominator.

    Returns:
        The ratio, or None if either fetch fails.
    """
    try:
        num_close = float(yf.Ticker(numerator).history(period="5d")["Close"].to_numpy()[-1])
        den_close = float(yf.Ticker(denominator).history(period="5d")["Close"].to_numpy()[-1])
        return num_close / den_close if den_close > 0 else None
    except Exception:
        return None


def _fetch_dxy_vs_200d(ticker: str = "UUP") -> float | None:
    """Fetch UUP's % distance above/below its own 200D SMA.

    Same pattern as macro_regime.py's SPY-vs-200d signal.

    Args:
        ticker: USD-strength proxy ETF ticker, default UUP.

    Returns:
        Percentage above (positive) or below (negative) the 200D SMA, or
        None if the fetch fails.
    """
    try:
        hist = yf.Ticker(ticker).history(period="1y")
        close = float(hist["Close"].to_numpy()[-1])
        sma_200 = float(hist["Close"].tail(200).mean().item())
        return (close - sma_200) / sma_200 * 100
    except Exception:
        return None


def compute_market_regime(target_portfolio_path: Path = TARGET_PATH) -> dict[str, Any]:
    """Primary orchestrator — 4-tier composite regime + per-ticker regime layer.

    Reuses macro_regime.get_macro_regime() for 3 of the 6 macro signals,
    fetches the 3 new ones (term-slope, breadth, DXY), classifies the
    composite regime, then classifies trend/momentum/volatility for every
    active holding. Does not write to disk itself — see main() for the
    CLI's --no-save-gated write, same convention as risk_engine.py's
    compute_risk_snapshot().

    Args:
        target_portfolio_path: Path to target-portfolio.json.

    Returns:
        Full market regime snapshot dict — see docs/superpowers/specs/
        2026-07-06-market-regime-classifier-design.md for the field-by-field shape.
    """
    macro = get_macro_regime()
    tickers = _load_active_tickers(target_portfolio_path)
    prices = get_prices(tickers, period="2y", interval="1d") if tickers else {}

    warnings: list[str] = []

    breadth_pct, breadth_excluded = compute_breadth(prices)
    for t in breadth_excluded:
        warnings.append(f"{t} excluded from breadth/trend: insufficient price history")

    term_slope_ratio = _fetch_ratio("IEF", "SHY")
    dxy_pct = _fetch_dxy_vs_200d()

    score = 0
    unavailable = 0
    signals: dict[str, Any] = {}

    # Re-invoke macro_regime.py's own classifiers on its raw values rather than
    # duplicating a second copy of their point tables — if macro_regime.py's
    # thresholds ever change, this stays in sync automatically. macro.vix_signal
    # (etc.) is still used for the UNAVAILABLE check, since a failed fetch
    # leaves the raw value at its harmless default (e.g. vix=20.0) rather than
    # None, and classifying that default would silently look like real data.
    if macro.vix_signal == "UNAVAILABLE":
        unavailable += 1
    else:
        _, vix_pts = _classify_vix(macro.vix)
        score += vix_pts
    if macro.spy_signal == "UNAVAILABLE":
        unavailable += 1
    else:
        _, spy_pts = _classify_spy(macro.spy_vs_200d)
        score += spy_pts
    if macro.credit_signal == "UNAVAILABLE":
        unavailable += 1
    else:
        _, credit_pts = _classify_credit(macro.hyg_lqd_ratio)
        score += credit_pts

    signals["vix"] = {"value": macro.vix, "signal": macro.vix_signal}
    signals["spy200d"] = {"value": macro.spy_vs_200d, "signal": macro.spy_signal}
    signals["credit"] = {"value": macro.hyg_lqd_ratio, "signal": macro.credit_signal}

    if term_slope_ratio is None:
        signals["termSlope"] = {"value": None, "signal": "UNAVAILABLE"}
        unavailable += 1
    else:
        term_signal, term_pts = _classify_term_slope(term_slope_ratio)
        signals["termSlope"] = {"value": round(term_slope_ratio, 4), "signal": term_signal}
        score += term_pts

    if breadth_pct is None:
        signals["breadth"] = {"value": None, "signal": "UNAVAILABLE"}
        unavailable += 1
    else:
        breadth_signal, breadth_pts = _classify_breadth(breadth_pct)
        signals["breadth"] = {"value": breadth_pct, "signal": breadth_signal}
        score += breadth_pts

    if dxy_pct is None:
        signals["dxy"] = {"value": None, "signal": "UNAVAILABLE"}
        unavailable += 1
    else:
        dxy_signal, dxy_pts = _classify_dxy(dxy_pct)
        signals["dxy"] = {"value": round(dxy_pct, 2), "signal": dxy_signal}
        score += dxy_pts

    regime, degraded = _classify_regime_v2(score, unavailable)

    ticker_regimes: list[dict[str, Any]] = []
    for ticker in tickers:
        rows = prices.get(ticker, {}).get("data", [])
        if not rows:
            ticker_regimes.append({
                "ticker": ticker, "trend": None,
                "momentumPercentile": None, "volatilityPercentile": None,
            })
            continue
        df = pd.DataFrame(rows)
        ticker_regimes.append({
            "ticker": ticker,
            "trend": classify_ticker_trend(df["close"]),
            "momentumPercentile": compute_momentum_percentile(df["close"]),
            "volatilityPercentile": compute_volatility_percentile(
                df["high"], df["low"], df["close"]
            ),
        })

    return {
        "asOf": date.today().isoformat(),
        "regime": regime,
        "score": score,
        "degraded": degraded,
        "signals": signals,
        "tickerRegimes": ticker_regimes,
        "warnings": warnings,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Market regime classifier")
    parser.add_argument("--pretty", action="store_true")
    parser.add_argument("--no-save", action="store_true", help="Print only, skip writing market_regime.json")
    args = parser.parse_args()

    snapshot = compute_market_regime()
    if not args.no_save:
        MARKET_REGIME_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(MARKET_REGIME_PATH, "w") as f:
            json.dump(snapshot, f, indent=2)

    print(json.dumps(snapshot, indent=2 if args.pretty else None))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run all tests to verify they pass**

Run: `python3 -m pytest investment_screener/backend/tests/py_services/test_market_regime.py -v`
Expected: PASS (all tests from Tasks 1-6)

- [ ] **Step 5: Manual smoke test against live data**

Run: `python3 investment_screener/backend/py_services/market_regime.py --no-save --pretty`
Expected: prints a full JSON snapshot with a `regime` field and non-empty
`tickerRegimes` for the current active holdings, no traceback.

- [ ] **Step 6: Commit**

```bash
git add investment_screener/backend/py_services/market_regime.py investment_screener/backend/tests/py_services/test_market_regime.py
git commit -m "feat: add market_regime.py orchestrator, CLI, and integration test (C2 task 6)"
```

---

## Task 7: Wire into `/daily`'s morning brief (additive)

**Files:**
- Modify: `plugins/portfolio-advisor/scripts/daily_brief.py:170-300` (import block,
  `run()` pipeline, `brief` dict assembly)
- Modify: `plugins/portfolio-advisor/scripts/daily_brief.py:341-348` (`render()`'s
  MACRO print block)
- Test: manual verification only (`daily_brief.py` has no existing unit test suite —
  same as E1's wiring task, which also verified manually via `--skip-ta` smoke run)

**Interfaces:**
- Consumes: `market_regime.compute_market_regime() -> dict[str, Any]` (Task 6)
- Produces: `brief["market_regime"]` in the JSON snapshot; a `REGIME:` line replacing
  the old `MACRO:` line in the rendered terminal output

**Critical constraint:** `brief_recommendations.build_recommendations()` gates
ACCUMULATE signals on `macro.get("regime") == "RISK-OFF"` (hyphenated) — this call
and its input **must not change**. `market_regime.py`'s output is purely additive
alongside it.

- [ ] **Step 1: Add the import and orchestrator call**

In `plugins/portfolio-advisor/scripts/daily_brief.py`, find this block (around line 173):

```python
    from macro_regime import get_macro_regime
    from risk_engine import compute_risk_snapshot
```

Change it to:

```python
    from macro_regime import get_macro_regime
    from market_regime import compute_market_regime
    from risk_engine import compute_risk_snapshot
```

Find this block (around line 187-197):

```python
    # ── 1. Macro regime ───────────────────────────────────────────────────────
    print("▶ Macro regime...", file=sys.stderr)
    macro = get_macro_regime()

    # ── 1b. Portfolio risk snapshot ───────────────────────────────────────────
```

Change it to:

```python
    # ── 1. Macro regime ───────────────────────────────────────────────────────
    print("▶ Macro regime...", file=sys.stderr)
    macro = get_macro_regime()

    # ── 1a. Market regime (additive — does not feed the RISK-OFF gate above) ──
    print("▶ Market regime...", file=sys.stderr)
    try:
        market_regime = compute_market_regime()
    except Exception as exc:
        print(f"  Market regime skipped: {exc}", file=sys.stderr)
        market_regime = None

    # ── 1b. Portfolio risk snapshot ───────────────────────────────────────────
```

- [ ] **Step 2: Attach to the brief dict**

Find this block (around line 278-294):

```python
    brief: dict[str, Any] = {
        "overnight_gaps": gaps,
        "date": date.today().isoformat(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "macro_regime": asdict(macro),
        "risk_snapshot": risk_snapshot,
```

Change it to:

```python
    brief: dict[str, Any] = {
        "overnight_gaps": gaps,
        "date": date.today().isoformat(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "macro_regime": asdict(macro),
        "market_regime": market_regime,
        "risk_snapshot": risk_snapshot,
```

- [ ] **Step 3: Replace the MACRO render line with REGIME**

Find this block (around line 341-348):

```python
    # ── Macro ─────────────────────────────────────────────────────────────────
    regime = macro["regime"]
    icon   = {"RISK-ON": "✅", "NEUTRAL": "⚠️", "RISK-OFF": "🔴"}.get(regime, "")
    lines.append(f"\n{icon}  MACRO REGIME: {regime}  (score={macro['score']})")
    for d in macro["details"]:
        lines.append(f"    {d}")
    if regime == "RISK-OFF":
        lines.append("    ⛔  Gate all ACCUMULATE signals. Execute only REDUCE / EXIT today.")
```

Change it to:

```python
    # ── Macro (unchanged — still feeds the RISK-OFF ACCUMULATE gate) ──────────
    macro_regime_label = macro["regime"]
    if macro_regime_label == "RISK-OFF":
        lines.append("\n⛔  MACRO GATE: RISK-OFF — ACCUMULATE signals blocked today.")

    # ── Market regime (new, C2 — additive, informational only) ────────────────
    mr = brief.get("market_regime")
    if mr:
        icon = {"RISK_ON": "✅", "NEUTRAL": "⚠️", "RISK_OFF": "🔴", "STRESS": "🆘"}.get(mr["regime"], "")
        breadth = mr["signals"].get("breadth", {}).get("value")
        term_slope = mr["signals"].get("termSlope", {}).get("value")
        breadth_str = f"{breadth:.0f}%" if breadth is not None else "n/a"
        term_str = f"{term_slope:+.2f}" if term_slope is not None else "n/a"
        lines.append(
            f"\n{icon}  REGIME: {mr['regime']} · breadth {breadth_str} · "
            f"term-slope {term_str} · degraded: {'yes' if mr['degraded'] else 'no'}"
        )
    else:
        lines.append("\n⚠️  REGIME: unavailable (market_regime.py failed — see stderr)")
```

- [ ] **Step 4: Manual smoke test**

Run: `python3 plugins/portfolio-advisor/scripts/daily_brief.py --skip-ta`

Expected: the terminal output shows a `REGIME:` line (new) and, only if the macro
gate is RISK-OFF, a `MACRO GATE: RISK-OFF` line — no traceback, and the run
completes. Confirm `brief["market_regime"]` is present in the day's saved snapshot
under `investment_screener/backend/data/daily_briefs/<today>.json`.

- [ ] **Step 5: Commit**

```bash
git add plugins/portfolio-advisor/scripts/daily_brief.py
git commit -m "feat: wire market_regime.py into /daily brief additively (C2 task 7)"
```

---

## Post-implementation: whole-branch review

Once all 7 tasks are committed in the feature worktree, run a whole-branch review
(same pattern as E1/Phase 2a/Phase 2b) before merging to local `main`. Pay particular
attention to:

- The additive (not replacing) gate wiring in Task 7 — confirm
  `brief_recommendations.build_recommendations()`'s call site truly received no
  changes to its `macro` argument.
- `_load_active_tickers` role filtering — confirm `INACTIVE_ROLES = {"exit", "avoid"}`
  matches the real enum values currently in `target-portfolio.json` (72 holdings,
  6 role values as of this writing).
- Per-ticker exclusion paths (`breadth_excluded`, `trend`/`momentum`/`volatility`
  each independently returning `None` on insufficient history) never crash
  `compute_market_regime()` end-to-end for a mixed fresh/short-history portfolio.

After merge to local `main`, push `feature/fable5-phase3-c2-market-regime` to
`origin` as a backup/PR source — same "Claude never merges into `origin/main`"
policy as every prior phase (see `start_here.md`'s Git policy section).
