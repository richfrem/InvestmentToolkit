#!/usr/bin/env python3
"""
tv_cdp_health.py - Python utility script.

Purpose:
    TV CDP Health Check Module

Provides health_check() function to verify TradingView CDP engine status.
Returns structured health status including port connectivity, chart responsiveness,
and Chrome version information.

Key Input Dependencies:
    - TradingView CDP engine running on localhost:9222
    - tv_client.py for CDP communication

Layer:
    Backend / Python Services

Usage Examples:
    TBD

Key Functions (Index):
    - HealthCheckResult()
    - health_check()
    - _check_port_open()
    - _get_chrome_version()
    - _check_chart_responsive()

Key Input Dependencies:
    None

Key Output Dependencies:
    None
"""
import json
import socket
import urllib.request
import urllib.error
import logging
from typing import TypedDict, Optional

# Configure logging for health checks
logger = logging.getLogger(__name__)


class HealthCheckResult(TypedDict):
    """Health check result structure."""
    port_open: bool
    chart_responsive: bool
    chrome_version: str
    last_error: Optional[str]


def health_check(timeout: int = 5) -> HealthCheckResult:
    """
    Check TradingView CDP engine health status.

    Verifies:
      1. Port 9222 is open and responding
      2. Chart read endpoint is responsive
      3. Chrome version is detectable
      4. Captures any errors encountered

    Args:
        timeout: Timeout in seconds for each check (default: 5)

    Returns:
        HealthCheckResult dict with:
            - port_open: bool indicating if port 9222 is responding
            - chart_responsive: bool indicating if chart read succeeds
            - chrome_version: str with Chrome version or "unknown"
            - last_error: str with error message or None
    """
    result: HealthCheckResult = {
        "port_open": False,
        "chart_responsive": False,
        "chrome_version": "unknown",
        "last_error": None,
    }

    # Step 1: Check port 9222 is open
    try:
        result["port_open"] = _check_port_open(9222, timeout=timeout)
    except Exception as e:
        error_msg = str(e)
        result["last_error"] = error_msg
        logger.warning(f"Port check failed: {error_msg}")
        return result

    if not result["port_open"]:
        result["last_error"] = "Port 9222 is not responding"
        return result

    # Step 2: Try to detect Chrome version from CDP
    try:
        chrome_version = _get_chrome_version(timeout=timeout)
        if chrome_version:
            result["chrome_version"] = chrome_version
    except Exception as e:
        error_msg = str(e)
        logger.warning(f"Chrome version detection failed: {error_msg}")

    # Step 3: Check chart responsiveness via tv_call
    try:
        result["chart_responsive"] = _check_chart_responsive(timeout=timeout)
    except Exception as e:
        error_msg = str(e)
        result["last_error"] = error_msg
        logger.warning(f"Chart responsiveness check failed: {error_msg}")

    return result


def _check_port_open(port: int, timeout: int = 5) -> bool:
    """
    Check if the given port is open and responding via HTTP.

    Args:
        port: Port number to check
        timeout: Timeout in seconds

    Returns:
        True if port responds to HTTP request, False otherwise

    Raises:
        Exception: If connection fails
    """
    try:
        url = f"http://localhost:{port}/json/list"
        req = urllib.request.urlopen(url, timeout=timeout)
        data = json.loads(req.read())
        return isinstance(data, list)
    except (urllib.error.URLError, socket.timeout, ConnectionRefusedError) as e:
        raise Exception(f"Port {port} not responding: {type(e).__name__}: {str(e)}")
    except json.JSONDecodeError as e:
        raise Exception(f"Invalid JSON from port {port}: {str(e)}")


def _get_chrome_version(timeout: int = 5) -> Optional[str]:
    """
    Detect Chrome version from CDP /json/version endpoint.

    Args:
        timeout: Timeout in seconds

    Returns:
        Chrome version string or None if unable to detect

    Raises:
        Exception: If version check fails
    """
    try:
        url = "http://localhost:9222/json/version"
        req = urllib.request.urlopen(url, timeout=timeout)
        data = json.loads(req.read())

        # Extract version from various possible formats
        if isinstance(data, dict):
            version = data.get("Browser", "")
            if version and "/" in version:
                # Format is typically "Chrome/120.0.1234.567"
                return version.split("/")[-1]
            return version if version else None
        return None
    except Exception as e:
        raise Exception(f"Chrome version detection error: {str(e)}")


def _check_chart_responsive(timeout: int = 5) -> bool:
    """
    Check if chart read command responds successfully via tv_call.

    Args:
        timeout: Timeout in seconds

    Returns:
        True if chart read succeeds with non-empty response, False otherwise

    Raises:
        Exception: If chart check fails
    """
    try:
        # Import tv_client here to avoid circular imports
        import sys
        from pathlib import Path

        tv_scripts = str(Path(__file__).resolve().parents[3] / "plugins/tradingview/scripts")
        if tv_scripts not in sys.path:
            sys.path.insert(0, tv_scripts)

        from tv_client import tv_call  # type: ignore[import]

        # Call chart read with timeout
        response = tv_call("chart", "read", timeout=timeout)

        # Verify response is non-empty
        if not response:
            raise Exception("Chart read returned empty response")

        return True
    except Exception as e:
        raise Exception(f"Chart responsiveness check failed: {str(e)}")
