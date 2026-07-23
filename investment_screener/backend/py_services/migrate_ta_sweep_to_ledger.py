#!/usr/bin/env python3
"""One-time migration: backfill the real ta-sweep-results.json snapshot into the
Intelligence Ledger as TECHNICAL_SWEEP events (Wave 5B, ADR-029).

Uses the exact same append_event/replay_events_to_db machinery
ta_sweep_batch.py::save_sweep_results() already uses for new sweeps, so future real
sweeps and this one-time backfill share one idempotency-key format
(ta-sweep-{ticker}-{scan_date}) — a real future sweep for an already-backfilled
ticker/date never double-writes.

Usage:
    python3 migrate_ta_sweep_to_ledger.py --dry-run
    python3 migrate_ta_sweep_to_ledger.py --write
"""
import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))

DEFAULT_JSON_PATH = REPO_ROOT / "investment_screener/backend/data/ta-sweep-results.json"
DEFAULT_DB_PATH = REPO_ROOT / "investment_screener/backend/data/intelligence.sqlite"


def migrate(json_path: Path, jsonl_path: Path, db_path: Path, dry_run: bool = True) -> dict:
    """Backfill one ta-sweep-results.json snapshot into intelligence_event.

    Args:
        json_path: Source ta-sweep-results.json to read.
        jsonl_path: observations.jsonl ledger to append TECHNICAL_SWEEP events to.
        db_path: intelligence.sqlite to replay the ledger into.
        dry_run: When True (default), report counts without writing anything.

    Returns:
        {"source_count": int, "written_count": int, "skipped": list[str]}
    """
    from intelligence.event_store import append_event
    from intelligence.replay_ledger import replay_events_to_db
    from intelligence.db_client import initialize_db

    if not json_path.exists():
        raise FileNotFoundError(f"Source file not found: {json_path}")

    with open(json_path) as f:
        raw = json.load(f)
    scan_date = raw.get("scan_date")
    results = raw.get("results", [])
    skipped: list[str] = []

    report = {"source_count": len(results), "written_count": 0, "skipped": skipped}
    if dry_run:
        return report

    for res in results:
        ticker = res.get("ticker")
        if not ticker or not scan_date:
            skipped.append(str(res))
            continue
        append_event(
            str(jsonl_path),
            event_type="TECHNICAL_SWEEP",
            effective_at=scan_date,
            status="ACTIVE",
            title=f"TA Sweep for {ticker}",
            body_markdown=f"Batch technical indicators for {ticker}.",
            ticker=ticker,
            source_id="wave5b-migration-backfill",
            payload=res,
            idempotency_key=f"ta-sweep-{ticker}-{scan_date}",
        )
        report["written_count"] += 1

    conn = initialize_db(str(db_path))
    try:
        replay_events_to_db(str(jsonl_path), conn)
    finally:
        conn.close()

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-path", default=str(DEFAULT_JSON_PATH))
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--jsonl-path", default=None, help="Defaults to the standard observations.jsonl ledger path.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true")
    group.add_argument("--write", action="store_true")
    args = parser.parse_args()

    from intelligence.event_store import _default_jsonl_path
    jsonl_path = Path(args.jsonl_path) if args.jsonl_path else _default_jsonl_path()

    report = migrate(Path(args.json_path), jsonl_path, Path(args.db_path), dry_run=args.dry_run)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
