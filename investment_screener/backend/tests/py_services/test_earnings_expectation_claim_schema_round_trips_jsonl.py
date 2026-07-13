"""Tests for earnings_expectations.py — B4 earnings expectation models round-trip.

Validates that EarningsExpectation and EarningsGrade Pydantic models
serialize to and deserialize from JSON correctly, preserving all fields
and types as required for predictions.jsonl and predictions_graded.jsonl
integration.
"""
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
PY_SERVICES = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(PY_SERVICES))

from earnings_expectations import (  # noqa: E402
    EarningsExpectation,
    EarningsExpectationClaim,
    EarningsGrade,
    EarningsGradeClaim,
)


class TestEarningsExpectationClaimRoundTrip:
    """EarningsExpectationClaim JSON serialization and deserialization."""

    def test_valid_claim_roundtrip(self):
        """Serialize and deserialize a valid claim, preserving all fields."""
        original = EarningsExpectationClaim(
            consensus_eps=0.52,
            consensus_revenue=9.4e9,
            earnings_date="2026-07-15"
        )
        json_str = original.model_dump_json()
        deserialized = EarningsExpectationClaim.model_validate_json(json_str)
        assert deserialized == original
        assert deserialized.consensus_eps == 0.52
        assert deserialized.consensus_revenue == 9.4e9
        assert deserialized.earnings_date == "2026-07-15"

    def test_claim_preserves_large_numbers(self):
        """Large revenue numbers (9.4e9) round-trip without precision loss."""
        claim = EarningsExpectationClaim(
            consensus_eps=0.52,
            consensus_revenue=9.4e9,
            earnings_date="2026-07-15"
        )
        data = json.loads(claim.model_dump_json())
        assert data["consensus_revenue"] == 9.4e9

    def test_claim_json_structure(self):
        """Serialized claim matches expected JSON structure."""
        claim = EarningsExpectationClaim(
            consensus_eps=0.52,
            consensus_revenue=9.4e9,
            earnings_date="2026-07-15"
        )
        data = json.loads(claim.model_dump_json())
        assert set(data.keys()) == {"consensus_eps", "consensus_revenue", "earnings_date"}
        assert data["consensus_eps"] == 0.52
        assert data["earnings_date"] == "2026-07-15"


class TestEarningsExpectationRoundTrip:
    """EarningsExpectation prediction record round-trip tests."""

    def test_full_prediction_roundtrip(self):
        """Complete EarningsExpectation record round-trips with all fields preserved."""
        original = EarningsExpectation(
            v=1,
            id="NVDA:earnings_expectation:2026-07-12",
            date="2026-07-12",
            ticker="NVDA",
            type="earnings_expectation",
            claim=EarningsExpectationClaim(
                consensus_eps=0.52,
                consensus_revenue=9.4e9,
                earnings_date="2026-07-15"
            ),
            direction="bullish",
            horizonDays=90,
            basePrice=118.50,
            baseSpyPrice=611.20,
            confidence=None,
            inputsHash="abc123def456",
            harvestedAt="2026-07-12T18:30:00Z"
        )
        json_str = original.model_dump_json()
        deserialized = EarningsExpectation.model_validate_json(json_str)
        assert deserialized == original
        assert deserialized.ticker == "NVDA"
        assert deserialized.type == "earnings_expectation"
        assert deserialized.claim.consensus_eps == 0.52

    def test_prediction_required_fields(self):
        """Verify all required fields are enforced."""
        with pytest.raises(ValueError):
            EarningsExpectation(
                # Missing required fields
                id="test",
                ticker="TEST"
            )

    def test_prediction_type_is_immutable(self):
        """Type field must always be 'earnings_expectation'."""
        data = {
            "v": 1,
            "id": "TEST:earnings_expectation:2026-07-12",
            "date": "2026-07-12",
            "ticker": "TEST",
            "type": "earnings_expectation",
            "claim": {
                "consensus_eps": 0.50,
                "consensus_revenue": 1e9,
                "earnings_date": "2026-07-15"
            },
            "direction": "bullish",
            "horizonDays": 90,
            "basePrice": 100.0,
            "baseSpyPrice": 600.0,
            "inputsHash": "hash123",
            "harvestedAt": "2026-07-12T18:30:00Z"
        }
        pred = EarningsExpectation.model_validate(data)
        assert pred.type == "earnings_expectation"

    def test_prediction_confidence_can_be_null(self):
        """Confidence field is optional and defaults to None."""
        pred = EarningsExpectation(
            v=1,
            id="TEST:earnings_expectation:2026-07-12",
            date="2026-07-12",
            ticker="TEST",
            claim=EarningsExpectationClaim(
                consensus_eps=0.50,
                consensus_revenue=1e9,
                earnings_date="2026-07-15"
            ),
            direction="bullish",
            horizonDays=90,
            basePrice=100.0,
            baseSpyPrice=600.0,
            inputsHash="hash123",
            harvestedAt="2026-07-12T18:30:00Z"
        )
        assert pred.confidence is None
        json_str = pred.model_dump_json()
        deserialized = EarningsExpectation.model_validate_json(json_str)
        assert deserialized.confidence is None

    def test_prediction_jsonl_line_serialization(self):
        """Prediction serializes to a single JSON line (no newlines in value)."""
        pred = EarningsExpectation(
            v=1,
            id="NVDA:earnings_expectation:2026-07-12",
            date="2026-07-12",
            ticker="NVDA",
            claim=EarningsExpectationClaim(
                consensus_eps=0.52,
                consensus_revenue=9.4e9,
                earnings_date="2026-07-15"
            ),
            direction="bullish",
            horizonDays=90,
            basePrice=118.50,
            baseSpyPrice=611.20,
            inputsHash="abc123",
            harvestedAt="2026-07-12T18:30:00Z"
        )
        json_line = pred.model_dump_json()
        assert "\n" not in json_line
        # Should deserialize from the line
        parsed = EarningsExpectation.model_validate_json(json_line)
        assert parsed.id == pred.id


