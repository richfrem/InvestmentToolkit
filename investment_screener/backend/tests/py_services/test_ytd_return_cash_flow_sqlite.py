"""Task 10 (Wave 4): ytd_return.py's cash-flow load is now backed by
cash_flow_repository (SQLite), not cash_flows.json.
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
PY_SERVICES = REPO_ROOT / "investment_screener/backend/py_services"
SCRIPTS_DIR = REPO_ROOT / "plugins/portfolio-advisor/scripts"
sys.path.insert(0, str(PY_SERVICES))
sys.path.insert(0, str(SCRIPTS_DIR))

from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.cash_flow_repository import (  # noqa: E402
    insert_cash_flow,
    upsert_cash_flow_baseline,
    CASH_FLOW_BASELINE_SENTINEL_ACCOUNT,
)
import ytd_return  # noqa: E402


def test_load_cash_flows_reads_from_sqlite(tmp_path):
    db_path = tmp_path / "test.sqlite"
    conn = initialize_db(str(db_path))
    upsert_cash_flow_baseline(conn, CASH_FLOW_BASELINE_SENTINEL_ACCOUNT, 37426.0, "2026-01-01")
    insert_cash_flow(conn, {
        "flow_id": "f1",
        "flow_date": "2026-02-06",
        "flow_type": "deposit",
        "amount_cad": 2000.0,
        "portfolio_value_before_flow_cad": 39120.0,
        "account": "TFSA",
    })

    result = ytd_return.load_cash_flows(db_path=str(db_path))

    assert result["starting_balance_cad"] == 37426.0
    assert len(result["cash_flows"]) == 1
    flow = result["cash_flows"][0]
    assert flow["date"] == "2026-02-06"
    assert flow["type"] == "deposit"
    assert flow["amount_cad"] == 2000.0
    assert flow["portfolio_value_before_flow_cad"] == 39120.0


def test_load_cash_flows_missing_db_degrades_to_empty(tmp_path):
    result = ytd_return.load_cash_flows(db_path=str(tmp_path / "nonexistent.sqlite"))
    assert result == {}


def test_load_cash_flows_no_baseline_degrades_to_empty(tmp_path):
    db_path = tmp_path / "test.sqlite"
    initialize_db(str(db_path))
    result = ytd_return.load_cash_flows(db_path=str(db_path))
    assert result == {}
