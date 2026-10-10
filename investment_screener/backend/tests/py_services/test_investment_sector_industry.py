"""investment.sector / investment.industry columns.

These two nullable TEXT columns hold the enriched-display facts GET /api/portfolio
returns for each holding. They are resolved by the same real fetch_portfolio_heatmap.py yfinance lookup during a
/refresh-prices call and persisted via update_investment_sector().

All state is tmp_path-scoped SQLite via the real repository functions — no mocking,
no live yfinance/TradingView call.
"""

import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from legacy_db import make_legacy_db  # noqa: E402
from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.investment_repository import (  # noqa: E402
    resolve_investment,
    get_investment,
    update_investment_sector,
    update_investment_fields,
)


def test_investment_table_has_sector_and_industry_columns(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    cols = {row[1] for row in conn.execute("PRAGMA table_info(investment);").fetchall()}
    assert "sector" in cols
    assert "industry" in cols


def test_sector_industry_default_null(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    inv = resolve_investment(conn, "NVDA", asset_class="EQUITY", currency="USD")
    row = get_investment(conn, inv)
    assert row["sector"] is None
    assert row["industry"] is None


def test_update_investment_sector_persists(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    inv = resolve_investment(conn, "NVDA", asset_class="EQUITY", currency="USD")
    update_investment_sector(conn, inv, "Technology", "Semiconductors")
    row = get_investment(conn, inv)
    assert row["sector"] == "Technology"
    assert row["industry"] == "Semiconductors"


def test_update_investment_sector_does_not_clobber_other_fields(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    inv = resolve_investment(conn, "PLTR", asset_class="EQUITY", currency="USD")
    update_investment_fields(
        conn, inv,
        standing_decision_type="HOLD", target_weight=0.04,
    )
    update_investment_sector(conn, inv, "Technology", "Software - Infrastructure")
    row = get_investment(conn, inv)
    assert row["standing_decision_type"] == "HOLD"
    assert row["target_weight"] == 0.04
    assert row["sector"] == "Technology"


def test_schema_evolution_self_heals_existing_file(tmp_path):
    """An older file whose investment table predates these columns must gain them
    on the next initialize_db() call (CREATE TABLE IF NOT EXISTS alone cannot)."""
    db_path = str(tmp_path / "old.sqlite")
    # Mirrors the real pre-completion file: the baseline minus the late sector/industry columns.
    make_legacy_db(db_path, drop={"investment": ["sector", "industry", "last_deep_analysis_at"]})

    conn = initialize_db(db_path)
    cols = {row[1] for row in conn.execute("PRAGMA table_info(investment);").fetchall()}
    assert "sector" in cols
    assert "industry" in cols
