"""Tests for risk_officer.py — G2 risk-officer veto classification (Phase 3, sub-spec 5)."""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

import pytest  # noqa: E402

from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.computed_snapshot_repository import (  # noqa: E402
    list_snapshots,
    load_latest_snapshot,
    save_snapshot,
)
from risk_officer import (  # noqa: E402
    classify_orders,
    compute_risk_officer_review,
    log_risk_officer_override,
    _cli_log_override,
)


def _store(db_path, name, payload):
    conn = initialize_db(str(db_path))
    try:
        save_snapshot(conn, name, payload)
    finally:
        conn.close()


def _stored(db_path, name):
    conn = initialize_db(str(db_path))
    try:
        return load_latest_snapshot(conn, name)
    finally:
        conn.close()


def _order(ticker, risk_warnings=None, breaker_warnings=None, **extra):
    return {
        "ticker": ticker, "action": "buy", "account": "TFSA", "shares": 10,
        "rationale": "Out of band: -3.1pp vs 1.5pp band",
        "gatesPassed": ["band_check"],
        "riskGateWarnings": risk_warnings or [],
        "breakerWarnings": breaker_warnings or [],
        "capitalGainsEstimate": None,
        **extra,
    }


def test_classify_orders_vetoes_on_risk_gate_warning_only():
    orders = [_order("CORZ", risk_warnings=["Estimated MRC would reach 31.2% (estimate) > 25% cap"])]
    vetoed, approved = classify_orders(orders)
    assert len(vetoed) == 1
    assert approved == []
    assert vetoed[0]["vetoReasons"] == ["Estimated MRC would reach 31.2% (estimate) > 25% cap"]


def test_classify_orders_vetoes_on_breaker_warning_only():
    orders = [_order("NBIS", breaker_warnings=["TRIGGERED breaker 'nbis-trend': current value 'DOWNTREND', streak 5"])]
    vetoed, approved = classify_orders(orders)
    assert len(vetoed) == 1
    assert vetoed[0]["vetoReasons"] == ["TRIGGERED breaker 'nbis-trend': current value 'DOWNTREND', streak 5"]


def test_classify_orders_approves_when_both_empty():
    orders = [_order("MSFT")]
    vetoed, approved = classify_orders(orders)
    assert vetoed == []
    assert len(approved) == 1
    assert "vetoReasons" not in approved[0]


def test_classify_orders_concatenates_both_reason_lists_risk_first():
    orders = [_order(
        "CORZ",
        risk_warnings=["MRC breach"],
        breaker_warnings=["TRIGGERED breaker 'corz-margin'"],
    )]
    vetoed, _ = classify_orders(orders)
    assert vetoed[0]["vetoReasons"] == ["MRC breach", "TRIGGERED breaker 'corz-margin'"]


def test_classify_orders_preserves_order_and_handles_mixed_batch():
    orders = [_order("A"), _order("B", risk_warnings=["breach"]), _order("C")]
    vetoed, approved = classify_orders(orders)
    assert [o["ticker"] for o in vetoed] == ["B"]
    assert [o["ticker"] for o in approved] == ["A", "C"]


def test_compute_risk_officer_review_no_stored_plan_returns_no_plan_status(tmp_path):
    db_path = tmp_path / "domain_model.sqlite"
    result = compute_risk_officer_review(db_path=db_path)
    assert result["status"] == "no_plan"
    assert result["vetoedOrders"] == []
    assert result["approvedOrders"] == []
    assert _stored(db_path, "risk_officer_review") is None


def test_compute_risk_officer_review_blocked_plan_returns_plan_blocked_status(tmp_path):
    db_path = tmp_path / "domain_model.sqlite"
    _store(db_path, "rebalance_plan", {
        "generatedAt": "2026-07-10T13:00:00Z", "blockedReason": "DATA_STALE — ...",
        "orders": [], "bands": {}, "skippedRestores": [], "accountDataSource": {}, "warnings": [],
    })
    result = compute_risk_officer_review(db_path=db_path)
    assert result["status"] == "plan_blocked"
    assert _stored(db_path, "risk_officer_review") is None


