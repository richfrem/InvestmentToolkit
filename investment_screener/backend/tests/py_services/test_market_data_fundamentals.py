import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock

import pandas as pd

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


def _fake_yf_financials_df(revenue=395000000000.0, net_income=94000000000.0):
    """Build a fake yfinance `.financials` annual income-statement DataFrame.

    Shape mirrors real yfinance: index is line items ("Total Revenue", "Net
    Income"), columns are fiscal year-end Timestamps with the most recent
    column first.
    """
    return pd.DataFrame(
        {pd.Timestamp("2025-09-27"): [revenue, net_income]},
        index=["Total Revenue", "Net Income"],
    )


def _fake_yf_info():
    fake_ticker = MagicMock()
    fake_ticker.info = {
        "totalRevenue": 395000000000.0,  # ~1% off EDGAR, within threshold
        "netIncomeToCommon": 94000000000.0,
    }
    # Annual figures used ONLY for the disagreement cross-check — matches
    # .info here (within threshold) so tests not focused on disagreement
    # stay unaffected.
    fake_ticker.financials = _fake_yf_financials_df()
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
    fake_yf.info = {"totalRevenue": 500000000000.0, "netIncomeToCommon": 94000000000.0}  # way off (TTM, unused for the check itself)
    # The disagreement check compares EDGAR's annual figure against
    # yfinance's own ANNUAL figure (.financials), not .info's TTM fields —
    # this must also be "way off" for the conflict to fire.
    fake_yf.financials = _fake_yf_financials_df(revenue=500000000000.0, net_income=94000000000.0)
    with patch("market_data.get_company_facts", return_value=_fake_edgar_facts()), \
         patch("market_data.yf.Ticker", return_value=fake_yf):
        result = get_fundamentals("AAPL", cik="0000320193")

    assert len(result["dataQuality"]["dataConflicts"]) >= 1
    # still returns the EDGAR value — disagreement is flagged, not auto-resolved
    assert result["revenue"]["value"] == 391035000000.0


def test_get_fundamentals_no_disagreement_when_annual_figures_actually_agree(tmp_path, monkeypatch):
    """Regression test for the annual-vs-TTM mismatch bug: EDGAR's annual
    revenue vs. yfinance's TTM totalRevenue would differ by far more than 5%
    for a growing company as a matter of routine — but when compared against
    yfinance's own ANNUAL figure (which genuinely agrees with EDGAR), no
    conflict should fire, even though the TTM figure is wildly different."""
    monkeypatch.setattr("cache.CACHE_DIR", tmp_path)
    fake_yf = MagicMock()
    # TTM (.info) is ~28% higher than EDGAR's annual figure — would trip the
    # 5% threshold if compared directly (the exact bug this finding fixes).
    fake_yf.info = {"totalRevenue": 500000000000.0, "netIncomeToCommon": 94000000000.0}
    # But yfinance's own ANNUAL figure agrees with EDGAR within threshold.
    fake_yf.financials = _fake_yf_financials_df(revenue=391035000000.0, net_income=93736000000.0)
    with patch("market_data.get_company_facts", return_value=_fake_edgar_facts()), \
         patch("market_data.yf.Ticker", return_value=fake_yf):
        result = get_fundamentals("AAPL", cik="0000320193")

    assert result["dataQuality"]["dataConflicts"] == []
    assert result["revenue"]["value"] == 391035000000.0


def test_get_fundamentals_financials_raises_skips_disagreement_check(tmp_path, monkeypatch):
    """yf.Ticker(ticker).financials raising must not crash get_fundamentals()
    — it degrades to 'no annual figure available', so the disagreement check
    is skipped for that metric rather than fabricating a comparison."""
    monkeypatch.setattr("cache.CACHE_DIR", tmp_path)
    fake_yf = MagicMock()
    fake_yf.info = {"totalRevenue": 395000000000.0, "netIncomeToCommon": 94000000000.0}
    type(fake_yf).financials = property(lambda self: (_ for _ in ()).throw(RuntimeError("boom")))
    with patch("market_data.get_company_facts", return_value=_fake_edgar_facts()), \
         patch("market_data.yf.Ticker", return_value=fake_yf):
        result = get_fundamentals("AAPL", cik="0000320193")

    assert result["revenue"]["source"] == "edgar"
    assert result["dataQuality"]["dataConflicts"] == []


