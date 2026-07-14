"""
Alert Manager — Alert Creation (Task 5C-1)

Creates TradingView price alerts by composing tv_client.py's tv_call()
(Task 5A-8's resilient, never-raises wrapper) with the real `alert create`
and `alert list` TV CDP CLI commands.

The real `alert create` command (tradingview-cdp/core/alerts.js:6-73) is
pure DOM/UI automation — it clicks buttons and fills form inputs, and its
response contains no alert ID at all
({success, price, condition, message, price_set, source}). There is also
no `ticker` parameter on alert creation; like every other single-chart TV
CDP command (CLAUDE.md pitfall #7), it operates on whatever chart is
currently active. To get a usable, real TV alert_id for a specific
ticker, create_price_alert() therefore:
    1. Switches the active chart to the target ticker.
    2. Creates the alert (no ID in the response).
    3. Lists all current alerts.
    4. Correlates the newly created one by ticker + condition to recover
       its real alert_id.

This module is the foundation for later 5C tasks (dedup, /daily
integration) — they call create_price_alert() rather than composing
tv_call() directly.

Key Input Dependencies:
    - plugins/tradingview/scripts/tv_client.py (Task 5A-8's tv_call())
"""

import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Cross-directory import of tv_call (Task 5A-8). Follows the exact same
# sys.path-insert pattern pine_script_manager.py already established —
# plugins/tradingview/scripts/ is not a package on the default path.
# tv_client.py is not touched; this module only wraps its output.
_TV_SCRIPTS_DIR = str(Path(__file__).resolve().parents[3] / "plugins" / "tradingview" / "scripts")
if _TV_SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _TV_SCRIPTS_DIR)

from tv_client import tv_call  # noqa: E402

logger = logging.getLogger(__name__)

# Maps this module's simple two-direction interface onto the real CLI's
# `--condition` vocabulary (tradingview-cdp/cli.js:49). The real CLI also
# supports a third condition, "crossing" — deliberately not exposed here,
# matching the "simple interface, complex multi-leg alerts deferred"
# design intent; a future task can expose it if a real use case needs it.
_DIRECTION_TO_CONDITION = {
    "above": "greater_than",
    "below": "less_than",
}


