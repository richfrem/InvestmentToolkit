#!/usr/bin/env python3
"""
evolution_events.py - Python utility script.

Purpose:
    Evolution events — G4 append-only event ledger and tracking system.

Tracks six types of portfolio evolution events with append-only JSONL storage:
  - data/evolution_events.jsonl    one record per event
  - Dedup on (ticker, event_type, event_date)
  - Outcome fields NULL until 7/30 day windows have passed

Supported event types:
  1. earnings_catalyst (EarningsGrade input)
  2. thesis_breaker_override (breaker override action)
  3. rebalance_execution (rebalance order execution)
  4. large_price_move (price move ±5% or TA signals)
  5. dividend_event (dividend payment)
  6. forced_exit (stop-loss or manual exit)

Usage:
    from evolution_events import (
        emit_earnings_event, emit_breaker_override_event,
        emit_rebalance_event, emit_price_move_event,
        emit_dividend_event, emit_forced_exit_event,
        populate_event_outcomes, generate_evolution_correlation_report
    )

Key Input Dependencies:
    - investment_screener/backend/data/portfolio.json
    - investment_screener/backend/data/ta-sweep-results.json
    - yfinance for historical price data

Layer:
    Backend / Python Services

Usage Examples:
    from evolution_events import (
        emit_earnings_event, emit_breaker_override_event,
        emit_rebalance_event, emit_price_move_event,
        emit_dividend_event, emit_forced_exit_event,
        populate_event_outcomes, generate_evolution_correlation_report
    )

Key Functions (Index):
    - EventType()
    - EarningsGrade()
    - _make_event_context()
    - _make_event_outcome()
    - _make_evolution_event()
    - _append_jsonl()
    - _load_jsonl()
    - _dedup_key()
    - _should_append_event()
    - emit_earnings_event()
    - emit_breaker_override_event()
    - emit_rebalance_event()
    - emit_price_move_event()
    - emit_dividend_event()
    - emit_forced_exit_event()
    - populate_event_outcomes()
    - generate_evolution_correlation_report()
    - load_events()
    - main()

Key Input Dependencies:
    None

Key Output Dependencies:
    None
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = REPO_ROOT / "investment_screener/backend/data"
EVOLUTION_EVENTS_PATH = DATA_DIR / "evolution_events.jsonl"


# ── Enums and Event Types ──────────────────────────────────────────────────────


class EventType(str, Enum):
    """Six event types tracked in the evolution ledger."""
    EARNINGS_CATALYST = "earnings_catalyst"
    THESIS_BREAKER_OVERRIDE = "thesis_breaker_override"
    REBALANCE_EXECUTION = "rebalance_execution"
    LARGE_PRICE_MOVE = "large_price_move"
    DIVIDEND_EVENT = "dividend_event"
    FORCED_EXIT = "forced_exit"


class EarningsGrade(str, Enum):
    """Earnings surprise grades."""
    BEAT = "beat"
    MISS = "miss"
    IN_LINE = "in_line"


# ── Schema Models (Pydantic-style dicts) ───────────────────────────────────────


def _make_event_context(
    ticker: str,
    event_type: EventType,
    event_date: str,
    entry_price: Optional[float] = None,
    shares: Optional[float] = None,
    current_price: Optional[float] = None,
) -> dict[str, Any]:
    """Build the context sub-model for an event."""
    return {
        "ticker": ticker,
        "event_type": event_type.value,
        "event_date": event_date,
        "entry_price": entry_price,
        "shares": shares,
        "current_price": current_price,
    }


def _make_event_outcome(
    outcome_seven_day: Optional[float] = None,
    outcome_thirty_day: Optional[float] = None,
    seven_day_price: Optional[float] = None,
    thirty_day_price: Optional[float] = None,
) -> dict[str, Any]:
    """Build the outcome sub-model for an event.

    Args:
        outcome_seven_day: Return % over 7 days (NULL if window not passed).
        outcome_thirty_day: Return % over 30 days (NULL if window not passed).
        seven_day_price: Price at 7-day mark (NULL if window not passed).
        thirty_day_price: Price at 30-day mark (NULL if window not passed).
    """
    return {
        "outcome_seven_day": outcome_seven_day,
        "outcome_thirty_day": outcome_thirty_day,
        "seven_day_price": seven_day_price,
        "thirty_day_price": thirty_day_price,
    }


def _make_evolution_event(
    ticker: str,
    event_type: EventType,
    event_date: str,
    context: dict[str, Any],
    event_details: dict[str, Any],
    entry_price: Optional[float] = None,
    shares: Optional[float] = None,
    current_price: Optional[float] = None,
) -> dict[str, Any]:
    """Build a complete evolution event record."""
    return {
        "event_id": f"{ticker}:{event_type.value}:{event_date}",
        "context": _make_event_context(
            ticker, event_type, event_date, entry_price, shares, current_price
        ),
        "event_details": event_details,
        "outcome": _make_event_outcome(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ── Helper Functions ───────────────────────────────────────────────────────────


def _append_jsonl(record: dict[str, Any], path: Path) -> None:
    """Append one JSON record as a line, creating parent dirs as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(record) + "\n")


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    """Load every record from a JSONL file, or [] if it doesn't exist."""
    if not path.exists():
        return []
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def _dedup_key(record: dict[str, Any]) -> tuple[str, str, str]:
    """Extract dedup key from an event record."""
    ctx = record.get("context", {})
    return (ctx.get("ticker", ""), ctx.get("event_type", ""), ctx.get("event_date", ""))


