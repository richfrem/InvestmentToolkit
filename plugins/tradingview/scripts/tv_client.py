#!/usr/bin/env python3
"""
tv_client.py - Core TradingView CLI client.

The Node.js CDP engine lives at PROJECT_ROOT/tradingview-cdp/.

Resolution order:
  1. TV_CDP_DIR environment variable (explicit override -- works in CI, Docker, post-install)
  2. Walk up from this file's real location looking for tradingview-cdp/cli.js
  3. Fail with clear, actionable setup instructions

This module is the SINGLE SOURCE OF TRUTH for Node.js path resolution.
All other TradingView Python scripts MUST import TV_NODE_DIR and TV_CLI from here.
"""

import json
import os
import sys
import subprocess
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


def _find_cdp_dir() -> Path:
    """
    Locate the tradingview-cdp Node.js package.
    """
    env_path = os.environ.get("TV_CDP_DIR")
    if env_path:
        p = Path(env_path).resolve()
        if (p / "cli.js").exists():
            return p
        raise FileNotFoundError(
            f"TV_CDP_DIR is set to '{env_path}' but 'cli.js' was not found there."
        )

    current = Path(__file__).resolve().parent
    for _ in range(10):
        candidate = current / "tradingview-cdp"
        if (candidate / "cli.js").exists():
            return candidate
        if current == current.parent:
            break
        current = current.parent

    raise FileNotFoundError(
        "\n"
        "+============================================================+\n"
        "|  TradingView CDP Engine Not Found                          |\n"
        "+============================================================+\n"
        "|                                                            |\n"
        "|  Expected at: <project-root>/tradingview-cdp/              |\n"
        "|                                                            |\n"
        "|  Setup:                                                    |\n"
        "|    cd <project-root>/tradingview-cdp                       |\n"
        "|    npm ci                                             |\n"
        "|                                                            |\n"
        "|  Or set the environment variable:                          |\n"
        "|    export TV_CDP_DIR=/path/to/tradingview-cdp              |\n"
        "|                                                            |\n"
        "|  See: plugins/tradingview/README.md for full setup guide   |\n"
        "+============================================================+\n"
    )

_CDP_MISSING_MSG = None
try:
    TV_NODE_DIR = _find_cdp_dir()
    TV_CLI = TV_NODE_DIR / "cli.js"
    TV_NODE_MODULES = TV_NODE_DIR / "node_modules"
    REPO_ROOT = TV_NODE_DIR.parent
except FileNotFoundError as e:
    TV_NODE_DIR = Path(".")
    TV_CLI = Path("./cli.js")
    TV_NODE_MODULES = Path("./node_modules")
    REPO_ROOT = Path(".")
    _CDP_MISSING_MSG = str(e)

TV_PORT = int(os.environ.get("TV_CDP_PORT", "9222"))

# --- Task 5A-8: resilience layer imports -----------------------------------
#
# tv_cdp_health.py (investment_screener/backend/py_services/) holds the
# generic, side-effect-free 5A-1..5A-7 building blocks (retry, circuit
# breaker, error logging, disk cache). tv_client.py lives three directories
# down at plugins/tradingview/scripts/, so the path back is computed the
# mirror image of tv_cdp_health.py's own lazy import of tv_client (see its
# _check_chart_responsive()). Wrapped in try/except so a missing/broken
# resilience dependency (e.g. pydantic unavailable) degrades tv_call() back
# to its pre-5A-8 raise-on-failure behavior rather than breaking import for
# all 19 real call sites.
_RESILIENCE_IMPORT_ERROR = None
try:
    _tv_health_dir = str(Path(__file__).resolve().parents[3] / "investment_screener/backend/py_services")
    if _tv_health_dir not in sys.path:
        sys.path.insert(0, _tv_health_dir)
    from tv_cdp_health import (  # type: ignore[import]
        retry_with_backoff,
        CircuitBreaker,
        log_tv_error,
        cache_get,
        cache_set,
        generate_cache_key,
        health_check,
    )
except Exception as e:  # pragma: no cover - defensive; deps should always be present
    _RESILIENCE_IMPORT_ERROR = str(e)

