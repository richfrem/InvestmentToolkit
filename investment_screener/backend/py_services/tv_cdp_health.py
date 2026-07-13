"""
TV CDP Health Check Module

Provides health_check() function to verify TradingView CDP engine status.
Returns structured health status including port connectivity, chart responsiveness,
and Chrome version information.

Also provides ensure_healthy() to detect stale Chrome sessions and restart TV CDP
if needed, with platform-specific process management (lsof on macOS, taskkill on Windows).

Also provides retry_with_backoff() — a generic, side-effect-free retry helper with
exponential delay, intended to be wrapped around any callable (TV CDP or otherwise)
by later resilience tasks (e.g. tv_call wrapping, order execution gates).

Key Input Dependencies:
    - TradingView CDP engine running on localhost:9222
    - tv_client.py for CDP communication
    - tv_launch.py for CDP subprocess spawning
    - Subprocess-based process killing: lsof/netstat output parsing +
      os.kill on macOS/Linux, taskkill on Windows (no psutil dependency)
"""

import json
import socket
import subprocess
import time
import platform
import os
import sys
import traceback
import urllib.request
import urllib.error
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import TypedDict, Optional, Dict, Any, Callable, Union

from pydantic import BaseModel, ValidationError

# Configure logging for health checks
logger = logging.getLogger(__name__)

# Append-only audit trail for tv_call() failures (Task 5A-5). Tests
# monkeypatch this module-level constant to a temp path — never write to
# the real path from a test.
TV_CDP_ERRORS_PATH = Path(__file__).resolve().parents[1] / "data" / "tv_cdp_errors.jsonl"


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


