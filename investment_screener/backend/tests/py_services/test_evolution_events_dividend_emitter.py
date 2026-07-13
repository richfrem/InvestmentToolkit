"""Test emit_dividend_event function (Task 6)."""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
PY_SERVICES = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(PY_SERVICES))

from evolution_events import (  # noqa: E402
    emit_dividend_event,
    load_events,
)


class TestEmitDividendEvent:
    """Test dividend event emission."""

    def test_emit_dividend(self, tmp_path, monkeypatch):
        import evolution_events

        events_path = tmp_path / "evolution_events.jsonl"
        monkeypatch.setattr(evolution_events, "EVOLUTION_EVENTS_PATH", events_path)

        emit_dividend_event(
            ticker="PSU-U.TO",
            dividend_amount=0.50,
            ex_date="2026-01-31",
            payment_date="2026-02-15",
            current_price=100.0,
        )

        events = load_events(events_path)
        assert len(events) == 1
        assert events[0]["context"]["ticker"] == "PSU-U.TO"
        assert events[0]["event_details"]["dividend_amount"] == 0.50
        assert events[0]["event_details"]["payment_date"] == "2026-02-15"

    def test_emit_dividend_without_payment_date(self, tmp_path, monkeypatch):
        import evolution_events

        events_path = tmp_path / "evolution_events.jsonl"
        monkeypatch.setattr(evolution_events, "EVOLUTION_EVENTS_PATH", events_path)

        emit_dividend_event(
            ticker="VFV",
            dividend_amount=1.25,
            ex_date="2026-02-15",
            current_price=45.5,
        )

        events = load_events(events_path)
        assert len(events) == 1
        assert events[0]["event_details"]["dividend_amount"] == 1.25
        assert events[0]["event_details"]["payment_date"] is None

    def test_emit_dividend_with_position_context(self, tmp_path, monkeypatch):
        import evolution_events

        events_path = tmp_path / "evolution_events.jsonl"
        monkeypatch.setattr(evolution_events, "EVOLUTION_EVENTS_PATH", events_path)

        emit_dividend_event(
            ticker="PSU-U.TO",
            dividend_amount=0.50,
            ex_date="2026-01-31",
            current_price=100.0,
            entry_price=95.0,
            shares=50,
        )

        events = load_events(events_path)
        assert events[0]["context"]["entry_price"] == 95.0
        assert events[0]["context"]["shares"] == 50

    def test_event_id_format(self, tmp_path, monkeypatch):
        import evolution_events

        events_path = tmp_path / "evolution_events.jsonl"
        monkeypatch.setattr(evolution_events, "EVOLUTION_EVENTS_PATH", events_path)

        emit_dividend_event(
            ticker="AAPL",
            dividend_amount=0.24,
            ex_date="2026-02-20",
        )

        events = load_events(events_path)
        assert events[0]["event_id"] == "AAPL:dividend_event:2026-02-20"

    def test_non_blocking_on_error(self, tmp_path, monkeypatch):
        import evolution_events

        monkeypatch.setattr(evolution_events, "EVOLUTION_EVENTS_PATH", Path("/invalid/path"))

        # Should not raise
        emit_dividend_event(
            ticker="PSU-U.TO",
            dividend_amount=0.50,
            ex_date="2026-01-31",
        )

    def test_dedup_on_same_ticker_type_date(self, tmp_path, monkeypatch):
        import evolution_events

        events_path = tmp_path / "evolution_events.jsonl"
        monkeypatch.setattr(evolution_events, "EVOLUTION_EVENTS_PATH", events_path)

        # First dividend
        emit_dividend_event(
            ticker="PSU-U.TO",
            dividend_amount=0.50,
            ex_date="2026-01-31",
        )

        # Same ex-date but different amount
        emit_dividend_event(
            ticker="PSU-U.TO",
            dividend_amount=0.55,  # Different amount
            ex_date="2026-01-31",
        )

        events = load_events(events_path)
        # Should append second one (details changed)
        assert len(events) == 2

    def test_multiple_dividends_same_ticker_different_dates(self, tmp_path, monkeypatch):
        import evolution_events

        events_path = tmp_path / "evolution_events.jsonl"
        monkeypatch.setattr(evolution_events, "EVOLUTION_EVENTS_PATH", events_path)

        emit_dividend_event(
            ticker="PSU-U.TO",
            dividend_amount=0.50,
            ex_date="2026-01-31",
        )

        emit_dividend_event(
            ticker="PSU-U.TO",
            dividend_amount=0.50,
            ex_date="2026-02-28",  # Different date
        )

        events = load_events(events_path)
        # Both should append (different dates)
        assert len(events) == 2
        assert events[0]["context"]["event_date"] == "2026-01-31"
        assert events[1]["context"]["event_date"] == "2026-02-28"
