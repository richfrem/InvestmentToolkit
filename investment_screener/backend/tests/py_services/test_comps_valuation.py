import json
import sys
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from comps_valuation import comps_implied_range, compute_ev, load_latest_projection  # noqa: E402


def _write_projection(dirpath, ticker, price, shares, revenue, source="AI_AGENT", saved_at="2026-01-01T00:00:00Z"):
    proj = [{
        "ticker": ticker, "source": source, "savedAt": saved_at,
        "snapshot": {"price": price, "shares": shares, "revenue": revenue},
    }]
    (dirpath / f"{ticker}.json").write_text(json.dumps(proj))


def test_compute_ev_combines_market_cap_debt_and_cash():
    ev = compute_ev(price=100.0, shares=10_000_000.0, debt=200_000_000.0, cash=50_000_000.0)
    assert ev == 100.0 * 10_000_000.0 + 200_000_000.0 - 50_000_000.0


def test_load_latest_projection_prefers_ai_agent_entry(tmp_path):
    proj = [
        {"ticker": "T", "source": "USER", "savedAt": "2026-01-01T00:00:00Z", "snapshot": {"price": 1}},
        {"ticker": "T", "source": "AI_AGENT", "savedAt": "2026-02-01T00:00:00Z", "snapshot": {"price": 2}},
    ]
    (tmp_path / "T.json").write_text(json.dumps(proj))
    result = load_latest_projection("T", str(tmp_path))
    assert result["snapshot"]["price"] == 2


def test_load_latest_projection_returns_none_when_file_missing(tmp_path):
    assert load_latest_projection("MISSING", str(tmp_path)) is None


def test_comps_implied_range_computes_median_ev_sales(tmp_path):
    _write_projection(tmp_path, "TARGET", price=100.0, shares=10_000_000.0, revenue=500_000_000.0)
    _write_projection(tmp_path, "PEERA", price=50.0, shares=20_000_000.0, revenue=400_000_000.0)
    _write_projection(tmp_path, "PEERB", price=80.0, shares=15_000_000.0, revenue=600_000_000.0)

    with patch("comps_valuation.get_fundamentals", return_value={}):
        result = comps_implied_range("TARGET", ["PEERA", "PEERB"], str(tmp_path))

    assert result["status"] == "ok"
    assert result["peersUsed"] == ["PEERA", "PEERB"]
    # PEERA EV/Sales = (50*20M)/400M = 2.5 ; PEERB EV/Sales = (80*15M)/600M = 2.0 ; median = 2.25
    assert result["evSalesMedian"] == 2.25


def test_comps_implied_range_insufficient_with_zero_peers(tmp_path):
    _write_projection(tmp_path, "TARGET", price=100.0, shares=10_000_000.0, revenue=500_000_000.0)
    result = comps_implied_range("TARGET", [], str(tmp_path))
    assert result["status"] == "insufficient_peer_data"
    assert result["peersUsed"] == []


def test_comps_implied_range_insufficient_with_only_one_usable_peer(tmp_path):
    _write_projection(tmp_path, "TARGET", price=100.0, shares=10_000_000.0, revenue=500_000_000.0)
    _write_projection(tmp_path, "PEERA", price=50.0, shares=20_000_000.0, revenue=400_000_000.0)
    with patch("comps_valuation.get_fundamentals", return_value={}):
        result = comps_implied_range("TARGET", ["PEERA", "MISSINGPEER"], str(tmp_path))
    assert result["status"] == "insufficient_peer_data"
    assert result["peersUsed"] == ["PEERA"]


def test_comps_implied_range_incorporates_target_debt_and_cash(tmp_path):
    _write_projection(tmp_path, "TARGET", price=100.0, shares=10_000_000.0, revenue=500_000_000.0)
    _write_projection(tmp_path, "PEERA", price=50.0, shares=20_000_000.0, revenue=400_000_000.0)
    _write_projection(tmp_path, "PEERB", price=80.0, shares=15_000_000.0, revenue=600_000_000.0)

    def fake_fundamentals(ticker, cik=None):
        if ticker == "TARGET":
            return {
                "totalDebt": {"value": 100_000_000.0, "source": "yfinance", "asOf": "x"},
                "cashAndEquivalents": {"value": 300_000_000.0, "source": "yfinance", "asOf": "x"},
            }
        return {}

    with patch("comps_valuation.get_fundamentals", side_effect=fake_fundamentals):
        result = comps_implied_range("TARGET", ["PEERA", "PEERB"], str(tmp_path))

    # evSalesMedian=2.25 -> impliedEV=2.25*500M=1125M
    # impliedPrice = (1125M - 100M + 300M)/10M = 132.5
    assert result["impliedPriceRange"]["low"] == round(132.5 * 0.9, 2)
    assert result["impliedPriceRange"]["high"] == round(132.5 * 1.1, 2)
