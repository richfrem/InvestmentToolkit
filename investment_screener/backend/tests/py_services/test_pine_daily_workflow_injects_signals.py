"""Task 5B-8: Integration into /daily.

Tests for daily_brief.py's chart step: _new_actionable_tickers() (day-over-day new-signal
detection) and _inject_pine_signals_step(), which draws each new ticker's stored price
levels by setting the AI TA Levels indicator's inputs (pine_level_inputs.draw_levels).

draw_levels is mocked at pine_level_inputs' module attribute, so no test here reaches
real tv_call/CDP.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
PY_SERVICES = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(PY_SERVICES))

from daily_brief import _new_actionable_tickers, _inject_pine_signals_step  # noqa: E402
import daily_brief  # noqa: E402 — needed to monkeypatch daily_brief.PY_SERVICES if required
import pine_script_manager  # noqa: E402
import pine_level_inputs  # noqa: E402


def _card(ticker: str, recommendation: str, actionable: bool) -> dict:
    return {"ticker": ticker, "recommendation": recommendation, "actionable": actionable}


def _yesterday_snapshot(recommendations: list[dict]) -> dict:
    return {"date": "2026-07-12", "recommendations": recommendations}


def _never_call(*args, **kwargs):
    """A draw_levels stand-in that fails the test loudly if invoked."""
    raise AssertionError(f"draw_levels must not be invoked, but was called with args={args}")


# --- _new_actionable_tickers ---

class TestNewActionableTickers:
    def test_returns_only_newly_actionable(self):
        today = [
            _card("AAPL", "BUY", True),
            _card("NBIS", "SELL", True),
            _card("PANW", "HOLD", False),
        ]
        yesterday = _yesterday_snapshot([
            _card("AAPL", "BUY", True),
            _card("NBIS", "HOLD", False),
        ])

        result = _new_actionable_tickers(today, yesterday)

        assert result == ["NBIS"]

    def test_first_run_no_yesterday_returns_all_actionable_today(self):
        today = [
            _card("AAPL", "BUY", True),
            _card("NBIS", "SELL", True),
            _card("PANW", "HOLD", False),
        ]

        result = _new_actionable_tickers(today, None)

        assert result == ["AAPL", "NBIS"]

    def test_ignores_non_actionable_cards(self):
        today = [
            _card("AAPL", "HOLD", False),
            _card("NBIS", "QUEUED", False),
        ]
        yesterday = _yesterday_snapshot([])

        result = _new_actionable_tickers(today, yesterday)

        assert result == []

    def test_returns_empty_when_nothing_new(self):
        today = [
            _card("AAPL", "BUY", True),
            _card("NBIS", "SELL", True),
        ]
        yesterday = _yesterday_snapshot([
            _card("AAPL", "BUY", True),
            _card("NBIS", "SELL", True),
        ])

        result = _new_actionable_tickers(today, yesterday)

        assert result == []


# --- _inject_pine_signals_step ---

class TestInjectPineSignalsStep:
    def test_injects_each_new_ticker_in_order(self, monkeypatch):
        today = [
            _card("NBIS", "SELL", True),
            _card("AAPL", "BUY", True),
        ]
        yesterday = _yesterday_snapshot([])

        calls = []

        def fake_draw(chart_symbol):
            calls.append(("ai-ta-levels", chart_symbol))
            return {"success": True}

        monkeypatch.setattr(pine_level_inputs, "draw_levels", fake_draw)

        result = _inject_pine_signals_step(today, yesterday)

        # _new_actionable_tickers sorts: AAPL before NBIS
        assert calls == [("ai-ta-levels", "AAPL"), ("ai-ta-levels", "NBIS")]
        assert result == [
            {"ticker": "AAPL", "injected": True},
            {"ticker": "NBIS", "injected": True},
        ]

    def test_continues_after_one_failure(self, monkeypatch, capsys):
        today = [
            _card("AAPL", "BUY", True),
            _card("NBIS", "SELL", True),
        ]
        yesterday = _yesterday_snapshot([])

        outcomes = {"AAPL": False, "NBIS": True}
        calls = []

        def fake_draw(chart_symbol):
            calls.append(("ai-ta-levels", chart_symbol))
            return {"success": outcomes[chart_symbol], "error": "not on chart"}

        monkeypatch.setattr(pine_level_inputs, "draw_levels", fake_draw)

        result = _inject_pine_signals_step(today, yesterday)

        assert calls == [("ai-ta-levels", "AAPL"), ("ai-ta-levels", "NBIS")]
        assert result == [
            {"ticker": "AAPL", "injected": False},
            {"ticker": "NBIS", "injected": True},
        ]

        captured = capsys.readouterr()
        assert "AAPL" in captured.err

    def test_returns_empty_list_without_calling_inject_when_nothing_new(self, monkeypatch):
        today = [_card("AAPL", "HOLD", False)]
        yesterday = _yesterday_snapshot([])

        monkeypatch.setattr(pine_level_inputs, "draw_levels", _never_call)

        result = _inject_pine_signals_step(today, yesterday)

        assert result == []
