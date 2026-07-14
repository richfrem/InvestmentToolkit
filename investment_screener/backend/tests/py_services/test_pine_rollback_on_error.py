"""
Task 5B-5: Rollback Mechanism

Tests for pine_script_manager.rollback_pine_script(), which composes
5B-4's list_script_versions() (real git history) with a raw git-show
file-content restore, a registry version/hash update, and 5B-3's
inject_pine_script() to roll a registered Pine Script back to a prior
version and re-inject it.

IMPORTANT: Tests that need real version history use a REAL temporary git
repository (subprocess.run(["git", "init", ...]) inside tmp_path, real
git add/commit calls, PINE_REGISTRY_PATH monkeypatched into that repo) —
same pattern as test_pine_version_history_from_git.py. tv_call is mocked
at the module level — same pattern as test_pine_injection_auto_clicks.py
— no test here ever shells out to the real TV CDP engine.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

import pine_script_manager  # noqa: E402
from pine_script_manager import load_registry, rollback_pine_script  # noqa: E402

VALID_PINE_V1 = (
    "//@version=6\n"
    'indicator("Rollback Test v1", overlay=true)\n'
    "plot(close)\n"
)

VALID_PINE_V2 = (
    "//@version=6\n"
    'indicator("Rollback Test v2", overlay=true)\n'
    "plot(close, color=color.blue)\n"
)


def _never_call(*args, **kwargs):
    """A tv_call stand-in that fails the test loudly if ever invoked."""
    raise AssertionError(f"tv_call must not be invoked, but was called with args={args}")


def _always_succeed_tv_call(*args, **kwargs):
    """A tv_call stand-in that always reports success."""
    return {"success": True}


def _git_env(day: int) -> dict:
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


def _commit_version(
    repo_dir: Path,
    registry_path: Path,
    script_name: str,
    filename: str,
    content: str,
    version: str,
    day: int,
) -> Path:
    """Write a .pine file + matching registry.json entry and commit both.

    Returns the full path of the .pine file written.
    """
    script_path = repo_dir / filename
    script_path.write_text(content)
    registry_data = {
        "scripts": {
            script_name: {
                "path": filename,
                "version": version,
                "description": "Rollback test script",
                "last_injected": None,
                "hash": f"hash-{version}",
            }
        }
    }
    registry_path.write_text(json.dumps(registry_data, indent=2))
    _run_git(["add", filename, registry_path.name], cwd=repo_dir, day=day)
    _run_git(["commit", "-m", f"v{version}"], cwd=repo_dir, day=day)
    return script_path


@pytest.fixture
def git_registry(tmp_path, monkeypatch):
    """A real git repo with PINE_REGISTRY_PATH pointed at registry.json inside it."""
    repo_dir = tmp_path / "repo"
    _init_repo(repo_dir)
    registry_path = repo_dir / "registry.json"
    monkeypatch.setattr(pine_script_manager, "PINE_REGISTRY_PATH", registry_path)
    return repo_dir, registry_path


# --- Test 1: happy path — restore prior version's content, reinject, persist ---

def test_rollback_pine_script_restores_prior_version_and_reinjects(git_registry, monkeypatch):
    repo_dir, registry_path = git_registry
    script_path = _commit_version(
        repo_dir, registry_path, "my-script", "my-script.pine", VALID_PINE_V1, "1.0.0", day=1
    )
    _commit_version(
        repo_dir, registry_path, "my-script", "my-script.pine", VALID_PINE_V2, "1.1.0", day=2
    )

    calls = []

    def fake_tv_call(*args, **kwargs):
        calls.append(args)
        return {"success": True}

    monkeypatch.setattr(pine_script_manager, "tv_call", fake_tv_call)

    result = rollback_pine_script("my-script", "1.0.0", "NVDA")

    assert result is True
    assert script_path.read_text() == VALID_PINE_V1
    registry = load_registry()
    assert registry.get_script("my-script").version == "1.0.0"
    assert registry.get_script("my-script").hash == "hash-1.0.0"
    assert calls[0] == ("chart", "symbol", "NVDA")
    assert calls[1] == ("pine", "inject", "--content", VALID_PINE_V1)


# --- Test 2: unknown script never touches git or tv_call ---

def test_rollback_pine_script_unknown_script_returns_false(tmp_path, monkeypatch):
    registry_path = tmp_path / "registry.json"
    monkeypatch.setattr(pine_script_manager, "PINE_REGISTRY_PATH", registry_path)
    monkeypatch.setattr(pine_script_manager, "tv_call", _never_call)

    result = rollback_pine_script("does-not-exist", "1.0.0", "NVDA")

    assert result is False


# --- Test 3: requested version never existed in real history ---

def test_rollback_pine_script_version_not_in_history_returns_false(git_registry, monkeypatch):
    repo_dir, registry_path = git_registry
    _commit_version(
        repo_dir, registry_path, "my-script", "my-script.pine", VALID_PINE_V1, "1.0.0", day=1
    )
    monkeypatch.setattr(pine_script_manager, "tv_call", _never_call)

    result = rollback_pine_script("my-script", "9.9.9", "NVDA")

    assert result is False


# --- Test 4: version found in history, but its content can't be read from git ---

def test_rollback_pine_script_git_show_failure_returns_false(git_registry, monkeypatch):
    repo_dir, registry_path = git_registry
    _commit_version(
        repo_dir, registry_path, "my-script", "my-script.pine", VALID_PINE_V1, "1.0.0", day=1
    )
    _commit_version(
        repo_dir, registry_path, "my-script", "my-script.pine", VALID_PINE_V2, "1.1.0", day=2
    )
    monkeypatch.setattr(pine_script_manager, "_git_show_file_content", lambda *a, **k: None)
    monkeypatch.setattr(pine_script_manager, "tv_call", _never_call)

    result = rollback_pine_script("my-script", "1.0.0", "NVDA")

    assert result is False


# --- Test 5: restore + registry update succeed, but re-injection fails ---

def test_rollback_pine_script_injection_failure_after_restore_still_restores_file(
    git_registry, monkeypatch
):
    repo_dir, registry_path = git_registry
    script_path = _commit_version(
        repo_dir, registry_path, "my-script", "my-script.pine", VALID_PINE_V1, "1.0.0", day=1
    )
    _commit_version(
        repo_dir, registry_path, "my-script", "my-script.pine", VALID_PINE_V2, "1.1.0", day=2
    )

    def fake_tv_call(*args, **kwargs):
        if args[:2] == ("chart", "symbol"):
            return {"success": True}
        # 5A-8 error-dict shape: no "success" key.
        return {
            "error": "CDP timeout",
            "data": None,
            "cached": False,
            "timestamp": "2026-07-13T00:00:00+00:00",
        }

    monkeypatch.setattr(pine_script_manager, "tv_call", fake_tv_call)

    result = rollback_pine_script("my-script", "1.0.0", "NVDA")

    assert result is False
    assert script_path.read_text() == VALID_PINE_V1
    registry = load_registry()
    assert registry.get_script("my-script").version == "1.0.0"


# --- Test 6: registry write failure must not block re-injection ---

def test_rollback_pine_script_registry_write_failure_does_not_block_reinject(
    git_registry, monkeypatch
):
    repo_dir, registry_path = git_registry
    _commit_version(
        repo_dir, registry_path, "my-script", "my-script.pine", VALID_PINE_V1, "1.0.0", day=1
    )
    _commit_version(
        repo_dir, registry_path, "my-script", "my-script.pine", VALID_PINE_V2, "1.1.0", day=2
    )

    monkeypatch.setattr(pine_script_manager, "tv_call", _always_succeed_tv_call)

    def failing_save_registry(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(pine_script_manager, "save_registry", failing_save_registry)

    result = rollback_pine_script("my-script", "1.0.0", "NVDA")

    assert result is True


# --- Test 7: file-write failure happens before any side effect / injection ---

def test_rollback_pine_script_file_write_failure_returns_false_before_injection(
    git_registry, monkeypatch
):
    repo_dir, registry_path = git_registry
    _commit_version(
        repo_dir, registry_path, "my-script", "my-script.pine", VALID_PINE_V1, "1.0.0", day=1
    )
    _commit_version(
        repo_dir, registry_path, "my-script", "my-script.pine", VALID_PINE_V2, "1.1.0", day=2
    )

    monkeypatch.setattr(pine_script_manager, "tv_call", _never_call)

    def boom(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(Path, "write_text", boom)

    result = rollback_pine_script("my-script", "1.0.0", "NVDA")

    assert result is False
