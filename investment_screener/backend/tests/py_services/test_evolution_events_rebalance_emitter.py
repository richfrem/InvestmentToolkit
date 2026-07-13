"""Test emit_rebalance_event function (Task 4)."""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
PY_SERVICES = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(PY_SERVICES))

from evolution_events import (  # noqa: E402
    emit_rebalance_event,
    load_events,
)


class TestEmitRebalanceEvent:
    """Test rebalance execution event emission."""

    def test_emit_buy_order(self, tmp_path, monkeypatch):
        import evolution_events

        events_path = tmp_path / "evolution_events.jsonl"
        monkeypatch.setattr(evolution_events, "EVOLUTION_EVENTS_PATH", events_path)

        emit_rebalance_event(
            ticker="AAPL",
            order_type="buy",
            order_quantity=50,
            order_price=150.0,
            rebalance_date="2026-01-10",
            trade_id="TRD-001",
        )

        events = load_events(events_path)
        assert len(events) == 1
        assert events[0]["context"]["ticker"] == "AAPL"
        assert events[0]["event_details"]["order_type"] == "buy"
        assert events[0]["event_details"]["order_quantity"] == 50
        assert events[0]["event_details"]["order_price"] == 150.0
        assert events[0]["event_details"]["trade_id"] == "TRD-001"

    def test_emit_sell_order(self, tmp_path, monkeypatch):
        import evolution_events

        events_path = tmp_path / "evolution_events.jsonl"
        monkeypatch.setattr(evolution_events, "EVOLUTION_EVENTS_PATH", events_path)

        emit_rebalance_event(
            ticker="MSFT",
            order_type="sell",
            order_quantity=25,
            order_price=320.0,
            rebalance_date="2026-01-12",
            trade_id="TRD-002",
            current_price=320.0,
        )

        events = load_events(events_path)
        assert len(events) == 1
        assert events[0]["event_details"]["order_type"] == "sell"
        assert events[0]["event_details"]["order_quantity"] == 25
        assert events[0]["context"]["current_price"] == 320.0

    def test_emit_with_position_context(self, tmp_path, monkeypatch):
        import evolution_events

        events_path = tmp_path / "evolution_events.jsonl"
        monkeypatch.setattr(evolution_events, "EVOLUTION_EVENTS_PATH", events_path)

        emit_rebalance_event(
            ticker="NVDA",
            order_type="buy",
            order_quantity=10,
            order_price=850.0,
            rebalance_date="2026-01-15",
            current_price=850.0,
            entry_price=800.0,
            shares=50,
        )

        events = load_events(events_path)
        assert events[0]["context"]["entry_price"] == 800.0
        assert events[0]["context"]["shares"] == 50

    def test_event_id_format(self, tmp_path, monkeypatch):
        import evolution_events

        events_path = tmp_path / "evolution_events.jsonl"
        monkeypatch.setattr(evolution_events, "EVOLUTION_EVENTS_PATH", events_path)

        emit_rebalance_event(
            ticker="TSLA",
            order_type="buy",
            order_quantity=5,
            order_price=245.0,
            rebalance_date="2026-02-01",
        )

        events = load_events(events_path)
        assert events[0]["event_id"] == "TSLA:rebalance_execution:2026-02-01"

    def test_non_blocking_on_error(self, tmp_path, monkeypatch):
        import evolution_events

        monkeypatch.setattr(evolution_events, "EVOLUTION_EVENTS_PATH", Path("/invalid/path"))

        # Should not raise
        emit_rebalance_event(
            ticker="AAPL",
            order_type="buy",
            order_quantity=10,
            order_price=150.0,
            rebalance_date="2026-01-10",
        )

    def test_dedup_on_same_ticker_type_date(self, tmp_path, monkeypatch):
        import evolution_events

        events_path = tmp_path / "evolution_events.jsonl"
        monkeypatch.setattr(evolution_events, "EVOLUTION_EVENTS_PATH", events_path)

        # First order
        emit_rebalance_event(
            ticker="AAPL",
            order_type="buy",
            order_quantity=50,
            order_price=150.0,
            rebalance_date="2026-01-10",
        )

        # Same date but different quantity
        emit_rebalance_event(
            ticker="AAPL",
            order_type="buy",
            order_quantity=75,  # Different quantity
            order_price=150.0,
            rebalance_date="2026-01-10",
        )

        events = load_events(events_path)
        # Should append second one (details changed)
        assert len(events) == 2

    def test_fractional_shares(self, tmp_path, monkeypatch):
        import evolution_events

        events_path = tmp_path / "evolution_events.jsonl"
        monkeypatch.setattr(evolution_events, "EVOLUTION_EVENTS_PATH", events_path)

        emit_rebalance_event(
            ticker="AAPL",
            order_type="buy",
            order_quantity=2.5,  # Fractional
            order_price=150.0,
            rebalance_date="2026-01-10",
        )

        events = load_events(events_path)
        assert events[0]["event_details"]["order_quantity"] == 2.5
