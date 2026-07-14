"""
Data Window Validator — Data Window Reader (Task 5D-1)

Extracts live OHLCV from TradingView's Data Window panel by composing
tv_client.py's tv_call() (Task 5A-8's resilient, never-raises wrapper)
with the real `chart symbol`, `chart timeframe`, `chart openDataWindow`,
and `chart read` TV CDP CLI commands.

The real `chart read` response (tradingview-cdp/core/chart.js:153-192's
readDataWindow(), confirmed live 2026-07-14 via a read-only inspection
against the user's connected TradingView Desktop — no chart symbol/
timeframe was changed for that check) is a FLAT, DOM-scraped,
string-keyed dict — NOT a structured {open, high, low, close, volume}
JSON object:
    {"success": true, "data": {
        "Date": "Tue 14 Jul '26", "Open": "217.04", "High": "222.75",
        "Low": "215.28", "Close": "216.10", "Vol": "1.64 M",
        "Volume": "1.64 M", "Volume MA": "16.97 M", "EMA Fast": "229.47",
        "RSI": "45.79", ...
    }}
Every value is raw DOM text. The exact key set varies with which
indicators are loaded on the active chart, so extract_data_window()
checks multiple plausible key-name variants defensively (_first_present)
rather than hardcoding one assumed vocabulary.

There is no TV-native field representing "how fresh is this read" — the
"Date" field is the displayed candle's date, not a read-time timestamp.
"Lag" is therefore detected as structurally incomplete data (missing
O/H/L/C after a fresh symbol/timeframe switch) rather than a
timestamp-age comparison, and extract_data_window() retries with
exponential backoff on that condition.

Key Input Dependencies:
    - plugins/tradingview/scripts/tv_client.py (Task 5A-8's tv_call())
"""

import math
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

# Cross-directory import of tv_call (Task 5A-8). Follows the exact same
# sys.path-insert pattern pine_script_manager.py/alert_manager.py already
# established — plugins/tradingview/scripts/ is not a package on the
# default path. tv_client.py is not touched; this module only wraps its
# output.
_TV_SCRIPTS_DIR = str(Path(__file__).resolve().parents[3] / "plugins" / "tradingview" / "scripts")
if _TV_SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _TV_SCRIPTS_DIR)

from tv_client import tv_call  # noqa: E402

# tv_cdp_health.py lives in the SAME directory as this module
# (investment_screener/backend/py_services/), unlike tv_call() above — a
# plain top-level import works with no sys.path manipulation. Top-level
# (not lazy/function-local) is used here per this task's brief: there's
# no heavy/side-effecting import-time behavior in tv_cdp_health.py to
# defer, and a top-level import is simpler.
from tv_cdp_health import cache_get, cache_set  # noqa: E402

# Key-variant lists, ordered most-to-least likely, based on the real
# confirmed live sample (2026-07-14) — see this module's docstring and
# this task's brief for why a single hardcoded vocabulary is unsafe.
_OPEN_KEYS = ["Open", "O"]
_HIGH_KEYS = ["High", "H"]
_LOW_KEYS = ["Low", "L"]
_CLOSE_KEYS = ["Close", "C"]
_VOLUME_KEYS = ["Vol", "Volume", "V"]

_MAX_ATTEMPTS = 5
_INITIAL_BACKOFF_SECONDS = 1


def _tv_call_succeeded(result: dict) -> bool:
    """Decide whether a tv_call() response signals success.

    Duplicated (not imported) from pine_script_manager.py's/
    alert_manager.py's own _tv_call_succeeded() — module-private,
    underscore-prefixed helpers shouldn't be imported cross-module, so
    this small, stable logic is copied here exactly as it was already
    copied twice before.

    Args:
        result: The raw dict returned by tv_call().

    Returns:
        False if either of tv_call()'s two distinct failure shapes is
        present (the Task 5A-8 error-dict contract with no "success"
        key, or the CLI's own {"success": False, ...} shape); True
        otherwise.
    """
    if not isinstance(result, dict):
        return False
    if "error" in result and "success" not in result:
        return False
    if result.get("success") is False:
        return False
    return True


