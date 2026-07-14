"""
Pine Script Manager — Registry Schema & Storage (Task 5B-1)

Provides the central JSON-backed registry for tracked Pine Script
indicators living under
plugins/tradingview/assets/pinescript-indicators/. Each entry records the
script's relative path, semantic version, human description, last
injection timestamp, and a content/commit hash for change detection.

This module is the foundation for all later 5B tasks (validation,
injection, version control, rollback, library management,
auto-discovery, /daily integration) — they all read/write through
load_registry() / save_registry() / register_script() rather than
touching registry.json directly.

Key Input Dependencies:
    - plugins/tradingview/assets/pinescript-indicators/registry.json
      (the real, tracked registry file this module manages)
"""

import json
import logging
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Cross-directory import of the real PineLinter (Task 5B-2) and tv_call
# (Task 5A-8). Follows the same sys.path-insert pattern as
# tv_cdp_health.py's import of tv_client.py — plugins/tradingview/scripts/
# is not a package on the default path. Neither pine_linter.py nor
# tv_client.py is touched; this module only wraps their output.
_TV_SCRIPTS_DIR = str(Path(__file__).resolve().parents[3] / "plugins" / "tradingview" / "scripts")
if _TV_SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _TV_SCRIPTS_DIR)

from pine_linter import PineLinter  # noqa: E402
from tv_client import tv_call  # noqa: E402

# Central Pine Script registry file. Tests monkeypatch this module-level
# constant to a temp path — never write to the real path from a test.
# Real path per the brief's Global Constraints (exact location).
PINE_REGISTRY_PATH = (
    Path(__file__).resolve().parents[3]
    / "plugins"
    / "tradingview"
    / "assets"
    / "pinescript-indicators"
    / "registry.json"
)


class PineScriptEntry(BaseModel):
    """A single registered Pine Script indicator.

    Attributes:
        path: Path to the .pine file, relative to
            plugins/tradingview/assets/pinescript-indicators/.
        version: Semantic version string for this script.
        description: Human-readable summary of what the indicator does.
        last_injected: ISO 8601 timestamp of the last successful
            injection into TradingView, or None if never injected.
        hash: Git commit hash or file content hash, used to detect
            changes since the last registration.
        category: Free-text tag for the script's style/purpose (e.g.
            "level", "trend-follower", "mean-reversion"). Not an enum —
            new categories can't be predicted in advance. None for
            scripts registered before Task 5B-6 or that never set one.
    """

    path: str
    version: str
    description: str
    last_injected: Optional[str] = None
    hash: str
    category: Optional[str] = None


class PineScriptRegistry(BaseModel):
    """Root registry model: a dict of script_name -> PineScriptEntry."""

    scripts: Dict[str, PineScriptEntry] = Field(default_factory=dict)

    def get_script(self, name: str) -> Optional[PineScriptEntry]:
        """Look up a registered script entry by name.

        Args:
            name: Registered script name (registry key).

        Returns:
            The matching PineScriptEntry, or None if not registered.
        """
        return self.scripts.get(name)

    def add_script(self, name: str, entry: PineScriptEntry) -> None:
        """Add or replace a script entry in this registry (in memory only).

        Args:
            name: Script name to register/update (registry key).
            entry: The PineScriptEntry to store under that name.
        """
        self.scripts[name] = entry


def _raise_corrupted_registry_error(cause: Exception) -> None:
    """Raise a clear, actionable error for a corrupted registry.json.

    Args:
        cause: The underlying JSONDecodeError from json.loads().

    Raises:
        ValueError: Always. Names the file and states it's corrupted,
            rather than surfacing a bare json.JSONDecodeError.
    """
    raise ValueError(
        f"Pine Script registry file is corrupted (invalid JSON) at "
        f"{PINE_REGISTRY_PATH}: {cause}. Fix or delete the file — a "
        f"deleted file is re-initialized as an empty registry on next load."
    ) from cause


