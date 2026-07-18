"""
Tests for rebuild_db.py — database rebuild from JSONL event ledger backup.

Key invariant under test:
  run_rebuild() must deterministically recreate intelligence.sqlite
  from observations.jsonl by (1) deleting any existing DB, (2) reinitializing
  the schema, and (3) replaying all events from the ledger.

Test tier: Category B (file I/O).
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from rebuild_db import run_rebuild, verify_rebuild  # noqa: E402
from intelligence.db_client import initialize_db  # noqa: E402


def test_run_rebuild(tmp_path):
    """run_rebuild must recreate DB from observations.jsonl."""
    db_path = tmp_path / "rebuilt_intelligence.sqlite"
    jsonl_path = tmp_path / "observations.jsonl"
    jsonl_path.write_text('{"event_id": "evt_test", "event_sequence": 1, "event_type": "MACRO_EVENT", "effective_at": "2026-07-18", "ingested_at": "2026-07-18", "status": "ACTIVE", "title": "Test event", "body_markdown": "Test body", "content_hash": "hash_val"}\n')

    run_rebuild(str(jsonl_path), str(db_path))
    assert db_path.exists()


def test_run_rebuild_verifies_with_skipped_event_accounted(tmp_path):
    """A rebuild whose ledger holds one valid event and one taxonomy-violating
    (skipped) event must still report verified=True, because the skipped event
    is accounted for: ledger_valid_lines == projected_rows + skipped."""
    db_path = tmp_path / "rebuilt_intelligence.sqlite"
    jsonl_path = tmp_path / "observations.jsonl"
    jsonl_path.write_text(
        '{"event_id": "evt_ok", "event_sequence": 1, "event_type": "MACRO_EVENT", '
        '"effective_at": "2026-07-18", "ingested_at": "2026-07-18", "status": "ACTIVE", '
        '"title": "Valid", "body_markdown": "B", "content_hash": "h1"}\n'
        '{"event_id": "evt_bad", "event_sequence": 2, "event_type": "NOT_IN_TAXONOMY", '
        '"effective_at": "2026-07-18", "ingested_at": "2026-07-18", "status": "ACTIVE", '
        '"title": "Bad", "body_markdown": "B", "content_hash": "h2"}\n'
    )

    result = run_rebuild(str(jsonl_path), str(db_path))

    assert result["ledger_valid_lines"] == 2
    assert result["projected_rows"] == 1
    assert result["skipped"] == 1
    assert result["verified"] is True


def test_verify_rebuild_reports_false_on_inconsistent_state(tmp_path):
    """verify_rebuild called directly against a deliberately mismatched DB
    (fewer rows than the ledger has valid lines, with no skips accounted for)
    must report verified=False."""
    db_path = tmp_path / "intelligence.sqlite"
    jsonl_path = tmp_path / "observations.jsonl"
    jsonl_path.write_text(
        '{"event_id": "a", "event_sequence": 1, "event_type": "MACRO_EVENT", '
        '"effective_at": "2026-07-18", "ingested_at": "2026-07-18", "status": "ACTIVE", '
        '"title": "A", "body_markdown": "B", "content_hash": "h1"}\n'
        '{"event_id": "b", "event_sequence": 2, "event_type": "MACRO_EVENT", '
        '"effective_at": "2026-07-18", "ingested_at": "2026-07-18", "status": "ACTIVE", '
        '"title": "B", "body_markdown": "B", "content_hash": "h2"}\n'
        '{"event_id": "c", "event_sequence": 3, "event_type": "MACRO_EVENT", '
        '"effective_at": "2026-07-18", "ingested_at": "2026-07-18", "status": "ACTIVE", '
        '"title": "C", "body_markdown": "B", "content_hash": "h3"}\n'
    )
    # DB has only one row — inconsistent with the 3 valid ledger lines.
    conn = initialize_db(str(db_path))
    conn.execute(
        "INSERT INTO intelligence_event (event_id, event_sequence, event_type, "
        "effective_at, ingested_at, status, title, body_markdown, content_hash) "
        "VALUES ('a', 1, 'MACRO_EVENT', '2026-07-18', '2026-07-18', 'ACTIVE', 'A', 'B', 'h1');"
    )
    conn.commit()
    conn.close()

    result = verify_rebuild(str(jsonl_path), str(db_path), skipped=0)

    assert result["ledger_valid_lines"] == 3
    assert result["projected_rows"] == 1
    assert result["verified"] is False
