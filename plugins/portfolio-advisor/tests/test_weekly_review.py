"""Tests for weekly_review.py context parsing."""
import sys
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "plugins/portfolio-advisor/scripts"))

from weekly_review import get_recent_reviews_context, load_target_holdings, load_watchlist_items  # noqa: E402

sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))
from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.investment_repository import resolve_investment, update_investment_fields  # noqa: E402
from domain_model.pillar_repository import resolve_pillar  # noqa: E402


def test_load_target_holdings_reads_from_sqlite_not_json(tmp_path):
    """Wave 2 rewire: target holdings must come from investment.target_weight,
    not target-portfolio.json."""
    db_path = tmp_path / "test.sqlite"
    conn = initialize_db(str(db_path))
    try:
        resolve_pillar(conn, "ai-compute", "AI Compute")
        nvda_id = resolve_investment(conn, "NVDA", asset_class="EQUITY")
        update_investment_fields(conn, nvda_id, pillar_id="ai-compute", target_weight=5.5)
        # Watchlist-only row (no pillar_id) must be excluded.
        wl_id = resolve_investment(conn, "ZZZZ", asset_class="EQUITY")
        update_investment_fields(conn, wl_id, is_watchlisted=True)
    finally:
        conn.close()

    holdings = load_target_holdings(db_path)
    assert holdings == [{"ticker": "NVDA", "targetWeight": 5.5}]


def test_load_watchlist_items_reads_from_sqlite_not_json(tmp_path):
    """Wave 2 rewire: watchlist tickers must come from investment.is_watchlisted,
    not watchlist.json."""
    db_path = tmp_path / "test.sqlite"
    conn = initialize_db(str(db_path))
    try:
        wl_id = resolve_investment(conn, "ZZZZ", asset_class="EQUITY")
        update_investment_fields(conn, wl_id, is_watchlisted=True)
        resolve_investment(conn, "NVDA", asset_class="EQUITY")  # not watchlisted
    finally:
        conn.close()

    items = load_watchlist_items(db_path)
    assert items == [{"ticker": "ZZZZ"}]


def test_load_target_holdings_missing_db_returns_empty(tmp_path):
    assert load_target_holdings(tmp_path / "nope.sqlite") == []


def test_load_watchlist_items_missing_db_returns_empty(tmp_path):
    assert load_watchlist_items(tmp_path / "nope.sqlite") == []


def test_get_recent_reviews_context(tmp_path):
    temp_daily = tmp_path / "investment_screener/backend/data/history/reviews/daily"
    temp_daily.mkdir(parents=True)
    
    mock_review = (
        "# Daily Portfolio Confluence Scan\n\n"
        "## Executive Summary\n"
        "* **Total Portfolio Value:** $28,287.33 USD\n"
        "* **Key Observations:**\n"
        "* **Drift Alerts:** Key target deviations in PLTR(-1.03%), SNDK(+1.00%), MU(-0.54%).\n"
        "## Sub-Strategy Analysis\n"
    )
    
    review_file = temp_daily / "daily_confluence_scan_2026-07-18.md"
    review_file.write_text(mock_review)
    
    # Run helper
    context = get_recent_reviews_context(tmp_path)
    
    assert "Already Captured" in context
    assert "PLTR(-1.03%)" in context
