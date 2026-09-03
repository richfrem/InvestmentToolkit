#!/usr/bin/env python3
"""
test_target_weight_invariant.py
===============================
Test that verify_portfolio_invariants.py enforces the 100% Target Weight Invariant.
Asserts that check_target_weight_invariant passes when sum == 100.0% (+/- 0.05%),
and fails with clear diagnostics when sum != 100%.
"""

import sqlite3
import pytest
from investment_screener.backend.py_services.verify_portfolio_invariants import check_target_weight_invariant


def test_target_weight_invariant_passes_on_100_percent():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE investment (
            investment_id TEXT PRIMARY KEY,
            symbol TEXT NOT NULL,
            target_weight REAL DEFAULT 0.0
        );
    """)
    conn.execute("INSERT INTO investment (investment_id, symbol, target_weight) VALUES ('1', 'AAPL', 50.0);")
    conn.execute("INSERT INTO investment (investment_id, symbol, target_weight) VALUES ('2', 'MSFT', 50.0);")
    conn.commit()

    res = check_target_weight_invariant(conn)
    assert res["passed"] is True
    assert res["check"] == "TARGET_WEIGHT_INVARIANT"
    assert abs(res["total_target_pct"] - 100.0) < 0.05
    conn.close()


def test_target_weight_invariant_fails_when_drifted():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE investment (
            investment_id TEXT PRIMARY KEY,
            symbol TEXT NOT NULL,
            target_weight REAL DEFAULT 0.0
        );
    """)
    conn.execute("INSERT INTO investment (investment_id, symbol, target_weight) VALUES ('1', 'AAPL', 50.0);")
    conn.execute("INSERT INTO investment (investment_id, symbol, target_weight) VALUES ('2', 'MSFT', 59.5);")
    conn.commit()

    res = check_target_weight_invariant(conn)
    assert res["passed"] is False
    assert res["check"] == "TARGET_WEIGHT_INVARIANT"
    assert res["total_target_pct"] == 109.5
    assert "exceeds 100%" in res["message"] or "Drift" in res["message"]
    conn.close()
