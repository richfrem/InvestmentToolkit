"""Event-append helper for the intelligence ledger (``intelligence.sqlite``).

Purpose:
    The single place ``event_sequence`` assignment, ``content_hash`` computation, ticker to
    instrument resolution and idempotency-key dedup live. Every writer (research
    persistence, TA sweeps, prediction ledger, daily brief, SKILL.md-driven writers) calls
    ``append_event`` or ``append_or_supersede_event`` with an open ledger connection; the
    ledger database is the only store (ADR-028, ADR-038).

Layer:
    Backend / Python Services / Data Persistence

Usage Examples:
    python3 -m intelligence.event_store --event-type RESEARCH_IMPORT --ticker NVDA \\
        --effective-at 2026-10-09 --status ACTIVE --title "NVDA note" --body "text"

Key Functions (Index):
    - default_db_path(): canonical intelligence.sqlite location
    - append_event(): insert one event (deduped by idempotency key) and return its id
    - append_or_supersede_event(): insert, or correct the event already written under a key
    - _main(): CLI for SKILL.md-driven writers

Key Input Dependencies:
    - intelligence.sqlite (via db_client.initialize_db)

Key Output Dependencies:
    - intelligence_event, instrument rows
"""

import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .event_repository import insert_event
from .instrument_repository import resolve_instrument


def default_db_path() -> Path:
    """Return the canonical ``intelligence.sqlite`` location.

    Derived from this file's location so the default works regardless of the caller's cwd.
    """
    repo_root = Path(__file__).resolve().parents[4]
    return repo_root / "investment_screener/backend/data/intelligence.sqlite"


def _find_by_idempotency_key(conn, idempotency_key: str):
    """Return the ``event_id`` already stored under ``idempotency_key``, else None."""
    row = conn.execute(
        "SELECT event_id FROM intelligence_event WHERE idempotency_key = ?;", (idempotency_key,)
    ).fetchone()
    return row[0] if row else None


