#!/usr/bin/env python3
"""
earnings_expectations.py - Python utility script.

Purpose:
    Defines Pydantic models for earnings expectation predictions and their
    grading outcomes. Earnings expectations capture consensus analyst forecasts
    at harvest time, then grade how actual earnings compare to those consensus
    targets at outcome time.

Layer:
    Backend / Python Services

Usage Examples:
    TBD

Key Functions (Index):
    - EarningsExpectationClaim()
    - EarningsExpectation()
    - EarningsGradeClaim()
    - EarningsGrade()
    - _fetch_consensus_for_ticker()
    - harvest_earnings_expectations()
    - grade_earnings_expectations()
    - get_earnings_context()

Key Input Dependencies:
    None

Key Output Dependencies:
    None
"""
from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, Field

# Optional yfinance import for graceful degradation
try:
    import yfinance as yf
except ImportError:
    yf = None


class EarningsExpectationClaim(BaseModel):
    """Earnings consensus forecast captured at harvest time.

    Attributes:
        consensus_eps: Consensus earnings per share from analyst surveys (float).
        consensus_revenue: Consensus revenue from analyst surveys (float, in USD).
        earnings_date: Date when actual earnings are expected to be released
            (YYYY-MM-DD format).
    """

    consensus_eps: float = Field(..., description="Consensus EPS from analyst surveys")
    consensus_revenue: float = Field(..., description="Consensus revenue in USD")
    earnings_date: str = Field(..., description="Expected earnings release date (YYYY-MM-DD)")

    model_config = {"json_schema_extra": {"examples": [
        {
            "consensus_eps": 0.52,
            "consensus_revenue": 9.4e9,
            "earnings_date": "2026-07-15"
        }
    ]}}


class EarningsExpectation(BaseModel):
    """Earnings expectation prediction record for predictions.jsonl.

    Captures a harvested earnings forecast prediction at a point in time,
    following the E3 prediction ledger schema with type="earnings_expectation".

    Attributes:
        v: Schema version (immutable, always 1).
        id: Stable prediction ID: {ticker}:{type}:{date}.
        date: Date the prediction was harvested (YYYY-MM-DD).
        ticker: Ticker symbol.
        type: Prediction type (must be "earnings_expectation").
        claim: Earnings consensus forecast.
        direction: Directional implication (bullish/bearish). For earnings
            expectations, typically derived from upside/downside implied by
            consensus vs. model forecasts.
        horizonDays: Days until grading horizon (typically 90 for earnings).
        basePrice: Ticker price at harvest time.
        baseSpyPrice: SPY price at harvest time (used for relative return calc).
        confidence: Optional confidence score (reserved, null for now).
        inputsHash: SHA256 hash of source artifact fields (for audit traceability).
        harvestedAt: ISO 8601 timestamp when prediction was harvested.
    """

    v: Literal[1] = Field(default=1)
    id: str = Field(..., description="Stable ID: {ticker}:{type}:{date}")
    date: str = Field(..., description="Harvest date (YYYY-MM-DD)")
    ticker: str = Field(..., description="Ticker symbol")
    type: Literal["earnings_expectation"] = Field(default="earnings_expectation")
    claim: EarningsExpectationClaim
    direction: str = Field(..., description="bullish or bearish")
    horizonDays: int = Field(default=90, description="Days until grading horizon")
    basePrice: float = Field(..., description="Ticker price at harvest")
    baseSpyPrice: float = Field(..., description="SPY price at harvest")
    confidence: Optional[float] = Field(default=None, description="Reserved for future use")
    inputsHash: str = Field(..., description="SHA256 of source artifact fields")
    harvestedAt: str = Field(..., description="ISO 8601 timestamp (UTC)")

    model_config = {
        "json_schema_extra": {"examples": [
            {
                "v": 1,
                "id": "NVDA:earnings_expectation:2026-07-12",
                "date": "2026-07-12",
                "ticker": "NVDA",
                "type": "earnings_expectation",
                "claim": {
                    "consensus_eps": 0.52,
                    "consensus_revenue": 9.4e9,
                    "earnings_date": "2026-07-15"
                },
                "direction": "bullish",
                "horizonDays": 90,
                "basePrice": 118.50,
                "baseSpyPrice": 611.20,
                "confidence": None,
                "inputsHash": "abc123...",
                "harvestedAt": "2026-07-12T18:30:00Z"
            }
        ]}
    }


