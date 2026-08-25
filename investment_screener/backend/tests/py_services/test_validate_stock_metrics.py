#!/usr/bin/env python3
"""
Unit test for validate_stock_metrics.py
"""
import pytest
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent.parent.parent / "py_services"
sys.path.insert(0, str(_HERE))

from validate_stock_metrics import validate_metrics_payload

def test_validate_metrics_success():
    payload = {
        "symbol": "INTC",
        "price": 88.90,
        "metrics": {"pe_ratio": 0.0, "revenue_growth": 25.4},
        "expert_metrics": {
            "piotroski_f_score": {"score": 5},
            "rule_of_40": {"revenue_growth": 25.4, "ebitda_margin": 27.2, "score": 52.6}
        }
    }
    result = validate_metrics_payload(payload, shares_held=0.0)
    assert result["valid"] is True
    assert len(result["errors"]) == 0

def test_validate_non_holding_action_guard():
    payload = {
        "symbol": "INTC",
        "price": 88.90,
        "action": "TRIM",
        "metrics": {},
        "expert_metrics": {"piotroski_f_score": {"score": 5}}
    }
    result = validate_metrics_payload(payload, shares_held=0.0)
    assert result["valid"] is False
    assert any("cannot have action 'TRIM'" in e for e in result["errors"])

def test_validate_non_holding_maintain_guard():
    payload = {
        "symbol": "INTC",
        "price": 88.90,
        "action": "MAINTAIN",
        "metrics": {},
        "expert_metrics": {"piotroski_f_score": {"score": 5}}
    }
    result = validate_metrics_payload(payload, shares_held=0.0)
    assert result["valid"] is False
    assert any("cannot have action 'MAINTAIN'" in e for e in result["errors"])

if __name__ == "__main__":
    pytest.main([__file__])
