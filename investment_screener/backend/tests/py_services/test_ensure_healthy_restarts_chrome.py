"""
Task 5A-2: Chrome Session Recovery

Tests for tv_cdp_health.py ensure_healthy() function.
Verifies Chrome process recovery, port polling, and recovery validation.
"""

import sys
import time
from pathlib import Path
from unittest.mock import patch, Mock, MagicMock, call

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from tv_cdp_health import (
    ensure_healthy,
    run_tv_cdp_subprocess,
    _kill_chrome_process_on_port,
    _wait_for_port_ready,
    health_check,
)


# --- Test 1: Returns early if already healthy ---

def test_ensure_healthy_returns_early_if_healthy():
    """
    When health_check() returns healthy (port_open=True, chart_responsive=True),
    ensure_healthy() should return early without restart.
    """
    healthy_result = {
        "port_open": True,
        "chart_responsive": True,
        "chrome_version": "120.0.1234.567",
        "last_error": None,
    }

    with patch("tv_cdp_health.health_check", return_value=healthy_result) as mock_health_check:
        with patch("tv_cdp_health.run_tv_cdp_subprocess") as mock_spawn:
            result = ensure_healthy(max_wait_seconds=30)

            # Should return early with no-op reason
            assert result["recovered"] is False
            assert "already healthy" in result["reason"]
            assert result["new_health"] == healthy_result

            # health_check called once (initial check only)
            mock_health_check.assert_called_once()

            # run_tv_cdp_subprocess should NOT be called
            mock_spawn.assert_not_called()


# --- Test 2: Kills Chrome process when unhealthy ---

def test_ensure_healthy_kills_chrome_process():
    """
    When health_check() returns unhealthy (port_open=False),
    ensure_healthy() should call _kill_chrome_process_on_port() to clean up.
    """
    unhealthy_initial = {
        "port_open": False,
        "chart_responsive": False,
        "chrome_version": "unknown",
        "last_error": "Port 9222 is not responding",
    }

    healthy_recovery = {
        "port_open": True,
        "chart_responsive": True,
        "chrome_version": "120.0.1234.567",
        "last_error": None,
    }

    with patch("tv_cdp_health.health_check", side_effect=[unhealthy_initial, healthy_recovery]):
        with patch("tv_cdp_health._kill_chrome_process_on_port", return_value=True) as mock_kill:
            with patch("tv_cdp_health.run_tv_cdp_subprocess"):
                with patch("tv_cdp_health._wait_for_port_ready", return_value=True):
                    with patch("time.sleep"):
                        result = ensure_healthy(max_wait_seconds=30)

                        # Should call kill_chrome_process_on_port with port 9222
                        mock_kill.assert_called_with(9222)
                        assert result["recovered"] is True


# --- Test 3: Respawns TV CDP when unhealthy ---

def test_ensure_healthy_respawns_tv_cdp():
    """
    When unhealthy, ensure_healthy() should call run_tv_cdp_subprocess()
    to re-spawn the TV CDP engine.
    """
    unhealthy_initial = {
        "port_open": False,
        "chart_responsive": False,
        "chrome_version": "unknown",
        "last_error": "Port 9222 is not responding",
    }

    healthy_recovery = {
        "port_open": True,
        "chart_responsive": True,
        "chrome_version": "120.0.1234.567",
        "last_error": None,
    }

    with patch("tv_cdp_health.health_check", side_effect=[unhealthy_initial, healthy_recovery]):
        with patch("tv_cdp_health._kill_chrome_process_on_port", return_value=True):
            with patch("tv_cdp_health.run_tv_cdp_subprocess") as mock_spawn:
                with patch("tv_cdp_health._wait_for_port_ready", return_value=True):
                    with patch("time.sleep"):
                        result = ensure_healthy(max_wait_seconds=30)

                        # Should call run_tv_cdp_subprocess
                        mock_spawn.assert_called_once()
                        assert result["recovered"] is True


# --- Test 4: Waits for port ready before recovery validation ---

def test_ensure_healthy_waits_for_port_ready():
    """
    When unhealthy, ensure_healthy() should wait for port 9222 to become
    ready (using _wait_for_port_ready) before calling final health_check.
    """
    unhealthy_initial = {
        "port_open": False,
        "chart_responsive": False,
        "chrome_version": "unknown",
        "last_error": "Port 9222 is not responding",
    }

    healthy_recovery = {
        "port_open": True,
        "chart_responsive": True,
        "chrome_version": "120.0.1234.567",
        "last_error": None,
    }

    with patch("tv_cdp_health.health_check", side_effect=[unhealthy_initial, healthy_recovery]):
        with patch("tv_cdp_health._kill_chrome_process_on_port", return_value=True):
            with patch("tv_cdp_health.run_tv_cdp_subprocess"):
                with patch("tv_cdp_health._wait_for_port_ready", return_value=True) as mock_wait:
                    with patch("time.sleep"):
                        result = ensure_healthy(max_wait_seconds=30)

                        # Should call _wait_for_port_ready with correct port and timeout
                        mock_wait.assert_called_with(9222, max_wait_seconds=30)
                        assert result["recovered"] is True