class EarningsGradeClaim(BaseModel):
    """Graded outcome for an earnings expectation prediction.

    Attributes:
        prediction_id: Foreign key to EarningsExpectation.id.
        grade_date: Date when grading was performed (YYYY-MM-DD).
        grade: Outcome verdict (BEAT, MEET, MISS).
        actual_eps: Actual EPS reported (float).
        actual_revenue: Actual revenue reported (float, in USD).
        eps_surprise_pct: Surprise percentage: (actual - consensus) / abs(consensus) * 100.
        revenue_surprise_pct: Surprise percentage: (actual - consensus) / abs(consensus) * 100.
    """

    prediction_id: str = Field(..., description="Foreign key to EarningsExpectation.id")
    grade_date: str = Field(..., description="Grading date (YYYY-MM-DD)")
    grade: str = Field(..., description="BEAT, MEET, or MISS")
    actual_eps: float = Field(..., description="Actual EPS reported")
    actual_revenue: float = Field(..., description="Actual revenue in USD")
    eps_surprise_pct: float = Field(..., description="(actual - consensus) / abs(consensus) * 100")
    revenue_surprise_pct: float = Field(..., description="(actual - consensus) / abs(consensus) * 100")

    model_config = {"json_schema_extra": {"examples": [
        {
            "prediction_id": "NVDA:earnings_expectation:2026-07-12",
            "grade_date": "2026-07-16",
            "grade": "BEAT",
            "actual_eps": 0.56,
            "actual_revenue": 9.8e9,
            "eps_surprise_pct": 7.7,
            "revenue_surprise_pct": 4.3
        }
    ]}}


class EarningsGrade(BaseModel):
    """Earnings expectation grade record for predictions_graded.jsonl.

    Note: This is B4-specific enrichment. The core E3 grading model
    (predictions_graded.jsonl) only contains v, predictionId, gradedAt,
    tickerReturn, spyReturn, relativeReturn, verdict. This model extends
    that for domain-specific grading metadata.

    Attributes:
        v: Schema version (immutable, always 1).
        predictionId: Foreign key to EarningsExpectation.id.
        gradedAt: ISO 8601 timestamp when grading was performed.
        tickerReturn: Ticker return over the horizon: (price_now - basePrice) / basePrice.
        spyReturn: SPY return over the horizon: (spy_now - baseSpyPrice) / baseSpyPrice.
        relativeReturn: Ticker return minus SPY return (used for verdict).
        verdict: Grade outcome (correct, incorrect, inconclusive).
    """

    v: Literal[1] = Field(default=1)
    predictionId: str = Field(..., description="Foreign key to EarningsExpectation.id")
    gradedAt: str = Field(..., description="ISO 8601 timestamp (UTC)")
    tickerReturn: float = Field(..., description="Ticker return over horizon")
    spyReturn: float = Field(..., description="SPY return over horizon")
    relativeReturn: float = Field(..., description="Ticker return - SPY return")
    verdict: str = Field(..., description="correct, incorrect, or inconclusive")

    model_config = {
        "json_schema_extra": {"examples": [
            {
                "v": 1,
                "predictionId": "NVDA:earnings_expectation:2026-07-12",
                "gradedAt": "2026-10-10T18:30:00Z",
                "tickerReturn": 0.045,
                "spyReturn": 0.012,
                "relativeReturn": 0.033,
                "verdict": "correct"
            }
        ]}
    }


def _fetch_consensus_for_ticker(ticker: str) -> dict | None:
    """Fetch consensus earnings expectations for a single ticker.

    Retrieves analyst consensus EPS and revenue estimates along with the
    next earnings date from yfinance. Returns None on missing data or errors.

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', 'INTC').

    Returns:
        Dict with keys {consensus_eps, consensus_revenue, earnings_date} on success,
        or None if data unavailable or API error. All values may be None individually.

        Example return:
            {
                "consensus_eps": 1.05,
                "consensus_revenue": 3.8e11,
                "earnings_date": "2026-07-15"
            }
    """
    if yf is None:
        return None

    try:
        ticker_obj = yf.Ticker(ticker)

        # Fetch consensus estimates from yfinance info dict
        # epsTrailingTwelveMonths: trailing twelve months EPS
        # totalRevenue: most recent annual revenue
        info = ticker_obj.info or {}

        consensus_eps = info.get("epsTrailingTwelveMonths")
        consensus_revenue = info.get("totalRevenue")

        # Fetch next earnings date from calendar
        earnings_date_str = None
        try:
            cal = ticker_obj.calendar
            if cal is not None:
                import pandas as pd

                # yfinance returns a DataFrame — columns are dates
                raw_dt = None
                if isinstance(cal, pd.DataFrame) and len(cal.columns) > 0:
                    raw_dt = cal.columns[0]
                elif isinstance(cal, dict):
                    dates = cal.get("Earnings Date", [])
                    raw_dt = dates[0] if dates else None

                if raw_dt is not None:
                    earnings_date_obj = date.fromisoformat(str(raw_dt)[:10])
                    earnings_date_str = earnings_date_obj.isoformat()
        except Exception:
            # Earnings date fetch failed, continue with consensus data
            pass

        # Return dict even if fields are None (graceful degrade)
        return {
            "consensus_eps": consensus_eps,
            "consensus_revenue": consensus_revenue,
            "earnings_date": earnings_date_str,
        }

    except Exception:
        # API error, rate limit, timeout, etc. → graceful degrade to None
        return None


