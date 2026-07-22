"""Tests the broker_exchange_rate singleton table repository (Wave 3 Task 8).

Stores the ONE broker-reported FX fact (USD->CAD), inferred at sync time from
TradingView's own native totalEquityCADCombined/totalEquityUSDCombined ratio
(CLAUDE.md pitfall #27). Never a CAD-denominated total -- just the scalar rate.
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.exchange_rate_repository import (  # noqa: E402
    upsert_exchange_rate,
    get_exchange_rate,
)


def test_get_exchange_rate_returns_none_when_never_synced(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    assert get_exchange_rate(conn) is None


def test_upsert_exchange_rate_creates_and_is_idempotent(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    upsert_exchange_rate(conn, 1.3795, "2026-07-20T00:00:00Z")
    assert get_exchange_rate(conn) == 1.3795
    # Second write overwrites the same singleton row, never a second row.
    upsert_exchange_rate(conn, 1.4012, "2026-07-21T00:00:00Z")
    assert get_exchange_rate(conn) == 1.4012
    count = conn.execute("SELECT COUNT(*) FROM broker_exchange_rate;").fetchone()[0]
    assert count == 1
