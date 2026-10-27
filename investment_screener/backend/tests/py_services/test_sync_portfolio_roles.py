"""Tests for sync_portfolio_roles.py, which syncs investment.lifecycle_status
(role) in domain_model.sqlite from the actual held positions.
"""
import sys
from pathlib import Path

REPO_ROOT = next(p for p in Path(__file__).resolve().parents if (p / "investment_screener").is_dir())
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
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

    monkeypatch.setattr(sync_portfolio_roles, "load_actual_shares", lambda db_path: {"NVDA": 5.0})

    sync_portfolio_roles.sync_roles(dry_run=False, db_path=db_path)

    conn = initialize_db(str(db_path))
    row = conn.execute("SELECT lifecycle_status FROM investment WHERE symbol = 'NVDA';").fetchone()
    conn.close()
    assert row[0] == "accumulate"


def test_sync_roles_dry_run_does_not_write(tmp_path, monkeypatch):
    db_path = tmp_path / "test.sqlite"
    _seed(db_path, "NVDA", target_weight=10.0, lifecycle_status="watchlist")

    monkeypatch.setattr(sync_portfolio_roles, "load_actual_shares", lambda db_path: {"NVDA": 5.0})

    sync_portfolio_roles.sync_roles(dry_run=True, db_path=db_path)

    conn = initialize_db(str(db_path))
    row = conn.execute("SELECT lifecycle_status FROM investment WHERE symbol = 'NVDA';").fetchone()
    conn.close()
    assert row[0] == "watchlist"


def test_sync_roles_leaves_correct_role_unchanged(tmp_path, monkeypatch):
    db_path = tmp_path / "test.sqlite"
    _seed(db_path, "NVDA", target_weight=10.0, lifecycle_status="accumulate")

    monkeypatch.setattr(sync_portfolio_roles, "load_actual_shares", lambda db_path: {"NVDA": 5.0})

    sync_portfolio_roles.sync_roles(dry_run=False, db_path=db_path)

    conn = initialize_db(str(db_path))
    row = conn.execute("SELECT lifecycle_status FROM investment WHERE symbol = 'NVDA';").fetchone()
    conn.close()
    assert row[0] == "accumulate"


def test_has_no_file_role_source():
    src = (SCRIPT_DIR / "sync_portfolio_roles.py").read_text()
    assert "TARGET_JSON" not in src


def test_load_actual_shares_reads_the_database_it_is_given(tmp_path):
    """load_actual_shares(db_path) returns the shares stored in that database, summed across accounts."""
    sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))
    from domain_model.account_investment_repository import upsert_account_investment
    from domain_model.account_repository import upsert_account
    from domain_model.db_client import initialize_db
    from domain_model.investment_price_repository import upsert_investment_price
    from domain_model.investment_repository import resolve_investment

    db = tmp_path / "t.sqlite"
    conn = initialize_db(str(db))
    for account in ("TFSA", "RRSP"):
        upsert_account(conn, account, account, account)
    investment_id = resolve_investment(conn, "AAPL", asset_class="EQUITY", currency="USD")
    upsert_investment_price(conn, investment_id, price=100.0, currency="USD", fetched_at="2026-10-09T00:00:00Z")
    for account, qty in (("TFSA", 30), ("RRSP", 10)):
        upsert_account_investment(conn, account, investment_id, qty, 100.0, qty * 100.0, "USD", "2026-10-09T00:00:00Z")
    conn.close()

    assert sync_portfolio_roles.load_actual_shares(db) == {"AAPL": 40.0}


def _seed_buy(db_path, symbol, trade_date):
    from domain_model.account_repository import upsert_account
    from domain_model.trade_log_entry_repository import upsert_trade_log_entry
    conn = initialize_db(str(db_path))
    upsert_account(conn, "TFSA", "TFSA", "TFSA")
    upsert_trade_log_entry(conn, {"entry_id": f"{symbol}-{trade_date}", "investment_id": symbol, "account_id": "TFSA",
                                  "action": "buy", "shares": 3, "price": 224.7, "trade_date": trade_date,
                                  "status": "filled", "source": "test"})
    conn.close()


def _role(db_path, symbol):
    conn = initialize_db(str(db_path))
    row = conn.execute("SELECT lifecycle_status FROM investment WHERE symbol = ?;", (symbol,)).fetchone()
    conn.close()
    return row[0]


def test_position_bought_after_a_zero_target_is_never_labelled_exit(tmp_path, monkeypatch):
    """The NVDA case: an initiate target of 0%, then the owner buys. The stale 0% must not become 'exit'."""
    from datetime import date, timedelta
    db_path = tmp_path / "test.sqlite"
    _seed(db_path, "NVDA", target_weight=0.0, lifecycle_status="initiate")
    _seed_buy(db_path, "NVDA", (date.today() - timedelta(days=5)).isoformat())
    monkeypatch.setattr(sync_portfolio_roles, "load_actual_shares", lambda db_path: {"NVDA": 4.0})

    sync_portfolio_roles.sync_roles(dry_run=False, db_path=db_path)
    assert _role(db_path, "NVDA") == "accumulate"


def test_existing_exit_label_is_corrected_after_a_buy(tmp_path, monkeypatch):
    from datetime import date, timedelta
    db_path = tmp_path / "test.sqlite"
    _seed(db_path, "NVDA", target_weight=0.0, lifecycle_status="exit")
    _seed_buy(db_path, "NVDA", (date.today() - timedelta(days=5)).isoformat())
    monkeypatch.setattr(sync_portfolio_roles, "load_actual_shares", lambda db_path: {"NVDA": 4.0})

    sync_portfolio_roles.sync_roles(dry_run=False, db_path=db_path)
    assert _role(db_path, "NVDA") == "accumulate"


def test_held_zero_target_without_a_buy_since_is_still_exit(tmp_path, monkeypatch):
    """An owner-set 0% target with no later buy keeps meaning exit."""
    db_path = tmp_path / "test.sqlite"
    _seed(db_path, "OLD", target_weight=0.0, lifecycle_status="watchlist")
    monkeypatch.setattr(sync_portfolio_roles, "load_actual_shares", lambda db_path: {"OLD": 2.0})

    sync_portfolio_roles.sync_roles(dry_run=False, db_path=db_path)
    assert _role(db_path, "OLD") == "exit"
