import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from intelligence.db_client import initialize_db  # noqa: E402
from intelligence.event_repository import insert_event, search_fts  # noqa: E402


def test_insert_event_returns_true_when_row_inserted(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    conn.execute("INSERT INTO instrument VALUES ('us-pltr', 'PLTR', 'NASDAQ', 'Palantir', '2026-07-18', NULL);")
    conn.commit()
    result = insert_event(conn, {
        "event_id": "evt_1", "event_sequence": 1, "instrument_id": "us-pltr",
        "event_type": "NEWS_SWEEP", "effective_at": "2026-07-18", "ingested_at": "2026-07-18",
        "status": "ACTIVE", "title": "T1", "body_markdown": "B1", "content_hash": "h1",
    })
    assert result is True


def test_insert_event_returns_false_when_sequence_duplicate(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    conn.execute("INSERT INTO instrument VALUES ('us-pltr', 'PLTR', 'NASDAQ', 'Palantir', '2026-07-18', NULL);")
    conn.commit()
    base = {
        "event_sequence": 1, "instrument_id": "us-pltr", "event_type": "NEWS_SWEEP",
        "effective_at": "2026-07-18", "ingested_at": "2026-07-18", "status": "ACTIVE",
        "title": "T1", "body_markdown": "B1",
    }
    assert insert_event(conn, {**base, "event_id": "evt_1", "content_hash": "h1"}) is True
    assert insert_event(conn, {**base, "event_id": "evt_2", "content_hash": "h2"}) is False


def test_search_fts_returns_matching_events(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    conn.execute("INSERT INTO instrument VALUES ('us-pltr', 'PLTR', 'NASDAQ', 'Palantir', '2026-07-18', NULL);")
    conn.commit()
    insert_event(conn, {
        "event_id": "evt_1", "event_sequence": 1, "instrument_id": "us-pltr",
        "event_type": "NEWS_SWEEP", "effective_at": "2026-07-18", "ingested_at": "2026-07-18",
        "status": "ACTIVE", "title": "Nvidia Partnership", "body_markdown": "Palantir and Nvidia.",
        "content_hash": "h1",
    })
    results = search_fts(conn, "Nvidia")
    assert len(results) == 1
    assert results[0]["title"] == "Nvidia Partnership"
