"""
Task 5B-2: Script Validation (Lint)

Tests for pine_script_manager.validate_pine_script(), a thin wrapper
around the existing plugins/tradingview/scripts/pine_linter.py's
PineLinter class. Exercises the REAL PineLinter against real, temp-file
.pine content (no mocking of PineLinter itself) — validates actual
linter behavior wrapped in a structured {"valid", "errors", "warnings"}
dict.

Covers: a clean valid script, a missing-version error, an unsafe
request.security() error, a warnings-only script (validity unaffected),
a missing-file path, and the exact shape/typing of the returned dict.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from pine_script_manager import validate_pine_script  # noqa: E402


def _write_pine(tmp_path, name: str, content: str) -> str:
    """Write `content` to tmp_path/name and return the path as a str."""
    path = tmp_path / name
    path.write_text(content)
    return str(path)


# --- Test 1: A clean, valid v6 script passes with no errors ---

def test_validate_pine_script_valid_file_returns_true(tmp_path):
    """A script with //@version=6 and exactly one indicator() declaration,
    with no risky constructs, passes with valid=True and errors=[]."""
    content = (
        "//@version=6\n"
        'indicator("Test", overlay=true)\n'
        "plot(close)\n"
    )
    file_path = _write_pine(tmp_path, "valid.pine", content)

    result = validate_pine_script(file_path)

    assert result["valid"] is True
    assert result["errors"] == []


# --- Test 2: Missing //@version=6 produces a specific error ---

def test_validate_pine_script_missing_version_returns_error(tmp_path):
    """A script with no //@version=6 line fails validation with a
    specific missing-version error message."""
    content = (
        'indicator("Test", overlay=true)\n'
        "plot(close)\n"
    )
    file_path = _write_pine(tmp_path, "no_version.pine", content)

    result = validate_pine_script(file_path)

    assert result["valid"] is False
    assert any("version" in e.lower() for e in result["errors"])


# --- Test 3: request.security() without lookahead= is an error ---

def test_validate_pine_script_unsafe_request_security_returns_error(tmp_path):
    """A script calling request.security() without an explicit lookahead=
    argument fails validation with that specific error message present."""
    content = (
        "//@version=6\n"
        'indicator("Test")\n'
        'value = request.security(syminfo.tickerid, "D", close)\n'
    )
    file_path = _write_pine(tmp_path, "unsafe_security.pine", content)

    result = validate_pine_script(file_path)

    assert result["valid"] is False
    assert any("request.security" in e for e in result["errors"])
    assert any("lookahead" in e for e in result["errors"])


# --- Test 4: Warnings don't affect validity ---

def test_validate_pine_script_warnings_dont_affect_validity(tmp_path):
    """A script that triggers a warning (drawing object created without
    var/varip) but has zero errors is still valid=True, with a non-empty
    warnings list."""
    content = (
        "//@version=6\n"
        'indicator("Test")\n'
        'label.new(bar_index, high, "hi")\n'
    )
    file_path = _write_pine(tmp_path, "warns_only.pine", content)

    result = validate_pine_script(file_path)

    assert result["valid"] is True
    assert result["errors"] == []
    assert len(result["warnings"]) > 0


# --- Test 5: Missing file returns valid=False with a meaningful error ---

def test_validate_pine_script_missing_file_returns_false(tmp_path):
    """Calling validate_pine_script() on a path that doesn't exist
    returns valid=False with a non-empty, meaningful errors list — not
    silently empty, even though PineLinter itself doesn't populate
    .errors for this specific case."""
    missing_path = str(tmp_path / "does_not_exist.pine")

    result = validate_pine_script(missing_path)

    assert result["valid"] is False
    assert len(result["errors"]) > 0
    assert any(
        "not found" in e.lower() or "does_not_exist" in e for e in result["errors"]
    )


# --- Test 6: Return shape is exactly valid/errors/warnings, correctly typed ---

def test_validate_pine_script_returns_structured_dict(tmp_path):
    """The returned dict has exactly the three keys valid/errors/warnings,
    with correct types: bool, list[str], list[str]."""
    content = (
        "//@version=6\n"
        'indicator("Test", overlay=true)\n'
        "plot(close)\n"
    )
    file_path = _write_pine(tmp_path, "shape_check.pine", content)

    result = validate_pine_script(file_path)

    assert set(result.keys()) == {"valid", "errors", "warnings"}
    assert isinstance(result["valid"], bool)
    assert isinstance(result["errors"], list)
    assert isinstance(result["warnings"], list)
    assert all(isinstance(e, str) for e in result["errors"])
    assert all(isinstance(w, str) for w in result["warnings"])
