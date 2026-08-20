#!/usr/bin/env python3
"""
test_manage_watchlist.py - Test suite for manage_watchlist.py utility.
======================================================================

Purpose:
    Validates unit contracts and SQLite persistence behaviors for manage_watchlist.py,
    including adding, updating, removing, and querying watchlisted equities.

Layer:
    Backend / Tests / py_services

Usage Examples:
    pytest investment_screener/backend/tests/py_services/test_manage_watchlist.py

Key Functions (Index):
    - test_db(tmp_path) -> str
    - test_add_and_list_watchlist(test_db) -> None
    - test_remove_from_watchlist(test_db) -> None

Key Input Dependencies:
    - Temporary SQLite schema mirror of domain_model.sqlite

Key Output Dependencies:
    - None (ephemeral pytest tmp_path fixtures)
"""

import sqlite3
import sys
from pathlib import Path
from typing import Generator
import pytest

_PY_SERVICES: Path = Path(__file__).resolve().parents[2] / "py_services"
sys.path.insert(0, str(_PY_SERVICES))

from manage_watchlist import (
    add_to_watchlist,
    remove_from_watchlist,
    get_watchlist_items,
)


# Dual-layer docs: test_db fixture
@pytest.fixture
def test_db(tmp_path: Path) -> str:
    """Create a temporary mock domain_model.sqlite schema for test isolation.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        str: Absolute path string to the ephemeral SQLite database.
    """
    db_file = tmp_path / "test_domain_model.sqlite"
    conn = sqlite3.connect(str(db_file))
    conn.execute("""
        CREATE TABLE strategy_pillar (
            pillar_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            target_weight REAL
        );
    """)
    conn.execute("""
        CREATE TABLE sub_strategy (
            sub_strategy_id TEXT PRIMARY KEY,
            pillar_id TEXT,
            name TEXT NOT NULL
        );
    """)
    conn.execute("""
        CREATE TABLE investment (
            investment_id TEXT PRIMARY KEY,
            symbol TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            asset_class TEXT NOT NULL,
            currency TEXT NOT NULL,
            lifecycle_status TEXT,
            target_weight REAL,
            target_action TEXT,
            standing_decision_type TEXT,
            standing_decision_reason TEXT,
            standing_decision_source TEXT,
            standing_decision_review TEXT,
            pillar_id TEXT,
            sub_strategy_id TEXT,
            thesis_for_inclusion TEXT,
            agent_rationale TEXT,
            is_watchlisted INTEGER DEFAULT 0,
            watchlist_added_at TEXT,
            thesis_breaker_status TEXT,
            sector TEXT,
            industry TEXT,
            latest_projection_id TEXT,
            created_at TEXT,
            updated_at TEXT
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
    conn.commit()
    conn.close()
    return str(db_file)


# Dual-layer docs: test_add_and_list_watchlist test case
def test_add_and_list_watchlist(test_db: str) -> None:
    """Verify that adding an item properly updates the database and appears in get_watchlist_items.

    Args:
        test_db: Path to the mock database.
    """
    res = add_to_watchlist(
        ticker="XYZ",
        db_path=test_db,
        name="XYZ Corp",
        pillar_id="defense",
        sub_strategy_id="space_defense",
        price=123.45,
        sector="Industrials",
        industry="Aerospace & Defense",
    )
    assert res["success"] is True
    assert res["ticker"] == "XYZ"

    items = get_watchlist_items(db_path=test_db)
    assert len(items) == 1
    assert items[0]["symbol"] == "XYZ"
    assert items[0]["is_watchlisted"] == 1
    assert items[0]["price"] == 123.45


# Dual-layer docs: test_remove_from_watchlist test case
def test_remove_from_watchlist(test_db: str) -> None:
    """Verify that removing an item sets is_watchlisted to 0 and clears it from active list.

    Args:
        test_db: Path to the mock database.
    """
    add_to_watchlist(ticker="ABC", db_path=test_db, price=50.0)
    assert len(get_watchlist_items(db_path=test_db)) == 1

    rem = remove_from_watchlist(ticker="ABC", db_path=test_db)
    assert rem["success"] is True

    items = get_watchlist_items(db_path=test_db)
    assert len(items) == 0
