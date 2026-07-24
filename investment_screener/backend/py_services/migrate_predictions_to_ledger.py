#!/usr/bin/env python3
"""One-time migration: backfill the real data/predictions.jsonl claims into the Intelligence
Ledger as PREDICTION_CLAIM events (Wave 5D, ADR-029).

Widens the intelligence_event.event_type CHECK constraint first (via
widen_event_type_constraint, rebuild-and-copy, verified row-for-row) since PREDICTION_CLAIM
does not exist in the live constraint before this wave. Then uses the same append_event/
replay_events_to_db machinery every other Wave 5 domain uses, and the same idempotency_key
format (prediction-claim-{id}) prediction_ledger.py's own dual-write already uses (Task 2) --
so a future real harvest_predictions.py run for an already-backfilled claim never double-writes.

Usage:
    python3 migrate_predictions_to_ledger.py --dry-run
    python3 migrate_predictions_to_ledger.py --write
"""
import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))

DEFAULT_PREDICTIONS_PATH = REPO_ROOT / "investment_screener/backend/data/predictions.jsonl"
DEFAULT_DB_PATH = REPO_ROOT / "investment_screener/backend/data/intelligence.sqlite"


def migrate(predictions_path: Path, jsonl_path: Path, db_path: Path, dry_run: bool = True) -> dict:
    """Backfill every data/predictions.jsonl claim into intelligence_event.

    Args:
        predictions_path: Path to predictions.jsonl (source of truth during migration).
        jsonl_path: observations.jsonl ledger to append PREDICTION_CLAIM events to.
        db_path: intelligence.sqlite to widen the constraint on and replay the ledger into.
        dry_run: When True (default), report counts without writing or widening anything.

    Returns:
        {"source_count": int, "written_count": int, "skipped": list[str]}
    """
    from intelligence.event_store import append_event
    from intelligence.replay_ledger import replay_events_to_db
    from intelligence.db_client import initialize_db
    from intelligence.migrations.widen_event_type_add_predictions import (
        widen_event_type_constraint,
    )

    records = []
    skipped: list[str] = []
    if predictions_path.exists():
        with open(predictions_path) as f:
            for i, line in enumerate(f):
                if not line.strip():
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    skipped.append(f"line {i}: invalid JSON")

    report = {"source_count": len(records), "written_count": 0, "skipped": skipped}

    if dry_run:
        for r in records:
            if not r.get("id") or not r.get("ticker"):
                skipped.append(f"record missing id/ticker: {r}")
        return report

    conn = initialize_db(str(db_path))
    widen_result = widen_event_type_constraint(conn)
    assert widen_result["before_row_count"] == widen_result["after_row_count"], (
        f"Constraint widening lost rows: {widen_result}"
    )
    conn.close()

    for r in records:
        if not r.get("id") or not r.get("ticker"):
            skipped.append(f"record missing id/ticker: {r}")
            continue
        append_event(
            str(jsonl_path),
            event_type="PREDICTION_CLAIM",
            effective_at=r.get("claimDate") or "",
            status="ACTIVE",
            title=f"Prediction claim: {r['ticker']} {r.get('type')} ({r.get('claimDate')})",
            body_markdown=f"Direction: {r.get('direction')}, horizon: "
                           f"{r.get('horizonDays')} days.",
            ticker=r["ticker"],
            source_id="wave5d-migration-backfill",
            payload=r,
            idempotency_key=f"prediction-claim-{r['id']}",
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
    parser.add_argument("--predictions-path", default=str(DEFAULT_PREDICTIONS_PATH))
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument(
        "--jsonl-path", default=None,
        help="Defaults to the standard observations.jsonl ledger path.",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true")
    group.add_argument("--write", action="store_true")
    args = parser.parse_args()

    from intelligence.event_store import _default_jsonl_path
    jsonl_path = Path(args.jsonl_path) if args.jsonl_path else _default_jsonl_path()

    report = migrate(
        Path(args.predictions_path), jsonl_path, Path(args.db_path), dry_run=args.dry_run
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
