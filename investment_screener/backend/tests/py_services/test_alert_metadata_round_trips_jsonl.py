"""
Task 5C-4: Alert Metadata Schema

Tests for alert_manager.AlertMetadata / save_alert_metadata() /
load_alert_metadata() — pure schema definition plus local JSONL
persistence for alert history, matching the established
evolution_events.jsonl/predictions.jsonl real-tracked-ledger pattern and
pine_script_manager.py's save_registry()/load_registry() write-raises/
read-degrades asymmetry.

This task is independent of 5C-1/5C-2/5C-3's TV CDP composition — none of
these tests call create_price_alert(), dedup_alerts(), or
sync_alert_state().

IMPORTANT: All tests monkeypatch the module-level ALERTS_STATE_PATH
constant to a pytest tmp_path location. None of these tests may write to
the real investment_screener/backend/data/alerts_state.jsonl path.
"""

import builtins
import json
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

import alert_manager  # noqa: E402
from alert_manager import (  # noqa: E402
    AlertMetadata,
    load_alert_metadata,
    save_alert_metadata,
)


@pytest.fixture
def alerts_state_path(tmp_path, monkeypatch):
    """Point ALERTS_STATE_PATH at a temp file for the duration of a test."""
    path = tmp_path / "alerts_state.jsonl"
    monkeypatch.setattr(alert_manager, "ALERTS_STATE_PATH", path)
    return path


def _make_record(**overrides) -> AlertMetadata:
    fields = {
        "id": "alert-123",
        "ticker": "NVDA",
        "price": 150.0,
        "direction": "above",
        "type": "price",
        "linked_claim_id": None,
        "created_at": "2026-07-13T12:00:00+00:00",
        "fired_at": None,
        "state": "pending",
    }
    fields.update(overrides)
    return AlertMetadata(**fields)


# --- Test 1: Validates required fields ---

def test_alert_metadata_validates_required_fields():
    """A valid AlertMetadata holds all fields with the correct values/types."""
    record = _make_record()

    assert record.id == "alert-123"
    assert record.ticker == "NVDA"
    assert record.price == 150.0
    assert record.direction == "above"
    assert record.type == "price"
    assert record.linked_claim_id is None
    assert record.created_at == "2026-07-13T12:00:00+00:00"
    assert record.fired_at is None
    assert record.state == "pending"


# --- Test 2: Rejects invalid direction ---

def test_alert_metadata_rejects_invalid_direction():
    """direction="sideways" is not in the Literal["above", "below"] vocabulary."""
    with pytest.raises(ValidationError):
        _make_record(direction="sideways")


# --- Test 3: Rejects invalid state ---

def test_alert_metadata_rejects_invalid_state():
    """state="unknown" is not in the Literal["pending", "fired", "expired"] vocabulary."""
    with pytest.raises(ValidationError):
        _make_record(state="unknown")


# --- Test 4: Rejects invalid type ---

def test_alert_metadata_rejects_invalid_type():
    """type="unsupported" is not in the Literal["price", "ta_signal"] vocabulary."""
    with pytest.raises(ValidationError):
        _make_record(type="unsupported")


# --- Test 5: Appends without overwriting ---

def test_save_alert_metadata_appends_without_overwriting(alerts_state_path):
    """Two distinct records saved sequentially both survive as two JSONL lines."""
    first = _make_record(id="alert-1", ticker="NVDA")
    second = _make_record(id="alert-2", ticker="TSLA")

    save_alert_metadata(first)
    save_alert_metadata(second)

    lines = [
        line for line in alerts_state_path.read_text().splitlines() if line.strip()
    ]
    assert len(lines) == 2
    assert json.loads(lines[0])["id"] == "alert-1"
    assert json.loads(lines[1])["id"] == "alert-2"


# --- Test 6: Load round-trips exact data ---

def test_load_alert_metadata_round_trips_exact_data(alerts_state_path):
    """A saved record loads back equal, field-by-field, to the original."""
    original = _make_record(
        id="alert-42",
        ticker="AAPL",
        price=200.5,
        direction="below",
        type="ta_signal",
        linked_claim_id="claim-7",
        created_at="2026-07-13T09:30:00+00:00",
        fired_at="2026-07-13T10:00:00+00:00",
        state="fired",
    )

    save_alert_metadata(original)
    loaded = load_alert_metadata()

    assert len(loaded) == 1
    assert loaded[0] == original


# --- Test 7: Missing file returns empty list ---

def test_load_alert_metadata_returns_empty_list_when_file_missing(alerts_state_path):
    """No file exists at ALERTS_STATE_PATH; load returns [] with no exception."""
    assert not alerts_state_path.exists()

    result = load_alert_metadata()

    assert result == []


# --- Test 8: Skips malformed lines and continues ---

def test_load_alert_metadata_skips_malformed_line_and_continues(alerts_state_path):
    """Invalid JSON and Pydantic-invalid lines are skipped; valid lines survive."""
    alerts_state_path.parent.mkdir(parents=True, exist_ok=True)

    valid_record = _make_record(id="alert-good", ticker="MSFT")
    invalid_json_line = "{not valid json,,,"
    invalid_pydantic_line = json.dumps(
        {
            "id": "alert-bad",
            "ticker": "GOOG",
            "price": 100.0,
            "direction": "sideways",  # invalid Literal value
            "type": "price",
            "linked_claim_id": None,
            "created_at": "2026-07-13T12:00:00+00:00",
            "fired_at": None,
            "state": "pending",
        }
    )

    with open(alerts_state_path, "w") as f:
        f.write(invalid_json_line + "\n")
        f.write(invalid_pydantic_line + "\n")
        f.write(valid_record.model_dump_json() + "\n")

    result = load_alert_metadata()

    assert len(result) == 1
    assert result[0].id == "alert-good"


# --- Test 9: Creates parent directory ---

def test_save_alert_metadata_creates_parent_directory(tmp_path, monkeypatch):
    """A nonexistent parent directory is created and the write succeeds."""
    nested_path = tmp_path / "nested" / "does_not_exist_yet" / "alerts_state.jsonl"
    monkeypatch.setattr(alert_manager, "ALERTS_STATE_PATH", nested_path)
    assert not nested_path.parent.exists()

    save_alert_metadata(_make_record())

    assert nested_path.exists()
    assert len(nested_path.read_text().splitlines()) == 1


# --- Test 10: Raises OSError on write failure ---

def test_save_alert_metadata_raises_oserror_on_write_failure(alerts_state_path, monkeypatch):
    """A failing underlying open() propagates as OSError, not swallowed."""

    real_open = builtins.open

    def _failing_open(path, *args, **kwargs):
        if Path(path) == alerts_state_path:
            raise OSError("disk full")
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", _failing_open)

    with pytest.raises(OSError):
        save_alert_metadata(_make_record())
