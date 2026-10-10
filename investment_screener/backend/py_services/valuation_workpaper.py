#!/usr/bin/env python3
"""
valuation_workpaper.py - Command line for the valuation working documents in domain_model.sqlite.

Purpose:
    The steps of a stock valuation run hand JSON documents to each other. Instead of shell
    redirects into temp/evaluations/<TICKER>_<stage>.json, a step pipes its output through
    `put`, which stores it and echoes it unchanged, and the next step reads it with `get`.

Layer:
    Backend / Python Services

Usage Examples:
    python3 fetch_financials.py MU | python3 valuation_workpaper.py put --ticker MU --stage raw > /dev/null
    python3 valuation_workpaper.py get --ticker MU --stage raw | python3 dcf_scenarios.py ...
    python3 valuation_workpaper.py put --ticker MU --stage scenarios --file scenarios.json
    python3 valuation_workpaper.py list --ticker MU

Key Functions (Index):
    - main(): CLI entry point (put, get, list)

Key Input Dependencies:
    - domain_model.sqlite (valuation_workpaper table)

Key Output Dependencies:
    - valuation_workpaper rows; `put` echoes the stored JSON on stdout, `get` prints the newest one
"""
import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))

from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.valuation_workpaper_repository import (  # noqa: E402
    get_latest_workpaper,
    list_workpapers,
    put_workpaper,
)

DEFAULT_DB_PATH = REPO_ROOT / "investment_screener/backend/data/domain_model.sqlite"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH))
    sub = parser.add_subparsers(dest="command", required=True)
    put = sub.add_parser("put", help="Store a JSON document (stdin or --file) and echo it")
    put.add_argument("--ticker", required=True)
    put.add_argument("--stage", required=True)
    put.add_argument("--file", help="Read the document from this file instead of stdin")
    put.add_argument("--as-of", help="YYYY-MM-DD (default: today)")
    get = sub.add_parser("get", help="Print the newest stored document for a ticker and stage")
    get.add_argument("--ticker", required=True)
    get.add_argument("--stage", required=True)
    lst = sub.add_parser("list", help="List stored documents (metadata only)")
    lst.add_argument("--ticker")
    lst.add_argument("--stage")
    args = parser.parse_args(argv)

    conn = initialize_db(args.db)
    try:
        if args.command == "put":
            text = Path(args.file).read_text() if args.file else sys.stdin.read()
            try:
                payload = json.loads(text)
            except json.JSONDecodeError as exc:
                print(f"ERROR: input is not JSON: {exc}", file=sys.stderr)
                return 2
            put_workpaper(conn, args.ticker, args.stage, payload, args.as_of, source=args.file or "stdin")
            print(json.dumps(payload))
            return 0
        if args.command == "get":
            payload = get_latest_workpaper(conn, args.ticker, args.stage)
            if payload is None:
                print(f"ERROR: no '{args.stage}' document stored for {args.ticker.upper()}", file=sys.stderr)
                return 1
            print(json.dumps(payload))
            return 0
        print(json.dumps(list_workpapers(conn, args.ticker, args.stage), indent=2))
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
