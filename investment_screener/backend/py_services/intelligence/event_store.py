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


def _default_jsonl_path() -> Path:
    """Return the canonical ``observations.jsonl`` location.

    Derived from this file's location so the default works regardless of
    the caller's cwd, per the ``investment_screener/backend/data/``
    convention used by ``market_regime.py`` et al.

    Returns:
        The repo-relative default path to the JSONL ledger.
    """
    repo_root = Path(__file__).resolve().parents[4]
    return repo_root / "investment_screener/backend/data/observations.jsonl"


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
        description="Append one event to the observations.jsonl ledger."
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
        "--jsonl-path",
        dest="jsonl_path",
        default=str(_default_jsonl_path()),
        help="Path to the observations.jsonl ledger (default: %(default)s).",
    )
    args = parser.parse_args()

    if args.body_file:
        body_markdown = Path(args.body_file).read_text()
    elif args.body is not None:
        body_markdown = args.body
    else:
        parser.error("one of --body-file or --body is required")
        return

    event_id = append_event(
        args.jsonl_path,
        event_type=args.event_type,
        effective_at=args.effective_at,
        status=args.status,
        title=args.title,
        body_markdown=body_markdown,
        ticker=args.ticker,
        source_id=args.source_id,
        idempotency_key=args.idempotency_key,
    )
    print(event_id)


if __name__ == "__main__":
    _main()