def _first_present(data: dict, keys: List[str]) -> Optional[str]:
    """Return the first non-missing value among `keys` in `data`, or
    None if none are present — defends against the real Data Window's
    key vocabulary varying by which indicators are loaded on the chart
    (confirmed live, 2026-07-14 — see this task's brief)."""
    for key in keys:
        if key in data:
            return data[key]
    return None


def _parse_price(raw: Optional[str]) -> Optional[float]:
    """Parse a Data Window price string (e.g. "217.04") to float.
    Never raises: unparseable input returns None."""
    if raw is None:
        return None
    try:
        return float(raw.replace(",", "").strip())
    except (ValueError, AttributeError):
        return None


def _parse_volume(raw: Optional[str]) -> Optional[int]:
    """Parse a Data Window volume string with a K/M/B suffix (e.g.
    "1.64 M" -> 1_640_000, "500 K" -> 500_000) to int. Never raises:
    unparseable input returns None."""
    if raw is None:
        return None
    match = re.match(r"^\s*([\d,.]+)\s*([KMB]?)\s*$", raw.strip(), re.IGNORECASE)
    if not match:
        return None
    number_str, suffix = match.groups()
    try:
        number = float(number_str.replace(",", ""))
    except ValueError:
        return None
    multiplier = {"": 1, "K": 1_000, "M": 1_000_000, "B": 1_000_000_000}.get(suffix.upper(), 1)
    return int(number * multiplier)


def _parse_ohlcv(data: dict) -> dict:
    """Parse OHLCV fields out of one raw `chart read` data dict.

    Args:
        data: The `data` sub-dict of a successful `chart read` response
            (flat, string-keyed, DOM-scraped — see this module's
            docstring).

    Returns:
        {"open", "high", "low", "close", "volume"} — each float/int or
        None if unparseable/missing. Never raises.
    """
    return {
        "open": _parse_price(_first_present(data, _OPEN_KEYS)),
        "high": _parse_price(_first_present(data, _HIGH_KEYS)),
        "low": _parse_price(_first_present(data, _LOW_KEYS)),
        "close": _parse_price(_first_present(data, _CLOSE_KEYS)),
        "volume": _parse_volume(_first_present(data, _VOLUME_KEYS)),
    }


def _is_complete(parsed: dict) -> bool:
    """True if all four price fields (O/H/L/C) parsed successfully.

    Volume is a soft requirement (see this task's brief's Key Design
    Decisions) — a result missing only volume still counts as complete.
    """
    return (
        parsed["open"] is not None
        and parsed["high"] is not None
        and parsed["low"] is not None
        and parsed["close"] is not None
    )


def _attempt_extract(ticker: str, timeframe: str) -> Optional[dict]:
    """Run one single switch+read+parse attempt.

    Args:
        ticker: Ticker symbol to switch the active chart to.
        timeframe: Real TV resolution string, passed through unmodified.

    Returns:
        A parsed {"open", "high", "low", "close", "volume", "timestamp"}
        dict if the chart switch/timeframe/read calls all succeeded
        (regardless of whether the parse came back complete — see
        _is_complete for the completeness check), or None if any
        underlying tv_call() failed outright.
    """
    switch_result = tv_call("chart", "symbol", ticker)
    if not _tv_call_succeeded(switch_result):
        return None

    timeframe_result = tv_call("chart", "timeframe", timeframe)
    if not _tv_call_succeeded(timeframe_result):
        return None

    # Idempotent; result not gated on (opening an already-open panel is
    # a harmless no-op per tradingview-cdp/core/chart.js:210's own
    # wasAlreadyOpen tracking).
    tv_call("chart", "openDataWindow")

    read_result = tv_call("chart", "read")
    if not _tv_call_succeeded(read_result):
        return None

    data = read_result.get("data", {})
    if not isinstance(data, dict):
        return None

    parsed = _parse_ohlcv(data)
    parsed["timestamp"] = datetime.now(timezone.utc).isoformat()
    return parsed


