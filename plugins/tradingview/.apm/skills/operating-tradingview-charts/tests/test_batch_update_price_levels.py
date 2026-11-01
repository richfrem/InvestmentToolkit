"""
Unit tests for batch_update_price_levels.py
Tests batch recalculation of price levels and chart synchronization.
"""

import json
from pathlib import Path
import sys
from unittest.mock import patch
import pytest

# Add skill scripts directory and backend py_services directory
SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
ENGINE_DIR = Path(__file__).resolve().parents[5] / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPTS_DIR))
sys.path.insert(0, str(ENGINE_DIR))

from batch_update_price_levels import (
    batch_recalculate_levels,
    build_level_plan,
    sync_chart_lines,
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


def test_build_level_plan_reads_stored_levels(mock_db):
    """Each ticker's lines come from its stored levels; a ticker with none gets an empty list."""
    plan = build_level_plan(["NVDA", "ZZZZ"], db_path=mock_db)
    nvda = {line["label"]: line["price"] for line in plan["NVDA"]}
    assert nvda["DCF Fair Value"] == 200.0
    assert nvda["Stop"] == 130.0
    assert all(line["price"] > 0 and line["color"].startswith("#") for line in plan["NVDA"])
    assert plan["ZZZZ"] == []   # unknown ticker: old lines are cleared, nothing drawn


def test_sync_chart_lines_draws_plan_then_blanks_indicator(mock_db):
    """The plan goes to the CDP engine in one call; then the indicator's level inputs are blanked."""
    calls = []

    def fake_call(*args, **kwargs):
        calls.append(args)
        if args[:2] == ("chart", "levelLines"):
            plan = json.loads(Path(args[args.index("--plan") + 1]).read_text())
            assert set(plan) == {"NVDA", "NFLX"}
            return {"success": True, "total": 2, "synced": ["NVDA", "NFLX"], "failed": []}
        return {"success": True}

    out = sync_chart_lines(["NVDA", "NFLX"], db_path=mock_db, call=fake_call)
    assert out["success"] is True and out["synced"] == ["NVDA", "NFLX"]
    assert calls[0][:2] == ("chart", "levelLines") and "--all-lines" not in calls[0]
    blank = json.loads(calls[1][calls[1].index("--values") + 1])
    assert calls[1][:2] == ("chart", "setInputs")
    assert blank["Levels for ticker"] == "" and blank["🟢 Buy Tier 1"] == 0


def test_sync_chart_lines_dry_run_and_all_lines_change_nothing_else(mock_db):
    """Dry run passes --dry-run and never blanks the indicator; --all-lines is passed through."""
    calls = []
    fake = lambda *a, **k: calls.append(a) or {"success": True, "synced": ["NVDA"], "failed": []}
    sync_chart_lines(["NVDA"], db_path=mock_db, dry_run=True, all_lines=True, call=fake)
    assert len(calls) == 1 and "--dry-run" in calls[0] and "--all-lines" in calls[0]


def test_sync_chart_lines_reports_failed_tickers(mock_db):
    """A ticker the engine could not draw is reported by name and the run is not a success."""
    fake = lambda *a, **k: ({"success": False, "synced": ["NVDA"], "failed": [{"symbol": "NFLX", "error": "chart is on ZS"}]}
                            if a[:2] == ("chart", "levelLines") else {"success": True})
    out = sync_chart_lines(["NVDA", "NFLX"], db_path=mock_db, call=fake)
    assert out["success"] is False and out["failed"][0]["symbol"] == "NFLX"


def test_batch_cli_ticker_dry_run(mock_db):
    """Verify CLI ticker option works in dry-run mode without mutating charts."""
    from batch_update_price_levels import main
    fake_sync = lambda *a, **k: {"success": True, "total": 1, "synced": ["NVDA"], "failed": [], "results": [],
                                 "indicator_blanked": False}
    with patch.object(sys, "argv", ["batch_update_price_levels.py", "--ticker", "NVDA", "--dry-run", "--db", mock_db]), \
         patch("batch_update_price_levels.sync_chart_lines", fake_sync):
        assert main() == 0