# ── Harvest core logic (Tasks 3-4) ──────────────────────────────────────────

# Import at module level for easier testing
try:
    from prediction_ledger import load_predictions as _load_predictions
    from prediction_ledger import make_prediction_id as _make_prediction_id
    from prediction_ledger import append_prediction as _append_prediction
    from prediction_ledger import load_graded as _load_graded
    from prediction_ledger import append_grade as _append_grade
    from prediction_ledger import grade_claim as _grade_claim
    PREDICTIONS_PATH = None  # Will be imported via prediction_ledger as needed
except ImportError:
    _load_predictions = None
    _make_prediction_id = None
    _append_prediction = None
    _load_graded = None
    _append_grade = None
    _grade_claim = None


def harvest_earnings_expectations(tickers: list[str] | None = None) -> list[dict]:
    """Harvest earnings expectations for given tickers, deduping on unchanged consensus.

    Main function for B4 Task 3-4. Compares current consensus to last-logged value
    (read from tail of predictions.jsonl). Appends new claim only if consensus changed
    or no prior record exists.

    Args:
        tickers: List of ticker symbols to harvest. If None, uses all holdings
            from target-portfolio.json.

    Returns:
        List of newly appended prediction dicts (empty if all were unchanged).

    Raises:
        No exception raised — gracefully degrades to empty list on missing data.
    """
    if not _load_predictions or not _append_prediction or not _make_prediction_id:
        return []

    # Load existing predictions (limit to last 1000 for efficiency)
    try:
        all_preds = _load_predictions()
        # Tail: keep only the last 1000
        recent_preds = all_preds[-1000:] if len(all_preds) > 1000 else all_preds
    except Exception:
        recent_preds = []

    # If tickers not provided, load from target-portfolio.json
    if tickers is None:
        try:
            from pathlib import Path
            repo_root = Path(__file__).resolve().parents[3]
            target_path = repo_root / "investment_screener/backend/data/theses/target-portfolio.json"
            with open(target_path) as f:
                target_data = json.load(f)
            tickers = [h.get("ticker") for h in target_data.get("holdings", [])
                      if h.get("ticker")]
        except Exception:
            tickers = []

    if not tickers:
        return []

    newly_appended = []
    today_str = date.today().isoformat()

    for ticker in tickers:
        try:
            # Fetch current consensus
            consensus = _fetch_consensus_for_ticker(ticker)
            if not consensus or consensus.get("consensus_eps") is None:
                # NULL consensus — graceful degrade, no claim logged
                continue

            earnings_date = consensus.get("earnings_date")
            if not earnings_date:
                # No earnings date — can't create claim
                continue

            # Check if we have a prior record for this ticker+earnings_date
            claim_type = "earnings_expectation"
            pred_id = _make_prediction_id(ticker, claim_type, today_str)
            last_pred = next(
                (p for p in reversed(recent_preds)
                 if p.get("ticker") == ticker and p.get("type") == claim_type),
                None
            )

            # Dedup: only append if consensus changed
            if last_pred:
                last_consensus_eps = last_pred.get("claim", {}).get("consensus_eps")
                if last_consensus_eps == consensus["consensus_eps"] and \
                   last_pred.get("claim", {}).get("consensus_revenue") == consensus["consensus_revenue"]:
                    # Unchanged — skip
                    continue

            # Fetch prices for base data
            try:
                # yfinance imported at module level
                ticker_data = yf.Ticker(ticker)
                base_price = ticker_data.info.get("currentPrice")
                if base_price is None:
                    base_price = ticker_data.info.get("regularMarketPrice", 0.0)
            except Exception:
                base_price = 0.0

            try:
                # yfinance imported at module level
                spy_data = yf.Ticker("SPY")
                base_spy_price = spy_data.info.get("currentPrice")
                if base_spy_price is None:
                    base_spy_price = spy_data.info.get("regularMarketPrice", 0.0)
            except Exception:
                base_spy_price = 0.0

            # Determine direction (bullish/bearish) based on consensus vs model
            direction = "bullish"  # Default; can be refined in future

            # Build inputsHash from consensus fields
            hash_input = json.dumps({
                "consensus_eps": consensus["consensus_eps"],
                "consensus_revenue": consensus["consensus_revenue"],
                "earnings_date": earnings_date,
            }, sort_keys=True)
            inputs_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:16]

            # Create and append claim
            claim = EarningsExpectationClaim(
                consensus_eps=consensus["consensus_eps"],
                consensus_revenue=consensus["consensus_revenue"],
                earnings_date=earnings_date,
            )

            prediction = EarningsExpectation(
                v=1,
                id=pred_id,
                date=today_str,
                ticker=ticker,
                type="earnings_expectation",
                claim=claim,
                direction=direction,
                horizonDays=90,
                basePrice=base_price,
                baseSpyPrice=base_spy_price,
                confidence=None,
                inputsHash=inputs_hash,
                harvestedAt=datetime.now(timezone.utc).isoformat(),
            )

            _append_prediction(prediction.model_dump())
            newly_appended.append(prediction.model_dump())

        except Exception:
            # Silently degrade on any per-ticker error
            continue

    return newly_appended


