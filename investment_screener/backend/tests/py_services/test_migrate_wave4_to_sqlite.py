import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.trade_log_entry_repository import list_trade_log_entries  # noqa: E402
from domain_model.order_execution_repository import list_order_executions  # noqa: E402
from domain_model.cash_flow_repository import (  # noqa: E402
    list_cash_flows,
    get_cash_flow_baseline,
    CASH_FLOW_BASELINE_SENTINEL_ACCOUNT,
)
from domain_model.account_repository import list_accounts  # noqa: E402
from domain_model.migrate_wave4_to_sqlite import (  # noqa: E402
    build_dry_run_report,
    execute_migration,
)


TRADE_LOG_FIXTURE = [
    {
        "id": "entry-1", "ticker": "AAPL", "action": "buy", "shares": 2.0,
        "price": 150.0, "totalCost": 300.0, "account": "TFSA",
        "orderType": "market", "limitPrice": None, "date": "2026-07-01",
        "notes": "test note", "status": "executed", "source": "manual",
        "priority": 1, "loggedAt": "2026-07-01T00:00:00Z",
        "extendedHours": False, "tvOrderId": "tv-1",
    },
    {
        "id": "entry-2", "ticker": "MSFT", "action": "sell", "shares": 1.0,
        "price": 400.0, "totalCost": 400.0, "account": "RRSP",
        "orderType": "limit", "limitPrice": 400.0, "date": "2026-07-02",
        "notes": None, "status": "pending", "source": "agent",
        "priority": 2, "loggedAt": "2026-07-02T00:00:00Z",
    },
    {
        "id": "entry-3", "action": "buy", "shares": 1.0, "price": 10.0,
        "totalCost": 10.0, "account": "TFSA", "orderType": "market",
        "limitPrice": None, "date": "2026-07-03", "notes": None,
        "status": "cancelled", "source": "manual", "priority": 1,
        "loggedAt": "2026-07-03T00:00:00Z",
    },
]

ORDERS_EXECUTED_FIXTURE = [
    {
        "timestamp": "2026-07-15T15:32:35.094016+00:00",
        "order": {"ticker": "AAPL", "side": "BUY", "shares": 1.0, "price": 150.0},
        "decision": "BLOCKED",
        "gate_result": {"passed": False, "reasons": ["Insufficient cash"]},
        "trade_execution_result": None,
    },
    {
        "timestamp": "2026-07-16T09:00:00.000000+00:00",
        "order": {"ticker": "MSFT", "side": "SELL", "shares": 1.0, "price": 400.0},
        "decision": "EXECUTED",
        "gate_result": {"passed": True, "reasons": []},
        "trade_execution_result": {"filled": True, "fill_price": 400.0},
    },
]

CASH_FLOWS_FIXTURE = {
    "starting_balance_cad": 37426.0,
    "starting_date": "2026-01-01",
    "cash_flows": [
        {
            "date": "2026-02-06", "type": "deposit", "amount_cad": 2000.0,
            "portfolio_value_before_flow_cad": 39120.0, "account": "TFSA",
        },
        {
            "date": "2026-03-01", "type": "withdrawal", "amount_cad": -500.0,
            "portfolio_value_before_flow_cad": 40000.0, "account": "RRSP",
        },
        {
            "date": "2026-04-01", "type": "deposit", "amount_cad": 100.0,
            "portfolio_value_before_flow_cad": 41000.0,
        },
    ],
}


def _write_fixtures(tmp_path):
    trade_log_path = tmp_path / "trade-log.json"
    orders_executed_path = tmp_path / "orders_executed.jsonl"
    cash_flows_path = tmp_path / "cash_flows.json"

    trade_log_path.write_text(json.dumps(TRADE_LOG_FIXTURE))
    orders_executed_path.write_text(
        "\n".join(json.dumps(rec) for rec in ORDERS_EXECUTED_FIXTURE)
    )
    cash_flows_path.write_text(json.dumps(CASH_FLOWS_FIXTURE))

    return str(trade_log_path), str(orders_executed_path), str(cash_flows_path)


def test_build_dry_run_report_counts_and_no_db_writes(tmp_path):
    trade_log_path, orders_executed_path, cash_flows_path = _write_fixtures(tmp_path)

    report = build_dry_run_report(trade_log_path, orders_executed_path, cash_flows_path)

    assert report["trade_log_entries_count"] == 3
    # entry-3 has no ticker and is excluded from the would-insert count
    assert report["trade_log_entries_would_insert_count"] == 2
    assert report["order_executions_count"] == 2
    assert report["order_executions_would_insert_count"] == 2
    assert report["cash_flows_count"] == 3
    assert report["cash_flows_would_insert_count"] == 3
    assert report["cash_flow_baseline_present"] is True

    # entry-3 has no ticker -> warning
    assert any("entry-3" in w or "missing" in w.lower() for w in report["warnings"])
    # one orders_executed record has non-null trade_execution_result -> warning
    assert any("trade_execution_result" in w for w in report["warnings"])

    # dry-run must not touch any real DB
    db_path = tmp_path / "domain_model.sqlite"
    assert not db_path.exists()


def test_execute_migration_writes_expected_rows_and_resolves_fks(tmp_path):
    trade_log_path, orders_executed_path, cash_flows_path = _write_fixtures(tmp_path)
    db_path = tmp_path / "domain_model.sqlite"
    conn = initialize_db(str(db_path))

    summary = execute_migration(conn, trade_log_path, orders_executed_path, cash_flows_path)

    trade_entries = list_trade_log_entries(conn)
    order_executions = list_order_executions(conn)
    cash_flows = list_cash_flows(conn)
    baseline = get_cash_flow_baseline(conn, CASH_FLOW_BASELINE_SENTINEL_ACCOUNT)
    accounts = list_accounts(conn)

    # entry-3 has no ticker, should be skipped from insertion
    assert len(trade_entries) == 2
    assert len(order_executions) == 2
    assert len(cash_flows) == 3
    assert baseline is not None
    assert baseline["starting_balance_cad"] == 37426.0
    assert baseline["starting_date"] == "2026-01-01"

    account_ids = {a["account_id"] for a in accounts}
    assert "TFSA" in account_ids
    assert "RRSP" in account_ids

    entry_by_id = {e["entry_id"]: e for e in trade_entries}
    assert entry_by_id["entry-1"]["investment_id"] == "AAPL"
    assert entry_by_id["entry-1"]["account_id"] == "TFSA"
    assert entry_by_id["entry-1"]["total_cost"] == 300.0

    assert summary["trade_log_entries_inserted"] == 2
    assert summary["order_executions_inserted"] == 2
    assert summary["cash_flows_inserted"] == 3
    assert summary["cash_flow_baseline_written"] is True


def test_execute_migration_is_idempotent(tmp_path):
    trade_log_path, orders_executed_path, cash_flows_path = _write_fixtures(tmp_path)
    db_path = tmp_path / "domain_model.sqlite"
    conn = initialize_db(str(db_path))

    execute_migration(conn, trade_log_path, orders_executed_path, cash_flows_path)
    execute_migration(conn, trade_log_path, orders_executed_path, cash_flows_path)

    assert len(list_trade_log_entries(conn)) == 2
    assert len(list_order_executions(conn)) == 2
    assert len(list_cash_flows(conn)) == 3
