#!/usr/bin/env python3
"""One-time migration: backfill account_policy.json + target-portfolio.json's
globalSettings sub-object into the domain_model.sqlite portfolio_policy singleton
row (Wave 5E, ADR-029).

account_policy.json fields (accountPreferenceRules, psuFundingRule, riskBudgetCaps,
bandConfig) map onto portfolio_policy's numeric caps/bands and the two JSON rule-blob
columns. target-portfolio.json's globalSettings sub-object (rebalanceFrequency,
portfolioValueUSD) maps onto rebalance_frequency/portfolio_value_usd_target -- this
is a value-only backfill, NOT a consumer cutover for globalSettings (see the wave
plan's Retained-JSON Rationale Bar: target-portfolio.json itself stays JSON per
Wave 2's approved exception).

Usage:
    python3 migrate_account_policy_to_sqlite.py --dry-run
    python3 migrate_account_policy_to_sqlite.py --write
"""
import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))

DEFAULT_ACCOUNT_POLICY_PATH = REPO_ROOT / "investment_screener/backend/data/account_policy.json"
DEFAULT_TARGET_PORTFOLIO_PATH = (
    REPO_ROOT / "investment_screener/backend/data/theses/target-portfolio.json"
)
DEFAULT_DB_PATH = REPO_ROOT / "investment_screener/backend/data/domain_model.sqlite"


def migrate(
    account_policy_path: Path, target_portfolio_path: Path, db_path: Path, dry_run: bool = True
) -> dict:
    """Backfill account_policy.json + target-portfolio.json's globalSettings into
    the portfolio_policy singleton row.

    Args:
        account_policy_path: Path to account_policy.json (source of truth for 4 of
            the 5 mapped fields until this wave's archive step).
        target_portfolio_path: Path to target-portfolio.json (source of
            globalSettings.rebalanceFrequency/portfolioValueUSD only -- the rest of
            this file is untouched, per Wave 2's retained-JSON exception).
        db_path: domain_model.sqlite to write the portfolio_policy row into.
        dry_run: When True (default), report the fields that would be migrated
            without writing anything.

    Returns:
        {"fields_migrated": list[str], "skipped": list[str]}
    """
    from domain_model.db_client import initialize_db
    from domain_model.portfolio_policy_repository import upsert_portfolio_policy

    skipped: list[str] = []
    fields: dict = {}

    if account_policy_path.exists():
        with open(account_policy_path) as f:
            account_policy = json.load(f)
        risk_caps = account_policy.get("riskBudgetCaps", {})
        band_config = account_policy.get("bandConfig", {})
        if "maxMarginalRiskContributionPct" in risk_caps:
            fields["max_marginal_risk_contribution_pct"] = risk_caps["maxMarginalRiskContributionPct"]
        if "maxClusterVarianceContributionPct" in risk_caps:
            fields["max_cluster_variance_contribution_pct"] = risk_caps["maxClusterVarianceContributionPct"]
        if "relativePct" in band_config:
            fields["rebalance_band_relative_pct"] = band_config["relativePct"]
        if "absolutePct" in band_config:
            fields["rebalance_band_absolute_pct"] = band_config["absolutePct"]
        if "criticalMultiplier" in band_config:
            fields["rebalance_band_critical_multiplier"] = band_config["criticalMultiplier"]
        if "accountPreferenceRules" in account_policy:
            fields["account_preference_rules_json"] = json.dumps(account_policy["accountPreferenceRules"])
        if "psuFundingRule" in account_policy:
            fields["psu_funding_rule_json"] = json.dumps(account_policy["psuFundingRule"])
    else:
        skipped.append(f"account_policy_path not found: {account_policy_path}")

    if target_portfolio_path.exists():
        with open(target_portfolio_path) as f:
            target_portfolio = json.load(f)
        global_settings = target_portfolio.get("globalSettings", {})
        if "rebalanceFrequency" in global_settings:
            fields["rebalance_frequency"] = global_settings["rebalanceFrequency"]
        if "portfolioValueUSD" in global_settings:
            fields["portfolio_value_usd_target"] = global_settings["portfolioValueUSD"]
    else:
        skipped.append(f"target_portfolio_path not found: {target_portfolio_path}")

    report = {"fields_migrated": sorted(fields.keys()), "skipped": skipped}

    if dry_run:
        return report

    conn = initialize_db(str(db_path))
    try:
        upsert_portfolio_policy(conn, **fields)
    finally:
        conn.close()

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--account-policy-path", default=str(DEFAULT_ACCOUNT_POLICY_PATH))
    parser.add_argument("--target-portfolio-path", default=str(DEFAULT_TARGET_PORTFOLIO_PATH))
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true")
    group.add_argument("--write", action="store_true")
    args = parser.parse_args()

    report = migrate(
        Path(args.account_policy_path),
        Path(args.target_portfolio_path),
        Path(args.db_path),
        dry_run=args.dry_run,
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
