"""Task 9: Integration into weekly_review and JSON round-trip tests."""
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from backtest_harness import (  # noqa: E402
    generate_backtest_report,
    Order,
)


def test_backtest_report_rounds_trips_json():
    """Backtest report serializes to JSON and deserializes without loss."""
    end_date = datetime.now().date().isoformat()
    start_date = (datetime.now().date() - timedelta(days=7)).isoformat()

    # Generate report
    report = generate_backtest_report(start_date, end_date)

    # Serialize to JSON string
    json_str = json.dumps(report)

    # Deserialize back to dict
    restored = json.loads(json_str)

    # Should be identical
    assert restored == report

    # All rebalances should round-trip
    for original_rebal, restored_rebal in zip(
        report.get("rebalances", []),
        restored.get("rebalances", []),
    ):
        assert original_rebal == restored_rebal


def test_backtest_order_serializes_to_json():
    """Order objects serialize via dataclass to JSON."""
    order = Order(
        ticker="AAPL",
        side="buy",
        shares=10.0,
        fill_price=150.0,
        executed_at=datetime.now().isoformat(),
        pnl=None,
    )

    # Convert to dict (as if serialized)
    from dataclasses import asdict

    order_dict = asdict(order)

    # Serialize to JSON
    json_str = json.dumps(order_dict)

    # Deserialize back
    restored_dict = json.loads(json_str)

    assert restored_dict == order_dict
    assert restored_dict["ticker"] == "AAPL"
    assert restored_dict["side"] == "buy"
    assert restored_dict["shares"] == 10.0


def test_backtest_report_contains_valid_json_in_counterfactuals():
    """Counterfactuals in report are JSON-serializable."""
    end_date = datetime.now().date().isoformat()
    start_date = (datetime.now().date() - timedelta(days=7)).isoformat()

    params = {"counterfactuals_enabled": True}
    report = generate_backtest_report(start_date, end_date, params)

    # Try to serialize entire report including counterfactuals
    json_str = json.dumps(report)
    restored = json.loads(json_str)

    # Counterfactuals should be present if rebalances exist
    if restored["rebalances"]:
        for rebalance in restored["rebalances"]:
            if "counterfactuals" in rebalance:
                assert "timing" in rebalance["counterfactuals"]
                assert "threshold" in rebalance["counterfactuals"]


def test_backtest_report_metadata_contains_iso_dates():
    """Backtest report uses ISO date format (YYYY-MM-DD)."""
    end_date = datetime.now().date().isoformat()
    start_date = (datetime.now().date() - timedelta(days=7)).isoformat()

    report = generate_backtest_report(start_date, end_date)

    # Dates should be in ISO format
    assert report["metadata"]["start_date"] == start_date
    assert report["metadata"]["end_date"] == end_date

    # run_timestamp should be ISO datetime
    assert "T" in report["metadata"]["run_timestamp"]


def test_backtest_json_preserves_numeric_precision():
    """JSON round-trip preserves numeric precision."""
    report = {
        "metadata": {"start_date": "2026-01-01", "end_date": "2026-01-31"},
        "rebalances": [
            {
                "date": "2026-01-15",
                "orders": [
                    {
                        "ticker": "AAPL",
                        "side": "sell",
                        "shares": 10.5,
                        "fill_price": 150.25,
                        "executed_at": "2026-01-15T10:00:00",
                        "pnl": 52.625,
                    },
                ],
                "realized_pnl": 52.625,
                "execution_quality": {"AAPL": 0.987654},
            },
        ],
        "summary": {"total_rebalances": 1, "total_pnl": 52.625, "avg_quality_score": 0.987654},
    }

    # Serialize and deserialize
    json_str = json.dumps(report)
    restored = json.loads(json_str)

    # Numeric precision should be preserved
    assert restored["rebalances"][0]["orders"][0]["fill_price"] == 150.25
    assert restored["rebalances"][0]["realized_pnl"] == 52.625
    assert restored["summary"]["avg_quality_score"] == pytest.approx(0.987654, rel=1e-6)
