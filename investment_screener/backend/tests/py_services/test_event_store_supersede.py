"""Tests for ``intelligence.event_store.append_or_supersede_event``.

A same-key re-write with a *different* payload must land as a correction that
supersedes the earlier event, instead of being silently dropped by idempotency.
Uses a real ledger file and a real SQLite read-model (no mocking).
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))

from intelligence.db_client import initialize_db  # noqa: E402
from intelligence.event_store import append_or_supersede_event  # noqa: E402
from intelligence.replay_ledger import replay_events_to_db  # noqa: E402

KEY = "ta-sweep-AAPL-2026-10-04"


def _write(jsonl_path, payload):
    return append_or_supersede_event(
        str(jsonl_path),
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


def _records(jsonl_path):
    return [json.loads(line) for line in jsonl_path.read_text().splitlines() if line.strip()]


def test_first_write_appends_plain_event(tmp_path):
    jsonl_path = tmp_path / "observations.jsonl"
    event_id = _write(jsonl_path, {"ticker": "AAPL", "close": 195.13})
    records = _records(jsonl_path)
    assert [r["event_id"] for r in records] == [event_id]
    assert records[0]["idempotency_key"] == KEY
    assert records[0]["supersedes_event_id"] is None


def test_identical_payload_is_a_no_op(tmp_path):
    jsonl_path = tmp_path / "observations.jsonl"
    first = _write(jsonl_path, {"ticker": "AAPL", "close": 195.13})
    second = _write(jsonl_path, {"ticker": "AAPL", "close": 195.13})
    assert second == first
    assert len(_records(jsonl_path)) == 1


def test_changed_payload_supersedes_latest_event_in_chain(tmp_path):
    jsonl_path = tmp_path / "observations.jsonl"
    first = _write(jsonl_path, {"ticker": "AAPL", "close": 195.13})
    second = _write(jsonl_path, {"ticker": "AAPL", "close": 255.40})
    third = _write(jsonl_path, {"ticker": "AAPL", "close": 256.10})

    records = _records(jsonl_path)
    assert [r["event_id"] for r in records] == [first, second, third]
    assert [r["supersedes_event_id"] for r in records] == [None, first, second]
    assert len({r["idempotency_key"] for r in records}) == 3
    assert [r["event_sequence"] for r in records] == [1, 2, 3]


def test_replay_leaves_only_the_correction_active(tmp_path):
    jsonl_path = tmp_path / "observations.jsonl"
    db_path = tmp_path / "intelligence.sqlite"
    conn = initialize_db(str(db_path))
    conn.execute("INSERT INTO instrument VALUES ('us-aapl', 'AAPL', 'NASDAQ', 'Apple', '2026-07-18', NULL);")
    conn.commit()

    _write(jsonl_path, {"ticker": "AAPL", "close": 195.13})
    replay_events_to_db(str(jsonl_path), conn)
    _write(jsonl_path, {"ticker": "AAPL", "close": 255.40})
    replay_events_to_db(str(jsonl_path), conn)

    rows = conn.execute(
        "SELECT status, payload_json FROM intelligence_event ORDER BY event_sequence;"
    ).fetchall()
    conn.close()
    assert [r[0] for r in rows] == ["SUPERSEDED", "ACTIVE"]
    assert json.loads(rows[1][1])["close"] == 255.40
