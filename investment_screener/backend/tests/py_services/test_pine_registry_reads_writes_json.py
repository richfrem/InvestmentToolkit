"""
Task 5B-1: Registry Schema & Storage

Tests for pine_script_manager.py: load_registry(), save_registry(),
register_script(), and the PineScriptEntry / PineScriptRegistry pydantic
models. Covers missing-file initialization, round-tripping existing
JSON, atomic writes, and add/update semantics for register_script().

IMPORTANT: All tests monkeypatch the module-level PINE_REGISTRY_PATH
constant to a pytest tmp_path location. None of these tests may write to
the real
plugins/tradingview/assets/pinescript-indicators/registry.json path.
"""

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

import pine_script_manager  # noqa: E402
from pine_script_manager import (  # noqa: E402
    PineScriptEntry,
    PineScriptRegistry,
    load_registry,
    save_registry,
    register_script,
)


@pytest.fixture
def registry_path(tmp_path, monkeypatch):
    """Point PINE_REGISTRY_PATH at a temp file for the duration of a test."""
    path = tmp_path / "registry.json"
    monkeypatch.setattr(pine_script_manager, "PINE_REGISTRY_PATH", path)
    return path


# --- Test 1: Missing file returns empty registry ---

def test_load_registry_creates_empty_if_missing(registry_path):
    """Calling load_registry() against a nonexistent path returns an
    empty PineScriptRegistry rather than raising."""
    assert not registry_path.exists()

    registry = load_registry()

    assert isinstance(registry, PineScriptRegistry)
    assert registry.scripts == {}


# --- Test 2: Existing JSON parses correctly ---

def test_load_registry_parses_existing_json(registry_path):
    """A registry.json with sample entries round-trips through load_registry()."""
    sample = {
        "scripts": {
            "ai-ta-levels": {
                "path": "ai-ta-levels.pine",
                "version": "1.0.0",
                "description": "Multi-EMA 21/50/200 + volume bias",
                "last_injected": "2026-07-01T12:00:00+00:00",
                "hash": "abc123",
            }
        }
    }
    registry_path.write_text(json.dumps(sample, indent=2))

    registry = load_registry()

    assert "ai-ta-levels" in registry.scripts
    entry = registry.get_script("ai-ta-levels")
    assert entry.path == "ai-ta-levels.pine"
    assert entry.version == "1.0.0"
    assert entry.description == "Multi-EMA 21/50/200 + volume bias"
    assert entry.last_injected == "2026-07-01T12:00:00+00:00"
    assert entry.hash == "abc123"


# --- Test 3: save_registry writes JSON to disk ---

def test_save_registry_writes_json(registry_path):
    """After save_registry(), the file exists and contains the added entry."""
    registry = PineScriptRegistry()
    registry.add_script(
        "ai-ta-levels",
        PineScriptEntry(
            path="ai-ta-levels.pine",
            version="1.0.0",
            description="Multi-EMA 21/50/200 + volume bias",
            hash="abc123",
        ),
    )

    save_registry(registry)

    assert registry_path.exists()
    on_disk = json.loads(registry_path.read_text())
    assert on_disk["scripts"]["ai-ta-levels"]["path"] == "ai-ta-levels.pine"
    assert on_disk["scripts"]["ai-ta-levels"]["hash"] == "abc123"
    # Pretty-printed with 2-space indent per Global Constraints.
    assert registry_path.read_text().startswith("{\n  ")


# --- Test 4: register_script adds a new entry ---

def test_register_script_adds_new_entry(registry_path):
    """register_script() persists a brand-new entry into the registry file."""
    entry = register_script(
        "ai-ta-levels",
        "ai-ta-levels.pine",
        "Multi-EMA 21/50/200 + volume bias",
    )

    assert isinstance(entry, PineScriptEntry)
    assert entry.version == "1.0.0"

    registry = load_registry()
    assert "ai-ta-levels" in registry.scripts
    assert registry.get_script("ai-ta-levels").path == "ai-ta-levels.pine"


# --- Test 5: register_script updates an existing entry's version ---

def test_register_script_updates_existing_version(registry_path):
    """Registering the same script name twice with different versions
    updates the stored version rather than creating a duplicate."""
    register_script("ai-ta-levels", "ai-ta-levels.pine", "First description", version="1.0.0")
    register_script("ai-ta-levels", "ai-ta-levels.pine", "Second description", version="2.0.0")

    registry = load_registry()

    assert len(registry.scripts) == 1
    entry = registry.get_script("ai-ta-levels")
    assert entry.version == "2.0.0"
    assert entry.description == "Second description"


# --- Test 6: Atomic write leaves no partial file on mid-write failure ---

def test_registry_file_atomic_write(registry_path, monkeypatch):
    """If the write fails partway through, no corrupted/partial registry
    file is left at PINE_REGISTRY_PATH — either the old content is
    preserved, or nothing exists yet."""
    # Seed an existing valid registry so we can prove it survives untouched.
    original = PineScriptRegistry()
    original.add_script(
        "existing-script",
        PineScriptEntry(
            path="existing.pine",
            version="1.0.0",
            description="Pre-existing entry",
            hash="orig000",
        ),
    )
    save_registry(original)
    original_bytes = registry_path.read_bytes()

    def _boom(*args, **kwargs):
        raise OSError("simulated disk failure mid-write")

    monkeypatch.setattr(pine_script_manager.os, "replace", _boom)

    new_registry = PineScriptRegistry()
    new_registry.add_script(
        "new-script",
        PineScriptEntry(
            path="new.pine",
            version="1.0.0",
            description="Should not persist",
            hash="new000",
        ),
    )

    with pytest.raises(OSError):
        save_registry(new_registry)

    # The real registry file must be untouched — same bytes as before —
    # and no stray .tmp file should remain.
    assert registry_path.read_bytes() == original_bytes
    tmp_candidates = list(registry_path.parent.glob("*.tmp"))
    assert tmp_candidates == []


# --- Corrupted JSON raises a clear error, not a vague parse error ---

def test_load_registry_corrupted_json_raises_clear_error(registry_path):
    """A malformed registry.json raises an error whose message names the
    file and explains it's corrupted, rather than a bare JSONDecodeError."""
    registry_path.write_text("{ not valid json ]")

    with pytest.raises(ValueError) as exc_info:
        load_registry()

    message = str(exc_info.value)
    assert "registry.json" in message or str(registry_path) in message
    assert "corrupt" in message.lower() or "invalid" in message.lower()