def load_registry() -> PineScriptRegistry:
    """Load the Pine Script registry from PINE_REGISTRY_PATH.

    Returns:
        The parsed PineScriptRegistry, or an empty registry (no scripts)
        if the file does not exist yet.

    Raises:
        ValueError: If the file exists but contains invalid JSON.
    """
    if not PINE_REGISTRY_PATH.exists():
        return PineScriptRegistry()

    raw_text = PINE_REGISTRY_PATH.read_text()
    try:
        raw_data = json.loads(raw_text)
    except json.JSONDecodeError as e:
        _raise_corrupted_registry_error(e)

    return PineScriptRegistry(**raw_data)


def save_registry(registry: PineScriptRegistry) -> None:
    """Atomically write the registry to PINE_REGISTRY_PATH.

    Writes to a sibling temp file first, then os.replace()s it over the
    real path in a single filesystem operation, so readers never observe
    a partially written registry file and a failure mid-write leaves the
    prior file (or no file) untouched.

    Args:
        registry: The PineScriptRegistry to persist.

    Raises:
        OSError: If directory creation, temp-file write, or the atomic
            rename fails. Callers are responsible for handling this.
    """
    PINE_REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = registry.model_dump_json(indent=2)

    tmp_path = PINE_REGISTRY_PATH.with_name(PINE_REGISTRY_PATH.name + ".tmp")
    try:
        with open(tmp_path, "w") as f:
            f.write(payload)
        os.replace(tmp_path, PINE_REGISTRY_PATH)
    except OSError:
        # Best-effort cleanup of the temp file so a failed write never
        # leaves a stray .tmp artifact behind alongside the untouched
        # real registry file.
        if tmp_path.exists():
            tmp_path.unlink()
        raise


def register_script(
    name: str,
    path: str,
    description: str,
    version: str = "1.0.0",
    category: Optional[str] = None,
) -> PineScriptEntry:
    """Create or update a script entry in the registry and persist it.

    Loads the current registry, adds/replaces the entry for `name`
    (re-registering an existing name overwrites its version/description/
    path/hash/category — entries are treated as immutable outside of
    this re-register path), and saves atomically.

    Args:
        name: Script name to register/update (registry key).
        path: Path to the .pine file, relative to
            plugins/tradingview/assets/pinescript-indicators/.
        description: Human-readable summary of the indicator.
        version: Semantic version string (default "1.0.0").
        category: Free-text style/purpose tag (e.g. "level",
            "trend-follower"). Defaults to None for backward
            compatibility with existing call sites (5B-1 through 5B-5)
            that don't pass one.

    Returns:
        The newly stored PineScriptEntry.
    """
    registry = load_registry()
    entry = PineScriptEntry(
        path=path,
        version=version,
        description=description,
        hash=_compute_placeholder_hash(path, version),
        category=category,
    )
    registry.add_script(name, entry)
    save_registry(registry)
    return entry


def _compute_placeholder_hash(path: str, version: str) -> str:
    """Derive a stable placeholder hash for a script entry.

    This task (5B-1) only owns registry storage, not file hashing
    (that's a later 5B task's concern — e.g. auto-discovery/validation
    computing a real content hash). Until then, register_script() needs
    *some* value for the required `hash` field; derive a deterministic
    one from (path, version) rather than leaving it blank, so repeated
    registrations of the same version are reproducible.

    Args:
        path: Path to the .pine file.
        version: Semantic version string.

    Returns:
        A short deterministic hex digest string.
    """
    import hashlib

    return hashlib.sha256(f"{path}:{version}".encode("utf-8")).hexdigest()[:12]


