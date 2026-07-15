"""
Task 5B-4: Version Control

Tests for pine_script_manager.py: list_script_versions(), which shells
out to real `git log`/`git show` against registry.json's own git history
to reconstruct a script's version timeline.

IMPORTANT: All tests use a REAL temporary git repository (via
subprocess.run(["git", "init", ...]) inside tmp_path) with
PINE_REGISTRY_PATH monkeypatched into that repo. subprocess/git are never
mocked here — this function's whole job is correctly parsing real git
output, so the only meaningful test is against a real repo. None of these
tests may touch the real
plugins/tradingview/assets/pinescript-indicators/registry.json path or
the worktree's own git history.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

import pine_script_manager  # noqa: E402
from pine_script_manager import list_script_versions  # noqa: E402


# Fixed author/committer date env so commit timestamps are deterministic
# and strictly increasing across sequential commits in a test.
_BASE_ENV_DATE = "2026-01-0{day}T12:00:00-05:00"


def _git_env(day: int) -> dict:
    """Build a subprocess env with deterministic author/committer dates."""
    import os

    env = os.environ.copy()
    date = _BASE_ENV_DATE.format(day=day)
    env["GIT_AUTHOR_DATE"] = date
    env["GIT_COMMITTER_DATE"] = date
    env["GIT_AUTHOR_NAME"] = "Test User"
    env["GIT_AUTHOR_EMAIL"] = "test@example.com"
    env["GIT_COMMITTER_NAME"] = "Test User"
    env["GIT_COMMITTER_EMAIL"] = "test@example.com"
    return env


def _run_git(args: list, cwd: Path, day: int = 1) -> None:
    """Run a git command in cwd, raising on failure (test setup helper)."""
    subprocess.run(
        ["git", *args],
        cwd=cwd,
        env=_git_env(day),
        capture_output=True,
        text=True,
        check=True,
    )


def _init_repo(repo_dir: Path) -> None:
    """git init a fresh repo with a deterministic default branch name."""
    repo_dir.mkdir(parents=True, exist_ok=True)
    _run_git(["init", "-b", "main"], cwd=repo_dir)
    _run_git(["config", "user.name", "Test User"], cwd=repo_dir)
    _run_git(["config", "user.email", "test@example.com"], cwd=repo_dir)


def _commit_registry(repo_dir: Path, registry_path: Path, content: dict, day: int) -> None:
    """Write `content` to registry_path and commit it with a fixed date."""
    registry_path.write_text(json.dumps(content, indent=2))
    _run_git(["add", registry_path.name], cwd=repo_dir, day=day)
    _run_git(["commit", "-m", f"registry update day {day}"], cwd=repo_dir, day=day)


@pytest.fixture
def git_registry(tmp_path, monkeypatch):
    """A real git repo with PINE_REGISTRY_PATH pointed at registry.json inside it."""
    repo_dir = tmp_path / "repo"
    _init_repo(repo_dir)
    registry_path = repo_dir / "registry.json"
    monkeypatch.setattr(pine_script_manager, "PINE_REGISTRY_PATH", registry_path)
    return repo_dir, registry_path


# --- Test 1: newest-first history with distinct version/hash per commit ---

def test_list_script_versions_returns_history_newest_first(git_registry):
    repo_dir, registry_path = git_registry

    _commit_registry(
        repo_dir,
        registry_path,
        {"scripts": {"ai-ta-levels": {
            "path": "ai-ta-levels.pine", "version": "1.0.0",
            "description": "d", "last_injected": None, "hash": "hash-v1",
        }}},
        day=1,
    )
    _commit_registry(
        repo_dir,
        registry_path,
        {"scripts": {"ai-ta-levels": {
            "path": "ai-ta-levels.pine", "version": "1.1.0",
            "description": "d", "last_injected": None, "hash": "hash-v2",
        }}},
        day=2,
    )
    _commit_registry(
        repo_dir,
        registry_path,
        {"scripts": {"ai-ta-levels": {
            "path": "ai-ta-levels.pine", "version": "2.0.0",
            "description": "d", "last_injected": None, "hash": "hash-v3",
        }}},
        day=3,
    )

    history = list_script_versions("ai-ta-levels")

    assert len(history) == 3
    assert [h["version"] for h in history] == ["2.0.0", "1.1.0", "1.0.0"]
    assert [h["hash"] for h in history] == ["hash-v3", "hash-v2", "hash-v1"]
    for entry in history:
        assert len(entry["commit"]) == 7
        assert "timestamp" in entry


# --- Test 2: consecutive identical version/hash pairs dedupe to one entry ---

def test_list_script_versions_dedupes_unchanged_entries(git_registry):
    repo_dir, registry_path = git_registry

    _commit_registry(
        repo_dir,
        registry_path,
        {"scripts": {"ai-ta-levels": {
            "path": "ai-ta-levels.pine", "version": "1.0.0",
            "description": "d", "last_injected": None, "hash": "hash-v1",
        }}},
        day=1,
    )
    # Second commit only changes last_injected — version/hash unchanged.
    _commit_registry(
        repo_dir,
        registry_path,
        {"scripts": {"ai-ta-levels": {
            "path": "ai-ta-levels.pine", "version": "1.0.0",
            "description": "d", "last_injected": "2026-01-02T00:00:00+00:00",
            "hash": "hash-v1",
        }}},
        day=2,
    )

    history = list_script_versions("ai-ta-levels")

    assert len(history) == 1
    assert history[0]["version"] == "1.0.0"
    assert history[0]["hash"] == "hash-v1"


# --- Test 3: script_name never existed in any historical revision ---

def test_list_script_versions_unknown_script_returns_empty(git_registry):
    repo_dir, registry_path = git_registry

    _commit_registry(
        repo_dir,
        registry_path,
        {"scripts": {"some-other-script": {
            "path": "other.pine", "version": "1.0.0",
            "description": "d", "last_injected": None, "hash": "hash-x",
        }}},
        day=1,
    )

    history = list_script_versions("ai-ta-levels")

    assert history == []


# --- Test 4: registry.json exists on disk but was never committed ---

def test_list_script_versions_no_git_history_returns_empty(git_registry):
    repo_dir, registry_path = git_registry

    # Commit an unrelated file so the repo has *some* history, but never
    # commit registry.json itself.
    other_file = repo_dir / "unrelated.txt"
    other_file.write_text("hello")
    _run_git(["add", "unrelated.txt"], cwd=repo_dir, day=1)
    _run_git(["commit", "-m", "unrelated commit"], cwd=repo_dir, day=1)

    registry_path.write_text(json.dumps({"scripts": {"ai-ta-levels": {
        "path": "ai-ta-levels.pine", "version": "1.0.0",
        "description": "d", "last_injected": None, "hash": "hash-v1",
    }}}))

    history = list_script_versions("ai-ta-levels")

    assert history == []


# --- Test 5: PINE_REGISTRY_PATH points outside any git repository ---

def test_list_script_versions_not_a_git_repo_returns_empty(tmp_path, monkeypatch):
    no_repo_dir = tmp_path / "no-repo"
    no_repo_dir.mkdir()
    registry_path = no_repo_dir / "registry.json"
    registry_path.write_text(json.dumps({"scripts": {"ai-ta-levels": {
        "path": "ai-ta-levels.pine", "version": "1.0.0",
        "description": "d", "last_injected": None, "hash": "hash-v1",
    }}}))
    monkeypatch.setattr(pine_script_manager, "PINE_REGISTRY_PATH", registry_path)

    history = list_script_versions("ai-ta-levels")

    assert history == []


# --- Test 6: returned timestamp parses as valid ISO 8601 (matches %aI) ---

def test_list_script_versions_timestamp_is_iso8601(git_registry):
    repo_dir, registry_path = git_registry

    _commit_registry(
        repo_dir,
        registry_path,
        {"scripts": {"ai-ta-levels": {
            "path": "ai-ta-levels.pine", "version": "1.0.0",
            "description": "d", "last_injected": None, "hash": "hash-v1",
        }}},
        day=1,
    )

    history = list_script_versions("ai-ta-levels")

    assert len(history) == 1
    from datetime import datetime

    parsed = datetime.fromisoformat(history[0]["timestamp"])
    assert parsed.year == 2026
    assert parsed.month == 1
    assert parsed.day == 1


# --- Bonus: a corrupted historical revision is skipped, not fatal ---

def test_list_script_versions_skips_corrupted_historical_revision(git_registry):
    repo_dir, registry_path = git_registry

    # Commit 1: valid registry with the script.
    _commit_registry(
        repo_dir,
        registry_path,
        {"scripts": {"ai-ta-levels": {
            "path": "ai-ta-levels.pine", "version": "1.0.0",
            "description": "d", "last_injected": None, "hash": "hash-v1",
        }}},
        day=1,
    )
    # Commit 2: corrupt JSON committed directly (not via json.dumps).
    registry_path.write_text("{ not valid json ]")
    _run_git(["add", "registry.json"], cwd=repo_dir, day=2)
    _run_git(["commit", "-m", "corrupt registry"], cwd=repo_dir, day=2)
    # Commit 3: valid again, different version.
    _commit_registry(
        repo_dir,
        registry_path,
        {"scripts": {"ai-ta-levels": {
            "path": "ai-ta-levels.pine", "version": "2.0.0",
            "description": "d", "last_injected": None, "hash": "hash-v2",
        }}},
        day=3,
    )

    history = list_script_versions("ai-ta-levels")

    # The corrupted middle commit is skipped; the two valid ones remain,
    # newest first.
    assert [h["version"] for h in history] == ["2.0.0", "1.0.0"]
