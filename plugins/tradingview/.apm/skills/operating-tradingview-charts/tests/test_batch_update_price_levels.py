"""
Unit tests for batch_update_price_levels.py
Tests batch recalculation of price levels and chart synchronization.
"""

from pathlib import Path
import sys
from unittest.mock import MagicMock, patch
import pytest

# Add skill scripts directory and backend py_services directory
SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
ENGINE_DIR = Path(__file__).resolve().parents[5] / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPTS_DIR))
sys.path.insert(0, str(ENGINE_DIR))

from batch_update_price_levels import (
    batch_recalculate_levels,
    batch_draw_watchlist,
)


@pytest.fixture
def mock_db(tmp_path):
    """Create a test domain_model.sqlite database with test investment records."""
    from domain_model.db_client import initialize_db
    from domain_model.investment_repository import resolve_investment, update_investment_fields
    from domain_model.projection_repository import save_projection_version, add_projection_scenario
    from domain_model.price_level_repository import replace_price_levels

    db_file = tmp_path / "test_domain_model.sqlite"
    conn = initialize_db(str(db_file))
    
    # Setup test tickers NVDA and NFLX
    for ticker, fv in [("NVDA", 200.0), ("NFLX", 100.0)]:
        inv = resolve_investment(conn, ticker, name=ticker)
        update_investment_fields(conn, inv, thesis_breaker_status="OK", is_watchlisted=1)
        save_projection_version(
            conn, inv, version=1, fair_value=fv, source="AI_AGENT",
            saved_at="2026-10-01T00:00:00Z", action="ACCUMULATE", snapshot_json='{"price": 100}'
        )
        for name, weight, price in [("bear", 0.25, fv * 0.7), ("base", 0.5, fv), ("bull", 0.25, fv * 1.3)]:
            add_projection_scenario(conn, f"{inv}:1", name, weight=weight, scenario_price=price)
        replace_price_levels(conn, inv, None, None, None, None, [], [], {"price": fv * 0.65}, fv * 0.8)

    conn.close()
    return str(db_file)


def test_batch_recalculate_levels_dry_run(mock_db):
    """Verify batch recalculation handles dry-run mode and returns summary."""
    with patch("chart_levels.fetch_daily_bars", return_value={}):
        res = batch_recalculate_levels(source="dcf", dry_run=True, db_path=mock_db)
        assert "updated" in res
        assert "skipped" in res
        assert "failed" in res


def test_batch_draw_watchlist_mocked():
    """Verify batch_draw_watchlist iterates through tickers and invokes draw_levels."""
    mock_draw = MagicMock(return_value={"success": True, "study": "AI TA Levels v6"})
    with patch("batch_update_price_levels.draw_levels", mock_draw):
        result = batch_draw_watchlist(tickers=["NVDA", "NFLX"], delay=0.01)
        assert result["total"] == 2
        assert len(result["drawn"]) == 2
        assert len(result["failed"]) == 0
        assert mock_draw.call_count == 2
        mock_draw.assert_any_call("NVDA", db_path=None, switch=True)
        mock_draw.assert_any_call("NFLX", db_path=None, switch=True)


def test_batch_cli_ticker_dry_run(mock_db):
    """Verify CLI ticker option works in dry-run mode without mutating charts."""
    from batch_update_price_levels import main
    with patch.object(sys, "argv", ["batch_update_price_levels.py", "--ticker", "NVDA", "--dry-run", "--db", mock_db]):
        assert main() == 0
