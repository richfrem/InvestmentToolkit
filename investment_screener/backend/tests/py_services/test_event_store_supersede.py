"""Tests for ``intelligence.event_store.append_or_supersede_event``.

A same-key re-write with a *different* payload must land as a correction that
supersedes the earlier event, instead of being silently dropped by idempotency.
Uses a real temporary ledger database (no mocking).
"""

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))

from intelligence.db_client import initialize_db  # noqa: E402
from intelligence.event_store import append_or_supersede_event  # noqa: E402

KEY = "ta-sweep-AAPL-2026-10-04"


@pytest.fixture
def conn(tmp_path):
    connection = initialize_db(str(tmp_path / "intelligence.sqlite"))
    yield connection
    connection.close()


def _write(conn, payload):
    return append_or_supersede_event(
        conn,
        event_type="TECHNICAL_SWEEP",
        effective_at="2026-10-04",
        status="ACTIVE",
        title="TA Sweep for AAPL",
        body_markdown="Batch technical indicators for AAPL.",
        ticker="AAPL",
        source_id="tradingview-cdp",
        payload=payload,
        idempotency_key=KEY,
    )


def _records(conn):
    return conn.execute(
        "SELECT event_id, idempotency_key, supersedes_event_id, event_sequence, status, payload_json "
        "FROM intelligence_event ORDER BY event_sequence;"
    ).fetchall()


def test_first_write_appends_plain_event(conn):
    event_id = _write(conn, {"ticker": "AAPL", "close": 195.13})
    records = _records(conn)
    assert [r[0] for r in records] == [event_id]
    assert records[0][1] == KEY
    assert records[0][2] is None


def test_identical_payload_is_a_no_op(conn):
    first = _write(conn, {"ticker": "AAPL", "close": 195.13})
    second = _write(conn, {"ticker": "AAPL", "close": 195.13})
    assert second == first
    assert len(_records(conn)) == 1


def test_changed_payload_supersedes_latest_event_in_chain(conn):
    first = _write(conn, {"ticker": "AAPL", "close": 195.13})
    second = _write(conn, {"ticker": "AAPL", "close": 255.40})
    third = _write(conn, {"ticker": "AAPL", "close": 256.10})

    records = _records(conn)
    assert [r[0] for r in records] == [first, second, third]
    assert [r[2] for r in records] == [None, first, second]
    assert len({r[1] for r in records}) == 3
    assert [r[3] for r in records] == [1, 2, 3]


def test_only_the_latest_correction_stays_active(conn):
    _write(conn, {"ticker": "AAPL", "close": 195.13})
    _write(conn, {"ticker": "AAPL", "close": 255.40})
    records = _records(conn)
    assert [r[4] for r in records] == ["SUPERSEDED", "ACTIVE"]
    assert json.loads(records[1][5])["close"] == 255.40