# ── Grade core logic (Tasks 6-7) ────────────────────────────────────────────

def grade_earnings_expectations() -> list[dict]:
    """Grade earnings expectations by comparing actual results to consensus.

    Main function for B4 Task 6-7. Fetches actual EPS/revenue post-earnings,
    classifies as BEAT/MEET/MISS, and appends to predictions_graded.jsonl.
    Only grades predictions with earnings_date <= today (past-date-only).
    Idempotent: grading same prediction twice produces identical output.

    Returns:
        List of newly appended grade dicts (empty if no predictions to grade).

    Raises:
        No exception raised — gracefully degrades to empty list on missing data.
    """
    if not _load_predictions or not _load_graded or not _append_grade or not _grade_claim:
        return []

    # Load predictions and already-graded records
    try:
        predictions = _load_predictions()
    except Exception:
        predictions = []

    try:
        graded_records = _load_graded()
        graded_pred_ids = {g.get("predictionId") for g in graded_records}
    except Exception:
        graded_records = []
        graded_pred_ids = set()

    newly_graded = []
    today = date.today()

    for pred in predictions:
        # Only grade earnings_expectation types
        if pred.get("type") != "earnings_expectation":
            continue

        pred_id = pred.get("id")
        if pred_id in graded_pred_ids:
            # Already graded — idempotence check: skip
            continue

        # Check if earnings date is in the past
        try:
            earnings_date_str = pred.get("claim", {}).get("earnings_date")
            if not earnings_date_str:
                continue
            earnings_date = date.fromisoformat(earnings_date_str)
            if earnings_date > today:
                # Future earnings — can't grade yet
                continue
        except Exception:
            continue

        ticker = pred.get("ticker")
        if not ticker:
            continue

        try:
            # Fetch actual earnings data from yfinance
            # yfinance imported at module level
            ticker_obj = yf.Ticker(ticker)
            info = ticker_obj.info or {}

            # Get actual EPS and revenue (most recent reported)
            actual_eps = info.get("epsTrailingTwelveMonths")
            actual_revenue = info.get("totalRevenue")

            if actual_eps is None or actual_revenue is None:
                # Can't grade — missing actual data
                continue

            # Get current price for return calculation
            try:
                current_price = ticker_obj.info.get("currentPrice")
                if current_price is None:
                    current_price = ticker_obj.info.get("regularMarketPrice", 0.0)
            except Exception:
                current_price = 0.0

            # Get SPY current price
            try:
                spy_data = yf.Ticker("SPY")
                current_spy_price = spy_data.info.get("currentPrice")
                if current_spy_price is None:
                    current_spy_price = spy_data.info.get("regularMarketPrice", 0.0)
            except Exception:
                current_spy_price = 0.0

            # Extract base prices from prediction
            base_price = pred.get("basePrice", 0.0)
            base_spy_price = pred.get("baseSpyPrice", 0.0)

            # Calculate returns
            ticker_return = (current_price - base_price) / base_price if base_price else 0.0
            spy_return = (current_spy_price - base_spy_price) / base_spy_price if base_spy_price else 0.0
            relative_return = ticker_return - spy_return

            # Get consensus values
            consensus_eps = pred.get("claim", {}).get("consensus_eps", 0.0)
            consensus_revenue = pred.get("claim", {}).get("consensus_revenue", 0.0)

            # Calculate surprise percentages
            eps_surprise_pct = ((actual_eps - consensus_eps) / abs(consensus_eps) * 100) if consensus_eps else 0.0
            revenue_surprise_pct = ((actual_revenue - consensus_revenue) / abs(consensus_revenue) * 100) if consensus_revenue else 0.0

            # Classify: BEAT (>2%), MEET (±2%), MISS (<-2%)
            if eps_surprise_pct > 2.0:
                grade = "BEAT"
            elif eps_surprise_pct < -2.0:
                grade = "MISS"
            else:
                grade = "MEET"

            # Use grade_claim to determine verdict
            verdict = _grade_claim(pred.get("direction", "bullish"), relative_return)

            # Create grade record
            grade_rec = EarningsGrade(
                v=1,
                predictionId=pred_id,
                gradedAt=datetime.now(timezone.utc).isoformat(),
                tickerReturn=ticker_return,
                spyReturn=spy_return,
                relativeReturn=relative_return,
                verdict=verdict,
            )

            _append_grade(grade_rec.model_dump())
            newly_graded.append(grade_rec.model_dump())

        except Exception:
            # Silently degrade on any grading error
            continue

    return newly_graded


