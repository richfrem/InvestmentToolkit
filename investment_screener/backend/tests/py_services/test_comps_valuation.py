import json
import sys
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from comps_valuation import comps_implied_range, compute_ev, load_latest_projection  # noqa: E402
from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.investment_repository import resolve_investment  # noqa: E402
from domain_model.projection_repository import save_projection_version  # noqa: E402


def _domain_db(tmp_path) -> Path:
    """Path to this tmp_path's (not-yet-created) domain_model.sqlite fixture DB."""
    return tmp_path / "domain_model.sqlite"


def _write_projection(tmp_path, ticker, price, shares, revenue, source="AI_AGENT",
                       saved_at="2026-01-01T00:00:00Z", version=1):
    """Insert a projection_version row for `ticker` (Wave 1 Task 7A: replaces the
    old projections/{TICKER}.json fixture writer)."""
    db_path = _domain_db(tmp_path)
    conn = initialize_db(str(db_path))
    investment_id = resolve_investment(conn, ticker)
    save_projection_version(
        conn, investment_id, version=version, saved_at=saved_at, source=source,
        snapshot_json=json.dumps({"price": price, "shares": shares, "revenue": revenue}),
    )
    conn.close()
    return db_path


def test_compute_ev_combines_market_cap_debt_and_cash():
    ev = compute_ev(price=100.0, shares=10_000_000.0, debt=200_000_000.0, cash=50_000_000.0)
    assert ev == 100.0 * 10_000_000.0 + 200_000_000.0 - 50_000_000.0


def test_load_latest_projection_prefers_ai_agent_entry(tmp_path):
    db_path = _write_projection(tmp_path, "T", price=1, shares=None, revenue=None,
                                 source="USER", version=1)
    # Second row: AI_AGENT-sourced, newer saved_at, higher version, different price —
    # must win over the USER-sourced row regardless of version ordering.
    conn = initialize_db(str(db_path))
    investment_id = resolve_investment(conn, "T")
    save_projection_version(
        conn, investment_id, version=2, saved_at="2026-02-01T00:00:00Z", source="AI_AGENT",
        snapshot_json=json.dumps({"price": 2}),
    )
    conn.close()

    result = load_latest_projection("T", str(db_path))
    assert result["snapshot"]["price"] == 2


def test_load_latest_projection_returns_none_when_file_missing(tmp_path):
    assert load_latest_projection("MISSING", str(_domain_db(tmp_path))) is None


def test_comps_implied_range_computes_median_ev_sales(tmp_path):
    db_path = _write_projection(tmp_path, "TARGET", price=100.0, shares=10_000_000.0, revenue=500_000_000.0)
    _write_projection(tmp_path, "PEERA", price=50.0, shares=20_000_000.0, revenue=400_000_000.0)
    _write_projection(tmp_path, "PEERB", price=80.0, shares=15_000_000.0, revenue=600_000_000.0)

    with patch("comps_valuation.get_fundamentals", return_value={}):
        result = comps_implied_range("TARGET", ["PEERA", "PEERB"], str(db_path))

    assert result["status"] == "ok"
    assert result["peersUsed"] == ["PEERA", "PEERB"]
    # PEERA EV/Sales = (50*20M)/400M = 2.5 ; PEERB EV/Sales = (80*15M)/600M = 2.0 ; median = 2.25
    assert result["evSalesMedian"] == 2.25


def test_comps_implied_range_insufficient_with_zero_peers(tmp_path):
    db_path = _write_projection(tmp_path, "TARGET", price=100.0, shares=10_000_000.0, revenue=500_000_000.0)
    result = comps_implied_range("TARGET", [], str(db_path))
    assert result["status"] == "insufficient_peer_data"
    assert result["peersUsed"] == []


def test_comps_implied_range_insufficient_with_only_one_usable_peer(tmp_path):
    db_path = _write_projection(tmp_path, "TARGET", price=100.0, shares=10_000_000.0, revenue=500_000_000.0)
    _write_projection(tmp_path, "PEERA", price=50.0, shares=20_000_000.0, revenue=400_000_000.0)
    with patch("comps_valuation.get_fundamentals", return_value={}):
        result = comps_implied_range("TARGET", ["PEERA", "MISSINGPEER"], str(db_path))
    assert result["status"] == "insufficient_peer_data"
    assert result["peersUsed"] == ["PEERA"]


def test_comps_implied_range_incorporates_target_debt_and_cash(tmp_path):
    db_path = _write_projection(tmp_path, "TARGET", price=100.0, shares=10_000_000.0, revenue=500_000_000.0)
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
        result = comps_implied_range("TARGET", ["PEERA", "PEERB"], str(db_path))

    # evSalesMedian=2.25 -> impliedEV=2.25*500M=1125M
    # impliedPrice = (1125M - 100M + 300M)/10M = 132.5
    assert result["impliedPriceRange"]["low"] == round(132.5 * 0.9, 2)
    assert result["impliedPriceRange"]["high"] == round(132.5 * 1.1, 2)


def test_comps_implied_range_includes_data_quality_per_ticker_used(tmp_path, monkeypatch):
    import comps_valuation

    db_path = _write_projection(tmp_path, "NVDA", price=100.0, shares=1000.0, revenue=5000.0)
    _write_projection(tmp_path, "AMD", price=50.0, shares=2000.0, revenue=3000.0)
    _write_projection(tmp_path, "AVGO", price=200.0, shares=500.0, revenue=4000.0)

    quality_by_ticker = {
        "NVDA": {"staleness": True, "dataConflicts": [], "flags": []},
        "AMD": {"staleness": False, "dataConflicts": [], "flags": []},
        "AVGO": {"staleness": False, "dataConflicts": [], "flags": []},
    }

    def fake_get_fundamentals(ticker, cik=None):
        return {
            "totalDebt": {"value": 0.0}, "cashAndEquivalents": {"value": 0.0},
            "dataQuality": quality_by_ticker[ticker],
        }

    monkeypatch.setattr(comps_valuation, "get_fundamentals", fake_get_fundamentals)

    result = comps_valuation.comps_implied_range("NVDA", ["AMD", "AVGO"], str(db_path))

    assert result["status"] == "ok"
    assert result["dataQuality"]["NVDA"]["staleness"] is True
    assert result["dataQuality"]["AMD"]["staleness"] is False
    assert result["dataQuality"]["AVGO"]["staleness"] is False
