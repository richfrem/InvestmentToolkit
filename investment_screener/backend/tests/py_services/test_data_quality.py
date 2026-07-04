import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from data_quality import check_disagreement, check_staleness  # noqa: E402


def test_check_disagreement_returns_none_when_within_threshold():
    result = check_disagreement(edgar_value=100.0, yfinance_value=103.0, metric_name="revenue")
    assert result is None


def test_check_disagreement_flags_when_beyond_threshold():
    result = check_disagreement(edgar_value=100.0, yfinance_value=110.0, metric_name="revenue")
    assert result is not None
    assert result["metric"] == "revenue"
    assert result["diffPct"] == 10.0


def test_check_disagreement_at_exact_threshold_boundary_is_not_flagged():
    # exactly 5.0% must not be flagged (threshold is inclusive of "within")
    result = check_disagreement(edgar_value=100.0, yfinance_value=105.0, metric_name="revenue")
    assert result is None


def test_check_disagreement_handles_zero_edgar_value_without_crashing():
    # edgar_value=0 would divide-by-zero on the naive percentage formula — must not crash
    result = check_disagreement(edgar_value=0.0, yfinance_value=110.0, metric_name="revenue")
    assert result is None


def test_check_staleness_returns_false_for_recent_date():
    recent = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")
    assert check_staleness(recent) is False


def test_check_staleness_returns_true_for_old_date():
    old = (datetime.now(timezone.utc) - timedelta(days=200)).strftime("%Y-%m-%d")
    assert check_staleness(old) is True


def test_check_staleness_at_exact_boundary_is_not_stale():
    boundary = (datetime.now(timezone.utc) - timedelta(days=120)).strftime("%Y-%m-%d")
    assert check_staleness(boundary) is False


def test_check_staleness_raises_on_malformed_date_string():
    # This is a programming-error contract, not an external-data-quality gap: callers
    # (market_data.py) already normalize dates to %Y-%m-%d before calling this. A malformed
    # string here indicates a bug in the caller, not missing/bad market data - it must
    # raise loudly (ValueError from strptime) rather than silently returning False/True.
    import pytest
    with pytest.raises(ValueError):
        check_staleness("not-a-date")
