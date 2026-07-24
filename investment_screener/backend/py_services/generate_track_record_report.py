#!/usr/bin/env python3
"""
generate_track_record_report.py - Python utility script.

Purpose:
    Generate track record report — E3 rolling hit-rate stats.

Joins predictions.jsonl and predictions_graded.jsonl into per-claim-type hit
rates. This is the "graded-predictions section" /weekly-review surfaces —
expected to be sparse for a while after this ships, which is fine.

Usage:
    python3 generate_track_record_report.py [--json]

Key Input Dependencies:
    - (stale reference removed, Wave 4 Task 12: build_report(predictions_path,
      graded_path) never actually reads or references trade-log.json anywhere
      in this file's body — confirmed dead docstring text during Wave 4 Task 0)

Layer:
    Backend / Python Services

Usage Examples:
    python3 generate_track_record_report.py [--json]

Key Functions (Index):
    - compute_hit_rates()
    - build_report()
    - main()

Key Input Dependencies:
    None

Key Output Dependencies:
    None
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import sys as _sys

_PY_SERVICES_DIR = Path(__file__).resolve().parent
if str(_PY_SERVICES_DIR) not in _sys.path:
    _sys.path.insert(0, str(_PY_SERVICES_DIR))

from intelligence.db_client import initialize_db
from intelligence.event_repository import list_active_events_by_type

REPO_ROOT = _PY_SERVICES_DIR.resolve().parents[2]
# _PY_SERVICES_DIR is investment_screener/backend/py_services, so its real
# data/ sibling is one level up (investment_screener/backend/data/), not two
# (REPO_ROOT/data/) -- confirmed against backtest_harness.py's equivalent
# DATA_DIR constant. The prior parents[2]-based path silently pointed at a
# nonexistent investment_screener/data/ directory; every existing test
# passes an explicit db_path override so this only ever affected the
# never-exercised default (found during Wave 5D Task 6's real-cycle check,
# fixed here while cutting alert_manager.py over as Task 8's missed consumer).
DEFAULT_INTEL_DB_PATH = str(_PY_SERVICES_DIR.resolve().parents[1] / "data/intelligence.sqlite")

_VERDICTS = ("correct", "incorrect", "inconclusive")


def _load_predictions_from_ledger(db_path: str) -> list[dict[str, Any]]:
    """Load every PREDICTION_CLAIM event's payload from intelligence.sqlite.

    Replaces prediction_ledger.load_predictions()'s JSONL read (Wave 5D Task 3
    consumer cutover) -- Task 2's dual-write already mirrors every JSONL
    append into ``intelligence_event`` as a PREDICTION_CLAIM row, so this
    reads the same logical records from the SQLite read model instead.
    """
    conn = initialize_db(db_path)
    events = list_active_events_by_type(conn, "PREDICTION_CLAIM")
    return [json.loads(e["payload_json"]) for e in events if e["payload_json"]]


def _load_graded_from_ledger(db_path: str) -> list[dict[str, Any]]:
    """Load every PREDICTION_GRADED event's payload from intelligence.sqlite."""
    conn = initialize_db(db_path)
    events = list_active_events_by_type(conn, "PREDICTION_GRADED")
    return [json.loads(e["payload_json"]) for e in events if e["payload_json"]]


def compute_hit_rates(predictions: list[dict[str, Any]], graded: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute per-claim-type hit rate from graded predictions only.

    hitRate excludes "inconclusive" verdicts from its denominator — a claim
    type with only inconclusive grades so far has a null (not 0.0) hit rate.
    """
    graded_by_id = {g["predictionId"]: g for g in graded}
    predictions_by_id = {p["id"]: p for p in predictions}

    by_type: dict[str, dict[str, int]] = {}
    for prediction_id, grade in graded_by_id.items():
        prediction = predictions_by_id.get(prediction_id)
        if prediction is None:
            continue
        claim_type = prediction["type"]
        bucket = by_type.setdefault(claim_type, {v: 0 for v in _VERDICTS})
        bucket[grade["verdict"]] += 1

    report: dict[str, Any] = {}
    for claim_type, counts in by_type.items():
        graded_total = sum(counts.values())
        decisive = counts["correct"] + counts["incorrect"]
        hit_rate = round(counts["correct"] / decisive, 4) if decisive else None
        report[claim_type] = {**counts, "gradedTotal": graded_total, "hitRate": hit_rate}
    return report


def build_report(db_path: str = DEFAULT_INTEL_DB_PATH) -> dict[str, Any]:
    """Build the full track-record report dict.

    Args:
        db_path: Path to intelligence.sqlite to read PREDICTION_CLAIM/
            PREDICTION_GRADED events from. Tests should override this with
            a tmp_path-scoped sqlite file so they never read/write the real,
            tracked intelligence.sqlite.
    """
    predictions = _load_predictions_from_ledger(db_path)
    graded = _load_graded_from_ledger(db_path)
    return {
        "generatedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "totalPredictions": len(predictions),
        "totalGraded": len(graded),
        "totalUngraded": len(predictions) - len(graded),
        "byClaimType": compute_hit_rates(predictions, graded),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the E3 track-record report")
    parser.add_argument("--json", action="store_true", help="Print raw JSON instead of a summary")
    args = parser.parse_args()

    report = build_report()
    if args.json:
        print(json.dumps(report, indent=2))
        return

    print(f"Track record — {report['totalGraded']}/{report['totalPredictions']} graded "
          f"({report['totalUngraded']} pending maturity)")
    if not report["byClaimType"]:
        print("  No graded predictions yet.")
        return
    for claim_type, stats in report["byClaimType"].items():
        rate = f"{stats['hitRate']:.0%}" if stats["hitRate"] is not None else "n/a"
        print(f"  {claim_type:<20} hit rate {rate:>5}  "
              f"({stats['correct']} correct / {stats['incorrect']} incorrect / {stats['inconclusive']} inconclusive)")


if __name__ == "__main__":
    main()