# --- Test 5: Verifies recovery with second health_check call ---

def test_ensure_healthy_verifies_recovery():
    """
    Full recovery scenario: ensure_healthy() calls health_check() before
    and after recovery attempt. Should detect recovery success and return
    the final health state.
    """
    unhealthy_initial = {
        "port_open": False,
        "chart_responsive": False,
        "chrome_version": "unknown",
        "last_error": "Port 9222 is not responding",
    }

    healthy_recovery = {
        "port_open": True,
        "chart_responsive": True,
        "chrome_version": "120.0.1234.567",
        "last_error": None,
    }

    with patch("tv_cdp_health.health_check", side_effect=[unhealthy_initial, healthy_recovery]) as mock_health_check:
        with patch("tv_cdp_health._kill_chrome_process_on_port", return_value=True):
            with patch("tv_cdp_health.run_tv_cdp_subprocess"):
                with patch("tv_cdp_health._wait_for_port_ready", return_value=True):
                    with patch("time.sleep"):
                        result = ensure_healthy(max_wait_seconds=30)

                        # Should call health_check twice: before and after recovery
                        assert mock_health_check.call_count == 2

                        # Result should contain the recovered health state
                        assert result["recovered"] is True
                        assert result["new_health"] == healthy_recovery
                        assert "recovery" in result["reason"].lower()


# --- Test 6: Timeout on recovery failure ---

def test_ensure_healthy_timeout_on_recovery_failure():
    """
    When port 9222 does not become ready within max_wait_seconds,
    ensure_healthy() should raise an exception with timeout context.
    """
    unhealthy_initial = {
        "port_open": False,
        "chart_responsive": False,
        "chrome_version": "unknown",
        "last_error": "Port 9222 is not responding",
    }

    with patch("tv_cdp_health.health_check", return_value=unhealthy_initial):
        with patch("tv_cdp_health._kill_chrome_process_on_port", return_value=True):
            with patch("tv_cdp_health.run_tv_cdp_subprocess"):
                with patch("tv_cdp_health._wait_for_port_ready", return_value=False):
                    with patch("time.sleep"):
                        # Should raise exception on timeout
                        with pytest.raises(Exception) as exc_info:
                            ensure_healthy(max_wait_seconds=30)

                        # Exception message should mention timeout and port/time
                        error_msg = str(exc_info.value)
                        assert "9222" in error_msg or "port" in error_msg.lower()
                        assert "30" in error_msg or "timeout" in error_msg.lower()


# --- Additional Edge Case Tests ---

def test_ensure_healthy_recovery_health_check_still_fails():
    """
    If recovery port polling succeeds but final health_check still reports
    unhealthy, ensure_healthy() should raise exception.
    """
    unhealthy_initial = {
        "port_open": False,
        "chart_responsive": False,
        "chrome_version": "unknown",
        "last_error": "Port 9222 is not responding",
    }

    # Port open but chart still not responsive
    unhealthy_recovery = {
        "port_open": True,
        "chart_responsive": False,
        "chrome_version": "120.0.1234.567",
        "last_error": "Chart read failed",
    }

    with patch("tv_cdp_health.health_check", side_effect=[unhealthy_initial, unhealthy_recovery]):
        with patch("tv_cdp_health._kill_chrome_process_on_port", return_value=True):
            with patch("tv_cdp_health.run_tv_cdp_subprocess"):
                with patch("tv_cdp_health._wait_for_port_ready", return_value=True):
                    with patch("time.sleep"):
                        # Should raise exception since recovery health is still unhealthy
                        with pytest.raises(Exception) as exc_info:
                            ensure_healthy(max_wait_seconds=30)

                        error_msg = str(exc_info.value)
                        assert "failed" in error_msg.lower()


def test_ensure_healthy_spawn_fails():
    """
    If run_tv_cdp_subprocess() raises exception, ensure_healthy()
    should propagate it with context.
    """
    unhealthy_initial = {
        "port_open": False,
        "chart_responsive": False,
        "chrome_version": "unknown",
        "last_error": "Port 9222 is not responding",
    }

    with patch("tv_cdp_health.health_check", return_value=unhealthy_initial):
        with patch("tv_cdp_health._kill_chrome_process_on_port", return_value=True):
            with patch("tv_cdp_health.run_tv_cdp_subprocess", side_effect=Exception("tv_launch.py not found")):
                with patch("time.sleep"):
                    # Should raise exception from spawn failure
                    with pytest.raises(Exception) as exc_info:
                        ensure_healthy(max_wait_seconds=30)

                    error_msg = str(exc_info.value)
                    assert "spawn" in error_msg.lower() or "launch" in error_msg.lower()


def test_run_tv_cdp_subprocess_success():
    """
    run_tv_cdp_subprocess() should spawn tv_launch.py subprocess
    and return True on successful spawn.
    """
    with patch("subprocess.Popen") as mock_popen:
        result = run_tv_cdp_subprocess()

        # Should return True
        assert result is True

        # Should call Popen with tv_launch.py
        mock_popen.assert_called_once()
        call_args = mock_popen.call_args[0][0]
        assert "tv_launch.py" in str(call_args)


