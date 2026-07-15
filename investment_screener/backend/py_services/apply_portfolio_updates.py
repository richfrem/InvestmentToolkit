#!/usr/bin/env python3
"""
apply_portfolio_updates.py - Python utility script.

Purpose:
    TBD

Layer:
    Backend / Python Services

Usage Examples:
    TBD

Key Functions (Index):
    - main()

Key Input Dependencies:
    None

Key Output Dependencies:
    None
"""
import json
from pathlib import Path

PORTFOLIO_PATH = Path("investment_screener/backend/data/portfolio.json")

def main():
    print("Loading portfolio database...")
    with open(PORTFOLIO_PATH, "r") as f:
        data = json.load(f)

    # 1. Update account snapshots
    tfsa_snap = None
    rrsp_snap = None

    tv_snapshot = data.get("tvSnapshot", {})
    for snap in tv_snapshot.get("snapshots", []):
        if snap.get("accountType") == "TFSA":
            tfsa_snap = snap
        elif snap.get("accountType") == "RRSP":
            rrsp_snap = snap

    if not tfsa_snap or not rrsp_snap:
        print("Error: Could not locate TFSA or RRSP account snapshots in database.")
        return

    # TFSA Positions Updates
    tfsa_positions = tfsa_snap.get("positions", [])
    for pos in tfsa_positions:
        sym = pos.get("symbol")
        if sym == "SNDK":
            pos["quantity"] = 0.58
            pos["avgFillPrice"] = 1483.9445
            print("  TFSA: Updated SNDK to 0.58 shares @ 1483.9445")
        elif sym == "PSU.U.TO":
            pos["quantity"] = 57.0
            print("  TFSA: Updated PSU.U.TO to 57.0 shares")
        elif sym == "BE":
            pos["quantity"] = 4.0
            pos["avgFillPrice"] = 265.1649
            print("  TFSA: Updated BE to 4.0 shares @ 265.1649")
        elif sym == "IREN":
            pos["quantity"] = 28.0
            pos["avgFillPrice"] = 43.7650
            print("  TFSA: Updated IREN to 28.0 shares @ 43.7650")

    # RRSP Positions Updates
    rrsp_positions = rrsp_snap.get("positions", [])
    for pos in rrsp_positions:
        sym = pos.get("symbol")
        if sym == "SNDK":
            pos["quantity"] = 0.36
            pos["avgFillPrice"] = 1461.3306
            print("  RRSP: Updated SNDK to 0.36 shares @ 1461.3306")
        elif sym == "PSU.U.TO":
            pos["quantity"] = 11.0
            print("  RRSP: Updated PSU.U.TO to 11.0 shares")
        elif sym == "BE":
            pos["quantity"] = 1.5
            pos["avgFillPrice"] = 272.9483
            print("  RRSP: Updated BE to 1.5 shares @ 272.9483")
        elif sym == "IREN":
            pos["quantity"] = 9.0
            pos["avgFillPrice"] = 46.4032
            print("  RRSP: Updated IREN to 9.0 shares @ 46.4032")

    # 2. Re-aggregate global holdings
    global_holdings = {}
    
    # Process TFSA positions
    for pos in tfsa_positions:
        sym = pos["symbol"]
        qty = pos["quantity"]
        px = pos.get("avgFillPrice", 0)
        global_holdings[sym] = {"shares": qty, "cost": qty * px}

    # Merge RRSP positions
    for pos in rrsp_positions:
        sym = pos["symbol"]
        qty = pos["quantity"]
        px = pos.get("avgFillPrice", 0)
        if sym in global_holdings:
            global_holdings[sym]["shares"] += qty
            global_holdings[sym]["cost"] += qty * px
        else:
            global_holdings[sym] = {"shares": qty, "cost": qty * px}

    # Format the updated global holdings list
    new_holdings = []
    for sym, item in global_holdings.items():
        # Keep formatting in sync
        shares = item["shares"]
        cost = item["cost"]
        avg_px = cost / shares if shares > 0 else 0
        
        # Find original record to preserve fields like last_updated and market price
        orig = next((h for h in data.get("holdings", []) if h["symbol"] == sym), {})
        
        h_record = {
            "symbol": sym,
            "shares": round(shares, 4),
            "book_price": round(avg_px, 4),
            "market_value": round(shares * orig.get("price", avg_px), 4),
            "price": orig.get("price", avg_px),
            "last_updated": orig.get("last_updated", "2026-07-02T17:48:00.000Z")
        }
        new_holdings.append(h_record)

    data["holdings"] = new_holdings
    print("Re-aggregated global holdings list.")

    # Save to portfolio.json
    with open(PORTFOLIO_PATH, "w") as f:
        json.dump(data, f, indent=2)
    print("Successfully saved updated portfolio database.")

if __name__ == "__main__":
    main()
