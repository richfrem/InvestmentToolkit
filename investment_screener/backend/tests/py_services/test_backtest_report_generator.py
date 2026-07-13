"""Task 7: Backtest report generator tests."""
import sys
from pathlib import Path
from datetime import datetime, timedelta

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from backtest_harness import generate_backtest_report  # noqa: E402


def test_backtest_report_aggregates_decisions():
    """Generate backtest report aggregates metrics from commit range."""
    # Use a recent date range (last 30 days)
    end_date = datetime.now().date().isoformat()
    start_date = (datetime.now().date() - timedelta(days=30)).isoformat()

    report = generate_backtest_report(start_date, end_date)

    # Should have required structure
    assert isinstance(report, dict)
    assert "metadata" in report
    assert "rebalances" in report
    assert "summary" in report

    # Metadata should have date range and timestamp
    assert report["metadata"]["start_date"] == start_date
    assert report["metadata"]["end_date"] == end_date
    assert "run_timestamp" in report["metadata"]

    # Summary should have aggregated metrics
    assert "total_rebalances" in report["summary"]
    assert "total_pnl" in report["summary"]
    assert "avg_quality_score" in report["summary"]

    # Rebalances should be a list (possibly empty for short date ranges)
    assert isinstance(report["rebalances"], list)


def test_backtest_report_structure_is_json_serializable():
    """Backtest report can be serialized to JSON without loss."""
    import json

    end_date = datetime.now().date().isoformat()
    start_date = (datetime.now().date() - timedelta(days=30)).isoformat()

    report = generate_backtest_report(start_date, end_date)

    # Should serialize to JSON and back without error
    json_str = json.dumps(report)
    restored = json.loads(json_str)

    assert restored == report


def test_backtest_report_handles_empty_date_range():
    """Backtest report handles date range with no commits gracefully."""
    # Use a future date range
    start_date = (datetime.now().date() + timedelta(days=1)).isoformat()
    end_date = (datetime.now().date() + timedelta(days=10)).isoformat()

    report = generate_backtest_report(start_date, end_date)

    # Should return empty report structure, not error
    assert isinstance(report, dict)
    assert isinstance(report["rebalances"], list)
    assert report["summary"]["total_rebalances"] == 0


def test_backtest_report_summary_fields_are_numeric():
    """Backtest report summary fields are numeric and non-negative."""
    end_date = datetime.now().date().isoformat()
    start_date = (datetime.now().date() - timedelta(days=30)).isoformat()

    report = generate_backtest_report(start_date, end_date)

    summary = report["summary"]
    assert isinstance(summary["total_rebalances"], int)
    assert isinstance(summary["total_pnl"], (int, float))
    assert isinstance(summary["avg_quality_score"], (int, float))

    # Should be non-negative
    assert summary["total_rebalances"] >= 0
    assert summary["avg_quality_score"] >= 0.0


def test_backtest_report_rebalances_have_required_fields():
    """Each rebalance snapshot has required fields."""
    end_date = datetime.now().date().isoformat()
    start_date = (datetime.now().date() - timedelta(days=7)).isoformat()

    report = generate_backtest_report(start_date, end_date)

    for rebalance in report["rebalances"]:
        assert "date" in rebalance
        assert "orders" in rebalance
        assert "realized_pnl" in rebalance
        assert "execution_quality" in rebalance

        # Orders should be a list
        assert isinstance(rebalance["orders"], list)

        # Each order should have required fields
        for order in rebalance["orders"]:
            assert "ticker" in order
            assert "side" in order
            assert "shares" in order
            assert "fill_price" in order
