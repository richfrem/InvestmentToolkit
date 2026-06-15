"""Tests for overnight_gaps.py — extended-hours gap scanner.

Run:
    python3 -m pytest investment_screener/backend/tests/py_services/test_overnight_gaps.py -v
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
PY_SERVICES = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(PY_SERVICES))

import overnight_gaps  # noqa: E402


class TestImport:
    def test_module_imports(self):
        assert hasattr(overnight_gaps, "get_overnight_gaps")
        assert hasattr(overnight_gaps, "_load_tickers")
        assert hasattr(overnight_gaps, "_fetch_gap")
        assert hasattr(overnight_gaps, "_is_scannable")


class TestIsScannable:
    def test_us_equity_passes(self):
        assert overnight_gaps._is_scannable("NVDA") is True

    def test_canadian_to_blocked(self):
        assert overnight_gaps._is_scannable("SHOP.TO") is False

    def test_futures_blocked(self):
        assert overnight_gaps._is_scannable("NQ1!") is False

    def test_lowercase_us_passes(self):
        assert overnight_gaps._is_scannable("aapl") is True


class TestLoadTickers:
    def test_loads_from_portfolio_and_watchlist(self, tmp_path, monkeypatch):
        portfolio = tmp_path / "portfolio.json"
        portfolio.write_text(json.dumps({"holdings": [
            {"symbol": "NVDA"}, {"symbol": "AAPL"}
        ]}))
        watchlist = tmp_path / "watchlist.json"
        watchlist.write_text(json.dumps({"watchlist": [
            {"ticker": "MSFT"}, {"ticker": "TSLA"}
        ]}))
        monkeypatch.setattr(overnight_gaps, "PORTFOLIO_PATH", portfolio)
        monkeypatch.setattr(overnight_gaps, "WATCHLIST_PATH", watchlist)
        result = overnight_gaps._load_tickers()
        assert result == ["NVDA", "AAPL", "MSFT", "TSLA"]

    def test_deduplicates_across_sources(self, tmp_path, monkeypatch):
        portfolio = tmp_path / "portfolio.json"
        portfolio.write_text(json.dumps({"holdings": [{"symbol": "NVDA"}]}))
        watchlist = tmp_path / "watchlist.json"
        watchlist.write_text(json.dumps({"watchlist": [
            {"ticker": "NVDA"}, {"ticker": "AAPL"}
        ]}))
        monkeypatch.setattr(overnight_gaps, "PORTFOLIO_PATH", portfolio)
        monkeypatch.setattr(overnight_gaps, "WATCHLIST_PATH", watchlist)
        result = overnight_gaps._load_tickers()
        assert result == ["NVDA", "AAPL"]

    def test_missing_portfolio_returns_watchlist_only(self, tmp_path, monkeypatch):
        missing = tmp_path / "missing.json"
        watchlist = tmp_path / "watchlist.json"
        watchlist.write_text(json.dumps({"watchlist": [{"ticker": "MSFT"}]}))
        monkeypatch.setattr(overnight_gaps, "PORTFOLIO_PATH", missing)
        monkeypatch.setattr(overnight_gaps, "WATCHLIST_PATH", watchlist)
        result = overnight_gaps._load_tickers()
        assert result == ["MSFT"]

    def test_missing_watchlist_returns_portfolio_only(self, tmp_path, monkeypatch):
        portfolio = tmp_path / "portfolio.json"
        portfolio.write_text(json.dumps({"holdings": [{"symbol": "NVDA"}]}))
        missing = tmp_path / "missing.json"
        monkeypatch.setattr(overnight_gaps, "PORTFOLIO_PATH", portfolio)
        monkeypatch.setattr(overnight_gaps, "WATCHLIST_PATH", missing)
        result = overnight_gaps._load_tickers()
        assert result == ["NVDA"]


class TestGetOvernightGaps:
    def _make_gap(self, ticker, change_pct):
        direction = "UP" if change_pct > 0 else "DOWN"
        return {
            "ticker": ticker,
            "prev_close": 100.0,
            "current": round(100.0 * (1 + change_pct / 100), 2),
            "change_pct": change_pct,
            "direction": direction,
            "market_state": "PRE",
        }

    def test_filters_below_threshold(self, monkeypatch):
        monkeypatch.setattr(overnight_gaps, "_fetch_gap",
                            lambda t: self._make_gap(t, 1.5))
        result = overnight_gaps.get_overnight_gaps(["NVDA"], threshold_pct=2.0)
        assert result == []

    def test_includes_at_threshold(self, monkeypatch):
        monkeypatch.setattr(overnight_gaps, "_fetch_gap",
                            lambda t: self._make_gap(t, 2.0))
        result = overnight_gaps.get_overnight_gaps(["NVDA"], threshold_pct=2.0)
        assert len(result) == 1
        assert result[0]["ticker"] == "NVDA"

    def test_negative_direction(self, monkeypatch):
        monkeypatch.setattr(overnight_gaps, "_fetch_gap",
                            lambda t: self._make_gap(t, -3.0))
        result = overnight_gaps.get_overnight_gaps(["AAPL"], threshold_pct=2.0)
        assert len(result) == 1
        assert result[0]["direction"] == "DOWN"

    def test_sorted_by_magnitude_descending(self, monkeypatch):
        data = {"NVDA": 2.5, "AAPL": 5.0, "MSFT": 3.0}
        monkeypatch.setattr(overnight_gaps, "_fetch_gap",
                            lambda t: self._make_gap(t, data[t]))
        result = overnight_gaps.get_overnight_gaps(list(data.keys()), threshold_pct=2.0)
        assert [r["ticker"] for r in result] == ["AAPL", "MSFT", "NVDA"]

    def test_futures_filtered_out(self, monkeypatch):
        called = []
        def fake_fetch(t):
            called.append(t)
            return self._make_gap(t, 3.0)
        monkeypatch.setattr(overnight_gaps, "_fetch_gap", fake_fetch)
        overnight_gaps.get_overnight_gaps(["NVDA", "NQ1!", "GC1!"], threshold_pct=2.0)
        assert "NQ1!" not in called
        assert "GC1!" not in called
        assert "NVDA" in called

    def test_none_from_fetch_excluded(self, monkeypatch):
        monkeypatch.setattr(overnight_gaps, "_fetch_gap", lambda t: None)
        result = overnight_gaps.get_overnight_gaps(["NVDA"], threshold_pct=2.0)
        assert result == []

    def test_empty_tickers_returns_empty(self, monkeypatch):
        def _should_not_call(t):
            raise AssertionError(f"_fetch_gap called unexpectedly with: {t}")
        monkeypatch.setattr(overnight_gaps, "_fetch_gap", _should_not_call)
        result = overnight_gaps.get_overnight_gaps([], threshold_pct=2.0)
        assert result == []

    def test_explicit_tickers_override_load(self, monkeypatch, tmp_path):
        # Patch PORTFOLIO_PATH to a missing file so _load_tickers would return []
        monkeypatch.setattr(overnight_gaps, "PORTFOLIO_PATH", tmp_path / "missing.json")
        monkeypatch.setattr(overnight_gaps, "WATCHLIST_PATH", tmp_path / "missing.json")
        monkeypatch.setattr(overnight_gaps, "_fetch_gap",
                            lambda t: self._make_gap(t, 3.0))
        result = overnight_gaps.get_overnight_gaps(["NVDA"], threshold_pct=2.0)
        assert len(result) == 1
        assert result[0]["ticker"] == "NVDA"
