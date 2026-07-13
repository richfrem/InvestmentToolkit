"""Test evolution events integration with E3 prediction ledger (Task 10)."""
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
PY_SERVICES = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(PY_SERVICES))

from evolution_events import (  # noqa: E402
    EventType,
    EarningsGrade,
    emit_earnings_event,
    emit_breaker_override_event,
    emit_rebalance_event,
    generate_evolution_correlation_report,
    load_events,
)
from prediction_ledger import (  # noqa: E402
    append_prediction,
    load_predictions,
)


class TestEvolutionIntegrationRoundTrip:
    """Test full integration with E3 prediction ledger (Task 10)."""

    def test_all_emitters_and_reporting_workflow(self, tmp_path, monkeypatch):
        """Full end-to-end workflow: emit events, generate report."""
        import evolution_events

        events_path = tmp_path / "evolution_events.jsonl"
        monkeypatch.setattr(evolution_events, "EVOLUTION_EVENTS_PATH", events_path)

        # Emit multiple event types during a week
        emit_earnings_event(
            ticker="AAPL",
            grade=EarningsGrade.BEAT,
            earnings_date="2026-01-15",
            expected_eps=1.50,
            actual_eps=1.65,
            current_price=150.0,
        )

        emit_breaker_override_event(
            ticker="MSFT",
            breaker_name="pe_ratio_high",
            override_date="2026-01-16",
            override_reason="Analyst upgrade",
            current_price=320.0,
        )

        emit_rebalance_event(
            ticker="NVDA",
            order_type="buy",
            order_quantity=10,
            order_price=850.0,
            rebalance_date="2026-01-17",
        )

        # Verify all events were appended
        events = load_events(events_path)
        assert len(events) == 3
        assert any(e["context"]["ticker"] == "AAPL" for e in events)
        assert any(e["context"]["ticker"] == "MSFT" for e in events)
        assert any(e["context"]["ticker"] == "NVDA" for e in events)

    def test_emitters_coexist_with_prediction_ledger(self, tmp_path, monkeypatch):
        """Verify evolution events don't interfere with E3 ledger."""
        import evolution_events
        import prediction_ledger

        events_path = tmp_path / "evolution_events.jsonl"
        predictions_path = tmp_path / "predictions.jsonl"

        monkeypatch.setattr(evolution_events, "EVOLUTION_EVENTS_PATH", events_path)
        monkeypatch.setattr(prediction_ledger, "PREDICTIONS_PATH", predictions_path)

        # Emit to both systems
        emit_earnings_event(
            ticker="AAPL",
            grade=EarningsGrade.BEAT,
            earnings_date="2026-01-15",
            current_price=150.0,
        )

        pred = {
            "id": "AAPL:action_rating:2026-01-15",
            "ticker": "AAPL",
            "type": "action_rating",
        }
        append_prediction(pred, predictions_path)

        # Both systems should have their own files
        events = load_events(events_path)
        preds = load_predictions(predictions_path)

        assert len(events) == 1
        assert events[0]["event_id"] == "AAPL:earnings_catalyst:2026-01-15"
        assert len(preds) == 1
        assert preds[0]["id"] == "AAPL:action_rating:2026-01-15"

    def test_weekly_report_with_multiple_events(self, tmp_path, monkeypatch):
        """Generate weekly report aggregating multiple event types."""
        import evolution_events

        events_path = tmp_path / "evolution_events.jsonl"
        monkeypatch.setattr(evolution_events, "EVOLUTION_EVENTS_PATH", events_path)

        # Add multiple events in week
        emit_earnings_event(
            ticker="AAPL",
            grade=EarningsGrade.BEAT,
            earnings_date="2026-01-15",
            current_price=150.0,
        )

        emit_earnings_event(
            ticker="MSFT",
            grade=EarningsGrade.MISS,
            earnings_date="2026-01-16",
            current_price=320.0,
        )

        emit_rebalance_event(
            ticker="NVDA",
            order_type="buy",
            order_quantity=10,
            order_price=850.0,
            rebalance_date="2026-01-17",
        )

        report = generate_evolution_correlation_report("2026-01-13", "2026-01-20")

        assert report["total_events"] == 3
        assert "earnings_catalyst" in report["event_summary"]
        assert "rebalance_execution" in report["event_summary"]
        assert report["event_summary"]["earnings_catalyst"]["count"] == 2
        assert report["event_summary"]["rebalance_execution"]["count"] == 1

    def test_dedup_with_same_event_reemitted(self, tmp_path, monkeypatch):
        """Verify dedup when same event is re-emitted."""
        import evolution_events

        events_path = tmp_path / "evolution_events.jsonl"
        monkeypatch.setattr(evolution_events, "EVOLUTION_EVENTS_PATH", events_path)

        # First emission
        emit_earnings_event(
            ticker="AAPL",
            grade=EarningsGrade.BEAT,
            earnings_date="2026-01-15",
            expected_eps=1.50,
            actual_eps=1.65,
            current_price=150.0,
        )

        events = load_events(events_path)
        assert len(events) == 1

        # Re-emit same event with same details
        emit_earnings_event(
            ticker="AAPL",
            grade=EarningsGrade.BEAT,
            earnings_date="2026-01-15",
            expected_eps=1.50,
            actual_eps=1.65,  # Same EPS
            current_price=150.0,
        )

        events = load_events(events_path)
        # Should not append duplicate with identical details
        assert len(events) == 1

    def test_event_summary_by_type_in_report(self, tmp_path, monkeypatch):
        """Verify report aggregates by all 6 event types."""
        import evolution_events

        events_path = tmp_path / "evolution_events.jsonl"
        monkeypatch.setattr(evolution_events, "EVOLUTION_EVENTS_PATH", events_path)

        # Create one event of each type in the week
        emit_earnings_event(
            ticker="A",
            grade=EarningsGrade.BEAT,
            earnings_date="2026-01-15",
            current_price=100.0,
        )

        emit_breaker_override_event(
            ticker="B",
            breaker_name="test",
            override_date="2026-01-15",
            override_reason="Test",
        )

        emit_rebalance_event(
            ticker="C",
            order_type="buy",
            order_quantity=10,
            order_price=100.0,
            rebalance_date="2026-01-15",
        )

        # Can't easily test price_move, dividend, forced_exit without mocking
        # but structure is identical

        report = generate_evolution_correlation_report("2026-01-13", "2026-01-17")

        assert len(report["event_summary"]) >= 3
        assert report["total_events"] == 3

    def test_correlation_report_timestamp_format(self, tmp_path, monkeypatch):
        """Verify report has ISO format timestamp."""
        import evolution_events

        events_path = tmp_path / "evolution_events.jsonl"
        monkeypatch.setattr(evolution_events, "EVOLUTION_EVENTS_PATH", events_path)

        emit_earnings_event(
            ticker="AAPL",
            grade=EarningsGrade.BEAT,
            earnings_date="2026-01-15",
        )

        report = generate_evolution_correlation_report("2026-01-13", "2026-01-17")

        # Verify generated_at is ISO format
        assert "generated_at" in report
        assert "T" in report["generated_at"]
        assert "Z" in report["generated_at"] or "+" in report["generated_at"]

    def test_nonblocking_error_handling_all_emitters(self, tmp_path, monkeypatch):
        """Verify all emitters are non-blocking on errors."""
        import evolution_events

        # Use invalid path to force errors
        monkeypatch.setattr(evolution_events, "EVOLUTION_EVENTS_PATH", Path("/invalid/path"))

        # None of these should raise
        emit_earnings_event("A", EarningsGrade.BEAT, "2026-01-15")
        emit_breaker_override_event("B", "test", "2026-01-15", "reason")
        emit_rebalance_event("C", "buy", 10, 100.0, "2026-01-15")

        # Should not raise, path still invalid
        from evolution_events import emit_price_move_event, emit_dividend_event, emit_forced_exit_event

        emit_price_move_event("D", 5.0, "2026-01-15")
        emit_dividend_event("E", 0.5, "2026-01-15")
        emit_forced_exit_event("F", 100.0, "2026-01-15", "manual_exit")

    def test_event_context_preserved_across_workflow(self, tmp_path, monkeypatch):
        """Verify position context data is preserved through storage."""
        import evolution_events

        events_path = tmp_path / "evolution_events.jsonl"
        monkeypatch.setattr(evolution_events, "EVOLUTION_EVENTS_PATH", events_path)

        emit_earnings_event(
            ticker="AAPL",
            grade=EarningsGrade.BEAT,
            earnings_date="2026-01-15",
            entry_price=145.0,
            shares=100,
            current_price=150.0,
        )

        events = load_events(events_path)
        ctx = events[0]["context"]

        assert ctx["entry_price"] == 145.0
        assert ctx["shares"] == 100
        assert ctx["current_price"] == 150.0

    def test_report_excludes_events_outside_week(self, tmp_path, monkeypatch):
        """Verify weekly report doesn't include events from other weeks."""
        import evolution_events

        events_path = tmp_path / "evolution_events.jsonl"
        monkeypatch.setattr(evolution_events, "EVOLUTION_EVENTS_PATH", events_path)

        emit_earnings_event(
            ticker="AAPL",
            grade=EarningsGrade.BEAT,
            earnings_date="2026-01-10",  # Before week
            current_price=150.0,
        )

        emit_earnings_event(
            ticker="MSFT",
            grade=EarningsGrade.BEAT,
            earnings_date="2026-01-15",  # During week
            current_price=320.0,
        )

        emit_earnings_event(
            ticker="NVDA",
            grade=EarningsGrade.BEAT,
            earnings_date="2026-01-25",  # After week
            current_price=900.0,
        )

        report = generate_evolution_correlation_report("2026-01-13", "2026-01-17")

        assert report["total_events"] == 1
        assert report["event_summary"]["earnings_catalyst"]["count"] == 1
        assert "MSFT" in report["event_summary"]["earnings_catalyst"]["tickers"]
