#!/usr/bin/env python3
"""
Unit test for stock_intake_persist.py CLI tool proving transactional atomicity & happy path.
"""
import json
import subprocess
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_BACKEND = _HERE.parent.parent
sys.path.insert(0, str(_BACKEND / "py_services"))

from domain_model.db_client import initialize_db

def test_stock_intake_persist_cli():
    repo_root = _BACKEND.parent
    script = _BACKEND / "py_services" / "stock_intake_persist.py"
    
    payload = {
        "symbol": "INTC",
        "target_weight": 2.0,
        "pillar_id": "compute",
        "lifecycle_status": "accumulate",
        "target_action": "ACCUMULATE",
        "standing_decision_type": "ACCUMULATE_SOVEREIGN_FOUNDRY",
        "standing_decision_reason": "18A yield inflection + High-NA EUV first-mover.",
        "standing_decision_source": "Grok sweep 2026-08-25",
        "standing_decision_review": "Quarterly 14A PDK milestone review.",
        "agent_rationale": "Position re-opened with Option A.",
        "price_levels": {
            "target_entry_price": 88.45,
            "buy_tiers": [{"tier": 1, "price": 78.67, "action": "PRIMARY_BUY", "basis": "200 EMA"}],
            "sell_tiers": [
                {"tier": 1, "price": 101.72, "action": "TRIM_1", "trimPct": 33.0, "basis": "50 EMA"},
                {"tier": 2, "price": 114.99, "action": "TRIM_2", "trimPct": 50.0, "basis": "FV Highs"}
            ],
            "stop_loss": {"price": 72.37, "basis": "Stop Loss below 200 EMA"}
        }
    }
    
    res = subprocess.run(
        [sys.executable, str(script), "--payload", json.dumps(payload), "--json"],
        capture_output=True,
        text=True,
        cwd=str(repo_root)
    )
    assert res.returncode == 0, f"Script failed: {res.stderr}"
    data = json.loads(res.stdout)
    assert data["status"] == "success"
    assert data["symbol"] == "INTC"

def test_stock_intake_persist_transactional_rollback_on_failure():
    """Negative-path test proving BEGIN IMMEDIATE atomicity:
    When investment fields update succeeds but price_levels insertion throws,
    the transaction rolls back and investment table is NOT mutated.
    """
    repo_root = _BACKEND.parent
    script = _BACKEND / "py_services" / "stock_intake_persist.py"
    db_path = str(_BACKEND / "data" / "domain_model.sqlite")

    # Read current state of INTC in DB before test
    conn = initialize_db(db_path)
    cur = conn.execute("SELECT standing_decision_reason, target_weight FROM investment WHERE symbol = 'INTC';")
    original_row = cur.fetchone()
    conn.close()

    original_reason = original_row[0] if original_row else None
    original_weight = original_row[1] if original_row else None

    # Construct failing payload: valid investment fields, but invalid price_levels (buy_tiers not a list)
    failing_payload = {
        "symbol": "INTC",
        "target_weight": 99.9,
        "standing_decision_reason": "SHOULD_BE_ROLLED_BACK_BECAUSE_OF_FAILING_PRICE_LEVELS",
        "price_levels": {
            "buy_tiers": "INVALID_NON_ITERABLE_DATA_CAUSING_REPLACE_PRICE_LEVELS_TO_THROW"
        }
    }

    res = subprocess.run(
        [sys.executable, str(script), "--payload", json.dumps(failing_payload), "--json"],
        capture_output=True,
        text=True,
        cwd=str(repo_root)
    )

    # Script MUST exit with non-zero code on failure
    assert res.returncode != 0, f"Script should have failed but exited 0: {res.stdout}"

    # Re-query SQLite directly to assert transaction rolled back completely
    conn = initialize_db(db_path)
    cur = conn.execute("SELECT standing_decision_reason, target_weight FROM investment WHERE symbol = 'INTC';")
    after_row = cur.fetchone()
    conn.close()

    assert after_row[0] == original_reason, f"Rollback failed! Reason was mutated to {after_row[0]}"
    assert after_row[1] == original_weight, f"Rollback failed! Weight was mutated to {after_row[1]}"

if __name__ == "__main__":
    test_stock_intake_persist_cli()
    test_stock_intake_persist_transactional_rollback_on_failure()
    print("test_stock_intake_persist tests PASSED")