def _tv_call_succeeded(result: dict) -> bool:
    """Decide whether a tv_call() response signals success.

    Duplicated (not imported) from pine_script_manager.py's own
    _tv_call_succeeded() (itself already a duplicate of
    tv_pine_inject.py:84-91) — module-private, underscore-prefixed
    helpers shouldn't be imported cross-module, so this small, stable
    logic is copied here exactly as it was already copied once before.

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


def _validate_alert_input(ticker: str, price: float, direction: str) -> str:
    """Validate create_price_alert()'s inputs and resolve the CLI condition.

    Args:
        ticker: Ticker symbol to switch the active chart to.
        price: Alert trigger price level.
        direction: Simple two-value direction ("above"/"below").

    Returns:
        The real CLI `--condition` value ("greater_than"/"less_than")
        corresponding to `direction`.

    Raises:
        ValueError: If `ticker` is not a non-empty string, `price` is not
            a positive number, or `direction` is not "above"/"below".
            These are caller/programmer errors, not transient TV
            failures, so validation happens eagerly before any tv_call().
    """
    if not isinstance(ticker, str) or not ticker.strip():
        raise ValueError(f"ticker must be a non-empty string, got: {ticker!r}")
    if not isinstance(price, (int, float)) or isinstance(price, bool) or price <= 0:
        raise ValueError(f"price must be a positive number, got: {price!r}")
    if direction not in _DIRECTION_TO_CONDITION:
        raise ValueError(
            f"direction must be one of {sorted(_DIRECTION_TO_CONDITION)}, got: {direction!r}"
        )
    return _DIRECTION_TO_CONDITION[direction]


def _find_created_alert_id(
    alerts: List[Dict], ticker: str, condition: str
) -> Optional[str]:
    """Correlate the just-created alert in a freshly listed alerts array.

    TV's `symbol` field may include an exchange prefix (e.g.
    "NASDAQ:NVDA" vs. a bare "NVDA" ticker), so matching uses a
    case-insensitive substring check rather than exact equality.

    Args:
        alerts: The `alerts` array from an `alert list` tv_call()
            response (real shape per tradingview-cdp/core/alerts.js:75-103).
        ticker: The ticker just switched to and alerted on.
        condition: The real CLI condition ("greater_than"/"less_than")
            just used to create the alert.

    Returns:
        The matching alert's `alert_id` if exactly one match is found.
        If multiple match (e.g. a pre-existing alert with the same
        ticker/condition already existed), the one with the latest
        `created` timestamp if present, else the first match. None if
        zero alerts match — a documented, accepted limitation (creation
        may have failed silently in the DOM, or this list call raced
        ahead of TV's own internal state), not solved here.
    """
    matches = [
        a for a in alerts
        if isinstance(a, dict)
        and a.get("condition") == condition
        and ticker.upper() in str(a.get("symbol", "")).upper()
    ]
    if not matches:
        return None
    if len(matches) == 1:
        return matches[0].get("alert_id")

    with_timestamps = [m for m in matches if m.get("created")]
    if with_timestamps:
        return max(with_timestamps, key=lambda m: m["created"]).get("alert_id")
    return matches[0].get("alert_id")


def create_price_alert(
    ticker: str,
    price: float,
    direction: str,
) -> Optional[str]:
    """
    Create a price alert in TradingView for `ticker`, returning its real
    TV alert_id.

    Switches the active TV chart to `ticker` first (TV CDP's alert
    create command has no ticker parameter — it operates on whatever
    chart is currently active, same limitation as every other
    single-chart CDP command). Since the real create response contains
    no alert ID, this then lists current alerts and correlates the
    newly created one by ticker + condition.

    Args:
        ticker: Ticker symbol to create the alert for (e.g. "NVDA").
        price: Alert trigger price level. Must be positive.
        direction: "above" or "below" — mapped to the real CLI's
            `--condition greater_than`/`less_than` respectively.

    Raises:
        ValueError: If `ticker`/`price`/`direction` fail input validation
            (caller error, not a transient TV failure).

    Never raises for TV/network failures — matches tv_call()'s own
    established contract (5A-8 onward). Returns None if the chart
    switch, creation, listing, or ID correlation fails at any step.

    Returns:
        The correlated real TV alert_id, or None on any TV/network
        failure or if no matching alert could be found in the post-
        creation listing.
    """
    condition = _validate_alert_input(ticker, price, direction)

    switch_result = tv_call("chart", "symbol", ticker)
    if not _tv_call_succeeded(switch_result):
        logger.warning(
            "create_price_alert: chart switch to '%s' failed: %s", ticker, switch_result
        )
        return None

    create_result = tv_call("alert", "create", "--price", str(price), "--condition", condition)
    if not _tv_call_succeeded(create_result):
        logger.warning(
            "create_price_alert: alert create failed for '%s' @ %s (%s): %s",
            ticker, price, condition, create_result,
        )
        return None

    list_result = tv_call("alert", "list")
    if not _tv_call_succeeded(list_result):
        logger.warning(
            "create_price_alert: alert list failed after creating '%s' @ %s (%s): %s",
            ticker, price, condition, list_result,
        )
        return None

    alert_id = _find_created_alert_id(list_result.get("alerts", []), ticker, condition)
    if alert_id is None:
        logger.warning(
            "create_price_alert: no matching alert found for '%s' (%s) in post-creation listing",
            ticker, condition,
        )
        return None

    logger.info(
        "create_price_alert: created alert_id=%s for ticker=%s price=%s condition=%s",
        alert_id, ticker, price, condition,
    )
    return alert_id
