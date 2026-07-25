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
    4. Correlates the newly created one by ticker + price to recover its
       real alert_id.

This module is the foundation for later 5C tasks (dedup, /daily
integration) — they call create_price_alert() rather than composing
tv_call() directly.

Key Input Dependencies:
    - plugins/tradingview/scripts/tv_client.py (Task 5A-8's tv_call())
"""

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, ValidationError

# Cross-directory import of tv_call (Task 5A-8). Follows the exact same
# sys.path-insert pattern pine_script_manager.py already established —
# plugins/tradingview/scripts/ is not a package on the default path.
# tv_client.py is not touched; this module only wraps its output.
_TV_SCRIPTS_DIR = str(Path(__file__).resolve().parents[3] / "plugins" / "tradingview" / "scripts")
if _TV_SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _TV_SCRIPTS_DIR)

from tv_client import tv_call  # noqa: E402

# Same-directory import (Task 5C-5, cut over to intelligence_event reads
# in Wave 5D Task 8 -- this consumer was missed by Task 3's original
# cutover, found via Task 8's archive-prerequisite grep against the now-
# archived predictions.jsonl). generate_track_record_report.py lives in
# this same py_services/ directory, so a plain top-level import works with
# no sys.path manipulation (unlike tv_client.py's genuinely cross-directory
# import above).
from generate_track_record_report import (  # noqa: E402
    DEFAULT_INTEL_DB_PATH,
    _load_predictions_from_ledger,
)

logger = logging.getLogger(__name__)

# Central alert metadata ledger (Task 5C-4). Tests monkeypatch this
# module-level constant to a temp path — never write to the real path
# from a test. Same `.parents[1]` pattern as tv_cdp_health.py's
# TV_CDP_ERRORS_PATH/TV_CDP_CACHE_PATH — alert_manager.py lives in the
# same py_services/ directory, so `.parents[1]` resolves to
# investment_screener/backend/.
ALERTS_STATE_PATH = Path(__file__).resolve().parents[1] / "data" / "alerts_state.jsonl"


class AlertMetadata(BaseModel):
    """One alert's persisted metadata record.

    `id` is the REAL TradingView alert_id (from create_price_alert()'s
    return value or sync_alert_state()'s output) — not a synthetic UUID.
    Reusing TV's own real ID as the primary key avoids a redundant
    parallel identifier scheme that would need its own correlation step
    against 5C-1/5C-3's already-real alert_ids.

    Attributes:
        id: The real TV alert_id.
        ticker: Ticker symbol the alert was created for.
        price: Alert trigger price level.
        direction: "above" or "below" (matches alert_manager.py's
            existing two-value interface, Task 5C-1).
        type: "price" (a plain price-threshold alert — everything
            alert_manager.py creates today) or "ta_signal" (reserved for
            a future signal-driven alert variant, not yet built by any
            completed task).
        linked_claim_id: An E3 prediction-ledger claim ID this alert is
            based on, or None if not yet linked (Task 5C-5's concern —
            this field exists now so 5C-5 doesn't need a schema
            migration later).
        created_at: ISO 8601 timestamp of when this metadata record was
            created (NOT necessarily identical to when TV created the
            alert — this is when *this record* was written).
        fired_at: ISO 8601 timestamp if fired, else None.
        state: "pending"/"fired"/"expired" — matches sync_alert_state()'s
            (Task 5C-3) exact 3-state vocabulary.
    """

    id: str
    ticker: str
    price: float
    direction: Literal["above", "below"]
    type: Literal["price", "ta_signal"]
    linked_claim_id: Optional[str] = None
    created_at: str
    fired_at: Optional[str] = None
    state: Literal["pending", "fired", "expired"]


def save_alert_metadata(record: AlertMetadata) -> None:
    """Append one alert metadata record to data/alerts_state.jsonl.

    Append-only: never rewrites or reads prior records. Creates the
    parent directory if needed.

    Args:
        record: The AlertMetadata to persist.

    Raises:
        OSError: If the append write fails. Callers are responsible for
            handling this — matches pine_script_manager.save_registry()'s
            precedent (Task 5B-1): this is a real file write to a
            genuine tracked deliverable, so silent failure would be
            worse than a clear, catchable exception.
    """
    ALERTS_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(ALERTS_STATE_PATH, "a") as f:
        f.write(record.model_dump_json() + "\n")


def load_alert_metadata() -> List[AlertMetadata]:
    """Load every alert metadata record from data/alerts_state.jsonl.

    Never raises: a missing file returns []. A line that fails JSON
    parsing or Pydantic validation is skipped (with a warning) rather
    than aborting the whole load — matches this module's established
    graceful-degradation posture for reads (writes are the one place
    this sub-spec allows raising, per save_alert_metadata() above).

    Returns:
        List of AlertMetadata records, in file order (oldest first).
    """
    if not ALERTS_STATE_PATH.exists():
        return []
    records: List[AlertMetadata] = []
    with open(ALERTS_STATE_PATH) as f:
        for line in f:
            if not line.strip():
                continue
            try:
                records.append(AlertMetadata(**json.loads(line)))
            except (json.JSONDecodeError, ValidationError) as e:
                logger.warning("load_alert_metadata: skipping malformed line: %s", e)
    return records


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


def _extract_condition_price(condition) -> Optional[float]:
    """Extract the price threshold from a real TV alert's raw `condition`
    object.

    Confirmed live against the user's real TradingView account
    (2026-07-14, 306 sampled alerts, read-only `alert list` call): every
    real alert's `condition` field is a nested object of the shape
    `{"type": ..., "series": [{"type": "barset"}, {"type": "value",
    "value": <price>}], ...}`, NOT a simple string — the price threshold
    lives at `condition["series"][1]["value"]`.

    Never raises: any structural mismatch (missing/malformed condition,
    too-short series, non-numeric value) degrades to None rather than
    raising — this is informational correlation, not a hard contract.

    Args:
        condition: The raw `condition` field from one entry in an
            `alert list` response's `alerts` array.

    Returns:
        The extracted price threshold as a float, or None if the
        structure doesn't match what's been observed against real data.
    """
    try:
        series = condition.get("series") if isinstance(condition, dict) else None
        if not isinstance(series, list) or len(series) < 2:
            return None
        value_entry = series[1]
        value = value_entry.get("value") if isinstance(value_entry, dict) else None
        return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None
    except Exception:
        return None


def _find_created_alert_id(
    alerts: List[Dict], ticker: str, price: float
) -> Optional[str]:
    """Correlate the just-created alert in a freshly listed alerts array.

    Matches on ticker (case-insensitive substring on `symbol`, since TV
    may prefix with an exchange, e.g. "NASDAQ:NVDA") + price threshold
    (within a small tolerance, since float round-tripping through TV's
    UI/API isn't guaranteed bit-exact) — NOT on condition.type, which is
    only confirmed as "cross" for every real alert sampled to date and
    cannot be reliably distinguished for "greater_than"/"less_than"
    without creating a live, permanently-undeletable test alert (not
    done — see this fix's own bugfix brief for why).

    Args:
        alerts: The `alerts` array from an `alert list` tv_call()
            response (real shape per tradingview-cdp/core/alerts.js:75-103).
        ticker: The ticker just switched to and alerted on.
        price: The price threshold just used to create the alert.

    Returns:
        The matching alert's `alert_id` if exactly one match is found.
        If multiple match (e.g. a pre-existing alert with the same
        ticker/price already existed), the one with the latest `created`
        timestamp if present, else the first match. None if zero alerts
        match — a documented, accepted limitation (creation may have
        failed silently in the DOM, or this list call raced ahead of
        TV's own internal state), not solved here.
    """
    matches = [
        a for a in alerts
        if isinstance(a, dict)
        and ticker.upper() in str(a.get("symbol", "")).upper()
        and (entry_price := _extract_condition_price(a.get("condition"))) is not None
        and abs(entry_price - price) < 0.01
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
    newly created one by ticker + price.

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

    alert_id = _find_created_alert_id(list_result.get("alerts", []), ticker, price)
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


def dedup_alerts(ticker: str, price: float, direction: str) -> Optional[str]:
    """
    Check whether an alert already exists for (ticker, price) among the
    user's current TV alerts, returning its real alert_id if so.

    `direction` is validated (raises ValueError on invalid input, same
    contract as create_price_alert()) but does NOT participate in the
    match — see this task's brief for why (the real TV alert list
    response can't reliably distinguish direction; see 5C-1's
    condition-shape bugfix, commit ea2d295).

    Read-only: never creates, modifies, or deletes any TV alert. Pure
    creation stays in create_price_alert() (5C-1's own design decision:
    "No dedup in this task... create_price_alert is pure creation") —
    this function is the symmetric "pure checking" counterpart. A caller
    wanting create-if-not-duplicate composes both:
        existing = dedup_alerts(ticker, price, direction)
        alert_id = existing or create_price_alert(ticker, price, direction)

    Never raises for TV/network failures — a list-call failure degrades
    to None (treated as "no duplicate found, safe to create" — matches
    the conservative default of not silently blocking a real signal from
    getting an alert just because a dedup check couldn't complete).

    Args:
        ticker: Ticker symbol to check for an existing alert.
        price: Alert trigger price level. Must be positive.
        direction: "above" or "below" (validated only, not matched).

    Raises:
        ValueError: If ticker/price/direction fail input validation.

    Returns:
        The existing alert's real TV alert_id if a (ticker, price) match
        is found, else None.
    """
    _validate_alert_input(ticker, price, direction)

    list_result = tv_call("alert", "list")
    if not _tv_call_succeeded(list_result):
        logger.warning("dedup_alerts: alert list failed for '%s': %s", ticker, list_result)
        return None

    return _find_created_alert_id(list_result.get("alerts", []), ticker, price)


def _classify_alert_state(entry: Dict) -> Optional[str]:
    """Classify one raw `alert list` entry into pending/fired/expired.

    Uses ONLY the real, confirmed `active` and `last_fired` fields
    (Task 5C-3's brief, grounded in 306 live-sampled real alerts) —
    deliberately never reads `expiration`, since no confirmed real
    example exists of that field's shape on a genuinely expired alert;
    guessing at it risks silently misclassifying real data.

    Classification priority (fired wins over everything else, since
    `last_fired`'s presence is the most information-dense, unambiguous
    real signal available):
        - last_fired is not None                  -> "fired"
        - last_fired is None and active is False   -> "expired"
        - last_fired is None and active is True    -> "pending"
        - anything else (missing/malformed `active`) -> "pending"
          (conservative fallback — never silently call an ambiguous
          entry "fired"/"expired" when it isn't clearly either)

    Args:
        entry: One raw entry from an `alert list` response's `alerts`
            array. Expected to be a dict, but this function does not
            validate `alert_id` presence — that check belongs to the
            caller (sync_alert_state()), which also decides whether to
            skip the entry entirely.

    Returns:
        "pending", "fired", or "expired".
    """
    last_fired = entry.get("last_fired")
    if last_fired is not None:
        return "fired"
    if entry.get("active") is False:
        return "expired"
    return "pending"


def sync_alert_state() -> List[Dict[str, Optional[str]]]:
    """
    Poll TV for all current alerts and classify each into pending/fired/
    expired for this single poll.

    Stateless: does not persist results or compare against a prior poll
    (Task 5C-4's persistence layer, not yet built, owns that). Classifies
    using TV's own authoritative `active`/`last_fired` fields — never
    independently re-derives firing status via a price comparison (TV's
    server-side alert firing is authoritative; re-deriving it client-side
    would be redundant and race-prone).

    Never raises: a failed `alert list` call, or any malformed individual
    alert entry, degrades gracefully (empty list, or that one entry
    skipped) rather than propagating.

    Returns:
        List of {"alert_id", "symbol", "state", "last_fired", "created"}
        dicts, one per successfully classified alert. Empty list if the
        TV call fails or there are no alerts.
    """
    list_result = tv_call("alert", "list")
    if not _tv_call_succeeded(list_result):
        logger.warning("sync_alert_state: alert list failed: %s", list_result)
        return []

    updated_alerts: List[Dict[str, Optional[str]]] = []
    for entry in list_result.get("alerts", []):
        if not isinstance(entry, dict) or "alert_id" not in entry:
            logger.warning("sync_alert_state: skipping malformed alert entry: %r", entry)
            continue

        updated_alerts.append({
            "alert_id": entry.get("alert_id"),
            "symbol": entry.get("symbol"),
            "state": _classify_alert_state(entry),
            "last_fired": entry.get("last_fired"),
            "created": entry.get("created"),
        })

    return updated_alerts


def _latest_alert_metadata(alert_id: str) -> Optional[AlertMetadata]:
    """Find the most recently appended AlertMetadata record for `alert_id`.

    alerts_state.jsonl may contain multiple snapshots per id (5C-4's
    append-only design — an update is a new record, not an in-place
    rewrite). File order is oldest-first, so the LAST matching record
    is the current/latest one.

    Args:
        alert_id: The real TV alert_id to look up.

    Returns:
        The latest AlertMetadata record for this id, or None if no
        record exists for it yet.
    """
    matches = [r for r in load_alert_metadata() if r.id == alert_id]
    return matches[-1] if matches else None


def link_alert_to_claim(
    alert_id: str, claim_id_from_e3: str, db_path: str = DEFAULT_INTEL_DB_PATH
) -> bool:
    """
    Link an existing alert's metadata to an E3 prediction-ledger claim,
    for audit ("was this alert based on this claim?").

    Verifies BOTH the alert (via _latest_alert_metadata) and the claim
    (via a PREDICTION_CLAIM read from intelligence_event, matching on the
    claim's real `id` field) exist before linking — a link to a
    nonexistent alert or claim is a no-op, not a partial/dangling link.

    Appends a NEW AlertMetadata snapshot (5C-4's append-only design):
    a copy of the alert's latest record with `linked_claim_id` set to
    `claim_id_from_e3` and `created_at` refreshed to the link time —
    every other field (ticker, price, direction, type, state, fired_at)
    is carried over unchanged from the latest prior snapshot.

    Raises:
        OSError: If the underlying save_alert_metadata() write fails —
            deliberately NOT caught here (see this task's brief for
            why: unlike Task 5B-3's inject_pine_script(), there is no
            prior external side effect this write could be "wasted"
            protecting — a write failure here IS a genuine failure of
            "did the link succeed," so it propagates rather than being
            silently swallowed).

    Args:
        alert_id: The real TV alert_id to link (must already have at
            least one AlertMetadata record).
        claim_id_from_e3: The E3 prediction-ledger claim's real `id`
            field (e.g. "AAPL:earnings_expectation:2026-07-12").

    Returns:
        True if the link was created (both alert and claim existed and
        the new snapshot was persisted). False if either the alert or
        the claim doesn't exist — no record is appended in that case.
    """
    existing = _latest_alert_metadata(alert_id)
    if existing is None:
        logger.warning("link_alert_to_claim: no existing alert metadata for '%s'", alert_id)
        return False

    claims = _load_predictions_from_ledger(db_path)
    if not any(c.get("id") == claim_id_from_e3 for c in claims):
        logger.warning("link_alert_to_claim: claim '%s' not found in predictions ledger",
                        claim_id_from_e3)
        return False

    updated = existing.model_copy(update={
        "linked_claim_id": claim_id_from_e3,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    save_alert_metadata(updated)
    return True


def get_alerts_for_ticker(ticker: str) -> List[Dict]:
    """
    Real TV alerts for `ticker`, enriched with extracted price + state.

    Filters tv_call("alert", "list")'s response by ticker (case-
    insensitive substring on `symbol`, same matching convention as
    _find_created_alert_id()), then enriches each match using the
    already-built _extract_condition_price() (5C-1) and
    _classify_alert_state() (5C-3) — reused unchanged, not reimplemented.

    Never raises: a failed list call returns []; a malformed entry
    (non-dict, missing alert_id) is skipped, matching sync_alert_state()'s
    established convention.

    Args:
        ticker: Ticker symbol to filter alerts for.

    Returns:
        List of {"alert_id": str, "symbol": str, "price": float | None,
        "state": str} dicts — one per matching alert. `price` is None if
        the condition's price threshold couldn't be extracted (matches
        _extract_condition_price()'s own degradation contract).
    """
    list_result = tv_call("alert", "list")
    if not _tv_call_succeeded(list_result):
        logger.warning("get_alerts_for_ticker: alert list failed for '%s': %s", ticker, list_result)
        return []

    results = []
    for entry in list_result.get("alerts", []):
        if not isinstance(entry, dict) or "alert_id" not in entry:
            logger.warning("get_alerts_for_ticker: skipping malformed entry: %r", entry)
            continue
        if ticker.upper() not in str(entry.get("symbol", "")).upper():
            continue
        results.append({
            "alert_id": entry["alert_id"],
            "symbol": entry.get("symbol"),
            "price": _extract_condition_price(entry.get("condition")),
            "state": _classify_alert_state(entry),
        })
    return results


# Mirrors brief_recommendations._ACTIONABLE_BANDS's value exactly — that
# constant is module-private (underscore-prefixed) so it isn't imported
# cross-module (same "don't import private names" convention already
# established for _tv_call_succeeded() in this file); duplicated here
# instead, same precedent.
_ACTIONABLE_BANDS = frozenset({"EXIT", "REDUCE", "ACCUMULATE"})


def score_alert_correlation(
    alert: Dict,
    current_price: float,
    ta_signal: Optional[Dict] = None,
) -> Dict:
    """
    Score how relevant one alert is right now.

    proximity_pct: how far (in %) `current_price` is from the alert's
    own price threshold — abs(current_price - alert_price) / alert_price
    * 100. Lower means the alert is closer to triggering. None if the
    alert's price couldn't be extracted (see get_alerts_for_ticker())
    or is exactly 0 (avoids a division-by-zero).

    matches_ta_signal: True only if `ta_signal` was supplied AND its
    "band" field is one of the actionable bands this codebase already
    uses elsewhere (ACCUMULATE/EXIT/REDUCE, matching
    brief_recommendations._ACTIONABLE_BANDS's exact value) — i.e. TV's
    alert and today's TA-driven signal agree this ticker deserves
    attention right now. False if no ta_signal was supplied, or its
    band isn't actionable, or the field is missing/malformed.

    Never raises: malformed/missing `ta_signal` fields degrade to
    matches_ta_signal=False.

    Args:
        alert: One entry from get_alerts_for_ticker()'s output.
        current_price: The ticker's current live price — caller-
            supplied (this module deliberately doesn't fetch pricing
            itself; see this task's brief for why).
        ta_signal: Optional dict with at least a "band" key, matching
            the shape of a conviction-score row (e.g.
            daily_brief.py's scores_raw entries) — the caller's own
            current TA read for this ticker, if it has one.

    Returns:
        {"proximity_pct": float | None, "matches_ta_signal": bool}
    """
    alert_price = alert.get("price")
    if alert_price is None or alert_price == 0:
        proximity_pct = None
    else:
        proximity_pct = abs(current_price - alert_price) / alert_price * 100

    band = (ta_signal or {}).get("band")
    matches_ta_signal = band in _ACTIONABLE_BANDS

    return {"proximity_pct": proximity_pct, "matches_ta_signal": matches_ta_signal}
