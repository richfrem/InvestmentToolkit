#!/usr/bin/env python3
"""
validate_weights.py - Portfolio weight validator and normaliser (domain_model.sqlite only).

Purpose:
    Two independent computations over the database:
      --mode current  actual weights: shares x price / portfolio total, per holding
      --mode target   target weights: the sum of investment.target_weight, per holding
      --mode both     both, as one JSON document (default)
    --normalize rescales the target weights to sum to exactly 100%; with --write it saves
    them to investment.target_weight and records one portfolio_change_log entry. Without
    --write nothing is written.

Layer:
    Plugin script (portfolio-advisor), linked into py_services

Usage Examples:
    python3 validate_weights.py                         # both modes, JSON to stdout
    python3 validate_weights.py --mode current
    python3 validate_weights.py --mode target
    python3 validate_weights.py --normalize             # dry run: report the rescaled total
    python3 validate_weights.py --normalize --write     # save and log the change
    python3 validate_weights.py --db /path/to/domain_model.sqlite

Key Functions (Index):
    - compute_current_from_db(): actual weight % per holding and the total value
    - compute_target(): target weight % per holding (zero weights omitted) and their sum
    - normalize_target(): the thesis holdings with weights rescaled to 100, and the new total
    - write_normalized_weights_to_db(): save rescaled weights and record the change
    - main(): command line

Key Input Dependencies:
    - investment_screener/backend/data/domain_model.sqlite (or --db): holdings, prices, targets

Key Output Dependencies:
    - investment.target_weight and portfolio_change_log (only with --normalize --write)
"""

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DB_PATH   = REPO_ROOT / "investment_screener/backend/data/domain_model.sqlite"

sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))
from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.investment_repository import (  # noqa: E402
    resolve_investment,
    update_investment_fields,
)
from domain_model.portfolio_change_log_repository import record_change  # noqa: E402
from portfolio_io import compute_weights, load_target_weights, load_thesis_holdings  # noqa: E402


def compute_current_from_db(db_path: Path) -> dict:
    """Actual weights computed live from domain_model.sqlite.

    The denominator is the portfolio total from ``load_portfolio_state_from_db`` (broker total
    when present, else equities plus cash), so it matches every other page. The weight formula
    is ``portfolio_io.compute_weights`` and is not re-derived here.

    Args:
        db_path: Database to read.

    Returns:
        {"total": sum of weights, "holdings": {symbol: weight %}, "total_value": USD}.
    """
    from domain_model.portfolio_repository import load_portfolio_state_from_db

    conn = initialize_db(str(db_path))
    try:
        state = load_portfolio_state_from_db(conn)
    finally:
        conn.close()
    total_value = state["total_usd"]
    if total_value == 0:
        return {"total": 0.0, "holdings": {}, "total_value": 0.0}
    weights = compute_weights(state["shares"], state["prices"], total_value)
    return {"total": round(sum(weights.values()), 4), "holdings": weights, "total_value": round(total_value, 2)}


def compute_target(db_path: Path) -> dict:
    """Target weights from ``investment.target_weight`` (zero weights omitted).

    Returns:
        {"total": sum of weights, "holdings": {symbol: weight %}}.
    """
    result = load_target_weights(str(db_path))
    return {"total": round(sum(result.values()), 4), "holdings": result}


def normalize_target(db_path: Path) -> tuple:
    """Rescale every positive target weight so they sum to exactly 100.

    Returns:
        ({"holdings": [{"ticker", "targetWeight"}, ...]}, new total). Exits 1 when there is
        nothing to scale.
    """
    holdings = [{"ticker": h["ticker"], "targetWeight": h["targetWeight"]} for h in load_thesis_holdings(str(db_path))]
    total = sum(h["targetWeight"] or 0 for h in holdings)
    if total == 0:
        print("ERROR: all target weights are 0 - nothing to normalize", file=sys.stderr)
        sys.exit(1)
    factor = 100.0 / total
    for h in holdings:
        if (h["targetWeight"] or 0) > 0:
            h["targetWeight"] = round(h["targetWeight"] * factor, 4)
    return {"holdings": holdings}, round(sum(h["targetWeight"] or 0 for h in holdings), 4)


def write_normalized_weights_to_db(data: dict, db_path: Path = DB_PATH) -> None:
    """Save rescaled ``targetWeight`` values to ``investment.target_weight`` and log the change.

    One ``portfolio_change_log`` entry is recorded for the whole batch.
    """
    conn = initialize_db(str(db_path))
    try:
        for h in data["holdings"]:
            investment_id = resolve_investment(conn, h["ticker"])
            update_investment_fields(conn, investment_id, target_weight=h.get("targetWeight", 0) or 0)
        record_change(conn, f"validate_weights.py --normalize: rescaled {len(data['holdings'])} target weights to sum to 100%")
    finally:
        conn.close()


def main():
    """Command line entry point; prints one JSON document to stdout."""
    parser = argparse.ArgumentParser(description="Validate and normalise portfolio weights")
    parser.add_argument("--mode",      choices=["current", "target", "both"], default="both")
    parser.add_argument("--normalize", action="store_true", help="Rescale target weights to sum to 100%")
    parser.add_argument("--write",     action="store_true", help="With --normalize: save to investment.target_weight and log the change")
    parser.add_argument("--db",        default=str(DB_PATH), help="Path to domain_model.sqlite")
    args = parser.parse_args()

    output = {}
    if args.normalize:
        normalised_data, new_total = normalize_target(Path(args.db))
        if args.write:
            write_normalized_weights_to_db(normalised_data, Path(args.db))
            print(
                f"Wrote normalised weights to {args.db} (investment.target_weight, sum={new_total:.4f}%)",
                file=sys.stderr,
            )
        output["normalised_total"] = new_total
        output["target"] = compute_target(Path(args.db))
    else:
        if args.mode in ("current", "both"):
            output["current"] = compute_current_from_db(Path(args.db))
        if args.mode in ("target", "both"):
            output["target"] = compute_target(Path(args.db))

    print(json.dumps(output))


if __name__ == "__main__":
    main()
