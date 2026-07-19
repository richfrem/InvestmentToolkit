import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.investment_repository import get_investment  # noqa: E402
from domain_model.backfill_investment_universe import (  # noqa: E402
    backfill_from_ticker_lists,
)


def test_backfill_creates_one_row_per_new_ticker(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    created = backfill_from_ticker_lists(conn, ["AAPL", "MSFT"])
    assert created == 2
    assert get_investment(conn, "AAPL") is not None
    assert get_investment(conn, "AAPL")["asset_class"] == "EQUITY"


def test_backfill_cash_concepts_use_asset_class_cash(tmp_path):
    """CASH_USD/CASH_CAD are real INVESTMENT rows per the v3.2 model (spec §3, resolved
    decision 5) — they must never silently default to EQUITY. The caller is responsible for
    passing asset_class="CASH" explicitly; this test guards against that contract being
    dropped, since a default-to-EQUITY cash row would be a real data-modeling bug, not a
    cosmetic one (it would corrupt asset_class-based portfolio composition queries).
    """
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    backfill_from_ticker_lists(conn, ["CASH_USD", "CASH_CAD"], asset_class="CASH")
    assert get_investment(conn, "CASH_USD")["asset_class"] == "CASH"
    assert get_investment(conn, "CASH_CAD")["asset_class"] == "CASH"


def test_backfill_is_idempotent_on_rerun(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    backfill_from_ticker_lists(conn, ["AAPL", "MSFT"])
    created_second_run = backfill_from_ticker_lists(conn, ["AAPL", "MSFT", "GOOGL"])
    assert created_second_run == 1  # only GOOGL is new
