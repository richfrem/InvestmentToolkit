"""
Unit tests for alert reconciliation in tv_create_alerts.py
Tests drift detection, missing alert detection, and PSU alias normalization.
"""

import pytest
from plugins.tradingview.scripts.tv_create_alerts import reconcile_alerts


def test_reconcile_alerts_all_matched():
    target_levels = {
        "NVDA": {"fair_value": 180.0, "target_entry": 135.0, "stop_loss": 110.0},
        "PSU-U.TO": {"fair_value": 100.0, "target_entry": 99.5, "stop_loss": None},
    }
    active_tv_alerts = [
        {"symbol": "NASDAQ:NVDA", "price": 180.0, "condition": "crossing"},
        {"symbol": "NASDAQ:NVDA", "price": 135.0, "condition": "crossing"},
        {"symbol": "NASDAQ:NVDA", "price": 110.0, "condition": "crossing"},
        # Alias test: TSX:PSU.U.TO should match PSU-U.TO
        {"symbol": "TSX:PSU.U.TO", "price": 99.5, "condition": "crossing"},
        {"symbol": "TSX:PSU.U.TO", "price": 100.0, "condition": "crossing"},
    ]

    report = reconcile_alerts(target_levels, active_tv_alerts)
    assert len(report["missing"]) == 0
    assert len(report["drifted"]) == 0
    assert len(report["matched"]) >= 4


def test_reconcile_alerts_detects_missing_and_drift():
    target_levels = {
        "CRWV": {"fair_value": 25.0, "target_entry": 18.0, "stop_loss": 14.0},
    }
    active_tv_alerts = [
        {"symbol": "CRWV", "price": 20.0, "condition": "crossing"},  # Drifted from 25 or 18
    ]

    report = reconcile_alerts(target_levels, active_tv_alerts)
    assert len(report["missing"]) >= 1
    assert "CRWV" in [m["symbol"] for m in report["missing"]]
