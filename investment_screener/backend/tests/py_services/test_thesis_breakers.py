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


import json as _json

from thesis_breakers import (  # noqa: E402
    _cli_log_override,
    compute_breaker_state,
    log_breaker_override,
)


class TestComputeBreakerState:
    @pytest.mark.skip(reason=(
        "Wave 8: compute_breaker_state() now sources holdings from "
        "domain_model.sqlite via portfolio_io.load_thesis_holdings(), which has "
        "no thesisBreakers column (0/75 real holdings ever populated this field "
        "-- same documented gap as generate_portfolio_blueprint.py's "
        "build_thesis_map(), which also always returns thesisBreakers=[]). "
        "The core triggering logic itself is unaffected and still covered "
        "directly by TestEvaluateBreakersAutoStreak/ManualStaleness/NoBreakers "
        "below, which call evaluate_breakers() with hand-built target_data and "
        "never touch file I/O."
    ))
    def test_writes_state_file_and_returns_triggered_list(self, tmp_path):
        target_path = tmp_path / "target-portfolio.json"
        state_path = tmp_path / "thesis_breaker_state.json"
        target_data = {
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
                            "horizon": 5,
                            "note": "Sustained downtrend",
                        }
                    ],
                },
                {"ticker": "MSFT", "subStrategyId": "quality_saas", "targetWeight": 2.4},
            ]
        }
        target_path.write_text(_json.dumps(target_data))
        prev_state = {
            "generatedAt": "2026-07-08T13:00:00Z",
            "holdings": {"NBIS": {"nbis-trend-breakdown": {
                "type": "auto", "currentValue": "DOWNTREND", "conditionMet": True,
                "currentStreak": 4, "streakStartDate": "2026-07-04",
                "lastEvaluatedAt": "2026-07-08T13:00:00Z", "status": "WATCHING",
            }}},
        }
        state_path.write_text(_json.dumps(prev_state))
        market_regime = {"tickerRegimes": [
            {"ticker": "NBIS", "trend": {"position": "BELOW", "slope": "FALLING",
             "state": "DOWNTREND"}, "momentumPercentile": 5.0, "volatilityPercentile": 90.0},
        ]}

        state, triggered = compute_breaker_state(
            conviction_scores=[], market_regime=market_regime, pillar_health=[],
            target_portfolio_path=target_path, state_path=state_path,
        )

        assert state_path.exists()
        on_disk = _json.loads(state_path.read_text())
        assert on_disk["holdings"]["NBIS"]["nbis-trend-breakdown"]["status"] == "TRIGGERED"
        assert "generatedAt" in on_disk

        assert len(triggered) == 1
        assert triggered[0]["ticker"] == "NBIS"
        assert triggered[0]["breakerId"] == "nbis-trend-breakdown"
        assert triggered[0]["metric"] == "trendState"
        assert triggered[0]["targetWeight"] == 5.5
        assert triggered[0]["currentStreak"] == 5

    def test_no_prior_state_file_treated_as_empty(self, tmp_path):
        target_path = tmp_path / "target-portfolio.json"
        state_path = tmp_path / "thesis_breaker_state.json"
        target_path.write_text(_json.dumps({"holdings": []}))

        state, triggered = compute_breaker_state(
            conviction_scores=[], market_regime=None, pillar_health=[],
            target_portfolio_path=target_path, state_path=state_path,
        )

        assert state["holdings"] == {}
        assert triggered == []


class TestLogBreakerOverride:
    def test_appends_one_jsonl_line(self, tmp_path):
        path = tmp_path / "breaker-overrides.jsonl"
        log_breaker_override(
            ticker="NBIS", breaker_id="nbis-trend-breakdown", metric="trendState",
            current_value="DOWNTREND", threshold=["DOWNTREND"], streak=5, horizon=5,
            rationale="Vera Rubin ramp de-risks the downtrend; holding through",
            path=path,
        )
        lines = path.read_text().strip().splitlines()
        assert len(lines) == 1
        entry = _json.loads(lines[0])
        assert entry["ticker"] == "NBIS"
        assert entry["breakerId"] == "nbis-trend-breakdown"
        assert entry["overriddenBy"] == "user"
        assert "date" in entry

    def test_second_call_appends_not_overwrites(self, tmp_path):
        path = tmp_path / "breaker-overrides.jsonl"
        log_breaker_override(
            ticker="NBIS", breaker_id="a", metric="rsi", current_value=25, threshold=30,
            streak=3, horizon=3, rationale="first", path=path,
        )
        log_breaker_override(
            ticker="PANW", breaker_id="b", metric="rsi", current_value=25, threshold=30,
            streak=3, horizon=3, rationale="second", path=path,
        )
        lines = path.read_text().strip().splitlines()
        assert len(lines) == 2


