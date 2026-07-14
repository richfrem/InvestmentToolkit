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

import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

# Cross-directory import of tv_call (Task 5A-8). Follows the exact same
# sys.path-insert pattern pine_script_manager.py/alert_manager.py already
# established — plugins/tradingview/scripts/ is not a package on the
# default path. tv_client.py is not touched; this module only wraps its
# output.
_TV_SCRIPTS_DIR = str(Path(__file__).resolve().parents[3] / "plugins" / "tradingview" / "scripts")
if _TV_SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _TV_SCRIPTS_DIR)

from tv_client import tv_call  # noqa: E402

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