def _should_append_event(
    record: dict[str, Any],
    existing_events: list[dict[str, Any]],
) -> bool:
    """Check if event should be appended based on dedup and context changes.

    Only appends if (ticker, event_type, event_date) is new OR if context has changed.
    """
    key = _dedup_key(record)
    for existing in existing_events:
        if _dedup_key(existing) == key:
            # Same (ticker, event_type, event_date) — only append if context differs
            return existing.get("event_details") != record.get("event_details")
    return True


# ── Event Emitters ─────────────────────────────────────────────────────────────


def emit_earnings_event(
    ticker: str,
    grade: EarningsGrade,
    earnings_date: str,
    expected_eps: Optional[float] = None,
    actual_eps: Optional[float] = None,
    current_price: Optional[float] = None,
    entry_price: Optional[float] = None,
    shares: Optional[float] = None,
) -> None:
    """Emit an earnings catalyst event (non-blocking).

    Args:
        ticker: Stock ticker.
        grade: EarningsGrade (beat, miss, or in_line).
        earnings_date: ISO date string.
        expected_eps: Expected earnings per share.
        actual_eps: Actual earnings per share.
        current_price: Current stock price.
        entry_price: Entry price at time of event.
        shares: Position size.
    """
    try:
        existing = _load_jsonl(EVOLUTION_EVENTS_PATH)
        event = _make_evolution_event(
            ticker=ticker,
            event_type=EventType.EARNINGS_CATALYST,
            event_date=earnings_date,
            context={},
            event_details={
                "grade": grade.value,
                "expected_eps": expected_eps,
                "actual_eps": actual_eps,
                "surprise_pct": (
                    ((actual_eps - expected_eps) / expected_eps * 100)
                    if expected_eps and actual_eps
                    else None
                ),
            },
            current_price=current_price,
            entry_price=entry_price,
            shares=shares,
        )
        if _should_append_event(event, existing):
            _append_jsonl(event, EVOLUTION_EVENTS_PATH)
    except Exception:
        # Non-blocking: silently fail
        pass


