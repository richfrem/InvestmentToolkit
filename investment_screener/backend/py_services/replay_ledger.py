"""Replay a JSONL intelligence-event ledger into the SQLite read model.

Reads newline-delimited JSON events from a ledger file and inserts any
events newer than the last recorded checkpoint into ``intelligence_event``.
After a successful pass, records progress in ``ledger_checkpoint`` so a
subsequent replay only processes events past the last processed sequence
number (idempotent re-runs).
"""

import hashlib
import json
from datetime import datetime, timezone

CHECKPOINT_ID = "global"
SCHEMA_VERSION = 1


def _compute_file_hash(jsonl_path):
    """Compute the sha256 hash of a ledger file's raw bytes.

    Args:
        jsonl_path: Path to the JSONL ledger file.

    Returns:
        Hex digest string, or "missing" if the file does not exist.
    """
    hasher = hashlib.sha256()
    try:
        with open(jsonl_path, "rb") as f:
            hasher.update(f.read())
        return hasher.hexdigest()
    except FileNotFoundError:
        return "missing"


def _get_last_checkpoint_sequence(conn):
    """Look up the highest last_event_sequence recorded in ledger_checkpoint.

    Args:
        conn: Open sqlite3 connection with the read-model schema applied.

    Returns:
        Integer sequence number, 0 if no checkpoint exists yet.
    """
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(last_event_sequence) FROM ledger_checkpoint;")
    row = cursor.fetchone()
    return row[0] if row and row[0] is not None else 0


def replay_events_to_db(jsonl_path, conn):
    """Replay a JSONL event ledger into the intelligence_event table.

    Reads each line of the ledger as a JSON event object, skips any event
    whose ``event_sequence`` is not greater than the last recorded
    checkpoint, and inserts the remainder into ``intelligence_event``.
    ``INSERT OR IGNORE`` makes re-inserting an already-present event_id a
    no-op, so replaying the same file twice does not duplicate rows. On
    completion, upserts a single 'global' row in ``ledger_checkpoint``
    recording the highest sequence processed, the corresponding event_id,
    the schema version, a UTC timestamp, and a sha256 hash of the ledger
    file's contents.

    Args:
        jsonl_path: Path to the JSONL ledger file to replay.
        conn: Open sqlite3 connection with the read-model schema applied
            (see db_client.initialize_db).

    Returns:
        None. Mutates the database in place and commits the transaction
        only if new events were processed.
    """
    last_seq = _get_last_checkpoint_sequence(conn)
    max_processed_sequence = last_seq
    last_event_id = None

    file_hash = _compute_file_hash(jsonl_path)

    try:
        with open(jsonl_path, "r") as f:
            for line in f:
                if not line.strip():
                    continue
                event = json.loads(line)
                seq = event["event_sequence"]
                if seq <= last_seq:
                    continue

                conn.execute(
                    """
                    INSERT OR IGNORE INTO intelligence_event (
                        event_id, event_sequence, event_type, effective_at,
                        ingested_at, status, title, body_markdown, content_hash
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        event["event_id"],
                        event["event_sequence"],
                        event["event_type"],
                        event["effective_at"],
                        event["ingested_at"],
                        event["status"],
                        event["title"],
                        event["body_markdown"],
                        event["content_hash"],
                    ),
                )

                if seq > max_processed_sequence:
                    max_processed_sequence = seq
                    last_event_id = event["event_id"]
    except FileNotFoundError:
        return

    if max_processed_sequence > last_seq:
        processed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        conn.execute(
            """
            INSERT OR REPLACE INTO ledger_checkpoint (
                checkpoint_id, last_event_sequence, last_event_id,
                schema_version, processed_at, ledger_file_hash
            )
            VALUES (?, ?, ?, ?, ?, ?);
            """,
            (
                CHECKPOINT_ID,
                max_processed_sequence,
                last_event_id,
                SCHEMA_VERSION,
                processed_at,
                file_hash,
            ),
        )
        conn.commit()
