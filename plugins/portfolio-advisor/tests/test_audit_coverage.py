#!/usr/bin/env python3
"""
test_audit_coverage.py - Test suite for audit_coverage.py plugin utility.
=========================================================================

Purpose:
    Validates portfolio coverage gap classification across SQLite holdings,
    projections, and watchlist items.

Layer:
    Portfolio Advisor / Tests

Usage Examples:
    pytest plugins/portfolio-advisor/tests/test_audit_coverage.py

Key Functions (Index):
    - test_audit_coverage_classification(tmp_path) -> None

Key Input Dependencies:
    - Temporary SQLite schema mirror of domain_model.sqlite

Key Output Dependencies:
    - None (ephemeral pytest tmp_path fixtures)
"""

import sqlite3
import sys
from pathlib import Path
import pytest

_PLUGIN_ROOT: Path = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PLUGIN_ROOT / "scripts"))

from audit_coverage import audit_portfolio_coverage


# Dual-layer docs: test_audit_coverage_classification test case
def test_audit_coverage_classification(tmp_path: Path) -> None:
    """Verify that tickers are categorized correctly into Tier 1-4 coverage buckets.

    Args:
        tmp_path: Pytest temporary directory fixture.
    """
    db_file = tmp_path / "test_domain_model.sqlite"
    conn = sqlite3.connect(str(db_file))
    conn.execute("""
        CREATE TABLE investment (
            investment_id TEXT PRIMARY KEY,
            symbol TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            lifecycle_status TEXT,
            target_weight REAL,
            pillar_id TEXT,
            sub_strategy_id TEXT,
            is_watchlisted INTEGER DEFAULT 0,
            latest_projection_id TEXT
        );
    """)
    conn.execute("""
        CREATE TABLE investment_price (
            investment_id TEXT PRIMARY KEY,
            price REAL NOT NULL,
            currency TEXT NOT NULL,
            as_of TEXT NOT NULL
        );
    """)
    conn.execute("""
        CREATE TABLE projection_version (
            projection_id TEXT PRIMARY KEY,
            investment_id TEXT,
            version TEXT,
            fair_value REAL,
            action TEXT,
            source TEXT
        );
    """)
    
    # Insert 1 fully analyzed holding (Tier 1)
    conn.execute("INSERT INTO investment VALUES ('NVDA', 'NVDA', 'Nvidia', 'holding', 5.0, 'compute', 'chips', 0, 'NVDA-P1')")
    conn.execute("INSERT INTO investment_price VALUES ('NVDA', 130.0, 'USD', '2026-08-20')")
    conn.execute("INSERT INTO projection_version VALUES ('NVDA-P1', 'NVDA', 'v1', 145.0, 'ACCUMULATE', 'AI_AGENT')")

    # Insert 1 unanalyzed watchlist item (Tier 4 Gap)
    conn.execute("INSERT INTO investment VALUES ('AAPL', 'AAPL', 'Apple', 'watchlist', 0.0, 'compute', 'mobile', 1, NULL)")
    conn.execute("INSERT INTO investment_price VALUES ('AAPL', 0.0, 'USD', '2026-08-20')")
    
    conn.commit()
    conn.close()

    report = audit_portfolio_coverage(db_path=db_file)
    assert report["total_count"] == 2
    assert len(report["fully_analyzed"]) == 1
    assert report["fully_analyzed"][0]["symbol"] == "NVDA"
    assert len(report["needs_analysis"]) == 1
    assert report["needs_analysis"][0]["symbol"] == "AAPL"
