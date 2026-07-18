import sys
from pathlib import Path
import pytest
import sqlite3

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from intelligence.db_client import initialize_db  # noqa: E402

def test_db_initialization(tmp_path):
    db_path = tmp_path / "test_intelligence.sqlite"
    conn = initialize_db(str(db_path))
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='instrument';")
    assert cursor.fetchone() is not None

def test_fts_search_sync(tmp_path):
    db_path = tmp_path / "test_intelligence.sqlite"
    conn = initialize_db(str(db_path))

    # Insert mock instrument & event
    conn.execute("INSERT INTO instrument VALUES ('us-pltr', 'PLTR', 'NASDAQ', 'Palantir', '2026-07-18', NULL);")
    conn.execute("""
        INSERT INTO intelligence_event (event_id, event_sequence, instrument_id, event_type, effective_at, ingested_at, status, title, body_markdown, content_hash)
        VALUES ('evt_1', 1, 'us-pltr', 'NEWS_SWEEP', '2026-07-18', '2026-07-18', 'ACTIVE', 'Nvidia AI Partnership', 'Palantir ontology builds secure node.', 'hash_1');
    """)
    conn.commit()

    cursor = conn.cursor()
    cursor.execute("SELECT rowid FROM intelligence_event_fts WHERE intelligence_event_fts MATCH 'Nvidia';")
    assert cursor.fetchone() is not None

def test_sequence_uniqueness_constraint(tmp_path):
    db_path = tmp_path / "test_intelligence.sqlite"
    conn = initialize_db(str(db_path))

    conn.execute("INSERT INTO instrument VALUES ('us-pltr', 'PLTR', 'NASDAQ', 'Palantir', '2026-07-18', NULL);")
    conn.execute("""
        INSERT INTO intelligence_event (event_id, event_sequence, instrument_id, event_type, effective_at, ingested_at, status, title, body_markdown, content_hash)
        VALUES ('evt_1', 1, 'us-pltr', 'NEWS_SWEEP', '2026-07-18', '2026-07-18', 'ACTIVE', 'Title 1', 'Body 1', 'hash_1');
    """)
    conn.commit()

    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("""
            INSERT INTO intelligence_event (event_id, event_sequence, instrument_id, event_type, effective_at, ingested_at, status, title, body_markdown, content_hash)
            VALUES ('evt_2', 1, 'us-pltr', 'NEWS_SWEEP', '2026-07-18', '2026-07-18', 'ACTIVE', 'Title 2', 'Body 2', 'hash_2');
        """)
        conn.commit()
