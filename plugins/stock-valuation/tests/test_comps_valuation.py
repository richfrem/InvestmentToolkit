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

from comps_valuation import comps_implied_range  # noqa: E402


def _write_projection(dirpath, ticker, price, shares, revenue):
    proj = [{
        "ticker": ticker, "source": "AI_AGENT", "savedAt": "2026-01-01T00:00:00Z",
        "snapshot": {"price": price, "shares": shares, "revenue": revenue},
    }]
    (dirpath / f"{ticker}.json").write_text(json.dumps(proj))


def test_comps_implied_range_threads_cik_to_target_fundamentals_call_only(tmp_path):
    _write_projection(tmp_path, "TARGET", price=100.0, shares=10_000_000.0, revenue=500_000_000.0)
    _write_projection(tmp_path, "PEERA", price=50.0, shares=20_000_000.0, revenue=400_000_000.0)
    _write_projection(tmp_path, "PEERB", price=80.0, shares=15_000_000.0, revenue=600_000_000.0)

    with patch("comps_valuation.get_fundamentals", return_value={}) as mock_fundamentals:
        comps_implied_range("TARGET", ["PEERA", "PEERB"], str(tmp_path), cik="0001045810")

    calls_by_ticker = {call.args[0]: call.kwargs.get("cik") for call in mock_fundamentals.call_args_list}

    assert calls_by_ticker["TARGET"] == "0001045810"
    assert calls_by_ticker["PEERA"] is None
    assert calls_by_ticker["PEERB"] is None


def test_comps_implied_range_defaults_cik_to_none(tmp_path):
    _write_projection(tmp_path, "TARGET", price=100.0, shares=10_000_000.0, revenue=500_000_000.0)
    _write_projection(tmp_path, "PEERA", price=50.0, shares=20_000_000.0, revenue=400_000_000.0)
    _write_projection(tmp_path, "PEERB", price=80.0, shares=15_000_000.0, revenue=600_000_000.0)

    with patch("comps_valuation.get_fundamentals", return_value={}) as mock_fundamentals:
        comps_implied_range("TARGET", ["PEERA", "PEERB"], str(tmp_path))

    calls_by_ticker = {call.args[0]: call.kwargs.get("cik") for call in mock_fundamentals.call_args_list}
    assert calls_by_ticker["TARGET"] is None
