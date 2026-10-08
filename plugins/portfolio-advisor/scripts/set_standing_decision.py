#!/usr/bin/env python3
"""
set_standing_decision.py — record, replace or clear an investment's standing decision.

Purpose:
    The one supported way to change a standing decision. Recommendations treat the
    standing decision as the anchor and flag it when it conflicts with the valuation
    action or no longer applies (standing_decision_check.py); resolving that flag
    means updating or clearing the decision here, with a dated source so its age is
    always known.
Layer:
    Portfolio advisor / data maintenance (writes investment.standing_decision_*).
Usage:
    python3 plugins/portfolio-advisor/scripts/set_standing_decision.py --ticker IREN \\
        --type TRIM_ON_STRENGTH --reason "Trim above $45 into strength." --review "After Q1 results"
    python3 plugins/portfolio-advisor/scripts/set_standing_decision.py --ticker GEV --clear
    Add --dry-run to preview, --json for machine-readable output.
Key Functions:
    set_standing_decision(conn, symbol, ...)   returns {"before", "after"}
Key Input Dependencies:
    domain_model.sqlite (investment table), via investment_repository only.

Type convention: start with the direction so every reader can interpret it —
HOLD / MAINTAIN / NO_ADD, TRIM / EXIT, ACCUMULATE / INITIATE, WATCHLIST / WAIT / AVOID —
then the condition, e.g. ACCUMULATE_200_EMA_RETEST.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_REPO_ROOT / "investment_screener/backend/py_services"))

from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.investment_repository import get_investment, update_investment_fields  # noqa: E402
from ticker_aliases import normalize_ticker  # noqa: E402

_DEFAULT_DB = str(_REPO_ROOT / "investment_screener/backend/data/domain_model.sqlite")
_FIELDS = ("type", "reason", "source", "review")


def _current(row: dict) -> dict[str, Any]:
    return {field: row.get(f"standing_decision_{field}") for field in _FIELDS}


def set_standing_decision(conn: Any, symbol: str, decision_type: str | None, reason: str | None,
                          review: str | None = None, source: str | None = None,
                          clear: bool = False, dry_run: bool = False) -> dict[str, Any]:
    """Replace or clear a standing decision; returns the before and after values.

    Raises:
        LookupError: the symbol is not an investment (nothing is created).
    """
    investment_id = normalize_ticker(symbol.strip().upper())
    row = get_investment(conn, investment_id)
    if row is None:
        raise LookupError(f"{investment_id} is not an investment in the portfolio database")
    after = dict.fromkeys(_FIELDS) if clear else {
        "type": "_".join(str(decision_type).upper().split()), "reason": reason,
        "source": source or f"user {date.today().isoformat()}", "review": review}
    if not dry_run:
        update_investment_fields(conn, investment_id, **{f"standing_decision_{field}": after[field] for field in _FIELDS})
    return {"ticker": investment_id, "before": _current(row), "after": after, "dry_run": dry_run}


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Record, replace or clear a standing decision")
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--type", dest="decision_type", help="Direction first, e.g. HOLD_AT_TARGET, TRIM_ON_STRENGTH")
    parser.add_argument("--reason", help="Why, in a sentence, with the specific level or condition")
    parser.add_argument("--review", help="When or on what trigger to revisit it")
    parser.add_argument("--source", help="Who set it and when (default: user <today>)")
    parser.add_argument("--clear", action="store_true", help="Remove the standing decision")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--db", default=_DEFAULT_DB)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if args.clear and (args.decision_type or args.reason):
        parser.error("--clear cannot be combined with --type or --reason")
    if not args.clear and not (args.decision_type and args.reason):
        parser.error("--type and --reason are both required (or use --clear)")

    conn = initialize_db(args.db)
    try:
        report = set_standing_decision(conn, args.ticker, args.decision_type, args.reason, args.review,
                                       args.source, clear=args.clear, dry_run=args.dry_run)
    except LookupError as error:
        print(json.dumps({"error": str(error)}) if args.json else f"Error: {error}", file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        verb = "Would set" if args.dry_run else "Set"
        print(f"{verb} {report['ticker']} standing decision: {report['before']['type']} -> {report['after']['type']}")


if __name__ == "__main__":
    main()
