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
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

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
    """

    path: str
    version: str
    description: str
    last_injected: Optional[str] = None
    hash: str


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
) -> PineScriptEntry:
    """Create or update a script entry in the registry and persist it.

    Loads the current registry, adds/replaces the entry for `name`
    (re-registering an existing name overwrites its version/description/
    path/hash — entries are treated as immutable outside of this
    re-register path), and saves atomically.

    Args:
        name: Script name to register/update (registry key).
        path: Path to the .pine file, relative to
            plugins/tradingview/assets/pinescript-indicators/.
        description: Human-readable summary of the indicator.
        version: Semantic version string (default "1.0.0").

    Returns:
        The newly stored PineScriptEntry.
    """
    registry = load_registry()
    entry = PineScriptEntry(
        path=path,
        version=version,
        description=description,
        hash=_compute_placeholder_hash(path, version),
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
    save_registry(registry)
    return True
