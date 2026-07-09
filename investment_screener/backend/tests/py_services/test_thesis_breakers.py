"""Tests for thesis_breakers.py — B5 structured thesis breaker evaluation."""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
PY_SERVICES = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(PY_SERVICES))

from thesis_breakers import (  # noqa: E402
    AUTO_METRICS,
    evaluate_condition,
    resolve_auto_metric_value,
)


class TestEvaluateCondition:
    def test_less_than_true(self):
        assert evaluate_condition(10, "<", 20) is True

    def test_less_than_false(self):
        assert evaluate_condition(20, "<", 20) is False

    def test_less_than_or_equal_boundary(self):
        assert evaluate_condition(20, "<=", 20) is True

    def test_greater_than_true(self):
        assert evaluate_condition(30, ">", 20) is True

    def test_greater_than_or_equal_boundary(self):
        assert evaluate_condition(20, ">=", 20) is True

    def test_equals(self):
        assert evaluate_condition("DOWNTREND", "==", "DOWNTREND") is True

    def test_in_list_match(self):
        assert evaluate_condition("DOWNTREND", "in", ["DOWNTREND", "WEAKENING"]) is True

    def test_in_list_no_match(self):
        assert evaluate_condition("UPTREND", "in", ["DOWNTREND", "WEAKENING"]) is False

    def test_none_value_never_meets_condition(self):
        assert evaluate_condition(None, "<", 20) is False

    def test_unknown_operator_raises(self):
        with pytest.raises(ValueError, match="Unknown operator"):
            evaluate_condition(10, "!=", 20)


class TestResolveAutoMetricValue:
    def _inputs(self):
        conviction_scores = [
            {"ticker": "NBIS", "rsi": 28.5, "pct_to_fv": -42.3},
            {"ticker": "PANW", "rsi": 55.0, "pct_to_fv": 12.0},
        ]
        market_regime = {
            "tickerRegimes": [
                {
                    "ticker": "NBIS",
                    "trend": {"position": "BELOW", "slope": "FALLING", "state": "DOWNTREND"},
                    "momentumPercentile": 8.5,
                    "volatilityPercentile": 91.0,
                },
                {"ticker": "PANW", "trend": None, "momentumPercentile": None,
                 "volatilityPercentile": None},
            ]
        }
        pillar_health = [
            {"pillar": "asi_race", "avg_score": -1.5, "count": 3, "min": -3, "max": 1},
        ]
        target_data = {
            "holdings": [
                {"ticker": "NBIS", "subStrategyId": "asi_race", "targetWeight": 5.5},
                {"ticker": "PANW", "subStrategyId": "cybersecurity", "targetWeight": 5.9},
            ]
        }
        return conviction_scores, market_regime, pillar_health, target_data

    def test_rsi_resolves_from_conviction_scores(self):
        scores, regime, pillars, target = self._inputs()
        assert resolve_auto_metric_value("rsi", "NBIS", scores, regime, pillars, target) == 28.5

    def test_dcf_fair_value_gap_resolves_from_pct_to_fv(self):
        scores, regime, pillars, target = self._inputs()
        assert resolve_auto_metric_value(
            "dcfFairValueGapPct", "NBIS", scores, regime, pillars, target
        ) == -42.3

    def test_trend_state_resolves_from_market_regime(self):
        scores, regime, pillars, target = self._inputs()
        assert resolve_auto_metric_value(
            "trendState", "NBIS", scores, regime, pillars, target
        ) == "DOWNTREND"

    def test_trend_state_none_when_trend_unavailable(self):
        scores, regime, pillars, target = self._inputs()
        assert resolve_auto_metric_value(
            "trendState", "PANW", scores, regime, pillars, target
        ) is None

    def test_momentum_percentile_resolves(self):
        scores, regime, pillars, target = self._inputs()
        assert resolve_auto_metric_value(
            "momentumPercentile", "NBIS", scores, regime, pillars, target
        ) == 8.5

    def test_pillar_avg_score_resolves_via_sub_strategy_id(self):
        scores, regime, pillars, target = self._inputs()
        assert resolve_auto_metric_value(
            "pillarAvgScore", "NBIS", scores, regime, pillars, target
        ) == -1.5

    def test_missing_ticker_in_conviction_scores_returns_none(self):
        scores, regime, pillars, target = self._inputs()
        assert resolve_auto_metric_value(
            "rsi", "UNKNOWN", scores, regime, pillars, target
        ) is None

    def test_market_regime_unavailable_returns_none(self):
        scores, _, pillars, target = self._inputs()
        assert resolve_auto_metric_value(
            "trendState", "NBIS", scores, None, pillars, target
        ) is None

    def test_unknown_metric_raises(self):
        scores, regime, pillars, target = self._inputs()
        with pytest.raises(ValueError, match="Unknown auto metric"):
            resolve_auto_metric_value("madeUpMetric", "NBIS", scores, regime, pillars, target)

    def test_auto_metrics_constant_has_five_entries(self):
        assert AUTO_METRICS == frozenset({
            "rsi", "dcfFairValueGapPct", "trendState", "momentumPercentile", "pillarAvgScore",
        })