def run_tv_cdp_subprocess() -> bool:
    """
    Spawn TV CDP subprocess via tv_launch.py.

    Launches TradingView Desktop with --remote-debugging-port=9222
    to re-establish the Chrome debugging protocol connection.

    Returns:
        True if launch subprocess was initiated successfully, False otherwise

    Raises:
        Exception: If subprocess execution fails
    """
    try:
        tv_launch_path = Path(__file__).resolve().parents[3] / "plugins/tradingview/scripts/tv_launch.py"

        if not tv_launch_path.exists():
            raise FileNotFoundError(f"tv_launch.py not found at {tv_launch_path}")

        logger.info(f"Spawning TV CDP subprocess via {tv_launch_path}")

        # Launch as detached subprocess (don't wait for it)
        if platform.system() == "Windows":
            # Windows: use CREATE_NEW_PROCESS_GROUP
            subprocess.Popen(
                [sys.executable, str(tv_launch_path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if hasattr(subprocess, 'CREATE_NEW_PROCESS_GROUP') else 0,
            )
        else:
            # Unix: use preexec_fn to create new process group
            subprocess.Popen(
                [sys.executable, str(tv_launch_path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                preexec_fn=os.setsid if hasattr(os, 'setsid') else None,
            )

        logger.info("TV CDP subprocess initiated")
        return True
    except Exception as e:
        error_msg = f"Failed to spawn TV CDP subprocess: {str(e)}"
        logger.error(error_msg)
        raise Exception(error_msg)


def _kill_chrome_process_on_port(port: int = 9222) -> bool:
    """
    Kill Chrome process holding the given port.

    Uses platform-specific tools:
      - macOS/Linux: lsof
      - Windows: taskkill via netstat

    Args:
        port: Port number to kill (default: 9222)

    Returns:
        True if process was killed or port was free, False on error
    """
    try:
        is_windows = platform.system() == "Windows"

        if not is_windows:
            # macOS/Linux: use lsof
            try:
                result = subprocess.run(
                    ["lsof", "-ti", f":{port}"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                pids = result.stdout.strip().split()
                for pid in pids:
                    if pid:
                        try:
                            pid_int = int(pid)
                            logger.info(f"Killing process PID {pid_int} on port {port}")
                            os.kill(pid_int, 9)  # SIGKILL
                            time.sleep(0.5)
                        except (ValueError, ProcessLookupError, PermissionError) as e:
                            logger.warning(f"Failed to kill PID {pid}: {str(e)}")
                            continue
                return True
            except FileNotFoundError:
                # lsof not available, fallback to netstat
                logger.warning("lsof not found, trying netstat fallback")
                result = subprocess.run(
                    ["netstat", "-tlnp"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                for line in result.stdout.splitlines():
                    if f":{port}" in line:
                        # Try to extract PID from netstat output
                        parts = line.split()
                        if len(parts) > 0 and "/" in parts[-1]:
                            pid_str = parts[-1].split("/")[0]
                            try:
                                pid_int = int(pid_str)
                                logger.info(f"Killing process PID {pid_int} on port {port} (via netstat)")
                                os.kill(pid_int, 9)
                                time.sleep(0.5)
                            except (ValueError, ProcessLookupError, PermissionError) as e:
                                logger.warning(f"Failed to kill PID {pid_str}: {str(e)}")
                return True
        else:
            # Windows: use netstat and taskkill
            result = subprocess.run(
                ["netstat", "-ano"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            for line in result.stdout.splitlines():
                if f":{port}" in line and "LISTENING" in line:
                    parts = line.split()
                    if len(parts) > 0:
                        pid = parts[-1]
                        try:
                            logger.info(f"Killing process PID {pid} on port {port} (via taskkill)")
                            subprocess.run(
                                ["taskkill", "/F", "/PID", pid],
                                capture_output=True,
                                timeout=5,
                            )
                            time.sleep(0.5)
                        except Exception as e:
                            logger.warning(f"Failed to kill PID {pid}: {str(e)}")
            return True
    except Exception as e:
        logger.error(f"Error killing Chrome process on port {port}: {str(e)}")
        return False


def _wait_for_port_ready(port: int = 9222, max_wait_seconds: int = 30) -> bool:
    """
    Poll port until it's reachable or timeout expires.

    Uses exponential backoff: 0.5s → 1s → 2s with a max_wait timeout.

    Args:
        port: Port number to poll
        max_wait_seconds: Maximum wait time in seconds

    Returns:
        True if port becomes reachable, False on timeout
    """
    start_time = time.time()
    wait_time = 0.5

    while time.time() - start_time < max_wait_seconds:
        try:
            with socket.create_connection(("localhost", port), timeout=1):
                logger.info(f"Port {port} is now reachable")
                return True
        except (socket.timeout, ConnectionRefusedError, OSError):
            pass

        time.sleep(wait_time)
        wait_time = min(wait_time * 2, 2)  # Exponential backoff, max 2s

    logger.warning(f"Port {port} did not become reachable within {max_wait_seconds}s")
    return False


def ensure_healthy(max_wait_seconds: int = 30) -> Dict:
    """
    Detect stale Chrome session and restart TV CDP if needed.

    Workflow:
      1. Call health_check() to assess current state
      2. If healthy: return early (no-op)
      3. If unhealthy:
         - Kill Chrome process on port 9222
         - Call run_tv_cdp_subprocess() to re-spawn TV CDP
         - Poll port 9222 for readiness (with timeout)
         - Call health_check() again to verify recovery
         - On recovery failure: raise exception with context

    Args:
        max_wait_seconds: Maximum wait time for port/health recovery (default: 30)

    Returns:
        Dict with keys:
            - recovered: bool indicating if recovery was successful
            - reason: str with recovery reason/explanation
            - new_health: HealthCheckResult dict from final health_check()

    Raises:
        Exception: If recovery fails after retries
    """
    logger.info("Running ensure_healthy() check...")

    # Step 1: Check initial health
    initial_health = health_check(timeout=5)
    is_healthy = initial_health.get("port_open", False) and initial_health.get("chart_responsive", False)

    if is_healthy:
        logger.info("Chrome session is healthy, no recovery needed")
        return {
            "recovered": False,
            "reason": "Chrome session is already healthy",
            "new_health": initial_health,
        }

    logger.warning(f"Chrome session is unhealthy: {initial_health}")

    # Step 2: Kill Chrome process on port 9222
    logger.info("Killing stale Chrome process on port 9222...")
    kill_result = _kill_chrome_process_on_port(9222)
    if not kill_result:
        logger.error("Failed to kill Chrome process")

    time.sleep(1)  # Grace period after kill

    # Step 3: Re-spawn TV CDP
    logger.info("Spawning new TV CDP subprocess...")
    try:
        run_tv_cdp_subprocess()
    except Exception as e:
        error_msg = f"Failed to spawn TV CDP: {str(e)}"
        logger.error(error_msg)
        raise Exception(error_msg)

    # Step 4: Wait for port to be ready
    logger.info(f"Waiting up to {max_wait_seconds}s for port 9222 to be ready...")
    port_ready = _wait_for_port_ready(9222, max_wait_seconds=max_wait_seconds)

    if not port_ready:
        error_msg = f"Port 9222 did not become ready within {max_wait_seconds}s"
        logger.error(error_msg)
        raise Exception(error_msg)

    time.sleep(2)  # Additional grace period for TV to fully initialize

    # Step 5: Verify recovery via health_check
    logger.info("Verifying recovery with health_check...")
    recovery_health = health_check(timeout=5)
    recovery_successful = recovery_health.get("port_open", False) and recovery_health.get("chart_responsive", False)

    if not recovery_successful:
        error_msg = f"Chrome recovery failed — health check still reports unhealthy: {recovery_health}"
        logger.error(error_msg)
        raise Exception(error_msg)

    logger.info("Chrome session successfully recovered")
    return {
        "recovered": True,
        "reason": "Chrome session recovery successful: killed stale process and re-spawned TV CDP",
        "new_health": recovery_health,
    }


def retry_with_backoff(
    fn: Callable,
    max_attempts: int = 3,
    backoff_factor: float = 2.0,
    initial_delay_seconds: float = 1.0,
) -> Any:
    """
    Retry a function with exponential backoff.

    Calls fn() with no arguments. On exception, logs the error, sleeps for
    an exponentially increasing delay, and retries. Returns the result on
    the first successful call. Raises the last exception after max_attempts
    failures.

    This is a generic, side-effect-free helper: it doesn't know anything
    about TV CDP or any specific caller. Any callable that takes no
    arguments and returns/raises can be wrapped with it.

    Args:
        fn: Zero-argument callable to invoke. May return any type.
        max_attempts: Maximum number of attempts before giving up (default: 3).
        backoff_factor: Multiplier for exponential delay growth (default: 2.0).
        initial_delay_seconds: Base delay in seconds before the multiplier
            is applied (default: 1.0).

    Returns:
        The result of fn() from its first successful call. Type matches
        whatever fn() returns.

    Raises:
        ValueError: If max_attempts is less than 1.
        Exception: Re-raises the last exception from fn() if all
            max_attempts calls fail.
    """
    if max_attempts < 1:
        raise ValueError(f"max_attempts must be >= 1, got {max_attempts}")

    last_exception: Optional[BaseException] = None

    for attempt_number in range(max_attempts):
        try:
            return fn()
        except Exception as e:
            last_exception = e
            logger.warning(f"[Retry] Attempt {attempt_number + 1}/{max_attempts} failed: {str(e)}")

            is_last_attempt = attempt_number == max_attempts - 1
            if is_last_attempt:
                break

            delay = initial_delay_seconds * (backoff_factor ** attempt_number)
            logger.info(f"[Retry] Attempt {attempt_number + 1}/{max_attempts}: sleeping {delay}s before retry")
            time.sleep(delay)

    raise last_exception


def _parse_response_payload(response: Union[dict, str]) -> Optional[dict]:
    """
    Normalize a TV CDP response into a dict, parsing JSON strings as needed.

    Args:
        response: The TV CDP response to normalize — either an already
            parsed dict, or a raw JSON string.

    Returns:
        The response normalized to a dict-like value. None if response
        was a string that failed to parse as JSON, or was neither a dict
        nor a string. Errors are logged at error level, never raised.
    """
    if isinstance(response, str):
        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse TV CDP response as JSON: {str(e)}")
            return None
    elif isinstance(response, dict):
        return response
    else:
        logger.error(
            f"TV CDP response has unsupported type {type(response).__name__}; "
            "expected dict or JSON string"
        )
        return None


def _log_validation_errors(e: ValidationError, expected_schema: type[BaseModel]) -> None:
    """
    Log a pydantic ValidationError as missing-key and other-field warnings.

    Args:
        e: The ValidationError raised while instantiating expected_schema.
        expected_schema: The pydantic BaseModel subclass validation was
            attempted against (used for log message context only).

    Returns:
        None. Always logs at warning level for any errors found; never raises.
    """
    missing_keys = [
        ".".join(str(part) for part in err["loc"])
        for err in e.errors()
        if err["type"] == "missing"
    ]
    other_errors = [
        f"{'.'.join(str(part) for part in err['loc'])}: {err['msg']}"
        for err in e.errors()
        if err["type"] != "missing"
    ]

    if missing_keys:
        logger.warning(
            f"TV CDP response failed schema validation against "
            f"{expected_schema.__name__}: missing keys: {missing_keys}"
        )
    if other_errors:
        logger.warning(
            f"TV CDP response failed schema validation against "
            f"{expected_schema.__name__}: {other_errors}"
        )


def validate_tv_response(
    response: Union[dict, str],
    expected_schema: type[BaseModel],
) -> bool:
    """
    Validate a TV CDP response against a pydantic schema.

    Accepts either a dict or a JSON string, attempts to instantiate
    expected_schema with the parsed data, and reports the outcome as a
    bool. This is a purely defensive, in-memory validation layer: it
    never raises, regardless of input shape. Extra fields present in the
    response but not declared on expected_schema are allowed (pydantic
    v2's default BaseModel config ignores them silently) since TV CDP may
    return fields we don't validate for yet.

    Args:
        response: The TV CDP response to validate — either an already
            parsed dict, or a raw JSON string.
        expected_schema: A pydantic BaseModel subclass (the class itself,
            not an instance) describing the expected shape of response.

    Returns:
        True if response was successfully parsed and validated against
        expected_schema. False on any parse error, validation error, or
        unexpected input type — full details are logged, never raised.
    """
    try:
        data = _parse_response_payload(response)
        if data is None:
            return False

        try:
            expected_schema(**data)
            return True
        except ValidationError as e:
            _log_validation_errors(e, expected_schema)
            return False
        except TypeError as e:
            # expected_schema(**data) requires data to be a mapping; guard
            # against non-dict JSON payloads (e.g. a bare list or number).
            logger.error(
                f"TV CDP response could not be validated against "
                f"{expected_schema.__name__}: {str(e)}"
            )
            return False
    except Exception as e:
        # Final defensive catch-all: this function must never raise.
        logger.error(f"Unexpected error validating TV CDP response: {str(e)}")
        return False


def _build_tv_error_record(
    function: str,
    args: dict,
    error: Exception,
    attempt_number: int,
) -> Dict[str, Any]:
    """
    Build a single tv_call() failure record for the JSONL audit trail.

    Args:
        function: Name of the tv_call function/command that failed.
        args: Arguments passed to the failed call (serialized as-is).
        error: The exception raised by the failed call.
        attempt_number: Which retry attempt this failure occurred on.

    Returns:
        Dict matching the schema: timestamp, function, args, error,
        traceback, attempt_number. `traceback` uses traceback.format_exc(),
        which captures the currently-handled exception (if called from
        within an except block) or "NoneType: None" otherwise.
    """
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "function": function,
        "args": args,
        "error": str(error),
        "traceback": traceback.format_exc(),
        "attempt_number": attempt_number,
    }


def _append_error_jsonl(record: Dict[str, Any], path: Path) -> None:
    """
    Append one JSON record as a line to path, creating parent dirs as needed.

    Atomic single open/write/close. `default=str` guards against
    non-JSON-serializable values that may end up in `args`.

    Args:
        record: The record dict to serialize and append.
        path: JSONL file path to append to.

    Raises:
        OSError: If directory creation or file write fails. Callers
            (log_tv_error) are responsible for catching this.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(record, default=str) + "\n")


def log_tv_error(
    function: str,
    args: dict,
    error: Exception,
    attempt_number: int = 0
) -> None:
    """
    Append error to data/tv_cdp_errors.jsonl.
    Never raises; logs to application logger on failure.

    Args:
        function: Name of the tv_call function/command that failed.
        args: Arguments passed to the failed call.
        error: The exception raised by the failed call.
        attempt_number: Which retry attempt this failure occurred on
            (default: 0).

    Returns:
        None. This is a best-effort audit log: any failure while building
        or writing the record is caught and logged (INFO on success,
        ERROR on failure), never raised.
    """
    try:
        record = _build_tv_error_record(function, args, error, attempt_number)
        _append_error_jsonl(record, TV_CDP_ERRORS_PATH)
        logger.info(
            f"Logged TV CDP error for {function} (attempt {attempt_number}): {record['error']}"
        )
    except Exception as log_error:
        logger.error(f"Failed to log TV CDP error for {function}: {str(log_error)}")


class CircuitBreaker:
    """
    Stateful circuit breaker for TV CDP calls.
    Protects against cascading failures by returning cached data.

    States (per Global Constraints in the task brief):
        healthy   — 0 consecutive failures; fn() is called normally.
        unhealthy — 1-2 consecutive failures; fn() is still called normally
            (informational state only; call() does not branch on it).
        fallback  — failure_count reached failure_threshold; call() never
            invokes fn() again and returns last_response instead. The only
            way out of fallback is an explicit reset() (manual, or later
            called by health-check monitoring per 5A-8) — there is no
            automatic self-healing probe back to healthy through call().

    This is deliberately the simple circuit-breaker pattern the brief
    asks for, not the more sophisticated half-open/auto-probe variant.
    """

    def __init__(self, failure_threshold: int = 3, recovery_attempts: int = 10):
        self.failure_threshold = failure_threshold
        self.recovery_attempts = recovery_attempts
        self.failure_count = 0
        self.success_count = 0
        self.state = "healthy"  # healthy, unhealthy, fallback
        self.last_response = None

    def call(self, fn: Callable, *args, **kwargs) -> Any:
        """
        Call fn; track state; return result or cached data on fallback.

        While state is "fallback", fn() is never invoked — last_response
        is returned directly (read-only; no side effects on the cache).
        Otherwise fn(*args, **kwargs) is called: on success the result is
        cached and success_count increments (failure_count only resets
        once success_count reaches recovery_attempts — see
        _record_success); on failure the original exception is
        re-raised to the caller after failure bookkeeping (matches this
        file's existing retry_with_backoff behavior of surfacing the
        real error rather than swallowing it).

        Args:
            fn: Callable to invoke when not in fallback state.
            *args: Positional args forwarded to fn.
            **kwargs: Keyword args forwarded to fn.

        Returns:
            fn's result on success, or the cached last_response while in
            fallback state.

        Raises:
            Exception: Re-raises whatever fn(*args, **kwargs) raises.
        """
        if self.state == "fallback":
            return self.last_response

        try:
            result = fn(*args, **kwargs)
        except Exception as e:
            self._record_failure(e)
            raise
        else:
            self._record_success(result)
            return result

    def reset(self) -> None:
        """
        Reset to healthy state.

        Manual intervention hook (per brief Notes: "eventually will be
        called by health-check monitoring"). Unconditionally clears both
        counters and restores state to "healthy"; logs the transition if
        state was not already healthy.
        """
        previous_state = self.state
        self.state = "healthy"
        self.failure_count = 0
        self.success_count = 0
        if previous_state != "healthy":
            logger.info(f"Circuit breaker: manual reset to healthy (was {previous_state})")

    def _record_success(self, result: Any) -> None:
        """
        Update counters/cache after a successful fn() call.

        Increments success_count and caches result as last_response.
        failure_count is deliberately left untouched by an individual
        success — per the resolved brief ambiguity (Scope §4 / Key
        Design Decisions govern over Scope §2), recovery only happens
        once success_count reaches recovery_attempts (default 10
        accumulated successes). At that point failure_count is reset
        to 0, state transition logic is re-run since failure_count
        changed, and success_count wraps back to 0 to start the next
        recovery cycle.

        Args:
            result: The value returned by fn(), cached for fallback use.
        """
        self.success_count += 1
        self.last_response = result
        if self.success_count >= self.recovery_attempts:
            self.failure_count = 0
            self.success_count = 0
            self._update_state()

    def _record_failure(self, error: Exception) -> None:
        """
        Update counters after a failed fn() call.

        Args:
            error: The exception raised by fn(), logged for context.
        """
        self.failure_count += 1
        logger.warning(
            f"Circuit breaker: call failed (failure {self.failure_count}/{self.failure_threshold}): {str(error)}"
        )
        self._update_state()

    def _update_state(self) -> None:
        """
        Recompute state from failure_count and log any transition.

        healthy: failure_count == 0. unhealthy: 0 < failure_count <
        failure_threshold. fallback: failure_count >= failure_threshold.
        """
        previous_state = self.state
        if self.failure_count >= self.failure_threshold:
            self.state = "fallback"
        elif self.failure_count > 0:
            self.state = "unhealthy"
        else:
            self.state = "healthy"

        if self.state != previous_state:
            logger.info(f"Circuit breaker: switching to {self.state} (was {previous_state})")
