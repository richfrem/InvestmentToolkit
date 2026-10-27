import json
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))
sys.path.insert(0, str(REPO_ROOT / "plugins/portfolio-advisor/scripts"))


def _seed_db(db_path: Path) -> None:
    from intelligence.db_client import initialize_db
    from intelligence.event_repository import insert_event

    conn = initialize_db(str(db_path))
    insert_event(conn, {
        "event_id": "evt_1", "event_sequence": 1, "instrument_id": None,
        "event_type": "REVIEW_DAILY", "effective_at": "2026-07-22",
        "observed_at": None, "ingested_at": "2026-07-22T10:00:00Z",
        "source_id": "daily_brief", "confidence_score": None, "status": "ACTIVE",
        "title": "Daily Brief for 2026-07-22", "body_markdown": "x",
        "payload_json": json.dumps({"date": "2026-07-22", "macro_regime": {"regime": "BULL"}}),
        "supersedes_event_id": None, "idempotency_key": "daily-brief-2026-07-22",
        "content_hash": "h1",
    })
    insert_event(conn, {
        "event_id": "evt_2", "event_sequence": 2, "instrument_id": None,
        "event_type": "REVIEW_DAILY", "effective_at": "2026-07-23",
        "observed_at": None, "ingested_at": "2026-07-23T10:00:00Z",
        "source_id": "daily_brief", "confidence_score": None, "status": "ACTIVE",
        "title": "Daily Brief for 2026-07-23", "body_markdown": "x",
        "payload_json": json.dumps({"date": "2026-07-23", "macro_regime": {"regime": "CONGESTION"}}),
        "supersedes_event_id": None, "idempotency_key": "daily-brief-2026-07-23",
        "content_hash": "h2",
    })
    conn.commit()
    conn.close()


def test_load_latest_brief_reads_from_ledger_not_json_glob(tmp_path, monkeypatch):
    import generate_reports

    db_path = tmp_path / "intelligence.sqlite"
    _seed_db(db_path)
    monkeypatch.setattr(generate_reports, "INTELLIGENCE_DB_PATH", str(db_path))

    # No data/daily-briefs directory exists at all in this tmp_path scenario —
    # proves the function no longer depends on the JSON glob path.
    result = generate_reports.load_latest_brief()

    assert result["date"] == "2026-07-23"
    assert result["macro_regime"]["regime"] == "CONGESTION"
