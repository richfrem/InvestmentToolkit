import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.cash_flow_repository import (  # noqa: E402
    insert_cash_flow,
    list_cash_flows,
    get_cash_flow_baseline,
    upsert_cash_flow_baseline,
)


def test_insert_cash_flow_creates_and_is_idempotent(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    flow = {
        "flow_id": "flow-1",
        "flow_date": "2026-02-06",
        "flow_type": "deposit",
        "amount_cad": 2000.0,
        "portfolio_value_before_flow_cad": 39120.0,
        "account": "TFSA",
    }
    id_1 = insert_cash_flow(conn, flow)
    flow["amount_cad"] = 2500.0
    id_2 = insert_cash_flow(conn, flow)
    assert id_1 == id_2 == "flow-1"
    rows = list_cash_flows(conn, account="TFSA")
    assert len(rows) == 1
    assert rows[0]["amount_cad"] == 2500.0


def test_list_cash_flows_all_and_filtered_by_account(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    insert_cash_flow(conn, {
        "flow_id": "flow-1", "flow_date": "2026-02-06", "flow_type": "deposit",
        "amount_cad": 2000.0, "portfolio_value_before_flow_cad": 39120.0,
        "account": "TFSA",
    })
    insert_cash_flow(conn, {
        "flow_id": "flow-2", "flow_date": "2026-03-24", "flow_type": "withdrawal",
        "amount_cad": 5300.0, "portfolio_value_before_flow_cad": 43500.0,
        "account": "RRSP",
    })
    all_rows = list_cash_flows(conn)
    assert len(all_rows) == 2
    tfsa_rows = list_cash_flows(conn, account="TFSA")
    assert len(tfsa_rows) == 1
    assert tfsa_rows[0]["flow_id"] == "flow-1"


def test_upsert_and_get_cash_flow_baseline(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    upsert_cash_flow_baseline(conn, "ALL", 37426.0, "2026-01-01")
    baseline = get_cash_flow_baseline(conn, "ALL")
    assert baseline is not None
    assert baseline["starting_balance_cad"] == 37426.0
    assert baseline["starting_date"] == "2026-01-01"

    upsert_cash_flow_baseline(conn, "ALL", 40000.0, "2026-01-01")
    updated = get_cash_flow_baseline(conn, "ALL")
    assert updated["starting_balance_cad"] == 40000.0


def test_get_cash_flow_baseline_returns_none_when_missing(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    assert get_cash_flow_baseline(conn, "ALL") is None