def _missing_file_errors(file_path: str, linter_errors: List[str], is_valid: bool) -> List[str]:
    """Fill in a synthetic error when PineLinter left .errors empty.

    PineLinter.lint() returns False for a nonexistent file but only
    prints a message — it does not append anything to self.errors for
    that specific case (confirmed against the real source). Without
    this, callers would see valid=False with an empty errors list,
    which the brief calls out as not meaningful.

    Args:
        file_path: The path that was validated.
        linter_errors: PineLinter's own .errors list after .lint().
        is_valid: PineLinter.lint()'s return value.

    Returns:
        linter_errors unchanged if non-empty or if is_valid is True;
        otherwise a single synthetic "file not found" message if the
        path genuinely doesn't exist on disk.
    """
    if linter_errors or is_valid:
        return linter_errors
    if not os.path.exists(file_path):
        return [f"File not found: {file_path}"]
    return linter_errors


def validate_pine_script(file_path: str) -> dict:
    """Validate a Pine Script file using the existing PineLinter.

    Wraps plugins/tradingview/scripts/pine_linter.py's PineLinter class,
    translating its bool-return-plus-printed-report interface into a
    structured result for programmatic callers (registry, injection,
    rollback in later 5B tasks). No lint rules are reimplemented here —
    PineLinter does all the actual checking.

    Args:
        file_path: Path to the .pine file to validate.

    Returns:
        Dict with exactly these keys:
            valid: True if PineLinter found zero errors (warnings never
                affect validity, matching PineLinter's own semantics).
            errors: List of error message strings. Non-empty whenever
                valid is False — a synthetic message is substituted for
                the missing-file case, since PineLinter itself doesn't
                populate .errors then.
            warnings: List of warning message strings (informational
                only; never affects `valid`).

    Never raises: a missing, malformed, or unreadable script file is a
    normal input for a validation function, not an exceptional one.
    """
    try:
        linter = PineLinter(file_path)
        is_valid = linter.lint()
    except Exception as e:
        return {
            "valid": False,
            "errors": [f"Unexpected error validating '{file_path}': {e}"],
            "warnings": [],
        }

    errors = _missing_file_errors(file_path, list(linter.errors), is_valid)
    return {"valid": is_valid, "errors": errors, "warnings": list(linter.warnings)}


def _resolve_script_path(entry: PineScriptEntry) -> Path:
    """Resolve a registry entry's `path` to a full filesystem path.

    Entry paths are relative to
    plugins/tradingview/assets/pinescript-indicators/, i.e. the parent
    directory of PINE_REGISTRY_PATH itself (read live off the module
    global so tests that monkeypatch PINE_REGISTRY_PATH resolve
    correctly against their temp registry's own directory).

    Args:
        entry: The registry entry whose path to resolve.

    Returns:
        The full filesystem Path to the .pine file.
    """
    return PINE_REGISTRY_PATH.parent / entry.path


def _tv_call_succeeded(result: dict) -> bool:
    """Decide whether a tv_call() response signals success.

    Reuses the exact distinguishing logic tv_pine_inject.py:84-91
    already established for tv_call()'s two distinct failure shapes:
    the Task 5A-8 error-dict contract ({"error": str, "data": ...,
    "cached": bool, "timestamp": str}, notably with no "success" key)
    and the CLI's own {"success": False, "error": ...} shape.

    Args:
        result: The raw dict returned by tv_call().

    Returns:
        False if either failure shape is present; True otherwise.
    """
    if not isinstance(result, dict):
        return False
    if "error" in result and "success" not in result:
        return False
    if result.get("success") is False:
        return False
    return True


def _switch_chart_and_inject(chart_symbol: str, script_content: str) -> bool:
    """Switch the active TV chart, then inject Pine Script content.

    Args:
        chart_symbol: Ticker to switch the active chart to first.
        script_content: Raw Pine Script source to inject.

    Returns:
        True only if both the chart-symbol switch and the injection
        call succeeded per _tv_call_succeeded().
    """
    switch_result = tv_call("chart", "symbol", chart_symbol)
    if not _tv_call_succeeded(switch_result):
        return False

    inject_result = tv_call("pine", "inject", "--content", script_content)
    return _tv_call_succeeded(inject_result)