# Process-lifetime singleton. One breaker for all tv_call() commands: TV CDP
# outages are almost always all-or-nothing (Chrome/port down), so a single
# global breaker is the "simple" pattern CircuitBreaker itself documents,
# not a more sophisticated per-command variant. tv_call() below only reads
# this breaker's *state* (healthy/unhealthy/fallback) to decide whether to
# even attempt a live call — it deliberately never reads breaker.last_response
# as fallback data, since that's a single slot shared across every command
# and would return the wrong payload for anything but the most-recently-
# succeeded command. The per-command, disk-backed cache (cache_get/cache_set)
# is the actual fallback data source, and is also what survives across the
# process restarts typical of these short-lived TV CLI scripts.
_circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_attempts=10) if not _RESILIENCE_IMPORT_ERROR else None


def validate_cdp_installation() -> dict:
    """
    Validate that the CDP engine is properly installed and ready.
    Returns a status dict. Call this from health checks.
    """
    issues = []

    if _CDP_MISSING_MSG:
        issues.append(_CDP_MISSING_MSG)
        return {
            "cdp_engine_path": "Not Found",
            "cli_path": "Not Found",
            "installed": False,
            "issues": issues
        }

    if not TV_CLI.exists():
        issues.append(f"cli.js not found at {TV_CLI}")

    if not TV_NODE_MODULES.exists():
        issues.append(
            f"node_modules/ not found at {TV_NODE_MODULES}. "
            f"Run: cd {TV_NODE_DIR} && npm ci"
        )
    elif not (TV_NODE_MODULES / "chrome-remote-interface").exists():
        issues.append(
            f"chrome-remote-interface not installed. "
            f"Run: cd {TV_NODE_DIR} && npm ci"
        )

    return {
        "cdp_engine_path": str(TV_NODE_DIR),
        "cli_path": str(TV_CLI),
        "installed": len(issues) == 0,
        "issues": issues
    }

def is_tv_running() -> bool:
    """
    Return True only if TradingView Desktop is on port 9222.
    """
    try:
        req = urllib.request.urlopen(
            f"http://localhost:{TV_PORT}/json/list", timeout=1
        )
        targets = json.loads(req.read())
        return any(
            t.get("type") == "page" and "tradingview" in t.get("url", "").lower()
            for t in targets
        )
    except Exception:
        return False


def _tv_call_once(*args, timeout: int = 10):
    """
    Make exactly one attempt at the TradingView CLI call and return parsed JSON.

    This is the original (pre-5A-8) tv_call() body, extracted unchanged as
    the single-attempt seam that retry_with_backoff()/CircuitBreaker wrap.
    Raises FileNotFoundError/RuntimeError on failure — callers needing the
    resilient, never-raises contract should call tv_call() instead.
    """
    if _CDP_MISSING_MSG:
        raise FileNotFoundError(_CDP_MISSING_MSG)

    if not TV_CLI or not TV_CLI.exists():
        raise FileNotFoundError(
            f"TradingView CLI not found at {TV_CLI}. "
            f"Run: cd {TV_NODE_DIR} && npm ci"
        )

    cmd = ["node", str(TV_CLI)] + [str(a) for a in args]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(TV_NODE_DIR)
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"TradingView CLI error (exit {result.returncode}): {result.stderr.strip()}"
        )

    return json.loads(result.stdout)


def _make_cache_key(args) -> str:
    """Deterministic disk-cache key for a tv_call(*args) invocation."""
    command_name = str(args[0]) if args else "unknown"
    return generate_cache_key(command_name, {"args": [str(a) for a in args]})


def _is_structurally_valid(response) -> bool:
    """
    Minimal structural check used by tv_call(enable_validation=True).

    Scope boundary (see Task 5A-8 report): validate_tv_response() from
    5A-4 requires a pydantic BaseModel per call, but tv_call(*args) is a
    generic dispatcher — different commands ("chart symbol", "chart read",
    "pine inject", ...) return structurally different JSON shapes, so no
    single schema fits here. This check only asserts the response parsed
    to a non-empty dict; real schema validation remains available via
    validate_tv_response() for higher-level callers that know their
    expected shape.
    """
    return isinstance(response, dict) and len(response) > 0


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _error_dict(message: str, data=None, cached: bool = False) -> dict:
    """Build the tv_call() error-response contract."""
    return {"error": message, "data": data, "cached": cached, "timestamp": _now_iso()}


