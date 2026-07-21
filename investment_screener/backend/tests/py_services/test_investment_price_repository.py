import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.investment_repository import resolve_investment  # noqa: E402
from domain_model.investment_price_repository import (  # noqa: E402
    upsert_investment_price,
    get_investment_price,
)


def test_upsert_investment_price_creates_and_is_idempotent(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    aapl_id = resolve_investment(conn, "AAPL", asset_class="EQUITY", currency="USD")
    upsert_investment_price(conn, aapl_id, price=150.0, currency="USD", fetched_at="2026-07-20T00:00:00Z")
    upsert_investment_price(conn, aapl_id, price=155.5, currency="USD", fetched_at="2026-07-20T01:00:00Z")
    row = get_investment_price(conn, aapl_id)
    assert row["price"] == 155.5  # last write wins, not a duplicate row
    cursor = conn.execute("SELECT COUNT(*) FROM investment_price WHERE investment_id = ?;", (aapl_id,))
    assert cursor.fetchone()[0] == 1


def test_get_investment_price_returns_none_for_unknown(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    assert get_investment_price(conn, "does-not-exist") is None
