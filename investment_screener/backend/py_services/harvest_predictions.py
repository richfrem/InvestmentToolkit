"""Harvest predictions — E3 claim harvester, reads persisted artifacts only.

Never modifies projections/*.json, rebalance_plan.json, or
thesis_breaker_state.json — purely additive, reads them and appends new
claims to data/predictions.jsonl. Dedup is done by comparing against the
most recently harvested claim of the same (ticker, type) already on the
ledger — no separate state file.

Usage:
    python3 harvest_predictions.py [--dry-run]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from prediction_ledger import (  # noqa: E402
    HORIZON_DAYS,
    PREDICTIONS_PATH,
    append_prediction,
    latest_prediction_for,
    load_predictions,
    make_prediction_id,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = REPO_ROOT / "investment_screener/backend/data"
PROJECTIONS_DIR = DATA_DIR / "projections"

_BULLISH_ACTIONS = {"INITIATE", "ACCUMULATE"}
_BEARISH_ACTIONS = {"TRIM", "EXIT"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _hash_claim(claim: dict[str, Any]) -> str:
    """Stable hash of a claim payload for traceability (not used for dedup)."""
    canonical = json.dumps(claim, sort_keys=True)
    return hashlib.sha256(canonical.encode()).hexdigest()


def _load_projection(path: Path) -> dict[str, Any] | None:
    """Load a projection file, unwrapping its list-wrapper if present."""
    with open(path) as f:
        data = json.load(f)
    if isinstance(data, list):
        return data[0] if data else None
    return data


def build_action_rating_claim(ticker: str, projection: dict[str, Any]) -> dict[str, Any] | None:
    """Extract an action_rating claim from a projection, or None if not gradable.

    MAINTAIN/WATCHLIST carry no directional prediction and are not harvested.
    """
    ai_thesis = projection.get("aiThesis", {}) or {}
    action = ai_thesis.get("action")
    if action not in (_BULLISH_ACTIONS | _BEARISH_ACTIONS):
        return None
    date_str = (ai_thesis.get("analyzedAt") or "")[:10]
    if not date_str:
        return None
    direction = "bullish" if action in _BULLISH_ACTIONS else "bearish"
    return {
        "ticker": ticker, "type": "action_rating", "date": date_str,
        "claim": {"action": action}, "direction": direction,
    }


def build_dcf_fair_value_claim(ticker: str, projection: dict[str, Any]) -> dict[str, Any] | None:
    """Extract a dcf_fair_value claim, preferring analyticsLog.dcf over aiThesis.

    Falls back to aiThesis.fairValue + snapshot.price (deriving upsidePct)
    when analyticsLog.dcf is absent — true for 78/80 current projections,
    since most predate the Phase 2a valuation-committee gate.
    """
    ai_thesis = projection.get("aiThesis", {}) or {}
    dcf = (projection.get("analyticsLog") or {}).get("dcf")
    date_str = (ai_thesis.get("analyzedAt") or "")[:10]
    if not date_str:
        return None

    if dcf and dcf.get("weightedFairValue") is not None and dcf.get("upsidePct") is not None:
        fair_value = dcf["weightedFairValue"]
        upside_pct = dcf["upsidePct"]
        source = "analyticsLog.dcf"
    else:
        fair_value = ai_thesis.get("fairValue")
        current_price = (projection.get("snapshot") or {}).get("price")
        if fair_value is None or not current_price:
            return None
        upside_pct = round((fair_value - current_price) / current_price * 100, 2)
        source = "aiThesis"

    direction = "bullish" if upside_pct > 0 else "bearish"
    return {
        "ticker": ticker, "type": "dcf_fair_value", "date": date_str,
        "claim": {"fairValue": fair_value, "upsidePct": upside_pct, "source": source},
        "direction": direction,
    }


def _price_on_or_after(rows: list[dict[str, Any]], target_date: str) -> float | None:
    """First close price on or after target_date; rows must be date-ascending."""
    for row in rows:
        if row["date"] >= target_date:
            return row["close"]
    return None


def _fetch_base_prices(ticker: str, claim_date: str) -> tuple[float, float] | None:
    """Fetch (ticker close, SPY close) on/after claim_date via market_data.get_prices()."""
    from market_data import get_prices
    result = get_prices([ticker, "SPY"], period="2y", interval="1d")
    t_rows = result.get(ticker, {}).get("data", [])
    spy_rows = result.get("SPY", {}).get("data", [])
    t_price = _price_on_or_after(t_rows, claim_date)
    spy_price = _price_on_or_after(spy_rows, claim_date)
    if t_price is None or spy_price is None:
        return None
    return t_price, spy_price


def _append_if_new(
    claim: dict[str, Any], existing: list[dict[str, Any]], predictions_path: Path
) -> list[dict[str, Any]]:
    """Append claim as a new prediction record unless it's an unchanged dup.

    Dedup rule: skip if the most recently logged claim of this (ticker, type)
    has an identical claim payload. Defends against id collision (same
    ticker+type+date logged twice with a different value) by skipping with a
    stderr warning rather than silently overwriting.

    Returns:
        A list containing the new record, or [] if nothing was appended.
    """
    new_id = make_prediction_id(claim["ticker"], claim["type"], claim["date"])
    prior = latest_prediction_for(claim["ticker"], claim["type"], existing)
    if prior is not None and prior["claim"] == claim["claim"]:
        return []
    if any(r["id"] == new_id for r in existing):
        print(f"  WARNING: id collision, skipping: {new_id}", file=sys.stderr)
        return []

    prices = _fetch_base_prices(claim["ticker"], claim["date"])
    if prices is None:
        return []
    base_price, base_spy_price = prices

    record = {
        "v": 1,
        "id": new_id,
        "date": claim["date"],
        "ticker": claim["ticker"],
        "type": claim["type"],
        "claim": claim["claim"],
        "direction": claim["direction"],
        "horizonDays": HORIZON_DAYS[claim["type"]],
        "basePrice": base_price,
        "baseSpyPrice": base_spy_price,
        "confidence": None,
        "inputsHash": _hash_claim(claim["claim"]),
        "harvestedAt": _now_iso(),
    }
    append_prediction(record, predictions_path)
    existing.append(record)
    return [record]


def harvest_action_and_dcf_claims(
    projections_dir: Path = PROJECTIONS_DIR,
    predictions_path: Path = PREDICTIONS_PATH,
) -> list[dict[str, Any]]:
    """Harvest action_rating and dcf_fair_value claims from every projection file.

    Args:
        projections_dir: Directory of per-ticker projection JSON files.
        predictions_path: Ledger path to read existing state from and append to.

    Returns:
        Every newly appended prediction record this run.
    """
    existing = load_predictions(predictions_path)
    new_records: list[dict[str, Any]] = []
    for proj_file in sorted(projections_dir.glob("*.json")):
        ticker = proj_file.stem
        projection = _load_projection(proj_file)
        if projection is None:
            continue
        for builder in (build_action_rating_claim, build_dcf_fair_value_claim):
            claim = builder(ticker, projection)
            if claim is None:
                continue
            new_records += _append_if_new(claim, existing, predictions_path)
    return new_records


def main() -> None:
    parser = argparse.ArgumentParser(description="Harvest graded claims into the prediction ledger")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be harvested, don't write")
    args = parser.parse_args()

    if args.dry_run:
        existing = load_predictions(PREDICTIONS_PATH)
        print(f"{len(existing)} existing predictions on ledger. Dry-run: no writes performed.")
        return

    new_records = harvest_action_and_dcf_claims()
    print(f"Harvested {len(new_records)} new claim(s).")


if __name__ == "__main__":
    main()
