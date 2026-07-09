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


from thesis_breakers import evaluate_breakers  # noqa: E402


def _target_data_one_auto_breaker(horizon: int = 5) -> dict:
    return {
        "holdings": [
            {
                "ticker": "NBIS",
                "subStrategyId": "asi_race",
                "targetWeight": 5.5,
                "thesisBreakers": [
                    {
                        "id": "nbis-trend-breakdown",
                        "type": "auto",
                        "metric": "trendState",
                        "operator": "in",
                        "threshold": ["DOWNTREND"],
                        "horizon": horizon,
                        "note": "Sustained downtrend contradicts the thesis",
                    }
                ],
            }
        ]
    }


def _regime_with_trend(state: str) -> dict:
    return {"tickerRegimes": [
        {"ticker": "NBIS", "trend": {"position": "BELOW", "slope": "FALLING", "state": state},
         "momentumPercentile": 10.0, "volatilityPercentile": 80.0},
    ]}


class TestEvaluateBreakersAutoStreak:
    def test_first_true_evaluation_starts_streak_at_one_and_watching(self):
        result = evaluate_breakers(
            _target_data_one_auto_breaker(horizon=5), [], _regime_with_trend("DOWNTREND"),
            [], prev_state={}, today="2026-07-09",
        )
        entry = result["NBIS"]["nbis-trend-breakdown"]
        assert entry["currentStreak"] == 1
        assert entry["conditionMet"] is True
        assert entry["status"] == "WATCHING"
        assert entry["streakStartDate"] == "2026-07-09"
        assert entry["currentValue"] == "DOWNTREND"

    def test_streak_increments_across_runs(self):
        prev_state = {"NBIS": {"nbis-trend-breakdown": {
            "type": "auto", "currentValue": "DOWNTREND", "conditionMet": True,
            "currentStreak": 3, "streakStartDate": "2026-07-05",
            "lastEvaluatedAt": "2026-07-08T13:00:00Z", "status": "WATCHING",
        }}}
        result = evaluate_breakers(
            _target_data_one_auto_breaker(horizon=5), [], _regime_with_trend("DOWNTREND"),
            [], prev_state=prev_state, today="2026-07-09",
        )
        entry = result["NBIS"]["nbis-trend-breakdown"]
        assert entry["currentStreak"] == 4
        assert entry["streakStartDate"] == "2026-07-05"
        assert entry["status"] == "WATCHING"

    def test_streak_reaches_horizon_becomes_triggered(self):
        prev_state = {"NBIS": {"nbis-trend-breakdown": {
            "type": "auto", "currentValue": "DOWNTREND", "conditionMet": True,
            "currentStreak": 4, "streakStartDate": "2026-07-05",
            "lastEvaluatedAt": "2026-07-08T13:00:00Z", "status": "WATCHING",
        }}}
        result = evaluate_breakers(
            _target_data_one_auto_breaker(horizon=5), [], _regime_with_trend("DOWNTREND"),
            [], prev_state=prev_state, today="2026-07-09",
        )
        entry = result["NBIS"]["nbis-trend-breakdown"]
        assert entry["currentStreak"] == 5
        assert entry["status"] == "TRIGGERED"

    def test_condition_false_resets_streak_to_zero(self):
        prev_state = {"NBIS": {"nbis-trend-breakdown": {
            "type": "auto", "currentValue": "DOWNTREND", "conditionMet": True,
            "currentStreak": 4, "streakStartDate": "2026-07-05",
            "lastEvaluatedAt": "2026-07-08T13:00:00Z", "status": "WATCHING",
        }}}
        result = evaluate_breakers(
            _target_data_one_auto_breaker(horizon=5), [], _regime_with_trend("UPTREND"),
            [], prev_state=prev_state, today="2026-07-09",
        )
        entry = result["NBIS"]["nbis-trend-breakdown"]
        assert entry["currentStreak"] == 0
        assert entry["conditionMet"] is False
        assert entry["status"] == "OK"
        assert entry["streakStartDate"] is None

    def test_unresolvable_metric_never_crashes_and_counts_as_not_met(self):
        result = evaluate_breakers(
            _target_data_one_auto_breaker(horizon=5), [], None,
            [], prev_state={}, today="2026-07-09",
        )
        entry = result["NBIS"]["nbis-trend-breakdown"]
        assert entry["conditionMet"] is False
        assert entry["currentStreak"] == 0


class TestEvaluateBreakersManualStaleness:
    def _target_data_one_manual_breaker(self, review_cadence_days: int = 90) -> dict:
        return {
            "holdings": [
                {
                    "ticker": "NBIS",
                    "subStrategyId": "asi_race",
                    "targetWeight": 5.5,
                    "thesisBreakers": [
                        {
                            "id": "nbis-ndr-floor",
                            "type": "manual",
                            "metric": "ndr",
                            "operator": "<",
                            "threshold": 115,
                            "horizon": "2 quarters",
                            "note": "NDR floor from 10-Q disclosures",
                            "status": "OK",
                            "statusSetAt": "2026-07-01",
                            "statusSetBy": "agent",
                            "reviewCadenceDays": review_cadence_days,
                        }
                    ],
                }
            ]
        }

    def test_manual_breaker_not_stale_within_cadence(self):
        result = evaluate_breakers(
            self._target_data_one_manual_breaker(review_cadence_days=90), [], None,
            [], prev_state={}, today="2026-07-09",
        )
        entry = result["NBIS"]["nbis-ndr-floor"]
        assert entry["daysSinceReview"] == 8
        assert entry["stale"] is False
        assert entry["status"] == "OK"

    def test_manual_breaker_stale_past_cadence(self):
        result = evaluate_breakers(
            self._target_data_one_manual_breaker(review_cadence_days=5), [], None,
            [], prev_state={}, today="2026-07-09",
        )
        entry = result["NBIS"]["nbis-ndr-floor"]
        assert entry["daysSinceReview"] == 8
        assert entry["stale"] is True

    def test_manual_breaker_status_passed_through_verbatim(self):
        target = self._target_data_one_manual_breaker()
        target["holdings"][0]["thesisBreakers"][0]["status"] = "TRIGGERED"
        result = evaluate_breakers(target, [], None, [], prev_state={}, today="2026-07-09")
        assert result["NBIS"]["nbis-ndr-floor"]["status"] == "TRIGGERED"


class TestEvaluateBreakersNoBreakers:
    def test_holding_with_no_thesis_breakers_produces_no_entries(self):
        target = {"holdings": [{"ticker": "MSFT", "targetWeight": 2.4}]}
        result = evaluate_breakers(target, [], None, [], prev_state={}, today="2026-07-09")
        assert result == {}
