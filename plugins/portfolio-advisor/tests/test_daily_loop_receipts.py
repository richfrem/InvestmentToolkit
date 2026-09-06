"""Tests for daily loop receipt engine and deterministic execution verifier.

Purpose:
    Provides comprehensive adversarial and unit testing for:
    1. Float normalization & deterministic canonical JSON hashing across runs.
    2. UNIQUE index on gate_name and BEGIN IMMEDIATE isolation for monotonic step ordering.
    3. Terminal anchor verification (DAILY_RUN_<run_id>_TERMINAL) rejecting truncated prefix runs.
    4. 4-way bound directory cleanup and process-liveness aware stale run pruning.

Layer:
    plugins/portfolio-advisor/tests (Testing & Verification)
"""

import json
import os
import sqlite3
import pytest
from pathlib import Path
from unittest.mock import patch

from daily_receipts import (
    ensure_receipt_index,
    normalize_numerics,
    canonical_json,
    compute_receipt_hash,
    compute_chain_hash,
    record_daily_receipt,
    record_terminal_receipt,
    MonotonicOrderError,
)
from verify_daily_run import (
    verify_run,
    clean_run_directory,
    prune_stale_runs,
    VerificationError,
    SecurityError,
)


@pytest.fixture
def test_db(tmp_path):
    """Create a temporary SQLite database initialized with verification_receipts table."""
    db_path = tmp_path / "test_control_plane.db"
    con = sqlite3.connect(db_path)
    con.execute("""
        CREATE TABLE verification_receipts (
            receipt_id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL,
            gate_name TEXT NOT NULL,
            command_executed TEXT NOT NULL,
            exit_code INTEGER NOT NULL,
            receipt_token TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    ensure_receipt_index(con)
    con.close()
    return db_path


# --- 1. Deterministic Float Normalization & Canonical JSON ---

def test_float_normalization_and_canonical_json_determinism():
    """Verify that different float representations serialize to identical canonical JSON."""
    payload_a = {
        "price": 123.456,
        "target_weight": 5.0,
        "scores": [0.85, 1.2000000000000002],
        "meta": {"ticker": "AAPL", "null_val": None}
    }
    payload_b = {
        "meta": {"null_val": None, "ticker": "AAPL"},
        "scores": [0.850000, 1.2],
        "target_weight": 5.000,
        "price": 123.456000000001
    }

    norm_a = normalize_numerics(payload_a)
    norm_b = normalize_numerics(payload_b)

    json_a = canonical_json(norm_a)
    json_b = canonical_json(norm_b)

    assert json_a == json_b
    assert compute_receipt_hash(norm_a) == compute_receipt_hash(norm_b)


# --- 2. Database Monotonic Ordering & Unique Index ---

def test_record_daily_receipt_monotonic_and_unique(test_db):
    """Verify that steps must be recorded monotonically and duplicate gate_names fail."""
    run_id = "DAILY-20260906-120000-ABCDEF12"

    # Step 0 succeeds
    p0 = {"status": "COMPLETED", "db_ok": True}
    h0 = record_daily_receipt(test_db, run_id, 0, "READINESS", "COMPLETED", p0)
    assert isinstance(h0, str)

    # Attempting duplicate Step 0 raises MonotonicOrderError or sqlite3.IntegrityError
    with pytest.raises((MonotonicOrderError, sqlite3.IntegrityError)):
        record_daily_receipt(test_db, run_id, 0, "READINESS", "COMPLETED", p0)

    # Directly inserting duplicate gate_name triggers sqlite3.IntegrityError from index
    con = sqlite3.connect(test_db)
    with pytest.raises(sqlite3.IntegrityError):
        con.execute(
            "INSERT INTO verification_receipts (task_id, gate_name, command_executed, exit_code, receipt_token) "
            "VALUES (?, ?, ?, ?, ?)",
            (run_id, f"DAILY_RUN_{run_id}_STEP_0", "cmd", 0, "token")
        )
    con.close()

    # Attempting Step 2 without Step 1 raises MonotonicOrderError
    p2 = {"status": "COMPLETED", "queue": 3}
    with pytest.raises(MonotonicOrderError):
        record_daily_receipt(test_db, run_id, 2, "TRIAGE", "COMPLETED", p2)

    # Step 1 succeeds
    p1 = {"status": "COMPLETED", "macro": "RISK-ON"}
    h1 = record_daily_receipt(test_db, run_id, 1, "BRIEF", "COMPLETED", p1)
    assert isinstance(h1, str)


# --- 3. Terminal Anchor & Chain Truncation Rejection ---

def test_verify_run_scan_mode_success(test_db, tmp_path):
    """Test full valid scan mode run with terminal anchor."""
    run_id = "DAILY-20260906-120000-11112222"
    run_dir = tmp_path / f"daily_run_{run_id}"
    run_dir.mkdir(parents=True)
    (run_dir / "run_manifest.json").write_text(
        json.dumps({"run_id": run_id, "mode": "scan", "pid": os.getpid()})
    )

    # Record Step 0 and Step 1
    h0 = record_daily_receipt(test_db, run_id, 0, "READINESS", "COMPLETED", {"status": "COMPLETED"})
    h1 = record_daily_receipt(test_db, run_id, 1, "BRIEF", "COMPLETED", {"status": "COMPLETED"})

    # Record Terminal Anchor
    record_terminal_receipt(
        test_db, run_id, "scan", "COMPLETED", [0, 1], final_chain_hash=h1
    )

    result = verify_run(run_id, test_db, run_dir)
    assert result["verified"] is True
    assert result["mode"] == "scan"


def test_verify_run_rejects_truncated_prefix(test_db, tmp_path):
    """A valid prefix of steps without the terminal anchor is rejected."""
    run_id = "DAILY-20260906-120000-TRUNCATED"
    run_dir = tmp_path / f"daily_run_{run_id}"
    run_dir.mkdir(parents=True)
    (run_dir / "run_manifest.json").write_text(
        json.dumps({"run_id": run_id, "mode": "interactive", "pid": os.getpid()})
    )

    # Only record Steps 0, 1, 2
    record_daily_receipt(test_db, run_id, 0, "READINESS", "COMPLETED", {"status": "COMPLETED"})
    record_daily_receipt(test_db, run_id, 1, "BRIEF", "COMPLETED", {"status": "COMPLETED"})
    record_daily_receipt(test_db, run_id, 2, "TRIAGE", "COMPLETED", {"status": "COMPLETED"})

    # Verifier must reject truncated run
    with pytest.raises(VerificationError, match="Missing terminal anchor"):
        verify_run(run_id, test_db, run_dir)


# --- 4. Cleanup & Janitor Security ---

def test_clean_run_directory_rejects_symlink(tmp_path, test_db):
    """Ensure that passing a symlink to clean_run_directory is rejected on unresolved path."""
    real_dir = tmp_path / "real_dir"
    real_dir.mkdir()
    sym_dir = tmp_path / "sym_link_dir"
    sym_dir.symlink_to(real_dir)

    with pytest.raises(SecurityError, match="Symlinks rejected"):
        clean_run_directory(sym_dir, "SOME-RUN-ID", test_db)


def test_prune_stale_runs_protects_live_pid(tmp_path, test_db):
    """Janitor must not delete directory if the process PID is still active."""
    run_id = "DAILY-20260906-STALE-CHECK"
    stale_dir = tmp_path / f"daily_run_{run_id}"
    stale_dir.mkdir()
    # Write current live test process PID
    (stale_dir / "run_manifest.json").write_text(
        json.dumps({"run_id": run_id, "pid": os.getpid()})
    )

    pruned = prune_stale_runs(tmp_path, test_db, older_than_days=0)
    assert pruned == 0
    assert stale_dir.exists()
