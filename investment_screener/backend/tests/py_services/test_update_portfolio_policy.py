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
from update_portfolio_policy import apply_updates  # noqa: E402


def test_dry_run_reports_change_without_writing(tmp_path):
    db_path = tmp_path / "domain_model.sqlite"
    conn = initialize_db(str(db_path))
    upsert_portfolio_policy(conn, max_marginal_risk_contribution_pct=25)
    conn.close()

    report = apply_updates(
        db_path, {"max_marginal_risk_contribution_pct": 30}, dry_run=True
    )
    assert report["would_update"] == {"max_marginal_risk_contribution_pct": 30}

    conn = initialize_db(str(db_path))
    row = get_portfolio_policy(conn)
    assert row["max_marginal_risk_contribution_pct"] == 25  # unchanged


def test_write_actually_updates_the_row(tmp_path):
    db_path = tmp_path / "domain_model.sqlite"
    conn = initialize_db(str(db_path))
    upsert_portfolio_policy(conn, max_marginal_risk_contribution_pct=25)
    conn.close()

    report = apply_updates(
        db_path, {"max_marginal_risk_contribution_pct": 30}, dry_run=False
    )
    assert report["updated"] == {"max_marginal_risk_contribution_pct": 30}

    conn = initialize_db(str(db_path))
    row = get_portfolio_policy(conn)
    assert row["max_marginal_risk_contribution_pct"] == 30


def test_rejects_unknown_field(tmp_path):
    db_path = tmp_path / "domain_model.sqlite"
    initialize_db(str(db_path))
    try:
        apply_updates(db_path, {"not_a_real_field": 1}, dry_run=True)
        assert False, "expected ValueError"
    except ValueError as e:
        assert "not_a_real_field" in str(e)
