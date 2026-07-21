"""Tests for overnight_gaps.py — extended-hours gap scanner.

Run:
    python3 -m pytest investment_screener/backend/tests/py_services/test_overnight_gaps.py -v
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
PY_SERVICES = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(PY_SERVICES))

import overnight_gaps  # noqa: E402
from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.account_repository import upsert_account  # noqa: E402
from domain_model.investment_repository import resolve_investment, update_investment_fields  # noqa: E402
from domain_model.investment_price_repository import upsert_investment_price  # noqa: E402
from domain_model.account_investment_repository import upsert_account_investment  # noqa: E402


def _make_db_with_watchlisted(tmp_path, tickers):
    db_path = tmp_path / "domain_model.sqlite"
    conn = initialize_db(str(db_path))
    for t in tickers:
        investment_id = resolve_investment(conn, t)
        update_investment_fields(conn, investment_id, is_watchlisted=True)
    conn.close()
    return db_path


def _make_db_with_holdings(tmp_path, tickers, watchlisted=None):
    """Seed domain_model.sqlite with held positions (account_investment rows)
    plus optional watchlisted-only investments — Wave 3 Task 6 cutover of
    _load_tickers() off portfolio.json onto SQLite.
    """
    db_path = tmp_path / "domain_model.sqlite"
    conn = initialize_db(str(db_path))
    upsert_account(conn, "TFSA", "TFSA", "TFSA")
    for t in tickers:
        investment_id = resolve_investment(conn, t, asset_class="EQUITY", currency="USD")
        upsert_investment_price(conn, investment_id, price=100.0, currency="USD", fetched_at="2026-07-20T00:00:00Z")
        upsert_account_investment(
            conn, "TFSA", investment_id, quantity=1, average_cost=100.0,
            book_value=100.0, currency="USD", last_synced_at="2026-07-20T00:00:00Z",
        )
    for t in watchlisted or []:
        investment_id = resolve_investment(conn, t)
        update_investment_fields(conn, investment_id, is_watchlisted=True)
    conn.close()
    return db_path


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
    def test_loads_from_holdings_and_watchlist_sqlite(self, tmp_path):
        """Wave 3 Task 6: holdings now come from account_investment in
        domain_model.sqlite, not portfolio.json."""
        db_path = _make_db_with_holdings(tmp_path, ["NVDA", "AAPL"], watchlisted=["MSFT", "TSLA"])
        result = overnight_gaps._load_tickers(db_path)
        assert set(result) == {"NVDA", "AAPL", "MSFT", "TSLA"}

    def test_deduplicates_across_sources(self, tmp_path):
        db_path = _make_db_with_holdings(tmp_path, ["NVDA"], watchlisted=["NVDA", "AAPL"])
        result = overnight_gaps._load_tickers(db_path)
        assert result.count("NVDA") == 1
        assert set(result) == {"NVDA", "AAPL"}

    def test_missing_holdings_returns_watchlist_only(self, tmp_path):
        db_path = _make_db_with_watchlisted(tmp_path, ["MSFT"])
        result = overnight_gaps._load_tickers(db_path)
        assert result == ["MSFT"]

    def test_missing_db_returns_empty(self, tmp_path):
        missing_db = tmp_path / "missing.sqlite"
        result = overnight_gaps._load_tickers(missing_db)
        assert result == []


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
        monkeypatch.setattr(overnight_gaps, "_fetch_gap", lambda _: None)
        result = overnight_gaps.get_overnight_gaps(["NVDA"], threshold_pct=2.0)
        assert result == []

    def test_empty_tickers_returns_empty(self, monkeypatch):
        def _should_not_call(t):
            raise AssertionError(f"_fetch_gap called unexpectedly with: {t}")
        monkeypatch.setattr(overnight_gaps, "_fetch_gap", _should_not_call)
        result = overnight_gaps.get_overnight_gaps([], threshold_pct=2.0)
        assert result == []

    def test_explicit_tickers_override_load(self, monkeypatch, tmp_path):
        # Patch DB_PATH to a missing file so _load_tickers would return []
        monkeypatch.setattr(overnight_gaps, "DB_PATH", tmp_path / "missing.sqlite")
        monkeypatch.setattr(overnight_gaps, "_fetch_gap",
                            lambda t: self._make_gap(t, 3.0))
        result = overnight_gaps.get_overnight_gaps(["NVDA"], threshold_pct=2.0)
        assert len(result) == 1
        assert result[0]["ticker"] == "NVDA"
