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
