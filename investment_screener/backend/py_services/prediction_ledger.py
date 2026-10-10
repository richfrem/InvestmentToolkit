"""
prediction_ledger.py - Prediction claims and grades in the intelligence ledger.

Purpose:
    Prediction ledger: E3 append-only claim/grade store and grading primitive. The durable
    store is the intelligence ledger (`intelligence_event`, event types
    `PREDICTION_CLAIM` / `PREDICTION_GRADED`); `append_prediction()` / `append_grade()` write
    there and nowhere else.

    See docs/superpowers/specs/2026-07-10-phase4-e3-prediction-ledger-design.md for the
    claim schema and grading rationale.

Layer:
    Backend / Python Services

Key Functions (Index):
    - make_prediction_id()
    - append_prediction()
    - append_grade()
    - latest_prediction_for()
    - grade_claim()

Key Input Dependencies:
    - intelligence.sqlite (via intelligence.event_store)

Key Output Dependencies:
    - PREDICTION_CLAIM / PREDICTION_GRADED events in intelligence_event
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]

_INTEL_DIR = REPO_ROOT / "investment_screener/backend/py_services"
if str(_INTEL_DIR) not in _sys.path:
    _sys.path.insert(0, str(_INTEL_DIR))

from intelligence.db_client import initialize_db  # noqa: E402
from intelligence.event_store import append_event as _append_event, default_db_path  # noqa: E402

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


def append_prediction(record: dict[str, Any], db_path: str | Path | None = None) -> None:
    """Write one PREDICTION_CLAIM event to the intelligence ledger.

    Real prediction records key the claim date as "date" (per schemas/prediction.schema.json),
    never "claimDate". The write is idempotent on ``prediction-claim-<id>``.

    Args:
        record: The prediction record (id, ticker, type, date, direction, horizonDays, ...).
        db_path: intelligence.sqlite to write to; defaults to the standard path.
    """
    ticker = record.get("ticker")
    claim_type = record.get("type")
    claim_date = record.get("date")
    conn = initialize_db(str(db_path or default_db_path()))
    try:
        _append_event(
            conn,
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
    finally:
        conn.close()


def append_grade(record: dict[str, Any], db_path: str | Path | None = None) -> None:
    """Write one PREDICTION_GRADED event to the intelligence ledger.

    Args:
        record: The grade record (predictionId, ticker, outcome, relativeReturn, gradedAt, ...).
        db_path: intelligence.sqlite to write to; defaults to the standard path.
    """
    ticker = record.get("ticker")
    prediction_id = record.get("predictionId")
    outcome = record.get("outcome")
    conn = initialize_db(str(db_path or default_db_path()))
    try:
        _append_event(
            conn,
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
            idempotency_key=f"prediction-grade-{prediction_id}",
        )
    finally:
        conn.close()


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
