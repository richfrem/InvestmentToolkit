"""Task 3: Rebalance order simulator tests."""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from backtest_harness import simulate_rebalance  # noqa: E402


def test_simulate_rebalance_calculates_orders():
    """Simulate rebalance generates buy/sell orders for weight changes."""
    targets_before = {"AAPL": 0.3, "MSFT": 0.5, "GOOGL": 0.2}
    targets_after = {"AAPL": 0.4, "MSFT": 0.4, "GOOGL": 0.2}

    prices = {
        "AAPL": {"open": 150.0, "high": 155.0, "low": 145.0, "close": 152.0, "volume": 1000000},
        "MSFT": {"open": 300.0, "high": 310.0, "low": 290.0, "close": 305.0, "volume": 500000},
        "GOOGL": {"open": 140.0, "high": 145.0, "low": 135.0, "close": 142.0, "volume": 800000},
    }

    orders, total_pnl = simulate_rebalance(targets_before, targets_after, prices)

    # Should have orders for AAPL (+0.1) and MSFT (-0.1)
    assert len(orders) >= 2

    # Check order structure
    for order in orders:
        assert hasattr(order, "ticker")
        assert hasattr(order, "side")
        assert hasattr(order, "shares")
        assert hasattr(order, "fill_price")
        assert order.side in ("buy", "sell")
        assert order.shares > 0
        assert order.fill_price > 0


def test_simulate_rebalance_uses_mid_price_for_execution():
    """Rebalance uses (high + low) / 2 as fill price."""
    targets_before = {"AAPL": 0.5}
    targets_after = {"AAPL": 0.3}  # Sell 0.2

    high, low = 160.0, 140.0
    prices = {
        "AAPL": {"open": 150.0, "high": high, "low": low, "close": 152.0, "volume": 1000000},
    }

    orders, _ = simulate_rebalance(targets_before, targets_after, prices)

    if orders:
        sell_order = [o for o in orders if o.side == "sell"][0]
        mid_price = (high + low) / 2.0
        assert sell_order.fill_price == pytest.approx(mid_price, rel=0.01)


def test_simulate_rebalance_calculates_pnl_on_sells():
    """Rebalance calculates P&L when entry prices provided."""
    targets_before = {"AAPL": 0.5}
    targets_after = {"AAPL": 0.2}  # Sell 0.3

    prices = {
        "AAPL": {"open": 150.0, "high": 160.0, "low": 140.0, "close": 152.0, "volume": 1000000},
    }
    entry_prices = {"AAPL": 120.0}  # Bought at 120, selling at mid-price (150)

    orders, total_pnl = simulate_rebalance(targets_before, targets_after, prices, entry_prices)

    # Expect positive P&L since selling above entry price
    if orders:
        sell_order = [o for o in orders if o.side == "sell"][0]
        assert sell_order.pnl is not None
        # Expect profit: (150 - 120) * 0.3 = 9.0
        assert sell_order.pnl > 0


def test_simulate_rebalance_skips_missing_prices():
    """Rebalance skips tickers without price data gracefully."""
    targets_before = {"AAPL": 0.5, "UNKNOWN": 0.5}
    targets_after = {"AAPL": 0.3, "UNKNOWN": 0.7}

    prices = {
        "AAPL": {"open": 150.0, "high": 160.0, "low": 140.0, "close": 152.0, "volume": 1000000},
        # UNKNOWN has no price data
    }

    orders, total_pnl = simulate_rebalance(targets_before, targets_after, prices)

    # Should only have order for AAPL (UNKNOWN is skipped)
    assert all(o.ticker == "AAPL" for o in orders)
