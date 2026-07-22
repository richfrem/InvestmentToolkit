"""Tests the broker_reported_total singleton table repository (Wave 3 Task 8,
tvSnapshot closure).

Stores the broker's OWN last-reported portfolio total (totalUSD/totalCAD/source),
captured at sync time solely to serve verify_portfolio_total.py's reconciliation
audit. Singleton (id=1), overwritten each sync — mirrors broker_exchange_rate.
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.broker_reported_total_repository import (  # noqa: E402
    upsert_broker_reported_total,
    get_broker_reported_total,
)


def test_get_returns_none_when_never_synced(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    assert get_broker_reported_total(conn) is None


def test_upsert_creates_and_is_idempotent(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    upsert_broker_reported_total(
        conn, 30373.98, 41900.0, "2026-07-20T00:00:00Z", "tv_authoritative"
    )
    row = get_broker_reported_total(conn)
    assert row["total_usd"] == 30373.98
    assert row["total_cad"] == 41900.0
    assert row["synced_at"] == "2026-07-20T00:00:00Z"
    assert row["source"] == "tv_authoritative"

    # Second write overwrites the same singleton row, never a second row.
    upsert_broker_reported_total(
        conn, 31000.0, None, "2026-07-21T00:00:00Z", "tv_authoritative"
    )
    row = get_broker_reported_total(conn)
    assert row["total_usd"] == 31000.0
    assert row["total_cad"] is None
    count = conn.execute("SELECT COUNT(*) FROM broker_reported_total;").fetchone()[0]
    assert count == 1
