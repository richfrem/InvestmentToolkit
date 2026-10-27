"""
test_price_changes.py — the single % change calculation for price periods.

price_changes.period_changes() replaces two diverging copies (fetch_financials
'performance' and history_store.calc_changes) that disagreed on 1W/1M/3M
offsets and reported missing data as 0.0%.
"""
import sys
from datetime import date, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "plugins/stock-valuation/scripts"))

from price_changes import PERIODS, period_changes  # noqa: E402


def _weekday_series(start: date, end: date, price_for):
    """Closes on every weekday from start to end inclusive (weekends skipped like a real market)."""
    dates, closes = [], []
    d = start
    while d <= end:
        if d.weekday() < 5:
            dates.append(d.isoformat())
            closes.append(price_for(d))
        d += timedelta(days=1)
    return dates, closes


def test_periods_are_the_shared_set():
    assert PERIODS == ("1d", "1w", "1m", "3m", "ytd", "1y", "5y")


def test_calendar_lookbacks_use_last_close_on_or_before_the_target_date():
    as_of = date(2026, 9, 25)                       # a Friday
    dates, closes = _weekday_series(date(2025, 9, 1), as_of, lambda d: 100.0)
    marks = {
        date(2026, 9, 24): 90.0,   # previous session      -> 1d
        date(2026, 9, 18): 80.0,   # as_of - 7 days        -> 1w
        date(2026, 8, 25): 50.0,   # as_of - 1 month       -> 1m
        date(2026, 6, 25): 40.0,   # as_of - 3 months      -> 3m
        date(2025, 9, 25): 25.0,   # as_of - 1 year        -> 1y
        date(2025, 12, 31): 20.0,  # prior year's last close -> ytd
    }
    closes = [marks.get(date.fromisoformat(d), c) for d, c in zip(dates, closes)]
    ch = period_changes(dates, closes)
    assert round(ch["1d"], 4) == round((100 / 90 - 1) * 100, 4)
    assert ch["1w"] == 25.0
    assert ch["1m"] == 100.0
    assert ch["3m"] == 150.0
    assert ch["1y"] == 300.0
    assert ch["ytd"] == 400.0


def test_target_on_a_weekend_uses_the_prior_friday():
    # as_of Mon 2026-09-28; 1w target Mon 09-21 exists; 1m target 08-28 (Fri) exists;
    # 3m target 2026-06-28 is a Sunday -> must use Fri 06-26.
    as_of = date(2026, 9, 28)
    dates, closes = _weekday_series(date(2026, 1, 1), as_of, lambda d: 50.0 if d == date(2026, 6, 26) else 100.0)
    assert period_changes(dates, closes)["3m"] == 100.0


def test_live_price_overrides_last_close():
    dates, closes = _weekday_series(date(2026, 9, 1), date(2026, 9, 25), lambda d: 100.0)
    ch = period_changes(dates, closes, current_price=110.0)
    assert round(ch["1w"], 6) == 10.0


def test_missing_history_is_none_not_zero():
    dates, closes = _weekday_series(date(2026, 8, 1), date(2026, 9, 25), lambda d: 100.0)
    ch = period_changes(dates, closes)
    assert ch["1y"] is None and ch["5y"] is None and ch["3m"] is None
    assert ch["1m"] == 0.0            # genuinely unchanged is still 0.0
    assert period_changes([], []) == {p: None for p in PERIODS}


def test_reference_dates_are_the_single_definition_of_each_period():
    from price_changes import period_reference_dates
    refs = period_reference_dates(date(2026, 3, 31))
    assert refs == {
        "1d": date(2026, 3, 30),
        "1w": date(2026, 3, 24),
        "1m": date(2026, 2, 28),      # calendar month, clamped (not "30 days")
        "3m": date(2025, 12, 31),
        "ytd": date(2025, 12, 31),    # prior year's last day
        "1y": date(2025, 3, 31),
        "5y": date(2021, 3, 31),
    }


def test_period_changes_uses_the_reference_dates():
    from price_changes import period_reference_dates
    as_of = date(2026, 9, 25)
    dates, closes = _weekday_series(date(2025, 1, 1), as_of, lambda d: float(d.toordinal() % 50 + 50))
    refs = period_reference_dates(as_of)
    ch = period_changes(dates, closes)
    for p in ("1w", "1m", "3m", "1y"):
        base = [c for d, c in zip(dates, closes) if d <= refs[p].isoformat()][-1]
        assert ch[p] == round((closes[-1] / base - 1) * 100, 4)
