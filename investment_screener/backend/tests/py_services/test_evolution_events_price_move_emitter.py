"""Test emit_price_move_event function (Task 5)."""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
PY_SERVICES = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(PY_SERVICES))

from evolution_events import (  # noqa: E402
    emit_price_move_event,
    load_events,
)


class TestEmitPriceMoveEvent:
    """Test large price move event emission."""

    def test_emit_positive_move(self, tmp_path, monkeypatch):
        import evolution_events

        events_path = tmp_path / "evolution_events.jsonl"
        monkeypatch.setattr(evolution_events, "EVOLUTION_EVENTS_PATH", events_path)

        emit_price_move_event(
            ticker="AAPL",
            move_pct=7.5,
            move_date="2026-01-10",
            prior_price=150.0,
            current_price=161.25,
        )

        events = load_events(events_path)
        assert len(events) == 1
        assert events[0]["context"]["ticker"] == "AAPL"
        assert events[0]["event_details"]["move_pct"] == 7.5
        assert events[0]["event_details"]["prior_price"] == 150.0
        assert events[0]["context"]["current_price"] == 161.25

    def test_emit_negative_move(self, tmp_path, monkeypatch):
        import evolution_events

        events_path = tmp_path / "evolution_events.jsonl"
        monkeypatch.setattr(evolution_events, "EVOLUTION_EVENTS_PATH", events_path)

        emit_price_move_event(
            ticker="MSFT",
            move_pct=-6.0,
            move_date="2026-01-12",
            current_price=300.8,
        )

        events = load_events(events_path)
        assert len(events) == 1
        assert events[0]["event_details"]["move_pct"] == -6.0

    def test_emit_with_ta_signal(self, tmp_path, monkeypatch):
        import evolution_events

        events_path = tmp_path / "evolution_events.jsonl"
        monkeypatch.setattr(evolution_events, "EVOLUTION_EVENTS_PATH", events_path)

        emit_price_move_event(
            ticker="NVDA",
            move_pct=8.2,
            move_date="2026-01-15",
            ta_signal="RSI_OVERBOUGHT",
            current_price=920.0,
        )

        events = load_events(events_path)
        assert events[0]["event_details"]["ta_signal"] == "RSI_OVERBOUGHT"

    def test_emit_with_adx_signal(self, tmp_path, monkeypatch):
        import evolution_events

        events_path = tmp_path / "evolution_events.jsonl"
        monkeypatch.setattr(evolution_events, "EVOLUTION_EVENTS_PATH", events_path)

        emit_price_move_event(
            ticker="TSLA",
            move_pct=-5.1,
            move_date="2026-01-18",
            ta_signal="ADX_STRONG_DOWNTREND",
        )

        events = load_events(events_path)
        assert events[0]["event_details"]["ta_signal"] == "ADX_STRONG_DOWNTREND"

    def test_event_id_format(self, tmp_path, monkeypatch):
        import evolution_events

        events_path = tmp_path / "evolution_events.jsonl"
        monkeypatch.setattr(evolution_events, "EVOLUTION_EVENTS_PATH", events_path)

        emit_price_move_event(
            ticker="CORZ",
            move_pct=5.5,
            move_date="2026-02-01",
        )

        events = load_events(events_path)
        assert events[0]["event_id"] == "CORZ:large_price_move:2026-02-01"

    def test_non_blocking_on_error(self, tmp_path, monkeypatch):
        import evolution_events

        monkeypatch.setattr(evolution_events, "EVOLUTION_EVENTS_PATH", Path("/invalid/path"))

        # Should not raise
        emit_price_move_event(
            ticker="AAPL",
            move_pct=5.0,
            move_date="2026-01-10",
        )

    def test_dedup_on_same_ticker_type_date(self, tmp_path, monkeypatch):
        import evolution_events

        events_path = tmp_path / "evolution_events.jsonl"
        monkeypatch.setattr(evolution_events, "EVOLUTION_EVENTS_PATH", events_path)

        # First move
        emit_price_move_event(
            ticker="AAPL",
            move_pct=5.0,
            move_date="2026-01-10",
            ta_signal="RSI_OVERBOUGHT",
        )

        # Same date but different move
        emit_price_move_event(
            ticker="AAPL",
            move_pct=5.2,  # Different move percentage
            move_date="2026-01-10",
            ta_signal="RSI_OVERBOUGHT",
        )

        events = load_events(events_path)
        # Should append second one (details changed)
        assert len(events) == 2

    def test_with_position_context(self, tmp_path, monkeypatch):
        import evolution_events

        events_path = tmp_path / "evolution_events.jsonl"
        monkeypatch.setattr(evolution_events, "EVOLUTION_EVENTS_PATH", events_path)

        emit_price_move_event(
            ticker="AAPL",
            move_pct=7.0,
            move_date="2026-01-10",
            current_price=160.5,
            entry_price=150.0,
            shares=100,
        )

        events = load_events(events_path)
        assert events[0]["context"]["entry_price"] == 150.0
        assert events[0]["context"]["shares"] == 100
