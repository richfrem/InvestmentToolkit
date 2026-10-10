#!/usr/bin/env python3
"""
set_cash_flow_baseline.py - Record the year-to-date baseline in domain_model.sqlite.

Purpose:
    The YTD summary needs the portfolio's starting balance (CAD), its start date and the USD/CAD
    rate on January 1. This tool writes them to the cash_flow_baseline row (account 'ALL') through
    the cash-flow repository. Update it each January. Prints the stored baseline; with
    --dry-run it only prints what would be stored.

Layer:
    Backend / Python Services

Usage Examples:
    python3 set_cash_flow_baseline.py --starting-balance-cad 37426 --starting-date 2026-01-01 --jan1-usd-cad-rate 1.3723
    python3 set_cash_flow_baseline.py --jan1-usd-cad-rate 1.3723      # keep balance and date, set only the rate

Key Functions (Index):
    - set_baseline(): upsert the baseline row and return it
    - main(): CLI entry point

Key Input Dependencies:
    - domain_model.sqlite (cash_flow_baseline)

Key Output Dependencies:
    - cash_flow_baseline row for account 'ALL'
"""
import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))

from domain_model.cash_flow_repository import (  # noqa: E402
    CASH_FLOW_BASELINE_SENTINEL_ACCOUNT,
    get_cash_flow_baseline,
    upsert_cash_flow_baseline,
)
from domain_model.db_client import initialize_db  # noqa: E402

DEFAULT_DB_PATH = REPO_ROOT / "investment_screener/backend/data/domain_model.sqlite"


def set_baseline(
    conn,
    starting_balance_cad: float | None = None,
    starting_date: str | None = None,
    jan1_usd_cad_rate: float | None = None,
) -> dict:
    """Upsert the 'ALL' baseline; omitted fields keep their stored value. Returns the stored row.

    Raises:
        ValueError: when there is no stored baseline and the balance or date is missing, or a
            value is not positive.
    """
    current = get_cash_flow_baseline(conn, CASH_FLOW_BASELINE_SENTINEL_ACCOUNT) or {}
    balance = starting_balance_cad if starting_balance_cad is not None else current.get("starting_balance_cad")
    date_ = starting_date if starting_date is not None else current.get("starting_date")
    if balance is None or date_ is None:
        raise ValueError("no baseline stored yet: --starting-balance-cad and --starting-date are required")
    if balance <= 0:
        raise ValueError("starting balance must be greater than 0")
    if jan1_usd_cad_rate is not None and jan1_usd_cad_rate <= 0:
        raise ValueError("January 1 USD/CAD rate must be greater than 0")
    upsert_cash_flow_baseline(conn, CASH_FLOW_BASELINE_SENTINEL_ACCOUNT, balance, date_, jan1_usd_cad_rate)
    return get_cash_flow_baseline(conn, CASH_FLOW_BASELINE_SENTINEL_ACCOUNT)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--starting-balance-cad", type=float)
    parser.add_argument("--starting-date", help="YYYY-MM-DD")
    parser.add_argument("--jan1-usd-cad-rate", type=float)
    parser.add_argument("--dry-run", action="store_true", help="Print the baseline that would be stored; write nothing")
    args = parser.parse_args()
    conn = initialize_db(args.db_path)
    try:
        if args.dry_run:
            current = get_cash_flow_baseline(conn, CASH_FLOW_BASELINE_SENTINEL_ACCOUNT) or {}
            print(json.dumps({"stored": current, "would_store": {
                "starting_balance_cad": args.starting_balance_cad, "starting_date": args.starting_date,
                "jan1_usd_cad_rate": args.jan1_usd_cad_rate}}, indent=2))
            return 0
        print(json.dumps(set_baseline(conn, args.starting_balance_cad, args.starting_date, args.jan1_usd_cad_rate), indent=2))
        return 0
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
