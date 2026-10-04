"""
Tests for Task 5E-8: Order Execution Audit Trail.

log_order_execution() appends one audit record per order attempt to the
``order_execution`` SQLite table (Wave 4 cutover; orders_executed.jsonl is
retired). Every test passes an explicit db_path pointed at a tmp_path
fixture, so the real domain_model.sqlite is never touched by this suite.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.order_execution_repository import list_order_executions  # noqa: E402
from order_risk_gates import log_order_execution  # noqa: E402

SAMPLE_ORDER = {"ticker": "NVDA", "side": "BUY", "shares": 10.0, "price": 120.50}

SAMPLE_GATE_RESULT_PASSED = {
    "passed": True,
    "gates": [
        {"name": "mrc", "passed": True, "reason": "Within MRC cap"},
        {"name": "cluster_variance", "passed": True, "reason": "Within cluster cap"},
        {"name": "breaker_veto", "passed": True, "reason": "No triggered breaker"},
        {"name": "size", "passed": True, "reason": "Within ADV limit"},
        {"name": "balance", "passed": True, "reason": "Sufficient cash"},
    ],
    "reasons": [],
}

SAMPLE_GATE_RESULT_FAILED = {
    "passed": False,
    "gates": [
        {"name": "mrc", "passed": False, "reason": "MRC exceeds 5% cap"},
        {"name": "cluster_variance", "passed": True, "reason": "Within cluster cap"},
        {"name": "breaker_veto", "passed": True, "reason": "No triggered breaker"},
        {"name": "size", "passed": True, "reason": "Within ADV limit"},
        {"name": "balance", "passed": True, "reason": "Sufficient cash"},
    ],
    "reasons": ["MRC exceeds 5% cap"],
}

SAMPLE_TRADE_EXECUTION_RESULT = {
    "matched": True,
    "shares_delta": 0.0,
    "price_slippage_pct": 0.41,
    "slippage_flagged": False,
    "reason": "Trade execution matches order",
}


def _db(tmp_path) -> str:
    db_path = str(tmp_path / "test.sqlite")
    initialize_db(db_path).close()
    return db_path


def _rows(db_path: str) -> list[dict]:
    conn = initialize_db(db_path)
    try:
        return list_order_executions(conn)
    finally:
        conn.close()


def _stored(row: dict) -> dict:
    return json.loads(row["gate_result_json"])


def test_log_order_execution_writes_one_row_with_order_fields(tmp_path):
    db_path = _db(tmp_path)
    result = log_order_execution(
        SAMPLE_ORDER, SAMPLE_GATE_RESULT_PASSED, "EXECUTED", db_path=db_path
    )
    assert result is True
    rows = _rows(db_path)
    assert len(rows) == 1
    row = rows[0]
    assert row["investment_id"] == "NVDA"
    assert row["side"] == "BUY"
    assert row["shares"] == 10.0
    assert row["price"] == 120.50
    assert set(_stored(row).keys()) == {"gate_result", "trade_execution_result"}


def test_log_order_execution_appends_not_overwrites(tmp_path):
    db_path = _db(tmp_path)
    order_1 = {**SAMPLE_ORDER, "ticker": "NVDA"}
    order_2 = {**SAMPLE_ORDER, "ticker": "AMD"}

    log_order_execution(order_1, SAMPLE_GATE_RESULT_PASSED, "EXECUTED", db_path=db_path)
    log_order_execution(order_2, SAMPLE_GATE_RESULT_FAILED, "BLOCKED", db_path=db_path)

    rows = _rows(db_path)
    assert len(rows) == 2
    assert [r["investment_id"] for r in rows] == ["NVDA", "AMD"]


def test_log_order_execution_includes_gate_result_verbatim(tmp_path):
    db_path = _db(tmp_path)
    log_order_execution(SAMPLE_ORDER, SAMPLE_GATE_RESULT_FAILED, "BLOCKED", db_path=db_path)
    assert _stored(_rows(db_path)[0])["gate_result"] == SAMPLE_GATE_RESULT_FAILED


def test_log_order_execution_trade_execution_result_defaults_to_none(tmp_path):
    db_path = _db(tmp_path)
    log_order_execution(SAMPLE_ORDER, SAMPLE_GATE_RESULT_PASSED, "EXECUTED", db_path=db_path)
    assert _stored(_rows(db_path)[0])["trade_execution_result"] is None


def test_log_order_execution_includes_trade_execution_result_when_supplied(tmp_path):
    db_path = _db(tmp_path)
    log_order_execution(
        SAMPLE_ORDER,
        SAMPLE_GATE_RESULT_PASSED,
        "EXECUTED",
        trade_execution_result=SAMPLE_TRADE_EXECUTION_RESULT,
        db_path=db_path,
    )
    assert _stored(_rows(db_path)[0])["trade_execution_result"] == SAMPLE_TRADE_EXECUTION_RESULT


def test_log_order_execution_never_raises_on_write_failure(tmp_path):
    # A directory is not an openable SQLite database — the write must fail
    # quietly (return False), never raise into a live order flow.
    dir_path = tmp_path / "a_directory"
    dir_path.mkdir()
    result = log_order_execution(
        SAMPLE_ORDER, SAMPLE_GATE_RESULT_PASSED, "EXECUTED", db_path=str(dir_path)
    )
    assert result is False


def test_log_order_execution_timestamp_is_iso8601_utc(tmp_path):
    db_path = _db(tmp_path)
    log_order_execution(SAMPLE_ORDER, SAMPLE_GATE_RESULT_PASSED, "EXECUTED", db_path=db_path)
    parsed = datetime.fromisoformat(_rows(db_path)[0]["executed_at"])
    assert parsed.tzinfo is not None
    assert parsed.utcoffset() == timezone.utc.utcoffset(None)


def test_log_order_execution_decision_value_recorded_as_given(tmp_path):
    db_path = _db(tmp_path)
    log_order_execution(SAMPLE_ORDER, SAMPLE_GATE_RESULT_FAILED, "BLOCKED", db_path=db_path)
    assert _rows(db_path)[0]["decision"] == "BLOCKED"
