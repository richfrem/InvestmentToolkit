import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.portfolio_policy_repository import (  # noqa: E402
    get_portfolio_policy,
    upsert_portfolio_policy,
)


def test_get_portfolio_policy_returns_none_when_never_written(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    assert get_portfolio_policy(conn) is None


def test_upsert_and_get_round_trips_all_fields(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    upsert_portfolio_policy(
        conn,
        rebalance_frequency="quarterly",
        portfolio_value_usd_target=30797,
        max_marginal_risk_contribution_pct=25,
        max_cluster_variance_contribution_pct=60,
        rebalance_band_relative_pct=20,
        rebalance_band_absolute_pct=1.5,
        rebalance_band_critical_multiplier=2.0,
        account_preference_rules_json='[{"match": "default", "prefer": "TFSA"}]',
        psu_funding_rule_json='{"ticker": "PSU-U.TO"}',
    )
    row = get_portfolio_policy(conn)
    assert row is not None
    assert row["rebalance_frequency"] == "quarterly"
    assert row["portfolio_value_usd_target"] == 30797
    assert row["max_marginal_risk_contribution_pct"] == 25
    assert row["rebalance_band_critical_multiplier"] == 2.0
    assert row["account_preference_rules_json"] == '[{"match": "default", "prefer": "TFSA"}]'
    assert row["psu_funding_rule_json"] == '{"ticker": "PSU-U.TO"}'
    assert row["updated_at"]


def test_upsert_is_idempotent_no_duplicate_row(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    upsert_portfolio_policy(conn, rebalance_frequency="quarterly")
    upsert_portfolio_policy(conn, rebalance_frequency="monthly")
    count = conn.execute("SELECT COUNT(*) FROM portfolio_policy;").fetchone()[0]
    assert count == 1
    row = get_portfolio_policy(conn)
    assert row["rebalance_frequency"] == "monthly"


def test_upsert_partial_update_preserves_other_fields(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    upsert_portfolio_policy(
        conn, rebalance_frequency="quarterly", max_marginal_risk_contribution_pct=25,
    )
    upsert_portfolio_policy(conn, max_marginal_risk_contribution_pct=30)
    row = get_portfolio_policy(conn)
    assert row["rebalance_frequency"] == "quarterly"
    assert row["max_marginal_risk_contribution_pct"] == 30
