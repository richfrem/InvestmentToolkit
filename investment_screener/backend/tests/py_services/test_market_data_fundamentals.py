import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from market_data import get_fundamentals  # noqa: E402


def _fake_edgar_facts(as_of: str = None):
    # Default to a recent date (30 days ago) so non-staleness-focused tests stay
    # valid regardless of when they're actually run — never hardcode a fixed
    # calendar date here, it will silently drift stale over real time.
    as_of = as_of or (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")
    return {
        "revenue": {"value": 391035000000.0, "asOf": as_of},
        "netIncome": {"value": 93736000000.0, "asOf": as_of},
        "operatingIncome": {"value": 114301000000.0, "asOf": as_of},
    }


def _fake_yf_info():
    fake_ticker = MagicMock()
    fake_ticker.info = {
        "totalRevenue": 395000000000.0,  # ~1% off EDGAR, within threshold
        "netIncomeToCommon": 94000000000.0,
    }
    return fake_ticker


def test_get_fundamentals_prefers_edgar_when_available(tmp_path, monkeypatch):
    monkeypatch.setattr("cache.CACHE_DIR", tmp_path)
    with patch("market_data.get_company_facts", return_value=_fake_edgar_facts()), \
         patch("market_data.yf.Ticker", return_value=_fake_yf_info()):
        result = get_fundamentals("AAPL", cik="0000320193")

    assert result["revenue"]["source"] == "edgar"
    assert result["revenue"]["value"] == 391035000000.0


def test_get_fundamentals_skips_edgar_when_no_cik(tmp_path, monkeypatch):
    monkeypatch.setattr("cache.CACHE_DIR", tmp_path)
    with patch("market_data.yf.Ticker", return_value=_fake_yf_info()):
        result = get_fundamentals("ASML", cik=None)

    assert result["revenue"]["source"] == "yfinance"


def test_get_fundamentals_flags_disagreement_without_hiding_it(tmp_path, monkeypatch):
    monkeypatch.setattr("cache.CACHE_DIR", tmp_path)
    fake_yf = MagicMock()
    fake_yf.info = {"totalRevenue": 500000000000.0, "netIncomeToCommon": 94000000000.0}  # way off
    with patch("market_data.get_company_facts", return_value=_fake_edgar_facts()), \
         patch("market_data.yf.Ticker", return_value=fake_yf):
        result = get_fundamentals("AAPL", cik="0000320193")

    assert len(result["dataQuality"]["dataConflicts"]) >= 1
    # still returns the EDGAR value — disagreement is flagged, not auto-resolved
    assert result["revenue"]["value"] == 391035000000.0


def test_get_fundamentals_never_returns_zero_for_missing_edgar_field(tmp_path, monkeypatch):
    monkeypatch.setattr("cache.CACHE_DIR", tmp_path)
    edgar_partial = {"revenue": _fake_edgar_facts()["revenue"]}  # no netIncome
    with patch("market_data.get_company_facts", return_value=edgar_partial), \
         patch("market_data.yf.Ticker", return_value=_fake_yf_info()):
        result = get_fundamentals("AAPL", cik="0000320193")

    # netIncome falls back to yfinance, not silently zeroed
    assert result["netIncome"]["source"] == "yfinance"
    assert result["netIncome"]["value"] == 94000000000.0


def test_get_fundamentals_flags_staleness_when_revenue_filing_is_old(tmp_path, monkeypatch):
    monkeypatch.setattr("cache.CACHE_DIR", tmp_path)
    old_date = (datetime.now(timezone.utc) - timedelta(days=200)).strftime("%Y-%m-%d")
    old_edgar_facts = _fake_edgar_facts(as_of=old_date)
    with patch("market_data.get_company_facts", return_value=old_edgar_facts), \
         patch("market_data.yf.Ticker", return_value=_fake_yf_info()):
        result = get_fundamentals("AAPL", cik="0000320193")

    assert result["dataQuality"]["staleness"] is True


def test_get_fundamentals_staleness_false_for_recent_filing(tmp_path, monkeypatch):
    monkeypatch.setattr("cache.CACHE_DIR", tmp_path)
    with patch("market_data.get_company_facts", return_value=_fake_edgar_facts()), \
         patch("market_data.yf.Ticker", return_value=_fake_yf_info()):
        result = get_fundamentals("AAPL", cik="0000320193")

    assert result["dataQuality"]["staleness"] is False


# --- Additional robustness tests (proactive, mirroring get_estimates()'s discipline) ---


def test_get_fundamentals_edgar_call_raises_falls_back_to_yfinance(tmp_path, monkeypatch):
    """get_company_facts() raising (network error, bad JSON, etc.) — not a clean
    404 — must not crash get_fundamentals(); it degrades to 'no EDGAR data'."""
    monkeypatch.setattr("cache.CACHE_DIR", tmp_path)
    with patch("market_data.get_company_facts", side_effect=ConnectionError("boom")), \
         patch("market_data.yf.Ticker", return_value=_fake_yf_info()):
        result = get_fundamentals("AAPL", cik="0000320193")

    assert result["revenue"]["source"] == "yfinance"
    assert result["revenue"]["value"] == 395000000000.0
    assert result["netIncome"]["source"] == "yfinance"


def test_get_fundamentals_yfinance_info_raises_falls_back_to_edgar_only(tmp_path, monkeypatch):
    """yf.Ticker(ticker).info raising must not crash the call — EDGAR-sourced
    metrics still come back, and no cross-source disagreement check is attempted."""
    monkeypatch.setattr("cache.CACHE_DIR", tmp_path)
    fake_ticker = MagicMock()
    type(fake_ticker).info = property(lambda self: (_ for _ in ()).throw(RuntimeError("boom")))
    with patch("market_data.get_company_facts", return_value=_fake_edgar_facts()), \
         patch("market_data.yf.Ticker", return_value=fake_ticker):
        result = get_fundamentals("AAPL", cik="0000320193")

    assert result["revenue"]["source"] == "edgar"
    assert result["revenue"]["value"] == 391035000000.0
    assert result["dataQuality"]["dataConflicts"] == []


def test_get_fundamentals_yfinance_info_is_none(tmp_path, monkeypatch):
    """Some yfinance versions/edge cases return None from .info instead of
    raising or returning a dict — must be treated as 'no yfinance data'."""
    monkeypatch.setattr("cache.CACHE_DIR", tmp_path)
    fake_ticker = MagicMock()
    fake_ticker.info = None
    with patch("market_data.get_company_facts", return_value=_fake_edgar_facts()), \
         patch("market_data.yf.Ticker", return_value=fake_ticker):
        result = get_fundamentals("AAPL", cik="0000320193")

    assert result["revenue"]["source"] == "edgar"
    assert result["dataQuality"]["dataConflicts"] == []


def test_get_fundamentals_missing_from_both_sources_is_absent_not_zero(tmp_path, monkeypatch):
    """When neither EDGAR nor yfinance has a metric at all, that metric key
    must be entirely absent from the result — never fabricated as 0.0."""
    monkeypatch.setattr("cache.CACHE_DIR", tmp_path)
    edgar_partial = {"revenue": _fake_edgar_facts()["revenue"]}  # no netIncome
    fake_ticker = MagicMock()
    fake_ticker.info = {"totalRevenue": 395000000000.0}  # no netIncomeToCommon either
    with patch("market_data.get_company_facts", return_value=edgar_partial), \
         patch("market_data.yf.Ticker", return_value=fake_ticker):
        result = get_fundamentals("AAPL", cik="0000320193")

    assert "netIncome" not in result
    assert result["revenue"]["value"] == 391035000000.0


def test_get_fundamentals_operating_income_stays_edgar_only(tmp_path, monkeypatch):
    """operatingIncome is an explicit scope boundary: EDGAR-only for this task.
    Even with plausible yfinance fields present (operatingMargins/totalRevenue),
    no yfinance-derived operatingIncome should be fabricated when EDGAR lacks it."""
    monkeypatch.setattr("cache.CACHE_DIR", tmp_path)
    edgar_no_opinc = {"revenue": _fake_edgar_facts()["revenue"]}  # no operatingIncome
    fake_ticker = MagicMock()
    fake_ticker.info = {
        "totalRevenue": 395000000000.0,
        "operatingMargins": 0.30,
    }
    with patch("market_data.get_company_facts", return_value=edgar_no_opinc), \
         patch("market_data.yf.Ticker", return_value=fake_ticker):
        result = get_fundamentals("AAPL", cik="0000320193")

    assert "operatingIncome" not in result
