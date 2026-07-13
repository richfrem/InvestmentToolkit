"""Test generate_evolution_correlation_report function (Task 9)."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
PY_SERVICES = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(PY_SERVICES))

from evolution_events import (  # noqa: E402
    generate_evolution_correlation_report,
    _append_jsonl,
)


class TestGenerateEvolutionCorrelationReport:
    """Test correlation report generation."""

    def test_report_structure(self, tmp_path, monkeypatch):
        import evolution_events

        events_path = tmp_path / "evolution_events.jsonl"
        monkeypatch.setattr(evolution_events, "EVOLUTION_EVENTS_PATH", events_path)

        # Create an event in the week
        event = {
            "event_id": "AAPL:earnings_catalyst:2026-01-15",
            "context": {
                "ticker": "AAPL",
                "event_type": "earnings_catalyst",
                "event_date": "2026-01-15",
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

        report = generate_evolution_correlation_report("2026-01-13", "2026-01-17")

        assert "week_start" in report
        assert "week_end" in report
        assert "event_summary" in report
        assert "total_events" in report
        assert "generated_at" in report
        assert report["week_start"] == "2026-01-13"
        assert report["week_end"] == "2026-01-17"
        assert report["total_events"] == 1

    def test_event_summary_aggregation(self, tmp_path, monkeypatch):
        import evolution_events

        events_path = tmp_path / "evolution_events.jsonl"
        monkeypatch.setattr(evolution_events, "EVOLUTION_EVENTS_PATH", events_path)

        # Create multiple event types
        events = [
            {
                "event_id": "AAPL:earnings_catalyst:2026-01-15",
                "context": {
                    "ticker": "AAPL",
                    "event_type": "earnings_catalyst",
                    "event_date": "2026-01-15",
                    "current_price": 150.0,
                },
                "event_details": {"grade": "beat"},
                "outcome": {
                    "outcome_seven_day": 5.0,
                    "outcome_thirty_day": 8.0,
                    "seven_day_price": 157.5,
                    "thirty_day_price": 162.0,
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            {
                "event_id": "MSFT:dividend_event:2026-01-20",
                "context": {
                    "ticker": "MSFT",
                    "event_type": "dividend_event",
                    "event_date": "2026-01-20",
                    "current_price": 320.0,
                },
                "event_details": {"dividend_amount": 0.68},
                "outcome": {
                    "outcome_seven_day": -2.0,
                    "outcome_thirty_day": 3.0,
                    "seven_day_price": 313.6,
                    "thirty_day_price": 329.6,
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            {
                "event_id": "NVDA:earnings_catalyst:2026-01-18",
                "context": {
                    "ticker": "NVDA",
                    "event_type": "earnings_catalyst",
                    "event_date": "2026-01-18",
                    "current_price": 920.0,
                },
                "event_details": {"grade": "beat"},
                "outcome": {
                    "outcome_seven_day": 7.0,
                    "outcome_thirty_day": 12.0,
                    "seven_day_price": 984.4,
                    "thirty_day_price": 1032.4,
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        ]

        for event in events:
            _append_jsonl(event, events_path)

        report = generate_evolution_correlation_report("2026-01-13", "2026-01-22")

        assert report["total_events"] == 3
        assert "earnings_catalyst" in report["event_summary"]
        assert "dividend_event" in report["event_summary"]

        earnings = report["event_summary"]["earnings_catalyst"]
        assert earnings["count"] == 2
        assert "AAPL" in earnings["tickers"]
        assert "NVDA" in earnings["tickers"]
        assert earnings["avg_7day_return"] == 6.0  # (5.0 + 7.0) / 2
        assert earnings["avg_30day_return"] == 10.0  # (8.0 + 12.0) / 2

        dividend = report["event_summary"]["dividend_event"]
        assert dividend["count"] == 1
        assert dividend["avg_7day_return"] == -2.0

    def test_averages_with_null_outcomes(self, tmp_path, monkeypatch):
        import evolution_events

        events_path = tmp_path / "evolution_events.jsonl"
        monkeypatch.setattr(evolution_events, "EVOLUTION_EVENTS_PATH", events_path)

        # Mix of events with and without outcomes
        events = [
            {
                "event_id": "AAPL:earnings_catalyst:2026-01-15",
                "context": {
                    "ticker": "AAPL",
                    "event_type": "earnings_catalyst",
                    "event_date": "2026-01-15",
                    "current_price": 150.0,
                },
                "event_details": {"grade": "beat"},
                "outcome": {
                    "outcome_seven_day": 5.0,
                    "outcome_thirty_day": None,  # No 30-day yet
                    "seven_day_price": 157.5,
                    "thirty_day_price": None,
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            {
                "event_id": "MSFT:earnings_catalyst:2026-01-18",
                "context": {
                    "ticker": "MSFT",
                    "event_type": "earnings_catalyst",
                    "event_date": "2026-01-18",
                    "current_price": 320.0,
                },
                "event_details": {"grade": "beat"},
                "outcome": {
                    "outcome_seven_day": None,  # No 7-day yet
                    "outcome_thirty_day": 8.0,
                    "seven_day_price": None,
                    "thirty_day_price": 345.6,
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        ]

        for event in events:
            _append_jsonl(event, events_path)

        report = generate_evolution_correlation_report("2026-01-13", "2026-01-20")

        earnings = report["event_summary"]["earnings_catalyst"]
        assert earnings["count"] == 2
        assert earnings["avg_7day_return"] == 5.0  # Only one has 7-day
        assert earnings["avg_30day_return"] == 8.0  # Only one has 30-day

    def test_empty_week(self, tmp_path, monkeypatch):
        import evolution_events

        events_path = tmp_path / "evolution_events.jsonl"
        monkeypatch.setattr(evolution_events, "EVOLUTION_EVENTS_PATH", events_path)

        # Add event outside the week range
        event = {
            "event_id": "AAPL:earnings_catalyst:2026-01-10",
            "context": {
                "ticker": "AAPL",
                "event_type": "earnings_catalyst",
                "event_date": "2026-01-10",
                "current_price": 150.0,
            },
            "event_details": {"grade": "beat"},
            "outcome": {
                "outcome_seven_day": 5.0,
                "outcome_thirty_day": 8.0,
                "seven_day_price": 157.5,
                "thirty_day_price": 162.0,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        _append_jsonl(event, events_path)

        report = generate_evolution_correlation_report("2026-01-13", "2026-01-17")

        assert report["total_events"] == 0
        assert report["event_summary"] == {}

    def test_all_event_types_in_summary(self, tmp_path, monkeypatch):
        import evolution_events

        events_path = tmp_path / "evolution_events.jsonl"
        monkeypatch.setattr(evolution_events, "EVOLUTION_EVENTS_PATH", events_path)

        # Create one of each event type
        event_types = [
            ("earnings_catalyst", "earnings_catalyst"),
            ("thesis_breaker_override", "thesis_breaker_override"),
            ("rebalance_execution", "rebalance_execution"),
            ("large_price_move", "large_price_move"),
            ("dividend_event", "dividend_event"),
            ("forced_exit", "forced_exit"),
        ]

        for i, (ticker_suffix, event_type) in enumerate(event_types):
            event = {
                "event_id": f"TEST{i}:{event_type}:2026-01-15",
                "context": {
                    "ticker": f"TEST{i}",
                    "event_type": event_type,
                    "event_date": "2026-01-15",
                    "current_price": 100.0,
                },
                "event_details": {},
                "outcome": {
                    "outcome_seven_day": float(i + 1),
                    "outcome_thirty_day": float(i + 2),
                    "seven_day_price": 100.0 + i,
                    "thirty_day_price": 100.0 + i + 1,
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            _append_jsonl(event, events_path)

        report = generate_evolution_correlation_report("2026-01-13", "2026-01-17")

        assert report["total_events"] == 6
        for event_type, _ in event_types:
            assert event_type in report["event_summary"]
            summary = report["event_summary"][event_type]
            assert summary["count"] == 1
            assert summary["avg_7day_return"] is not None
            assert summary["avg_30day_return"] is not None

    def test_report_handles_missing_file(self, tmp_path, monkeypatch):
        import evolution_events

        events_path = tmp_path / "evolution_events.jsonl"
        monkeypatch.setattr(evolution_events, "EVOLUTION_EVENTS_PATH", events_path)

        # Don't create the file
        report = generate_evolution_correlation_report("2026-01-13", "2026-01-17")

        assert report["total_events"] == 0
        assert report["week_start"] == "2026-01-13"
        assert report["week_end"] == "2026-01-17"