def extract_data_window(ticker: str, timeframe: str = "1D") -> Optional[dict]:
    """
    Extract OHLCV from TradingView's live Data Window panel.

    Switches the active chart to `ticker`/`timeframe`, opens the Data
    Window if needed, and reads it. Since TV provides no native
    per-read freshness/staleness signal (confirmed live — see this
    task's brief), "lag" is detected as structurally incomplete data
    (missing Open/High/Low/Close after a fresh switch — TV's Data
    Window can take a moment to catch up right after a symbol/timeframe
    change) rather than a timestamp-age comparison.

    Retries up to 5 times with exponential backoff (1s, 2s, 4s, 8s,
    16s) whenever the switch/timeframe calls fail OR the read succeeds
    but O/H/L/C can't all be parsed. Returns the last successfully
    parsed result (last-known-good) if a later attempt fails after an
    earlier one succeeded.

    Never raises.

    Args:
        ticker: Ticker symbol (e.g. "NVDA").
        timeframe: Real TV resolution string — "1D"/"D"/"W" or a plain
            minute count ("60" = 1H, "240" = 4H, "15" = 15m). NOT the
            "4H"/"15m" suffix format an earlier draft of this task
            assumed — see this brief's correction notes.

    Returns:
        {"open": float, "high": float, "low": float, "close": float,
        "volume": int | None, "timestamp": str}. `timestamp` is THIS
        function's own read-time stamp (ISO 8601, UTC) — not a
        TV-native field, since none exists (see brief).

        `None` is returned ONLY when every one of the 5 attempts'
        underlying tv_call() calls failed outright at the CDP layer
        (chart symbol switch, timeframe change, or the read itself) —
        i.e. `_attempt_extract()` returned None on every attempt. This
        is the "TV/CDP unreachable" case.

        If `_attempt_extract()` succeeds at least once but the parsed
        result is never structurally complete (e.g. `chart read`
        succeeds every time but "Close" is missing from the Data
        Window on every attempt — see `_is_complete()`), this function
        does NOT collapse that to None. It returns the LAST such
        partial dict as-is, with the missing field(s) set to None
        inside it (e.g. `{"open": 217.04, "high": 222.75, "low":
        215.28, "close": None, "volume": ..., "timestamp": ...}`).
        This is deliberate: a partial read is strictly more useful to
        a caller than discarding the data outright, since the caller
        can see exactly which fields came back. Callers MUST check the
        individual O/H/L/C sub-fields for None — a non-None return
        value alone does not guarantee a complete price read.
    """
    last_known_good = None
    delay = _INITIAL_BACKOFF_SECONDS
    for attempt in range(_MAX_ATTEMPTS):
        result = _attempt_extract(ticker, timeframe)
        if result is not None:
            last_known_good = result
            if _is_complete(result):
                return last_known_good
        if attempt < _MAX_ATTEMPTS - 1:
            time.sleep(delay)
            delay *= 2
    return last_known_good


# --- Task 5D-2: OHLCV Validation ---
#
# validate_ohlcv() is a pure, offline validation function operating on
# a candle dict matching extract_data_window()'s (5D-1) real output
# shape. It does NOT call extract_data_window() or any tv_call()-based
# function.

_PRICE_FIELDS = ["open", "high", "low", "close"]
_MAX_SPREAD_PERCENT = 2.0


