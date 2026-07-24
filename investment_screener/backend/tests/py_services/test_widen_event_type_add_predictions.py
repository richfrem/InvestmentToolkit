import sqlite3
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from intelligence.db_client import initialize_db  # noqa: E402
from intelligence.migrations.widen_event_type_add_predictions import (  # noqa: E402
    widen_event_type_constraint,
)


def _seed_events(conn, count_by_type):
    """Insert minimal valid rows so the fixture DB isn't empty when widened."""
    seq = 1
    for event_type, count in count_by_type.items():
        for i in range(count):
            conn.execute(
                "INSERT INTO intelligence_event "
                "(event_id, event_sequence, event_type, effective_at, ingested_at, status, "
                "content_hash) VALUES (?, ?, ?, ?, ?, 'ACTIVE', ?);",
                (f"{event_type}-{i}", seq, event_type, "2026-01-01T00:00:00Z",
                 "2026-01-01T00:00:00Z", f"hash-{seq}"),
            )
            seq += 1
    conn.commit()


def test_widen_preserves_all_existing_rows(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    _seed_events(conn, {"RESEARCH_IMPORT": 3, "TECHNICAL_SWEEP": 2, "REVIEW_DAILY": 1})
    result = widen_event_type_constraint(conn)
    assert result["before_row_count"] == 6
    assert result["after_row_count"] == 6
    cursor = conn.execute("SELECT COUNT(*) FROM intelligence_event;")
    assert cursor.fetchone()[0] == 6


def test_widen_allows_prediction_claim_insert_after(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    _seed_events(conn, {"RESEARCH_IMPORT": 1})
    widen_event_type_constraint(conn)
    # Must not raise IntegrityError now that the constraint is widened.
    conn.execute(
        "INSERT INTO intelligence_event "
        "(event_id, event_sequence, event_type, effective_at, ingested_at, status, "
        "content_hash) VALUES ('pred-1', 99, 'PREDICTION_CLAIM', '2026-01-01T00:00:00Z', "
        "'2026-01-01T00:00:00Z', 'ACTIVE', 'hash-99');"
    )
    conn.execute(
        "INSERT INTO intelligence_event "
        "(event_id, event_sequence, event_type, effective_at, ingested_at, status, "
        "content_hash) VALUES ('grade-1', 100, 'PREDICTION_GRADED', '2026-01-01T00:00:00Z', "
        "'2026-01-01T00:00:00Z', 'ACTIVE', 'hash-100');"
    )
    conn.commit()
    cursor = conn.execute(
        "SELECT COUNT(*) FROM intelligence_event WHERE event_type IN "
        "('PREDICTION_CLAIM', 'PREDICTION_GRADED');"
    )
    assert cursor.fetchone()[0] == 2


def test_widen_still_rejects_truly_invalid_event_type(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    _seed_events(conn, {"RESEARCH_IMPORT": 1})
    widen_event_type_constraint(conn)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO intelligence_event "
            "(event_id, event_sequence, event_type, effective_at, ingested_at, status, "
            "content_hash) VALUES ('bad-1', 101, 'NOT_A_REAL_TYPE', '2026-01-01T00:00:00Z', "
            "'2026-01-01T00:00:00Z', 'ACTIVE', 'hash-101');"
        )


def test_widen_is_idempotent_on_rerun(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    _seed_events(conn, {"RESEARCH_IMPORT": 2})
    widen_event_type_constraint(conn)
    result_second = widen_event_type_constraint(conn)
    assert result_second["before_row_count"] == 2
    assert result_second["after_row_count"] == 2


def test_widen_preserves_fts_and_triggers(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    conn.execute(
        "INSERT INTO intelligence_event "
        "(event_id, event_sequence, event_type, effective_at, ingested_at, status, "
        "title, body_markdown, content_hash) VALUES "
        "('r-1', 1, 'RESEARCH_IMPORT', '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z', "
        "'ACTIVE', 'Test Title', 'Test body content.', 'hash-1');"
    )
    conn.commit()
    widen_event_type_constraint(conn)
    cursor = conn.execute(
        "SELECT rowid FROM intelligence_event_fts WHERE intelligence_event_fts MATCH 'Test';"
    )
    # FTS shadow table content must survive the rebuild -- either the trigger reindexed it
    # during copy, or the rebuild step explicitly repopulates FTS. Either is acceptable;
    # the row must be findable afterward.
    rows = cursor.fetchall()
    assert len(rows) >= 0  # placeholder assertion replaced below
    cursor2 = conn.execute(
        "SELECT ie.event_id FROM intelligence_event_fts fts "
        "JOIN intelligence_event ie ON ie.rowid = fts.rowid "
        "WHERE intelligence_event_fts MATCH 'Test';"
    )
    assert [r[0] for r in cursor2.fetchall()] == ["r-1"]
