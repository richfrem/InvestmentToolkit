"""Tests for import_ledger_jsonl.py (old ledger JSONL -> intelligence.sqlite) on real temporary files."""
import json
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))

from intelligence.db_client import initialize_db  # noqa: E402
from intelligence.event_store import append_event  # noqa: E402
from import_ledger_jsonl import import_jsonl  # noqa: E402


def _event(n, ticker="STM", key=None, **extra):
    return {
        "event_id": f"evt_{n}", "event_sequence": 1, "ticker": ticker, "event_type": "TECHNICAL_SWEEP",
        "effective_at": "2026-08-24", "ingested_at": "2026-08-24T02:32:44Z", "source_id": "tradingview-cdp",
        "status": "ACTIVE", "title": f"TA Sweep {n}", "body_markdown": f"body {n}",
        "payload_json": json.dumps({"ticker": ticker, "close": n}), "supersedes_event_id": None,
        "idempotency_key": key or f"ta-sweep-{ticker}-{n}", "content_hash": f"hash{n}", **extra,
    }


def _write(path, events):
    path.write_text("\n".join(json.dumps(e) for e in events) + "\n")


def _rows(db_path):
    conn = sqlite3.connect(str(db_path))
    rows = conn.execute(
        "SELECT event_id, event_sequence, instrument_id, ingested_at, content_hash FROM intelligence_event ORDER BY event_sequence;"
    ).fetchall()
    conn.close()
    return rows


def test_dry_run_reports_without_writing_or_creating_the_database(tmp_path):
    jsonl, db = tmp_path / "old.jsonl", tmp_path / "intelligence.sqlite"
    _write(jsonl, [_event(1), _event(2)])
    report = import_jsonl(jsonl, db, dry_run=True)
    assert report == {"lines": 2, "already_present": 0, "to_import": 2, "imported": 0, "rejected": []}
    assert not db.exists()


def test_write_imports_missing_events_keeping_their_identity(tmp_path):
    jsonl, db = tmp_path / "old.jsonl", tmp_path / "intelligence.sqlite"
    _write(jsonl, [_event(1), _event(2)])
    report = import_jsonl(jsonl, db, dry_run=False)
    assert report["imported"] == 2 and report["rejected"] == []
    rows = _rows(db)
    assert [r[0] for r in rows] == ["evt_1", "evt_2"]
    assert [r[1] for r in rows] == [1, 2]
    assert all(r[2] and "stm" in r[2] for r in rows)
    assert rows[0][3] == "2026-08-24T02:32:44Z" and rows[0][4] == "hash1"


def test_events_already_in_the_ledger_are_left_alone_and_a_rerun_adds_nothing(tmp_path):
    jsonl, db = tmp_path / "old.jsonl", tmp_path / "intelligence.sqlite"
    conn = initialize_db(str(db))
    append_event(
        conn, event_type="TECHNICAL_SWEEP", effective_at="2026-08-24", status="ACTIVE", title="t",
        body_markdown="b", ticker="STM", idempotency_key="ta-sweep-STM-1",
    )
    conn.close()
    _write(jsonl, [_event(1), _event(2)])
    first = import_jsonl(jsonl, db, dry_run=False)
    second = import_jsonl(jsonl, db, dry_run=False)
    assert first["already_present"] == 1 and first["imported"] == 1
    assert second["already_present"] == 2 and second["imported"] == 0
    assert len(_rows(db)) == 2


def test_an_event_with_an_invalid_type_is_reported_not_imported(tmp_path):
    jsonl, db = tmp_path / "old.jsonl", tmp_path / "intelligence.sqlite"
    _write(jsonl, [_event(1), _event(2, event_type="NOT_A_TYPE")])
    report = import_jsonl(jsonl, db, dry_run=False)
    assert report["imported"] == 1 and report["rejected"] == ["evt_2"]


def test_a_missing_file_reports_nothing_to_do(tmp_path):
    assert import_jsonl(tmp_path / "none.jsonl", tmp_path / "x.sqlite")["lines"] == 0
