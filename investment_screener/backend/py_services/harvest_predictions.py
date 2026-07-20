#!/usr/bin/env python3
"""
harvest_predictions.py - Python utility script.

Purpose:
    Harvest predictions — E3 claim harvester, reads persisted artifacts only.

Never modifies projections/*.json, rebalance_plan.json, or
thesis_breaker_state.json — purely additive, reads them and appends new
claims to data/predictions.jsonl. Dedup is done by comparing against the
most recently harvested claim of the same (ticker, type) already on the
ledger — no separate state file.

Usage:
    python3 harvest_predictions.py [--dry-run]

Key Input Dependencies:
    - investment_screener/backend/data/daily-briefs/ (Aggregates daily performance)

Layer:
    Backend / Python Services

Usage Examples:
    python3 harvest_predictions.py [--dry-run]

Key Functions (Index):
    - _now_iso()
    - _hash_claim()
    - _load_projection_from_db()
    - build_action_rating_claim()
    - build_dcf_fair_value_claim()
    - build_rebalance_order_claims()
    - build_breaker_forecast_claims()
    - harvest_rebalance_and_breaker_claims()
    - _price_on_or_after()
    - _fetch_base_prices()
    - _append_if_new()
    - harvest_action_and_dcf_claims()
    - main()

Key Input Dependencies:
    None

Key Output Dependencies:
    None
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
DB_PATH = DATA_DIR / "domain_model.sqlite"

sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))
from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.projection_repository import (  # noqa: E402
    get_latest_projection_by_source,
    list_symbols_with_projections,
)

_BULLISH_ACTIONS = {"INITIATE", "ACCUMULATE"}
_BEARISH_ACTIONS = {"TRIM", "EXIT"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _hash_claim(claim: dict[str, Any]) -> str:
    """Stable hash of a claim payload for traceability (not used for dedup)."""
    canonical = json.dumps(claim, sort_keys=True)
    return hashlib.sha256(canonical.encode()).hexdigest()


def _load_projection_from_db(conn, investment_id: str) -> dict[str, Any] | None:
    """Load the latest AI_AGENT projection for an investment from
    domain_model.sqlite's ``projection_version`` table (Wave 2 consumer
    cutover), reconstructing the same {"aiThesis", "analyticsLog", "snapshot"}
    shape ``build_action_rating_claim``/``build_dcf_fair_value_claim`` expect —
    those two builder functions are unchanged.

    Replaces the former ``projections/{TICKER}.json`` flat-file read (the
    ``projections/`` directory was archived after the Wave 1 SQLite cutover
    and no longer exists on disk — this was a real, confirmed-dead read path).
    Mirrors ``get_latest_projection_by_source(..., "AI_AGENT")``'s existing
    "prefer the latest AI_AGENT-sourced row" convention (same as
    ``compute_conviction_scores.py``'s ``_load_dcf``), and preserves this
    function's own pre-migration "no AI_AGENT entry -> None, skip this
    ticker" behavior exactly (no fallback to a non-AI_AGENT row, unlike
    ``compute_conviction_scores.py``'s fallback -- the original
    ``_load_projection`` never fell back either).
    """
    entry = get_latest_projection_by_source(conn, investment_id, "AI_AGENT")
    if entry is None:
        return None
    analytics_log = json.loads(entry["analytics_log_json"]) if entry.get("analytics_log_json") else {}
    snapshot = json.loads(entry["snapshot_json"]) if entry.get("snapshot_json") else {}
    return {
        "aiThesis": {
            "action": entry.get("action"),
            "analyzedAt": entry.get("analyzed_at"),
            "fairValue": entry.get("fair_value"),
        },
        "analyticsLog": analytics_log,
        "snapshot": snapshot,
    }


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


REBALANCE_PLAN_PATH = DATA_DIR / "rebalance_plan.json"
THESIS_BREAKER_STATE_PATH = DATA_DIR / "thesis_breaker_state.json"
TARGET_PATH = DATA_DIR / "theses/target-portfolio.json"


def build_rebalance_order_claims(rebalance_plan: dict[str, Any], claim_date: str) -> list[dict[str, Any]]:
    """Extract rebalance_order claims from a rebalance_plan.json dict.

    buy -> bullish, sell -> bearish. gateWarningsPresent is recorded but not
    itself gradable — it's traceability only, matching the design's
    read-only posture toward risk_officer/thesis-breaker warn flags.
    """
    claims = []
    for order in rebalance_plan.get("orders", []):
        ticker = order.get("ticker")
        action = order.get("action")
        if not ticker or action not in ("buy", "sell"):
            continue
        direction = "bullish" if action == "buy" else "bearish"
        gate_warnings_present = bool(order.get("riskGateWarnings") or order.get("breakerWarnings"))
        claims.append({
            "ticker": ticker, "type": "rebalance_order", "date": claim_date,
            "claim": {"action": action, "gateWarningsPresent": gate_warnings_present},
            "direction": direction,
        })
    return claims


def build_breaker_forecast_claims(
    breaker_state: dict[str, Any], target_data: dict[str, Any], claim_date: str
) -> list[dict[str, Any]]:
    """Extract breaker_forecast claims — only TRIGGERED breakers are claims.

    A breaker at OK status is the absence of a prediction, not one.
    """
    definitions = {
        (h["ticker"], b["id"]): b
        for h in target_data.get("holdings", [])
        for b in h.get("thesisBreakers", [])
    }
    claims = []
    for ticker, breakers in (breaker_state.get("holdings") or {}).items():
        for breaker_id, entry in breakers.items():
            if entry.get("status") != "TRIGGERED":
                continue
            definition = definitions.get((ticker, breaker_id), {})
            claims.append({
                "ticker": ticker, "type": "breaker_forecast", "date": claim_date,
                "claim": {"breakerId": breaker_id, "metric": definition.get("metric"), "status": "TRIGGERED"},
                "direction": "bearish",
            })
    return claims


def harvest_rebalance_and_breaker_claims(
    rebalance_plan_path: Path = REBALANCE_PLAN_PATH,
    thesis_breaker_state_path: Path = THESIS_BREAKER_STATE_PATH,
    target_portfolio_path: Path = TARGET_PATH,
    predictions_path: Path = PREDICTIONS_PATH,
) -> list[dict[str, Any]]:
    """Harvest rebalance_order and breaker_forecast claims, if their artifacts exist.

    Neither artifact existing yet (rebalance_plan.json is only written after
    a /rebalance run; thesis_breaker_state.json may have zero holdings
    populated) is a normal, expected state — not an error.
    """
    existing = load_predictions(predictions_path)
    new_records: list[dict[str, Any]] = []

    if rebalance_plan_path.exists():
        with open(rebalance_plan_path) as f:
            rebalance_plan = json.load(f)
        claim_date = (rebalance_plan.get("generatedAt") or "")[:10]
        if claim_date:
            for claim in build_rebalance_order_claims(rebalance_plan, claim_date):
                new_records += _append_if_new(claim, existing, predictions_path)

    if thesis_breaker_state_path.exists() and target_portfolio_path.exists():
        with open(thesis_breaker_state_path) as f:
            breaker_state = json.load(f)
        with open(target_portfolio_path) as f:
            target_data = json.load(f)
        claim_date = (breaker_state.get("generatedAt") or "")[:10]
        if claim_date:
            for claim in build_breaker_forecast_claims(breaker_state, target_data, claim_date):
                new_records += _append_if_new(claim, existing, predictions_path)

    return new_records


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
        print(f"  Harvest skipped for {new_id}: price lookup failed", file=sys.stderr)
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
    db_path: Path = DB_PATH,
    predictions_path: Path = PREDICTIONS_PATH,
) -> list[dict[str, Any]]:
    """Harvest action_rating and dcf_fair_value claims from every investment
    with at least one projection_version row in domain_model.sqlite.

    Args:
        db_path: Path to domain_model.sqlite (Wave 2 consumer cutover --
            replaces the former projections/*.json directory glob, which no
            longer exists on disk since Wave 1's archive).
        predictions_path: Ledger path to read existing state from and append to.

    Returns:
        Every newly appended prediction record this run.
    """
    existing = load_predictions(predictions_path)
    new_records: list[dict[str, Any]] = []
    conn = initialize_db(str(db_path))
    for ticker in list_symbols_with_projections(conn):
        projection = _load_projection_from_db(conn, ticker)
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
    new_records += harvest_rebalance_and_breaker_claims()
    print(f"Harvested {len(new_records)} new claim(s).")


if __name__ == "__main__":
    main()
