#!/usr/bin/env python3
"""cash_flow_cli.py — CLI producer for the cash_flow / cash_flow_baseline tables.

This is the FIRST real write path for cash flow data. Historically
``data/cash_flows.json`` had no code producer at all -- it was hand-edited by
the user. Going forward, new cash flows (deposits/withdrawals) should be added
via this script instead of hand-editing JSON.

Usage:
  # Add a new cash flow:
  python3 cash_flow_cli.py --add --date 2026-07-22 --type deposit \\
      --amount-cad 2000 --account TFSA --portfolio-value-before-flow-cad 39120

  # List all cash flows:
  python3 cash_flow_cli.py --list

  # List cash flows for one account:
  python3 cash_flow_cli.py --list --account TFSA
"""

import argparse
import sys
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB_PATH = REPO_ROOT / "investment_screener/backend/data/domain_model.sqlite"

sys.path.insert(0, str(Path(__file__).parent))
from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.cash_flow_repository import (  # noqa: E402
    insert_cash_flow,
    list_cash_flows,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Add or list cash flow records in the domain-model SQLite database."
    )
    parser.add_argument("--add", action="store_true", help="Add a new cash flow record.")
    parser.add_argument("--list", action="store_true", help="List cash flow records.")
    parser.add_argument("--date", help="Flow date, e.g. 2026-07-22 (required with --add).")
    parser.add_argument(
        "--type", dest="flow_type", choices=["deposit", "withdrawal"],
        help="Flow type (required with --add).",
    )
    parser.add_argument("--amount-cad", type=float, help="Flow amount in CAD (required with --add).")
    parser.add_argument("--account", help="Account (e.g. TFSA, RRSP). Required with --add; optional filter with --list.")
    parser.add_argument(
        "--portfolio-value-before-flow-cad", type=float,
        help="Portfolio value in CAD immediately before this flow (required with --add).",
    )
    parser.add_argument(
        "--db-path", default=str(DEFAULT_DB_PATH),
        help=f"Path to the domain-model SQLite database (default: {DEFAULT_DB_PATH}).",
    )
    return parser


def do_add(conn, args) -> str:
    missing = [
        name for name, val in [
            ("--date", args.date),
            ("--type", args.flow_type),
            ("--amount-cad", args.amount_cad),
            ("--account", args.account),
            ("--portfolio-value-before-flow-cad", args.portfolio_value_before_flow_cad),
        ]
        if val is None
    ]
    if missing:
        raise SystemExit(f"--add requires: {', '.join(missing)}")

    flow_id = uuid.uuid4().hex[:12]
    flow = {
        "flow_id": flow_id,
        "flow_date": args.date,
        "flow_type": args.flow_type,
        "amount_cad": args.amount_cad,
        "portfolio_value_before_flow_cad": args.portfolio_value_before_flow_cad,
        "account": args.account,
    }
    insert_cash_flow(conn, flow)
    print(
        f"Added cash flow {flow_id}: {args.flow_type} {args.amount_cad:.2f} CAD "
        f"on {args.date} for {args.account} "
        f"(portfolio value before flow: {args.portfolio_value_before_flow_cad:.2f} CAD)"
    )
    return flow_id


def do_list(conn, args) -> list:
    rows = list_cash_flows(conn, account=args.account)
    if not rows:
        print("No cash flows found.")
        return rows
    for row in sorted(rows, key=lambda r: r.get("flow_date") or ""):
        print(
            f"{row['flow_id']}  {row['flow_date']}  {row['flow_type']:>10}  "
            f"{row['amount_cad']:>12.2f} CAD  account={row['account']}  "
            f"portfolio_value_before={row['portfolio_value_before_flow_cad']:.2f} CAD"
        )
    return rows


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.add and not args.list:
        parser.print_help()
        return 1

    conn = initialize_db(str(args.db_path))
    try:
        if args.add:
            do_add(conn, args)
        if args.list:
            do_list(conn, args)
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
