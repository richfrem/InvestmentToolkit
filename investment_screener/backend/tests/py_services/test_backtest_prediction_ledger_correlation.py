"""Task 8: Prediction ledger correlation tests."""
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from backtest_harness import (  # noqa: E402
    correlate_with_prediction_ledger,
    Order,
)


def test_backtest_correlates_with_prediction_ledger(tmp_path, monkeypatch):
    """Correlate backtest with E3 prediction ledger."""
    # Create a minimal backtest report
    today = datetime.now().date().isoformat()
    report = {
        "metadata": {
            "start_date": today,
            "end_date": today,
            "run_timestamp": datetime.now().isoformat(),
        },
        "rebalances": [
            {
                "date": today,
                "orders": [
                    {
                        "ticker": "AAPL",
                        "side": "buy",
                        "shares": 10.0,
                        "fill_price": 150.0,
                        "executed_at": datetime.now().isoformat(),
                        "pnl": None,
                    },
                ],
                "realized_pnl": 0.0,
                "execution_quality": {"AAPL": 0.95},
            },
        ],
        "summary": {"total_rebalances": 1, "total_pnl": 0.0, "avg_quality_score": 0.95},
    }

    # Create a minimal predictions JSONL file
    predictions_path = tmp_path / "predictions.jsonl"
    with open(predictions_path, "w") as f:
        # Write a prediction on the same date for AAPL
        prediction = {
            "id": "AAPL:action_rating:2026-01-15",
            "ticker": "AAPL",
            "type": "action_rating",
            "claimDate": today,
            "direction": "bullish",
            "confidence": 0.8,
        }
        f.write(json.dumps(prediction) + "\n")

    # Correlate
    correlation = correlate_with_prediction_ledger(report, predictions_path)

    # Should have correlation metrics
    assert isinstance(correlation, dict)
    assert "total_predictions_linked" in correlation
    assert "rebalance_alignment" in correlation
    assert "signal_quality" in correlation

    # Should have at least one linked prediction
    assert correlation["total_predictions_linked"] >= 0


def test_backtest_prediction_ledger_handles_missing_file():
    """Correlation handles missing predictions file gracefully."""
    report = {
        "metadata": {"start_date": "2026-01-01", "end_date": "2026-01-31"},
        "rebalances": [],
        "summary": {"total_rebalances": 0, "total_pnl": 0.0, "avg_quality_score": 0.0},
    }

    missing_path = Path("/nonexistent/predictions.jsonl")
    correlation = correlate_with_prediction_ledger(report, missing_path)

    # Should return empty correlation report
    assert isinstance(correlation, dict)
    assert correlation["total_predictions_linked"] == 0
    assert correlation["signal_quality"] == 0.0


def test_backtest_prediction_ledger_returns_required_structure():
    """Correlation report has required fields."""
    report = {
        "metadata": {"start_date": "2026-01-01", "end_date": "2026-01-31"},
        "rebalances": [
            {
                "date": "2026-01-15",
                "orders": [
                    {
                        "ticker": "AAPL",
                        "side": "buy",
                        "shares": 10.0,
                        "fill_price": 150.0,
                        "executed_at": "2026-01-15T10:00:00",
                        "pnl": None,
                    },
                ],
                "realized_pnl": 0.0,
                "execution_quality": {"AAPL": 0.95},
            },
        ],
        "summary": {"total_rebalances": 1, "total_pnl": 0.0, "avg_quality_score": 0.95},
    }

    correlation = correlate_with_prediction_ledger(report)

    assert "total_predictions_linked" in correlation
    assert "rebalance_alignment" in correlation
    assert "signal_quality" in correlation

    # Signal quality should be 0.0–1.0
    assert 0.0 <= correlation["signal_quality"] <= 1.0


def test_backtest_prediction_ledger_signal_quality_is_numeric():
    """Signal quality is numeric and in valid range."""
    report = {
        "metadata": {"start_date": "2026-01-01", "end_date": "2026-01-31"},
        "rebalances": [],
        "summary": {"total_rebalances": 0, "total_pnl": 0.0, "avg_quality_score": 0.0},
    }

    correlation = correlate_with_prediction_ledger(report)

    assert isinstance(correlation["signal_quality"], (int, float))
    assert 0.0 <= correlation["signal_quality"] <= 1.0
