"""Tests for verify_daily_run.py.

Validates deterministic verification of the daily loop checklist execution,
including required step artifacts, step validation rules, and cleanup.
"""

import json
import pytest
from pathlib import Path
from datetime import date

import sys
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "plugins/portfolio-advisor/scripts"))

from verify_daily_run import (
    REQUIRED_STEPS,
    verify_run_directory,
    clean_run_directory,
    VerificationError,
)


def _seed_valid_step_artifacts(run_dir: Path):
    """Populate run_dir with valid step artifact files for all required steps."""
    run_dir.mkdir(parents=True, exist_ok=True)
    today_str = date.today().isoformat()

    # Step 0: Readiness
    (run_dir / "step0_readiness.json").write_text(
        json.dumps({
            "step": 0,
            "status": "COMPLETED",
            "server_running": True,
            "domain_db_verified": True,
            "tv_snapshot_positions": 27,
            "timestamp": f"{today_str}T08:00:00Z"
        })
    )

    # Step 1: Morning Brief
    (run_dir / "step1_brief.json").write_text(
        json.dumps({
            "step": 1,
            "status": "COMPLETED",
            "date": today_str,
            "macro_regime": "RISK-ON",
            "conviction_scores_count": 27,
            "timestamp": f"{today_str}T08:01:00Z"
        })
    )

    # Step 2: Triage
    (run_dir / "step2_triage.json").write_text(
        json.dumps({
            "step": 2,
            "status": "COMPLETED",
            "queue_length": 5,
            "confluence_verified": True,
            "timestamp": f"{today_str}T08:02:00Z"
        })
    )

    # Step 3: Action Cards
    (run_dir / "step3_actions.json").write_text(
        json.dumps({
            "step": 3,
            "status": "COMPLETED",
            "cards_presented": 5,
            "actions_executed": 2,
            "actions_deferred": 3,
            "timestamp": f"{today_str}T08:03:00Z"
        })
    )

    # Step 4: Evolution
    (run_dir / "step4_evolution.json").write_text(
        json.dumps({
            "step": 4,
            "status": "COMPLETED",
            "evolution_logged": True,
            "triage_history_updated": True,
            "timestamp": f"{today_str}T08:04:00Z"
        })
    )

    # Step 5: Summary
    (run_dir / "step5_summary.json").write_text(
        json.dumps({
            "step": 5,
            "status": "COMPLETED",
            "reviewed_holdings": 27,
            "acted_trades": 2,
            "timestamp": f"{today_str}T08:05:00Z"
        })
    )


def test_verify_run_directory_success(tmp_path):
    run_dir = tmp_path / "daily_run_test"
    _seed_valid_step_artifacts(run_dir)

    result = verify_run_directory(run_dir)
    assert result["verified"] is True
    assert len(result["steps_verified"]) == len(REQUIRED_STEPS)


def test_verify_run_directory_missing_step(tmp_path):
    run_dir = tmp_path / "daily_run_test"
    _seed_valid_step_artifacts(run_dir)
    # Remove step 4
    (run_dir / "step4_evolution.json").unlink()

    with pytest.raises(VerificationError, match="Missing required step artifact: step4_evolution.json"):
        verify_run_directory(run_dir)


def test_verify_run_directory_invalid_status(tmp_path):
    run_dir = tmp_path / "daily_run_test"
    _seed_valid_step_artifacts(run_dir)
    # Mark step 2 as INCOMPLETE
    (run_dir / "step2_triage.json").write_text(
        json.dumps({"step": 2, "status": "FAILED"})
    )

    with pytest.raises(VerificationError, match="Step 2 status is 'FAILED', expected 'COMPLETED'"):
        verify_run_directory(run_dir)


def test_clean_run_directory(tmp_path):
    run_dir = tmp_path / "daily_run_test"
    _seed_valid_step_artifacts(run_dir)

    assert run_dir.exists()
    clean_run_directory(run_dir)
    assert not run_dir.exists()
