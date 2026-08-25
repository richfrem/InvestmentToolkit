#!/usr/bin/env python3
"""
portfolio_inspect.py - CLI tool to inspect portfolio holding and thesis states from SQLite.

Purpose:
    Canonical, versioned CLI tool to inspect holding details, target weights,
    account share distributions, standing decisions, and broker sync status
    from domain_model.sqlite without writing ad-hoc inline SQL queries.

Layer:
    Backend / py_services

Usage Examples:
    python3 py_services/portfolio_inspect.py --symbol IREN
    python3 py_services/portfolio_inspect.py --symbol IREN --json
"""
import argparse
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from domain_model.db_client import initialize_db
from domain_model.investment_repository import get_investment
from domain_model.portfolio_repository import load_portfolio_state_from_db
from ticker_aliases import normalize_ticker

_DB_PATH = str(_HERE / ".." / "data" / "domain_model.sqlite")

def inspect_symbol(symbol: str) -> dict:
    canonical = normalize_ticker(symbol)
    conn = initialize_db(_DB_PATH)
    try:
        inv = get_investment(conn, canonical)
        state = load_portfolio_state_from_db(conn)
        
        shares = state.get("shares", {}).get(canonical, 0.0)
        price = state.get("prices", {}).get(canonical, 0.0)
        market_val = shares * price
        total_usd = state.get("total_usd", 0.0)
        weight_pct = (market_val / total_usd * 100.0) if total_usd > 0 else 0.0
        
        # Per-account breakdown
        cur = conn.execute(
            """
            SELECT a.account_name, ai.quantity, ai.average_cost
            FROM account_investment ai
            JOIN account a ON ai.account_id = a.account_id
            WHERE ai.investment_id = ?;
            """,
            (canonical,)
        )
        accounts = [{"account": r[0], "shares": r[1], "avg_cost": r[2]} for r in cur.fetchall()]
        
        return {
            "symbol": canonical,
            "name": inv.get("name") if inv else canonical,
            "target_weight": inv.get("target_weight", 0.0) if inv else 0.0,
            "current_weight_pct": round(weight_pct, 2),
            "shares": shares,
            "price": price,
            "market_value_usd": round(market_val, 2),
            "total_portfolio_usd": round(total_usd, 2),
            "lifecycle_status": inv.get("lifecycle_status") if inv else None,
            "pillar_id": inv.get("pillar_id") if inv else None,
            "standing_decision": {
                "type": inv.get("standing_decision_type") if inv else None,
                "reason": inv.get("standing_decision_reason") if inv else None,
                "source": inv.get("standing_decision_source") if inv else None
            },
            "agent_rationale": inv.get("agent_rationale") if inv else None,
            "accounts": accounts
        }
    finally:
        conn.close()

def main():
    parser = argparse.ArgumentParser(description="Inspect holding state and thesis metadata from domain_model.sqlite")
    parser.add_argument("--symbol", "-s", type=str, help="Ticker symbol to inspect")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    if not args.symbol:
        parser.print_help()
        sys.exit(1)

    d = inspect_symbol(args.symbol)
    if args.json:
        print(json.dumps(d, indent=2))
    else:
        print(f"=== {d["symbol"]} Holding & Thesis State ===")
        print(f"Name:              {d["name"]}")
        print(f"Pillar:            {d["pillar_id"]}")
        print(f"Shares:            {d["shares"]} across {len(d["accounts"])} account(s)")
        print(f"Price:             ${d["price"]:.2f}")
        print(f"Market Value:      ${d["market_value_usd"]:.2f} ({d["current_weight_pct"]}% of portfolio)")
        print(f"Target Weight:     {d["target_weight"]}%")
        print(f"Standing Decision: [{d["standing_decision"]["type"]}] {d["standing_decision"]["reason"]}")
        if d.get("agent_rationale"):
            print(f"Agent Rationale:   {d["agent_rationale"]}")

if __name__ == "__main__":
    main()
