#!/usr/bin/env python3
"""
prediction_ledger.py - Python utility script.

Purpose:
    Prediction ledger — E3 append-only claim/grade store and grading primitive.

The durable store is the Intelligence Ledger (`intelligence_event`, event types
`PREDICTION_CLAIM`/`PREDICTION_GRADED`), since Wave 5D of the Domain Data Model v3.2
migration. `append_prediction()`/`append_grade()` write there exclusively.

Historical note: this module originally wrote two append-only JSONL files directly
(`data/predictions.jsonl`, `data/predictions_graded.jsonl`). Wave 5D cut over all 7 real
consumers to `intelligence_event` and archived `predictions.jsonl` via `git mv` (it's now
at `ARCHIVE/investment_screener/backend/data/predictions.jsonl`);
`predictions_graded.jsonl` never existed on disk. `_append_jsonl()`/`load_predictions()`/
`load_graded()` are kept as JSONL primitives only for `_validate_all()` (the `--validate`
CLI below), which can still schema-validate the archived file on demand.

See docs/superpowers/specs/2026-07-10-phase4-e3-prediction-ledger-design.md
for the full schema and grading rationale (pre-Wave-5D storage design; superseded by the
intelligence_event target described in
docs/architecture/supplementary-domain-schemas.md).

Usage:
    python3 prediction_ledger.py --validate

Key Input Dependencies:
    - investment_screener/backend/data/daily-briefs/ (Maintains prediction schema)

Layer:
    Backend / Python Services

Usage Examples:
    python3 prediction_ledger.py --validate

Key Functions (Index):
    - make_prediction_id()
    - _append_jsonl()
    - _load_jsonl()
    - append_prediction()
    - append_grade()
    - load_predictions()
    - load_graded()
    - latest_prediction_for()
    - grade_claim()
    - _validate_all()
    - main()

Key Input Dependencies:
    None

Key Output Dependencies:
    None
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

import sys as _sys

_INTEL_DIR = REPO_ROOT / "investment_screener/backend/py_services"
if str(_INTEL_DIR) not in _sys.path:
    _sys.path.insert(0, str(_INTEL_DIR))

from intelligence.event_store import append_event as _append_event  # noqa: E402

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


def _append_prediction_event(record: dict[str, Any], jsonl_path) -> None:
    """Write one PREDICTION_CLAIM event to the intelligence ledger.

    Isolated into its own function (rather than inlined in append_prediction) so a ledger
    outage can be simulated/monkeypatched in tests without touching the JSONL append path --
    JSONL remains authoritative during the dual-write window (Hybrid Exit Criteria).
    """
    from intelligence.event_store import _default_jsonl_path

    resolved_path = str(jsonl_path) if jsonl_path else str(_default_jsonl_path())
    ticker = record.get("ticker")
    claim_type = record.get("type")
    # Real prediction records key the claim date as "date" (per
    # schemas/prediction.schema.json), never "claimDate" -- confirmed by
    # sampling the real predictions.jsonl. Using the wrong key here silently
    # produced empty effective_at/"(None)" titles for every real backfilled
    # PREDICTION_CLAIM event (caught during Wave 5D Task 6's real-cycle
    # parity check).
    claim_date = record.get("date")
    _append_event(
        resolved_path,
        event_type="PREDICTION_CLAIM",
        effective_at=claim_date or "",
        status="ACTIVE",
        title=f"Prediction claim: {ticker} {claim_type} ({claim_date})",
        body_markdown=f"Direction: {record.get('direction')}, horizon: "
                       f"{record.get('horizonDays')} days.",
        ticker=ticker,
        source_id="prediction_ledger",
        payload=record,
        idempotency_key=f"prediction-claim-{record.get('id')}",
    )


def _append_grade_event(record: dict[str, Any], jsonl_path) -> None:
    """Write one PREDICTION_GRADED event to the intelligence ledger."""
    from intelligence.event_store import _default_jsonl_path

    resolved_path = str(jsonl_path) if jsonl_path else str(_default_jsonl_path())
    ticker = record.get("ticker")
    prediction_id = record.get("predictionId")
    outcome = record.get("outcome")
    _append_event(
        resolved_path,
        event_type="PREDICTION_GRADED",
        effective_at=record.get("gradedAt") or "",
        status="ACTIVE",
        title=f"Prediction grade: {ticker} "
              f"{prediction_id.split(':')[1] if prediction_id and ':' in prediction_id else ''} "
              f"({outcome})".replace("  ", " ").strip(),
        body_markdown=f"Outcome: {outcome}, relative return: "
                       f"{record.get('relativeReturn')}.",
        ticker=ticker,
        source_id="prediction_ledger",
        payload=record,
        supersedes_event_id=None,
        idempotency_key=f"prediction-grade-{prediction_id}",
    )


def append_prediction(
    record: dict[str, Any], path: Path = PREDICTIONS_PATH, jsonl_path=None
) -> None:
    """Append one PREDICTION_CLAIM event to the intelligence ledger.

    predictions.jsonl is no longer written here. Wave 5D's dual-write (this function,
    Task 2) was a temporary migration aid -- once all 7 real consumers were cut over to
    read intelligence_event (Task 3 + Task 8's alert_manager.py discovery) and the file
    was archived via `git mv` (Task 8), continuing to write predictions.jsonl here would
    silently un-archive it on the very next real prediction-harvest cycle (the exact
    "permanent hybrid state" this migration's Hybrid Exit Criteria forbids). The `path`
    parameter is kept, unused, only so every already-migrated call site
    (harvest_predictions.py, grade_predictions.py, etc.) keeps working without another
    signature change.

    The ledger write is now the sole write and is no longer wrapped in try/except --
    there is no JSONL fallback left to protect, so a real write failure must propagate
    rather than being silently logged and swallowed.
    """
    _append_prediction_event(record, jsonl_path)


def append_grade(
    record: dict[str, Any], path: Path = GRADED_PATH, jsonl_path=None
) -> None:
    """Append one PREDICTION_GRADED event to the intelligence ledger.

    predictions_graded.jsonl is no longer written -- same reasoning as append_prediction()
    above. It never existed on disk in this project's real data to begin with (confirmed
    at Wave 5D Task 0 and again at wave-exit).
    """
    _append_grade_event(record, jsonl_path)


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
