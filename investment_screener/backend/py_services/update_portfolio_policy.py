#!/usr/bin/env python3
"""Manual-edit CLI for the portfolio_policy singleton row (Wave 5E).

Replaces hand-editing account_policy.json -- account_policy.json is manually
maintained (no code producer ever wrote it), so this migration must build a new
write path rather than redirect an existing one. Matches this codebase's
established dry-run/--write CLI convention for manually-maintained domains.

Usage:
    python3 update_portfolio_policy.py --set max_marginal_risk_contribution_pct=30 --dry-run
    python3 update_portfolio_policy.py --set max_marginal_risk_contribution_pct=30 --write
"""
import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))

DEFAULT_DB_PATH = REPO_ROOT / "investment_screener/backend/data/domain_model.sqlite"

_NUMERIC_FIELDS = {
    "portfolio_value_usd_target",
    "max_marginal_risk_contribution_pct",
    "max_cluster_variance_contribution_pct",
    "rebalance_band_relative_pct",
    "rebalance_band_absolute_pct",
    "rebalance_band_critical_multiplier",
}

def _coerce(field: str, raw_value: str):
    if field in _NUMERIC_FIELDS:
        return float(raw_value)
    return raw_value


def apply_updates(db_path: Path, updates: dict, dry_run: bool = True) -> dict:
    """Apply (or, if dry_run, preview) a set of field updates to the singleton
    portfolio_policy row.

    Args:
        db_path: domain_model.sqlite path.
        updates: {field_name: new_value} -- field_name must be a real
            portfolio_policy column name.
        dry_run: When True (default), report the change without writing.

    Returns:
        {"would_update": updates} on dry-run, {"updated": updates} on write.

    Raises:
        ValueError: if any key in updates is not a real portfolio_policy field.
    """
    from domain_model.db_client import initialize_db
    from domain_model.portfolio_policy_repository import _UPDATABLE_FIELDS, upsert_portfolio_policy

    unknown = set(updates) - _UPDATABLE_FIELDS
    if unknown:
        raise ValueError(f"Unknown portfolio_policy field(s): {sorted(unknown)}")

    if dry_run:
        return {"would_update": updates}

    conn = initialize_db(str(db_path))
    try:
        upsert_portfolio_policy(conn, **updates)
    finally:
        conn.close()

    return {"updated": updates}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--set", action="append", default=[], metavar="FIELD=VALUE",
        help="Set a portfolio_policy field, e.g. --set max_marginal_risk_contribution_pct=30",
    )
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true")
    group.add_argument("--write", action="store_true")
    args = parser.parse_args()

    updates = {}
    for item in args.set:
        field, _, raw_value = item.partition("=")
        updates[field] = _coerce(field, raw_value)

    report = apply_updates(Path(args.db_path), updates, dry_run=args.dry_run)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
