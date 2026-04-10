#!/usr/bin/env python3
"""
history_store.py - Persistent CSV-based historical price store for portfolio stocks.

Storage: py_services/cache/<SYMBOL>_history.csv
Schema:  date (YYYY-MM-DD), close

Strategy:
  - First run:        fetch 1 full year via yfinance (period="1y")
  - Incremental run:  fetch only dates after last cached date
  - Rolling window:   drop rows older than 365 calendar days after each update
  - ~252 rows/stock × 30 stocks = ~7,560 rows total — very lightweight

Usage:
    from history_store import HistoricalPriceStore
    store = HistoricalPriceStore()
    df = store.get_or_update("AAPL")   # returns DataFrame with [date, close]
    changes = store.calc_changes("AAPL", current_price=185.20)
"""

import os
import csv
import logging
from datetime import date, timedelta, datetime

import yfinance as yf

logger = logging.getLogger(__name__)

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")
HISTORY_DAYS = 365  # rolling window


class HistoricalPriceStore:

    def __init__(self, cache_dir: str = CACHE_DIR):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_or_update(self, symbol: str) -> list[dict]:
        """
        Return a sorted list of {date, close} dicts for the past year.
        Fetches full history on first call; incremental on subsequent calls.
        """
        rows = self._load(symbol)

        if not rows:
            rows = self._fetch_full(symbol)
        else:
            rows = self._fetch_incremental(symbol, rows)

        rows = self._trim(rows)
        self._save(symbol, rows)
        return rows

    def calc_changes(self, symbol: str, current_price: float) -> dict:
        """
        Derive % change for common periods from the stored history.
        Returns a dict with keys: change_1w, change_1m, change_ytd, change_1y.
        Values are floats (percent) or None if not enough history.
        """
        rows = self.get_or_update(symbol)
        if not rows or current_price <= 0:
            return self._empty_changes()

        closes = rows  # already sorted oldest → newest

        def pct(past_close: float) -> float | None:
            if past_close and past_close > 0:
                return round(((current_price - past_close) / past_close) * 100, 2)
            return None

        # Trading-day offsets (approximate)
        n = len(closes)
        change_1w  = pct(closes[-6]["close"])  if n >= 6   else None
        change_1m  = pct(closes[-22]["close"]) if n >= 22  else None
        change_1y  = pct(closes[0]["close"])   if n >= 200 else None  # ~252 days, accept 200 min

        # YTD: first close of current calendar year
        current_year = date.today().year
        ytd_rows = [r for r in closes if r["date"].startswith(str(current_year))]
        change_ytd = pct(ytd_rows[0]["close"]) if ytd_rows else None

        return {
            "change_1w":  change_1w,
            "change_1m":  change_1m,
            "change_ytd": change_ytd,
            "change_1y":  change_1y,
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
        return {"change_1w": None, "change_1m": None, "change_ytd": None, "change_1y": None}
