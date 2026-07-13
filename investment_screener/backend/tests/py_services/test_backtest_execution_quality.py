"""Task 4: Execution quality analyzer tests."""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from backtest_harness import (  # noqa: E402
    Order,
    analyze_execution_quality,
    simulate_rebalance,
)


def test_simulate_rebalance_execution_price():
    """Execution quality scores orders against VWAP."""
    # Create orders with specific fill prices
    orders = [
        Order(
            ticker="AAPL",
            side="buy",
            shares=10.0,
            fill_price=150.0,
            executed_at="2026-01-15T10:00:00",
            pnl=None,
        ),
    ]

    prices = {
        "AAPL": {"open": 150.0, "high": 155.0, "low": 145.0, "close": 150.5, "volume": 1000000},
    }

    quality = analyze_execution_quality(orders, prices)

    assert isinstance(quality, dict)
    assert "AAPL" in quality
    # Quality score should be 0.0–1.0
    assert 0.0 <= quality["AAPL"] <= 1.0


def test_analyze_execution_quality_compares_fill_vs_vwap():
    """Quality is calculated as 1.0 - (slippage_bps / 100)."""
    # Perfect fill at VWAP should have quality ~1.0
    # VWAP ~ (high + low + close) / 3 = (160 + 140 + 150) / 3 = 150

    orders = [
        Order(
            ticker="AAPL",
            side="buy",
            shares=10.0,
            fill_price=150.0,
            executed_at="2026-01-15T10:00:00",
            pnl=None,
        ),
    ]

    prices = {
        "AAPL": {"open": 150.0, "high": 160.0, "low": 140.0, "close": 150.0, "volume": 1000000},
    }

    quality = analyze_execution_quality(orders, prices)
    aapl_quality = quality.get("AAPL", 0.0)

    # Fill at VWAP should have high quality (close to 1.0)
    assert aapl_quality >= 0.9


def test_analyze_execution_quality_handles_missing_prices():
    """Quality skips tickers without price data."""
    orders = [
        Order(
            ticker="AAPL",
            side="buy",
            shares=10.0,
            fill_price=150.0,
            executed_at="2026-01-15T10:00:00",
            pnl=None,
        ),
        Order(
            ticker="UNKNOWN",
            side="buy",
            shares=5.0,
            fill_price=100.0,
            executed_at="2026-01-15T10:00:00",
            pnl=None,
        ),
    ]

    prices = {
        "AAPL": {"open": 150.0, "high": 160.0, "low": 140.0, "close": 150.0, "volume": 1000000},
        # UNKNOWN has no price data
    }

    quality = analyze_execution_quality(orders, prices)

    # Should only have quality score for AAPL
    assert "AAPL" in quality
    assert "UNKNOWN" not in quality


def test_analyze_execution_quality_poor_execution_has_low_score():
    """Large slippage results in lower quality score."""
    # Fill at 170 when VWAP is ~150 (200 bps slippage)
    orders = [
        Order(
            ticker="AAPL",
            side="buy",
            shares=10.0,
            fill_price=170.0,
            executed_at="2026-01-15T10:00:00",
            pnl=None,
        ),
    ]

    prices = {
        "AAPL": {"open": 150.0, "high": 160.0, "low": 140.0, "close": 150.0, "volume": 1000000},
    }

    quality = analyze_execution_quality(orders, prices)
    aapl_quality = quality.get("AAPL", 1.0)

    # Should have lower quality due to slippage
    assert aapl_quality < 1.0