class TestEarningsGradeClaimRoundTrip:
    """EarningsGradeClaim enrichment model round-trip tests."""

    def test_grade_claim_roundtrip(self):
        """EarningsGradeClaim serializes and deserializes correctly."""
        original = EarningsGradeClaim(
            prediction_id="NVDA:earnings_expectation:2026-07-12",
            grade_date="2026-07-16",
            grade="BEAT",
            actual_eps=0.56,
            actual_revenue=9.8e9,
            eps_surprise_pct=7.7,
            revenue_surprise_pct=4.3
        )
        json_str = original.model_dump_json()
        deserialized = EarningsGradeClaim.model_validate_json(json_str)
        assert deserialized == original
        assert deserialized.grade == "BEAT"
        assert deserialized.eps_surprise_pct == 7.7

    def test_grade_claim_grades_enum(self):
        """Test all valid grade values: BEAT, MEET, MISS."""
        for grade_val in ["BEAT", "MEET", "MISS"]:
            claim = EarningsGradeClaim(
                prediction_id="TEST:earnings_expectation:2026-07-12",
                grade_date="2026-07-16",
                grade=grade_val,
                actual_eps=0.50,
                actual_revenue=1e9,
                eps_surprise_pct=0.0,
                revenue_surprise_pct=0.0
            )
            assert claim.grade == grade_val


class TestEarningsGradeRoundTrip:
    """EarningsGrade (for predictions_graded.jsonl) round-trip tests."""

    def test_full_grade_roundtrip(self):
        """Complete EarningsGrade record round-trips with all fields."""
        original = EarningsGrade(
            v=1,
            predictionId="NVDA:earnings_expectation:2026-07-12",
            gradedAt="2026-10-10T18:30:00Z",
            tickerReturn=0.045,
            spyReturn=0.012,
            relativeReturn=0.033,
            verdict="correct"
        )
        json_str = original.model_dump_json()
        deserialized = EarningsGrade.model_validate_json(json_str)
        assert deserialized == original
        assert deserialized.verdict == "correct"
        assert deserialized.relativeReturn == 0.033

    def test_grade_verdict_enum(self):
        """Test all valid verdict values: correct, incorrect, inconclusive."""
        for verdict_val in ["correct", "incorrect", "inconclusive"]:
            grade = EarningsGrade(
                v=1,
                predictionId="TEST:earnings_expectation:2026-07-12",
                gradedAt="2026-10-10T18:30:00Z",
                tickerReturn=0.0,
                spyReturn=0.0,
                relativeReturn=0.0,
                verdict=verdict_val
            )
            assert grade.verdict == verdict_val

    def test_grade_v_defaults_to_one(self):
        """Version field defaults to 1."""
        grade = EarningsGrade(
            predictionId="TEST:earnings_expectation:2026-07-12",
            gradedAt="2026-10-10T18:30:00Z",
            tickerReturn=0.0,
            spyReturn=0.0,
            relativeReturn=0.0,
            verdict="correct"
        )
        assert grade.v == 1

    def test_grade_jsonl_line_serialization(self):
        """Grade serializes to a single JSON line."""
        grade = EarningsGrade(
            v=1,
            predictionId="NVDA:earnings_expectation:2026-07-12",
            gradedAt="2026-10-10T18:30:00Z",
            tickerReturn=0.045,
            spyReturn=0.012,
            relativeReturn=0.033,
            verdict="correct"
        )
        json_line = grade.model_dump_json()
        assert "\n" not in json_line
        parsed = EarningsGrade.model_validate_json(json_line)
        assert parsed.predictionId == grade.predictionId


class TestEarningsExpectationSchemaCompliance:
    """Validate that models comply with E3 prediction ledger schema."""

    def test_prediction_schema_fields_match_spec(self):
        """EarningsExpectation includes all required E3 schema fields."""
        pred = EarningsExpectation(
            v=1,
            id="NVDA:earnings_expectation:2026-07-12",
            date="2026-07-12",
            ticker="NVDA",
            claim=EarningsExpectationClaim(
                consensus_eps=0.52,
                consensus_revenue=9.4e9,
                earnings_date="2026-07-15"
            ),
            direction="bullish",
            horizonDays=90,
            basePrice=118.50,
            baseSpyPrice=611.20,
            inputsHash="abc123",
            harvestedAt="2026-07-12T18:30:00Z"
        )
        data = pred.model_dump(exclude_none=True)
        required_fields = {"v", "id", "date", "ticker", "type", "claim",
                          "direction", "horizonDays", "basePrice", "baseSpyPrice",
                          "inputsHash", "harvestedAt"}
        assert required_fields.issubset(set(data.keys()))

    def test_grade_schema_fields_match_spec(self):
        """EarningsGrade includes all required E3 grade fields."""
        grade = EarningsGrade(
            v=1,
            predictionId="NVDA:earnings_expectation:2026-07-12",
            gradedAt="2026-10-10T18:30:00Z",
            tickerReturn=0.045,
            spyReturn=0.012,
            relativeReturn=0.033,
            verdict="correct"
        )
        data = grade.model_dump()
        required_fields = {"v", "predictionId", "gradedAt", "tickerReturn",
                          "spyReturn", "relativeReturn", "verdict"}
        assert set(data.keys()) == required_fields
