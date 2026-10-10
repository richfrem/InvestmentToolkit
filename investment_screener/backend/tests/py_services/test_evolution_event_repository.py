"""Tests for evolution_event_repository.py and the breaker override log against a real temporary database."""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))

from domain_model.db_client import initialize_db  # noqa: E402
from domain_model import evolution_event_repository as events  # noqa: E402
from domain_model import thesis_breaker_repository as breakers  # noqa: E402


@pytest.fixture
def conn(tmp_path):
    connection = initialize_db(str(tmp_path / "domain_model.sqlite"))
    yield connection
    connection.close()


def _record(ticker="AAPL", event_type="earnings_catalyst", event_date="2026-01-15", detail="beat"):
    return {
        "event_id": f"{ticker}:{event_type}:{event_date}",
        "context": {"ticker": ticker, "event_type": event_type, "event_date": event_date},
        "event_details": {"grade": detail},
        "outcome": {"outcome_seven_day": None},
    }


def test_events_come_back_oldest_first(conn):
    events.insert_event(conn, _record("AAPL"))
    events.insert_event(conn, _record("TSLA", "dividend_event", "2026-01-16"))
    assert [e["event_id"] for e in events.list_events(conn)] == [
        "AAPL:earnings_catalyst:2026-01-15", "TSLA:dividend_event:2026-01-16",
    ]


def test_the_same_key_can_be_stored_again_when_the_details_change(conn):
    events.insert_event(conn, _record(detail="beat"))
    events.insert_event(conn, _record(detail="miss"))
    assert [e["event_details"]["grade"] for e in events.list_events(conn)] == ["beat", "miss"]


def test_an_outcome_can_be_filled_in_later(conn):
    seq = events.insert_event(conn, _record())
    record = events.list_events(conn)[0]
    record["outcome"]["outcome_seven_day"] = 4.2
    events.update_event(conn, seq, record)
    assert events.list_events(conn)[0]["outcome"]["outcome_seven_day"] == 4.2
    assert [s for s, _ in events.list_events_with_seq(conn)] == [seq]


def test_breaker_overrides_are_appended_in_order_and_filterable_by_ticker(conn):
    breakers.insert_override(conn, {"ticker": "NBIS", "breakerId": "a", "date": "2026-10-01", "rationale": "first"})
    breakers.insert_override(conn, {"ticker": "PANW", "breakerId": "b", "date": "2026-10-02", "rationale": "second"})
    assert [o["rationale"] for o in breakers.list_overrides(conn)] == ["first", "second"]
    assert [o["ticker"] for o in breakers.list_overrides(conn, "PANW")] == ["PANW"]