def _is_finite_number(value: Any) -> bool:
    """True only for a real, finite int/float — excludes bool (Python's
    bool is a subclass of int), None, NaN, and +/-inf."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return not (math.isnan(value) or math.isinf(value))


def _validate_price_fields(candle: dict) -> List[str]:
    """Check each of open/high/low/close via `_is_finite_number()`.

    Args:
        candle: The candle dict being validated.

    Returns:
        One specific error message per invalid/missing price field
        (empty list if all four are finite numbers).
    """
    errors = []
    for field in _PRICE_FIELDS:
        if not _is_finite_number(candle.get(field)):
            errors.append(f"{field} is missing or not a finite number")
    return errors


def _validate_relations_and_spread(candle: dict) -> List[str]:
    """Run the three relational checks plus the spread check.

    Only called once all four price fields are confirmed finite numbers
    (see validate_ohlcv) — a relational comparison against None/NaN
    would raise TypeError, so this is never called until that's ruled
    out.

    Checks exactly `open <= high`, `high >= low`, `low <= close` — see
    validate_ohlcv's docstring and this task's brief for why this
    three-relation set is deliberately not expanded with `low <= open`/
    `close <= high`. Spread is intraday range as a percentage of low
    (`(high - low) / low * 100`), flagged at >= 2% — a best-effort
    interpretation of an ambiguous plan requirement, see this task's
    brief.

    `_is_finite_number()` (the caller's precondition) accepts 0.0 and
    negative numbers as finite — it only rejects None/bool/non-numeric/
    NaN/inf. A `low` of zero or below therefore reaches this function
    and, left unguarded, `(high - low) / low * 100` would raise
    ZeroDivisionError (low == 0) or silently produce a meaningless
    negative "spread" (low < 0), violating this module's never-raises
    contract. The spread division is therefore only attempted when
    `low > 0`; a non-positive low is itself flagged as an error instead
    (skipping the spread check for that candle) rather than silently
    ignored — see this task's fix-round report.

    Args:
        candle: The candle dict being validated (all four price fields
            already confirmed finite numbers by the caller).

    Returns:
        One specific error message per failed check (empty list if all
        pass).
    """
    errors = []
    open_, high, low, close = candle["open"], candle["high"], candle["low"], candle["close"]

    if not (open_ <= high):
        errors.append(f"open ({open_}) must be <= high ({high})")
    if not (high >= low):
        errors.append(f"high ({high}) must be >= low ({low})")
    if not (low <= close):
        errors.append(f"low ({low}) must be <= close ({close})")

    if low > 0:
        spread_percent = (high - low) / low * 100
        if spread_percent >= _MAX_SPREAD_PERCENT:
            errors.append(
                f"spread {spread_percent:.2f}% exceeds {_MAX_SPREAD_PERCENT}% threshold "
                "(intraday range as % of low)"
            )
    else:
        errors.append(f"low ({low}) must be positive to compute spread")

    return errors


def _validate_volume(candle: dict) -> List[str]:
    """Volume is a soft/optional check (matches 5D-1's own soft-
    requirement precedent for volume) — only run if volume is present.

    Args:
        candle: The candle dict being validated.

    Returns:
        A single error message if volume is present but non-positive or
        not a finite number; empty list if volume is None/missing or
        valid.
    """
    volume = candle.get("volume")
    if volume is None:
        return []
    if not _is_finite_number(volume) or volume <= 0:
        return [f"volume ({volume}) must be a positive finite number"]
    return []


def validate_ohlcv(candle: Any) -> Dict[str, Any]:
    """
    Validate a candle dict (matching extract_data_window()'s real
    output shape, Task 5D-1) for structural sanity.

    Checks:
    - Every price field (open/high/low/close) is present, a finite
      real number (not None, not NaN/inf, not a bool) — a candle with
      any missing/malformed price field is immediately invalid, since
      the relational checks below assume real numbers to compare.
    - open <= high, high >= low, low <= close — exactly these three
      relations, per the plan/spec's own literal (and admittedly
      incomplete — see this task's brief) requirement. Does NOT check
      low <= open or close <= high.
    - volume > 0, IF volume is present (volume is a soft/optional field
      per 5D-1's own contract — a None volume does not itself
      invalidate the candle; a present, non-positive volume does).
    - Intraday spread (high - low) / low * 100 is below 2% — a
      best-effort interpretation of an ambiguous plan requirement (see
      this task's brief); division is only attempted when `low > 0` —
      the price-field check only guarantees low is a finite number, NOT
      that it's positive, so a zero/negative low is flagged as its own
      error (see this task's fix-round report) instead of being passed
      into the division.

    Never raises: any malformed/missing input degrades to a structured
    invalid result (`{"valid": False, "errors": [...]}`), never an
    exception — including a non-dict `candle` argument.

    Args:
        candle: A candle dict, expected to match extract_data_window()'s
            shape (open/high/low/close/volume/timestamp keys), though
            any input is accepted defensively.

    Returns:
        {"valid": bool, "errors": list[str]} — valid is True only if
        errors is empty. All applicable checks run and accumulate into
        errors (not just the first failure) — a candle can fail
        multiple checks simultaneously and all are reported.
    """
    if not isinstance(candle, dict):
        return {"valid": False, "errors": ["candle is not a dict"]}

    errors: List[str] = []
    price_errors = _validate_price_fields(candle)
    errors.extend(price_errors)

    # Relational/spread checks are meaningless (and comparison-unsafe)
    # once any price field is None/NaN/inf — skip them entirely here.
    if not price_errors:
        errors.extend(_validate_relations_and_spread(candle))

    errors.extend(_validate_volume(candle))

    return {"valid": not errors, "errors": errors}


# --- Task 5D-3: Indicator Extraction ---
#
# extract_indicators() is an independent, parallel extraction path
# reading the same live Data Window (5D-1's confirmed real response
# shape) for a representative, non-exhaustive set of indicator fields
# instead of OHLCV. Unlike extract_data_window(), it takes no ticker
# parameter and never switches the chart's symbol — only its timeframe
# — matching the plan's literal extract_indicators(timeframe) signature.
# No retry/backoff here (unlike extract_data_window()): single-attempt
# only, per this task's explicit scope boundary — Task 5D-6 owns retry
# generalization, not duplicated here.

# Key-variant lists for the target indicators. RSI/ADX/ATR keys are
# confirmed against the real live sample gathered for Task 5D-1's brief
# (2026-07-14). MACD/BB keys are reasonable best-effort guesses — no
# chart with those indicators loaded was inspected live; if a future
# task finds these names wrong against a real MACD/BB-loaded chart, that
# discovery should update this list, not be treated as evidence this
# task was built wrong (see this task's brief).
_RSI_KEYS = ["RSI"]
_MACD_KEYS = ["MACD"]
_BB_UPPER_KEYS = ["BB Upper", "Bollinger Upper", "BB_upper"]
_BB_LOWER_KEYS = ["BB Lower", "Bollinger Lower", "BB_lower"]
_ADX_KEYS = ["ADX"]
_ATR_KEYS = ["ATR"]


def _validate_range(
    value: Optional[float], low: Optional[float], high: Optional[float]
) -> Optional[float]:
    """Return `value` unchanged if it's a finite number within
    [low, high] (either bound optional — pass None to skip that side),
    else None. A present-but-implausible value degrades to None, same
    treatment as a genuinely missing one (per this task's "graceful
    fail" requirement)."""
    if value is None or not _is_finite_number(value):
        return None
    if low is not None and value < low:
        return None
    if high is not None and value > high:
        return None
    return value


def extract_indicators(timeframe: str) -> Dict[str, Optional[float]]:
    """
    Extract a representative set of technical indicators from
    TradingView's live Data Window panel, on whichever chart symbol is
    currently active.

    Unlike extract_data_window() (5D-1), this function does NOT switch
    the chart's symbol — only its timeframe. Call
    extract_data_window(ticker, timeframe) first if a specific ticker's
    chart needs to be active before calling this.

    Targets a representative, non-exhaustive indicator set (rsi, macd,
    bb_upper, bb_lower, adx, atr) — a chart's real indicator set is
    unbounded; this does not attempt dynamic discovery of arbitrary
    other indicators. Each value is range-validated (rsi/adx in
    [0, 100], atr/bb_upper/bb_lower >= 0, macd merely finite, bb_upper
    >= bb_lower when both present) — a present-but-implausible value is
    treated identically to a genuinely missing one: None.

    Does NOT retry with backoff (unlike extract_data_window()) — a
    single-attempt read; retry/lag-tolerance generalization is Task
    5D-6's concern, not duplicated here (see Key Design Decisions).

    Never raises.

    Args:
        timeframe: Real TV resolution string, passed through unmodified
            (see Task 5D-1's brief for the real vocabulary — "1D"/"D"/
            "W" or a plain minute count).

    Returns:
        {"rsi": float | None, "macd": float | None, "bb_upper": float | None,
        "bb_lower": float | None, "adx": float | None, "atr": float | None}
        — every key always present; value is None for any indicator
        that's missing from the chart, unparseable, or fails its range
        check.
    """
    empty = {"rsi": None, "macd": None, "bb_upper": None, "bb_lower": None, "adx": None, "atr": None}

    timeframe_result = tv_call("chart", "timeframe", timeframe)
    if not _tv_call_succeeded(timeframe_result):
        return dict(empty)

    tv_call("chart", "openDataWindow")  # idempotent, same precedent as 5D-1

    read_result = tv_call("chart", "read")
    if not _tv_call_succeeded(read_result):
        return dict(empty)

    data = read_result.get("data", {})
    if not isinstance(data, dict):
        return dict(empty)

    rsi = _validate_range(_parse_price(_first_present(data, _RSI_KEYS)), 0, 100)
    macd = _parse_price(_first_present(data, _MACD_KEYS))
    macd = macd if _is_finite_number(macd) else None
    bb_upper = _validate_range(_parse_price(_first_present(data, _BB_UPPER_KEYS)), 0, None)
    bb_lower = _validate_range(_parse_price(_first_present(data, _BB_LOWER_KEYS)), 0, None)
    if bb_upper is not None and bb_lower is not None and bb_upper < bb_lower:
        bb_upper, bb_lower = None, None
    adx = _validate_range(_parse_price(_first_present(data, _ADX_KEYS)), 0, 100)
    atr = _validate_range(_parse_price(_first_present(data, _ATR_KEYS)), 0, None)

    return {"rsi": rsi, "macd": macd, "bb_upper": bb_upper, "bb_lower": bb_lower, "adx": adx, "atr": atr}


# --- Task 5D-4: Local Caching ---
#
# cache_data_window() deliberately reuses tv_cdp_health.py's already-built,
# already-tested generic file-based TTL cache (cache_get()/cache_set(),
# Task 5A-7) rather than reimplementing atomic-write/lazy-expiration logic
# in a second, separate data_window_cache.jsonl file. See this task's
# brief for the full reasoning — entries share the SAME physical cache
# file (tv_cdp_responses_cache.jsonl) as other tv_call() response caching,
# namespaced under "data_window:" to guarantee no key collision.

_CACHE_KEY_PREFIX = "data_window:"


def cache_data_window(key: str, data: dict, ttl: int = 300) -> bool:
    """
    Cache a Data Window extraction result (an OHLCV candle from
    extract_data_window(), an indicator dict from extract_indicators(),
    or any other JSON-serializable payload) with TTL-based expiration.

    Reuses tv_cdp_health.py's already-built, already-tested generic
    file-based TTL cache (cache_set()/cache_get(), Task 5A-7) rather
    than reimplementing atomic-write/lazy-expiration logic — see this
    task's brief for why entries deliberately share the SAME physical
    cache file (tv_cdp_responses_cache.jsonl) as other tv_call()
    response caching, rather than a separate data_window_cache.jsonl
    file the plan's terse checklist names but which would require
    duplicating already-reviewed logic to honor literally.

    A "data_window:" prefix is applied to the caller's key before
    storage, guaranteeing this task's cache entries can never collide
    with any tv_call()-command's own cache key (those are always raw
    hex digests from generate_cache_key(), never starting with
    "data_window:").

    Honest success/failure reporting: cache_set() itself deliberately
    never raises and never reports success/failure (its own docstring:
    "Best-effort... write failures are logged, never raised") — the
    information is structurally unavailable to a caller just by
    invoking it. To honor this function's `-> bool` contract honestly
    (not just always returning True), this wrapper immediately verifies
    the write by reading the entry back via cache_get() and checking it
    round-tripped successfully — a legitimate, cheap (local file read)
    verification technique, not a workaround masking a design flaw.

    Never raises (cache_set()/cache_get() already never raise; this
    wrapper adds no new exception surface).

    Args:
        key: Caller-supplied cache key (e.g. "NVDA:1D" for a ticker+
            timeframe combination). Used directly (with the namespacing
            prefix above) — NOT hashed via generate_cache_key(), since
            Data Window callers already have a natural, short,
            meaningful key available and don't need
            generate_cache_key()'s (function_name, args)-based scheme.
        data: The payload to cache; must be JSON-serializable.
        ttl: Seconds until this entry expires (default 300 = 5 min,
            matches 5A-7's own default and the plan's ask).

    Returns:
        True if the entry was verified present (and not already
        expired) immediately after writing; False if the verification
        read didn't find it (a genuine write failure, or — extremely
        unlikely but theoretically possible with ttl=0 — the entry
        expiring in the instant between write and verify).
    """
    namespaced_key = f"{_CACHE_KEY_PREFIX}{key}"
    cache_set(namespaced_key, data, ttl_seconds=ttl)
    return cache_get(namespaced_key) is not None


# --- Task 5D-5: Cache Hit Logic ---
#
# get_cached_or_fetch() is a generic cache-aside function layered on top of
# 5D-4's cache_data_window() and 5A-7's cache_get() — both already
# imported at module level above (line 62). Deliberately synchronous, no
# asyncio anywhere: see this task's brief for why the plan's "async if
# possible" aspiration doesn't fit this codebase (every Python service
# here, including tv_call() itself, is synchronous — there's no
# precedent and no ready async caller).


def get_cached_or_fetch(
    key: str, fetch_fn: Callable[[], Optional[dict]], ttl: int = 300
) -> Optional[dict]:
    """
    Cache-aside lookup: return the cached value for `key` if a fresh entry
    exists, else call `fetch_fn()`, cache its result (via this module's
    own cache_data_window(), Task 5D-4, reusing the same "data_window:"
    namespacing so entries are visible to both functions interchangeably),
    and return it.

    Args:
        key: Cache key — the same bare string a caller would pass to
            cache_data_window() (e.g. "NVDA:1D"). Namespacing is applied
            internally by this function's own cache_get() call, matching
            5D-4's established "data_window:" prefix convention — the
            caller never sees or supplies the prefix.
        fetch_fn: A zero-argument callable that fetches fresh data on a
            cache miss (e.g. a lambda wrapping
            extract_data_window(ticker, timeframe) or
            extract_indicators(timeframe)). Called synchronously, at most
            once per call to get_cached_or_fetch(), and ONLY on a genuine
            cache miss — never on a hit.
        ttl: Seconds the freshly-fetched result should be cached for on a
            miss (irrelevant on a hit — an existing entry's TTL was
            already set when it was originally cached).

    Returns:
        The cached dict on a hit, or fetch_fn()'s return value on a miss
        (which may itself be None — see below).

    A miss where fetch_fn() returns None is NOT cached (caching a
    failure/empty result would poison the cache for the full TTL window,
    hiding a subsequent successful fetch attempt) — the None is still
    returned as-is to the caller, matching extract_data_window()'s own
    real "give up after retries" contract (Task 5D-1).

    Does NOT catch exceptions from fetch_fn() — a raising fetch_fn is the
    caller's own responsibility to handle; only this function's own
    cache-lookup/cache-write logic (via cache_get()/cache_data_window(),
    both already never-raising per 5A-7/5D-4) is guaranteed not to raise
    on its own.
    """
    namespaced_key = f"{_CACHE_KEY_PREFIX}{key}"
    cached = cache_get(namespaced_key)
    if cached is not None:
        return cached

    fresh = fetch_fn()
    if fresh is not None:
        cache_data_window(key, fresh, ttl=ttl)
    return fresh
