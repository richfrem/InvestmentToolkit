"""
Task 5A-1: Health Check Implementation

Tests for tv_cdp_health.py health_check() function.
Verifies port connectivity, chart responsiveness, Chrome version detection,
and error handling.
"""

import sys
import json
from pathlib import Path
from unittest.mock import patch, Mock, MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from tv_cdp_health import health_check, _check_port_open, _get_chrome_version, _check_chart_responsive


def test_health_check_port_open_returns_true():
    """Port 9222 responds to HTTP request, port_open=True."""
    mock_response = Mock()
    mock_response.read.return_value = json.dumps([
        {
            "type": "page",
            "url": "https://www.tradingview.com",
            "title": "TradingView"
        }
    ]).encode()

    with patch("urllib.request.urlopen", return_value=mock_response) as mock_urlopen:
        with patch("tv_cdp_health._check_chart_responsive", return_value=True):
            result = health_check(timeout=5)

            # Port check should succeed
            assert result["port_open"] is True
            mock_urlopen.assert_called()


def test_health_check_port_closed_returns_false():
    """Port 9222 is closed, port_open=False and last_error is set."""
    with patch("urllib.request.urlopen", side_effect=ConnectionRefusedError("Connection refused")):
        result = health_check(timeout=5)

        # Port check should fail
        assert result["port_open"] is False
        assert result["last_error"] is not None
        assert "Connection refused" in result["last_error"] or "not responding" in result["last_error"]


def test_health_check_chart_responsive_returns_true():
    """Chart read command succeeds with non-empty response, chart_responsive=True."""
    mock_response = Mock()
    mock_response.read.return_value = json.dumps([
        {
            "type": "page",
            "url": "https://www.tradingview.com",
            "title": "TradingView"
        }
    ]).encode()

    chart_data = {
        "symbol": "AAPL",
        "close": 150.0,
        "volume": 1000000
    }

    with patch("urllib.request.urlopen", return_value=mock_response):
        with patch("tv_cdp_health._check_chart_responsive", return_value=True) as mock_chart:
            result = health_check(timeout=5)

            # Chart check should succeed
            assert result["chart_responsive"] is True
            mock_chart.assert_called()


def test_health_check_chart_stale_returns_false():
    """Chart read returns empty/error, chart_responsive=False and last_error set."""
    mock_response = Mock()
    mock_response.read.return_value = json.dumps([
        {
            "type": "page",
            "url": "https://www.tradingview.com",
            "title": "TradingView"
        }
    ]).encode()

    with patch("urllib.request.urlopen", return_value=mock_response):
        with patch("tv_cdp_health._check_chart_responsive", side_effect=Exception("Chart read failed")):
            result = health_check(timeout=5)

            # Chart check should fail due to error
            assert result["chart_responsive"] is False
            assert result["last_error"] is not None


def test_health_check_chrome_version_extracted():
    """Chrome version is detected and populated in result."""
    mock_port_response = Mock()
    mock_port_response.read.return_value = json.dumps([
        {
            "type": "page",
            "url": "https://www.tradingview.com",
            "title": "TradingView"
        }
    ]).encode()

    mock_version_response = Mock()
    mock_version_response.read.return_value = json.dumps({
        "Browser": "Chrome/120.0.6099.129"
    }).encode()

    def mock_urlopen(url, *args, **kwargs):
        if "/json/version" in url:
            return mock_version_response
        return mock_port_response

    with patch("urllib.request.urlopen", side_effect=mock_urlopen):
        with patch("tv_cdp_health._check_chart_responsive", return_value=True):
            result = health_check(timeout=5)

            # Chrome version should be extracted
            assert result["chrome_version"] != "unknown"
            assert "120" in result["chrome_version"] or "6099" in result["chrome_version"]


def test_health_check_error_message_captures_exception():
    """Exceptions are captured and stored in last_error on failures."""
    with patch("urllib.request.urlopen", side_effect=Exception("Network error occurred")):
        result = health_check(timeout=5)

        # last_error should capture the exception message
        assert result["last_error"] is not None
        assert "Network error" in result["last_error"] or "not responding" in result["last_error"]
        assert result["port_open"] is False


# Additional edge case tests for comprehensive coverage

def test_check_port_open_with_timeout():
    """Port check respects timeout parameter."""
    mock_response = Mock()
    mock_response.read.return_value = json.dumps([]).encode()

    with patch("urllib.request.urlopen", return_value=mock_response) as mock_urlopen:
        result = _check_port_open(9222, timeout=3)

        assert result is True
        # Verify that urlopen was called with the correct timeout
        call_kwargs = mock_urlopen.call_args[1]
        assert call_kwargs["timeout"] == 3


def test_get_chrome_version_with_standard_format():
    """Chrome version parsing handles standard Chrome version format."""
    mock_response = Mock()
    mock_response.read.return_value = json.dumps({
        "Browser": "Chrome/119.0.5555.123",
        "Protocol-Version": "1.3"
    }).encode()

    with patch("urllib.request.urlopen", return_value=mock_response):
        version = _get_chrome_version(timeout=5)

        assert version == "119.0.5555.123"


def test_get_chrome_version_returns_none_on_empty():
    """Chrome version returns None if version field is empty."""
    mock_response = Mock()
    mock_response.read.return_value = json.dumps({
        "Browser": ""
    }).encode()

    with patch("urllib.request.urlopen", return_value=mock_response):
        version = _get_chrome_version(timeout=5)

        assert version is None


def test_check_chart_responsive_handles_missing_tv_client():
    """Chart check gracefully handles when tv_client module is unavailable."""
    mock_response = Mock()
    mock_response.read.return_value = json.dumps([
        {
            "type": "page",
            "url": "https://www.tradingview.com",
            "title": "TradingView"
        }
    ]).encode()

    with patch("urllib.request.urlopen", return_value=mock_response):
        with patch("tv_cdp_health._check_chart_responsive", side_effect=ImportError("tv_client not found")):
            result = health_check(timeout=5)

            # Should handle the import error gracefully
            assert result["port_open"] is True
            assert result["chart_responsive"] is False
            assert result["last_error"] is not None
