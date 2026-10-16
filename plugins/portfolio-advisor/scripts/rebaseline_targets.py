#!/usr/bin/env python3
"""
rebaseline_targets.py — reset target weights the owner's latest trades superseded.

Purpose:
    Daily-loop Step 0, after the position sync and price refresh. A fill newer than a target's
    target_set_at resets that target to the post-trade weight (0% when sold out); untraded
    targets stay as set and the cash target absorbs the difference so targets sum to 100%. The
    brief flags the stale ones for the owner (target_rebaseline.target_staleness).
Layer:
    Portfolio advisor / data maintenance (writes investment.target_weight / target_set_at).
Usage:
    python3 plugins/portfolio-advisor/scripts/rebaseline_targets.py           # preview
    python3 plugins/portfolio-advisor/scripts/rebaseline_targets.py --write   # apply
    Add --json for machine-readable output, --db to use another database.
Key Functions:
    main()  prints the plan from target_rebaseline.plan_rebaseline and applies it on --write
Key Input Dependencies:
    domain_model.sqlite via target_rebaseline.py (repositories only).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_REPO_ROOT / "investment_screener/backend/py_services"))

from domain_model.db_client import initialize_db  # noqa: E402
from target_rebaseline import apply_rebaseline, plan_rebaseline  # noqa: E402

_DEFAULT_DB = str(_REPO_ROOT / "investment_screener/backend/data/domain_model.sqlite")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--write", action="store_true", help="apply the plan (default: preview)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--db", default=_DEFAULT_DB)
    args = ap.parse_args(argv)

    conn = initialize_db(args.db)
    try:
        plan = plan_rebaseline(conn)
        written = apply_rebaseline(conn, plan) if args.write else 0
    finally:
        conn.close()

    if args.json:
        print(json.dumps({**plan, "written": written, "dry_run": not args.write}, indent=2))
        return 0
    if not plan["changes"]:
        print("No fills newer than their targets; nothing to re-baseline.")
    else:
        print(f"{'Ticker':<10}{'Old %':>9}{'New %':>9}  Reason")
        for c in plan["changes"]:
            print(f"{c['symbol']:<10}{c['old']:>9.2f}{c['new']:>9.2f}  {c['reason']}")
        print(f"Total {plan['total_before']:.2f}% → {plan['total_after']:.2f}%")
    for s in plan["skipped"]:
        print(f"Skipped {s['symbol']}: {s['reason']}")
    print("Written." if args.write and written else "Preview only; add --write to apply." if plan["changes"] else "")
    return 0


if __name__ == "__main__":
    sys.exit(main())
