"""Deterministic receipt and hash-chaining engine for daily operations.

Purpose:
    Provides canonical JSON serialization with float normalization, SHA-256
    hash-chaining, monotonic step validation under BEGIN IMMEDIATE SQLite
    transactions, and database-level uniqueness enforcement for daily execution receipts.

Layer:
    plugins/portfolio-advisor/scripts (Execution & Audit Engine)

Key Functions:
    - ensure_receipt_index(con): Creates UNIQUE index on verification_receipts(gate_name).
    - normalize_numerics(payload): Recursively converts floats to fixed-precision strings.
    - canonical_json(data): Deterministic JSON serialization.
    - compute_receipt_hash(payload): SHA-256 hash of normalized canonical JSON.
    - compute_chain_hash(prev_hash, receipt_hash): Cryptographic hash accumulator.
    - record_daily_receipt(db_path, run_id, step_num, step_name, status, payload):
        Atomic monotonic step insertion.
    - record_terminal_receipt(db_path, run_id, mode, state, required_steps, final_chain_hash):
        Atomic terminal anchor insertion.
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import sqlite3
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional


class MonotonicOrderError(Exception):
    """Raised when step insertion violates strict monotonic ordering."""


class ReceiptError(Exception):
    """Raised for general receipt engine failures."""


def generate_run_id() -> str:
    """Generate a control-plane owned unique run identifier."""
    now_str = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    rand_hex = secrets.token_hex(4).upper()
    return f"DAILY-{now_str}-{rand_hex}"


def ensure_receipt_index(con: sqlite3.Connection) -> None:
    """Ensure unique index on verification_receipts(gate_name) exists."""
    con.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_verification_receipts_gate_name "
        "ON verification_receipts(gate_name)"
    )


def normalize_numerics(obj: Any) -> Any:
    """Recursively convert float values to fixed-precision strings for cross-platform determinism."""
    if isinstance(obj, float):
        return f"{obj:.4f}"
    elif isinstance(obj, Decimal):
        return f"{obj:.4f}"
    elif isinstance(obj, dict):
        return {k: normalize_numerics(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [normalize_numerics(v) for v in obj]
    return obj


def canonical_json(data: Any) -> str:
    """Serialize data into deterministic, canonical JSON."""
    return json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def compute_receipt_hash(payload: Dict[str, Any]) -> str:
    """Compute SHA-256 hash of canonical JSON normalized payload."""
    normalized = normalize_numerics(payload)
    canonical = canonical_json(normalized)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def compute_chain_hash(prev_chain_hash: str, receipt_hash: str) -> str:
    """Compute chained accumulator hash: SHA256(prev_chain_hash + ':' + receipt_hash)."""
    combined = f"{prev_chain_hash}:{receipt_hash}"
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


def record_daily_receipt(
    db_path: Path | str,
    run_id: str,
    step_num: int,
    step_name: str,
    status: str,
    payload: Dict[str, Any],
    correlation_id: Optional[str] = None,
) -> str:
    """Record a daily step receipt under BEGIN IMMEDIATE transaction isolation."""
    con = sqlite3.connect(str(db_path), isolation_level=None)
    try:
        ensure_receipt_index(con)
        con.execute("BEGIN IMMEDIATE")

        # Query existing steps for this run to enforce monotonic order & retrieve previous hash
        cur = con.cursor()
        cur.execute(
            "SELECT receipt_token FROM verification_receipts "
            "WHERE gate_name LIKE ? ORDER BY receipt_id ASC",
            (f"DAILY_RUN_{run_id}_STEP_%",),
        )
        existing_rows = cur.fetchall()

        if not existing_rows:
            if step_num != 0:
                raise MonotonicOrderError(
                    f"First step must be 0 (Readiness), got step {step_num}"
                )
            prev_chain_hash = hashlib.sha256(run_id.encode("utf-8")).hexdigest()
        else:
            last_token_str = existing_rows[-1][0]
            try:
                last_envelope = json.loads(last_token_str)
                last_step = int(last_envelope["step_num"])
                prev_chain_hash = last_envelope["chain_hash"]
            except Exception as e:
                raise ReceiptError(f"Corrupt previous receipt token: {e}") from e

            expected_step = last_step + 1
            if step_num != expected_step:
                raise MonotonicOrderError(
                    f"Expected step {expected_step}, got step {step_num} (monotonic violation)"
                )

        receipt_hash = compute_receipt_hash(payload)
        chain_hash = compute_chain_hash(prev_chain_hash, receipt_hash)

        envelope = {
            "run_id": run_id,
            "correlation_id": correlation_id,
            "step_num": step_num,
            "step_name": step_name,
            "status": status,
            "prev_chain_hash": prev_chain_hash,
            "receipt_hash": receipt_hash,
            "chain_hash": chain_hash,
            "payload": normalize_numerics(payload),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        gate_name = f"DAILY_RUN_{run_id}_STEP_{step_num}"
        receipt_token = canonical_json(envelope)

        cur.execute(
            "INSERT INTO verification_receipts "
            "(task_id, gate_name, command_executed, exit_code, receipt_token) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                run_id,
                gate_name,
                f"step_{step_num}_{step_name.lower()}",
                0 if status == "COMPLETED" else 1,
                receipt_token,
            ),
        )
        con.execute("COMMIT")
        return chain_hash
    except Exception:
        con.execute("ROLLBACK")
        raise
    finally:
        con.close()


def record_terminal_receipt(
    db_path: Path | str,
    run_id: str,
    mode: str,
    state: str,
    required_steps: List[int],
    final_chain_hash: str,
    error_msg: Optional[str] = None,
    correlation_id: Optional[str] = None,
) -> str:
    """Record terminal anchor receipt for a daily run under BEGIN IMMEDIATE."""
    con = sqlite3.connect(str(db_path), isolation_level=None)
    try:
        ensure_receipt_index(con)
        con.execute("BEGIN IMMEDIATE")

        gate_name = f"DAILY_RUN_{run_id}_TERMINAL"
        envelope = {
            "run_id": run_id,
            "correlation_id": correlation_id,
            "mode": mode,
            "terminal_state": state,
            "required_steps": required_steps,
            "final_chain_hash": final_chain_hash,
            "error_msg": error_msg,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        receipt_token = canonical_json(envelope)
        cur = con.cursor()
        cur.execute(
            "INSERT INTO verification_receipts "
            "(task_id, gate_name, command_executed, exit_code, receipt_token) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                run_id,
                gate_name,
                "daily_run_finalize",
                0 if state == "COMPLETED" else 1,
                receipt_token,
            ),
        )
        con.execute("COMMIT")
        return receipt_token
    except Exception:
        con.execute("ROLLBACK")
        raise
    finally:
        con.close()
