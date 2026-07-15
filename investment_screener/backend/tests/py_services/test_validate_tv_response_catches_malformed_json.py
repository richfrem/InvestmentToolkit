"""
Task 5A-4: Response Validation

Tests for tv_cdp_health.py validate_tv_response() function.
Verifies pydantic-schema validation of TV CDP responses: valid dicts return
True, missing/extra/mistyped fields and malformed JSON strings return False
(never raise), with WARNING logs for validation failures and ERROR logs for
parse failures.
"""

import sys
from pathlib import Path

import pytest
from pydantic import BaseModel

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from tv_cdp_health import validate_tv_response


class QuoteSchema(BaseModel):
    """Minimal schema used across tests: a symbol and an open price."""
    symbol: str
    open: int


# --- Test 1: Valid dict matching schema returns True ---

def test_validate_response_valid_schema_returns_true():
    """
    A dict that satisfies all required fields of the schema should
    validate successfully and return True.
    """
    response = {"symbol": "AAPL", "open": 150}

    result = validate_tv_response(response, QuoteSchema)

    assert result is True


# --- Test 2: Missing required field returns False + warning log ---

def test_validate_response_missing_required_field_returns_false(caplog):
    """
    A dict missing a required field ("open") should fail validation,
    return False, and log a WARNING (not raise).
    """
    response = {"symbol": "AAPL"}

    with caplog.at_level("WARNING"):
        result = validate_tv_response(response, QuoteSchema)

    assert result is False
    assert any(record.levelname == "WARNING" for record in caplog.records)


# --- Test 3: Extra fields allowed by default (pydantic v2 default behavior) ---

def test_validate_response_extra_fields_allowed():
    """
    Pydantic v2's default BaseModel config silently ignores extra fields
    rather than rejecting them. A dict with unexpected extra keys should
    still validate successfully and return True.
    """
    response = {"symbol": "AAPL", "open": 150, "unexpected_new_field": "value"}

    result = validate_tv_response(response, QuoteSchema)

    assert result is True


# --- Test 4: Malformed JSON string returns False + error log ---

def test_validate_response_malformed_json_string_returns_false(caplog):
    """
    A response passed as a string that isn't valid JSON should fail to
    parse, return False, and log an ERROR (not raise).
    """
    response = "{not valid json,,,"

    with caplog.at_level("ERROR"):
        result = validate_tv_response(response, QuoteSchema)

    assert result is False
    assert any(record.levelname == "ERROR" for record in caplog.records)


# --- Test 5: Type mismatch on a field returns False ---

def test_validate_response_type_mismatch_returns_false():
    """
    A dict where a field has the wrong type ("open" as a non-numeric
    string) should fail pydantic validation and return False.
    """
    response = {"symbol": "AAPL", "open": "not-a-number"}

    result = validate_tv_response(response, QuoteSchema)

    assert result is False


# --- Test 6: Warning log contains the specific missing key names ---

def test_validate_response_logs_missing_keys(caplog):
    """
    The WARNING log emitted on validation failure should explicitly name
    the missing required key(s), per the brief's "keep error messages
    specific" requirement (e.g. mentions "open", not just "validation
    failed").
    """
    response = {"symbol": "AAPL"}

    with caplog.at_level("WARNING"):
        validate_tv_response(response, QuoteSchema)

    warning_messages = [
        record.message for record in caplog.records if record.levelname == "WARNING"
    ]
    assert any("open" in msg for msg in warning_messages)


# --- Additional: valid JSON string input (not just dict) is accepted ---

def test_validate_response_valid_json_string_returns_true():
    """
    A response passed as a valid JSON string should be parsed and
    validated the same as an equivalent dict.
    """
    response = '{"symbol": "AAPL", "open": 150}'

    result = validate_tv_response(response, QuoteSchema)

    assert result is True


# --- Additional: function never raises, even on wildly wrong input types ---

def test_validate_response_never_raises_on_unexpected_input():
    """
    Defensive guarantee from the brief: this function must never raise.
    Passing None (not a dict or str) should be handled gracefully and
    return False rather than propagating a TypeError/AttributeError.
    """
    result = validate_tv_response(None, QuoteSchema)  # type: ignore[arg-type]

    assert result is False
