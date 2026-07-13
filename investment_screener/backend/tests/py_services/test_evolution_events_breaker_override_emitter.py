"""Test emit_breaker_override_event function (Task 3)."""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
PY_SERVICES = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(PY_SERVICES))

from evolution_events import (  # noqa: E402
    emit_breaker_override_event,
    load_events,
)


class TestEmitBreakerOverrideEvent:
    """Test thesis breaker override event emission."""

    def test_emit_basic_override(self, tmp_path, monkeypatch):
        import evolution_events

        events_path = tmp_path / "evolution_events.jsonl"
        monkeypatch.setattr(evolution_events, "EVOLUTION_EVENTS_PATH", events_path)

        emit_breaker_override_event(
            ticker="AAPL",
            breaker_name="pe_ratio_high",
            override_date="2026-01-10",
            override_reason="Analyst upgrade justifies higher multiple",
            breaker_threshold=25.0,
        )

        events = load_events(events_path)
        assert len(events) == 1
        assert events[0]["context"]["ticker"] == "AAPL"
        assert events[0]["event_details"]["breaker_name"] == "pe_ratio_high"
        assert events[0]["event_details"]["override_reason"] == "Analyst upgrade justifies higher multiple"
        assert events[0]["event_details"]["breaker_threshold"] == 25.0

    def test_emit_with_position_data(self, tmp_path, monkeypatch):
        import evolution_events

        events_path = tmp_path / "evolution_events.jsonl"
        monkeypatch.setattr(evolution_events, "EVOLUTION_EVENTS_PATH", events_path)

        emit_breaker_override_event(
            ticker="TSLA",
            breaker_name="debt_to_equity_high",
            override_date="2026-01-15",
            override_reason="Balance sheet improved with new facility",
            current_price=245.0,
            entry_price=200.0,
            shares=25,
        )

        events = load_events(events_path)
        assert events[0]["context"]["current_price"] == 245.0
        assert events[0]["context"]["entry_price"] == 200.0
        assert events[0]["context"]["shares"] == 25

    def test_event_id_format(self, tmp_path, monkeypatch):
        import evolution_events

        events_path = tmp_path / "evolution_events.jsonl"
        monkeypatch.setattr(evolution_events, "EVOLUTION_EVENTS_PATH", events_path)

        emit_breaker_override_event(
            ticker="NVDA",
            breaker_name="revenue_decline",
            override_date="2026-02-01",
            override_reason="Q4 guidance strong",
        )

        events = load_events(events_path)
        assert events[0]["event_id"] == "NVDA:thesis_breaker_override:2026-02-01"

    def test_non_blocking_on_error(self, tmp_path, monkeypatch):
        import evolution_events

        monkeypatch.setattr(evolution_events, "EVOLUTION_EVENTS_PATH", Path("/invalid/path"))

        # Should not raise
        emit_breaker_override_event(
            ticker="AAPL",
            breaker_name="test_breaker",
            override_date="2026-01-10",
            override_reason="Test override",
        )

    def test_dedup_on_same_ticker_type_date(self, tmp_path, monkeypatch):
        import evolution_events

        events_path = tmp_path / "evolution_events.jsonl"
        monkeypatch.setattr(evolution_events, "EVOLUTION_EVENTS_PATH", events_path)

        # First override
        emit_breaker_override_event(
            ticker="AAPL",
            breaker_name="pe_ratio_high",
            override_date="2026-01-10",
            override_reason="Reason 1",
        )

        # Same ticker/type/date but different reason
        emit_breaker_override_event(
            ticker="AAPL",
            breaker_name="pe_ratio_high",
            override_date="2026-01-10",
            override_reason="Reason 2",  # Different context
        )

        events = load_events(events_path)
        # Should append second one (context changed)
        assert len(events) == 2

    def test_multiple_breakdowns_same_day(self, tmp_path, monkeypatch):
        import evolution_events

        events_path = tmp_path / "evolution_events.jsonl"
        monkeypatch.setattr(evolution_events, "EVOLUTION_EVENTS_PATH", events_path)

        emit_breaker_override_event(
            ticker="AAPL",
            breaker_name="breaker_1",
            override_date="2026-01-10",
            override_reason="Override 1",
        )

        emit_breaker_override_event(
            ticker="AAPL",
            breaker_name="breaker_2",
            override_date="2026-01-10",
            override_reason="Override 2",
        )

        events = load_events(events_path)
        # Different breaker types should both append
        assert len(events) == 2
        assert events[0]["event_details"]["breaker_name"] == "breaker_1"
        assert events[1]["event_details"]["breaker_name"] == "breaker_2"
