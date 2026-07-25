"""Tests for sync_portfolio_roles.py — Wave 8 cutover to domain_model.sqlite.

Real bug this replaces: sync_roles() read AND wrote
target-portfolio.json's holdings[].role directly (json.loads/write_text) --
this script's entire purpose is syncing lifecycle_status/role from actual
held positions, and it kept writing to a file the live app no longer reads
once the thesis document itself was retired.
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = REPO_ROOT / "plugins/portfolio-advisor/scripts"
PY_SERVICES = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(PY_SERVICES))

from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.investment_repository import resolve_investment, update_investment_fields  # noqa: E402
import sync_portfolio_roles  # noqa: E402


def _seed(db_path, symbol, target_weight, lifecycle_status):
    conn = initialize_db(str(db_path))
    inv_id = resolve_investment(conn, symbol, asset_class="EQUITY")
    update_investment_fields(conn, inv_id, target_weight=target_weight, lifecycle_status=lifecycle_status)
    conn.close()


def test_sync_roles_fixes_wrong_role_for_held_position(tmp_path, monkeypatch):
    db_path = tmp_path / "test.sqlite"
    _seed(db_path, "NVDA", target_weight=10.0, lifecycle_status="watchlist")  # wrong: held but "watchlist"

    monkeypatch.setattr(sync_portfolio_roles, "load_actual_shares", lambda path: {"NVDA": 5.0})

    sync_portfolio_roles.sync_roles(dry_run=False, db_path=db_path)

    conn = initialize_db(str(db_path))
    row = conn.execute("SELECT lifecycle_status FROM investment WHERE symbol = 'NVDA';").fetchone()
    conn.close()
    assert row[0] == "accumulate"


def test_sync_roles_dry_run_does_not_write(tmp_path, monkeypatch):
    db_path = tmp_path / "test.sqlite"
    _seed(db_path, "NVDA", target_weight=10.0, lifecycle_status="watchlist")

    monkeypatch.setattr(sync_portfolio_roles, "load_actual_shares", lambda path: {"NVDA": 5.0})

    sync_portfolio_roles.sync_roles(dry_run=True, db_path=db_path)

    conn = initialize_db(str(db_path))
    row = conn.execute("SELECT lifecycle_status FROM investment WHERE symbol = 'NVDA';").fetchone()
    conn.close()
    assert row[0] == "watchlist"


def test_sync_roles_leaves_correct_role_unchanged(tmp_path, monkeypatch):
    db_path = tmp_path / "test.sqlite"
    _seed(db_path, "NVDA", target_weight=10.0, lifecycle_status="accumulate")

    monkeypatch.setattr(sync_portfolio_roles, "load_actual_shares", lambda path: {"NVDA": 5.0})

    sync_portfolio_roles.sync_roles(dry_run=False, db_path=db_path)

    conn = initialize_db(str(db_path))
    row = conn.execute("SELECT lifecycle_status FROM investment WHERE symbol = 'NVDA';").fetchone()
    conn.close()
    assert row[0] == "accumulate"


def test_no_longer_references_target_portfolio_json():
    src = (SCRIPT_DIR / "sync_portfolio_roles.py").read_text()
    assert "target-portfolio.json" not in src
    assert "TARGET_JSON" not in src
