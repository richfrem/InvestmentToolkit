"""
test_tv_manage_indicators.py (Unit Test Suite)
==============================================

Purpose:
    Unit tests for tv_manage_indicators.py orchestrator.

Layer:
    Testing / TradingView Plugin
"""

import pytest
from unittest.mock import patch
import sys
from pathlib import Path

# The scripts under test live in the skill's scripts/ folder; the shared engine (tv_client, ...) is in the backend.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if (p / "investment_screener").is_dir())
                       / "investment_screener/backend/py_services"))
from tv_manage_indicators import (
    list_chart_indicators,
    add_chart_indicator,
    remove_chart_indicator,
)


def test_list_chart_indicators():
    with patch("tv_manage_indicators.tv_call") as mock_call:
        mock_call.return_value = {
            "success": True,
            "indicators": ["AI-TA", "RSI"],
            "count": 2,
            "source": "legend",
        }
        res = list_chart_indicators()
        assert res["success"] is True
        assert res["count"] == 2
        assert "AI-TA" in res["indicators"]
        mock_call.assert_called_once_with("chart", "indicators")


def test_add_chart_indicator():
    with patch("tv_manage_indicators.tv_call") as mock_call:
        mock_call.return_value = {"success": True, "added": "RSI"}
        res = add_chart_indicator("RSI")
        assert res["success"] is True
        mock_call.assert_called_once_with("chart", "addIndicator", "RSI")


def test_add_chart_indicator_empty():
    res = add_chart_indicator("")
    assert res["success"] is False
    assert "cannot be empty" in res["error"]


def test_remove_chart_indicator():
    with patch("tv_manage_indicators.tv_call") as mock_call:
        mock_call.return_value = {"success": True, "removed": "RSI"}
        res = remove_chart_indicator("RSI")
        assert res["success"] is True
        mock_call.assert_called_once_with("chart", "removeIndicator", "RSI")


def test_remove_chart_indicator_empty():
    res = remove_chart_indicator("   ")
    assert res["success"] is False
    assert "cannot be empty" in res["error"]
