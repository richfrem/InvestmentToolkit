"""Tests for ``intelligence.event_store.append_event`` against a real temporary ledger database."""
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from intelligence.db_client import initialize_db  # noqa: E402
from intelligence.event_store import append_event  # noqa: E402


@pytest.fixture
def conn(tmp_path):
    connection = initialize_db(str(tmp_path / "intelligence.sqlite"))
    yield connection
    connection.close()


def _rows(conn):
    conn.row_factory = None
    return conn.execute(
        "SELECT event_id, event_sequence, instrument_id, status, content_hash FROM intelligence_event "
        "ORDER BY event_sequence;"
    ).fetchall()


def test_append_event_assigns_incrementing_sequence(conn):
    id_1 = append_event(
        conn, event_type="NEWS_SWEEP", effective_at="2026-07-18",
        status="ACTIVE", title="First", body_markdown="Body 1", ticker="PLTR",
    )
    id_2 = append_event(
        conn, event_type="NEWS_SWEEP", effective_at="2026-07-18",
        status="ACTIVE", title="Second", body_markdown="Body 2", ticker="PLTR",
    )
    rows = _rows(conn)
    assert [r[0] for r in rows] == [id_1, id_2]
    assert [r[1] for r in rows] == [1, 2]
    assert rows[0][4] != rows[1][4]


def test_append_event_resolves_the_ticker_to_an_instrument(conn):
    append_event(
        conn, event_type="NEWS_SWEEP", effective_at="2026-07-18",
        status="ACTIVE", title="One", body_markdown="B", ticker="PLTR",
    )
    append_event(
        conn, event_type="MACRO_EVENT", effective_at="2026-07-18",
        status="ACTIVE", title="Macro", body_markdown="B",
    )
    rows = _rows(conn)
    assert rows[0][2] is not None and "pltr" in rows[0][2]
    assert rows[1][2] is None


def test_append_event_idempotency_key_dedups(conn):
    id_1 = append_event(
        conn, event_type="NEWS_SWEEP", effective_at="2026-07-18",
        status="ACTIVE", title="First", body_markdown="Body 1", ticker="PLTR",
        idempotency_key="dedup-key-1",
    )
    id_2 = append_event(
        conn, event_type="NEWS_SWEEP", effective_at="2026-07-18",
        status="ACTIVE", title="First (retry)", body_markdown="Body 1", ticker="PLTR",
        idempotency_key="dedup-key-1",
    )
    assert len(_rows(conn)) == 1
    assert id_1 == id_2


def test_append_event_stores_the_payload_as_json(conn):
    event_id = append_event(
        conn, event_type="TECHNICAL_SWEEP", effective_at="2026-07-18", status="ACTIVE",
        title="TA", body_markdown="B", ticker="PLTR", payload={"close": 12.5},
    )
    stored = conn.execute("SELECT payload_json FROM intelligence_event WHERE event_id = ?;", (event_id,)).fetchone()[0]
    assert json.loads(stored) == {"close": 12.5}


def test_append_event_rejects_an_invalid_event_type(conn):
    with pytest.raises(ValueError):
        append_event(
            conn, event_type="NOT_A_TYPE", effective_at="2026-07-18",
            status="ACTIVE", title="Bad", body_markdown="B",
        )
    assert _rows(conn) == []


def test_a_superseding_event_marks_the_earlier_one_superseded(conn):
    first = append_event(
        conn, event_type="NEWS_SWEEP", effective_at="2026-07-18",
        status="ACTIVE", title="Old", body_markdown="B", ticker="PLTR",
    )
    append_event(
        conn, event_type="NEWS_SWEEP", effective_at="2026-07-18",
        status="ACTIVE", title="New", body_markdown="B2", ticker="PLTR",
        supersedes_event_id=first,
    )
    assert [r[3] for r in _rows(conn)] == ["SUPERSEDED", "ACTIVE"]