def append_event(
    conn,
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
    """Insert a new event into ``intelligence_event`` and return its id.

    Assigns the next ``event_sequence``, computes a ``content_hash``, resolves ``ticker`` to
    an ``instrument_id`` and, when ``idempotency_key`` is already stored, returns the
    existing event's id instead of writing a duplicate. When ``supersedes_event_id`` is set
    the superseded event becomes ``SUPERSEDED``.

    Args:
        conn: Open sqlite3 connection to the ledger (``db_client.initialize_db``).
        event_type: One of the ``intelligence_event.event_type`` taxonomy values.
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
        The ``event_id`` of the newly written (or deduped, pre-existing) event.

    Raises:
        ValueError: If the database rejects the row (invalid event_type/status).
    """
    if idempotency_key:
        existing = _find_by_idempotency_key(conn, idempotency_key)
        if existing:
            return existing

    event_id = f"evt_{uuid.uuid4().hex[:12]}"
    content_hash = hashlib.sha256(
        f"{event_type}|{effective_at}|{title}|{body_markdown}".encode("utf-8")
    ).hexdigest()
    sequence = conn.execute("SELECT COALESCE(MAX(event_sequence), 0) + 1 FROM intelligence_event;").fetchone()[0]
    record = {
        "event_id": event_id,
        "event_sequence": sequence,
        "instrument_id": resolve_instrument(conn, ticker) if ticker else None,
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
    if not insert_event(conn, record):
        raise ValueError(
            f"ledger rejected event {event_type!r}/{status!r} (invalid event_type or status, or a duplicate key)"
        )
    if supersedes_event_id:
        conn.execute(
            "UPDATE intelligence_event SET status = 'SUPERSEDED' WHERE event_id = ?;", (supersedes_event_id,)
        )
        conn.commit()
    return event_id


def _latest_in_idempotency_chain(conn, idempotency_key: str):
    """Return (record, chain_length) for the newest event written under a key.

    A chain is the original event (``key``) plus any corrections (``key#r2``, ``key#r3``, ...)
    appended by ``append_or_supersede_event``.

    Returns:
        ``(latest_record, chain_length)`` where the record has ``event_id`` and
        ``payload_json``, or ``(None, 0)`` if no event has been written under the key yet.
    """
    rows = conn.execute(
        "SELECT event_id, payload_json, idempotency_key FROM intelligence_event "
        "WHERE idempotency_key = ? OR idempotency_key LIKE ? ORDER BY event_sequence;",
        (idempotency_key, f"{idempotency_key}#r%"),
    ).fetchall()
    if not rows:
        return None, 0
    latest = rows[-1]
    return {"event_id": latest[0], "payload_json": latest[1]}, len(rows)


def append_or_supersede_event(conn, *, idempotency_key: str, payload: dict, **event_fields) -> str:
    """Append an event, or correct the one already written under its key.

    ``append_event`` treats an existing ``idempotency_key`` as "already written" and drops the
    new payload, so a same-key re-run can never fix bad data. This keeps true retries
    idempotent but lets a changed payload through as a correction that supersedes the previous
    event, which then becomes ``SUPERSEDED``.

    Args:
        conn: Open sqlite3 connection to the ledger.
        idempotency_key: Base dedup key for the logical event.
        payload: Structured payload; compared against the latest event in the key's chain to
            tell a retry from a correction.
        **event_fields: Remaining ``append_event`` arguments.

    Returns:
        The ``event_id`` of the event now current for the key: the existing one when the
        payload is unchanged, else the newly appended one.
    """
    latest, chain_length = _latest_in_idempotency_chain(conn, idempotency_key)
    if latest is None:
        return append_event(conn, payload=payload, idempotency_key=idempotency_key, **event_fields)
    if latest.get("payload_json") == json.dumps(payload):
        return latest["event_id"]
    return append_event(
        conn,
        payload=payload,
        supersedes_event_id=latest["event_id"],
        idempotency_key=f"{idempotency_key}#r{chain_length + 1}",
        **event_fields,
    )


def _main() -> None:
    """CLI entry point: append one event to the ledger from flags.

    Thin wrapper around ``append_event`` for SKILL.md-driven writers (see
    ``plugins/stock-valuation/skills/stock_valuation/SKILL.md`` and
    ``.../stock-research/SKILL.md``) that shell out via
    ``python3 -m intelligence.event_store`` rather than importing this
    module directly. Body markdown is supplied via ``--body-file`` (a path
    to a file containing the markdown) or ``--body`` (an inline string);
    exactly one is required. Prints the resulting ``event_id`` to stdout.
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="Append one event to the intelligence ledger (intelligence.sqlite)."
    )
    parser.add_argument("--event-type", required=True, dest="event_type")
    parser.add_argument("--ticker")
    parser.add_argument("--effective-at", required=True, dest="effective_at")
    parser.add_argument("--status", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--body-file", dest="body_file", help="Path to a markdown file to use as the event body.")
    parser.add_argument("--body", help="Inline markdown body (alternative to --body-file).")
    parser.add_argument("--source-id", dest="source_id")
    parser.add_argument("--idempotency-key", dest="idempotency_key")
    parser.add_argument(
        "--db-path",
        dest="db_path",
        default=str(default_db_path()),
        help="Path to intelligence.sqlite (default: %(default)s).",
    )
    args = parser.parse_args()

    if args.body_file:
        body_markdown = Path(args.body_file).read_text()
    elif args.body is not None:
        body_markdown = args.body
    else:
        parser.error("one of --body-file or --body is required")
        return

    from .db_client import initialize_db

    conn = initialize_db(args.db_path)
    event_id = append_event(
        conn,
        event_type=args.event_type,
        effective_at=args.effective_at,
        status=args.status,
        title=args.title,
        body_markdown=body_markdown,
        ticker=args.ticker,
        source_id=args.source_id,
        idempotency_key=args.idempotency_key,
    )
    conn.close()
    print(event_id)


if __name__ == "__main__":
    _main()
