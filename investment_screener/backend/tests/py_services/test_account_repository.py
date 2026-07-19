import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.account_repository import (  # noqa: E402
    upsert_account,
    get_account,
    list_accounts,
)


def test_upsert_account_creates_and_is_idempotent(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    upsert_account(conn, "TFSA", "TFSA", "TFSA", base_currency="CAD")
    upsert_account(conn, "TFSA", "TFSA", "TFSA", base_currency="CAD")
    cursor = conn.execute("SELECT COUNT(*) FROM account WHERE account_id = 'TFSA';")
    assert cursor.fetchone()[0] == 1


def test_get_account_returns_row(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    upsert_account(conn, "RRSP", "RRSP", "RRSP", base_currency="CAD")
    row = get_account(conn, "RRSP")
    assert row["account_name"] == "RRSP"


def test_list_accounts_returns_all(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    upsert_account(conn, "TFSA", "TFSA", "TFSA")
    upsert_account(conn, "RRSP", "RRSP", "RRSP")
    accounts = list_accounts(conn)
    assert {a["account_id"] for a in accounts} == {"TFSA", "RRSP"}