# ── Context aggregator (Task 8) ─────────────────────────────────────────────

def get_earnings_context(ticker: str, days_ahead: int = 7) -> dict | None:
    """Get earnings context for daily/weekly brief aggregation.

    Fetches next earnings date, consensus, prior beat rate, portfolio weight,
    and target action for a single ticker.

    Args:
        ticker: Ticker symbol.
        days_ahead: Number of days ahead to consider "upcoming" (default 7).

    Returns:
        Dict with keys {ticker, earnings_date, days_away, consensus_eps,
        consensus_revenue, prior_beat_pct, portfolio_weight, target_action}
        or None if earnings data unavailable.
    """
    from datetime import timedelta

    try:
        # Fetch consensus
        consensus = _fetch_consensus_for_ticker(ticker)
        if not consensus or consensus.get("consensus_eps") is None:
            return None

        earnings_date_str = consensus.get("earnings_date")
        if not earnings_date_str:
            return None

        earnings_date = date.fromisoformat(earnings_date_str)
        days_away = (earnings_date - date.today()).days

        if days_away > days_ahead:
            # Outside window
            return None

        # Load target portfolio
        try:
            from pathlib import Path
            repo_root = Path(__file__).resolve().parents[3]
            target_path = repo_root / "investment_screener/backend/data/theses/target-portfolio.json"
            with open(target_path) as f:
                target_data = json.load(f)
        except Exception:
            target_data = {}

        # Find holding entry
        holding = next(
            (h for h in target_data.get("holdings", []) if h.get("ticker") == ticker),
            None
        )
        portfolio_weight = holding.get("targetWeight", 0.0) if holding else 0.0
        target_action = holding.get("role", "unknown") if holding else "unknown"

        # Calculate prior beat rate from graded predictions
        try:
            from prediction_ledger import load_graded
            graded = load_graded()
            # Filter for this ticker's earnings grades
            ticker_grades = [g for g in graded if ticker in g.get("predictionId", "")]
            if ticker_grades:
                beats = sum(1 for g in ticker_grades if "BEAT" in g.get("predictionId", ""))
                prior_beat_pct = (beats / len(ticker_grades)) * 100 if ticker_grades else 0.0
            else:
                prior_beat_pct = None
        except Exception:
            prior_beat_pct = None

        return {
            "ticker": ticker,
            "earnings_date": earnings_date_str,
            "days_away": days_away,
            "consensus_eps": consensus["consensus_eps"],
            "consensus_revenue": consensus["consensus_revenue"],
            "prior_beat_pct": prior_beat_pct,
            "portfolio_weight": portfolio_weight,
            "target_action": target_action,
        }

    except Exception:
        # Graceful degrade on any error
        return None
