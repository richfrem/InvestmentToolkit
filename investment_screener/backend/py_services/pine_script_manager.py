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
from pathlib import Path
from typing import Dict, Optional

from pydantic import BaseModel, Field

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
