"""Tests for comps_valuation.py's cik threading — comps_implied_range()'s target-ticker
get_fundamentals() call must accept an optional SEC CIK (mirroring wacc.py's established
--cik pattern) so EDGAR cross-checking can be enabled for the target. Peer-level cik
threading is deliberately out of scope: peers are only used for their EV/Sales multiple,
not compared against EDGAR filings directly.
"""
import json
import sys
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = REPO_ROOT / "plugins/stock-valuation/scripts"
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))

from comps_valuation import comps_implied_range  # noqa: E402
from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.investment_repository import resolve_investment  # noqa: E402
from domain_model.projection_repository import save_projection_version  # noqa: E402


def _write_projection(tmp_path, ticker, price, shares, revenue):
    """Insert a projection_version row for `ticker` (Wave 1 Task 7A: replaces
    the old projections/{TICKER}.json fixture writer). Returns the shared
    domain_model.sqlite path for this tmp_path."""
    db_path = tmp_path / "domain_model.sqlite"
    conn = initialize_db(str(db_path))
    investment_id = resolve_investment(conn, ticker)
    save_projection_version(
        conn, investment_id, version=1, saved_at="2026-01-01T00:00:00Z", source="AI_AGENT",
        snapshot_json=json.dumps({"price": price, "shares": shares, "revenue": revenue}),
    )
    conn.close()
    return db_path


def test_comps_implied_range_threads_cik_to_target_fundamentals_call_only(tmp_path):
    _write_projection(tmp_path, "TARGET", price=100.0, shares=10_000_000.0, revenue=500_000_000.0)
    _write_projection(tmp_path, "PEERA", price=50.0, shares=20_000_000.0, revenue=400_000_000.0)
    db_path = _write_projection(tmp_path, "PEERB", price=80.0, shares=15_000_000.0, revenue=600_000_000.0)

    with patch("comps_valuation.get_fundamentals", return_value={}) as mock_fundamentals:
        comps_implied_range("TARGET", ["PEERA", "PEERB"], str(db_path), cik="0001045810")

    calls_by_ticker = {call.args[0]: call.kwargs.get("cik") for call in mock_fundamentals.call_args_list}

    assert calls_by_ticker["TARGET"] == "0001045810"
    assert calls_by_ticker["PEERA"] is None
    assert calls_by_ticker["PEERB"] is None


def test_comps_implied_range_defaults_cik_to_none(tmp_path):
    _write_projection(tmp_path, "TARGET", price=100.0, shares=10_000_000.0, revenue=500_000_000.0)
    _write_projection(tmp_path, "PEERA", price=50.0, shares=20_000_000.0, revenue=400_000_000.0)
    db_path = _write_projection(tmp_path, "PEERB", price=80.0, shares=15_000_000.0, revenue=600_000_000.0)

    with patch("comps_valuation.get_fundamentals", return_value={}) as mock_fundamentals:
        comps_implied_range("TARGET", ["PEERA", "PEERB"], str(db_path))

    calls_by_ticker = {call.args[0]: call.kwargs.get("cik") for call in mock_fundamentals.call_args_list}
    assert calls_by_ticker["TARGET"] is None
