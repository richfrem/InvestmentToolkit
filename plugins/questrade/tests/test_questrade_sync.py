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
    - test_sync_uses_canonical_account_ids_not_questrade_uuid()
    - test_resync_does_not_duplicate_rows()
    - test_resync_removes_stale_sold_position()
    - test_broker_reported_total_aggregates_across_accounts()

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
from domain_model.broker_reported_total_repository import get_broker_reported_total

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

    # Verify accounts table — canonical account_id ("TFSA"), not the Questrade uuid
    accs = list_accounts(conn)
    assert len(accs) == 2
    tfsa_row = next(a for a in accs if a["account_id"] == "TFSA")
    assert tfsa_row["account_type"] == "TFSA"

    # Verify account_investment table (BTDR + CASH_USD cash row), keyed "TFSA"
    pos = list_account_investments(conn, account_id="TFSA")
    assert len(pos) == 2, f"Expected 2 holdings (BTDR + CASH_USD), found: {pos}"

    btdr_row = next(r for r in pos if r["investment_id"] == "BTDR")
    assert btdr_row["quantity"] == 23.0
    assert btdr_row["average_cost"] == 11.10

    cash_row = next(r for r in pos if r["investment_id"] == "CASH_USD")
    assert cash_row["quantity"] == 3317.07, "Expected '$3,317.07' string parsed to float 3317.07"
    assert cash_row["average_cost"] == 1.0

    print("✓ test_sync_accounts_and_positions passed!")


def test_sync_uses_canonical_account_ids_not_questrade_uuid():
    """Guards against the 2026-08-26 duplication bug: syncing must converge onto
    the SAME account_id another broker sync (TradingView) would use, not fork a
    parallel uuid-keyed row set for the same real account."""
    conn = setup_in_memory_db()
    tfsa_id = "91484e92-b210-49d2-0afe-184f9d0a1f28"

    persist_questrade_data_to_db(
        conn=conn,
        accounts=[{"id": tfsa_id, "name": "TFSA - 53408189", "productType": "SD", "supportTrading": True}],
        balances={tfsa_id: {"totalEquity": {"combinedCad": "$100.00", "combinedUsd": "$70.00"}, "cash": {"usd": "$10.00"}}},
        positions={tfsa_id: [{"instrument": "AAPL", "qty": 1, "avgPrice": 200.0}]},
    )

    accs = list_accounts(conn)
    account_ids = {a["account_id"] for a in accs}
    assert tfsa_id not in account_ids, f"Questrade uuid {tfsa_id} must not be used as account_id"
    assert "TFSA" in account_ids

    print("✓ test_sync_uses_canonical_account_ids_not_questrade_uuid passed!")


def test_resync_does_not_duplicate_rows():
    """Re-running a sync with unchanged data must update in place, not add rows —
    the exact failure mode that produced 2 rows per symbol in production."""
    conn = setup_in_memory_db()
    tfsa_id = "91484e92-b210-49d2-0afe-184f9d0a1f28"
    accounts = [{"id": tfsa_id, "name": "TFSA - 53408189", "productType": "SD", "supportTrading": True}]
    balances = {tfsa_id: {"totalEquity": {"combinedCad": "$100.00", "combinedUsd": "$70.00"}, "cash": {"usd": "$10.00"}}}
    positions = {tfsa_id: [{"instrument": "BTDR", "qty": 22.0, "avgPrice": 11.16}]}

    persist_questrade_data_to_db(conn=conn, accounts=accounts, balances=balances, positions=positions)
    persist_questrade_data_to_db(conn=conn, accounts=accounts, balances=balances, positions=positions)

    pos = list_account_investments(conn, account_id="TFSA")
    assert len(pos) == 2, f"Expected exactly 2 rows (BTDR + CASH_USD) after 2 syncs, found: {pos}"
    assert len([p for p in pos if p["investment_id"] == "BTDR"]) == 1

    print("✓ test_resync_does_not_duplicate_rows passed!")


def test_resync_removes_stale_sold_position():
    """A position dropped from the live payload (fully sold) must be removed,
    not left behind as a stale row overstating holdings."""
    conn = setup_in_memory_db()
    tfsa_id = "91484e92-b210-49d2-0afe-184f9d0a1f28"
    accounts = [{"id": tfsa_id, "name": "TFSA - 53408189", "productType": "SD", "supportTrading": True}]
    balances = {tfsa_id: {"totalEquity": {"combinedCad": "$100.00", "combinedUsd": "$70.00"}, "cash": {"usd": "$10.00"}}}

    persist_questrade_data_to_db(
        conn=conn, accounts=accounts, balances=balances,
        positions={tfsa_id: [{"instrument": "BTDR", "qty": 22.0, "avgPrice": 11.16}, {"instrument": "RIOT", "qty": 24.0, "avgPrice": 19.22}]},
    )
    # BTDR fully sold — absent from this sync's positions
    persist_questrade_data_to_db(
        conn=conn, accounts=accounts, balances=balances,
        positions={tfsa_id: [{"instrument": "RIOT", "qty": 24.0, "avgPrice": 19.22}]},
    )

    pos = list_account_investments(conn, account_id="TFSA")
    symbols = {p["investment_id"] for p in pos}
    assert "BTDR" not in symbols, f"Sold position BTDR should have been removed, found: {pos}"
    assert "RIOT" in symbols

    print("✓ test_resync_removes_stale_sold_position passed!")


def test_broker_reported_total_aggregates_across_accounts():
    """broker_reported_total is a single-row table (id=1) meant to hold the
    COMBINED portfolio total. A prior version called upsert once per account,
    silently overwriting itself down to just the last account processed."""
    conn = setup_in_memory_db()
    tfsa_id = "91484e92-b210-49d2-0afe-184f9d0a1f28"
    rrsp_id = "a35aef24-2e61-4202-079c-0d026087293a"

    persist_questrade_data_to_db(
        conn=conn,
        accounts=[
            {"id": tfsa_id, "name": "TFSA - 53408189", "productType": "SD", "supportTrading": True},
            {"id": rrsp_id, "name": "RRSP - 53408195", "productType": "SD", "supportTrading": True},
        ],
        balances={
            tfsa_id: {"totalEquity": {"combinedCad": "$30,000.00", "combinedUsd": "$21,900.00"}, "cash": {"usd": "$3,300.00"}},
            rrsp_id: {"totalEquity": {"combinedCad": "$14,000.00", "combinedUsd": "$10,100.00"}, "cash": {"usd": "$1,000.00"}},
        },
        positions={tfsa_id: [], rrsp_id: []},
    )

    total = get_broker_reported_total(conn)
    assert total is not None
    assert total["total_usd"] == 21900.00 + 10100.00, f"Expected combined total, got: {total}"
    assert total["total_cad"] == 30000.00 + 14000.00

    print("✓ test_broker_reported_total_aggregates_across_accounts passed!")


if __name__ == "__main__":
    test_sync_accounts_and_positions()
    test_sync_uses_canonical_account_ids_not_questrade_uuid()
    test_resync_does_not_duplicate_rows()
    test_resync_removes_stale_sold_position()
    test_broker_reported_total_aggregates_across_accounts()
