"""Replay a JSONL intelligence-event ledger into the SQLite read model.

Reads newline-delimited JSON events from a ledger file and inserts any
event whose ``event_id`` is not yet in ``intelligence_event`` (identity-based,
so a ledger whose numbering restarted, or a checkpoint advanced by another
source, can no longer hide new events). A ledger ``event_sequence`` already
owned by another read-model row is reassigned to MAX(event_sequence)+1.
After a successful pass, records progress in ``ledger_checkpoint`` so a
subsequent replay only processes events past the last processed sequence
number (idempotent re-runs).
"""

import hashlib
import json
import logging
from datetime import datetime, timezone

from .event_repository import insert_event
from .instrument_repository import resolve_instrument

CHECKPOINT_ID = "global"
SCHEMA_VERSION = 1

logger = logging.getLogger(__name__)


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


def _free_sequence(conn, ledger_sequence):
    """Return ledger_sequence if unused in the read model, else MAX(event_sequence)+1.

    Args:
        conn: Open sqlite3 connection with the read-model schema applied.
        ledger_sequence: The event's sequence number within its ledger file.

    Returns:
        A read-model event_sequence that does not collide with an existing row.
    """
    taken = conn.execute(
        "SELECT 1 FROM intelligence_event WHERE event_sequence = ?;", (ledger_sequence,)
    ).fetchone()
    if not taken:
        return ledger_sequence
    return conn.execute("SELECT COALESCE(MAX(event_sequence), 0) + 1 FROM intelligence_event;").fetchone()[0]


def replay_events_to_db(jsonl_path, conn):
    """Replay a JSONL event ledger into the intelligence_event table.

    Reads each line of the ledger as a JSON event object and skips any event
    whose ``event_id`` is already present in the read model (the checkpoint
    is bookkeeping only; see the module docstring for why sequences are not
    comparable across ledgers). A sequence collision with an existing row is
    resolved by ``_free_sequence()``. Events written via ``event_store.append_event()`` carry a
    ``"ticker"`` string rather than an ``instrument_id`` (JSONL appends must
    not require a live SQLite connection), so for any event with a truthy
    ``ticker`` and no ``instrument_id`` already set, this function resolves
    the ticker to a real ``instrument_id`` via
    ``instrument_repository.resolve_instrument()`` before insertion. Events
    with no ticker (e.g. ticker-agnostic ``MACRO_EVENT`` rows) are inserted
    with ``instrument_id`` left as ``NULL``. The (possibly-augmented) event
    is then routed through ``event_repository.insert_event()`` (which uses
    ``INSERT OR IGNORE``
    under the hood). Re-inserting an already-present event_id is a no-op,
    so replaying the same file twice does not duplicate rows. It also
    means a row that violates a UNIQUE or CHECK constraint (e.g. an
    invalid ``event_type``/``status`` value, or a duplicate
    ``event_sequence``) is skipped rather than raising ``IntegrityError``.
    To avoid the checkpoint permanently advancing past such a row (which
    would make it unrecoverable on future replays), this function only
    advances the in-memory checkpoint bookkeeping for rows
    ``insert_event()`` reports as actually inserted. Rows that were
    rejected are logged at WARNING level and collected into the returned
    ``skipped`` list instead. On completion, upserts a single 'global' row
    in ``ledger_checkpoint`` recording the highest *actually-inserted*
    sequence processed, the corresponding event_id, the schema version, a
    UTC timestamp, and a sha256 hash of the ledger file's contents.

    Args:
        jsonl_path: Path to the JSONL ledger file to replay.
        conn: Open sqlite3 connection with the read-model schema applied
            (see db_client.initialize_db).

    Returns:
        A dict ``{"processed": int, "skipped": list[dict]}`` where
        ``processed`` is the count of rows actually inserted and
        ``skipped`` contains one entry per rejected event with keys
        ``event_id``, ``event_sequence``, and ``reason``. Mutates the
        database in place and commits the transaction only if new events
        were actually inserted.
    """
    last_seq = _get_last_checkpoint_sequence(conn)
    max_processed_sequence = last_seq
    last_event_id = None
    processed_count = 0
    skipped_events = []

    file_hash = _compute_file_hash(jsonl_path)

    # Identity, not sequence, decides what is already applied. Ledger files
    # number their own events (observations.jsonl restarted at 1 on
    # 2026-08-25) and record_intelligence_event.py writes straight to the
    # read model with MAX(event_sequence)+1, so ledger sequences and the
    # 'global' checkpoint are not comparable with read-model sequences.
    # Skipping by `seq <= checkpoint` silently dropped every new ledger event.
    known_ids = {row[0] for row in conn.execute("SELECT event_id FROM intelligence_event;")}

    try:
        with open(jsonl_path, "r") as f:
            for line in f:
                if not line.strip():
                    continue
                event = json.loads(line)
                seq = event["event_sequence"]
                if event.get("event_id") in known_ids:
                    continue

                ticker = event.get("ticker")
                if ticker and not event.get("instrument_id"):
                    event = {
                        **event,
                        "instrument_id": resolve_instrument(conn, ticker),
                    }

                event = {**event, "event_sequence": _free_sequence(conn, seq)}
                inserted = insert_event(conn, event)
                if inserted:
                    known_ids.add(event["event_id"])

                if inserted:
                    processed_count += 1
                    superseded_id = event.get("supersedes_event_id")
                    if superseded_id:
                        # Only flip the prior event AFTER the new (superseding)
                        # event was actually persisted — a rejected/skipped
                        # event must never retroactively supersede anything.
                        conn.execute(
                            "UPDATE intelligence_event SET status = 'SUPERSEDED' "
                            "WHERE event_id = ?;",
                            (superseded_id,),
                        )
                        conn.commit()
                    if seq > max_processed_sequence:
                        max_processed_sequence = seq
                        last_event_id = event["event_id"]
                else:
                    reason = (
                        "constraint violation (UNIQUE event_sequence/event_id "
                        "or CHECK event_type/status taxonomy) — row not inserted"
                    )
                    logger.warning(
                        "Skipped event_id=%s event_sequence=%s during replay of "
                        "%s: %s",
                        event.get("event_id"),
                        seq,
                        jsonl_path,
                        reason,
                    )
                    skipped_events.append(
                        {
                            "event_id": event.get("event_id"),
                            "event_sequence": seq,
                            "reason": reason,
                        }
                    )
    except FileNotFoundError:
        return {"processed": processed_count, "skipped": skipped_events}

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

    return {"processed": processed_count, "skipped": skipped_events}