def _cached_fallback_or_error(command_name: str, args: tuple, cache_key: str,
                               message: str, enable_cache_fallback: bool) -> dict:
    """
    Final-failure path: try the disk last-known-good cache, else give up.

    Always logs the failure (non-blocking — log_tv_error never raises).
    """
    log_tv_error(command_name, {"args": [str(a) for a in args]}, RuntimeError(message))

    cached = cache_get(cache_key) if enable_cache_fallback else None
    if cached is not None:
        return _error_dict(message, data=cached, cached=True)
    return _error_dict(message, data=None, cached=False)


def _run_resilient_attempt(args: tuple, timeout: int, enable_retry: bool, max_attempts: int):
    """Run one logical tv_call attempt, applying retry_with_backoff if enabled. May raise."""
    def _once():
        return _tv_call_once(*args, timeout=timeout)

    if enable_retry:
        return retry_with_backoff(_once, max_attempts=max_attempts)
    return _once()


def _probe_and_maybe_reset_breaker(breaker) -> bool:
    """
    Half-open probe for a tripped circuit breaker (deferred 5A finding).

    CircuitBreaker.reset() previously had no production caller — once a
    breaker tripped to "fallback" in a long-lived process, it never
    self-healed even after TV CDP recovered, since tv_call() short-
    circuits fallback-state calls before ever reaching breaker.call()'s
    own success-counting path. This probes real current health via
    health_check() (cheap: a port check + one chart read) each time
    tv_call() is invoked while in fallback state, and resets the breaker
    on a healthy result so the caller's current attempt proceeds live
    instead of being served stale cached data forever.

    Args:
        breaker: The CircuitBreaker instance currently in "fallback" state.

    Returns:
        True if TV CDP is currently healthy and the breaker was reset
        (caller should proceed with a real attempt); False if still
        unhealthy (caller should keep serving cached/error fallback).
        Never raises — a failed probe itself just counts as unhealthy.
    """
    try:
        result = health_check(timeout=5)
        healthy = bool(result.get("port_open")) and bool(result.get("chart_responsive"))
    except Exception:
        healthy = False

    if healthy:
        breaker.reset()
    return healthy


def tv_call(
    *args,
    timeout: int = 10,
    enable_retry: bool = True,
    enable_circuit_breaker: bool = True,
    enable_validation: bool = True,
    enable_cache_fallback: bool = True,
    max_attempts: int = 3,
):
    """
    Resilient wrapper around the TradingView CLI (Task 5A-8).

    Layers, applied in order: retry (5A-3) -> circuit breaker (5A-6) ->
    structural validation (5A-4 scope boundary) -> disk cache fallback
    (5A-7), with every failure logged to tv_cdp_errors.jsonl (5A-5,
    non-blocking).

    Backward compatible: called positionally exactly like the pre-5A-8
    tv_call(*args, timeout=10) at all 19 real call sites. On a fresh,
    valid success, returns the raw parsed CLI response unchanged (no
    wrapping) — existing callers' `.get(...)` access patterns keep
    working untouched. Only the failure path changes: instead of raising
    (the old behavior), it returns
    {"error": str, "data": None | dict, "cached": bool, "timestamp": str}.
    This function never raises.

    Args:
        *args: Positional CLI arguments, e.g. tv_call("chart", "read").
        timeout: Per-attempt subprocess timeout in seconds.
        enable_retry: Retry transient failures with exponential backoff.
        enable_circuit_breaker: Route through the module-level circuit
            breaker to avoid hammering a down TV CDP once it has failed
            failure_threshold times in a row.
        enable_validation: Reject structurally malformed (non-dict/empty)
            successful responses (see _is_structurally_valid).
        enable_cache_fallback: Read/write the disk last-known-good cache
            (survives across process restarts, unlike the circuit
            breaker's in-memory state).
        max_attempts: Max attempts per retry_with_backoff() call.

    Returns:
        dict: raw CLI response on fresh success, or the error-dict
        contract on any failure/degraded path.
    """
    if _RESILIENCE_IMPORT_ERROR:
        # Resilience deps unavailable — fall back to pre-5A-8 behavior
        # (single attempt, may raise) rather than silently pretending to
        # offer guarantees (logging/caching) we can't actually provide.
        return _tv_call_once(*args, timeout=timeout)

    command_name = str(args[0]) if args else "unknown"
    cache_key = _make_cache_key(args)
    breaker = _circuit_breaker if enable_circuit_breaker else None

    if breaker is not None and breaker.state == "fallback":
        # Circuit already open: probe real current health before giving
        # up again (see _probe_and_maybe_reset_breaker) — if TV CDP has
        # actually recovered, reset the breaker and fall through to a
        # live attempt below instead of serving stale cached data forever.
        if not _probe_and_maybe_reset_breaker(breaker):
            # Still down. Deliberately do NOT use breaker.last_response
            # here — the breaker is a single global instance shared by
            # every command, so its last_response is one shared slot
            # holding whatever command most recently succeeded, not
            # necessarily *this* command's data. The per-command disk
            # cache (keyed by command+args) is the correct source of
            # last-known-good data across different commands.
            return _cached_fallback_or_error(
                command_name, args, cache_key,
                "Circuit breaker open; TV CDP calls are currently suspended",
                enable_cache_fallback,
            )

    try:
        if breaker is not None:
            result = breaker.call(_run_resilient_attempt, args, timeout, enable_retry, max_attempts)
        else:
            result = _run_resilient_attempt(args, timeout, enable_retry, max_attempts)
    except Exception as e:
        return _cached_fallback_or_error(command_name, args, cache_key, str(e), enable_cache_fallback)

    if enable_validation and not _is_structurally_valid(result):
        message = f"TV CDP response for '{command_name}' failed structural validation"
        return _cached_fallback_or_error(command_name, args, cache_key, message, enable_cache_fallback)

    if enable_cache_fallback:
        cache_set(cache_key, result)

    return result


