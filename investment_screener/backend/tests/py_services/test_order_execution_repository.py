import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.investment_repository import resolve_investment  # noqa: E402
from domain_model.order_execution_repository import (  # noqa: E402
    insert_order_execution,
    list_order_executions,
)


def _seed_investment(conn, ticker="NVDA"):
    return resolve_investment(conn, ticker, asset_class="EQUITY", currency="USD")


def test_insert_order_execution_creates_and_is_idempotent(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    investment_id = _seed_investment(conn)
    execution = {
        "execution_id": "exec-1",
        "executed_at": "2026-07-01T00:00:00Z",
        "investment_id": investment_id,
        "side": "BUY",
        "shares": 10.0,
        "price": 200.0,
        "decision": "EXECUTED",
        "gate_result_json": '{"gate": "pass"}',
    }
    id_1 = insert_order_execution(conn, execution)

    updated = dict(execution)
    updated["decision"] = "OVERRIDDEN"
    updated["shares"] = 12.0
    id_2 = insert_order_execution(conn, updated)

    assert id_1 == id_2 == "exec-1"
    rows = list_order_executions(conn, investment_id=investment_id)
    assert len(rows) == 1
    assert rows[0]["decision"] == "OVERRIDDEN"
    assert rows[0]["shares"] == 12.0


def test_list_order_executions_all_and_filtered(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    inv_a = _seed_investment(conn, "NVDA")
    inv_b = _seed_investment(conn, "AAPL")

    insert_order_execution(conn, {
        "execution_id": "exec-a1",
        "executed_at": "2026-07-01T00:00:00Z",
        "investment_id": inv_a,
        "side": "BUY",
        "shares": 5.0,
        "price": 100.0,
        "decision": "EXECUTED",
        "gate_result_json": None,
    })
    insert_order_execution(conn, {
        "execution_id": "exec-b1",
        "executed_at": "2026-07-02T00:00:00Z",
        "investment_id": inv_b,
        "side": "SELL",
        "shares": 2.0,
        "price": 150.0,
        "decision": "BLOCKED",
        "gate_result_json": None,
    })

    all_rows = list_order_executions(conn)
    assert len(all_rows) == 2

    filtered = list_order_executions(conn, investment_id=inv_a)
    assert len(filtered) == 1
    assert filtered[0]["execution_id"] == "exec-a1"
