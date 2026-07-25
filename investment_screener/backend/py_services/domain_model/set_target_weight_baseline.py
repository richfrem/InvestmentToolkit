#!/usr/bin/env python3
"""
set_target_weight_baseline.py — One-off baseline reset: target_weight = current %.

Purpose:
    For every currently-held investment (real account_investment row), set
    investment.target_weight to that ticker's current live weight % (matching
    the Portfolio Table's CURRENT % column: quantity*price / portfolio total,
    from account_investment/investment_price). Every investment NOT currently
    held gets target_weight reset to 0. CASH_USD is excluded entirely (cash
    has no thesis target in this app's convention).

    User-requested new baseline (2026-07-25): "set target holdings to equal
    current %, then can adjust from there up or down."

Layer:
    Backend / Python Services / domain_model

Usage:
    python3 set_target_weight_baseline.py            # dry-run, prints planned changes
    python3 set_target_weight_baseline.py --write     # applies to domain_model.sqlite
"""
import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
DB_PATH = REPO_ROOT / "investment_screener/backend/data/domain_model.sqlite"

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db_client import initialize_db  # noqa: E402
from domain_model.portfolio_repository import load_portfolio_state_from_db  # noqa: E402
from domain_model.investment_repository import list_investments, update_investment_fields  # noqa: E402

_CASH_SYMBOL = "CASH_USD"


def compute_baseline(db_path: Path = DB_PATH) -> dict:
    conn = initialize_db(str(db_path))
    try:
        state = load_portfolio_state_from_db(conn)
        shares = state["shares"]
        prices = state["prices"]
        total_usd = state["total_usd"]

        held_weights: dict[str, float] = {}
        if total_usd > 0:
            for sym, qty in shares.items():
                if sym == _CASH_SYMBOL:
                    continue
                px = prices.get(sym, 0)
                held_weights[sym] = round(qty * px / total_usd * 100, 4)

        all_investments = list_investments(conn)
        changes = []
        for inv in all_investments:
            sym = inv.get("symbol")
            if not sym or sym == _CASH_SYMBOL:
                continue
            old_weight = inv.get("target_weight")
            new_weight = held_weights.get(sym, 0.0)
            changes.append({
                "symbol": sym,
                "investment_id": inv["investment_id"],
                "old_target_weight": old_weight,
                "new_target_weight": new_weight,
                "held": sym in held_weights,
            })
        return {"changes": changes, "total_usd": total_usd}
    finally:
        conn.close()


def apply_baseline(db_path: Path = DB_PATH) -> dict:
    result = compute_baseline(db_path)
    conn = initialize_db(str(db_path))
    try:
        for c in result["changes"]:
            update_investment_fields(conn, c["investment_id"], target_weight=c["new_target_weight"])
    finally:
        conn.close()
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Reset target_weight baseline to current %")
    parser.add_argument("--write", action="store_true", help="Apply changes (default is dry-run)")
    parser.add_argument("--db", default=str(DB_PATH))
    args = parser.parse_args()

    db_path = Path(args.db)
    if args.write:
        result = apply_baseline(db_path)
    else:
        result = compute_baseline(db_path)

    held = [c for c in result["changes"] if c["held"]]
    zeroed = [c for c in result["changes"] if not c["held"] and (c["old_target_weight"] or 0) != 0]
    print(json.dumps({
        "dry_run": not args.write,
        "total_usd": result["total_usd"],
        "held_count": len(held),
        "zeroed_count": len(zeroed),
        "held": held,
        "zeroed": zeroed,
    }, indent=2))


if __name__ == "__main__":
    main()
