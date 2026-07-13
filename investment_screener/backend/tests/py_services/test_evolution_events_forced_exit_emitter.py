"""Test emit_forced_exit_event function (Task 7)."""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
PY_SERVICES = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(PY_SERVICES))

from evolution_events import (  # noqa: E402
    emit_forced_exit_event,
    load_events,
)


class TestEmitForcedExitEvent:
    """Test forced exit event emission."""

    def test_emit_stop_loss_exit(self, tmp_path, monkeypatch):
        import evolution_events

        events_path = tmp_path / "evolution_events.jsonl"
        monkeypatch.setattr(evolution_events, "EVOLUTION_EVENTS_PATH", events_path)

        emit_forced_exit_event(
            ticker="CORZ",
            exit_price=9.50,
            exit_date="2026-01-15",
            exit_reason="stop_loss",
            stop_loss_price=9.50,
            entry_price=12.0,
            shares=100,
        )

        events = load_events(events_path)
        assert len(events) == 1
        assert events[0]["context"]["ticker"] == "CORZ"
        assert events[0]["event_details"]["exit_price"] == 9.50
        assert events[0]["event_details"]["exit_reason"] == "stop_loss"
        assert abs(events[0]["event_details"]["realized_loss_pct"] - (-20.833333333333332)) < 0.01

    def test_emit_manual_exit(self, tmp_path, monkeypatch):
        import evolution_events

        events_path = tmp_path / "evolution_events.jsonl"
        monkeypatch.setattr(evolution_events, "EVOLUTION_EVENTS_PATH", events_path)

        emit_forced_exit_event(
            ticker="AAPL",
            exit_price=160.0,
            exit_date="2026-01-20",
            exit_reason="manual_exit",
            entry_price=150.0,
            shares=50,
        )

        events = load_events(events_path)
        assert len(events) == 1
        assert events[0]["event_details"]["exit_reason"] == "manual_exit"
        assert abs(events[0]["event_details"]["realized_loss_pct"] - 6.666666666666666) < 0.01

    def test_emit_thesis_breach_exit(self, tmp_path, monkeypatch):
        import evolution_events

        events_path = tmp_path / "evolution_events.jsonl"
        monkeypatch.setattr(evolution_events, "EVOLUTION_EVENTS_PATH", events_path)

        emit_forced_exit_event(
            ticker="TSLA",
            exit_price=200.0,
            exit_date="2026-02-01",
            exit_reason="thesis_breach",
            entry_price=250.0,
            shares=25,
        )

        events = load_events(events_path)
        assert len(events) == 1
        assert events[0]["event_details"]["exit_reason"] == "thesis_breach"
        assert events[0]["event_details"]["realized_loss_pct"] == -20.0

    def test_emit_profitable_exit(self, tmp_path, monkeypatch):
        import evolution_events

        events_path = tmp_path / "evolution_events.jsonl"
        monkeypatch.setattr(evolution_events, "EVOLUTION_EVENTS_PATH", events_path)

        emit_forced_exit_event(
            ticker="NVDA",
            exit_price=950.0,
            exit_date="2026-01-25",
            exit_reason="target_reached",
            entry_price=800.0,
            shares=10,
        )

        events = load_events(events_path)
        assert events[0]["event_details"]["realized_loss_pct"] == 18.75

    def test_event_id_format(self, tmp_path, monkeypatch):
        import evolution_events

        events_path = tmp_path / "evolution_events.jsonl"
        monkeypatch.setattr(evolution_events, "EVOLUTION_EVENTS_PATH", events_path)

        emit_forced_exit_event(
            ticker="MSFT",
            exit_price=320.0,
            exit_date="2026-02-05",
            exit_reason="manual_exit",
        )

        events = load_events(events_path)
        assert events[0]["event_id"] == "MSFT:forced_exit:2026-02-05"

    def test_non_blocking_on_error(self, tmp_path, monkeypatch):
        import evolution_events

        monkeypatch.setattr(evolution_events, "EVOLUTION_EVENTS_PATH", Path("/invalid/path"))

        # Should not raise
        emit_forced_exit_event(
            ticker="AAPL",
            exit_price=150.0,
            exit_date="2026-01-10",
            exit_reason="manual_exit",
        )

    def test_dedup_on_same_ticker_type_date(self, tmp_path, monkeypatch):
        import evolution_events

        events_path = tmp_path / "evolution_events.jsonl"
        monkeypatch.setattr(evolution_events, "EVOLUTION_EVENTS_PATH", events_path)

        # First exit
        emit_forced_exit_event(
            ticker="AAPL",
            exit_price=150.0,
            exit_date="2026-01-15",
            exit_reason="stop_loss",
        )

        # Same date but different exit price
        emit_forced_exit_event(
            ticker="AAPL",
            exit_price=151.0,  # Different exit price
            exit_date="2026-01-15",
            exit_reason="stop_loss",
        )

        events = load_events(events_path)
        # Should append second one (details changed)
        assert len(events) == 2

    def test_exit_without_entry_price(self, tmp_path, monkeypatch):
        import evolution_events

        events_path = tmp_path / "evolution_events.jsonl"
        monkeypatch.setattr(evolution_events, "EVOLUTION_EVENTS_PATH", events_path)

        emit_forced_exit_event(
            ticker="AAPL",
            exit_price=150.0,
            exit_date="2026-01-15",
            exit_reason="manual_exit",
        )

        events = load_events(events_path)
        assert events[0]["event_details"]["realized_loss_pct"] is None
        assert events[0]["context"]["entry_price"] is None

    def test_exit_with_full_position_context(self, tmp_path, monkeypatch):
        import evolution_events

        events_path = tmp_path / "evolution_events.jsonl"
        monkeypatch.setattr(evolution_events, "EVOLUTION_EVENTS_PATH", events_path)

        emit_forced_exit_event(
            ticker="CORZ",
            exit_price=9.50,
            exit_date="2026-01-15",
            exit_reason="stop_loss",
            stop_loss_price=9.50,
            entry_price=12.0,
            shares=100,
        )

        events = load_events(events_path)
        assert events[0]["context"]["entry_price"] == 12.0
        assert events[0]["context"]["shares"] == 100
        assert events[0]["event_details"]["stop_loss_price"] == 9.50
