#!/usr/bin/env python3
"""
Tests for the stock_intake_persist.py CLI: happy path, transactional atomicity,
and foreign-key fallback.

Every test runs the CLI against a throwaway database passed via --db-path.
The CLI's default target is the real, gitignored domain_model.sqlite, so a
test that omits --db-path overwrites real holdings data (this happened: INTC
and BE rows were clobbered by an earlier version of this file).
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent
_BACKEND = _HERE.parent.parent
sys.path.insert(0, str(_BACKEND / "py_services"))

from domain_model.db_client import initialize_db
from domain_model.investment_repository import get_investment, resolve_investment, update_investment_fields
from domain_model.pillar_repository import resolve_pillar, resolve_sub_strategy

_SCRIPT = _BACKEND / "py_services" / "stock_intake_persist.py"
_REAL_DB = _BACKEND / "data" / "domain_model.sqlite"


@pytest.fixture
def db_path(tmp_path) -> str:
    """A real-schema domain_model.sqlite seeded with the pillars and holdings the tests use."""
    path = str(tmp_path / "domain_model.sqlite")
    conn = initialize_db(path)
    for pillar_id in ("compute", "power", "other"):
        resolve_pillar(conn, pillar_id, pillar_id.title())
    resolve_sub_strategy(conn, "power-infrastructure", "power", "Power Infrastructure")
    for symbol in ("INTC", "BE"):
        resolve_investment(conn, symbol)
    update_investment_fields(
        conn, "INTC", target_weight=1.5, standing_decision_reason="Original reason",
    )
    update_investment_fields(
        conn, "BE", pillar_id="power", sub_strategy_id="power-infrastructure",
    )
    conn.commit()
    conn.close()
    return path


def _run(payload: dict, db_path: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(_SCRIPT), "--payload", json.dumps(payload), "--json", "--db-path", db_path],
        capture_output=True,
        text=True,
        cwd=str(_BACKEND.parent),
    )


def _investment(db_path: str, symbol: str) -> dict:
    conn = initialize_db(db_path)
    try:
        return get_investment(conn, symbol)
    finally:
        conn.close()


def _real_db_state():
    return (_REAL_DB.stat().st_mtime, _REAL_DB.stat().st_size) if _REAL_DB.exists() else None


def test_stock_intake_persist_cli(db_path):
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
    real_before = _real_db_state()

    res = _run(payload, db_path)

    assert res.returncode == 0, f"Script failed: {res.stderr}"
    data = json.loads(res.stdout)
    assert data["status"] == "success"
    assert data["symbol"] == "INTC"
    row = _investment(db_path, "INTC")
    assert row["target_weight"] == 2.0
    assert row["pillar_id"] == "compute"
    assert _real_db_state() == real_before, "the real domain_model.sqlite must not be touched"


def test_stock_intake_persist_transactional_rollback_on_failure(db_path):
    """Negative-path test proving BEGIN IMMEDIATE atomicity:
    When investment fields update succeeds but price_levels insertion throws,
    the transaction rolls back and investment table is NOT mutated.
    """
    # Valid investment fields, but invalid price_levels (buy_tiers not a list)
    failing_payload = {
        "symbol": "INTC",
        "target_weight": 99.9,
        "standing_decision_reason": "SHOULD_BE_ROLLED_BACK_BECAUSE_OF_FAILING_PRICE_LEVELS",
        "price_levels": {
            "buy_tiers": "INVALID_NON_ITERABLE_DATA_CAUSING_REPLACE_PRICE_LEVELS_TO_THROW"
        }
    }

    res = _run(failing_payload, db_path)

    # Script MUST exit with non-zero code on failure
    assert res.returncode != 0, f"Script should have failed but exited 0: {res.stdout}"
    row = _investment(db_path, "INTC")
    assert row["standing_decision_reason"] == "Original reason", "Rollback failed! Reason was mutated"
    assert row["target_weight"] == 1.5, "Rollback failed! Weight was mutated"


def test_stock_intake_persist_foreign_key_validation_and_inheritance(db_path):
    """Verify that invalid pillar/sub-strategy foreign keys do not cause crash,
    and instead inherit valid existing database records or default gracefully.
    """
    payload = {
        "symbol": "BE",
        "pillar_id": "invalid_test_pillar_id_that_does_not_exist",
        "sub_strategy_id": "invalid_test_sub_strategy_id_that_does_not_exist",
        "agent_rationale": "Automated regression test for FK fallback"
    }

    res = _run(payload, db_path)

    assert res.returncode == 0, f"FK validation test failed: {res.stderr}"
    data = json.loads(res.stdout)
    assert data["status"] == "success"
    assert data["symbol"] == "BE"
    row = _investment(db_path, "BE")
    assert row["pillar_id"] == "power"
    assert row["sub_strategy_id"] == "power-infrastructure"
