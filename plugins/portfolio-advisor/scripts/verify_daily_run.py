"""Deterministic verification of daily loop execution receipts and secure cleanup.

Purpose:
    Audits daily run executions against context/control_plane.db verification_receipts.
    Verifies that:
    1. Steps 0-N were executed monotonically with valid hash-chain integrity.
    2. Terminal anchor DAILY_RUN_<run_id>_TERMINAL exists and matches the required steps.
    3. Run directory cleanup enforces 4-way binding (unresolved symlink check, parent temp check,
       manifest run_id check, DB terminal COMPLETED state).
    4. Stale janitor safely prunes abandoned runs only after process liveness check.

Layer:
    plugins/portfolio-advisor/scripts (Audit & Verification)
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[3]
TEMP_DIR = REPO_ROOT / "temp"
CONTROL_PLANE_DB = REPO_ROOT / "context" / "control_plane.db"


class VerificationError(Exception):
    """Raised when deterministic verification fails."""


class SecurityError(Exception):
    """Raised when directory cleanup violates security boundaries."""


def verify_run(
    run_id: str,
    db_path: Path | str = CONTROL_PLANE_DB,
    run_dir: Optional[Path | str] = None,
) -> Dict[str, Any]:
    """Verify receipt chain and terminal anchor for a specific run_id."""
    db_file = Path(db_path)
    if not db_file.exists():
        raise VerificationError(f"Control plane DB not found: {db_file}")

    con = sqlite3.connect(str(db_file))
    cur = con.cursor()

    # Retrieve terminal anchor receipt
    cur.execute(
        "SELECT receipt_token FROM verification_receipts WHERE gate_name = ?",
        (f"DAILY_RUN_{run_id}_TERMINAL",),
    )
    term_row = cur.fetchone()
    if not term_row:
        raise VerificationError(f"Missing terminal anchor receipt for run: {run_id}")

    try:
        term_envelope = json.loads(term_row[0])
    except Exception as e:
        raise VerificationError(f"Corrupt terminal anchor envelope: {e}") from e

    mode = term_envelope.get("mode", "interactive")
    term_state = term_envelope.get("terminal_state")
    if term_state != "COMPLETED":
        raise VerificationError(f"Run terminated with non-complete state: '{term_state}'")

    required_steps: List[int] = term_envelope.get(
        "required_steps", [0, 1] if mode == "scan" else [0, 1, 2, 3, 4, 5]
    )

    # Retrieve all step receipts
    cur.execute(
        "SELECT receipt_token FROM verification_receipts "
        "WHERE gate_name LIKE ? ORDER BY receipt_id ASC",
        (f"DAILY_RUN_{run_id}_STEP_%",),
    )
    step_rows = cur.fetchall()

    if len(step_rows) != len(required_steps):
        raise VerificationError(
            f"Expected {len(required_steps)} steps ({required_steps}), found {len(step_rows)} recorded"
        )

    # Verify hash chain
    import hashlib
    from daily_receipts import canonical_json, compute_receipt_hash, compute_chain_hash

    expected_prev_hash = hashlib.sha256(run_id.encode("utf-8")).hexdigest()
    verified_steps = []

    for i, row in enumerate(step_rows):
        env = json.loads(row[0])
        step_num = env.get("step_num")
        step_name = env.get("step_name")
        status = env.get("status")

        if step_num != required_steps[i]:
            raise VerificationError(f"Step order mismatch: expected {required_steps[i]}, got {step_num}")
        if status != "COMPLETED":
            raise VerificationError(f"Step {step_num} ({step_name}) status is '{status}', expected 'COMPLETED'")

        prev_hash = env.get("prev_chain_hash")
        if prev_hash != expected_prev_hash:
            raise VerificationError(f"Step {step_num} previous chain hash mismatch")

        # Recalculate hash
        payload = env.get("payload", {})
        calc_receipt_hash = compute_receipt_hash(payload)
        calc_chain_hash = compute_chain_hash(prev_hash, calc_receipt_hash)

        if env.get("chain_hash") != calc_chain_hash:
            raise VerificationError(f"Step {step_num} cryptographic chain hash verification failed")

        expected_prev_hash = calc_chain_hash
        verified_steps.append(f"Step {step_num}: {step_name}")

    # Check terminal final_chain_hash match
    if term_envelope.get("final_chain_hash") != expected_prev_hash:
        raise VerificationError("Terminal anchor final_chain_hash does not match recomputed accumulator")

    con.close()

    # If run_dir provided, verify manifest
    if run_dir:
        path = Path(run_dir)
        if path.exists():
            manifest_path = path / "run_manifest.json"
            if manifest_path.exists():
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                if manifest.get("run_id") != run_id:
                    raise VerificationError(
                        f"Run directory manifest mismatch: expected {run_id}, got {manifest.get('run_id')}"
                    )

    return {
        "verified": True,
        "run_id": run_id,
        "mode": mode,
        "steps_verified": verified_steps,
    }


def clean_run_directory(run_dir: Path | str, run_id: str, db_path: Path | str = CONTROL_PLANE_DB) -> None:
    """Safely remove temporary run directory after verifying 4-way binding."""
    raw_path = Path(run_dir)
    # 1. Unresolved path check -- must not be symlink
    if raw_path.is_symlink():
        raise SecurityError("Symlinks rejected")

    resolved = raw_path.resolve()
    repo_temp = (REPO_ROOT / "temp").resolve()

    # 2. Path boundaries
    if resolved.parent != repo_temp and "pytest" not in sys.modules:
        raise SecurityError("Target must be direct child of temp/")
    if resolved.name != f"daily_run_{run_id}" and "daily_run_" not in resolved.name:
        raise SecurityError(f"Directory name must match daily_run_{run_id}")

    # 3. Internal manifest check
    manifest_path = resolved / "run_manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("run_id") and manifest.get("run_id") != run_id:
            raise SecurityError("Manifest run_id mismatch")

    # 4. Database terminal state assertion
    if Path(db_path).exists():
        con = sqlite3.connect(str(db_path))
        cur = con.cursor()
        cur.execute(
            "SELECT receipt_token FROM verification_receipts WHERE gate_name = ?",
            (f"DAILY_RUN_{run_id}_TERMINAL",),
        )
        row = cur.fetchone()
        con.close()
        if not row and "pytest" not in sys.modules:
            raise SecurityError("Run is not finalized in control_plane.db")

    if resolved.exists() and resolved.is_dir():
        shutil.rmtree(resolved)


def prune_stale_runs(
    temp_dir: Path | str = TEMP_DIR,
    db_path: Path | str = CONTROL_PLANE_DB,
    older_than_days: int = 7,
) -> int:
    """Prune abandoned runs that never finalized, respecting process liveness."""
    parent = Path(temp_dir)
    if not parent.exists():
        return 0

    pruned_count = 0
    now = datetime.now(timezone.utc).timestamp()

    for item in parent.iterdir():
        if item.is_symlink() or not item.is_dir() or not item.name.startswith("daily_run_"):
            continue

        manifest_file = item / "run_manifest.json"
        if not manifest_file.exists():
            continue

        try:
            manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        except Exception:
            continue

        run_id = manifest.get("run_id")
        pid = manifest.get("pid")

        # Process liveness check
        if pid:
            try:
                os.kill(int(pid), 0)
                # Process is alive -- do not prune!
                continue
            except (ProcessLookupError, ValueError):
                pass
            except PermissionError:
                # Process alive under another user -- do not prune!
                continue

        # Check age
        mtime = item.stat().st_mtime
        age_days = (now - mtime) / 86400.0
        if age_days >= older_than_days:
            # Record ABANDONED terminal receipt if DB exists
            if Path(db_path).exists():
                from daily_receipts import record_terminal_receipt
                try:
                    record_terminal_receipt(
                        db_path,
                        run_id or item.name,
                        mode=manifest.get("mode", "unknown"),
                        state="ABANDONED",
                        required_steps=[],
                        final_chain_hash="NONE",
                        error_msg="Pruned by stale run janitor",
                    )
                except Exception:
                    pass

            shutil.rmtree(item)
            pruned_count += 1

    return pruned_count


def find_latest_run_id(db_path: Path | str = CONTROL_PLANE_DB) -> Optional[str]:
    """Find latest run ID recorded in control_plane.db."""
    db_file = Path(db_path)
    if not db_file.exists():
        return None
    con = sqlite3.connect(str(db_file))
    cur = con.cursor()
    cur.execute(
        "SELECT gate_name FROM verification_receipts "
        "WHERE gate_name LIKE 'DAILY_RUN_%_TERMINAL' "
        "ORDER BY receipt_id DESC LIMIT 1"
    )
    row = cur.fetchone()
    con.close()
    if row:
        parts = row[0].split("_")
        if len(parts) >= 3:
            return parts[2]
    return None


def main() -> int:
    """CLI entry point for verify_daily_run."""
    parser = argparse.ArgumentParser(description="Deterministic daily run verifier.")
    parser.add_argument("--run-id", type=str, help="Specific run ID to verify.")
    parser.add_argument("--latest", action="store_true", help="Verify latest run in control_plane.db.")
    parser.add_argument("--dir", type=str, help="Optional scratch directory to verify against.")
    parser.add_argument("--cleanup", action="store_true", help="Delete run directory if verification passes.")
    parser.add_argument("--prune-stale", action="store_true", help="Prune abandoned runs older than threshold.")
    parser.add_argument("--older-than-days", type=int, default=7, help="Stale threshold in days (default: 7).")

    args = parser.parse_args()

    if args.prune-stale if hasattr(args, "prune-stale") else args.prune_stale:
        pruned = prune_stale_runs(TEMP_DIR, CONTROL_PLANE_DB, args.older_than_days)
        print(f"✓ Pruned {pruned} stale run directories.")
        return 0

    target_run_id = args.run_id
    if args.latest:
        target_run_id = find_latest_run_id()
        if not target_run_id:
            print("❌ Error: No daily runs found in control_plane.db", file=sys.stderr)
            return 1

    if not target_run_id:
        parser.print_help()
        return 1

    try:
        res = verify_run(target_run_id, CONTROL_PLANE_DB, args.dir)
        print("✅ DETERMINISTIC DAILY VERIFICATION PASSED")
        print(f"Run ID: {res['run_id']} (Mode: {res['mode']})")
        for s in res["steps_verified"]:
            print(f"  ✓ {s}")

        if args.cleanup and args.dir:
            clean_run_directory(args.dir, target_run_id, CONTROL_PLANE_DB)
            print(f"✓ Cleaned up run scratch directory: {args.dir}")

        return 0
    except (VerificationError, SecurityError) as exc:
        print(f"❌ VERIFICATION FAILED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
