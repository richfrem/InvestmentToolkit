"""Earnings expectation claims — B4 sub-spec for Earnings Intelligence feature.

Purpose:
    Defines Pydantic models for earnings expectation predictions and their
    grading outcomes. Earnings expectations capture consensus analyst forecasts
    at harvest time, then grade how actual earnings compare to those consensus
    targets at outcome time.

Layer:
    Prediction ledger (E3) extension — adds B4 claim type alongside E3's four
    existing types (action_rating, dcf_fair_value, rebalance_order,
    breaker_forecast).

Key Input Dependencies:
    - investment_screener/backend/py_services/prediction_ledger.py (Parent schema)
    - schemas/prediction.schema.json (Defines enum: earnings_expectation)
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


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
