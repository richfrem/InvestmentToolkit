"""Tests for execution_quality_scorecard.py — Phase 6 execution-quality groundwork.

Wave 4 cutover: load_orders_executed()/build_report() now read the
``order_execution`` SQLite table via order_execution_repository, not
orders_executed.jsonl (retired/archived).
"""
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
PY_SERVICES = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(PY_SERVICES))

from execution_quality_scorecard import (  # noqa: E402
    build_report,
    compute_decision_breakdown,
    compute_gate_fail_rates,
    compute_overridden_registry,
    load_orders_executed,
)
from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.investment_repository import resolve_investment  # noqa: E402
from domain_model.order_execution_repository import insert_order_execution  # noqa: E402


def _seed(db_path, decision, gates, ticker="AAPL", side="BUY", execution_id=None,
          timestamp="2026-07-15T15:32:35.094016+00:00"):
    conn = initialize_db(str(db_path))
    investment_id = resolve_investment(conn, ticker)
    gate_result = {
        "passed": all(g["passed"] for g in gates),
        "gates": gates,
        "reasons": [g["reason"] for g in gates if not g["passed"]],
    }
    insert_order_execution(conn, {
        "execution_id": execution_id or f"{ticker}-{timestamp}",
        "executed_at": timestamp,
        "investment_id": investment_id,
        "side": side,
        "shares": 1.0,
        "price": 150.0,
        "decision": decision,
        "gate_result_json": json.dumps({
            "gate_result": gate_result,
            "trade_execution_result": None,
        }),
    })


def _order(decision, gates, ticker="AAPL", side="BUY"):
    """In-memory dict shape matching load_orders_executed()'s output."""
    return {
        "timestamp": "2026-07-15T15:32:35.094016+00:00",
        "order": {"ticker": ticker, "side": side, "shares": 1.0, "price": 150.0},
        "decision": decision,
        "gate_result": {
            "passed": all(g["passed"] for g in gates),
            "gates": gates,
            "reasons": [g["reason"] for g in gates if not g["passed"]],
        },
        "trade_execution_result": None,
    }


class TestLoadOrdersExecuted:
    def test_missing_db_returns_empty_list(self, tmp_path):
        assert load_orders_executed(tmp_path / "nonexistent.sqlite") == []

    def test_loads_real_records_from_sqlite(self, tmp_path):
        db_path = tmp_path / "test.sqlite"
        _seed(db_path, "BLOCKED", [{"name": "balance", "passed": False, "reason": "Insufficient cash"}])
        loaded = load_orders_executed(db_path)
        assert len(loaded) == 1
        assert loaded[0]["decision"] == "BLOCKED"
        assert loaded[0]["order"]["ticker"] == "AAPL"
        assert loaded[0]["gate_result"]["gates"][0]["name"] == "balance"


class TestComputeDecisionBreakdown:
    def test_counts_each_decision_type(self):
        orders = [
            _order("EXECUTED", [{"name": "balance", "passed": True, "reason": "ok"}]),
            _order("EXECUTED", [{"name": "balance", "passed": True, "reason": "ok"}]),
            _order("BLOCKED", [{"name": "balance", "passed": False, "reason": "no cash"}]),
            _order("OVERRIDDEN", [{"name": "mrc", "passed": False, "reason": "MRC over cap"}]),
        ]
        result = compute_decision_breakdown(orders)
        assert result == {"EXECUTED": 2, "BLOCKED": 1, "OVERRIDDEN": 1}

    def test_empty_input_yields_all_zero_counts(self):
        result = compute_decision_breakdown([])
        assert result == {"EXECUTED": 0, "BLOCKED": 0, "OVERRIDDEN": 0}


class TestComputeGateFailRates:
    def test_computes_fail_rate_per_gate(self):
        orders = [
            _order("EXECUTED", [
                {"name": "balance", "passed": True, "reason": "ok"},
                {"name": "mrc", "passed": True, "reason": "ok"},
            ]),
            _order("BLOCKED", [
                {"name": "balance", "passed": False, "reason": "no cash"},
                {"name": "mrc", "passed": True, "reason": "ok"},
            ]),
        ]
        result = compute_gate_fail_rates(orders)
        assert result["balance"] == {"failCount": 1, "totalSeen": 2, "failRate": 0.5}
        assert result["mrc"] == {"failCount": 0, "totalSeen": 2, "failRate": 0.0}

    def test_gate_never_seen_is_absent_not_zero(self):
        orders = [_order("EXECUTED", [{"name": "balance", "passed": True, "reason": "ok"}])]
        result = compute_gate_fail_rates(orders)
        assert "cluster_variance" not in result

    def test_empty_input_yields_empty_dict(self):
        assert compute_gate_fail_rates([]) == {}


class TestComputeOverriddenRegistry:
    def test_lists_only_overridden_orders_with_failed_gate_detail(self):
        orders = [
            _order("EXECUTED", [{"name": "balance", "passed": True, "reason": "ok"}]),
            _order("OVERRIDDEN", [
                {"name": "mrc", "passed": False, "reason": "MRC over cap"},
                {"name": "balance", "passed": True, "reason": "ok"},
            ], ticker="NVDA", side="BUY"),
        ]
        registry = compute_overridden_registry(orders)
        assert len(registry) == 1
        assert registry[0]["ticker"] == "NVDA"
        assert registry[0]["overriddenGates"] == ["mrc"]
        assert registry[0]["reasons"] == ["MRC over cap"]

    def test_no_overridden_orders_yields_empty_list(self):
        orders = [_order("EXECUTED", [{"name": "balance", "passed": True, "reason": "ok"}])]
        assert compute_overridden_registry(orders) == []


class TestBuildReport:
    def test_report_has_expected_shape(self, tmp_path):
        db_path = tmp_path / "test.sqlite"
        _seed(db_path, "BLOCKED", [{"name": "balance", "passed": False, "reason": "no cash"}])

        report = build_report(db_path)
        assert report["totalOrdersLogged"] == 1
        assert report["decisionBreakdown"]["BLOCKED"] == 1
        assert "balance" in report["gateFailRates"]
        assert report["overriddenRegistry"] == []

    def test_report_on_missing_db_degrades_gracefully(self, tmp_path):
        report = build_report(tmp_path / "no_such_file.sqlite")
        assert report["totalOrdersLogged"] == 0
        assert report["decisionBreakdown"] == {"EXECUTED": 0, "BLOCKED": 0, "OVERRIDDEN": 0}
        assert report["gateFailRates"] == {}
        assert report["overriddenRegistry"] == []
