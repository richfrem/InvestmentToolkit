"""
test_history_store_changes.py — HistoricalPriceStore.calc_changes() delegates to
the shared price_changes.period_changes() (one definition of period % change for
heatmap, Portfolio Table, Screener and Stock Analysis). The math itself is tested
in plugins/stock-valuation/tests/test_price_changes.py.
"""
import sys
from datetime import date, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))

import history_store  # noqa: E402
from history_store import HistoricalPriceStore  # noqa: E402
from price_changes import period_changes  # noqa: E402


def _store(tmp_path, rows):
    store = HistoricalPriceStore(cache_dir=str(tmp_path))
    store.get_or_update = lambda symbol: rows
    return store


def _weekday_rows(days_back: int, price_for):
    today = date.today()
    rows = []
    for i in range(days_back, -1, -1):
        d = today - timedelta(days=i)
        if d.weekday() < 5:
            rows.append({"date": d.isoformat(), "close": price_for(d)})
    return rows


def test_calc_changes_matches_the_shared_calculation(tmp_path):
    rows = _weekday_rows(400, lambda d: 50.0 + d.toordinal() % 37)
    changes = _store(tmp_path, rows).calc_changes("APLD", 120.0)
    shared = period_changes([r["date"] for r in rows], [r["close"] for r in rows],
                            current_price=120.0, as_of=date.today())
    for p in ("1w", "1m", "3m", "ytd", "1y"):
        assert changes[f"change_{p}"] == (round(shared[p], 2) if shared[p] is not None else None)


def test_calc_changes_exposes_three_month_change(tmp_path):
    rows = _weekday_rows(200, lambda d: 100.0)
    assert _store(tmp_path, rows).calc_changes("APLD", 110.0)["change_3m"] == 10.0


def test_empty_history_reports_every_period_as_none(tmp_path):
    changes = _store(tmp_path, []).calc_changes("APLD", 100.0)
    assert set(changes) == {"change_1w", "change_1m", "change_3m", "change_ytd", "change_1y"}
    assert all(v is None for v in changes.values())


def test_history_window_reaches_one_year_back():
    # The rolling window must cover as_of - 1 year plus weekend/holiday slack,
    # otherwise 1Y is always None under the shared calendar rule.
    assert history_store.HISTORY_DAYS >= 372


def test_cache_shorter_than_the_window_is_refetched_in_full(tmp_path):
    # CSVs cached under the old 365-day window never reach 1 year back; an
    # incremental update only appends newer days, so they must be refetched.
    store = HistoricalPriceStore(cache_dir=str(tmp_path))
    old = _weekday_rows(365, lambda d: 100.0)
    full = _weekday_rows(history_store.HISTORY_DAYS, lambda d: 100.0)
    calls = []
    store._load = lambda s: old
    store._fetch_full = lambda s: calls.append("full") or full
    store._fetch_incremental = lambda s, rows: calls.append("incremental") or rows
    store._save = lambda s, rows: None
    assert store.get_or_update("APLD")[0]["date"] == full[0]["date"]
    assert calls == ["full"]


def test_cache_covering_the_window_updates_incrementally(tmp_path):
    store = HistoricalPriceStore(cache_dir=str(tmp_path))
    rows = _weekday_rows(history_store.HISTORY_DAYS, lambda d: 100.0)
    calls = []
    store._load = lambda s: rows
    store._fetch_full = lambda s: calls.append("full") or rows
    store._fetch_incremental = lambda s, r: calls.append("incremental") or r
    store._save = lambda s, r: None
    store.get_or_update("APLD")
    assert calls == ["incremental"]
