import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.account_repository import upsert_account  # noqa: E402
from domain_model.investment_repository import resolve_investment  # noqa: E402
from domain_model.account_investment_repository import (  # noqa: E402
    upsert_account_investment,
    list_account_investments,
)


def _seed(conn):
    upsert_account(conn, "TFSA", "TFSA", "TFSA")
    upsert_account(conn, "RRSP", "RRSP", "RRSP")
    aapl_id = resolve_investment(conn, "AAPL", asset_class="EQUITY", currency="USD")
    return aapl_id


def test_upsert_account_investment_creates_and_is_idempotent(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    aapl_id = _seed(conn)
    ai_id_1 = upsert_account_investment(
        conn, "TFSA", aapl_id, quantity=10, average_cost=150.0,
        book_value=1500.0, currency="USD", last_synced_at="2026-07-19T00:00:00Z",
    )
    ai_id_2 = upsert_account_investment(
        conn, "TFSA", aapl_id, quantity=12, average_cost=150.0,
        book_value=1800.0, currency="USD", last_synced_at="2026-07-19T01:00:00Z",
    )
    assert ai_id_1 == ai_id_2 == "TFSA:AAPL"
    rows = list_account_investments(conn, account_id="TFSA")
    assert len(rows) == 1
    assert rows[0]["quantity"] == 12  # last write wins, not a duplicate row


def test_same_investment_across_two_accounts(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    aapl_id = _seed(conn)
    upsert_account_investment(
        conn, "TFSA", aapl_id, quantity=10, average_cost=150.0,
        book_value=1500.0, currency="USD", last_synced_at="2026-07-19T00:00:00Z",
    )
    upsert_account_investment(
        conn, "RRSP", aapl_id, quantity=3, average_cost=150.0,
        book_value=450.0, currency="USD", last_synced_at="2026-07-19T00:00:00Z",
    )
    rows = list_account_investments(conn, investment_id=aapl_id)
    assert {r["account_id"] for r in rows} == {"TFSA", "RRSP"}
