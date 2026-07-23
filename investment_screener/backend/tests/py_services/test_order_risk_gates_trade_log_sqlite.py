"""Task 8 (Wave 4): get_trade_log_entries() and log_order_execution() are
now backed by trade_log_entry_repository / order_execution_repository
(SQLite), not trade-log.json / orders_executed.jsonl.
"""
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.trade_log_entry_repository import upsert_trade_log_entry  # noqa: E402
from domain_model.order_execution_repository import list_order_executions  # noqa: E402
from domain_model.investment_repository import resolve_investment  # noqa: E402
from domain_model.account_repository import upsert_account  # noqa: E402
import order_risk_gates  # noqa: E402


def _make_conn(tmp_path):
    return initialize_db(str(tmp_path / "test.sqlite"))


def test_get_trade_log_entries_reads_from_sqlite(tmp_path):
    conn = _make_conn(tmp_path)
    investment_id = resolve_investment(conn, "NVDA")
    upsert_account(conn, "TFSA", "TFSA", "TFSA")
    upsert_trade_log_entry(conn, {
        "entry_id": "e1",
        "investment_id": investment_id,
        "account_id": "TFSA",
        "action": "buy",
        "shares": 10.0,
        "price": 200.0,
        "total_cost": 2000.0,
        "order_type": "market",
        "limit_price": None,
        "trade_date": "2026-07-01",
        "notes": "test",
        "status": "logged",
        "source": "manual",
        "priority": "normal",
        "logged_at": "2026-07-01T00:00:00Z",
    })

    entries = order_risk_gates.get_trade_log_entries(db_path=str(tmp_path / "test.sqlite"))

    assert len(entries) == 1
    entry = entries[0]
    assert entry["id"] == "e1"
    assert entry["ticker"] == "NVDA"
    assert entry["action"] == "buy"
    assert entry["shares"] == 10.0
    assert entry["price"] == 200.0
    assert entry["account"] == "TFSA"
    assert entry["status"] == "logged"
    assert entry["loggedAt"] == "2026-07-01T00:00:00Z"


def test_get_trade_log_entries_empty_db_returns_empty_list(tmp_path):
    entries = order_risk_gates.get_trade_log_entries(db_path=str(tmp_path / "empty.sqlite"))
    assert entries == []


def test_find_matching_trade_log_entry_still_works_on_sqlite_shaped_entries(tmp_path):
    conn = _make_conn(tmp_path)
    investment_id = resolve_investment(conn, "NVDA")
    upsert_account(conn, "TFSA", "TFSA", "TFSA")
    upsert_trade_log_entry(conn, {
        "entry_id": "e1",
        "investment_id": investment_id,
        "account_id": "TFSA",
        "action": "buy",
        "shares": 10.0,
        "price": 200.0,
        "total_cost": 2000.0,
        "order_type": "market",
        "limit_price": None,
        "trade_date": "2026-07-01",
        "notes": None,
        "status": "logged",
        "source": "manual",
        "priority": "normal",
        "logged_at": "2026-07-01T00:00:00Z",
    })
    entries = order_risk_gates.get_trade_log_entries(db_path=str(tmp_path / "test.sqlite"))
    match = order_risk_gates.find_matching_trade_log_entry(
        {"ticker": "NVDA", "side": "buy", "shares": 10.0, "price": 200.0}, entries
    )
    assert match is not None
    assert match["id"] == "e1"


def test_log_order_execution_writes_to_sqlite(tmp_path):
    db_path = str(tmp_path / "test.sqlite")
    conn = initialize_db(db_path)
    conn.close()

    order = {"ticker": "NVDA", "side": "BUY", "shares": 5.0, "price": 100.0}
    gate_result = {"passed": True, "gates": [], "reasons": []}

    ok = order_risk_gates.log_order_execution(
        order, gate_result, "EXECUTED", trade_execution_result=None, db_path=db_path,
    )
    assert ok is True

    conn2 = initialize_db(db_path)
    rows = list_order_executions(conn2)
    assert len(rows) == 1
    row = rows[0]
    assert row["decision"] == "EXECUTED"
    assert row["side"] == "BUY"
    assert row["shares"] == 5.0
    stored = json.loads(row["gate_result_json"])
    assert stored["gate_result"] == gate_result
    assert stored["trade_execution_result"] is None


def test_log_order_execution_preserves_trade_execution_result(tmp_path):
    db_path = str(tmp_path / "test.sqlite")
    initialize_db(db_path).close()

    order = {"ticker": "NVDA", "side": "BUY", "shares": 5.0, "price": 100.0}
    gate_result = {"passed": True, "gates": [], "reasons": []}
    trade_execution_result = {"matched": True, "shares_delta": 0.0}

    order_risk_gates.log_order_execution(
        order, gate_result, "EXECUTED",
        trade_execution_result=trade_execution_result, db_path=db_path,
    )

    conn2 = initialize_db(db_path)
    rows = list_order_executions(conn2)
    stored = json.loads(rows[0]["gate_result_json"])
    assert stored["trade_execution_result"] == trade_execution_result


def test_log_order_execution_never_raises_on_bad_db_path(tmp_path):
    bad_path = str(tmp_path / "nonexistent_dir" / "test.sqlite")
    order = {"ticker": "NVDA", "side": "BUY", "shares": 5.0, "price": 100.0}
    gate_result = {"passed": True, "gates": [], "reasons": []}
    ok = order_risk_gates.log_order_execution(order, gate_result, "EXECUTED", db_path=bad_path)
    assert ok is False
