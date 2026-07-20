import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.investment_repository import resolve_investment  # noqa: E402
from domain_model.alert_repository import upsert_alert, list_alerts  # noqa: E402


def _seed_investment(conn):
    return resolve_investment(conn, "NVDA", asset_class="EQUITY", currency="USD")


def test_upsert_alert_creates_and_is_idempotent(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    investment_id = _seed_investment(conn)
    id_1 = upsert_alert(
        conn, "alert-1", investment_id, "PRICE_ABOVE", "NVDA above 200", 200.0,
        None, True, None, "2026-07-01T00:00:00Z", None, None, "2026-07-19T00:00:00Z",
    )
    id_2 = upsert_alert(
        conn, "alert-1", investment_id, "PRICE_ABOVE", "NVDA above 200", 200.0,
        None, False, "TRIGGERED", "2026-07-01T00:00:00Z", "2026-07-19T00:00:00Z",
        None, "2026-07-19T01:00:00Z",
    )
    assert id_1 == id_2 == "alert-1"
    rows = list_alerts(conn, investment_id=investment_id)
    assert len(rows) == 1
    assert rows[0]["active"] == 0


def test_list_alerts_active_only_filter(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    investment_id = _seed_investment(conn)
    upsert_alert(conn, "a1", investment_id, "PRICE_ABOVE", "msg", 100.0, None,
                 True, None, "2026-07-01T00:00:00Z", None, None, "2026-07-19T00:00:00Z")
    upsert_alert(conn, "a2", investment_id, "PRICE_BELOW", "msg", 90.0, None,
                 False, "TRIGGERED", "2026-07-01T00:00:00Z", None, None,
                 "2026-07-19T00:00:00Z")
    active = list_alerts(conn, investment_id=investment_id, active_only=True)
    assert len(active) == 1
    assert active[0]["alert_id"] == "a1"
