"""Tests for market_regime.py — 4-tier composite regime classifier (Phase 3, C2)."""
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
PY_SERVICES = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(PY_SERVICES))

from market_regime import (  # noqa: E402
    _classify_term_slope,
    _classify_breadth,
    _classify_dxy,
    _classify_regime_v2,
    _load_active_tickers,
    _sma,
    compute_breadth,
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
        # Build a pattern where SMA slope is falling while price is still above it:
        # Early base (high), middle drop (low), recent recovery (medium-high).
        # sma200[-21] sees mostly high base; sma200[-1] sees mix of drop + recovery.
        early_base = [110.0] * 20  # High base for sma200[-21]
        middle_base = [100.0] * 180  # Transition
        drop = [80.0] * 10  # Significant drop
        recovery = [105.0] * 20  # Recovery but still under the high base
        closes = pd.Series(early_base + middle_base + drop + recovery)
        result = classify_ticker_trend(closes)
        assert result["slope"] == "FALLING"

    def test_insufficient_history_returns_none(self):
        closes = pd.Series([100.0, 101.0, 99.0])
        assert classify_ticker_trend(closes) is None
