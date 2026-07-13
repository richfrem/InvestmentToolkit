"""Test evolution_events.py schema round-trips to/from JSONL (Task 1)."""
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
PY_SERVICES = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(PY_SERVICES))

from evolution_events import (  # noqa: E402
    EventType,
    EarningsGrade,
    _make_evolution_event,
    _make_event_context,
    _make_event_outcome,
    _append_jsonl,
    _load_jsonl,
)


class TestEventContext:
    """Test context sub-model creation."""

    def test_context_creation(self):
        ctx = _make_event_context(
            ticker="AAPL",
            event_type=EventType.EARNINGS_CATALYST,
            event_date="2026-01-01",
            entry_price=150.0,
            shares=10,
            current_price=155.0,
        )
        assert ctx["ticker"] == "AAPL"
        assert ctx["event_type"] == "earnings_catalyst"
        assert ctx["event_date"] == "2026-01-01"
        assert ctx["entry_price"] == 150.0
        assert ctx["shares"] == 10
        assert ctx["current_price"] == 155.0

    def test_context_nullable_fields(self):
        ctx = _make_event_context(
            ticker="AAPL",
            event_type=EventType.EARNINGS_CATALYST,
            event_date="2026-01-01",
        )
        assert ctx["entry_price"] is None
        assert ctx["shares"] is None
        assert ctx["current_price"] is None


class TestEventOutcome:
    """Test outcome sub-model creation."""

    def test_outcome_creation_null_fields(self):
        outcome = _make_event_outcome()
        assert outcome["outcome_seven_day"] is None
        assert outcome["outcome_thirty_day"] is None
        assert outcome["seven_day_price"] is None
        assert outcome["thirty_day_price"] is None

    def test_outcome_with_values(self):
        outcome = _make_event_outcome(
            outcome_seven_day=5.2,
            outcome_thirty_day=8.1,
            seven_day_price=160.0,
            thirty_day_price=165.0,
        )
        assert outcome["outcome_seven_day"] == 5.2
        assert outcome["outcome_thirty_day"] == 8.1
        assert outcome["seven_day_price"] == 160.0
        assert outcome["thirty_day_price"] == 165.0


class TestEvolutionEvent:
    """Test complete event record creation."""

    def test_event_creation(self):
        event = _make_evolution_event(
            ticker="AAPL",
            event_type=EventType.EARNINGS_CATALYST,
            event_date="2026-01-01",
            context={"test": "value"},
            event_details={"grade": "beat"},
            entry_price=150.0,
            current_price=155.0,
        )
        assert event["event_id"] == "AAPL:earnings_catalyst:2026-01-01"
        assert event["context"]["ticker"] == "AAPL"
        assert event["event_details"]["grade"] == "beat"
        assert "timestamp" in event
        assert event["outcome"]["outcome_seven_day"] is None

    def test_event_id_format(self):
        event = _make_evolution_event(
            ticker="TSLA",
            event_type=EventType.DIVIDEND_EVENT,
            event_date="2026-07-10",
            context={},
            event_details={},
        )
        assert event["event_id"] == "TSLA:dividend_event:2026-07-10"


class TestJSONLRoundTrip:
    """Test JSONL append and load round-trip."""

    def test_append_and_load_single_event(self, tmp_path):
        path = tmp_path / "events.jsonl"
        event = _make_evolution_event(
            ticker="AAPL",
            event_type=EventType.EARNINGS_CATALYST,
            event_date="2026-01-01",
            context={},
            event_details={"grade": "beat"},
        )
        _append_jsonl(event, path)
        loaded = _load_jsonl(path)

        assert len(loaded) == 1
        assert loaded[0]["event_id"] == event["event_id"]
        assert loaded[0]["event_details"]["grade"] == "beat"

    def test_append_multiple_without_truncate(self, tmp_path):
        path = tmp_path / "events.jsonl"
        event1 = _make_evolution_event(
            ticker="AAPL",
            event_type=EventType.EARNINGS_CATALYST,
            event_date="2026-01-01",
            context={},
            event_details={"grade": "beat"},
        )
        event2 = _make_evolution_event(
            ticker="TSLA",
            event_type=EventType.DIVIDEND_EVENT,
            event_date="2026-01-02",
            context={},
            event_details={"dividend_amount": 0.5},
        )
        _append_jsonl(event1, path)
        _append_jsonl(event2, path)
        loaded = _load_jsonl(path)

        assert len(loaded) == 2
        assert loaded[0]["event_id"] == "AAPL:earnings_catalyst:2026-01-01"
        assert loaded[1]["event_id"] == "TSLA:dividend_event:2026-01-02"

    def test_load_missing_file_returns_empty_list(self, tmp_path):
        path = tmp_path / "does_not_exist.jsonl"
        assert _load_jsonl(path) == []

    def test_jsonl_preserves_nested_structures(self, tmp_path):
        path = tmp_path / "events.jsonl"
        event = _make_evolution_event(
            ticker="CORZ",
            event_type=EventType.REBALANCE_EXECUTION,
            event_date="2026-05-15",
            context={},
            event_details={
                "order_type": "buy",
                "order_quantity": 50,
                "order_price": 10.5,
            },
            entry_price=10.0,
            shares=100.0,
        )
        _append_jsonl(event, path)
        loaded = _load_jsonl(path)

        assert loaded[0]["event_details"]["order_type"] == "buy"
        assert loaded[0]["event_details"]["order_quantity"] == 50
        assert loaded[0]["context"]["entry_price"] == 10.0
        assert loaded[0]["context"]["shares"] == 100.0

    def test_jsonl_handles_null_values(self, tmp_path):
        path = tmp_path / "events.jsonl"
        event = _make_evolution_event(
            ticker="AAPL",
            event_type=EventType.EARNINGS_CATALYST,
            event_date="2026-01-01",
            context={},
            event_details={"grade": "beat", "surprise_pct": None},
        )
        _append_jsonl(event, path)
        loaded = _load_jsonl(path)

        assert loaded[0]["event_details"]["surprise_pct"] is None
        assert loaded[0]["outcome"]["outcome_seven_day"] is None


class TestEventTypeEnum:
    """Test EventType enum."""

    def test_all_event_types_present(self):
        expected = [
            "earnings_catalyst",
            "thesis_breaker_override",
            "rebalance_execution",
            "large_price_move",
            "dividend_event",
            "forced_exit",
        ]
        actual = [e.value for e in EventType]
        assert set(actual) == set(expected)


class TestEarningsGradeEnum:
    """Test EarningsGrade enum."""

    def test_all_grades_present(self):
        expected = ["beat", "miss", "in_line"]
        actual = [g.value for g in EarningsGrade]
        assert set(actual) == set(expected)
