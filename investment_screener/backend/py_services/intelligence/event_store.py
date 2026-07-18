"""Shared event-append helper for the ``observations.jsonl`` ledger.

This is the single place ``event_sequence`` assignment, ``content_hash``
computation, and idempotency-key dedup logic live. Every writer (research
migration, SKILL.md-driven writers, etc.) should call ``append_event``
rather than writing to the ledger file directly, per ADR-028's
"Replay-first authority flow" — the ledger file is the source of truth and
the SQLite read model (see ``db_client.py`` / ``replay_ledger.py``) is
rebuilt from it.
"""

import json
import hashlib
import uuid
from datetime import datetime, timezone
from pathlib import Path


def _last_sequence(jsonl_path: str) -> int:
    """Return the highest ``event_sequence`` already present in the ledger.

    Args:
        jsonl_path: Path to the JSONL ledger file.

    Returns:
        The highest sequence number found, or 0 if the file does not exist
        or contains no events yet.
    """
    path = Path(jsonl_path)
    if not path.exists():
        return 0
    last = 0
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        last = json.loads(line)["event_sequence"]
    return last


def _find_by_idempotency_key(jsonl_path: str, idempotency_key: str):
    """Look up an existing event_id for a given idempotency key.

    Args:
        jsonl_path: Path to the JSONL ledger file.
        idempotency_key: Caller-supplied dedup key to search for.

    Returns:
        The matching ``event_id`` if found, else ``None``.
    """
    path = Path(jsonl_path)
    if not path.exists():
        return None
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if record.get("idempotency_key") == idempotency_key:
            return record["event_id"]
    return None


def append_event(
    jsonl_path: str,
    event_type: str,
    effective_at: str,
    status: str,
    title: str,
    body_markdown: str,
    ticker: str | None = None,
    source_id: str | None = None,
    payload: dict | None = None,
    supersedes_event_id: str | None = None,
    idempotency_key: str | None = None,
) -> str:
    """Append a new event record to the JSONL ledger.

    Assigns an incrementing ``event_sequence``, computes a ``content_hash``,
    and — when ``idempotency_key`` is supplied and already present in the
    ledger — returns the existing event's id instead of writing a duplicate
    row.

    Args:
        jsonl_path: Path to the JSONL ledger file (created if missing).
        event_type: One of the ``intelligence_event.event_type`` taxonomy
            values (see ``db_client.py``).
        effective_at: ISO date/timestamp the event pertains to.
        status: One of the ``intelligence_event.status`` taxonomy values.
        title: Short event title.
        body_markdown: Event body, as markdown.
        ticker: Optional ticker symbol the event relates to.
        source_id: Optional identifier for the originating source record.
        payload: Optional structured payload, serialized to JSON.
        supersedes_event_id: Optional event_id this event supersedes.
        idempotency_key: Optional caller-supplied dedup key.

    Returns:
        The ``event_id`` of the newly written (or deduped, pre-existing)
        event.
    """
    if idempotency_key:
        existing = _find_by_idempotency_key(jsonl_path, idempotency_key)
        if existing:
            return existing

    event_id = f"evt_{uuid.uuid4().hex[:12]}"
    content_hash = hashlib.sha256(
        f"{event_type}|{effective_at}|{title}|{body_markdown}".encode("utf-8")
    ).hexdigest()
    record = {
        "event_id": event_id,
        "event_sequence": _last_sequence(jsonl_path) + 1,
        "ticker": ticker,
        "event_type": event_type,
        "effective_at": effective_at,
        "ingested_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_id": source_id,
        "status": status,
        "title": title,
        "body_markdown": body_markdown,
        "payload_json": json.dumps(payload) if payload is not None else None,
        "supersedes_event_id": supersedes_event_id,
        "idempotency_key": idempotency_key,
        "content_hash": content_hash,
    }
    path = Path(jsonl_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(record) + "\n")
    return event_id
