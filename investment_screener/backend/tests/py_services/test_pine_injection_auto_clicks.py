"""
Task 5B-3: Script Injection

Tests for pine_script_manager.inject_pine_script(), which composes 5B-1's
registry (load_registry/save_registry) and 5B-2's validate_pine_script()
with tv_client.py's tv_call() primitive to inject a registered Pine
Script onto a TradingView chart.

tv_call is mocked at the pine_script_manager module's imported
reference — no test here ever shells out to the real TV CDP engine.
Registry lookups, file reads, and validation are all genuinely exercised
against real temp registries and real temp .pine file content; only the
final tv_call() boundary is mocked.
"""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

import pine_script_manager  # noqa: E402
from pine_script_manager import (  # noqa: E402
    inject_pine_script,
    load_registry,
    register_script,
)

VALID_PINE = (
    "//@version=6\n"
    'indicator("Test", overlay=true)\n'
    "plot(close)\n"
)

# Missing //@version=6 -- fails 5B-2's validate_pine_script().
INVALID_PINE = (
    'indicator("Test", overlay=true)\n'
    "plot(close)\n"
)


@pytest.fixture
def registry_path(tmp_path, monkeypatch):
    """Point PINE_REGISTRY_PATH at a temp file for the duration of a test.

    The parent directory doubles as the pinescript-indicators asset root
    that registry entries' `path` field is resolved relative to.
    """
    path = tmp_path / "registry.json"
    monkeypatch.setattr(pine_script_manager, "PINE_REGISTRY_PATH", path)
    return path


def _register_real_script(registry_path, name: str, filename: str, content: str) -> Path:
    """Write a real .pine file next to registry_path and register it."""
    script_path = registry_path.parent / filename
    script_path.write_text(content)
    register_script(name, filename, "Test script")
    return script_path


def _never_call(*args, **kwargs):
    """A tv_call stand-in that fails the test loudly if ever invoked."""
    raise AssertionError(f"tv_call must not be invoked, but was called with args={args}")


# --- Test 1: Registered, valid script injects successfully ---

def test_inject_pine_script_success_updates_registry(registry_path, monkeypatch):
    """A registered, valid script switches the chart, injects via
    tv_call, and stamps last_injected in the persisted registry."""
    _register_real_script(registry_path, "my-script", "my-script.pine", VALID_PINE)

    calls = []

    def fake_tv_call(*args, **kwargs):
        calls.append(args)
        return {"success": True}

    monkeypatch.setattr(pine_script_manager, "tv_call", fake_tv_call)

    result = inject_pine_script("my-script", "NVDA")

    assert result is True
    assert calls[0] == ("chart", "symbol", "NVDA")
    assert calls[1] == ("pine", "inject", "--content", VALID_PINE)

    registry = load_registry()
    assert registry.get_script("my-script").last_injected is not None


# --- Test 2: Unknown script name never reaches tv_call ---

def test_inject_pine_script_unknown_script_returns_false(registry_path, monkeypatch):
    """A script name not present in the registry returns False without
    ever invoking tv_call."""
    monkeypatch.setattr(pine_script_manager, "tv_call", _never_call)

    result = inject_pine_script("does-not-exist", "NVDA")

    assert result is False


# --- Test 3: Registered but file missing on disk never reaches tv_call ---

def test_inject_pine_script_missing_file_returns_false(registry_path, monkeypatch):
    """A registry entry whose .pine file doesn't exist on disk returns
    False without ever invoking tv_call."""
    register_script("ghost-script", "ghost.pine", "Never written to disk")

    monkeypatch.setattr(pine_script_manager, "tv_call", _never_call)

    result = inject_pine_script("ghost-script", "NVDA")

    assert result is False


# --- Test 4: Invalid script content never reaches tv_call ---

def test_inject_pine_script_invalid_script_returns_false(registry_path, monkeypatch):
    """A script that fails validate_pine_script (missing //@version=6)
    returns False without ever invoking tv_call, and last_injected stays
    unchanged."""
    _register_real_script(registry_path, "bad-script", "bad-script.pine", INVALID_PINE)

    monkeypatch.setattr(pine_script_manager, "tv_call", _never_call)

    result = inject_pine_script("bad-script", "NVDA")

    assert result is False
    registry = load_registry()
    assert registry.get_script("bad-script").last_injected is None


# --- Test 5: tv_call's 5A-8 error-dict failure shape (no "success" key) ---

def test_inject_pine_script_injection_failure_returns_false(registry_path, monkeypatch):
    """A valid script whose injection call returns tv_call()'s Task 5A-8
    error-dict shape ({"error": ..., "data": None, "cached": bool,
    "timestamp": ...}, no "success" key) is treated as a failure."""
    _register_real_script(registry_path, "my-script", "my-script.pine", VALID_PINE)

    def fake_tv_call(*args, **kwargs):
        if args[:2] == ("chart", "symbol"):
            return {"success": True}
        return {
            "error": "CDP timeout",
            "data": None,
            "cached": False,
            "timestamp": "2026-07-12T00:00:00+00:00",
        }

    monkeypatch.setattr(pine_script_manager, "tv_call", fake_tv_call)

    result = inject_pine_script("my-script", "NVDA")

    assert result is False
    registry = load_registry()
    assert registry.get_script("my-script").last_injected is None


# --- Test 6: The CLI's own {"success": False, ...} failure shape ---

def test_inject_pine_script_cli_style_failure_returns_false(registry_path, monkeypatch):
    """A valid script whose injection call returns the CLI's own
    {"success": False, "error": ...} shape (distinct from the 5A-8
    error-dict shape) is also treated as a failure. Pins the exact
    distinguishing logic from tv_pine_inject.py:89."""
    _register_real_script(registry_path, "my-script", "my-script.pine", VALID_PINE)

    def fake_tv_call(*args, **kwargs):
        if args[:2] == ("chart", "symbol"):
            return {"success": True}
        return {"success": False, "error": "Pine Editor not open"}

    monkeypatch.setattr(pine_script_manager, "tv_call", fake_tv_call)

    result = inject_pine_script("my-script", "NVDA")

    assert result is False
    registry = load_registry()
    assert registry.get_script("my-script").last_injected is None
