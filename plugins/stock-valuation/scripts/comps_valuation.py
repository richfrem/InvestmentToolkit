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
        --projections-dir investment_screener/backend/data/projections --pretty

Key Functions:
    - load_latest_projection() - Reads the latest AI_AGENT (or [0]) entry from a
      versioned projections/{TICKER}.json file
    - compute_ev() - Enterprise value from price * shares + debt - cash
    - comps_implied_range() - Primary orchestrator: peer-median EV/Sales -> implied price range
"""

import argparse
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from market_data import get_fundamentals  # noqa: E402


def load_latest_projection(ticker: str, projections_dir: str) -> dict | None:
    """Load the latest AI_AGENT entry (or the only entry) from projections/{TICKER}.json.

    Mirrors portfolio_action.py._load_ai_upside()'s established read pattern
    for this repo's versioned-list projection file format.

    Args:
        ticker: Ticker symbol.
        projections_dir: Path to the projections directory.

    Returns:
        The latest projection dict, or None if the file doesn't exist or is empty.
    """
    path = Path(projections_dir) / f"{ticker}.json"
    if not path.exists():
        return None
    with open(path) as f:
        projs = json.load(f)
    if isinstance(projs, list):
        if not projs:
            return None
        ai = [p for p in projs if p.get("source") == "AI_AGENT"]
        return max(ai, key=lambda x: x.get("savedAt", "")) if ai else projs[0]
    return projs


def compute_ev(price: float, shares: float, debt: float, cash: float) -> float:
    """Enterprise value: market cap (price * shares) + debt - cash."""
    return price * shares + debt - cash


def _peer_ev_sales(ticker: str, projections_dir: str) -> float | None:
    """EV/Sales for one peer ticker, or None if its data is unusable."""
    proj = load_latest_projection(ticker, projections_dir)
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


def comps_implied_range(ticker: str, peer_tickers: list[str], projections_dir: str) -> dict:
    """Peer-median EV/Sales applied to the target's own revenue -> implied price range.

    Args:
        ticker: Target ticker.
        peer_tickers: Curated peer ticker list (from projections/{TICKER}.json's `peers` field).
        projections_dir: Path to the projections directory.

    Returns:
        {"status": "ok", "impliedPriceRange": {"low": float, "high": float},
         "peersUsed": [...], "evSalesMedian": float}
        or {"status": "insufficient_peer_data", "peersUsed": [...]} when fewer
        than 2 peers have usable data.
    """
    target_proj = load_latest_projection(ticker, projections_dir)
    if target_proj is None:
        return {"status": "insufficient_peer_data", "peersUsed": []}

    snapshot = target_proj.get("snapshot", {})
    target_shares = snapshot.get("shares")
    target_revenue = snapshot.get("revenue")
    if not target_shares or not target_revenue:
        return {"status": "insufficient_peer_data", "peersUsed": []}

    peer_multiples = {}
    for peer in peer_tickers:
        multiple = _peer_ev_sales(peer, projections_dir)
        if multiple is not None:
            peer_multiples[peer] = multiple

    if len(peer_multiples) < 2:
        return {"status": "insufficient_peer_data", "peersUsed": list(peer_multiples)}

    ev_sales_median = statistics.median(peer_multiples.values())

    fundamentals = get_fundamentals(ticker)
    target_debt = fundamentals.get("totalDebt", {}).get("value") or 0.0
    target_cash = fundamentals.get("cashAndEquivalents", {}).get("value") or 0.0

    implied_ev = ev_sales_median * target_revenue
    implied_price = (implied_ev - target_debt + target_cash) / target_shares

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
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Peer-multiple (EV/Sales) comps cross-check")
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--peers", required=True, help="Comma-separated peer tickers")
    parser.add_argument("--projections-dir", required=True)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    peer_tickers = [p.strip() for p in args.peers.split(",") if p.strip()]
    result = comps_implied_range(args.ticker, peer_tickers, args.projections_dir)
    print(json.dumps(result, indent=2 if args.pretty else None))


if __name__ == "__main__":
    main()
