"""Test emit_earnings_event function (Task 2)."""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
PY_SERVICES = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(PY_SERVICES))

from evolution_events import (  # noqa: E402
    EarningsGrade,
    emit_earnings_event,
    load_events,
)


class TestEmitEarningsEvent:
    """Test earnings catalyst event emission."""

    def test_emit_beat_grade(self, tmp_path, monkeypatch):
        # Monkeypatch the path for testing
        import evolution_events

        events_path = tmp_path / "evolution_events.jsonl"
        monkeypatch.setattr(evolution_events, "EVOLUTION_EVENTS_PATH", events_path)

        emit_earnings_event(
            ticker="AAPL",
            grade=EarningsGrade.BEAT,
            earnings_date="2026-01-15",
            expected_eps=1.50,
            actual_eps=1.65,
            current_price=150.0,
            entry_price=145.0,
            shares=100,
        )

        events = load_events(events_path)
        assert len(events) == 1
        assert events[0]["context"]["ticker"] == "AAPL"
        assert events[0]["event_details"]["grade"] == "beat"
        assert events[0]["event_details"]["expected_eps"] == 1.50
        assert events[0]["event_details"]["actual_eps"] == 1.65
        assert abs(events[0]["event_details"]["surprise_pct"] - 10.0) < 0.01

    def test_emit_miss_grade(self, tmp_path, monkeypatch):
        import evolution_events

        events_path = tmp_path / "evolution_events.jsonl"
        monkeypatch.setattr(evolution_events, "EVOLUTION_EVENTS_PATH", events_path)

        emit_earnings_event(
            ticker="MSFT",
            grade=EarningsGrade.MISS,
            earnings_date="2026-01-20",
            expected_eps=2.50,
            actual_eps=2.30,
            current_price=320.0,
        )

        events = load_events(events_path)
        assert len(events) == 1
        assert events[0]["event_details"]["grade"] == "miss"
        assert abs(events[0]["event_details"]["surprise_pct"] - (-8.0)) < 0.01

    def test_emit_in_line_grade(self, tmp_path, monkeypatch):
        import evolution_events

        events_path = tmp_path / "evolution_events.jsonl"
        monkeypatch.setattr(evolution_events, "EVOLUTION_EVENTS_PATH", events_path)

        emit_earnings_event(
            ticker="NVDA",
            grade=EarningsGrade.IN_LINE,
            earnings_date="2026-01-25",
            expected_eps=3.00,
            actual_eps=3.00,
        )

        events = load_events(events_path)
        assert len(events) == 1
        assert events[0]["event_details"]["grade"] == "in_line"
        assert events[0]["event_details"]["surprise_pct"] == 0.0

    def test_emit_without_eps_data(self, tmp_path, monkeypatch):
        import evolution_events

        events_path = tmp_path / "evolution_events.jsonl"
        monkeypatch.setattr(evolution_events, "EVOLUTION_EVENTS_PATH", events_path)

        emit_earnings_event(
            ticker="TSLA",
            grade=EarningsGrade.BEAT,
            earnings_date="2026-02-01",
        )

        events = load_events(events_path)
        assert len(events) == 1
        assert events[0]["event_details"]["surprise_pct"] is None

    def test_non_blocking_on_error(self, tmp_path, monkeypatch):
        import evolution_events

        # Monkeypatch to a bad path
        monkeypatch.setattr(evolution_events, "EVOLUTION_EVENTS_PATH", Path("/invalid/path"))

        # Should not raise, just silently fail
        emit_earnings_event(
            ticker="AAPL",
            grade=EarningsGrade.BEAT,
            earnings_date="2026-01-15",
        )

    def test_dedup_on_same_ticker_type_date(self, tmp_path, monkeypatch):
        import evolution_events

        events_path = tmp_path / "evolution_events.jsonl"
        monkeypatch.setattr(evolution_events, "EVOLUTION_EVENTS_PATH", events_path)

        # Emit first event
        emit_earnings_event(
            ticker="AAPL",
            grade=EarningsGrade.BEAT,
            earnings_date="2026-01-15",
            expected_eps=1.50,
            actual_eps=1.65,
        )

        # Emit same (ticker, type, date) with different details
        emit_earnings_event(
            ticker="AAPL",
            grade=EarningsGrade.BEAT,
            earnings_date="2026-01-15",
            expected_eps=1.50,
            actual_eps=1.70,  # Different actual_eps
        )

        events = load_events(events_path)
        # Should have appended the second one (context changed)
        assert len(events) == 2

    def test_preserves_position_data(self, tmp_path, monkeypatch):
        import evolution_events

        events_path = tmp_path / "evolution_events.jsonl"
        monkeypatch.setattr(evolution_events, "EVOLUTION_EVENTS_PATH", events_path)

        emit_earnings_event(
            ticker="AAPL",
            grade=EarningsGrade.BEAT,
            earnings_date="2026-01-15",
            entry_price=145.0,
            shares=50,
            current_price=150.0,
        )

        events = load_events(events_path)
        assert events[0]["context"]["entry_price"] == 145.0
        assert events[0]["context"]["shares"] == 50
        assert events[0]["context"]["current_price"] == 150.0
