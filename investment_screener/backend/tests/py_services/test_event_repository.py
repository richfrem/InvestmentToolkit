import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from intelligence.db_client import initialize_db  # noqa: E402
from intelligence.event_repository import (  # noqa: E402
    insert_event,
    list_active_events_for_ticker,
    search_fts,
)


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


def test_list_active_events_for_ticker_filters_status_and_ticker(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    conn.execute("INSERT INTO instrument VALUES ('us-pltr', 'PLTR', 'NASDAQ', 'Palantir', '2026-07-18', NULL);")
    conn.execute("INSERT INTO instrument VALUES ('us-nvda', 'NVDA', 'NASDAQ', 'Nvidia', '2026-07-18', NULL);")
    conn.commit()
    insert_event(conn, {
        "event_id": "evt_1", "event_sequence": 1, "instrument_id": "us-pltr",
        "event_type": "NEWS_SWEEP", "effective_at": "2026-07-01", "ingested_at": "2026-07-01",
        "status": "ACTIVE", "title": "Older PLTR event", "body_markdown": "Older body.",
        "content_hash": "h1",
    })
    insert_event(conn, {
        "event_id": "evt_2", "event_sequence": 2, "instrument_id": "us-pltr",
        "event_type": "NEWS_SWEEP", "effective_at": "2026-07-10", "ingested_at": "2026-07-10",
        "status": "ACTIVE", "title": "Newer PLTR event", "body_markdown": "Newer body.",
        "content_hash": "h2",
    })
    insert_event(conn, {
        "event_id": "evt_3", "event_sequence": 3, "instrument_id": "us-pltr",
        "event_type": "NEWS_SWEEP", "effective_at": "2026-07-15", "ingested_at": "2026-07-15",
        "status": "SUPERSEDED", "title": "Superseded PLTR event", "body_markdown": "Stale body.",
        "content_hash": "h3",
    })
    insert_event(conn, {
        "event_id": "evt_4", "event_sequence": 4, "instrument_id": "us-nvda",
        "event_type": "NEWS_SWEEP", "effective_at": "2026-07-12", "ingested_at": "2026-07-12",
        "status": "ACTIVE", "title": "NVDA event", "body_markdown": "Other ticker body.",
        "content_hash": "h4",
    })

    results = list_active_events_for_ticker(conn, "PLTR")

    assert [r["event_id"] for r in results] == ["evt_2", "evt_1"]
    assert all(r["status"] == "ACTIVE" for r in results)
