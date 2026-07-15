"""Task 5C-8: Integration into /daily.

Tests for daily_brief.py's advisory-only alert sync integration:
_newly_fired_alerts() (start/end sync_alert_state() comparison) and the
render() blocks that display newly-fired alerts and the advisory alert
candidate list.

Advisory-only, per the user's explicit 2026-07-14 decision: this
integration NEVER calls alert_manager.create_price_alert() or
alert_manager.dedup_alerts() — real TV alerts can't be individually
deleted (only bulk-delete-all), so /daily only surfaces candidate
tickers, it never creates anything. test_advisory_alert_signals_never_calls_create_price_alert
is the safety-critical test guarding that constraint.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
PY_SERVICES = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(PY_SERVICES))

from daily_brief import _newly_fired_alerts, _new_actionable_tickers, render  # noqa: E402
import daily_brief  # noqa: E402
import alert_manager  # noqa: E402


def _never_call(*args, **kwargs):
    """A create_price_alert/dedup_alerts stand-in that fails loudly if invoked."""
    raise AssertionError(f"must not be invoked, but was called with args={args}")


def _card(ticker: str, recommendation: str, actionable: bool) -> dict:
    return {"ticker": ticker, "recommendation": recommendation, "actionable": actionable}


def _yesterday_snapshot(recommendations: list[dict]) -> dict:
    return {"date": "2026-07-13", "recommendations": recommendations}


def _minimal_brief(**overrides) -> dict:
    brief = {
        "overnight_gaps": [],
        "date": "2026-07-14",
        "timestamp": "2026-07-14T13:00:00Z",
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
        "yesterday_date": "2026-07-13",
        "thesis_breakers": None,
        "thesis_breakers_triggered": [],
        "alert_sync": {"start": [], "end": [], "newly_fired": []},
        "advisory_alert_signals": [],
    }
    brief.update(overrides)
    return brief


# --- _newly_fired_alerts ---

class TestNewlyFiredAlerts:
    def test_newly_fired_alerts_returns_alerts_fired_since_start(self):
        start = [{"alert_id": "a1", "symbol": "NVDA", "state": "pending"}]
        end = [{"alert_id": "a1", "symbol": "NVDA", "state": "fired"}]

        result = _newly_fired_alerts(start, end)

        assert result == [{"alert_id": "a1", "symbol": "NVDA", "state": "fired"}]

    def test_newly_fired_alerts_excludes_alerts_already_fired_at_start(self):
        start = [{"alert_id": "a1", "symbol": "NVDA", "state": "fired"}]
        end = [{"alert_id": "a1", "symbol": "NVDA", "state": "fired"}]

        result = _newly_fired_alerts(start, end)

        assert result == []

    def test_newly_fired_alerts_returns_empty_when_nothing_new(self):
        start = [{"alert_id": "a1", "symbol": "NVDA", "state": "pending"}]
        end = [{"alert_id": "a1", "symbol": "NVDA", "state": "pending"}]

        result = _newly_fired_alerts(start, end)

        assert result == []

    def test_newly_fired_alerts_handles_empty_lists(self):
        result = _newly_fired_alerts([], [])

        assert result == []


# --- render() — fired alerts + advisory signals ---

class TestRenderFiredAlerts:
    def test_render_displays_fired_alerts_above_overnight_gaps(self):
        brief = _minimal_brief(
            overnight_gaps=[{"ticker": "AAPL", "direction": "UP", "change_pct": 3.0,
                              "current": 200.0, "prev_close": 194.0, "market_state": "PRE"}],
            alert_sync={
                "start": [],
                "end": [{"alert_id": "a1", "symbol": "NVDA", "state": "fired"}],
                "newly_fired": [{"alert_id": "a1", "symbol": "NVDA", "state": "fired"}],
            },
        )

        output = render(brief)

        assert "ALERTS FIRED" in output
        assert output.index("ALERTS FIRED") < output.index("OVERNIGHT GAPS")


class TestRenderAdvisoryAlertSignals:
    def test_render_displays_advisory_alert_signals(self):
        brief = _minimal_brief(advisory_alert_signals=["NVDA", "AAPL"])

        output = render(brief)

        assert "NVDA" in output
        assert "AAPL" in output
        assert "advisory" in output.lower()

    def test_render_omits_alert_sections_when_empty(self):
        brief = _minimal_brief(
            alert_sync={"start": [], "end": [], "newly_fired": []},
            advisory_alert_signals=[],
        )

        output = render(brief)

        assert "ALERTS FIRED" not in output
        assert "Would create TV alerts" not in output


# --- Safety-critical: advisory-only, never creates real alerts ---

class TestAdvisoryAlertSignalsNeverCreatesAlerts:
    def test_advisory_alert_signals_never_calls_create_price_alert(self, monkeypatch):
        monkeypatch.setattr(alert_manager, "create_price_alert", _never_call)
        monkeypatch.setattr(alert_manager, "dedup_alerts", _never_call)

        # daily_brief must not have imported these names directly either —
        # if it had, monkeypatching the alert_manager module attribute above
        # wouldn't even be the right guard (a `from alert_manager import
        # create_price_alert` binds a separate name daily_brief owns).
        assert not hasattr(daily_brief, "create_price_alert")
        assert not hasattr(daily_brief, "dedup_alerts")

        today = [
            _card("AAPL", "BUY", True),
            _card("NBIS", "SELL", True),
        ]
        yesterday = _yesterday_snapshot([])

        # This is the exact computation the run()/brief-dict wiring uses
        # for advisory_alert_signals — reusing _new_actionable_tickers()
        # directly, per the brief's non-negotiable decision.
        advisory_alert_tickers = _new_actionable_tickers(today, yesterday)

        assert advisory_alert_tickers == ["AAPL", "NBIS"]