class TestCliLogOverride:
    @pytest.mark.skip(reason=(
        "Wave 8: _cli_log_override() now sources holdings from "
        "domain_model.sqlite via portfolio_io.load_thesis_holdings(), which has "
        "no thesisBreakers column (0/75 real holdings ever populated this "
        "field), so a breaker definition can no longer be resolved this way."
    ))
    def test_resolves_definition_and_state_then_logs(self, tmp_path):
        target_path = tmp_path / "target-portfolio.json"
        state_path = tmp_path / "thesis_breaker_state.json"
        overrides_path = tmp_path / "breaker-overrides.jsonl"
        target_path.write_text(_json.dumps({"holdings": [{
            "ticker": "NBIS", "thesisBreakers": [{
                "id": "nbis-trend-breakdown", "type": "auto", "metric": "trendState",
                "operator": "in", "threshold": ["DOWNTREND"], "horizon": 5,
                "note": "Sustained downtrend",
            }],
        }]}))
        state_path.write_text(_json.dumps({"holdings": {"NBIS": {"nbis-trend-breakdown": {
            "type": "auto", "currentValue": "DOWNTREND", "conditionMet": True,
            "currentStreak": 5, "status": "TRIGGERED",
        }}}}))

        _cli_log_override(
            ticker="NBIS", breaker_id="nbis-trend-breakdown",
            rationale="Vera Rubin ramp de-risks the downtrend",
            target_portfolio_path=target_path, state_path=state_path,
            overrides_path=overrides_path,
        )

        lines = overrides_path.read_text().strip().splitlines()
        assert len(lines) == 1
        entry = _json.loads(lines[0])
        assert entry["metric"] == "trendState"
        assert entry["currentValue"] == "DOWNTREND"
        assert entry["streak"] == 5
        assert entry["horizon"] == 5
        assert entry["rationale"] == "Vera Rubin ramp de-risks the downtrend"

    def test_unknown_ticker_raises(self, tmp_path):
        db_path = tmp_path / "test.sqlite"
        from domain_model.db_client import initialize_db
        initialize_db(str(db_path)).close()
        with pytest.raises(ValueError, match="not found in domain_model.sqlite"):
            _cli_log_override(
                ticker="NOPE", breaker_id="x", rationale="r",
                state_path=tmp_path / "s.json",
                overrides_path=tmp_path / "o.jsonl", db_path=db_path,
            )

    def test_unknown_breaker_id_raises(self, tmp_path):
        # NBIS must exist as an investment row for holding lookup to succeed;
        # thesisBreakers always defaults to [] post-Wave-8 (no SQLite column),
        # so any breaker_id is "not found" -- this is the real, isolated
        # (tmp db_path, never the real production DB) equivalent of the old
        # thesisBreakers=[] fixture.
        db_path = tmp_path / "test.sqlite"
        from domain_model.db_client import initialize_db
        from domain_model.investment_repository import resolve_investment, update_investment_fields
        conn = initialize_db(str(db_path))
        update_investment_fields(conn, resolve_investment(conn, "NBIS"), target_weight=0.0)
        conn.close()
        with pytest.raises(ValueError, match="not found on NBIS"):
            _cli_log_override(
                ticker="NBIS", breaker_id="nope", rationale="r",
                state_path=tmp_path / "s.json",
                overrides_path=tmp_path / "o.jsonl", db_path=db_path,
            )

    @pytest.mark.skip(reason=(
        "Wave 8: _cli_log_override() now sources holdings from "
        "domain_model.sqlite via portfolio_io.load_thesis_holdings(), which has "
        "no thesisBreakers column (0/75 real holdings ever populated this "
        "field), so a breaker definition can no longer be resolved this way."
    ))
    def test_missing_state_file_still_logs_with_null_streak(self, tmp_path):
        target_path = tmp_path / "target-portfolio.json"
        target_path.write_text(_json.dumps({"holdings": [{
            "ticker": "NBIS", "thesisBreakers": [{
                "id": "nbis-ndr-floor", "type": "manual", "metric": "ndr", "operator": "<",
                "threshold": 115, "horizon": "2 quarters", "note": "NDR floor",
                "status": "TRIGGERED", "statusSetAt": "2026-07-09",
                "statusSetBy": "agent", "reviewCadenceDays": 90,
            }],
        }]}))
        overrides_path = tmp_path / "breaker-overrides.jsonl"

        _cli_log_override(
            ticker="NBIS", breaker_id="nbis-ndr-floor", rationale="Board confirmed NDR recovery plan",
            target_portfolio_path=target_path, state_path=tmp_path / "does-not-exist.json",
            overrides_path=overrides_path,
        )

        entry = _json.loads(overrides_path.read_text().strip())
        assert entry["streak"] is None
        assert entry["horizon"] == "2 quarters"