def emit_breaker_override_event(
    ticker: str,
    breaker_name: str,
    override_date: str,
    override_reason: str,
    breaker_threshold: Optional[float] = None,
    current_price: Optional[float] = None,
    entry_price: Optional[float] = None,
    shares: Optional[float] = None,
) -> None:
    """Emit a thesis breaker override event (non-blocking).

    Args:
        ticker: Stock ticker.
        breaker_name: Name of the thesis breaker.
        override_date: ISO date string.
        override_reason: Reason for override.
        breaker_threshold: Breaker threshold value.
        current_price: Current stock price.
        entry_price: Entry price at time of event.
        shares: Position size.
    """
    try:
        existing = _load_jsonl(EVOLUTION_EVENTS_PATH)
        event = _make_evolution_event(
            ticker=ticker,
            event_type=EventType.THESIS_BREAKER_OVERRIDE,
            event_date=override_date,
            context={},
            event_details={
                "breaker_name": breaker_name,
                "override_reason": override_reason,
                "breaker_threshold": breaker_threshold,
            },
            current_price=current_price,
            entry_price=entry_price,
            shares=shares,
        )
        if _should_append_event(event, existing):
            _append_jsonl(event, EVOLUTION_EVENTS_PATH)
    except Exception:
        # Non-blocking: silently fail
        pass


def emit_rebalance_event(
    ticker: str,
    order_type: str,  # "buy" or "sell"
    order_quantity: float,
    order_price: float,
    rebalance_date: str,
    trade_id: Optional[str] = None,
    current_price: Optional[float] = None,
    entry_price: Optional[float] = None,
    shares: Optional[float] = None,
) -> None:
    """Emit a rebalance execution event (non-blocking).

    Args:
        ticker: Stock ticker.
        order_type: "buy" or "sell".
        order_quantity: Quantity in the order.
        order_price: Price at execution.
        rebalance_date: ISO date string.
        trade_id: Optional trade identifier.
        current_price: Current stock price.
        entry_price: Entry price at time of event.
        shares: Position size.
    """
    try:
        existing = _load_jsonl(EVOLUTION_EVENTS_PATH)
        event = _make_evolution_event(
            ticker=ticker,
            event_type=EventType.REBALANCE_EXECUTION,
            event_date=rebalance_date,
            context={},
            event_details={
                "order_type": order_type,
                "order_quantity": order_quantity,
                "order_price": order_price,
                "trade_id": trade_id,
            },
            current_price=current_price,
            entry_price=entry_price,
            shares=shares,
        )
        if _should_append_event(event, existing):
            _append_jsonl(event, EVOLUTION_EVENTS_PATH)
    except Exception:
        # Non-blocking: silently fail
        pass


def emit_price_move_event(
    ticker: str,
    move_pct: float,
    move_date: str,
    ta_signal: Optional[str] = None,
    prior_price: Optional[float] = None,
    current_price: Optional[float] = None,
    entry_price: Optional[float] = None,
    shares: Optional[float] = None,
) -> None:
    """Emit a large price move event (±5% or TA signal trigger).

    Args:
        ticker: Stock ticker.
        move_pct: Price move percentage (positive/negative).
        move_date: ISO date string.
        ta_signal: TA signal name (e.g., "RSI_OVERBOUGHT", "ADX_STRONG").
        prior_price: Price before move.
        current_price: Current stock price.
        entry_price: Entry price at time of event.
        shares: Position size.
    """
    try:
        existing = _load_jsonl(EVOLUTION_EVENTS_PATH)
        event = _make_evolution_event(
            ticker=ticker,
            event_type=EventType.LARGE_PRICE_MOVE,
            event_date=move_date,
            context={},
            event_details={
                "move_pct": move_pct,
                "ta_signal": ta_signal,
                "prior_price": prior_price,
            },
            current_price=current_price,
            entry_price=entry_price,
            shares=shares,
        )
        if _should_append_event(event, existing):
            _append_jsonl(event, EVOLUTION_EVENTS_PATH)
    except Exception:
        # Non-blocking: silently fail
        pass


