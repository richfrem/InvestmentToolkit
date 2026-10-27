"""
Tests update_price_levels.py's compute_price_level_snapshot_from_db()
(Wave 3 Task 5.8): proves the priceLevelSnapshot (nextBuyTier/nextSellTier/
stopLoss/proximityFlags) is fully computable from already-migrated SQLite
tables -- price_level_tier (Wave 2 Task 9) + investment_price (Wave 3 Task 1)
-- with no new schema, matching the task brief's instruction to confirm this
rather than duplicate existing schema.
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "plugins/portfolio-advisor/scripts"))
sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))

from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.investment_repository import resolve_investment  # noqa: E402
from domain_model.investment_price_repository import upsert_investment_price  # noqa: E402
from domain_model.price_level_repository import replace_price_levels  # noqa: E402

from update_price_levels import compute_price_level_snapshot_from_db  # noqa: E402

BUY_TIER = {"tier": 1, "price": 100.0, "action": "accumulate", "trimPct": None,
            "orderType": "limit", "basis": "b", "source": "dcf", "sourceDate": "2026-01-01",
            "condition": None, "status": "active"}
SELL_TIER = {"tier": 1, "price": 200.0, "action": "trim", "trimPct": 30,
             "orderType": "limit", "basis": "s", "source": "dcf", "sourceDate": "2026-01-01",
             "condition": None, "status": "active"}
STOP_LOSS = {"price": 80.0, "basis": "stop", "source": "dcf", "sourceDate": "2026-01-01",
             "type": "thesis_breaker", "status": "active"}


def test_computes_snapshot_from_price_level_tier_and_investment_price(tmp_path):
    db_path = tmp_path / "test.sqlite"
    conn = initialize_db(str(db_path))
    investment_id = resolve_investment(conn, "GOOG")
    replace_price_levels(
        conn, investment_id, schema_version="1.0", last_updated="2026-01-01",
        last_updated_by="dcf", note=None, buy_tiers=[BUY_TIER], sell_tiers=[SELL_TIER],
        stop_loss=STOP_LOSS, target_entry_price=None,
    )
    upsert_investment_price(conn, investment_id, price=99.0, currency="USD", fetched_at="2026-01-01T00:00:00Z")

    snap = compute_price_level_snapshot_from_db(conn, investment_id)
    conn.close()

    assert snap is not None
    assert snap["nextBuyTier"]["price"] == 100.0
    assert snap["nextSellTier"]["price"] == 200.0
    assert snap["stopLoss"]["price"] == 80.0
    assert "AT_BUY_TIER_1" in snap["proximityFlags"]


def test_returns_none_when_no_price_level_set(tmp_path):
    db_path = tmp_path / "test.sqlite"
    conn = initialize_db(str(db_path))
    investment_id = resolve_investment(conn, "NOPRICELEVELS")
    upsert_investment_price(conn, investment_id, price=50.0, currency="USD", fetched_at="2026-01-01T00:00:00Z")
    snap = compute_price_level_snapshot_from_db(conn, investment_id)
    conn.close()
    assert snap is None


def test_returns_none_when_no_current_price(tmp_path):
    db_path = tmp_path / "test.sqlite"
    conn = initialize_db(str(db_path))
    investment_id = resolve_investment(conn, "NOPRICE")
    replace_price_levels(
        conn, investment_id, schema_version="1.0", last_updated="2026-01-01",
        last_updated_by="dcf", note=None, buy_tiers=[BUY_TIER], sell_tiers=[SELL_TIER],
        stop_loss=STOP_LOSS, target_entry_price=None,
    )
    snap = compute_price_level_snapshot_from_db(conn, investment_id)
    conn.close()
    assert snap is None
