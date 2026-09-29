#!/usr/bin/env python3
"""
price_changes.py — the single % change calculation for price periods.

Purpose:
    One definition of "1D / 1W / 1M / 3M / YTD / 1Y / 5Y change" for every
    surface: fetch_financials 'performance' (Stock Analysis chips) and
    history_store.calc_changes (heatmap, Portfolio Table, Screener). Before
    2026-09-28 those were two copies that disagreed (1W was 4 trading days back
    in one and 5 in the other) and one reported missing history as 0.0%.

Definition:
    - Lookbacks are calendar-based: change vs the last close on or before
      (as_of - period), like Yahoo / TradingView, so weekends and holidays need
      no trading-day approximations.
    - 1D is vs the last close strictly before as_of.
    - YTD is vs the prior year's last close.
    - Missing history returns None, never 0.0.

Layer:
    plugins/stock-valuation/scripts/ (canonical; symlinked into
    investment_screener/backend/py_services/ and the update-stock-analysis skill)

Usage:
    from price_changes import period_changes
    period_changes(["2026-09-24", "2026-09-25"], [100.0, 101.0])  # {"1d": 1.0, ...}

Key Functions (Index):
    - period_reference_dates(as_of) - the one date rule per period
    - period_changes(dates, closes, current_price, as_of) - % change per period
    - _shift_months(d, months) - calendar month shift clamped to month end
    - _close_on_or_before(dates, closes, target) - last close at/before a date

Key Input Dependencies:
    None (pure standard library)
"""
from bisect import bisect_right
from calendar import monthrange
from datetime import date, timedelta
from typing import Optional, Sequence

PERIODS = ("1d", "1w", "1m", "3m", "ytd", "1y", "5y")


def _shift_months(d: date, months: int) -> date:
    """Return d moved by `months` calendar months, clamped to the target month's last day."""
    month_index = d.year * 12 + (d.month - 1) + months
    year, month = divmod(month_index, 12)
    month += 1
    return date(year, month, min(d.day, monthrange(year, month)[1]))


def _close_on_or_before(dates: Sequence[str], closes: Sequence[float], target: date) -> Optional[float]:
    """Last close dated on or before target, or None if history starts after target."""
    idx = bisect_right(dates, target.isoformat()) - 1
    return closes[idx] if idx >= 0 else None


def period_reference_dates(as_of: date) -> dict[str, date]:
    """The single definition of each period's reference date.

    A period's change compares against the last close on or before this date.
    Used by period_changes() (per stock) and portfolio_performance (whole
    portfolio), so "1M ago" means the same thing everywhere.
    """
    return {
        "1d": as_of - timedelta(days=1),
        "1w": as_of - timedelta(days=7),
        "1m": _shift_months(as_of, -1),
        "3m": _shift_months(as_of, -3),
        "ytd": date(as_of.year - 1, 12, 31),
        "1y": _shift_months(as_of, -12),
        "5y": _shift_months(as_of, -60),
    }


def period_changes(
    dates: Sequence[str],
    closes: Sequence[float],
    current_price: Optional[float] = None,
    as_of: Optional[date] = None,
) -> dict[str, Optional[float]]:
    """% change for each period in PERIODS.

    Args:
        dates: ISO dates (YYYY-MM-DD), ascending, one per close.
        closes: Daily closes matching `dates`.
        current_price: Latest price (e.g. live quote); defaults to the last close.
        as_of: Date the current price belongs to; defaults to the last close's date.

    Returns:
        {period: percent change rounded to 4 dp, or None when history doesn't reach}.
    """
    if not dates or not closes or len(dates) != len(closes):
        return {p: None for p in PERIODS}
    as_of = as_of or date.fromisoformat(dates[-1])
    current = current_price if current_price is not None else closes[-1]
    if not current or current <= 0:
        return {p: None for p in PERIODS}

    def pct(base: Optional[float]) -> Optional[float]:
        if base is None or base <= 0:
            return None
        return round((current / base - 1) * 100, 4)

    earliest = date.fromisoformat(dates[0])
    refs = period_reference_dates(as_of)

    def lookback(target: date) -> Optional[float]:
        # A target before the first stored close can't be answered from this history.
        return None if target < earliest else pct(_close_on_or_before(dates, closes, target))

    return {p: lookback(refs[p]) for p in PERIODS}
