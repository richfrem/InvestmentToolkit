"""
recommendation.py — THE canonical recommendation (action) function.

Purpose:
    Single source of truth for TRIM / EXIT / ACCUMULATE / INITIATE / MAINTAIN /
    WATCHLIST across the whole app (API, every page, every script).
Layer:
    Business logic (pure function + thin SQLite loader).
Usage:
    python3 recommendation.py --all [--db PATH]   -> JSON {TICKER: {...}}
Key Functions:
    valuation_signal(upside_pct)            BUY / HOLD / SELL band
    recommend(held, upside_pct, exit_signal) pure decision
    recommend_all(db_path)                  per-ticker records for the API
Key Input Dependencies:
    domain_model.sqlite (holdings, prices, latest projection fair value),
    thesis_breaker_state.json (TRIGGERED breakers = exit signal).

Policy: a recommendation is decided BEFORE targets. It uses valuation against
the latest fair value plus an explicit exit signal. Target weights play no part;
the app shows the current holding and asks the user to set the target.

Rules (held):    exit signal -> EXIT; SELL band -> TRIM; BUY band -> ACCUMULATE;
                 otherwise MAINTAIN (also when there is no valuation).
Rules (not held): BUY band -> INITIATE; otherwise WATCHLIST.
The +/-15% band matches the standing-decision materiality threshold.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ACT_THRESHOLD_PCT = 15.0

ACTION_EMOJI = {
    "INITIATE": "🟢", "ACCUMULATE": "🔵", "MAINTAIN": "⚪",
    "TRIM": "🟡", "EXIT": "🔴", "WATCHLIST": "👁️",
}


def valuation_signal(upside_pct: float | None) -> str | None:
    """Classify upside to fair value into BUY / HOLD / SELL (None if unknown)."""
    if upside_pct is None:
        return None
    if upside_pct >= ACT_THRESHOLD_PCT:
        return "BUY"
    if upside_pct <= -ACT_THRESHOLD_PCT:
        return "SELL"
    return "HOLD"


def recommend(held: bool, upside_pct: float | None, exit_signal: bool = False) -> dict[str, Any]:
    """Return the one recommendation for a ticker.

    Args:
        held: True if shares > 0 in any account.
        upside_pct: (fair value - price) / price * 100, or None if no valuation.
        exit_signal: Explicit exit (TRIGGERED thesis breaker or EXIT projection).

    Returns:
        {"action", "reason", "valuation", "upside_pct"}.
    """
    val = valuation_signal(upside_pct)
    if not held:
        action = "INITIATE" if val == "BUY" else "WATCHLIST"
        reason = (f"Not held; valuation {val} ({upside_pct:+.0f}% to fair value)"
                  if val else "Not held; no valuation")
    elif exit_signal:
        action, reason = "EXIT", "Explicit exit signal (thesis breaker or EXIT projection)"
    elif val == "SELL":
        action, reason = "TRIM", f"Price {abs(upside_pct):.0f}% above fair value"
    elif val == "BUY":
        action, reason = "ACCUMULATE", f"Price {upside_pct:.0f}% below fair value"
    elif val == "HOLD":
        action, reason = "MAINTAIN", f"Within ±{ACT_THRESHOLD_PCT:.0f}% of fair value"
    else:
        action, reason = "MAINTAIN", "No valuation available"
    return {"action": action, "reason": reason, "valuation": val, "upside_pct": upside_pct}


def _triggered_tickers() -> set[str]:
    """Tickers with at least one TRIGGERED thesis breaker (read-only)."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "investment_screener/backend/py_services"))
    try:
        from thesis_breakers import STATE_PATH
        state = json.loads(Path(STATE_PATH).read_text()).get("holdings", {})
    except Exception:
        return set()
    return {t for t, bs in state.items() if any(b.get("status") == "TRIGGERED" for b in bs.values())}


def recommend_all(db_path: str | None = None) -> dict[str, dict[str, Any]]:
    """Recommendation record for every investment in domain_model.sqlite."""
    py = str(Path(__file__).resolve().parents[3] / "investment_screener/backend/py_services")
    sys.path.insert(0, py)
    from domain_model.db_client import initialize_db
    from domain_model.projection_repository import get_latest_projection, get_latest_projection_by_source
    from portfolio_io import compute_weights, load_portfolio_state
    from thesis_breakers import DB_PATH

    state = load_portfolio_state(None, db_path=db_path)
    weights = compute_weights(state["shares"], state["prices"], state["total_usd"])
    triggered = _triggered_tickers()
    out: dict[str, dict[str, Any]] = {}
    conn = initialize_db(db_path or str(DB_PATH))
    try:
        for inv_id, symbol in conn.execute("SELECT investment_id, symbol FROM investment;").fetchall():
            entry = (get_latest_projection_by_source(conn, inv_id, "AI_AGENT")
                     or get_latest_projection(conn, inv_id))
            fv = entry.get("fair_value") if entry else None
            price = state["prices"].get(symbol)
            if not price and entry and entry.get("snapshot_json"):
                price = json.loads(entry["snapshot_json"]).get("price")
            upside = round((fv - price) / price * 100, 1) if fv and price and price > 0 else None
            held = (state["shares"].get(symbol) or 0) > 0
            exit_signal = symbol in triggered or bool(entry and entry.get("action") == "EXIT")
            rec = recommend(held, upside, exit_signal)
            rec.update(ticker=symbol, held=held, current_weight_pct=round(weights.get(symbol, 0.0), 2),
                       fair_value=fv, price=price)
            out[symbol] = rec
    finally:
        conn.close()
    return out


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", required=True)
    ap.add_argument("--db", default=None)
    print(json.dumps(recommend_all(ap.parse_args().db)))