def run_node_module_raw(js_code: str, timeout: int = 30) -> subprocess.CompletedProcess:
    """
    Execute inline ES module code with the CDP engine's node_modules in scope.
    """
    if _CDP_MISSING_MSG:
        raise FileNotFoundError(_CDP_MISSING_MSG)

    return subprocess.run(
        ["node", "--input-type=module"],
        input=js_code,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(TV_NODE_DIR)
    )

def run_node_module(js_code: str, timeout: int = 30) -> dict:
    """
    Execute inline ES module code and parse the returned JSON.
    """
    result = run_node_module_raw(js_code, timeout=timeout)
    if result.returncode != 0 and not result.stdout.strip():
        raise RuntimeError(f"Node.js error (exit {result.returncode}): {result.stderr.strip()[:500]}")
    try:
        return json.loads(result.stdout.strip())
    except json.JSONDecodeError:
        return {"raw": result.stdout.strip(), "stderr": result.stderr.strip()}

def tv_call_or_fallback(*args, fallback_fn, timeout: int = 10):
    """
    Try a single TV CLI attempt. If TradingView is unavailable or any
    error occurs, call fallback_fn() instead.

    Task 5A-8 note on the tv_call()/tv_call_or_fallback() overlap: as of
    5A-8, tv_call() itself never raises (it returns an error dict and
    degrades via retry/circuit-breaker/disk-cache internally), so this
    function deliberately calls the lower-level _tv_call_once() single
    attempt instead of tv_call() — if it called tv_call(), the `except
    Exception` below would never fire and a TV failure would silently
    return tv_call()'s error dict tagged "tradingview" instead of routing
    to fallback_fn(). This keeps the two mechanisms as separate, non-
    conflicting resilience strategies: tv_call() is the general-purpose,
    self-healing wrapper (retry + circuit breaker + disk cache, no caller
    fallback needed); tv_call_or_fallback() is for call sites that already
    have their own well-defined alternate data source (e.g. a yfinance
    fallback) and want a direct, single-attempt "try TV, else use mine"
    decision without tv_call()'s extra layers or disk-cache side effects.
    """
    if not is_tv_running():
        return fallback_fn(), "fallback"

    try:
        result = _tv_call_once(*args, timeout=timeout)
        return result, "tradingview"
    except Exception:
        return fallback_fn(), "fallback"
