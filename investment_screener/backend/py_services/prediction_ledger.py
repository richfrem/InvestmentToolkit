"""Prediction ledger — E3 append-only claim/grade store and grading primitive.

Two append-only JSONL files, never rewritten in place:
  - data/predictions.jsonl        one record per harvested claim
  - data/predictions_graded.jsonl one record per graded outcome, referencing
                                   a prediction's id

See docs/superpowers/specs/2026-07-10-phase4-e3-prediction-ledger-design.md
for the full schema and grading rationale.

Usage:
    python3 prediction_ledger.py --validate

Key Input Dependencies:
    - investment_screener/backend/data/daily-briefs/ (Maintains prediction schema)
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = REPO_ROOT / "investment_screener/backend/data"
PREDICTIONS_PATH = DATA_DIR / "predictions.jsonl"
GRADED_PATH = DATA_DIR / "predictions_graded.jsonl"
SCHEMA_PATH = REPO_ROOT / "schemas/prediction.schema.json"

HORIZON_DAYS: dict[str, int] = {
    "action_rating": 90,
    "dcf_fair_value": 180,
    "rebalance_order": 90,
    "breaker_forecast": 90,
    "earnings_expectation": 90,
}

INCONCLUSIVE_BAND = 0.02


def make_prediction_id(ticker: str, claim_type: str, claim_date: str) -> str:
    """Build the stable, reconstructible id for one prediction record."""
    return f"{ticker}:{claim_type}:{claim_date}"


def _append_jsonl(record: dict[str, Any], path: Path) -> None:
    """Append one JSON record as a line, creating parent dirs as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(record) + "\n")


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    """Load every record from a JSONL file, or [] if it doesn't exist."""
    if not path.exists():
        return []
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def append_prediction(record: dict[str, Any], path: Path = PREDICTIONS_PATH) -> None:
    """Append one prediction record to predictions.jsonl."""
    _append_jsonl(record, path)


def append_grade(record: dict[str, Any], path: Path = GRADED_PATH) -> None:
    """Append one grade record to predictions_graded.jsonl."""
    _append_jsonl(record, path)


def load_predictions(path: Path = PREDICTIONS_PATH) -> list[dict[str, Any]]:
    """Load every prediction record on disk."""
    return _load_jsonl(path)


def load_graded(path: Path = GRADED_PATH) -> list[dict[str, Any]]:
    """Load every grade record on disk."""
    return _load_jsonl(path)


def latest_prediction_for(
    ticker: str, claim_type: str, predictions: list[dict[str, Any]]
) -> dict[str, Any] | None:
    """Return the most recently harvested prediction matching ticker+type, or None.

    Args:
        ticker: Ticker symbol.
        claim_type: One of HORIZON_DAYS's keys.
        predictions: Prediction records, in the order they were harvested
            (oldest first) — the same order load_predictions() returns.

    Returns:
        The last matching record, or None if no match exists.
    """
    matches = [p for p in predictions if p["ticker"] == ticker and p["type"] == claim_type]
    return matches[-1] if matches else None


def grade_claim(direction: str, relative_return: float, band: float = INCONCLUSIVE_BAND) -> str:
    """Grade a claim's outcome from its stated direction and realized relative return.

    Args:
        direction: "bullish" or "bearish".
        relative_return: Ticker return minus SPY return over the claim's horizon.
        band: Absolute relative-return threshold below which the outcome is
            "inconclusive" rather than decisively correct/incorrect.

    Returns:
        "correct", "incorrect", or "inconclusive".
    """
    if abs(relative_return) <= band:
        return "inconclusive"
    if direction == "bullish":
        return "correct" if relative_return > band else "incorrect"
    return "correct" if relative_return < -band else "incorrect"


def _validate_all() -> int:
    """Schema-validate every record in both JSONL files. Returns exit code.

    Passes PREDICTIONS_PATH/GRADED_PATH explicitly (not relying on
    load_predictions()/load_graded()'s own default parameter values) so that
    tests can monkeypatch the module-level globals and have this function
    pick up the new value — default parameter values are bound once at def
    time, not at call time, so relying on them here would silently ignore
    a monkeypatched global.
    """
    import jsonschema

    with open(SCHEMA_PATH) as f:
        schema = json.load(f)

    errors = 0
    for record in load_predictions(PREDICTIONS_PATH):
        try:
            jsonschema.validate(record, schema["definitions"]["prediction"])
        except jsonschema.ValidationError as exc:
            print(f"INVALID prediction {record.get('id')}: {exc.message}")
            errors += 1
    for record in load_graded(GRADED_PATH):
        try:
            jsonschema.validate(record, schema["definitions"]["grade"])
        except jsonschema.ValidationError as exc:
            print(f"INVALID grade {record.get('predictionId')}: {exc.message}")
            errors += 1

    if errors:
        print(f"{errors} invalid record(s).")
        return 1
    print("All prediction/grade records valid.")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Prediction ledger utilities")
    parser.add_argument("--validate", action="store_true", help="Schema-validate the ledger")
    args = parser.parse_args()

    if args.validate:
        raise SystemExit(_validate_all())
    parser.print_help()


if __name__ == "__main__":
    main()
