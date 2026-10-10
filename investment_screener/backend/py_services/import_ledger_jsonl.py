#!/usr/bin/env python3
"""
import_ledger_jsonl.py - One-time import of old ledger JSONL files into intelligence.sqlite.

Purpose:
    The intelligence ledger used to be written to JSONL files (observations.jsonl,
    intelligence_events.jsonl) and replayed into the database. The database is now the only
    store. This tool loads any event still found only in such a file, keeping its event id,
    ingestion time, content hash and idempotency key. An event already in the database (same
    idempotency key, event id or content hash) is left alone. Dry-run by default; --write
    needs a reviewed dry-run report.

Layer:
    Backend / Python Services / Migration (one-time)

Usage Examples:
    python3 import_ledger_jsonl.py --jsonl-path data/intelligence_events.jsonl --dry-run
    python3 import_ledger_jsonl.py --jsonl-path data/intelligence_events.jsonl --write

Key Functions (Index):
    - import_jsonl(): compare a JSONL file with the ledger and (unless dry-run) load the missing events
    - main(): CLI entry point

Key Input Dependencies:
    - A ledger JSONL file (--jsonl-path), one event per line
    - intelligence.sqlite (--db-path)

Key Output Dependencies:
    - intelligence_event and instrument rows
"""
import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))

from intelligence.db_client import initialize_db  # noqa: E402
from intelligence.event_repository import insert_event  # noqa: E402
from intelligence.instrument_repository import resolve_instrument  # noqa: E402

DEFAULT_DB_PATH = REPO_ROOT / "investment_screener/backend/data/intelligence.sqlite"


def _known(conn) -> dict:
    """Idempotency keys, event ids and content hashes already in the ledger."""
    known = {"keys": set(), "ids": set(), "hashes": set()}
    for event_id, key, content_hash in conn.execute(
        "SELECT event_id, idempotency_key, content_hash FROM intelligence_event;"
    ):
        known["ids"].add(event_id)
        known["hashes"].add(content_hash)
        if key:
            known["keys"].add(key)
    return known


def _is_present(event: dict, known: dict) -> bool:
    key = event.get("idempotency_key")
    return bool(
        (key and key in known["keys"])
        or event.get("event_id") in known["ids"]
        or event.get("content_hash") in known["hashes"]
    )


def import_jsonl(jsonl_path: Path, db_path: Path, dry_run: bool = True) -> dict:
    """Load events found only in ``jsonl_path`` into the ledger at ``db_path``.

    Returns:
        {"lines", "already_present", "to_import", "imported", "rejected": [event ids]}.
        ``to_import`` counts events missing from the ledger; ``imported`` is 0 in a dry run.
    """
    report = {"lines": 0, "already_present": 0, "to_import": 0, "imported": 0, "rejected": []}
    if not Path(jsonl_path).exists():
        return report
    if dry_run and not Path(db_path).exists():
        conn = None
        known = {"keys": set(), "ids": set(), "hashes": set()}
    else:
        conn = initialize_db(str(db_path))
        known = _known(conn)
    try:
        for line in Path(jsonl_path).read_text().splitlines():
            if not line.strip():
                continue
            event = json.loads(line)
            report["lines"] += 1
            if _is_present(event, known):
                report["already_present"] += 1
                continue
            report["to_import"] += 1
            if dry_run:
                continue
            ticker = event.get("ticker")
            sequence = conn.execute("SELECT COALESCE(MAX(event_sequence), 0) + 1 FROM intelligence_event;").fetchone()[0]
            superseded = event.get("supersedes_event_id")
            row = {
                **event,
                "event_sequence": sequence,
                "instrument_id": resolve_instrument(conn, ticker) if ticker else None,
                "supersedes_event_id": superseded if superseded in known["ids"] else None,
            }
            if insert_event(conn, row):
                report["imported"] += 1
                known["ids"].add(event["event_id"])
                known["hashes"].add(event.get("content_hash"))
                if event.get("idempotency_key"):
                    known["keys"].add(event["idempotency_key"])
            else:
                report["rejected"].append(event.get("event_id"))
    finally:
        if conn is not None:
            conn.close()
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jsonl-path", required=True, help="Old ledger JSONL file to import")
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true")
    group.add_argument("--write", action="store_true")
    args = parser.parse_args()
    print(json.dumps(import_jsonl(Path(args.jsonl_path), Path(args.db_path), dry_run=args.dry_run), indent=2))


if __name__ == "__main__":
    main()
