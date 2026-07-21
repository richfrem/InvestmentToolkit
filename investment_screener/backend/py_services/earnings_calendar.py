#!/usr/bin/env python3
"""
earnings_calendar.py - Python utility script.

Purpose:
    Earnings calendar — flags portfolio holdings with upcoming binary events.

Fetches next earnings dates via yfinance for all active holdings and
classifies proximity. Used by the daily brief to gate position sizing
before binary events.

Usage:
    python3 earnings_calendar.py
    python3 earnings_calendar.py --days 14 --json

Key Input Dependencies:
    - investment_screener/backend/data/domain_model.sqlite (Finds upcoming holdings
      earnings; Wave 3 Task 6 cutover — previously portfolio.json)

Layer:
    Backend / Python Services

Usage Examples:
    python3 earnings_calendar.py
    python3 earnings_calendar.py --days 14 --json

Key Functions (Index):
    - EarningsEntry()
    - _load_tickers()
    - _fetch_earnings_date()
    - _flag()
    - get_earnings_calendar()
    - main()

Key Input Dependencies:
    None

Key Output Dependencies:
    None
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.portfolio_repository import load_portfolio_state_from_db  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]
DB_PATH = REPO_ROOT / "investment_screener/backend/data/domain_model.sqlite"
SKIP_TICKERS: frozenset[str] = frozenset({"PSU-U.TO", "PSU.U.TO", "USD_CASH"})

# ETFs and funds — no earnings dates exist; excluding them avoids yfinance 404s
# and prevents them being misreported as earnings-calendar "blind spots".
# DRAM = HBM/memory ETF · HUMN = humanoid robotics ETF · KOID = robotics ETF
ETF_TICKERS: frozenset[str] = frozenset({
    "DRAM", "HUMN", "KOID", "ETHA", "IBIT", "SOLZ", "DXYZ",
})


@dataclass
class EarningsEntry:
    """Earnings event for one holding."""

    ticker: str
    earnings_date: str | None
    days_away: int | None
    flag: str  # IMMINENT | APPROACHING | UPCOMING | OK | UNKNOWN


def _load_tickers(db_path: Path = DB_PATH) -> list[str]:
    """Load active ticker list from domain_model.sqlite (Wave 3 Task 6 cutover
    — previously portfolio.json).

    Returns:
        Sorted list of equity ticker symbols.
    """
    if not db_path.exists():
        return []
    conn = initialize_db(str(db_path))
    try:
        symbols = load_portfolio_state_from_db(conn)["shares"].keys()
    finally:
        conn.close()
    return sorted(
        s for s in symbols
        if s and s not in SKIP_TICKERS and s not in ETF_TICKERS
    )


def _fetch_earnings_date(ticker: str) -> tuple[str | None, int | None]:
    """Fetch next earnings date for a single ticker.

    Args:
        ticker: Stock ticker symbol.

    Returns:
        Tuple of (iso_date_string, days_until_earnings) or (None, None).
    """
    try:
        import yfinance as yf
        t = yf.Ticker(ticker)
        cal = t.calendar
        if cal is None:
            return None, None

        # yfinance returns a DataFrame — columns are dates, rows are event types
        import pandas as pd
        raw_dt = None
        if isinstance(cal, pd.DataFrame) and len(cal.columns) > 0:
            raw_dt = cal.columns[0]
        elif isinstance(cal, dict):
            dates = cal.get("Earnings Date", [])
            raw_dt = dates[0] if dates else None

        if raw_dt is None:
            return None, None

        earn_date = date.fromisoformat(str(raw_dt)[:10])

        days = (earn_date - date.today()).days
        return earn_date.isoformat(), days
    except Exception:
        return None, None


def _flag(days: int | None) -> str:
    """Classify earnings proximity.

    Args:
        days: Calendar days until earnings (negative = already reported).

    Returns:
        Flag string for urgency classification.
    """
    if days is None:
        return "UNKNOWN"
    if days < 0:
        return "OK"
    if days < 7:
        return "IMMINENT"
    if days < 14:
        return "APPROACHING"
    if days < 30:
        return "UPCOMING"
    return "OK"


def get_earnings_calendar(days_threshold: int = 30) -> list[EarningsEntry]:
    """Get upcoming earnings events for all portfolio holdings.

    Args:
        days_threshold: Include only events within this many days.

    Returns:
        EarningsEntry list sorted by days_away ascending, excluding OK/past.
    """
    tickers = _load_tickers()
    entries: list[EarningsEntry] = []

    for ticker in tickers:
        earn_date, days = _fetch_earnings_date(ticker)
        entry_flag = _flag(days)
        # Include only IMMINENT/APPROACHING/UPCOMING within threshold
        if days is not None and 0 <= days <= days_threshold:
            entries.append(EarningsEntry(
                ticker=ticker,
                earnings_date=earn_date,
                days_away=days,
                flag=entry_flag,
            ))
        elif entry_flag == "UNKNOWN":
            entries.append(EarningsEntry(
                ticker=ticker,
                earnings_date=None,
                days_away=None,
                flag="UNKNOWN",
            ))

    return sorted(
        entries,
        key=lambda e: (e.days_away if e.days_away is not None else 9999),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Earnings calendar checker")
    parser.add_argument("--days", type=int, default=30, help="Look-ahead window in days")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    args = parser.parse_args()

    entries = get_earnings_calendar(args.days)
    entries = [e for e in entries if e.flag != "UNKNOWN"]

    if args.json:
        print(json.dumps([{
            "ticker": e.ticker,
            "earnings_date": e.earnings_date,
            "days_away": e.days_away,
            "flag": e.flag,
        } for e in entries], indent=2))
        return

    if not entries:
        print(f"No earnings within {args.days} days.")
        return

    print(f"\nEarnings within {args.days} days:")
    icon_map = {"IMMINENT": "🔴", "APPROACHING": "🟡", "UPCOMING": "○"}
    for e in entries:
        icon = icon_map.get(e.flag, " ")
        print(f"  {icon} {e.ticker:<8} {e.earnings_date or 'unknown':<12} "
              f"({e.days_away:>3}d)  [{e.flag}]")


if __name__ == "__main__":
    main()