def test_run_tv_cdp_subprocess_file_not_found():
    """
    run_tv_cdp_subprocess() should raise FileNotFoundError if tv_launch.py
    cannot be located.
    """
    with patch("pathlib.Path.exists", return_value=False):
        # Should raise FileNotFoundError
        with pytest.raises(Exception) as exc_info:
            run_tv_cdp_subprocess()

        error_msg = str(exc_info.value)
        assert "tv_launch.py" in error_msg.lower() or "not found" in error_msg.lower()


def test_kill_chrome_process_on_port_macos():
    """
    On macOS, _kill_chrome_process_on_port() should use lsof to find
    and kill the Chrome process.
    """
    # Mock macOS platform
    with patch("platform.system", return_value="Darwin"):
        # Mock lsof output: "1234" (PID)
        mock_lsof_result = Mock()
        mock_lsof_result.stdout = "1234\n"
        mock_lsof_result.returncode = 0

        with patch("subprocess.run", return_value=mock_lsof_result) as mock_run:
            with patch("os.kill") as mock_kill:
                with patch("time.sleep"):
                    result = _kill_chrome_process_on_port(9222)

                    # Should call lsof
                    calls = [c for c in mock_run.call_args_list if "lsof" in str(c)]
                    assert len(calls) > 0

                    # Should call os.kill with PID 1234
                    mock_kill.assert_called_with(1234, 9)
                    assert result is True


def test_kill_chrome_process_on_port_windows():
    """
    On Windows, _kill_chrome_process_on_port() should use taskkill
    via netstat output parsing.
    """
    # Mock Windows platform
    with patch("platform.system", return_value="Windows"):
        # Mock netstat output
        netstat_output = (
            "Proto  Local Address          Foreign Address        State           PID\n"
            "TCP    0.0.0.0:9222           0.0.0.0:0              LISTENING       5678\n"
        )
        mock_netstat_result = Mock()
        mock_netstat_result.stdout = netstat_output
        mock_netstat_result.returncode = 0

        with patch("subprocess.run", return_value=mock_netstat_result) as mock_run:
            with patch("time.sleep"):
                result = _kill_chrome_process_on_port(9222)

                # Should call taskkill with PID 5678
                calls = [c for c in mock_run.call_args_list if "taskkill" in str(c)]
                assert len(calls) > 0

                assert result is True


def test_wait_for_port_ready_success():
    """
    _wait_for_port_ready() should return True when socket connection
    succeeds before timeout.
    """
    mock_socket = MagicMock()
    mock_socket.__enter__.return_value = Mock()
    mock_socket.__exit__.return_value = None

    with patch("socket.create_connection", return_value=mock_socket):
        result = _wait_for_port_ready(9222, max_wait_seconds=30)

        assert result is True


def test_wait_for_port_ready_timeout():
    """
    _wait_for_port_ready() should return False if port doesn't respond
    within max_wait_seconds.
    """
    # Deterministic fake clock: advances only when time.sleep() is called,
    # so the while-loop's `time.time() - start_time < max_wait_seconds`
    # check doesn't busy-spin against the real wall clock for 2s.
    fake_now = [0.0]

    def mock_time():
        return fake_now[0]

    def mock_sleep(duration):
        fake_now[0] += duration

    # Mock socket connection always failing
    with patch("socket.create_connection", side_effect=ConnectionRefusedError("Connection refused")):
        with patch("time.sleep", side_effect=mock_sleep):  # Speed up test by mocking sleep
            with patch("time.time", side_effect=mock_time):
                result = _wait_for_port_ready(9222, max_wait_seconds=2)

                assert result is False


def test_wait_for_port_ready_exponential_backoff():
    """
    _wait_for_port_ready() should use exponential backoff when polling.
    Backoff starts at 0.5s and increases up to 2s.
    """
    sleep_calls = []
    connection_attempts = [0]

    def mock_sleep(duration):
        sleep_calls.append(duration)

    def mock_create_connection(*args, **kwargs):
        connection_attempts[0] += 1
        # Succeed on 4th attempt (after 3 failures and 3 sleeps)
        if connection_attempts[0] >= 4:
            mock_socket = MagicMock()
            mock_socket.__enter__.return_value = Mock()
            mock_socket.__exit__.return_value = None
            return mock_socket
        # Fail on first 3 attempts
        raise ConnectionRefusedError("Connection refused")

    with patch("time.sleep", side_effect=mock_sleep):
        with patch("socket.create_connection", side_effect=mock_create_connection):
            result = _wait_for_port_ready(9222, max_wait_seconds=30)

            # Should have succeeded
            assert result is True

            # Should have called sleep multiple times with backoff
            assert len(sleep_calls) > 0
            # First sleep should be 0.5s
            if len(sleep_calls) > 0:
                assert sleep_calls[0] == 0.5
