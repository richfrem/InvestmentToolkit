"""
Caught live 2026-10-01 on MU: fetch_financials.py's "revenue" / "historical_revenue[-1]"
came from yfinance's ANNUAL income statement, so for a company whose fiscal year ended
months ago the "latest year" was a stale full fiscal year (MU: FY25's $37.38B, labelled
TTM, while four reported quarters through 2026-05-31 summed to ~$90B and FY26 actually
closed at $133.2B). Every downstream consumer (DCF base revenue, margins, P/S,
Rule-of-40) inherited the stale base. overlay_ttm() appends a trailing-twelve-month
column built from the last four reported quarters whenever the quarterly statement is
meaningfully newer than the annual one.

Run:
    python3 -m pytest investment_screener/backend/tests/py_services/test_fetch_financials_ttm_overlay.py -v
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))

from fetch_financials import overlay_ttm  # noqa: E402

ANNUAL_END = pd.Timestamp("2025-08-28")
Q_ENDS = [pd.Timestamp(d) for d in ("2025-08-28", "2025-11-30", "2026-02-28", "2026-05-31")]


def _annual():
    return pd.DataFrame(
        {pd.Timestamp("2024-08-29"): [25.111e9, 0.778e9], ANNUAL_END: [37.378e9, 8.539e9]},
        index=["Total Revenue", "Net Income"],
    )


def _quarterly(revs=(11.32e9, 13.643e9, 23.86e9, 41.456e9), nis=(1.0e9, 2.0e9, 3.0e9, 4.0e9)):
    # yfinance returns newest-first columns; overlay_ttm must not depend on column order.
    cols = list(reversed(Q_ENDS))
    return pd.DataFrame(
        {c: [r, n] for c, r, n in zip(cols, reversed(revs), reversed(nis))},
        index=["Total Revenue", "Net Income"],
    )


def test_flow_overlay_appends_ttm_column_from_last_four_quarters():
    out, applied = overlay_ttm(_annual(), _quarterly(), kind="flow")
    assert applied is True
    newest = out.columns.max()
    assert newest == Q_ENDS[-1]
    assert out.loc["Total Revenue", newest] == 11.32e9 + 13.643e9 + 23.86e9 + 41.456e9
    assert out.loc["Net Income", newest] == 10.0e9
    # annual history is preserved, oldest -> newest
    assert list(out.columns) == sorted(out.columns)
    assert out.loc["Total Revenue", ANNUAL_END] == 37.378e9


def test_no_overlay_when_quarterly_is_not_newer_than_annual():
    q = _quarterly()
    q = q.drop(columns=[Q_ENDS[-1], Q_ENDS[-2], Q_ENDS[-3]])  # newest quarter == annual date
    out, applied = overlay_ttm(_annual(), q, kind="flow")
    assert applied is False
    assert out.equals(_annual())


def test_no_overlay_with_fewer_than_four_quarters():
    q = _quarterly().iloc[:, :3]
    out, applied = overlay_ttm(_annual(), q, kind="flow")
    assert applied is False
    assert out.equals(_annual())


def test_flow_row_with_a_missing_quarter_stays_nan_not_partial_sum():
    q = _quarterly()
    q.loc["Net Income", Q_ENDS[1]] = np.nan
    out, applied = overlay_ttm(_annual(), q, kind="flow")
    assert applied is True
    assert pd.isna(out.loc["Net Income", Q_ENDS[-1]])
    assert not pd.isna(out.loc["Total Revenue", Q_ENDS[-1]])


def test_point_in_time_overlay_uses_latest_quarter_not_a_sum():
    ann = pd.DataFrame({ANNUAL_END: [100.0]}, index=["Total Assets"])
    q = pd.DataFrame({c: [v] for c, v in zip(Q_ENDS, (100.0, 110.0, 120.0, 130.0))}, index=["Total Assets"])
    out, applied = overlay_ttm(ann, q, kind="point")
    assert applied is True
    assert out.loc["Total Assets", Q_ENDS[-1]] == 130.0


def test_missing_or_empty_quarterly_returns_annual_unchanged():
    for q in (None, pd.DataFrame()):
        out, applied = overlay_ttm(_annual(), q, kind="flow")
        assert applied is False
        assert out.equals(_annual())


def test_result_is_trimmed_to_five_newest_columns():
    cols = [pd.Timestamp(f"{y}-08-28") for y in range(2021, 2026)]  # 5 annual columns
    ann = pd.DataFrame({c: [float(i)] for i, c in enumerate(cols)}, index=["Total Revenue"])
    q = pd.DataFrame({c: [1.0] for c in Q_ENDS}, index=["Total Revenue"])
    out, applied = overlay_ttm(ann, q, kind="flow")
    assert applied is True
    assert out.shape[1] == 5
    assert out.columns.max() == Q_ENDS[-1]
