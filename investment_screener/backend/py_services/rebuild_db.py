"""
Rebuild DB from JSONL event ledger backup.

Standalone utility for deterministic full-rebuild and backup verification.
Imports initialize_db and replay_events_to_db from the intelligence package
to avoid duplicating schema or replay logic.
"""

import json
import os
import sqlite3

from intelligence.db_client import initialize_db
from intelligence.replay_ledger import replay_events_to_db


def _count_valid_ledger_lines(jsonl_path):
    """Count the JSON-parseable, non-blank lines in a ledger file.

    Mirrors the skip-blank-lines logic ``replay_ledger.replay_events_to_db``
    applies when it reads the ledger, so the two counts are comparable.

    Args:
        jsonl_path: Path to the JSONL ledger file.

    Returns:
        The number of non-blank lines that parse as JSON. A missing file
        yields 0.
    """
    count = 0
    try:
        with open(jsonl_path, "r") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    json.loads(line)
                except json.JSONDecodeError:
                    continue
                count += 1
    except FileNotFoundError:
        return 0
    return count


def verify_rebuild(jsonl_path, db_path, skipped=0):
    """Verify a rebuilt DB is consistent with its source ledger.

    Confirms every valid ledger line is accounted for in the rebuilt DB:
    either projected into ``intelligence_event`` or legitimately rejected by
    ``replay_events_to_db`` (taxonomy/UNIQUE-constraint violations). The
    ``skipped`` count is threaded through from ``replay_events_to_db``'s
    return value so those rejections don't count as data loss.

    Args:
        jsonl_path: Path to the source JSONL ledger file.
        db_path: Path to the rebuilt ``intelligence.sqlite`` DB.
        skipped: Number of events ``replay_events_to_db`` rejected/skipped
            during the rebuild (defaults to 0).

    Returns:
        Dict with ``ledger_valid_lines``, ``projected_rows``, ``skipped``,
        and ``verified`` (True only when
        ``ledger_valid_lines == projected_rows + skipped``).
    """
    ledger_valid_lines = _count_valid_ledger_lines(jsonl_path)
    conn = sqlite3.connect(db_path)
    try:
        projected_rows = conn.execute(
            "SELECT COUNT(*) FROM intelligence_event;"
        ).fetchone()[0]
    finally:
        conn.close()
    return {
        "ledger_valid_lines": ledger_valid_lines,
        "projected_rows": projected_rows,
        "skipped": skipped,
        "verified": ledger_valid_lines == projected_rows + skipped,
    }


def run_rebuild(jsonl_path, db_path):
    """
    Delete existing DB, rebuild from JSONL ledger, and verify the result.

    Args:
        jsonl_path: Path to observations.jsonl ledger file
        db_path: Path where intelligence.sqlite will be created

    Returns:
        The ``verify_rebuild`` result dict (see that function), so callers
        can assert the rebuild is consistent with the source ledger.
    """
    if os.path.exists(db_path):
        os.remove(db_path)
    conn = initialize_db(db_path)
    try:
        replay_result = replay_events_to_db(jsonl_path, conn)
    finally:
        conn.close()
    return verify_rebuild(
        jsonl_path, db_path, skipped=len(replay_result["skipped"])
    )
