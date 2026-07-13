"""Test populate_event_outcomes function (Task 8)."""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
PY_SERVICES = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(PY_SERVICES))

from evolution_events import (  # noqa: E402
    populate_event_outcomes,
    _append_jsonl,
    load_events,
)


class TestPopulateEventOutcomes:
    """Test outcome population with no lookahead bias."""

    def test_outcome_fields_null_when_window_not_passed(self, tmp_path, monkeypatch):
        import evolution_events

        events_path = tmp_path / "evolution_events.jsonl"
        monkeypatch.setattr(evolution_events, "EVOLUTION_EVENTS_PATH", events_path)

        # Create event from today
        today = datetime.now(timezone.utc)
        event_date = today.isoformat()[:10]

        event = {
            "event_id": f"AAPL:earnings_catalyst:{event_date}",
            "context": {
                "ticker": "AAPL",
                "event_type": "earnings_catalyst",
                "event_date": event_date,
                "current_price": 150.0,
            },
            "event_details": {"grade": "beat"},
            "outcome": {
                "outcome_seven_day": None,
                "outcome_thirty_day": None,
                "seven_day_price": None,
                "thirty_day_price": None,
            },
            "timestamp": today.isoformat(),
        }
        _append_jsonl(event, events_path)

        # Try to populate — windows haven't passed yet
        populate_event_outcomes()

        events = load_events(events_path)
        assert len(events) == 1
        assert events[0]["outcome"]["outcome_seven_day"] is None
        assert events[0]["outcome"]["outcome_thirty_day"] is None

    def test_outcome_fields_null_for_missing_price(self, tmp_path, monkeypatch):
        import evolution_events

        events_path = tmp_path / "evolution_events.jsonl"
        monkeypatch.setattr(evolution_events, "EVOLUTION_EVENTS_PATH", events_path)

        # Event without current_price
        event = {
            "event_id": "AAPL:earnings_catalyst:2026-01-01",
            "context": {
                "ticker": "AAPL",
                "event_type": "earnings_catalyst",
                "event_date": "2026-01-01",
                "current_price": None,  # Missing price
            },
            "event_details": {"grade": "beat"},
            "outcome": {
                "outcome_seven_day": None,
                "outcome_thirty_day": None,
                "seven_day_price": None,
                "thirty_day_price": None,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        _append_jsonl(event, events_path)

        populate_event_outcomes()

        events = load_events(events_path)
        assert events[0]["outcome"]["outcome_seven_day"] is None

    def test_outcome_fields_skipped_if_already_populated(self, tmp_path, monkeypatch):
        import evolution_events

        events_path = tmp_path / "evolution_events.jsonl"
        monkeypatch.setattr(evolution_events, "EVOLUTION_EVENTS_PATH", events_path)

        # Event that already has outcome populated
        event = {
            "event_id": "AAPL:earnings_catalyst:2026-01-01",
            "context": {
                "ticker": "AAPL",
                "event_type": "earnings_catalyst",
                "event_date": "2026-01-01",
                "current_price": 150.0,
            },
            "event_details": {"grade": "beat"},
            "outcome": {
                "outcome_seven_day": 5.0,  # Already populated
                "outcome_thirty_day": None,
                "seven_day_price": 157.5,
                "thirty_day_price": None,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        _append_jsonl(event, events_path)

        populate_event_outcomes()

        events = load_events(events_path)
        # Should not be modified (already has seven_day outcome)
        assert events[0]["outcome"]["outcome_seven_day"] == 5.0

    def test_outcome_structure_preserved(self, tmp_path, monkeypatch):
        import evolution_events

        events_path = tmp_path / "evolution_events.jsonl"
        monkeypatch.setattr(evolution_events, "EVOLUTION_EVENTS_PATH", events_path)

        event = {
            "event_id": "AAPL:earnings_catalyst:2026-01-01",
            "context": {
                "ticker": "AAPL",
                "event_type": "earnings_catalyst",
                "event_date": "2026-01-01",
                "current_price": 150.0,
            },
            "event_details": {"grade": "beat"},
            "outcome": {
                "outcome_seven_day": None,
                "outcome_thirty_day": None,
                "seven_day_price": None,
                "thirty_day_price": None,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        _append_jsonl(event, events_path)

        populate_event_outcomes()

        events = load_events(events_path)
        outcome = events[0]["outcome"]
        # All four outcome fields should exist, even if None
        assert "outcome_seven_day" in outcome
        assert "outcome_thirty_day" in outcome
        assert "seven_day_price" in outcome
        assert "thirty_day_price" in outcome

    def test_multiple_events_processed(self, tmp_path, monkeypatch):
        import evolution_events

        events_path = tmp_path / "evolution_events.jsonl"
        monkeypatch.setattr(evolution_events, "EVOLUTION_EVENTS_PATH", events_path)

        # Add multiple events
        for i, ticker in enumerate(["AAPL", "MSFT", "NVDA"]):
            event = {
                "event_id": f"{ticker}:earnings_catalyst:2026-01-01",
                "context": {
                    "ticker": ticker,
                    "event_type": "earnings_catalyst",
                    "event_date": "2026-01-01",
                    "current_price": 150.0 + i * 10,
                },
                "event_details": {"grade": "beat"},
                "outcome": {
                    "outcome_seven_day": None,
                    "outcome_thirty_day": None,
                    "seven_day_price": None,
                    "thirty_day_price": None,
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            _append_jsonl(event, events_path)

        populate_event_outcomes()

        events = load_events(events_path)
        assert len(events) == 3
        # All outcomes should still be None (windows not passed)
        for event in events:
            assert event["outcome"]["outcome_seven_day"] is None
            assert event["outcome"]["outcome_thirty_day"] is None

    def test_empty_events_file(self, tmp_path, monkeypatch):
        import evolution_events

        events_path = tmp_path / "evolution_events.jsonl"
        monkeypatch.setattr(evolution_events, "EVOLUTION_EVENTS_PATH", events_path)

        # Populate with no events
        populate_event_outcomes()

        events = load_events(events_path)
        assert len(events) == 0

    def test_non_blocking_on_yfinance_error(self, tmp_path, monkeypatch):
        import evolution_events

        events_path = tmp_path / "evolution_events.jsonl"
        monkeypatch.setattr(evolution_events, "EVOLUTION_EVENTS_PATH", events_path)

        # Event with valid structure
        event = {
            "event_id": "AAPL:earnings_catalyst:2026-01-01",
            "context": {
                "ticker": "AAPL",
                "event_type": "earnings_catalyst",
                "event_date": "2026-01-01",
                "current_price": 150.0,
            },
            "event_details": {"grade": "beat"},
            "outcome": {
                "outcome_seven_day": None,
                "outcome_thirty_day": None,
                "seven_day_price": None,
                "thirty_day_price": None,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        _append_jsonl(event, events_path)

        # Should not raise on yfinance errors
        populate_event_outcomes()

        events = load_events(events_path)
        # Event should still exist
        assert len(events) == 1
