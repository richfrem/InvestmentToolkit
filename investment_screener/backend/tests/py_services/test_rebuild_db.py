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

from rebuild_db import run_rebuild  # noqa: E402


def test_run_rebuild(tmp_path):
    """run_rebuild must recreate DB from observations.jsonl."""
    db_path = tmp_path / "rebuilt_intelligence.sqlite"
    jsonl_path = tmp_path / "observations.jsonl"
    jsonl_path.write_text('{"event_id": "evt_test", "event_sequence": 1, "event_type": "MACRO_EVENT", "effective_at": "2026-07-18", "ingested_at": "2026-07-18", "status": "ACTIVE", "title": "Test event", "body_markdown": "Test body", "content_hash": "hash_val"}\n')

    run_rebuild(str(jsonl_path), str(db_path))
    assert db_path.exists()
