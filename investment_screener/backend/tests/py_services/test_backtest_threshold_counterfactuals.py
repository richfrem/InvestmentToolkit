"""Task 6: Threshold counterfactual generator tests."""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from backtest_harness import (  # noqa: E402
    Order,
    generate_threshold_counterfactuals,
)


def test_generate_counterfactuals_threshold_variation():
    """Generate threshold counterfactuals with ±5% weight drift."""
    before_weights = {"AAPL": 0.3, "MSFT": 0.5}

    orders = [
        Order(
            ticker="AAPL",
            side="sell",
            shares=5.0,
            fill_price=150.0,
            executed_at="2026-01-15T10:00:00",
            pnl=10.0,
        ),
        Order(
            ticker="MSFT",
            side="buy",
            shares=3.0,
            fill_price=300.0,
            executed_at="2026-01-15T10:00:00",
            pnl=None,
        ),
    ]

    prices = {
        "AAPL": {"open": 150.0, "high": 155.0, "low": 145.0, "close": 152.0, "volume": 1000000},
        "MSFT": {"open": 300.0, "high": 310.0, "low": 290.0, "close": 305.0, "volume": 500000},
    }

    counterfactuals = generate_threshold_counterfactuals(before_weights, orders, prices)

    assert isinstance(counterfactuals, dict)
    assert "minus_5pct" in counterfactuals
    assert "plus_5pct" in counterfactuals


def test_generate_threshold_counterfactuals_calculates_alt_pnl():
    """Threshold counterfactuals recalculate P&L with drifted share counts."""
    before_weights = {"AAPL": 0.3}

    orders = [
        Order(
            ticker="AAPL",
            side="sell",
            shares=5.0,
            fill_price=150.0,
            executed_at="2026-01-15T10:00:00",
            pnl=10.0,  # Base P&L: (150 - 140) * 5 = 50
        ),
    ]

    prices = {
        "AAPL": {"open": 150.0, "high": 155.0, "low": 145.0, "close": 152.0, "volume": 1000000},
    }

    counterfactuals = generate_threshold_counterfactuals(before_weights, orders, prices)

    # Should have alternative P&L calculations
    assert "minus_5pct" in counterfactuals
    assert "plus_5pct" in counterfactuals


def test_generate_threshold_counterfactuals_handles_missing_prices():
    """Threshold counterfactuals skip tickers without price data."""
    before_weights = {"AAPL": 0.3, "UNKNOWN": 0.2}

    orders = [
        Order(
            ticker="AAPL",
            side="sell",
            shares=5.0,
            fill_price=150.0,
            executed_at="2026-01-15T10:00:00",
            pnl=10.0,
        ),
        Order(
            ticker="UNKNOWN",
            side="sell",
            shares=2.0,
            fill_price=100.0,
            executed_at="2026-01-15T10:00:00",
            pnl=5.0,
        ),
    ]

    prices = {
        "AAPL": {"open": 150.0, "high": 155.0, "low": 145.0, "close": 152.0, "volume": 1000000},
        # UNKNOWN has no price data
    }

    counterfactuals = generate_threshold_counterfactuals(before_weights, orders, prices)

    # Should only calculate alternative P&L for AAPL
    # (UNKNOWN is skipped due to missing prices)
    assert isinstance(counterfactuals["minus_5pct"], dict)
    assert isinstance(counterfactuals["plus_5pct"], dict)


def test_generate_threshold_counterfactuals_only_affects_sells():
    """Threshold counterfactuals only calculate P&L for sell orders."""
    before_weights = {"AAPL": 0.3}

    orders = [
        Order(
            ticker="AAPL",
            side="buy",
            shares=5.0,
            fill_price=150.0,
            executed_at="2026-01-15T10:00:00",
            pnl=None,
        ),
    ]

    prices = {
        "AAPL": {"open": 150.0, "high": 155.0, "low": 145.0, "close": 152.0, "volume": 1000000},
    }

    counterfactuals = generate_threshold_counterfactuals(before_weights, orders, prices)

    # Should have empty dicts (buy orders don't contribute P&L)
    assert counterfactuals["minus_5pct"] == {}
    assert counterfactuals["plus_5pct"] == {}
