#!/usr/bin/env python3
"""
apply_portfolio_updates.py - Python utility script.

Purpose:
    One-off manual patch tool: hardcoded per-ticker share/avgFillPrice corrections
    for SNDK/PSU.U.TO/BE/IREN across TFSA and RRSP, then re-aggregates the flat
    holdings[] array from the patched per-account positions.

Layer:
    Backend / Python Services

Usage Examples:
    python3 apply_portfolio_updates.py

Key Functions (Index):
    - main()

Key Input Dependencies:
    investment_screener/backend/data/portfolio.json

Key Output Dependencies:
    investment_screener/backend/data/portfolio.json
    investment_screener/backend/data/domain_model.sqlite (Wave 3 Task 5.6:
    patched TFSA/RRSP positions are also upserted as account_investment rows)
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PORTFOLIO_PATH = Path("investment_screener/backend/data/portfolio.json")
DB_PATH = Path("investment_screener/backend/data/domain_model.sqlite")

sys.path.insert(0, str(Path(__file__).resolve().parent))


def _persist_account_positions_to_db(db_path: str, account_id: str, positions: list[dict]) -> int:
    """Upsert every real position in one account's patched position list as an
    account_investment row. Mirrors migrate_portfolio_to_sqlite.py's per-holding
    write shape -- one upsert_account_investment call per real position, using
    account_investment_repository directly (no full portfolio_repository.py
    abstraction needed for this single-holding CLI tool, per this task's brief).
    """
    from domain_model.db_client import initialize_db
    from domain_model.account_repository import upsert_account
    from domain_model.account_investment_repository import upsert_account_investment
    from domain_model.investment_repository import resolve_investment

    conn = initialize_db(db_path)
    upsert_account(conn, account_id, account_id, account_id)
    now = datetime.now(timezone.utc).isoformat()
    written = 0
    for pos in positions:
        quantity = float(pos.get("quantity") or 0)
        if quantity <= 0:
            continue  # closed/flattened position -- no noise row
        symbol = pos["symbol"]
        investment_id = resolve_investment(conn, symbol, asset_class="EQUITY", currency="USD")
        upsert_account_investment(
            conn, account_id, investment_id, quantity=quantity,
            average_cost=pos.get("avgFillPrice"), book_value=None,
            currency="USD", last_synced_at=now,
        )
        written += 1
    return written


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

    # Wave 3 Task 5.6: also persist the patched real per-account positions to
    # domain_model.sqlite (additive -- portfolio.json write above is unchanged).
    tfsa_written = _persist_account_positions_to_db(str(DB_PATH), "TFSA", tfsa_positions)
    rrsp_written = _persist_account_positions_to_db(str(DB_PATH), "RRSP", rrsp_positions)
    print(f"Persisted {tfsa_written} TFSA + {rrsp_written} RRSP position(s) to domain_model.sqlite.")

if __name__ == "__main__":
    main()