def inject_pine_script(script_name: str, chart_symbol: str) -> bool:
    """Validate and inject a registered Pine Script onto a chart.

    Looks up `script_name` in the registry (5B-1), reads its .pine file
    content, validates it (5B-2), then switches the given chart to
    `chart_symbol` and injects the script via TV CDP (tv_client.tv_call,
    5A-8). Updates the registry's `last_injected` timestamp only on
    confirmed success. Refuses to call tv_call at all for an
    unregistered, missing, or invalid script.

    Never raises: every failure mode (unknown script, missing file,
    invalid script, chart-switch failure, injection failure) is a
    normal, expected outcome and returns False.

    Args:
        script_name: Registry key of the script to inject.
        chart_symbol: Ticker symbol to switch the active chart to
            before injecting (e.g. "NVDA").

    Returns:
        True only if the chart-symbol switch and the injection both
        succeeded; False otherwise.
    """
    registry = load_registry()
    entry = registry.get_script(script_name)
    if entry is None:
        print(f"inject_pine_script: '{script_name}' not found in registry", file=sys.stderr)
        return False

    full_path = _resolve_script_path(entry)
    if not full_path.exists():
        print(f"inject_pine_script: file missing at {full_path}", file=sys.stderr)
        return False

    validation = validate_pine_script(str(full_path))
    if not validation["valid"]:
        print(
            f"inject_pine_script: '{script_name}' failed validation: {validation['errors']}",
            file=sys.stderr,
        )
        return False

    script_content = full_path.read_text()
    if not _switch_chart_and_inject(chart_symbol, script_content):
        print(
            f"inject_pine_script: injection failed for '{script_name}' on {chart_symbol}",
            file=sys.stderr,
        )
        return False

    entry.last_injected = datetime.now(timezone.utc).isoformat()
    try:
        save_registry(registry)
    except OSError as e:
        # The chart injection above already succeeded — that real side
        # effect can't be undone, so a registry-write failure here must
        # not violate this function's never-raises contract. Bookkeeping
        # (last_injected) is secondary to the injection outcome itself.
        print(
            f"inject_pine_script: '{script_name}' injected but registry "
            f"update failed: {e}",
            file=sys.stderr,
        )
    return True


def _git_repo_root(start_path: Path) -> Optional[Path]:
    """Resolve the git repository root containing `start_path`.

    Args:
        start_path: A file or directory to resolve the enclosing repo
            root for (PINE_REGISTRY_PATH's parent directory).

    Returns:
        The repo root as a Path, or None if `start_path` is not inside a
        git repository, `git` is unavailable, or the call fails/times
        out for any reason.
    """
    cwd = start_path if start_path.is_dir() else start_path.parent
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as e:
        logger.warning("list_script_versions: git rev-parse failed: %s", e)
        return None
    if result.returncode != 0 or not result.stdout.strip():
        return None
    return Path(result.stdout.strip())


