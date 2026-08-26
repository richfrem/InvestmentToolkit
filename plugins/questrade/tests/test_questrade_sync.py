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
    """Verify that Questrade accounts, balances, and holdings upsert correctly."""
    conn = setup_in_memory_db()

    accounts_payload = [
        {"type": "TFSA", "number": "53408189", "status": "Active", "isPrimary": True},
        {"type": "RRSP", "number": "53408195", "status": "Active", "isPrimary": False},
    ]

    balances_payload = {
        "53408189": {
            "totalEquityUSD": 21850.0,
            "totalEquityCAD": 29500.0,
            "cashUSD": 3317.07,
            "cashCAD": 150.00,
            "marketValueUSD": 18532.93,
        }
    }

    positions_payload = {
        "53408189": [
            {
                "symbol": "BTDR",
                "openQuantity": 23.0,
                "avgPrice": 11.10,
                "currentPrice": 12.50,
            }
        ]
    }

    written = persist_questrade_data_to_db(
        conn=conn,
        accounts=accounts_payload,
        balances=balances_payload,
        positions=positions_payload,
    )

    assert written >= 1, "Expected at least 1 position written"

    # Verify accounts table
    accs = list_accounts(conn)
    assert len(accs) == 2
    assert any(a["account_id"] == "53408189" for a in accs)

    # Verify account_investment table (BTDR + CASH_USD cash row)
    pos = list_account_investments(conn, account_id="53408189")
    assert len(pos) == 2, f"Expected 2 holdings (BTDR + CASH_USD), found: {pos}"
    
    btdr_row = next(r for r in pos if r["investment_id"] == "BTDR")
    assert btdr_row["quantity"] == 23.0
    assert btdr_row["average_cost"] == 11.10

    cash_row = next(r for r in pos if r["investment_id"] == "CASH_USD")
    assert cash_row["quantity"] == 3317.07
    assert cash_row["average_cost"] == 1.0

    print("✓ test_sync_accounts_and_positions passed!")


if __name__ == "__main__":
    test_sync_accounts_and_positions()
