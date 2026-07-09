"""Tests for daily_brief.py's B5 thesis-breaker triage integration."""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
PY_SERVICES = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(PY_SERVICES))

from daily_brief import render  # noqa: E402


def _minimal_brief(**overrides) -> dict:
    brief = {
        "overnight_gaps": [],
        "date": "2026-07-09",
        "timestamp": "2026-07-09T13:00:00Z",
        "macro_regime": {"regime": "NEUTRAL", "score": 0, "degraded": False},
        "market_regime": None,
        "risk_snapshot": None,
        "ta_refreshed": False,
        "ta_skip_reason": "",
        "conviction_scores": [],
        "recommendations": [],
        "total_equity": 10000.0,
        "score_deltas": {},
        "pillar_health": [],
        "pillar_deltas": {},
        "earnings_flags": [],
        "yesterday_date": "2026-07-08",
        "thesis_breakers": None,
        "thesis_breakers_triggered": [],
    }
    brief.update(overrides)
    return brief


class TestRenderNoBreakersTriggered:
    def test_no_triggered_block_when_list_empty(self):
        output = render(_minimal_brief())
        assert "THESIS BREAKER TRIGGERED" not in output


class TestRenderTriggeredBreakerAtTopOfTriage:
    def _triggered_brief(self):
        return _minimal_brief(
            overnight_gaps=[{"ticker": "AAPL", "direction": "UP", "change_pct": 3.0,
                              "current": 200.0, "prev_close": 194.0, "market_state": "PRE"}],
            conviction_scores=[{
                "ticker": "NBIS", "total": -3, "band": "EXIT", "dcf_pts": -2, "ta_pts": -1,
                "weight_gap_pts": 0, "momentum_pts": 0, "dcf_action": "SELL",
                "pct_to_fv": -40.0, "rsi": 22.0, "adx": 30.0, "vol_bias": 1.0,
                "actual_weight": 3.7, "target_weight": 5.5, "weight_gap": 1.8,
                "flags": [], "ta_staleness_days": 0,
            }],
            thesis_breakers_triggered=[{
                "ticker": "NBIS", "breakerId": "nbis-trend-breakdown", "targetWeight": 5.5,
                "type": "auto", "metric": "trendState", "operator": "in",
                "threshold": ["DOWNTREND"], "horizon": 5,
                "note": "Sustained downtrend contradicts the thesis",
                "currentValue": "DOWNTREND", "conditionMet": True, "currentStreak": 5,
                "streakStartDate": "2026-07-05", "lastEvaluatedAt": "2026-07-09T13:00:00Z",
                "status": "TRIGGERED",
            }],
        )

    def test_triggered_block_appears_before_overnight_gaps(self):
        output = render(self._triggered_brief())
        assert "THESIS BREAKER TRIGGERED" in output
        assert output.index("THESIS BREAKER TRIGGERED") < output.index("OVERNIGHT GAPS")

    def test_triggered_block_appears_before_reduce_exit_section(self):
        output = render(self._triggered_brief())
        assert output.index("THESIS BREAKER TRIGGERED") < output.index("REDUCE / EXIT")

    def test_triggered_block_shows_ticker_metric_and_streak(self):
        output = render(self._triggered_brief())
        assert "NBIS" in output
        assert "trendState" in output
        assert "5/5" in output
        assert "Sustained downtrend contradicts the thesis" in output

    def test_multiple_triggered_sorted_by_target_weight_descending(self):
        brief = self._triggered_brief()
        brief["thesis_breakers_triggered"].append({
            "ticker": "PANW", "breakerId": "panw-rsi-floor", "targetWeight": 5.9,
            "type": "auto", "metric": "rsi", "operator": "<", "threshold": 25, "horizon": 3,
            "note": "RSI breakdown", "currentValue": 20.0, "conditionMet": True,
            "currentStreak": 3, "streakStartDate": "2026-07-07",
            "lastEvaluatedAt": "2026-07-09T13:00:00Z", "status": "TRIGGERED",
        })
        output = render(brief)
        assert output.index("PANW") < output.index("NBIS")


class TestRenderManualBreakerStaleness:
    def test_stale_manual_breaker_renders_review_note(self):
        brief = _minimal_brief(thesis_breakers={
            "generatedAt": "2026-07-09T13:00:00Z",
            "holdings": {"NBIS": {"nbis-ndr-floor": {
                "type": "manual", "status": "OK", "statusSetAt": "2026-04-01",
                "reviewCadenceDays": 90, "daysSinceReview": 99, "stale": True,
            }}},
        })
        output = render(brief)
        assert "MANUAL BREAKERS NEEDING REVIEW" in output
        assert "NBIS" in output
        assert "nbis-ndr-floor" in output

    def test_non_stale_manual_breaker_no_review_note(self):
        brief = _minimal_brief(thesis_breakers={
            "generatedAt": "2026-07-09T13:00:00Z",
            "holdings": {"NBIS": {"nbis-ndr-floor": {
                "type": "manual", "status": "OK", "statusSetAt": "2026-07-01",
                "reviewCadenceDays": 90, "daysSinceReview": 8, "stale": False,
            }}},
        })
        output = render(brief)
        assert "MANUAL BREAKERS NEEDING REVIEW" not in output
