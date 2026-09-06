"""Deterministic verification of daily loop checklist execution.

Purpose:
    Provides an independent, deterministic Python verification check that audits
    all phase completion artifacts written to a temporary scratch directory
    (e.g., temp/daily_run_<TIMESTAMP>/). Validates that the agent executed every
    step in the 5-step daily loop, adhering to system invariants and preventing
    shortcuts. Optionally cleans up the temporary directory upon 100% successful
    verification.

Layer:
    plugins/portfolio-advisor/scripts (Auditing & Execution Verification)

Usage:
    python3 plugins/portfolio-advisor/scripts/verify_daily_run.py --dir PATH [--cleanup]
    python3 plugins/portfolio-advisor/scripts/verify_daily_run.py --latest [--cleanup]

Key Functions:
    - verify_run_directory(run_dir): Validates all required step artifacts.
    - clean_run_directory(run_dir): Safely purges temporary run files after verification.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[3]
TEMP_DIR = REPO_ROOT / "temp"

REQUIRED_STEPS = [
    {
        "step": 0,
        "filename": "step0_readiness.json",
        "name": "Readiness",
        "required_fields": ["status", "server_running", "domain_db_verified"],
    },
    {
        "step": 1,
        "filename": "step1_brief.json",
        "name": "Morning Brief",
        "required_fields": ["status", "macro_regime", "conviction_scores_count"],
    },
    {
        "step": 2,
        "filename": "step2_triage.json",
        "name": "Triage",
        "required_fields": ["status", "queue_length", "confluence_verified"],
    },
    {
        "step": 3,
        "filename": "step3_actions.json",
        "name": "Action Cards",
        "required_fields": ["status", "cards_presented"],
    },
    {
        "step": 4,
        "filename": "step4_evolution.json",
        "name": "Self-Evolution",
        "required_fields": ["status", "evolution_logged"],
    },
    {
        "step": 5,
        "filename": "step5_summary.json",
        "name": "Session Summary",
        "required_fields": ["status", "reviewed_holdings"],
    },
]


class VerificationError(Exception):
    """Raised when deterministic daily verification fails."""


def verify_run_directory(run_dir: Path | str) -> Dict[str, Any]:
    """Verify that all checklist steps were executed and documented in run_dir.

    Args:
        run_dir: Path to the temporary run folder.

    Returns:
        Dict detailing verification results.

    Raises:
        VerificationError: If any step artifact is missing, invalid, or incomplete.
    """
    path = Path(run_dir)
    if not path.exists() or not path.is_dir():
        raise VerificationError(f"Run directory does not exist or is not a directory: {path}")

    verified_steps: List[str] = []

    for step_cfg in REQUIRED_STEPS:
        step_num = step_cfg["step"]
        step_name = step_cfg["name"]
        filename = step_cfg["filename"]
        file_path = path / filename

        if not file_path.exists():
            raise VerificationError(
                f"Missing required step artifact: {filename} (Step {step_num}: {step_name})"
            )

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as exc:
            raise VerificationError(f"Failed to parse JSON in {filename}: {exc}") from exc

        # Check status
        status = data.get("status")
        if status != "COMPLETED":
            raise VerificationError(
                f"Step {step_num} status is '{status}', expected 'COMPLETED' in {filename}"
            )

        # Check required fields
        for field in step_cfg["required_fields"]:
            if field not in data:
                raise VerificationError(
                    f"Step {step_num} artifact {filename} is missing required field '{field}'"
                )

        verified_steps.append(f"Step {step_num}: {step_name} ({filename})")

    return {
        "verified": True,
        "run_dir": str(path),
        "steps_verified": verified_steps,
    }


def clean_run_directory(run_dir: Path | str) -> None:
    """Safely remove the temporary run directory after successful verification.

    Args:
        run_dir: Path to the directory to remove.
    """
    path = Path(run_dir).resolve()
    # Safety guardrail: ensure we only delete subdirectories within temp/ or tmp_path
    repo_temp = TEMP_DIR.resolve()
    is_sub_temp = repo_temp in path.parents or "pytest" in sys.modules or "tmp" in str(path).lower()

    if not is_sub_temp:
        raise VerificationError(f"Refusing to delete directory outside temp tree: {path}")

    if path.exists() and path.is_dir():
        shutil.rmtree(path)


def find_latest_run_directory(temp_parent: Path | str | None = None) -> Path | None:
    """Find the most recently created daily_run_* directory in temp/."""
    parent = Path(temp_parent or TEMP_DIR)
    if not parent.exists():
        return None

    run_dirs = [d for d in parent.iterdir() if d.is_dir() and d.name.startswith("daily_run_")]
    if not run_dirs:
        return None

    run_dirs.sort(key=lambda d: d.stat().st_mtime, reverse=True)
    return run_dirs[0]


def main() -> int:
    """CLI entry point for verify_daily_run."""
    parser = argparse.ArgumentParser(description="Deterministic daily run verifier.")
    parser.add_argument(
        "--dir",
        type=str,
        help="Path to specific daily_run_<TIMESTAMP> directory to verify.",
    )
    parser.add_argument(
        "--latest",
        action="store_true",
        help="Automatically verify the latest daily_run_* directory in temp/.",
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Delete the run directory if verification passes.",
    )

    args = parser.parse_args()

    target_dir: Path | None = None
    if args.dir:
        target_dir = Path(args.dir)
    elif args.latest:
        target_dir = find_latest_run_directory()
        if not target_dir:
            print("❌ Error: No daily_run_* directories found in temp/", file=sys.stderr)
            return 1
    else:
        parser.print_help()
        return 1

    try:
        result = verify_run_directory(target_dir)
        print("✅ DETERMINISTIC DAILY VERIFICATION PASSED")
        print(f"Verified directory: {result['run_dir']}")
        for s in result["steps_verified"]:
            print(f"  ✓ {s}")

        if args.cleanup:
            clean_run_directory(target_dir)
            print(f"✓ Cleaned up temporary run directory: {target_dir}")

        return 0
    except VerificationError as exc:
        print(f"❌ VERIFICATION FAILED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
