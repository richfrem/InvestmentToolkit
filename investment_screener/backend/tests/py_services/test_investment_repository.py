import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.investment_repository import (  # noqa: E402
    resolve_investment,
    get_investment,
)


def test_resolve_investment_creates_new_and_is_idempotent(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    id_1 = resolve_investment(conn, "AAPL", asset_class="EQUITY", currency="USD", name="Apple Inc.")
    id_2 = resolve_investment(conn, "AAPL", asset_class="EQUITY", currency="USD", name="Apple Inc.")
    assert id_1 == id_2
    cursor = conn.execute("SELECT COUNT(*) FROM investment WHERE symbol = 'AAPL';")
    assert cursor.fetchone()[0] == 1


def test_resolve_investment_supports_cash_concepts(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    investment_id = resolve_investment(conn, "CASH_USD", asset_class="CASH", currency="USD")
    row = get_investment(conn, investment_id)
    assert row["asset_class"] == "CASH"
    assert row["symbol"] == "CASH_USD"


def test_get_investment_returns_none_for_unknown_id(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    assert get_investment(conn, "does-not-exist") is None
