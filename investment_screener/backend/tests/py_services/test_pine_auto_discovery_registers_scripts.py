"""
Task 5B-7: Auto-Discovery

Tests for pine_script_manager.py's discover_and_register_scripts() and
_first_commit_hash(), which scan
plugins/tradingview/assets/pinescript-indicators/ (top-level only, via
Path.glob("*.pine")) for .pine files not yet in the registry, and
auto-register each new one with register_script() (5B-1), deriving its
version from the git commit hash that first added the file (or
"untracked" if it has no git history / isn't inside a repo at all).

IMPORTANT: All tests use a REAL temporary git repository (via
subprocess.run(["git", "init", ...]) inside tmp_path) with
PINE_REGISTRY_PATH monkeypatched into that repo's directory structure —
same pattern as test_pine_version_history_from_git.py and
test_pine_rollback_on_error.py. subprocess/git are never mocked here.
None of these tests may touch the real
plugins/tradingview/assets/pinescript-indicators/registry.json path or
the worktree's own git history.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

import pine_script_manager  # noqa: E402
from pine_script_manager import (  # noqa: E402
    discover_and_register_scripts,
    load_registry,
    register_script,
)

SAMPLE_PINE = (
    "//@version=6\n"
    'indicator("Sample", overlay=true)\n'
    "plot(close)\n"
)


def _git_env(day: int = 1) -> dict:
    """Build a subprocess env with deterministic author/committer dates."""
    env = os.environ.copy()
    date = f"2026-01-0{day}T12:00:00-05:00"
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


def _commit_file(repo_dir: Path, relative_path: str, day: int = 1) -> None:
    """git add + commit an already-written file, relative to repo_dir."""
    _run_git(["add", relative_path], cwd=repo_dir, day=day)
    _run_git(["commit", "-m", f"add {relative_path}"], cwd=repo_dir, day=day)


def _real_first_commit_hash(repo_dir: Path, relative_path: str) -> str:
    """Independently compute the expected short hash via raw git log,
    so assertions never hardcode a commit hash string."""
    result = subprocess.run(
        ["git", "log", "--follow", "--diff-filter=A", "--format=%H", "--", relative_path],
        cwd=repo_dir,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip().splitlines()[-1][:7]


@pytest.fixture
def git_registry(tmp_path, monkeypatch):
    """A real git repo with PINE_REGISTRY_PATH pointed at registry.json
    inside it — its parent directory stands in for
    plugins/tradingview/assets/pinescript-indicators/."""
    repo_dir = tmp_path / "repo"
    _init_repo(repo_dir)
    registry_path = repo_dir / "registry.json"
    monkeypatch.setattr(pine_script_manager, "PINE_REGISTRY_PATH", registry_path)
    return repo_dir, registry_path


# --- Test 1: a new top-level .pine file gets discovered and registered ---

def test_discover_and_register_scripts_registers_new_top_level_file(git_registry):
    repo_dir, _ = git_registry
    pine_file = repo_dir / "new-script.pine"
    pine_file.write_text(SAMPLE_PINE)
    _commit_file(repo_dir, "new-script.pine", day=1)

    result = discover_and_register_scripts()

    assert result == ["new-script"]
    registry = load_registry()
    entry = registry.get_script("new-script")
    assert entry is not None
    expected_hash = _real_first_commit_hash(repo_dir, "new-script.pine")
    assert entry.version == expected_hash
    assert len(entry.version) == 7


# --- Test 2: an already-registered script is skipped, version untouched ---

def test_discover_and_register_scripts_skips_already_registered(git_registry):
    repo_dir, _ = git_registry
    pine_file = repo_dir / "existing.pine"
    pine_file.write_text(SAMPLE_PINE)
    _commit_file(repo_dir, "existing.pine", day=1)
    register_script("existing", "existing.pine", "Manually registered", version="1.0.0")

    result = discover_and_register_scripts()

    assert "existing" not in result
    registry = load_registry()
    entry = registry.get_script("existing")
    assert entry.version == "1.0.0"


# --- Test 3: community-reference/ subdirectory is never scanned ---

def test_discover_and_register_scripts_excludes_community_reference_subdirectory(git_registry):
    repo_dir, _ = git_registry
    subdir = repo_dir / "community-reference"
    subdir.mkdir()
    pine_file = subdir / "some-third-party.pine"
    pine_file.write_text(SAMPLE_PINE)
    _commit_file(repo_dir, "community-reference/some-third-party.pine", day=1)

    result = discover_and_register_scripts()

    assert result == []
    registry = load_registry()
    assert registry.get_script("some-third-party") is None


# --- Test 4: versions/<script>/ archive subdirectory is never scanned ---

def test_discover_and_register_scripts_excludes_versions_subdirectory(git_registry):
    repo_dir, _ = git_registry
    subdir = repo_dir / "versions" / "some-script"
    subdir.mkdir(parents=True)
    pine_file = subdir / "1.0.0.pine"
    pine_file.write_text(SAMPLE_PINE)
    _commit_file(repo_dir, "versions/some-script/1.0.0.pine", day=1)

    result = discover_and_register_scripts()

    assert result == []
    registry = load_registry()
    assert registry.get_script("1.0.0") is None


# --- Test 5: an untracked (never committed) file still gets discovered ---

def test_discover_and_register_scripts_untracked_file_gets_untracked_version(git_registry):
    repo_dir, _ = git_registry
    pine_file = repo_dir / "untracked-script.pine"
    pine_file.write_text(SAMPLE_PINE)
    # Deliberately never `git add`ed or committed.

    result = discover_and_register_scripts()

    assert result == ["untracked-script"]
    registry = load_registry()
    entry = registry.get_script("untracked-script")
    assert entry is not None
    assert entry.version == "untracked"


# --- Test 6: PINE_REGISTRY_PATH's parent isn't inside a git repo at all ---

def test_discover_and_register_scripts_not_a_git_repo_returns_untracked_version(
    tmp_path, monkeypatch
):
    no_repo_dir = tmp_path / "no-repo"
    no_repo_dir.mkdir()
    registry_path = no_repo_dir / "registry.json"
    monkeypatch.setattr(pine_script_manager, "PINE_REGISTRY_PATH", registry_path)
    pine_file = no_repo_dir / "standalone.pine"
    pine_file.write_text(SAMPLE_PINE)

    result = discover_and_register_scripts()

    assert result == ["standalone"]
    registry = load_registry()
    entry = registry.get_script("standalone")
    assert entry is not None
    assert entry.version == "untracked"


# --- Test 7: nothing new to discover returns an empty list ---

def test_discover_and_register_scripts_returns_empty_list_when_nothing_new(git_registry):
    repo_dir, _ = git_registry
    pine_file = repo_dir / "existing.pine"
    pine_file.write_text(SAMPLE_PINE)
    _commit_file(repo_dir, "existing.pine", day=1)
    register_script("existing", "existing.pine", "Manually registered", version="1.0.0")

    result = discover_and_register_scripts()

    assert result == []


# --- Test 8: PINE_REGISTRY_PATH's parent directory doesn't exist on disk ---

def test_discover_and_register_scripts_missing_directory_returns_empty_list(
    tmp_path, monkeypatch
):
    missing_dir = tmp_path / "does-not-exist"
    registry_path = missing_dir / "registry.json"
    monkeypatch.setattr(pine_script_manager, "PINE_REGISTRY_PATH", registry_path)

    result = discover_and_register_scripts()

    assert result == []
