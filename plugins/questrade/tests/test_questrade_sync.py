#!/usr/bin/env python3
"""
test_questrade_sync.py - Unit tests for Questrade SQLite sync service.

Purpose:
    Validates that Questrade MCP account, balance, and position payloads correctly
    upsert into domain_model.sqlite tables (account, account_investment) and
    preserve the Mandatory Cash Invariant (Rule #18).

Layer:
    Testing / Plugins / Questrade

Usage Examples:
    pytest plugins/questrade/tests/test_questrade_sync.py
    python3 plugins/questrade/tests/test_questrade_sync.py

Key Functions (Index):
    - test_sync_accounts_and_positions()
    - test_cash_invariant_preserved()

Key Input Dependencies:
    - plugins/questrade/scripts/questrade_sync.py
"""

import sys
import sqlite3
from pathlib import Path

# Add repo and py_services to path
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))
sys.path.insert(0, str(REPO_ROOT / "plugins/questrade/scripts"))

from domain_model.db_client import initialize_db
from domain_model.account_investment_repository import list_account_investments
from domain_model.account_repository import list_accounts

# Import sync functions from questrade_sync
from questrade_sync import persist_questrade_data_to_db


def setup_in_memory_db() -> sqlite3.Connection:
    """Create in-memory SQLite db with full domain model schema."""
    return initialize_db(":memory:")


def test_sync_accounts_and_positions():
    """Verify that Questrade accounts, balances, and holdings upsert correctly.

    Fixtures mirror the REAL live MCP response shapes captured in
    plugins/questrade/references/questrade-tool-schemas.md:
    - list_accounts: [{id, name, productType, supportTrading}] — no separate
      type/number fields, both embedded in `name`.
    - get_balances: balances.cash / balances.totalEquity are
      {cad, usd, combinedCad, combinedUsd} formatted currency STRINGS.
    - get_positions: [{id, instrument, qty, side, avgPrice}].
    """
    conn = setup_in_memory_db()

    tfsa_id = "91484e92-b210-49d2-0afe-184f9d0a1f28"

    accounts_payload = [
        {"id": tfsa_id, "name": "TFSA - 53408189", "productType": "SD", "supportTrading": True},
        {"id": "a35aef24-2e61-4202-079c-0d026087293a", "name": "RRSP - 53408195", "productType": "SD", "supportTrading": True},
    ]

    balances_payload = {
        tfsa_id: {
            "totalEquity": {"cad": "$0.50", "usd": "$21,872.55", "combinedCad": "$30,269.92", "combinedUsd": "$21,872.91"},
            "cash": {"cad": "$0.50", "usd": "$3,317.07", "combinedCad": "$4,591.00", "combinedUsd": "$3,317.43"},
        }
    }

    positions_payload = {
        tfsa_id: [
            {"id": "755a2840-2465-4542-0bf5-c99d111b0f44", "instrument": "BTDR", "qty": 23.0, "side": "buy", "avgPrice": 11.10}
        ]
    }

    written = persist_questrade_data_to_db(
        conn=conn,
        accounts=accounts_payload,
        balances=balances_payload,
        positions=positions_payload,
    )

    assert written >= 1, "Expected at least 1 position written"

    # Verify accounts table — type/number parsed out of "name"
    accs = list_accounts(conn)
    assert len(accs) == 2
    tfsa_row = next(a for a in accs if a["account_id"] == tfsa_id)
    assert tfsa_row["account_type"] == "TFSA"

    # Verify account_investment table (BTDR + CASH_USD cash row)
    pos = list_account_investments(conn, account_id=tfsa_id)
    assert len(pos) == 2, f"Expected 2 holdings (BTDR + CASH_USD), found: {pos}"

    btdr_row = next(r for r in pos if r["investment_id"] == "BTDR")
    assert btdr_row["quantity"] == 23.0
    assert btdr_row["average_cost"] == 11.10

    cash_row = next(r for r in pos if r["investment_id"] == "CASH_USD")
    assert cash_row["quantity"] == 3317.07, "Expected '$3,317.07' string parsed to float 3317.07"
    assert cash_row["average_cost"] == 1.0

    print("✓ test_sync_accounts_and_positions passed!")


if __name__ == "__main__":
    test_sync_accounts_and_positions()
