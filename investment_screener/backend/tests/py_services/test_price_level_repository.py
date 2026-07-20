import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.investment_repository import resolve_investment  # noqa: E402
from domain_model.price_level_repository import (  # noqa: E402
    replace_price_levels,
    get_price_levels,
)


def _seed_investment(conn):
    return resolve_investment(conn, "SNDK", asset_class="EQUITY", currency="USD")


def test_replace_price_levels_creates_full_structure(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    investment_id = _seed_investment(conn)
    replace_price_levels(
        conn,
        investment_id,
        schema_version="1.0",
        last_updated="2026-07-01T00:00:00Z",
        last_updated_by="update_price_levels.py",
        note="Q2 revision",
        buy_tiers=[
            {"tier": 1, "price": 1048.0, "action": "BUY", "trimPct": None,
             "orderType": "LIMIT", "basis": "support", "source": "TA",
             "sourceDate": "2026-06-01", "condition": None, "status": "ACTIVE"},
            {"tier": 2, "price": 1070.0, "action": "BUY", "trimPct": None,
             "orderType": "LIMIT", "basis": "support", "source": "TA",
             "sourceDate": "2026-06-01", "condition": None, "status": "ACTIVE"},
        ],
        sell_tiers=[],
        stop_loss={"price": 950.0, "basis": "support", "source": "TA",
                    "sourceDate": "2026-06-01", "type": "HARD", "status": "ACTIVE"},
        target_entry_price=1350.0,
    )
    result = get_price_levels(conn, investment_id)
    assert result is not None
    assert len(result["buy_tiers"]) == 2
    assert result["buy_tiers"][0]["price"] == 1048.0
    assert result["stop_loss"]["price"] == 950.0
    assert result["target_entry"]["price"] == 1350.0
    assert result["target_entry"]["price"] not in {1048.0, 1070.0}


def test_replace_price_levels_is_full_replace_not_append(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    investment_id = _seed_investment(conn)
    replace_price_levels(
        conn, investment_id, schema_version="1.0", last_updated=None,
        last_updated_by=None, note=None,
        buy_tiers=[{"tier": 1, "price": 100.0, "action": "BUY", "trimPct": None,
                     "orderType": "LIMIT", "basis": None, "source": None,
                     "sourceDate": None, "condition": None, "status": "ACTIVE"}],
        sell_tiers=[], stop_loss=None, target_entry_price=None,
    )
    replace_price_levels(
        conn, investment_id, schema_version="1.1", last_updated=None,
        last_updated_by=None, note=None,
        buy_tiers=[{"tier": 1, "price": 200.0, "action": "BUY", "trimPct": None,
                     "orderType": "LIMIT", "basis": None, "source": None,
                     "sourceDate": None, "condition": None, "status": "ACTIVE"}],
        sell_tiers=[], stop_loss=None, target_entry_price=None,
    )
    result = get_price_levels(conn, investment_id)
    assert len(result["buy_tiers"]) == 1
    assert result["buy_tiers"][0]["price"] == 200.0


def test_get_price_levels_returns_none_for_investment_with_no_levels(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    investment_id = _seed_investment(conn)
    assert get_price_levels(conn, investment_id) is None
