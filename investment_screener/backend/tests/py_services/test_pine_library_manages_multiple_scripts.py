"""
Task 5B-6: Script Library Management

Tests for pine_script_manager's `category` field extension to
PineScriptEntry/register_script(), and the new filesystem version-archive
functions archive_script_version() / list_available_versions().

This archive mechanism is deliberately separate from 5B-4/5B-5's
git-history-based versioning (list_script_versions() /
rollback_pine_script()) — it snapshots a script's current .pine content
under a versions/<script_name>/<version>.pine path, independent of git,
so history is browsable even for files never individually committed.

All registry and archive operations run against a monkeypatched
PINE_REGISTRY_PATH pointed at tmp_path — never the real repo registry or
its real versions/ directory.
"""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

import pine_script_manager  # noqa: E402
from pine_script_manager import (  # noqa: E402
    archive_script_version,
    list_available_versions,
    load_registry,
    register_script,
)

VALID_PINE = (
    "//@version=6\n"
    'indicator("Test", overlay=true)\n'
    "plot(close)\n"
)


@pytest.fixture
def registry_path(tmp_path, monkeypatch):
    """Point PINE_REGISTRY_PATH at a temp file for the duration of a test.

    The parent directory doubles as the pinescript-indicators asset root
    that registry entries' `path` field resolves relative to, and that
    _versions_dir() resolves the versions/ archive relative to.
    """
    path = tmp_path / "registry.json"
    monkeypatch.setattr(pine_script_manager, "PINE_REGISTRY_PATH", path)
    return path


def _register_real_script(
    registry_path, name: str, filename: str, content: str, version: str = "1.0.0"
) -> Path:
    """Write a real .pine file next to registry_path and register it."""
    script_path = registry_path.parent / filename
    script_path.write_text(content)
    register_script(name, filename, "Test script", version=version)
    return script_path


# --- Test 1: category persists and round-trips ---

def test_register_script_with_category_persists_and_round_trips(registry_path):
    """register_script(..., category="level") persists and reloads with
    that category intact."""
    register_script(
        "ai-ta-levels",
        "ai-ta-levels.pine",
        "Multi-EMA levels",
        version="2.0.0",
        category="level",
    )

    registry = load_registry()
    entry = registry.get_script("ai-ta-levels")
    assert entry is not None
    assert entry.category == "level"


# --- Test 2: category defaults to None (backward compat) ---

def test_register_script_without_category_defaults_to_none(registry_path):
    """Existing call sites (5B-1 through 5B-5) that never pass `category`
    must keep persisting an entry with category=None."""
    register_script("my-script", "my-script.pine", "Test script")

    registry = load_registry()
    entry = registry.get_script("my-script")
    assert entry is not None
    assert entry.category is None


# --- Test 3: archive_script_version copies current file content ---

def test_archive_script_version_copies_current_file_to_versions_dir(registry_path):
    """archive_script_version() snapshots the registered script's current
    file content into versions/<name>/<version>.pine, matching exactly."""
    _register_real_script(
        registry_path, "my-script", "my-script.pine", VALID_PINE, version="1.0.0"
    )

    archived_path = archive_script_version("my-script")

    assert archived_path is not None
    assert archived_path.exists()
    assert archived_path.read_text() == VALID_PINE
    assert archived_path.name == "1.0.0.pine"


# --- Test 4: unregistered script returns None, no directory created ---

def test_archive_script_version_unregistered_script_returns_none(registry_path):
    """An unregistered script name returns None and creates no archive
    directory at all."""
    result = archive_script_version("does-not-exist")

    assert result is None
    assert not (registry_path.parent / "versions" / "does-not-exist").exists()


# --- Test 5: registered but file missing on disk returns None ---

def test_archive_script_version_missing_file_returns_none(registry_path):
    """A registered entry whose .pine file was never written to disk
    returns None instead of raising FileNotFoundError."""
    register_script("ghost-script", "ghost-script.pine", "Never written to disk")

    result = archive_script_version("ghost-script")

    assert result is None


# --- Test 6: write failure (OSError) returns None, never raises ---

def test_archive_script_version_write_failure_returns_none(registry_path, monkeypatch):
    """A filesystem failure during the versions/ directory create or the
    file write degrades to None rather than propagating."""
    _register_real_script(
        registry_path, "my-script", "my-script.pine", VALID_PINE, version="1.0.0"
    )

    def _raise_oserror(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(Path, "mkdir", _raise_oserror)

    result = archive_script_version("my-script")

    assert result is None


# --- Test 7: list_available_versions returns sorted version strings ---

def test_list_available_versions_returns_sorted_version_strings(registry_path):
    """Archiving a script at two successive versions produces a sorted
    list of both version strings."""
    script_path = _register_real_script(
        registry_path, "my-script", "my-script.pine", VALID_PINE, version="1.0.0"
    )
    archive_script_version("my-script")

    # Bump the registered version, reusing the same file path, and
    # archive again.
    script_path.write_text(VALID_PINE + "// v2\n")
    register_script("my-script", "my-script.pine", "Test script", version="2.0.0")
    archive_script_version("my-script")

    assert list_available_versions("my-script") == ["1.0.0", "2.0.0"]


# --- Test 8: unknown script with no archive directory returns [] ---

def test_list_available_versions_unknown_script_returns_empty_list(registry_path):
    """A script name with no versions/ archive directory returns an
    empty list rather than raising."""
    assert list_available_versions("never-archived") == []
