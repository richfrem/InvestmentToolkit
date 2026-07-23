#!/usr/bin/env python3
"""One-time migration: backfill the real data/daily-briefs/*.json snapshots into the
Intelligence Ledger as REVIEW_DAILY events (Wave 5C, ADR-029).

Uses the exact same append_event/replay_events_to_db machinery daily_brief.py's own
dual-write block already uses, and the same idempotency_key format
(daily-brief-{date}) — so a future real daily_brief.py run for an already-backfilled
date never double-writes.

Usage:
    python3 migrate_daily_briefs_to_ledger.py --dry-run
    python3 migrate_daily_briefs_to_ledger.py --write
"""
import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))

DEFAULT_BRIEFS_DIR = REPO_ROOT / "investment_screener/backend/data/daily-briefs"
DEFAULT_DB_PATH = REPO_ROOT / "investment_screener/backend/data/intelligence.sqlite"


def migrate(briefs_dir: Path, jsonl_path: Path, db_path: Path, dry_run: bool = True) -> dict:
    """Backfill every data/daily-briefs/*.json snapshot into intelligence_event.

    Args:
        briefs_dir: Directory containing one {date}.json snapshot file per day.
        jsonl_path: observations.jsonl ledger to append REVIEW_DAILY events to.
        db_path: intelligence.sqlite to replay the ledger into.
        dry_run: When True (default), report counts without writing anything.

    Returns:
        {"source_count": int, "written_count": int, "skipped": list[str]}
    """
    from intelligence.event_store import append_event
    from intelligence.replay_ledger import replay_events_to_db
    from intelligence.db_client import initialize_db

    files = sorted(briefs_dir.glob("*.json")) if briefs_dir.exists() else []
    skipped: list[str] = []
    report = {"source_count": len(files), "written_count": 0, "skipped": skipped}

    if dry_run:
        for f in files:
            with open(f) as fh:
                raw = json.load(fh)
            if not raw.get("date"):
                skipped.append(f.name)
        return report

    for f in files:
        with open(f) as fh:
            raw = json.load(fh)
        date_str = raw.get("date")
        if not date_str:
            skipped.append(f.name)
            continue
        append_event(
            str(jsonl_path),
            event_type="REVIEW_DAILY",
            effective_at=date_str,
            status="ACTIVE",
            title=f"Daily Brief for {date_str}",
            body_markdown="Generated daily brief summary metrics.",
            ticker=None,
            source_id="wave5c-migration-backfill",
            payload=raw,
            idempotency_key=f"daily-brief-{date_str}",
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
    parser.add_argument("--briefs-dir", default=str(DEFAULT_BRIEFS_DIR))
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--jsonl-path", default=None, help="Defaults to the standard observations.jsonl ledger path.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true")
    group.add_argument("--write", action="store_true")
    args = parser.parse_args()

    from intelligence.event_store import _default_jsonl_path
    jsonl_path = Path(args.jsonl_path) if args.jsonl_path else _default_jsonl_path()

    report = migrate(Path(args.briefs_dir), jsonl_path, Path(args.db_path), dry_run=args.dry_run)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
