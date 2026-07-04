"""
market_data.py (Python Service)
=====================================

Purpose:
    Single provider-abstracted interface for prices, quotes, analyst estimates,
    and fundamentals. Every returned field is source-tagged {"value","source","asOf"}
    (or, for get_prices/get_quote/get_estimates, the whole response is tagged since
    there is only ever one real provider per call). Only get_fundamentals() has a
    real multi-provider waterfall (EDGAR primary, yfinance supplement) — see
    docs/superpowers/specs/2026-07-02-data-layer-design.md.

    Never returns a zeroed/defaulted value for missing data — a missing field is
    absent from the response, not present-and-wrong. This applies equally to
    partial/NaN rows from upstream providers: a NaN value must never be
    silently coerced to zero, and must never crash the whole batch request
    either — the affected row is simply omitted for that ticker.

Layer: Backend / Python Services / Data Layer
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yfinance as yf

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cache import cache_get, cache_set  # noqa: E402
from edgar_facts import get_company_facts  # noqa: E402
from data_quality import check_disagreement, check_staleness  # noqa: E402


def _now_iso() -> str:
    """Return current UTC time in ISO 8601 format.

    Returns:
        ISO 8601 datetime string (UTC).
    """
    return datetime.now(timezone.utc).isoformat()


def get_prices(tickers: list[str], period: str, interval: str = "1d") -> dict[str, dict]:
    """Fetch OHLCV price data for one or more tickers.

    Attempts to retrieve prices from cache first. For any ticker not in cache,
    fetches from yfinance, caches the result, and returns it tagged with the source.

    Args:
        tickers: List of ticker symbols (e.g., ["AAPL", "MSFT"]).
        period: Time period for historical data (e.g., "5d", "1mo", "1y").
        interval: Candle interval (default "1d" for daily).

    Returns:
        Dict mapping ticker to result dict. Each result has:
            - "data": List of OHLCV dicts with keys date, open, high, low, close, volume.
            - "source": "yfinance" or "cache".
            - "asOf": ISO 8601 timestamp of fetch/cache.
    """
    result = {}
    to_fetch = []
    for t in tickers:
        cached = cache_get(f"{t}_{period}_{interval}", "ohlcv")
        if cached is not None:
            result[t] = {**cached, "source": "cache"}
        else:
            to_fetch.append(t)

    if not to_fetch:
        return result

    raw = yf.download(to_fetch, period=period, interval=interval, auto_adjust=True, progress=False)
    if raw is None or raw.empty:
        return result

    for t in to_fetch:
        try:
            if isinstance(raw.columns, type(raw.columns)) and hasattr(raw.columns, "levels"):
                sub = raw.xs(t, axis=1, level=1)
            else:
                sub = raw
        except KeyError:
            continue
        rows = []
        for idx, row in sub.iterrows():
            o, hi, lo, c, v = (
                row.get("Open"), row.get("High"), row.get("Low"),
                row.get("Close"), row.get("Volume"),
            )
            # Misaligned trading calendars (e.g. a TSX ticker alongside a NASDAQ
            # ticker) leave real NaN values — not missing keys — for the ticker
            # that didn't trade that day. Skip the row for this ticker rather
            # than crash (int(NaN) raises ValueError) or fabricate a zero.
            if any(pd.isna(field) for field in (o, hi, lo, c, v)):
                continue
            rows.append({
                "date": idx.strftime("%Y-%m-%d"),
                "open": float(o),
                "high": float(hi),
                "low": float(lo),
                "close": float(c),
                "volume": int(v),
            })
        entry = {"data": rows, "asOf": _now_iso()}
        cache_set(f"{t}_{period}_{interval}", "ohlcv", entry)
        result[t] = {**entry, "source": "yfinance"}

    return result


def get_quote(tickers: list[str]) -> dict[str, dict]:
    """Fetch the latest price quote for one or more tickers.

    Attempts to retrieve each quote from cache first (15-minute TTL, see
    cache.CACHE_TTL_SECONDS["quote"]). For any ticker not in cache, fetches
    the current price from yfinance's fast_info, caches the result, and
    returns it tagged with the source.

    Note: this is yfinance-only. Per documented pitfall #7, TV CDP's `quote`
    command reads only the active chart symbol regardless of the ticker
    requested, so it cannot be used for batch quoting without silently
    returning wrong-ticker data. A TV-CDP single-ticker quote path is
    intentionally out of scope here.

    Args:
        tickers: List of ticker symbols (e.g., ["AAPL", "MSFT"]).

    Returns:
        Dict mapping ticker to result dict. Each result has:
            - "price": Latest price as a float.
            - "source": "yfinance" or "cache".
            - "asOf": ISO 8601 timestamp of fetch/cache.
    """
    result = {}
    for t in tickers:
        cached = cache_get(t, "quote")
        if cached is not None:
            result[t] = {**cached, "source": "cache"}
            continue
        # A single bad/delisted ticker (missing "lastPrice", or any other
        # response-shape drift from yfinance) must not raise out of this
        # loop and kill the whole batch — skip just this ticker and keep
        # processing the rest, mirroring the per-row skip in get_prices().
        try:
            info = yf.Ticker(t).fast_info
            price = info.get("lastPrice") if hasattr(info, "get") else info["lastPrice"]
            price = float(price)
        except (TypeError, ValueError, KeyError, AttributeError):
            continue
        entry = {"price": price, "asOf": _now_iso()}
        cache_set(t, "quote", entry)
        result[t] = {**entry, "source": "yfinance"}
    return result


def _extract_avg_estimate(df, row_label: str):
    """Safely pull a float 'avg' value for one row out of an estimates table.

    Guards against every way an analyst-estimates DataFrame can be missing or
    malformed: the whole object being None, not a DataFrame, empty, lacking
    the requested row or the 'avg' column, or containing a NaN in that cell.
    None of these are errors worth raising for — they all mean "no estimate
    available for this field" and must degrade to None, never 0.0.

    Args:
        df: The (possibly None/empty/malformed) estimates DataFrame.
        row_label: Row index label to read (e.g. "0y", "+1y").

    Returns:
        The estimate as a float, or None if unavailable in any way.
    """
    if not isinstance(df, pd.DataFrame) or df.empty:
        return None
    if row_label not in df.index or "avg" not in df.columns:
        return None
    try:
        value = df.loc[row_label, "avg"]
    except (KeyError, TypeError):
        return None
    if pd.isna(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def get_estimates(ticker: str) -> dict:
    """Fetch analyst forward revenue estimates for the current and next fiscal year.

    Attempts to retrieve the estimate from cache first (24h TTL, see
    cache.CACHE_TTL_SECONDS["fundamentals"]). On a cache miss, fetches
    yfinance's revenue_estimate table, extracts the "0y" (current fiscal
    year) and "+1y" (next fiscal year) analyst-consensus averages, caches
    the result, and returns it tagged with the source.

    Never raises on missing or malformed upstream data: a ticker with no
    analyst coverage, a revenue_estimate access that itself throws, an
    empty/None table, a missing row, or a NaN 'avg' cell all degrade to a
    None value for the affected field rather than crashing the caller or
    silently returning a zeroed estimate.

    Args:
        ticker: Ticker symbol (e.g., "PLTR").

    Returns:
        Dict with:
            - "y1RevEstimate": float|None current fiscal year revenue estimate.
            - "y2RevEstimate": float|None next fiscal year revenue estimate.
            - "source": "yfinance" or "cache".
            - "asOf": ISO 8601 timestamp of fetch/cache.
    """
    cached = cache_get(ticker, "fundamentals")
    if cached is not None and "y1RevEstimate" in cached:
        return {**cached, "source": "cache"}

    # yfinance's revenue_estimate property can itself raise (network errors,
    # upstream parsing failures, etc.) for a single ticker — that must not
    # propagate and kill the caller, mirroring the per-ticker guard in
    # get_quote().
    try:
        df = yf.Ticker(ticker).revenue_estimate
    except Exception:  # noqa: BLE001 - yfinance's failure modes here are unbounded
        # (network errors, upstream JSON/schema drift, etc.); any of them means
        # "no estimate available", never a reason to crash the caller.
        df = None

    y1 = _extract_avg_estimate(df, "0y")
    y2 = _extract_avg_estimate(df, "+1y")

    entry = {"y1RevEstimate": y1, "y2RevEstimate": y2, "asOf": _now_iso()}
    cache_set(ticker, "fundamentals", entry)
    return {**entry, "source": "yfinance"}


# yfinance's .info dict field for each metric that has a clean 1:1 raw
# equivalent. operatingIncome is deliberately excluded — yfinance has no raw
# field for it, only a derived ratio (operatingMargins * totalRevenue), and
# mixing computed-vs-raw provenance in one merge function is an explicit
# scope boundary for this task, not an oversight (see task brief / ADR).
_YF_FUNDAMENTALS_FIELDS = {
    "revenue": "totalRevenue",
    "netIncome": "netIncomeToCommon",
}

# yfinance's `.financials` (annual income statement) row label for each
# metric that has a clean 1:1 annual equivalent — used ONLY for the
# EDGAR-vs-yfinance disagreement cross-check. EDGAR's revenue/netIncome are
# always annual (from the latest 10-K); `.info`'s totalRevenue/
# netIncomeToCommon are trailing-twelve-months (TTM). Comparing an annual
# EDGAR figure against a TTM yfinance figure via check_disagreement() would
# produce false-positive "conflicts" for any growing/shrinking company as a
# matter of routine, not a real data-quality signal — so the disagreement
# check must use yfinance's own annual figures instead.
_YF_FINANCIALS_ANNUAL_ROWS = {
    "revenue": "Total Revenue",
    "netIncome": "Net Income",
}


def _safe_float(value):
    """Coerce a raw upstream value to float, treating anything unusable as absent.

    Guards every way a value from EDGAR or yfinance can fail to be a clean
    number: None, a non-numeric type, or NaN. None of these are errors worth
    raising for — they all mean "no usable value", never 0.0.

    Args:
        value: Raw value from an upstream provider (may be None, NaN, str, etc.).

    Returns:
        The value as a float, or None if it is missing/malformed.
    """
    if value is None:
        return None
    try:
        as_float = float(value)
    except (TypeError, ValueError):
        return None
    if pd.isna(as_float):
        return None
    return as_float


def _safe_edgar_facts(cik):
    """Fetch EDGAR company facts, tolerating any failure as "no EDGAR data".

    get_company_facts() already returns {} for a clean 404 (invalid CIK) or
    a metric missing/malformed within an otherwise-valid response. But the
    underlying HTTP/JSON call can also raise for reasons unrelated to a
    clean 404 (network timeout, DNS failure, non-JSON response body, etc.).
    None of those are reasons to crash get_fundamentals() — EDGAR being
    unavailable for any reason just means every metric falls through to
    yfinance instead.

    Args:
        cik: SEC Central Index Key string, or None/falsy to skip EDGAR
            entirely (non-US tickers have no CIK).

    Returns:
        Dict from get_company_facts(), or {} if cik is falsy or the call
        fails for any reason.
    """
    if not cik:
        return {}
    try:
        return get_company_facts(cik) or {}
    except Exception:  # noqa: BLE001 - network/parsing failures here are unbounded
        return {}


def _safe_yf_info(ticker):
    """Fetch yfinance's `.info` dict, tolerating any failure as "no yfinance data".

    Mirrors the per-ticker guard already used in get_quote()/get_estimates():
    a single ticker's `.info` access raising, returning None, or returning a
    non-dict must never crash the caller.

    Args:
        ticker: Ticker symbol (e.g., "AAPL").

    Returns:
        The `.info` dict, or {} if unavailable for any reason.
    """
    try:
        info = yf.Ticker(ticker).info
    except Exception:  # noqa: BLE001 - yfinance's failure modes here are unbounded
        return {}
    return info if isinstance(info, dict) else {}


def _safe_yf_annual_financials(ticker):
    """Fetch yfinance's annual income-statement figures, for disagreement cross-checks only.

    EDGAR's revenue/netIncome values always come from the latest 10-K
    (annual). `.info`'s totalRevenue/netIncomeToCommon are TTM (trailing
    twelve months) — a reasonable *fallback* value when EDGAR is unavailable,
    but not a fair basis for a disagreement comparison against an annual
    EDGAR figure. `.financials` is yfinance's annual income statement
    DataFrame (index: line items like "Total Revenue"/"Net Income"; columns:
    fiscal year-end dates, most recent column first) — the correct
    like-for-like comparison source for check_disagreement().

    Guards every way this can fail, mirroring the per-ticker guard pattern
    used elsewhere in this module: `.financials` raising, returning
    something that isn't a DataFrame, being empty, or lacking the expected
    row all degrade to "no annual figure available for this metric" —
    the caller then simply skips the disagreement check for that metric
    rather than crashing or fabricating a comparison value.

    Args:
        ticker: Ticker symbol (e.g., "AAPL").

    Returns:
        Dict mapping metric key ("revenue", "netIncome") to the latest
        annual float value, only for metrics that were cleanly extracted.
    """
    try:
        df = yf.Ticker(ticker).financials
    except Exception:  # noqa: BLE001 - yfinance's failure modes here are unbounded
        return {}

    if not isinstance(df, pd.DataFrame) or df.empty:
        return {}

    latest_col = df.columns[0]
    result = {}
    for metric, row_label in _YF_FINANCIALS_ANNUAL_ROWS.items():
        if row_label not in df.index:
            continue
        value = _safe_float(df.loc[row_label, latest_col])
        if value is not None:
            result[metric] = value
    return result


def get_fundamentals(ticker: str, cik: str = None) -> dict:
    """Fetch revenue/netIncome/operatingIncome via an EDGAR-primary, yfinance-supplement waterfall.

    For "revenue" and "netIncome": EDGAR (point-in-time-correct, US filers
    only, via edgar_facts.get_company_facts()) is preferred whenever it has
    a value; yfinance's `.info` dict supplements any metric EDGAR lacks.
    When both sources have a value for the same metric, check_disagreement()
    flags — but never hides or auto-resolves — a divergence beyond the
    default threshold; EDGAR's value is still the one returned. The
    disagreement check compares EDGAR's annual figure against yfinance's own
    ANNUAL figure (`.financials`, not `.info`'s TTM fields) — comparing
    across periods would produce false-positive conflicts for any
    growing/shrinking company as a matter of routine. When `cik` is None
    (non-US ticker, e.g. "ASML", "PSU-U.TO"), EDGAR is skipped entirely and
    every field is sourced from yfinance's `.info` (TTM, a reasonable
    fallback when there's no EDGAR figure to compare it against).

    "operatingIncome" is EDGAR-only in this pass: yfinance's `.info` has no
    clean raw field for it (only a derived margin ratio), and mixing
    computed-vs-raw provenance in one merge function is an explicit,
    deliberate scope boundary — not a gap to silently fill with a yfinance
    fallback.

    A metric absent from both sources is simply omitted from the result —
    never coerced to 0.0. Any failure fetching from EDGAR or yfinance
    (network error, malformed response, missing/NaN fields, unexpected
    response shape) degrades to "no data from that source" for the affected
    metric rather than crashing the caller.

    Args:
        ticker: Ticker symbol (e.g., "AAPL").
        cik: SEC Central Index Key, or None to skip EDGAR (non-US tickers).

    Returns:
        Dict with per-metric entries for any of "revenue", "netIncome", and
        "operatingIncome" that have data from at least one source, each
        shaped {"value": float, "source": "edgar"|"yfinance", "asOf": str},
        plus "dataQuality": {"staleness": bool, "dataConflicts": list, "flags": list}.
    """
    cached = cache_get(ticker, "fundamentals")
    if cached is not None and "revenue" in cached:
        return {
            **cached,
            "dataQuality": cached.get(
                "dataQuality", {"staleness": False, "dataConflicts": [], "flags": []}
            ),
        }

    edgar = _safe_edgar_facts(cik)
    yf_info = _safe_yf_info(ticker)
    # Annual figures, fetched only for the disagreement cross-check below —
    # never used as the yfinance-only fallback value (that's still `.info`,
    # a TTM approximation, which is fine as a fallback but not as a fair
    # comparison against EDGAR's annual figure).
    yf_annual = _safe_yf_annual_financials(ticker) if edgar else {}

    result = {}
    conflicts = []

    for metric, yf_key in _YF_FUNDAMENTALS_FIELDS.items():
        edgar_field = edgar.get(metric)
        edgar_value = _safe_float(edgar_field.get("value")) if edgar_field else None
        yf_value = _safe_float(yf_info.get(yf_key))

        if edgar_value is not None:
            result[metric] = {
                "value": edgar_value,
                "source": "edgar",
                "asOf": edgar_field.get("asOf"),
            }
            annual_value = yf_annual.get(metric)
            if annual_value is not None:
                conflict = check_disagreement(edgar_value, annual_value, metric)
                if conflict:
                    conflicts.append(conflict)
            # else: no clean annual yfinance figure available — skip the
            # disagreement check for this metric rather than fabricating
            # a comparison against a TTM value, or crashing.
        elif yf_value is not None:
            result[metric] = {"value": yf_value, "source": "yfinance", "asOf": _now_iso()}
        # else: absent from both sources — omitted entirely, never zeroed.

    # operatingIncome: EDGAR-only for this pass (see docstring for rationale).
    operating_field = edgar.get("operatingIncome")
    operating_value = _safe_float(operating_field.get("value")) if operating_field else None
    if operating_value is not None:
        result["operatingIncome"] = {
            "value": operating_value,
            "source": "edgar",
            "asOf": operating_field.get("asOf"),
        }

    # Staleness is judged on revenue's asOf date — revenue is always present
    # when any data was found at all, and is the metric every downstream
    # valuation script (DCF, framework_score) anchors on.
    is_stale = False
    revenue_as_of = result.get("revenue", {}).get("asOf")
    if revenue_as_of:
        try:
            is_stale = check_staleness(revenue_as_of[:10])
        except ValueError:
            # Malformed/unexpected asOf format must never crash the whole
            # call — treat as "cannot determine staleness", not stale.
            is_stale = False

    result["dataQuality"] = {"staleness": is_stale, "dataConflicts": conflicts, "flags": []}
    cache_set(ticker, "fundamentals", result)
    return result
