"""Task 5B-8: Integration into /daily.

Tests for daily_brief.py's Pine signal auto-injection step —
_new_actionable_tickers() (day-over-day new-signal detection) and
_inject_pine_signals_step() (real TradingView chart side effect via
pine_script_manager.inject_pine_script()).

inject_pine_script is mocked at pine_script_manager's module-level
attribute (same technique test_pine_injection_auto_clicks.py uses for
tv_call) — _inject_pine_signals_step's local `from pine_script_manager
import inject_pine_script` re-reads the module attribute at call time,
so no test here ever reaches real tv_call/CDP.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
PY_SERVICES = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(PY_SERVICES))

from daily_brief import _new_actionable_tickers, _inject_pine_signals_step  # noqa: E402
import daily_brief  # noqa: E402 — needed to monkeypatch daily_brief.PY_SERVICES if required
import pine_script_manager  # noqa: E402


def _card(ticker: str, recommendation: str, actionable: bool) -> dict:
    return {"ticker": ticker, "recommendation": recommendation, "actionable": actionable}


def _yesterday_snapshot(recommendations: list[dict]) -> dict:
    return {"date": "2026-07-12", "recommendations": recommendations}


def _never_call(*args, **kwargs):
    """An inject_pine_script stand-in that fails the test loudly if invoked."""
    raise AssertionError(f"inject_pine_script must not be invoked, but was called with args={args}")


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

        def fake_inject(script_name, chart_symbol):
            calls.append((script_name, chart_symbol))
            return True

        monkeypatch.setattr(pine_script_manager, "inject_pine_script", fake_inject)

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

        def fake_inject(script_name, chart_symbol):
            calls.append((script_name, chart_symbol))
            return outcomes[chart_symbol]

        monkeypatch.setattr(pine_script_manager, "inject_pine_script", fake_inject)

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

        monkeypatch.setattr(pine_script_manager, "inject_pine_script", _never_call)

        result = _inject_pine_signals_step(today, yesterday)

        assert result == []
