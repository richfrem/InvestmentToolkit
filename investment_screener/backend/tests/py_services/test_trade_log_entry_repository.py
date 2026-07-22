import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.account_repository import upsert_account  # noqa: E402
from domain_model.investment_repository import resolve_investment  # noqa: E402
from domain_model.trade_log_entry_repository import (  # noqa: E402
    upsert_trade_log_entry,
    list_trade_log_entries,
    get_trade_log_entry,
    delete_trade_log_entry,
)


def _seed(conn):
    upsert_account(conn, "TFSA", "TFSA", "TFSA")
    return resolve_investment(conn, "LITE", asset_class="EQUITY", currency="USD")


def _entry(investment_id, **overrides):
    base = {
        "entry_id": "00fd51941b80",
        "investment_id": investment_id,
        "account_id": "TFSA",
        "action": "sell",
        "shares": 0.5,
        "price": 0,
        "total_cost": 0,
        "order_type": "market",
        "limit_price": None,
        "trade_date": "2026-05-18",
        "notes": "EXIT -- SA LP closed $478.6M. Sell pending.",
        "status": "cancelled",
        "source": "13f_clean",
        "priority": 1,
        "logged_at": "2026-05-18T13:58:18.293352+00:00",
    }
    base.update(overrides)
    return base


def test_upsert_trade_log_entry_creates_and_is_idempotent(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    investment_id = _seed(conn)
    entry = _entry(investment_id)
    id_1 = upsert_trade_log_entry(conn, entry)
    entry2 = _entry(investment_id, status="executed", price=25.0)
    id_2 = upsert_trade_log_entry(conn, entry2)
    assert id_1 == id_2 == "00fd51941b80"
    rows = list_trade_log_entries(conn, account_id="TFSA")
    assert len(rows) == 1
    assert rows[0]["status"] == "executed"
    assert rows[0]["price"] == 25.0


def test_list_trade_log_entries_filters_by_account(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    investment_id = _seed(conn)
    upsert_account(conn, "RRSP", "RRSP", "RRSP")
    upsert_trade_log_entry(conn, _entry(investment_id, entry_id="e1", account_id="TFSA"))
    upsert_trade_log_entry(conn, _entry(investment_id, entry_id="e2", account_id="RRSP"))
    tfsa_rows = list_trade_log_entries(conn, account_id="TFSA")
    assert len(tfsa_rows) == 1
    assert tfsa_rows[0]["entry_id"] == "e1"
    all_rows = list_trade_log_entries(conn)
    assert len(all_rows) == 2


def test_get_trade_log_entry_returns_none_when_missing(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    investment_id = _seed(conn)
    upsert_trade_log_entry(conn, _entry(investment_id, entry_id="e1"))
    found = get_trade_log_entry(conn, "e1")
    assert found is not None
    assert found["entry_id"] == "e1"
    assert get_trade_log_entry(conn, "does-not-exist") is None


def test_delete_trade_log_entry(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    investment_id = _seed(conn)
    upsert_trade_log_entry(conn, _entry(investment_id, entry_id="e1"))
    delete_trade_log_entry(conn, "e1")
    assert get_trade_log_entry(conn, "e1") is None