def test_get_fundamentals_financials_empty_skips_disagreement_check(tmp_path, monkeypatch):
    """An empty `.financials` DataFrame (e.g. a ticker with no annual
    filings yet) must degrade to 'no annual figure available', not crash."""
    monkeypatch.setattr("cache.CACHE_DIR", tmp_path)
    fake_yf = MagicMock()
    fake_yf.info = {"totalRevenue": 395000000000.0, "netIncomeToCommon": 94000000000.0}
    fake_yf.financials = pd.DataFrame()
    with patch("market_data.get_company_facts", return_value=_fake_edgar_facts()), \
         patch("market_data.yf.Ticker", return_value=fake_yf):
        result = get_fundamentals("AAPL", cik="0000320193")

    assert result["revenue"]["source"] == "edgar"
    assert result["dataQuality"]["dataConflicts"] == []


def test_get_fundamentals_financials_missing_expected_row_skips_disagreement_check(
    tmp_path, monkeypatch
):
    """A `.financials` DataFrame that doesn't have the expected row (e.g.
    upstream naming drift) must degrade to 'no annual figure available' for
    that metric, not crash or fabricate a comparison value."""
    monkeypatch.setattr("cache.CACHE_DIR", tmp_path)
    fake_yf = MagicMock()
    fake_yf.info = {"totalRevenue": 395000000000.0, "netIncomeToCommon": 94000000000.0}
    fake_yf.financials = pd.DataFrame(
        {pd.Timestamp("2025-09-27"): [1.0]}, index=["Some Other Line Item"]
    )
    with patch("market_data.get_company_facts", return_value=_fake_edgar_facts()), \
         patch("market_data.yf.Ticker", return_value=fake_yf):
        result = get_fundamentals("AAPL", cik="0000320193")

    assert result["revenue"]["source"] == "edgar"
    assert result["dataQuality"]["dataConflicts"] == []


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


def test_get_fundamentals_includes_debt_cash_interest_from_yfinance(tmp_path, monkeypatch):
    monkeypatch.setattr("cache.CACHE_DIR", tmp_path)
    fake_yf = MagicMock()
    fake_yf.info = {
        "totalRevenue": 395000000000.0,
        "netIncomeToCommon": 94000000000.0,
        "totalDebt": 120000000000.0,
        "totalCash": 65000000000.0,
        "interestExpense": 3900000000.0,
    }
    fake_yf.financials = _fake_yf_financials_df()
    with patch("market_data.get_company_facts", return_value=_fake_edgar_facts()), \
         patch("market_data.yf.Ticker", return_value=fake_yf):
        result = get_fundamentals("AAPL", cik="0000320193")

    assert result["totalDebt"]["value"] == 120000000000.0
    assert result["totalDebt"]["source"] == "yfinance"
    assert result["cashAndEquivalents"]["value"] == 65000000000.0
    assert result["cashAndEquivalents"]["source"] == "yfinance"
    assert result["interestExpense"]["value"] == 3900000000.0
    assert result["interestExpense"]["source"] == "yfinance"


def test_get_fundamentals_omits_debt_cash_interest_when_yfinance_lacks_them(tmp_path, monkeypatch):
    monkeypatch.setattr("cache.CACHE_DIR", tmp_path)
    fake_yf = MagicMock()
    fake_yf.info = {"totalRevenue": 395000000000.0, "netIncomeToCommon": 94000000000.0}
    fake_yf.financials = _fake_yf_financials_df()
    with patch("market_data.get_company_facts", return_value=_fake_edgar_facts()), \
         patch("market_data.yf.Ticker", return_value=fake_yf):
        result = get_fundamentals("AAPL", cik="0000320193")

    assert "totalDebt" not in result
    assert "cashAndEquivalents" not in result
    assert "interestExpense" not in result


def test_get_fundamentals_includes_ebitda_current_ratio_and_free_cash_flow():
    """New yfinance-only fields needed by framework_score.py (Phase 2b)."""
    fake_info = {
        "totalRevenue": 1_000_000.0,
        "ebitda": 250_000.0,
        "currentRatio": 1.8,
        "freeCashflow": 120_000.0,
    }
    with patch("market_data._safe_yf_info", return_value=fake_info), \
         patch("market_data._safe_edgar_facts", return_value={}), \
         patch("market_data.cache_get", return_value=None), \
         patch("market_data.cache_set"):
        result = get_fundamentals("TEST", cik=None)

    assert result["ebitda"]["value"] == 250_000.0
    assert result["ebitda"]["source"] == "yfinance"
    assert result["currentRatio"]["value"] == 1.8
    assert result["freeCashflow"]["value"] == 120_000.0


def test_get_fundamentals_omits_ebitda_when_absent_from_yfinance():
    """A ticker with no ebitda in yfinance .info must not get a zeroed field."""
    fake_info = {"totalRevenue": 1_000_000.0}
    with patch("market_data._safe_yf_info", return_value=fake_info), \
         patch("market_data._safe_edgar_facts", return_value={}), \
         patch("market_data.cache_get", return_value=None), \
         patch("market_data.cache_set"):
        result = get_fundamentals("TEST", cik=None)

    assert "ebitda" not in result
