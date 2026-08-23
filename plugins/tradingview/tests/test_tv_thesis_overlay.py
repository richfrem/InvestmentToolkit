"""
Unit tests for tv_thesis_overlay.py
Tests multi-table data resolution from domain_model.sqlite, Pine Script v6 generation,
and pine_linter.py validation.
"""

import os
import sqlite3
import pytest
from plugins.tradingview.scripts.tv_thesis_overlay import (
    generate_pine_script_content,
    resolve_ticker_levels,
)
from plugins.tradingview.scripts.pine_linter import PineLinter


@pytest.fixture
def mock_db(tmp_path):
    """Create a minimal SQLite schema matching domain_model.sqlite for testing."""
    db_file = tmp_path / "test_domain_model.sqlite"
    conn = sqlite3.connect(str(db_file))
    
    # Investment table
    conn.execute("""
        CREATE TABLE investment (
            investment_id TEXT PRIMARY KEY,
            symbol TEXT NOT NULL UNIQUE,
            name TEXT,
            thesis_breaker_status TEXT
        );
    """)
    # Projection version table
    conn.execute("""
        CREATE TABLE projection_version (
            projection_id TEXT PRIMARY KEY,
            investment_id TEXT NOT NULL,
            version INTEGER NOT NULL,
            fair_value REAL,
            action TEXT
        );
    """)
    # Price level tables
    conn.execute("""
        CREATE TABLE price_level_set (
            price_level_set_id TEXT PRIMARY KEY,
            investment_id TEXT NOT NULL
        );
    """)
    conn.execute("""
        CREATE TABLE price_level_tier (
            tier_id TEXT PRIMARY KEY,
            price_level_set_id TEXT NOT NULL,
            tier_kind TEXT NOT NULL,
            price REAL NOT NULL
        );
    """)
    
    # Seed NVDA test data
    conn.execute("INSERT INTO investment (investment_id, symbol, name, thesis_breaker_status) VALUES ('NVDA', 'NVDA', 'Nvidia', 'OK');")
    conn.execute("INSERT INTO projection_version (projection_id, investment_id, version, fair_value, action) VALUES ('NVDA:1', 'NVDA', 1, 185.00, 'ACCUMULATE');")
    conn.execute("INSERT INTO price_level_set (price_level_set_id, investment_id) VALUES ('NVDA-pls', 'NVDA');")
    conn.execute("INSERT INTO price_level_tier (tier_id, price_level_set_id, tier_kind, price) VALUES ('NVDA-tier-1', 'NVDA-pls', 'TARGET_ENTRY', 135.50);")
    conn.execute("INSERT INTO price_level_tier (tier_id, price_level_set_id, tier_kind, price) VALUES ('NVDA-tier-2', 'NVDA-pls', 'STOP_LOSS', 110.00);")
    
    conn.commit()
    conn.close()
    return str(db_file)


def test_resolve_ticker_levels(mock_db):
    levels = resolve_ticker_levels("NVDA", db_path=mock_db)
    assert levels["symbol"] == "NVDA"
    assert levels["fair_value"] == 185.00
    assert levels["target_entry"] == 135.50
    assert levels["stop_loss"] == 110.00
    assert levels["breaker_status"] == "OK"


def test_generate_pine_script_validity(tmp_path):
    levels = {
        "symbol": "NVDA",
        "fair_value": 185.00,
        "target_entry": 135.50,
        "stop_loss": 110.00,
        "action": "ACCUMULATE",
    }
    pine_code = generate_pine_script_content(levels)
    assert "//@version=6" in pine_code
    assert 'indicator("AI Thesis Overlay - NVDA"' in pine_code
    assert "185.0" in pine_code
    assert "135.5" in pine_code
    assert "110.0" in pine_code

    # Verify that the generated Pine Script passes pine_linter.py without errors
    pine_file = tmp_path / "test_overlay.pine"
    pine_file.write_text(pine_code, encoding="utf-8")
    linter = PineLinter(str(pine_file))
    assert linter.lint() is True
    assert len(linter.errors) == 0
