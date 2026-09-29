#!/usr/bin/env python3
"""
history_store.py - Python utility script.

Purpose:
    Provides a persistent, CSV-based historical price store for portfolio holdings.
    Implements a rolling 365-day window with incremental yfinance updates to minimize API overhead.
    Used primarily for calculating period performance (1w, 1m, YTD, 1y).

Layer:
    Backend / Python Services

Usage Examples:
    TBD

Key Functions (Index):
    - HistoricalPriceStore()
    - __init__()
    - get_or_update()
    - calc_changes()
    - pct()
    - _csv_path()
    - _load()
    - _save()
    - _fetch_full()
    - _fetch_incremental()
    - _trim()
    - _df_to_rows()
    - _empty_changes()

Key Input Dependencies:
    None

Key Output Dependencies:
    None
"""
import os
import csv
import logging
from datetime import date, timedelta, datetime

from price_changes import period_changes

import yfinance as yf

logger = logging.getLogger(__name__)

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")
HISTORY_DAYS = 380  # rolling window: 1 year + slack so the 1Y lookback (calendar-based) always has a close


class HistoricalPriceStore:

    def __init__(self, cache_dir: str = CACHE_DIR):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_or_update(self, symbol: str) -> list[dict]:
        """
        Return a sorted list of {date, close} dicts covering HISTORY_DAYS.
        Fetches full history on first call; incremental on subsequent calls.
        """
        rows = self._load(symbol)

        # A cache that doesn't reach the start of the window (e.g. written under
        # an older, shorter HISTORY_DAYS) can't be fixed incrementally, which only
        # appends newer days — refetch it in full.
        window_start = (date.today() - timedelta(days=HISTORY_DAYS - 7)).isoformat()
        if not rows or rows[0]["date"] > window_start:
            rows = self._fetch_full(symbol)
        else:
            rows = self._fetch_incremental(symbol, rows)

        rows = self._trim(rows)
        self._save(symbol, rows)
        return rows

    def calc_changes(self, symbol: str, current_price: float) -> dict:
        """
        % change for the heatmap / table periods, via the shared
        price_changes.period_changes() so every surface uses one definition.
        Returns change_1w, change_1m, change_3m, change_ytd, change_1y
        (percent, 2 dp) or None where the stored history doesn't reach.
        """
        rows = self.get_or_update(symbol)
        if not rows or current_price <= 0:
            return self._empty_changes()
        changes = period_changes(
            [r["date"] for r in rows], [r["close"] for r in rows],
            current_price=current_price, as_of=date.today(),
        )
        return {
            f"change_{p}": (round(changes[p], 2) if changes[p] is not None else None)
            for p in ("1w", "1m", "3m", "ytd", "1y")
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _csv_path(self, symbol: str) -> str:
        safe = "".join(c for c in symbol if c.isalnum() or c in ("-", "."))
        return os.path.join(self.cache_dir, f"{safe}_history.csv")

    def _load(self, symbol: str) -> list[dict]:
        path = self._csv_path(symbol)
        if not os.path.exists(path):
            return []
        rows = []
        try:
            with open(path, newline="") as f:
                for row in csv.DictReader(f):
                    rows.append({"date": row["date"], "close": float(row["close"])})
        except Exception as e:
            logger.warning(f"[HistoryStore] Failed to read {path}: {e}")
            return []
        return sorted(rows, key=lambda r: r["date"])

    def _save(self, symbol: str, rows: list[dict]) -> None:
        path = self._csv_path(symbol)
        try:
            with open(path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["date", "close"])
                writer.writeheader()
                writer.writerows(rows)
        except Exception as e:
            logger.warning(f"[HistoryStore] Failed to write {path}: {e}")

    def _fetch_full(self, symbol: str) -> list[dict]:
        """Baseline: pull exactly HISTORY_DAYS of data using an explicit date range."""
        start = (date.today() - timedelta(days=HISTORY_DAYS)).isoformat()
        end   = (date.today() + timedelta(days=1)).isoformat()
        logger.info(f"[HistoryStore] Full fetch for {symbol}  {start} → {end}")
        try:
            hist = yf.Ticker(symbol).history(start=start, end=end)
            if hist.empty:
                return []
            return self._df_to_rows(hist)
        except Exception as e:
            logger.warning(f"[HistoryStore] Full fetch failed for {symbol}: {e}")
            return []

    def _fetch_incremental(self, symbol: str, existing: list[dict]) -> list[dict]:
        """Pull only the gap: last cached date+1 → today (exact date range)."""
        last_date_str = existing[-1]["date"]
        last_date = datetime.strptime(last_date_str, "%Y-%m-%d").date()
        today = date.today()

        if last_date >= today:
            # Already up to date (or today not closed yet)
            return existing

        start = last_date + timedelta(days=1)
        end   = today + timedelta(days=1)  # yfinance end is exclusive
        gap_days = (today - last_date).days
        logger.info(f"[HistoryStore] Incremental fetch for {symbol}  {start} → {today}  ({gap_days} calendar days)")
        try:
            hist = yf.Ticker(symbol).history(start=start.isoformat(), end=end.isoformat())
            if hist.empty:
                return existing
            new_rows = self._df_to_rows(hist)
            # Merge: avoid duplicates by date key
            existing_dates = {r["date"] for r in existing}
            merged = existing + [r for r in new_rows if r["date"] not in existing_dates]
            return sorted(merged, key=lambda r: r["date"])
        except Exception as e:
            logger.warning(f"[HistoryStore] Incremental fetch failed for {symbol}: {e}")
            return existing

    def _trim(self, rows: list[dict]) -> list[dict]:
        """Remove rows older than HISTORY_DAYS calendar days."""
        cutoff = (date.today() - timedelta(days=HISTORY_DAYS)).isoformat()
        return [r for r in rows if r["date"] >= cutoff]

    @staticmethod
    def _df_to_rows(hist) -> list[dict]:
        rows = []
        for ts, row in hist.iterrows():
            date_str = ts.date().isoformat() if hasattr(ts, "date") else str(ts)[:10]
            close = float(row["Close"])
            if close > 0:
                rows.append({"date": date_str, "close": close})
        return rows

    @staticmethod
    def _empty_changes() -> dict:
        return {"change_1w": None, "change_1m": None, "change_3m": None, "change_ytd": None, "change_1y": None}
