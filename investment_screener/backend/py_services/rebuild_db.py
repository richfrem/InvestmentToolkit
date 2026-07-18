"""
Rebuild DB from JSONL event ledger backup.

Standalone utility for deterministic full-rebuild and backup verification.
Imports initialize_db and replay_events_to_db from the intelligence package
to avoid duplicating schema or replay logic.
"""

import os
from intelligence.db_client import initialize_db
from intelligence.replay_ledger import replay_events_to_db


def run_rebuild(jsonl_path, db_path):
    """
    Delete existing DB and rebuild from JSONL ledger.

    Args:
        jsonl_path: Path to observations.jsonl ledger file
        db_path: Path where intelligence.sqlite will be created
    """
    if os.path.exists(db_path):
        os.remove(db_path)
    conn = initialize_db(db_path)
    replay_events_to_db(jsonl_path, conn)
    conn.close()
