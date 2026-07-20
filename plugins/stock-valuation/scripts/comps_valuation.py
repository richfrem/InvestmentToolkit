#!/usr/bin/env python3
"""
comps_valuation.py (Python Service)
=====================================

Purpose:
    Peer-multiple cross-check for DCF fair value: computes EV/Sales for a
    curated peer set and applies the peer-median multiple to the target
    ticker's own revenue to derive an implied price range. EV/EBITDA comps
    is deliberately out of scope for this pass — no EBITDA source exists
    anywhere in the current data layer (see docs/architecture/ADR-valuation-committee.md).

Layer: Backend / Python Services / Valuation Math

Usage:
    python3 comps_valuation.py --ticker NVDA --peers AMD,AVGO,QCOM \
        --db-path investment_screener/backend/data/domain_model.sqlite --pretty

Key Functions:
    - load_latest_projection() - Reads the latest AI_AGENT (or latest-any-source)
      projection_version row for a ticker from domain_model.sqlite
    - compute_ev() - Enterprise value from price * shares + debt - cash
    - comps_implied_range() - Primary orchestrator: peer-median EV/Sales -> implied price range

Key Input Dependencies:
    - investment_screener/backend/data/portfolio.json (Internal state database)
    - investment_screener/backend/data/domain_model.sqlite (projection_version, ADR-029)
"""

import argparse
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from market_data import get_fundamentals  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))
from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.projection_repository import (  # noqa: E402
    get_latest_projection,
    get_latest_projection_by_source,
)


def load_latest_projection(ticker: str, db_path: str) -> dict | None:
    """Load the latest AI_AGENT projection_version row (or the latest of any
    source) for a ticker, reshaped to the legacy `{"snapshot": {...}}` dict
    shape this module's callers expect.

    Storage backend (Wave 1 Task 7A): reads `projection_version` via
    `domain_model.projection_repository`, not `projections/{TICKER}.json`
    directly (ADR-029). Mirrors portfolio_action.py's `_load_ai_upside()`
    Task 6 fix — prefers `get_latest_projection_by_source(..., "AI_AGENT")`
    over plain `MAX(version)`, since version numbers are not always
    chronological, falling back to `get_latest_projection` (any source) when
    no AI_AGENT row exists (mirroring the original file-based code's
    `projs[0]` fallback).

    Args:
        ticker: Ticker symbol.
        db_path: Path to domain_model.sqlite.

    Returns:
        `{"snapshot": {"price", "shares", "revenue", ...}}`, or None if the
        investment has no projection rows at all.
    """
    conn = initialize_db(str(db_path))
    try:
        row = conn.execute("SELECT investment_id FROM investment WHERE symbol = ?;", (ticker,)).fetchone()
        if row is None:
            return None
        investment_id = row[0]
        entry = get_latest_projection_by_source(conn, investment_id, "AI_AGENT")
        if entry is None:
            entry = get_latest_projection(conn, investment_id)
        if entry is None:
            return None
        snapshot = json.loads(entry["snapshot_json"]) if entry.get("snapshot_json") else {}
        return {"snapshot": snapshot}
    finally:
        conn.close()


def compute_ev(price: float, shares: float, debt: float, cash: float) -> float:
    """Enterprise value: market cap (price * shares) + debt - cash."""
    return price * shares + debt - cash


def _peer_ev_sales(ticker: str, db_path: str) -> float | None:
    """EV/Sales for one peer ticker, or None if its data is unusable."""
    proj = load_latest_projection(ticker, db_path)
    if proj is None:
        return None
    snapshot = proj.get("snapshot", {})
    price = snapshot.get("price")
    shares = snapshot.get("shares")
    revenue = snapshot.get("revenue")
    if not price or not shares or not revenue or revenue <= 0:
        return None

    fundamentals = get_fundamentals(ticker)
    debt = fundamentals.get("totalDebt", {}).get("value") or 0.0
    cash = fundamentals.get("cashAndEquivalents", {}).get("value") or 0.0

    return compute_ev(price, shares, debt, cash) / revenue


def comps_implied_range(
    ticker: str, peer_tickers: list[str], db_path: str, cik: str | None = None,
) -> dict:
    """Peer-median EV/Sales applied to the target's own revenue -> implied price range.

    Args:
        ticker: Target ticker.
        peer_tickers: Curated peer ticker list (from the target's projection's
            `peers` field).
        db_path: Path to domain_model.sqlite.
        cik: SEC CIK for EDGAR cross-checking of the target's fundamentals, or None.
            Peer fundamentals are never threaded with a cik — peers are only used
            for their EV/Sales multiple, not compared against EDGAR filings directly.

    Returns:
        {"status": "ok", "impliedPriceRange": {"low": float, "high": float},
         "peersUsed": [...], "evSalesMedian": float,
         "dataQuality": {ticker: {"staleness","dataConflicts","flags"}, ...peers...}}
        or {"status": "insufficient_peer_data", "peersUsed": [...]} when fewer
        than 2 peers have usable data. dataQuality is keyed by every ticker
        whose get_fundamentals() was actually consulted (target + peersUsed).
    """
    target_proj = load_latest_projection(ticker, db_path)
    if target_proj is None:
        return {"status": "insufficient_peer_data", "peersUsed": []}

    snapshot = target_proj.get("snapshot", {})
    target_shares = snapshot.get("shares")
    target_revenue = snapshot.get("revenue")
    if not target_shares or not target_revenue:
        return {"status": "insufficient_peer_data", "peersUsed": []}

    peer_multiples = {}
    for peer in peer_tickers:
        multiple = _peer_ev_sales(peer, db_path)
        if multiple is not None:
            peer_multiples[peer] = multiple

    if len(peer_multiples) < 2:
        return {"status": "insufficient_peer_data", "peersUsed": list(peer_multiples)}

    ev_sales_median = statistics.median(peer_multiples.values())

    fundamentals = get_fundamentals(ticker, cik=cik)
    target_debt = fundamentals.get("totalDebt", {}).get("value") or 0.0
    target_cash = fundamentals.get("cashAndEquivalents", {}).get("value") or 0.0

    implied_ev = ev_sales_median * target_revenue
    implied_price = (implied_ev - target_debt + target_cash) / target_shares

    data_quality = {ticker: fundamentals.get(
        "dataQuality", {"staleness": False, "dataConflicts": [], "flags": []}
    )}
    for peer in peer_multiples:
        peer_fundamentals = get_fundamentals(peer)
        data_quality[peer] = peer_fundamentals.get(
            "dataQuality", {"staleness": False, "dataConflicts": [], "flags": []}
        )

    # +/-10% band around the point estimate — a single multiple from a small
    # peer set is not precise enough to present as one number.
    return {
        "status": "ok",
        "impliedPriceRange": {
            "low": round(implied_price * 0.9, 2),
            "high": round(implied_price * 1.1, 2),
        },
        "peersUsed": list(peer_multiples),
        "evSalesMedian": round(ev_sales_median, 3),
        "dataQuality": data_quality,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Peer-multiple (EV/Sales) comps cross-check")
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--peers", required=True, help="Comma-separated peer tickers")
    parser.add_argument("--db-path", required=True)
    parser.add_argument("--cik", default=None, help="SEC CIK for the target ticker, omit for non-US tickers")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    peer_tickers = [p.strip() for p in args.peers.split(",") if p.strip()]
    result = comps_implied_range(args.ticker, peer_tickers, args.db_path, cik=args.cik)
    print(json.dumps(result, indent=2 if args.pretty else None))


if __name__ == "__main__":
    main()
