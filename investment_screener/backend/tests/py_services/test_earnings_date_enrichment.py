#!/usr/bin/env python3
"""
Test-Driven Development (TDD) unit test for earnings date extraction and enrichment.
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

_HERE = Path(__file__).resolve().parent
_PY_SERVICES = _HERE.parent.parent / "py_services"
sys.path.insert(0, str(_PY_SERVICES))

from fetch_portfolio_heatmap import extract_earnings_info

def test_extract_earnings_info_from_timestamp():
    # 1788292800 -> 2026-09-01
    info = {"earningsTimestamp": 1788292800}
    res = extract_earnings_info(info)
    assert res is not None
    assert res["earningsDate"] == "2026-09-01"
    assert res["earningsTimestamp"] == 1788292800
    assert isinstance(res["daysToEarnings"], int)

def test_extract_earnings_info_from_start_timestamp():
    info = {"earningsTimestampStart": 1788465600}
    res = extract_earnings_info(info)
    assert res is not None
    assert res["earningsDate"] == "2026-09-03"
    assert res["earningsTimestamp"] == 1788465600

def test_extract_earnings_info_none():
    info = {}
    res = extract_earnings_info(info)
    assert res is None

if __name__ == "__main__":
    import pytest
    pytest.main([__file__])