def _git_log_commits(repo_root: Path, relative_path: str) -> List[Tuple[str, str]]:
    """List (commit_hash, author_date_iso8601) touching a file, newest first.

    Args:
        repo_root: Root of the git repository to run `git log` in.
        relative_path: Path to the tracked file, relative to repo_root.

    Returns:
        A list of (full commit hash, %aI-formatted author date) tuples in
        `git log`'s default newest-first order. Empty list if the file
        has no history or the git call fails for any reason.
    """
    try:
        result = subprocess.run(
            ["git", "log", "--follow", "--format=%H|%aI", "--", relative_path],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as e:
        logger.warning("list_script_versions: git log failed: %s", e)
        return []
    if result.returncode != 0 or not result.stdout.strip():
        return []

    commits = []
    for line in result.stdout.strip().splitlines():
        if "|" not in line:
            continue
        commit_hash, timestamp = line.split("|", 1)
        commits.append((commit_hash, timestamp))
    return commits


def _git_show_registry_json(
    repo_root: Path, commit_hash: str, relative_path: str
) -> Optional[dict]:
    """Read and parse a historical revision of the registry file.

    Args:
        repo_root: Root of the git repository to run `git show` in.
        commit_hash: The commit whose revision of the file to read.
        relative_path: Path to the tracked file, relative to repo_root.

    Returns:
        The parsed JSON dict, or None if the git call fails or the
        historical content isn't valid JSON (logged as a warning either
        way rather than raised).
    """
    try:
        result = subprocess.run(
            ["git", "show", f"{commit_hash}:{relative_path}"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as e:
        logger.warning("list_script_versions: git show failed for %s: %s", commit_hash, e)
        return None
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        logger.warning(
            "list_script_versions: corrupted registry at commit %s: %s", commit_hash, e
        )
        return None


def _script_version_hash(data: dict, script_name: str) -> Optional[Tuple[str, str]]:
    """Extract (version, hash) for `script_name` from a parsed registry dict.

    Args:
        data: A parsed registry.json revision (arbitrary/untrusted shape).
        script_name: Registry key to look up.

    Returns:
        (version, hash) if `script_name` is present with both fields set,
        otherwise None.
    """
    scripts = data.get("scripts") if isinstance(data, dict) else None
    if not isinstance(scripts, dict):
        return None
    entry = scripts.get(script_name)
    if not isinstance(entry, dict):
        return None
    version, hash_value = entry.get("version"), entry.get("hash")
    if version is None or hash_value is None:
        return None
    return (version, hash_value)


def list_script_versions(script_name: str) -> List[dict]:
    """Return a script's version history from registry.json's git history.

    Walks `git log --follow` for PINE_REGISTRY_PATH (newest first),
    reading each historical revision via `git show` and recording a
    version-history entry whenever `script_name`'s (version, hash) pair
    differs from the immediately newer entry already collected — so a
    commit that only touched a different script's entry, or this
    script's `last_injected`, does not produce a spurious duplicate row.

    Args:
        script_name: Registry key of the script to look up history for.

    Returns:
        A list of {"version", "hash", "timestamp", "commit"} dicts,
        newest first. Empty list if `script_name` has no history, the
        registry file has no git history, or PINE_REGISTRY_PATH isn't
        inside a git repository at all. Never raises — every failure
        mode (missing repo, missing history, corrupted historical
        revision) degrades to an empty or partial list.
    """
    repo_root = _git_repo_root(PINE_REGISTRY_PATH.parent)
    if repo_root is None:
        logger.warning(
            "list_script_versions: %s is not inside a git repository", PINE_REGISTRY_PATH
        )
        return []

    try:
        relative_path = str(PINE_REGISTRY_PATH.relative_to(repo_root))
    except ValueError as e:
        logger.warning(
            "list_script_versions: %s is outside repo root %s: %s",
            PINE_REGISTRY_PATH,
            repo_root,
            e,
        )
        return []

    commits = _git_log_commits(repo_root, relative_path)

    history: List[dict] = []
    last_version_hash: Optional[Tuple[str, str]] = None
    for commit_hash, timestamp in commits:
        data = _git_show_registry_json(repo_root, commit_hash, relative_path)
        if data is None:
            continue
        version_hash = _script_version_hash(data, script_name)
        if version_hash is None or version_hash == last_version_hash:
            continue
        last_version_hash = version_hash
        history.append({
            "version": version_hash[0],
            "hash": version_hash[1],
            "timestamp": timestamp,
            "commit": commit_hash[:7],
        })
    return history


def _git_show_file_content(repo_root: Path, commit_hash: str, relative_path: str) -> Optional[str]:
    """Read a historical revision of an arbitrary tracked file as text.

    Sibling to _git_show_registry_json() (5B-4), but returns the raw
    stdout text instead of json.loads()-ing it, since a rolled-back
    .pine file's historical content isn't JSON.

    Args:
        repo_root: Root of the git repository to run `git show` in.
        commit_hash: The commit whose revision of the file to read.
        relative_path: Path to the tracked file, relative to repo_root.

    Returns:
        The raw file content as a string, or None if the git call fails
        for any reason (non-zero exit, OSError, SubprocessError, or
        timeout). Never raises.
    """
    try:
        result = subprocess.run(
            ["git", "show", f"{commit_hash}:{relative_path}"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as e:
        logger.warning("rollback_pine_script: git show failed for %s: %s", commit_hash, e)
        return None
    if result.returncode != 0:
        return None
    return result.stdout


def _find_history_entry(script_name: str, to_version: str) -> Optional[dict]:
    """Find the most recent version-history entry matching `to_version`.

    Args:
        script_name: Registry key to look up version history for.
        to_version: The semantic version string to search for.

    Returns:
        The matching {"version", "hash", "timestamp", "commit"} dict from
        list_script_versions() (5B-4) — the first (i.e. most recent,
        given the newest-first list) match — or None if no entry in the
        script's history has that version.
    """
    for entry in list_script_versions(script_name):
        if entry["version"] == to_version:
            return entry
    return None


def _restore_script_content(entry: PineScriptEntry, commit_hash: str) -> Optional[str]:
    """Read a script's historical .pine content at a given commit.

    Resolves the repo root and the entry's current file path relative to
    it (renamed-file history is out of scope, matching 5B-4's own scope
    boundary for registry.json), then reads that path's content as of
    `commit_hash`.

    Args:
        entry: The current registry entry — used only to resolve the
            .pine file's repo-relative path.
        commit_hash: The short commit hash to read historical content
            from (as returned by list_script_versions()).

    Returns:
        The historical file content, or None if the repo root can't be
        resolved, the .pine path lies outside the repo, or the git show
        call fails. Never raises.
    """
    repo_root = _git_repo_root(PINE_REGISTRY_PATH.parent)
    if repo_root is None:
        return None
    full_path = _resolve_script_path(entry)
    try:
        relative_path = str(full_path.relative_to(repo_root))
    except ValueError:
        return None
    return _git_show_file_content(repo_root, commit_hash, relative_path)


def rollback_pine_script(script_name: str, to_version: str, chart_symbol: str) -> bool:
    """
    Restore a registered script to a prior version and re-inject it.

    Finds `to_version` in the script's registry.json git history (5B-4),
    restores the .pine file's content from that historical commit,
    updates the registry entry's version/hash to match, then re-injects
    via inject_pine_script() (5B-3).

    Non-atomic by design: restoring the file and updating the registry
    are real, separate side effects that happen before re-injection is
    attempted. If injection then fails, they are NOT rolled back — this
    matches the module's existing philosophy (no transaction log
    anywhere in 5B-1 through 5B-4); "never raises" is about not throwing
    exceptions, not about atomicity.

    Never raises: every failure mode (unregistered script, version not
    found in history, git show failure, file-write failure, registry
    save failure, injection failure) returns False rather than
    propagating.

    Args:
        script_name: Registry key of the script to roll back.
        to_version: The semantic version string to restore. Caller-
            specified, not auto-detected — typically the entry just
            before the one that broke, per a prior list_script_versions()
            call.
        chart_symbol: Ticker symbol to switch the active chart to before
            re-injecting (passed straight through to
            inject_pine_script()).

    Returns:
        True only if the historical version is found, its content is
        restored to disk, and re-injection succeeds; False otherwise.
    """
    registry = load_registry()
    entry = registry.get_script(script_name)
    if entry is None:
        print(f"rollback_pine_script: '{script_name}' not found in registry", file=sys.stderr)
        return False

    history_entry = _find_history_entry(script_name, to_version)
    if history_entry is None:
        print(
            f"rollback_pine_script: version '{to_version}' not found in "
            f"history for '{script_name}'",
            file=sys.stderr,
        )
        return False

    restored_content = _restore_script_content(entry, history_entry["commit"])
    if restored_content is None:
        print(
            f"rollback_pine_script: could not read historical content for "
            f"'{script_name}' at commit {history_entry['commit']}",
            file=sys.stderr,
        )
        return False

    full_path = _resolve_script_path(entry)
    try:
        full_path.write_text(restored_content)
    except OSError as e:
        print(f"rollback_pine_script: failed to write {full_path}: {e}", file=sys.stderr)
        return False

    entry.version = to_version
    entry.hash = history_entry["hash"]
    registry.add_script(script_name, entry)
    try:
        save_registry(registry)
    except OSError as e:
        # The file has already been restored on disk — a real side
        # effect that can't be undone — so a registry bookkeeping
        # failure here must not block the re-injection attempt below.
        # Mirrors the exact precedent established by inject_pine_script's
        # own 5B-3 OSError fix (commit 40a17fe).
        print(
            f"rollback_pine_script: '{script_name}' restored but registry "
            f"update failed: {e}",
            file=sys.stderr,
        )

    return inject_pine_script(script_name, chart_symbol)


def _versions_dir(script_name: str) -> Path:
    """Resolve the version-archive directory for a script.

    Relative to PINE_REGISTRY_PATH's parent — the same base every entry
    `path` resolves against — read live off the module global so
    monkeypatched tests resolve into their own temp directory, matching
    _resolve_script_path()'s existing pattern.

    Args:
        script_name: Registry key of the script.

    Returns:
        Path to plugins/tradingview/assets/pinescript-indicators/
        versions/<script_name>/ (or the monkeypatched temp equivalent).
    """
    return PINE_REGISTRY_PATH.parent / "versions" / script_name


def archive_script_version(script_name: str) -> Optional[Path]:
    """Snapshot a registered script's current file content into its
    versions/ archive, named after its current registry version.

    Opt-in, not automatic — callers (e.g. a future CLI wrapper, or the
    5B-8 /daily integration) invoke this deliberately before overwriting
    an entry with a new version via register_script(), to preserve the
    outgoing version's content. This is a separate mechanism from
    5B-4/5B-5's git-history-based versioning (list_script_versions() /
    rollback_pine_script()) — a plain filesystem archive, independent of
    git, that coexists with rather than replaces it.

    Never raises: an unregistered script, a missing file on disk, or a
    filesystem write failure all degrade to None.

    Args:
        script_name: Registry key of the script to archive.

    Returns:
        The path the snapshot was written to, or None if the script
        isn't registered, its file is missing on disk, or the write
        failed.
    """
    registry = load_registry()
    entry = registry.get_script(script_name)
    if entry is None:
        return None

    full_path = _resolve_script_path(entry)
    if not full_path.exists():
        return None

    content = full_path.read_text()
    versions_dir = _versions_dir(script_name)
    snapshot_path = versions_dir / f"{entry.version}.pine"
    try:
        versions_dir.mkdir(parents=True, exist_ok=True)
        snapshot_path.write_text(content)
    except OSError as e:
        logger.warning(
            "archive_script_version: failed to archive '%s' version '%s': %s",
            script_name,
            entry.version,
            e,
        )
        return None
    return snapshot_path


def list_available_versions(script_name: str) -> List[str]:
    """List version strings archived for a script under its versions/
    directory (filenames without the .pine extension).

    Never raises: no archive directory, or any read failure, returns [].
    Sort order is lexical on the version string (NOT semver-aware — a
    real limitation, acceptable for now since no caller needs numeric
    version ordering yet; flag it if a later task does).

    Args:
        script_name: Registry key to look up archived versions for.

    Returns:
        Sorted list of version strings (e.g. ["1.0.0", "2.0.0"]), or []
        if none exist.
    """
    versions_dir = _versions_dir(script_name)
    if not versions_dir.exists():
        return []
    try:
        return sorted(p.stem for p in versions_dir.glob("*.pine"))
    except OSError as e:
        logger.warning(
            "list_available_versions: failed to list versions for '%s': %s",
            script_name,
            e,
        )
        return []
