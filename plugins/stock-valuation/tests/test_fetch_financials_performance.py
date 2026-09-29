"""
test_fetch_financials_performance.py — Stock Analysis 'performance' chips use the
shared price_changes.period_changes() (AGENTS.md rule 22), not a local copy.
Before 2026-09-28 the local copy took 1W as 4 trading days back and reported
missing history as 0.0%.
"""
import sys
from datetime import date
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "plugins/stock-valuation/scripts"))

from fetch_financials import compute_performance  # noqa: E402
from price_changes import PERIODS, period_changes  # noqa: E402


def _history(start: str, end: str, price_for) -> pd.DataFrame:
    idx = pd.bdate_range(start, end, tz="America/New_York")   # yfinance-style tz-aware index
    return pd.DataFrame({"Close": [price_for(d.date()) for d in idx]}, index=idx)


def test_performance_matches_the_shared_calculation():
    hist = _history("2024-01-01", "2026-09-25", lambda d: 10.0 + d.toordinal() % 29)
    perf = compute_performance(hist)
    shared = period_changes([d.date().isoformat() for d in hist.index], list(hist["Close"]))
    assert set(perf) == set(PERIODS)
    assert perf == shared


def test_performance_reports_missing_history_as_none():
    hist = _history("2026-08-03", "2026-09-25", lambda d: 100.0)
    perf = compute_performance(hist)
    assert perf["1y"] is None and perf["5y"] is None
    assert perf["1m"] == 0.0


def test_performance_of_empty_history_is_all_none():
    assert compute_performance(pd.DataFrame({"Close": []})) == {p: None for p in PERIODS}
