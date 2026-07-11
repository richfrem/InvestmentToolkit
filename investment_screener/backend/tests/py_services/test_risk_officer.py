"""Tests for risk_officer.py — G2 risk-officer veto classification (Phase 3, sub-spec 5)."""
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from risk_officer import classify_orders, compute_risk_officer_review  # noqa: E402


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


def test_compute_risk_officer_review_no_plan_file_returns_no_plan_status(tmp_path):
    plan_path = tmp_path / "rebalance_plan.json"
    output_path = tmp_path / "risk_officer_review.json"
    result = compute_risk_officer_review(rebalance_plan_path=plan_path, output_path=output_path)
    assert result["status"] == "no_plan"
    assert result["vetoedOrders"] == []
    assert result["approvedOrders"] == []
    assert not output_path.exists()


def test_compute_risk_officer_review_blocked_plan_returns_plan_blocked_status(tmp_path):
    plan_path = tmp_path / "rebalance_plan.json"
    plan_path.write_text(json.dumps({
        "generatedAt": "2026-07-10T13:00:00Z", "blockedReason": "DATA_STALE — ...",
        "orders": [], "bands": {}, "skippedRestores": [], "accountDataSource": {}, "warnings": [],
    }))
    output_path = tmp_path / "risk_officer_review.json"
    result = compute_risk_officer_review(rebalance_plan_path=plan_path, output_path=output_path)
    assert result["status"] == "plan_blocked"
    assert not output_path.exists()


def test_compute_risk_officer_review_writes_file_and_round_trips(tmp_path):
    plan_path = tmp_path / "rebalance_plan.json"
    plan_path.write_text(json.dumps({
        "generatedAt": "2026-07-10T13:58:00Z", "blockedReason": None,
        "orders": [
            _order("CORZ", risk_warnings=["MRC breach"]),
            _order("MSFT"),
        ],
        "bands": {}, "skippedRestores": [], "accountDataSource": {}, "warnings": [],
    }))
    output_path = tmp_path / "risk_officer_review.json"

    result = compute_risk_officer_review(rebalance_plan_path=plan_path, output_path=output_path)

    assert result["status"] == "ok"
    assert result["sourceRebalancePlanGeneratedAt"] == "2026-07-10T13:58:00Z"
    assert "generatedAt" in result
    assert [o["ticker"] for o in result["vetoedOrders"]] == ["CORZ"]
    assert [o["ticker"] for o in result["approvedOrders"]] == ["MSFT"]

    assert output_path.exists()
    on_disk = json.loads(output_path.read_text())
    assert on_disk == result


def test_compute_risk_officer_review_no_save_skips_write(tmp_path):
    plan_path = tmp_path / "rebalance_plan.json"
    plan_path.write_text(json.dumps({
        "generatedAt": "x", "blockedReason": None, "orders": [_order("MSFT")],
        "bands": {}, "skippedRestores": [], "accountDataSource": {}, "warnings": [],
    }))
    output_path = tmp_path / "risk_officer_review.json"
    compute_risk_officer_review(rebalance_plan_path=plan_path, output_path=output_path, save=False)
    assert not output_path.exists()


import pytest

from risk_officer import log_risk_officer_override, _cli_log_override  # noqa: E402


class TestLogRiskOfficerOverride:
    def test_appends_one_jsonl_line(self, tmp_path):
        path = tmp_path / "risk_officer_overrides.jsonl"
        log_risk_officer_override(
            ticker="CORZ", action="buy", account="TFSA", shares=10.0,
            veto_reasons=["MRC breach"],
            rationale="Conviction unchanged, MRC estimate is first-order only",
            path=path,
        )
        lines = path.read_text().strip().splitlines()
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["ticker"] == "CORZ"
        assert entry["action"] == "buy"
        assert entry["account"] == "TFSA"
        assert entry["shares"] == 10.0
        assert entry["vetoReasons"] == ["MRC breach"]
        assert entry["overriddenBy"] == "user"
        assert "date" in entry

    def test_second_call_appends_not_overwrites(self, tmp_path):
        path = tmp_path / "risk_officer_overrides.jsonl"
        log_risk_officer_override(
            ticker="CORZ", action="buy", account="TFSA", shares=10.0,
            veto_reasons=["a"], rationale="first", path=path,
        )
        log_risk_officer_override(
            ticker="NBIS", action="buy", account="RRSP", shares=3.0,
            veto_reasons=["b"], rationale="second", path=path,
        )
        lines = path.read_text().strip().splitlines()
        assert len(lines) == 2


class TestCliLogOverride:
    def test_resolves_vetoed_order_then_logs(self, tmp_path):
        review_path = tmp_path / "risk_officer_review.json"
        overrides_path = tmp_path / "risk_officer_overrides.jsonl"
        review_path.write_text(json.dumps({
            "status": "ok", "generatedAt": "x", "sourceRebalancePlanGeneratedAt": "y",
            "vetoedOrders": [{
                "ticker": "CORZ", "action": "buy", "account": "TFSA", "shares": 10,
                "vetoReasons": ["MRC breach"],
            }],
            "approvedOrders": [],
        }))
        _cli_log_override(
            ticker="CORZ", action="buy", account="TFSA",
            rationale="Conviction unchanged",
            review_path=review_path, overrides_path=overrides_path,
        )
        entry = json.loads(overrides_path.read_text().strip())
        assert entry["shares"] == 10
        assert entry["vetoReasons"] == ["MRC breach"]

    def test_missing_review_file_raises(self, tmp_path):
        review_path = tmp_path / "does_not_exist.json"
        overrides_path = tmp_path / "risk_officer_overrides.jsonl"
        with pytest.raises(ValueError, match="not found"):
            _cli_log_override(
                ticker="CORZ", action="buy", account="TFSA", rationale="x",
                review_path=review_path, overrides_path=overrides_path,
            )

    def test_no_matching_vetoed_order_raises(self, tmp_path):
        review_path = tmp_path / "risk_officer_review.json"
        overrides_path = tmp_path / "risk_officer_overrides.jsonl"
        review_path.write_text(json.dumps({
            "status": "ok", "generatedAt": "x", "sourceRebalancePlanGeneratedAt": "y",
            "vetoedOrders": [], "approvedOrders": [],
        }))
        with pytest.raises(ValueError, match="no vetoed order"):
            _cli_log_override(
                ticker="CORZ", action="buy", account="TFSA", rationale="x",
                review_path=review_path, overrides_path=overrides_path,
            )
