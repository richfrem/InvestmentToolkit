"""Generate track record report — E3 rolling hit-rate stats.

Joins predictions.jsonl and predictions_graded.jsonl into per-claim-type hit
rates. This is the "graded-predictions section" /weekly-review surfaces —
expected to be sparse for a while after this ships, which is fine.

Usage:
    python3 generate_track_record_report.py [--json]
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from prediction_ledger import GRADED_PATH, PREDICTIONS_PATH, load_graded, load_predictions

_VERDICTS = ("correct", "incorrect", "inconclusive")


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


def build_report(
    predictions_path: Path = PREDICTIONS_PATH, graded_path: Path = GRADED_PATH
) -> dict[str, Any]:
    """Build the full track-record report dict."""
    predictions = load_predictions(predictions_path)
    graded = load_graded(graded_path)
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
