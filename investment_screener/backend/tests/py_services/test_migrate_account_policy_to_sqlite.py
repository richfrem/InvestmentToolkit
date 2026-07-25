import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.portfolio_policy_repository import get_portfolio_policy  # noqa: E402
from migrate_account_policy_to_sqlite import migrate  # noqa: E402


def _write_fixture_account_policy(path):
    data = {
        "accountPreferenceRules": [{"match": "default", "prefer": "TFSA"}],
        "psuFundingRule": {"ticker": "PSU-U.TO", "sameAccountOnly": True},
        "riskBudgetCaps": {
            "maxMarginalRiskContributionPct": 25,
            "maxClusterVarianceContributionPct": 60,
        },
        "bandConfig": {"relativePct": 20, "absolutePct": 1.5, "criticalMultiplier": 2.0},
    }
    path.write_text(json.dumps(data))


def _write_fixture_target_portfolio(path):
    data = {"globalSettings": {"rebalanceFrequency": "quarterly", "portfolioValueUSD": 30797}}
    path.write_text(json.dumps(data))


def test_migrate_dry_run_reports_fields_without_writing(tmp_path):
    account_policy_path = tmp_path / "account_policy.json"
    target_portfolio_path = tmp_path / "target-portfolio.json"
    db_path = tmp_path / "domain_model.sqlite"
    _write_fixture_account_policy(account_policy_path)
    _write_fixture_target_portfolio(target_portfolio_path)

    report = migrate(account_policy_path, target_portfolio_path, db_path, dry_run=True)

    assert set(report["fields_migrated"]) == {
        "rebalance_frequency", "portfolio_value_usd_target",
        "max_marginal_risk_contribution_pct", "max_cluster_variance_contribution_pct",
        "rebalance_band_relative_pct", "rebalance_band_absolute_pct",
        "rebalance_band_critical_multiplier", "account_preference_rules_json",
        "psu_funding_rule_json",
    }
    assert report["skipped"] == []
    conn = initialize_db(str(db_path))
    assert get_portfolio_policy(conn) is None


def test_migrate_write_upserts_all_fields_correctly(tmp_path):
    account_policy_path = tmp_path / "account_policy.json"
    target_portfolio_path = tmp_path / "target-portfolio.json"
    db_path = tmp_path / "domain_model.sqlite"
    _write_fixture_account_policy(account_policy_path)
    _write_fixture_target_portfolio(target_portfolio_path)

    report = migrate(account_policy_path, target_portfolio_path, db_path, dry_run=False)
    assert report["skipped"] == []

    conn = initialize_db(str(db_path))
    row = get_portfolio_policy(conn)
    assert row is not None
    assert row["rebalance_frequency"] == "quarterly"
    assert row["portfolio_value_usd_target"] == 30797
    assert row["max_marginal_risk_contribution_pct"] == 25
    assert row["max_cluster_variance_contribution_pct"] == 60
    assert row["rebalance_band_relative_pct"] == 20
    assert row["rebalance_band_absolute_pct"] == 1.5
    assert row["rebalance_band_critical_multiplier"] == 2.0
    assert json.loads(row["account_preference_rules_json"]) == [
        {"match": "default", "prefer": "TFSA"}
    ]
    assert json.loads(row["psu_funding_rule_json"]) == {
        "ticker": "PSU-U.TO", "sameAccountOnly": True
    }


def test_migrate_is_idempotent_on_rerun(tmp_path):
    account_policy_path = tmp_path / "account_policy.json"
    target_portfolio_path = tmp_path / "target-portfolio.json"
    db_path = tmp_path / "domain_model.sqlite"
    _write_fixture_account_policy(account_policy_path)
    _write_fixture_target_portfolio(target_portfolio_path)

    migrate(account_policy_path, target_portfolio_path, db_path, dry_run=False)
    migrate(account_policy_path, target_portfolio_path, db_path, dry_run=False)

    conn = initialize_db(str(db_path))
    count = conn.execute("SELECT COUNT(*) FROM portfolio_policy;").fetchone()[0]
    assert count == 1
