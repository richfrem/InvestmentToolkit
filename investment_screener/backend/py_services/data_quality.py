"""Data quality checks for market data layer.

Purpose:
    This module provides cross-source disagreement and staleness validation for financial data.
    Every get_fundamentals() call gates through these checks. Flags attach to the response and never
    block it — the calling script/agent decides whether to proceed. This matches the repo's existing
    philosophy of surfacing conflicts rather than auto-resolving them (used elsewhere for standing
    decisions, confluence gates, and portfolio-total reconciliation).

Layer:
    Market data layer — pre-response quality gates.

Key Input Dependencies:
    - investment_screener/backend/data/portfolio.json (Validates schema alignment)
"""

from datetime import datetime, timezone


def check_disagreement(
    edgar_value: float, yfinance_value: float, metric_name: str, threshold_pct: float = 5.0
) -> dict | None:
    """Check if edgar_value and yfinance_value disagree beyond a threshold.

    Args:
        edgar_value: The value from SEC EDGAR source.
        yfinance_value: The value from yfinance source.
        metric_name: Name of the metric being compared (e.g., "revenue", "eps").
        threshold_pct: Percentage threshold for flagging disagreement. Default 5.0.

    Returns:
        None if values agree within threshold_pct (inclusive), or if edgar_value is 0.0.
        Otherwise, a dict with keys: "metric", "edgarValue", "yfinanceValue", "diffPct".
    """
    # Guard against division by zero
    if edgar_value == 0.0:
        return None

    # Calculate percentage difference: (yfinance - edgar) / edgar * 100
    diff_pct = abs((yfinance_value - edgar_value) / edgar_value) * 100

    # Threshold is inclusive: exactly at threshold or below is NOT flagged
    if diff_pct <= threshold_pct:
        return None

    return {
        "metric": metric_name,
        "edgarValue": edgar_value,
        "yfinanceValue": yfinance_value,
        "diffPct": diff_pct,
    }


def check_staleness(as_of_date: str, max_age_days: int = 120) -> bool:
    """Check if as_of_date is older than max_age_days.

    Args:
        as_of_date: Date string in "%Y-%m-%d" format.
        max_age_days: Maximum age in days before data is considered stale. Default 120.

    Returns:
        False if data is within max_age_days (inclusive).
        True if data is older than max_age_days.

    Raises:
        ValueError: If as_of_date is not in "%Y-%m-%d" format.
    """
    # Parse the date string; will raise ValueError if malformed
    as_of = datetime.strptime(as_of_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)

    # Get current time
    now = datetime.now(timezone.utc)

    # Calculate age in days
    age = (now - as_of).days

    # Boundary is inclusive: exactly at max_age_days is NOT stale
    return age > max_age_days
