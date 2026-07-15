"""
Tests for Task 5E-8: Order Execution Audit Trail.

log_order_execution() appends one JSONL record per order attempt to
data/orders_executed.jsonl. Every test passes an explicit
orders_executed_path pointed at a tmp_path fixture — the real
investment_screener/backend/data/orders_executed.jsonl does not exist yet
on disk and must never be created as a side effect of running this suite.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

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


def test_log_order_execution_writes_valid_json_line(tmp_path):
    path = tmp_path / "orders_executed.jsonl"
    result = log_order_execution(
        SAMPLE_ORDER, SAMPLE_GATE_RESULT_PASSED, "EXECUTED", orders_executed_path=path
    )
    assert result is True
    lines = path.read_text().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert set(record.keys()) == {
        "timestamp",
        "order",
        "decision",
        "gate_result",
        "trade_execution_result",
    }


def test_log_order_execution_appends_not_overwrites(tmp_path):
    path = tmp_path / "orders_executed.jsonl"
    order_1 = {**SAMPLE_ORDER, "ticker": "NVDA"}
    order_2 = {**SAMPLE_ORDER, "ticker": "AMD"}

    log_order_execution(order_1, SAMPLE_GATE_RESULT_PASSED, "EXECUTED", orders_executed_path=path)
    log_order_execution(order_2, SAMPLE_GATE_RESULT_FAILED, "BLOCKED", orders_executed_path=path)

    lines = path.read_text().splitlines()
    assert len(lines) == 2
    record_1 = json.loads(lines[0])
    record_2 = json.loads(lines[1])
    assert record_1["order"]["ticker"] == "NVDA"
    assert record_2["order"]["ticker"] == "AMD"


def test_log_order_execution_returns_true_on_success(tmp_path):
    path = tmp_path / "orders_executed.jsonl"
    result = log_order_execution(
        SAMPLE_ORDER, SAMPLE_GATE_RESULT_PASSED, "EXECUTED", orders_executed_path=path
    )
    assert result is True


def test_log_order_execution_includes_gate_result_verbatim(tmp_path):
    path = tmp_path / "orders_executed.jsonl"
    log_order_execution(
        SAMPLE_ORDER, SAMPLE_GATE_RESULT_FAILED, "BLOCKED", orders_executed_path=path
    )
    record = json.loads(path.read_text().splitlines()[0])
    assert record["gate_result"] == SAMPLE_GATE_RESULT_FAILED


def test_log_order_execution_trade_execution_result_defaults_to_none(tmp_path):
    path = tmp_path / "orders_executed.jsonl"
    log_order_execution(
        SAMPLE_ORDER, SAMPLE_GATE_RESULT_PASSED, "EXECUTED", orders_executed_path=path
    )
    record = json.loads(path.read_text().splitlines()[0])
    assert record["trade_execution_result"] is None


def test_log_order_execution_includes_trade_execution_result_when_supplied(tmp_path):
    path = tmp_path / "orders_executed.jsonl"
    log_order_execution(
        SAMPLE_ORDER,
        SAMPLE_GATE_RESULT_PASSED,
        "EXECUTED",
        trade_execution_result=SAMPLE_TRADE_EXECUTION_RESULT,
        orders_executed_path=path,
    )
    record = json.loads(path.read_text().splitlines()[0])
    assert record["trade_execution_result"] == SAMPLE_TRADE_EXECUTION_RESULT


def test_log_order_execution_creates_parent_directory_if_missing(tmp_path):
    path = tmp_path / "nested" / "does_not_exist_yet" / "orders_executed.jsonl"
    assert not path.parent.exists()
    result = log_order_execution(
        SAMPLE_ORDER, SAMPLE_GATE_RESULT_PASSED, "EXECUTED", orders_executed_path=path
    )
    assert result is True
    assert path.exists()
    assert len(path.read_text().splitlines()) == 1


def test_log_order_execution_never_raises_on_write_failure(tmp_path):
    # Point orders_executed_path at a directory (not a file) — open() for
    # append against a directory path raises IsADirectoryError, a subclass
    # of OSError, on every platform this project targets.
    dir_path = tmp_path / "a_directory"
    dir_path.mkdir()
    result = log_order_execution(
        SAMPLE_ORDER, SAMPLE_GATE_RESULT_PASSED, "EXECUTED", orders_executed_path=dir_path
    )
    assert result is False


def test_log_order_execution_timestamp_is_iso8601_utc(tmp_path):
    path = tmp_path / "orders_executed.jsonl"
    log_order_execution(
        SAMPLE_ORDER, SAMPLE_GATE_RESULT_PASSED, "EXECUTED", orders_executed_path=path
    )
    record = json.loads(path.read_text().splitlines()[0])
    parsed = datetime.fromisoformat(record["timestamp"])
    assert parsed.tzinfo is not None
    assert parsed.utcoffset() == timezone.utc.utcoffset(None)


def test_log_order_execution_decision_value_recorded_as_given(tmp_path):
    path = tmp_path / "orders_executed.jsonl"
    log_order_execution(
        SAMPLE_ORDER, SAMPLE_GATE_RESULT_FAILED, "BLOCKED", orders_executed_path=path
    )
    record = json.loads(path.read_text().splitlines()[0])
    assert record["decision"] == "BLOCKED"


def test_log_order_execution_does_not_touch_real_orders_executed_file(tmp_path):
    """Sanity guard: confirms the real data file is never created by this
    suite. Every other test in this file passes an explicit tmp_path
    override; this test asserts that invariant holds project-wide by
    checking the real path does not exist after the full run so far.
    """
    from order_risk_gates import ORDERS_EXECUTED_PATH

    assert not ORDERS_EXECUTED_PATH.exists()