def emit_dividend_event(
    ticker: str,
    dividend_amount: float,
    ex_date: str,
    payment_date: Optional[str] = None,
    current_price: Optional[float] = None,
    entry_price: Optional[float] = None,
    shares: Optional[float] = None,
) -> None:
    """Emit a dividend event (non-blocking).

    Args:
        ticker: Stock ticker.
        dividend_amount: Dividend amount per share.
        ex_date: ISO ex-dividend date.
        payment_date: ISO payment date.
        current_price: Current stock price.
        entry_price: Entry price at time of event.
        shares: Position size.
    """
    try:
        existing = _load_jsonl(EVOLUTION_EVENTS_PATH)
        event = _make_evolution_event(
            ticker=ticker,
            event_type=EventType.DIVIDEND_EVENT,
            event_date=ex_date,
            context={},
            event_details={
                "dividend_amount": dividend_amount,
                "payment_date": payment_date,
            },
            current_price=current_price,
            entry_price=entry_price,
            shares=shares,
        )
        if _should_append_event(event, existing):
            _append_jsonl(event, EVOLUTION_EVENTS_PATH)
    except Exception:
        # Non-blocking: silently fail
        pass


def emit_forced_exit_event(
    ticker: str,
    exit_price: float,
    exit_date: str,
    exit_reason: str,  # "stop_loss", "manual_exit", etc.
    stop_loss_price: Optional[float] = None,
    entry_price: Optional[float] = None,
    shares: Optional[float] = None,
) -> None:
    """Emit a forced exit event (stop-loss or manual exit).

    Args:
        ticker: Stock ticker.
        exit_price: Price at which exit occurred.
        exit_date: ISO date string.
        exit_reason: Reason for exit (stop_loss, manual_exit, etc.).
        stop_loss_price: Stop loss level (if applicable).
        entry_price: Entry price at time of event.
        shares: Position size (before exit).
    """
    try:
        existing = _load_jsonl(EVOLUTION_EVENTS_PATH)
        event = _make_evolution_event(
            ticker=ticker,
            event_type=EventType.FORCED_EXIT,
            event_date=exit_date,
            context={},
            event_details={
                "exit_price": exit_price,
                "exit_reason": exit_reason,
                "stop_loss_price": stop_loss_price,
                "realized_loss_pct": (
                    ((exit_price - entry_price) / entry_price * 100)
                    if entry_price
                    else None
                ),
            },
            current_price=exit_price,
            entry_price=entry_price,
            shares=shares,
        )
        if _should_append_event(event, existing):
            _append_jsonl(event, EVOLUTION_EVENTS_PATH)
    except Exception:
        # Non-blocking: silently fail
        pass


# ── Outcome Population ─────────────────────────────────────────────────────────


def populate_event_outcomes() -> None:
    """Populate outcome fields for events where the window has passed.

    Fetches prices 7d and 30d after event_date and populates:
      - outcome_seven_day (return %)
      - outcome_thirty_day (return %)
      - seven_day_price
      - thirty_day_price

    Only updates if window has fully passed (no lookahead bias).
    """
    try:
        import yfinance as yf

        events = _load_jsonl(EVOLUTION_EVENTS_PATH)
        updated = False

        for event in events:
            ctx = event.get("context", {})
            ticker = ctx.get("ticker")
            event_date_str = ctx.get("event_date")
            current_price = ctx.get("current_price")

            if not ticker or not event_date_str or not current_price:
                continue

            outcome = event.get("outcome", {})
            # Skip if outcome already populated
            if outcome.get("outcome_seven_day") is not None:
                continue

            try:
                event_dt = datetime.fromisoformat(event_date_str)
                today = datetime.now(timezone.utc)

                # 7-day window
                seven_day_dt = event_dt + timedelta(days=7)
                if today >= seven_day_dt:
                    yf_ticker = yf.Ticker(ticker)
                    hist = yf_ticker.history(start=event_date_str, end=seven_day_dt.date())
                    if not hist.empty:
                        seven_day_price = hist["Close"].iloc[-1]
                        outcome["seven_day_price"] = float(seven_day_price)
                        outcome["outcome_seven_day"] = (
                            (seven_day_price - current_price) / current_price * 100
                        )
                        updated = True

                # 30-day window
                thirty_day_dt = event_dt + timedelta(days=30)
                if today >= thirty_day_dt:
                    yf_ticker = yf.Ticker(ticker)
                    hist = yf_ticker.history(start=event_date_str, end=thirty_day_dt.date())
                    if not hist.empty:
                        thirty_day_price = hist["Close"].iloc[-1]
                        outcome["thirty_day_price"] = float(thirty_day_price)
                        outcome["outcome_thirty_day"] = (
                            (thirty_day_price - current_price) / current_price * 100
                        )
                        updated = True

                event["outcome"] = outcome
            except Exception:
                # Skip this event on error
                continue

        if updated:
            # Rewrite the file with updated outcomes
            EVOLUTION_EVENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(EVOLUTION_EVENTS_PATH, "w") as f:
                for event in events:
                    f.write(json.dumps(event) + "\n")
    except Exception:
        # Non-blocking: silently fail
        pass


