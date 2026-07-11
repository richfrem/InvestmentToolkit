"""Tests for peer_bench.py — peer benchmarking table with Z-scores/percentiles (Phase 2b)."""
import sys
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from peer_bench import compute_peer_benchmark  # noqa: E402


def _metrics(revenue_growth):
    """A minimal compute_raw_metrics()-shaped dict varying only revenueGrowth."""
    return {
        "revenueGrowth": revenue_growth, "ruleOf40Raw": None, "ruleOf40Method": "A",
        "operatingMargin": None, "roic": None, "evSales": None, "fcfYield": None,
        "debtEbitda": None, "interestCoverage": None, "currentRatio": None,
    }


def test_compute_peer_benchmark_computes_zscore_and_percentile():
    values = {"TARGET": 0.30, "PEERA": 0.10, "PEERB": 0.20}

    def fake_raw_metrics(ticker, sector, projections_dir, cik=None):
        return _metrics(values[ticker])

    with patch("peer_bench.compute_raw_metrics", side_effect=fake_raw_metrics):
        result = compute_peer_benchmark("TARGET", ["PEERA", "PEERB"], "chips_ai", "/fake/dir")

    assert result["status"] == "ok"
    assert result["peersUsed"] == ["PEERA", "PEERB"]
    row = next(r for r in result["table"] if r["metric"] == "revenueGrowth")
    assert row["ticker"] == 0.30
    assert row["peerMedian"] == 0.15  # median of [0.10, 0.20]
    assert row["zScore"] == 3.0  # peer-only: mean=0.15, pstdev=0.05, (0.30-0.15)/0.05
    assert row["percentile"] == 100  # highest of the three values


def test_compute_peer_benchmark_insufficient_peer_data():
    def fake_raw_metrics(ticker, sector, projections_dir, cik=None):
        return _metrics(0.30) if ticker == "TARGET" else _metrics(None)

    with patch("peer_bench.compute_raw_metrics", side_effect=fake_raw_metrics):
        result = compute_peer_benchmark("TARGET", ["PEERA", "PEERB"], "chips_ai", "/fake/dir")

    assert result["status"] == "insufficient_peer_data"
    assert result["peersUsed"] == []


def test_compute_peer_benchmark_skips_metrics_with_no_target_value():
    def fake_raw_metrics(ticker, sector, projections_dir, cik=None):
        m = _metrics(0.30 if ticker == "TARGET" else 0.10)
        return m  # operatingMargin stays None for everyone

    with patch("peer_bench.compute_raw_metrics", side_effect=fake_raw_metrics):
        result = compute_peer_benchmark("TARGET", ["PEERA", "PEERB"], "chips_ai", "/fake/dir")

    metric_names = {r["metric"] for r in result["table"]}
    assert "operatingMargin" not in metric_names
    assert "revenueGrowth" in metric_names


def test_compute_peer_benchmark_includes_data_quality_per_ticker_used(monkeypatch):
    import peer_bench

    def fake_raw_metrics(ticker, sector, projections_dir, cik=None):
        return {"revenueGrowth": {"NVDA": 0.5, "AMD": 0.3, "AVGO": 0.4}[ticker]}

    def fake_get_fundamentals(ticker, cik=None):
        return {"dataQuality": {
            "NVDA": {"staleness": True, "dataConflicts": [], "flags": []},
            "AMD": {"staleness": False, "dataConflicts": [], "flags": []},
            "AVGO": {"staleness": False, "dataConflicts": [], "flags": []},
        }[ticker]}

    monkeypatch.setattr(peer_bench, "compute_raw_metrics", fake_raw_metrics)
    monkeypatch.setattr(peer_bench, "get_fundamentals", fake_get_fundamentals)

    result = peer_bench.compute_peer_benchmark("NVDA", ["AMD", "AVGO"], "chips_ai", "/tmp/unused")

    assert result["status"] == "ok"
    assert result["dataQuality"]["NVDA"]["staleness"] is True
    assert result["dataQuality"]["AMD"]["staleness"] is False