def test_compute_risk_officer_review_stores_the_review_and_round_trips(tmp_path):
    db_path = tmp_path / "domain_model.sqlite"
    _store(db_path, "rebalance_plan", {
        "generatedAt": "2026-07-10T13:58:00Z", "blockedReason": None,
        "orders": [
            _order("CORZ", risk_warnings=["MRC breach"]),
            _order("MSFT"),
        ],
        "bands": {}, "skippedRestores": [], "accountDataSource": {}, "warnings": [],
    })

    result = compute_risk_officer_review(db_path=db_path)

    assert result["status"] == "ok"
    assert result["sourceRebalancePlanGeneratedAt"] == "2026-07-10T13:58:00Z"
    assert "generatedAt" in result
    assert [o["ticker"] for o in result["vetoedOrders"]] == ["CORZ"]
    assert [o["ticker"] for o in result["approvedOrders"]] == ["MSFT"]
    assert _stored(db_path, "risk_officer_review") == result


def test_compute_risk_officer_review_no_save_stores_nothing(tmp_path):
    db_path = tmp_path / "domain_model.sqlite"
    _store(db_path, "rebalance_plan", {
        "generatedAt": "x", "blockedReason": None, "orders": [_order("MSFT")],
        "bands": {}, "skippedRestores": [], "accountDataSource": {}, "warnings": [],
    })
    compute_risk_officer_review(db_path=db_path, save=False)
    assert _stored(db_path, "risk_officer_review") is None


def _overrides(db_path):
    conn = initialize_db(str(db_path))
    try:
        return list_snapshots(conn, "risk_officer_override")
    finally:
        conn.close()


class TestLogRiskOfficerOverride:
    def test_stores_one_override_record(self, tmp_path):
        db_path = tmp_path / "domain_model.sqlite"
        log_risk_officer_override(
            ticker="CORZ", action="buy", account="TFSA", shares=10.0,
            veto_reasons=["MRC breach"],
            rationale="Conviction unchanged, MRC estimate is first-order only",
            db_path=db_path,
        )
        entries = _overrides(db_path)
        assert len(entries) == 1
        entry = entries[0]
        assert entry["ticker"] == "CORZ"
        assert entry["action"] == "buy"
        assert entry["account"] == "TFSA"
        assert entry["shares"] == 10.0
        assert entry["vetoReasons"] == ["MRC breach"]
        assert entry["overriddenBy"] == "user"
        assert "date" in entry

    def test_second_call_appends_not_overwrites(self, tmp_path):
        db_path = tmp_path / "domain_model.sqlite"
        log_risk_officer_override(
            ticker="CORZ", action="buy", account="TFSA", shares=10.0,
            veto_reasons=["a"], rationale="first", db_path=db_path,
        )
        log_risk_officer_override(
            ticker="NBIS", action="buy", account="RRSP", shares=3.0,
            veto_reasons=["b"], rationale="second", db_path=db_path,
        )
        assert [e["rationale"] for e in _overrides(db_path)] == ["first", "second"]


class TestCliLogOverride:
    def test_resolves_vetoed_order_then_logs(self, tmp_path):
        db_path = tmp_path / "domain_model.sqlite"
        _store(db_path, "risk_officer_review", {
            "status": "ok", "generatedAt": "x", "sourceRebalancePlanGeneratedAt": "y",
            "vetoedOrders": [{
                "ticker": "CORZ", "action": "buy", "account": "TFSA", "shares": 10,
                "vetoReasons": ["MRC breach"],
            }],
            "approvedOrders": [],
        })
        _cli_log_override(
            ticker="CORZ", action="buy", account="TFSA",
            rationale="Conviction unchanged", db_path=db_path,
        )
        entry = _overrides(db_path)[0]
        assert entry["shares"] == 10
        assert entry["vetoReasons"] == ["MRC breach"]

    def test_missing_review_raises(self, tmp_path):
        db_path = tmp_path / "domain_model.sqlite"
        with pytest.raises(ValueError, match="no stored risk officer review"):
            _cli_log_override(
                ticker="CORZ", action="buy", account="TFSA", rationale="x", db_path=db_path,
            )

    def test_no_matching_vetoed_order_raises(self, tmp_path):
        db_path = tmp_path / "domain_model.sqlite"
        _store(db_path, "risk_officer_review", {
            "status": "ok", "generatedAt": "x", "sourceRebalancePlanGeneratedAt": "y",
            "vetoedOrders": [], "approvedOrders": [],
        })
        with pytest.raises(ValueError, match="no vetoed order"):
            _cli_log_override(
                ticker="CORZ", action="buy", account="TFSA", rationale="x", db_path=db_path,
            )