# ── Correlation Reporting ─────────────────────────────────────────────────────


def generate_evolution_correlation_report(
    week_start: str,
    week_end: str,
) -> dict[str, Any]:
    """Generate evolution event correlation report for a week.

    Aggregates events by type, computes return statistics for each event type.

    Args:
        week_start: ISO date string (Monday of week).
        week_end: ISO date string (Friday of week).

    Returns:
        Dict with event_summary, correlation_stats, and recommendations.
    """
    try:
        events = _load_jsonl(EVOLUTION_EVENTS_PATH)

        # Filter to week range
        week_events = [
            e
            for e in events
            if week_start <= e.get("context", {}).get("event_date", "") <= week_end
        ]

        # Aggregate by event type
        event_summary: dict[str, Any] = {}
        for evt_type in EventType:
            type_events = [
                e for e in week_events
                if e.get("context", {}).get("event_type") == evt_type.value
            ]
            event_summary[evt_type.value] = {
                "count": len(type_events),
                "tickers": list(
                    set(e.get("context", {}).get("ticker") for e in type_events)
                ),
                "avg_7day_return": None,
                "avg_30day_return": None,
            }

            # Compute averages
            seven_day_returns = [
                e.get("outcome", {}).get("outcome_seven_day")
                for e in type_events
                if e.get("outcome", {}).get("outcome_seven_day") is not None
            ]
            thirty_day_returns = [
                e.get("outcome", {}).get("outcome_thirty_day")
                for e in type_events
                if e.get("outcome", {}).get("outcome_thirty_day") is not None
            ]

            if seven_day_returns:
                event_summary[evt_type.value]["avg_7day_return"] = sum(
                    seven_day_returns
                ) / len(seven_day_returns)
            if thirty_day_returns:
                event_summary[evt_type.value]["avg_30day_return"] = sum(
                    thirty_day_returns
                ) / len(thirty_day_returns)

        return {
            "week_start": week_start,
            "week_end": week_end,
            "event_summary": event_summary,
            "total_events": len(week_events),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception:
        return {
            "week_start": week_start,
            "week_end": week_end,
            "event_summary": {},
            "total_events": 0,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "error": "Failed to generate report",
        }


# ── CLI / Testing ──────────────────────────────────────────────────────────────


def load_events(path: Path = EVOLUTION_EVENTS_PATH) -> list[dict[str, Any]]:
    """Load all events from the JSONL file."""
    return _load_jsonl(path)


def main() -> None:
    """CLI entry point for testing/validation."""
    parser = argparse.ArgumentParser(description="Evolution events utilities")
    parser.add_argument("--validate", action="store_true", help="Validate event schema")
    args = parser.parse_args()

    if args.validate:
        events = load_events()
        print(f"Loaded {len(events)} events")
        for evt in events[:5]:
            print(f"  {evt.get('event_id')}")
        return
    parser.print_help()


if __name__ == "__main__":
    main()
