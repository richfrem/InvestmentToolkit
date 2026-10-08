"""Purpose: contract tests for the canonical recent-trade context on recommendations.

Layer: Business-logic unit tests. Key Functions: summary, action context and window cases.
Key Input Dependencies: recent_trades.py pure functions; no database or network.
"""
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from recent_trades import RECENT_TRADE_DAYS, summarize_recent_trades, trade_context  # noqa: E402

TODAY = date(2026, 10, 8)


def fill(action: str, shares: float, day: str, account: str = "TFSA", price: float = 210.0) -> dict:
    """One filled trade row in repository column names."""
    return {"action": action, "shares": shares, "trade_date": day, "account_id": account, "price": price}


def test_summary_totals_sells_and_buys_inside_the_window() -> None:
    """Shares are totalled per side and the newest fill is reported."""
    summary = summarize_recent_trades(
        [fill("sell", 2, "2026-10-06"), fill("SELL", 1, "2026-10-06", "RRSP"), fill("buy", 4, "2026-09-30")], TODAY)
    assert summary["window_days"] == RECENT_TRADE_DAYS
    assert (summary["sold_shares"], summary["bought_shares"], summary["count"]) == (3, 4, 3)
    assert summary["last"] == {"date": "2026-10-06", "action": "sell", "shares": 1, "price": 210.0, "account": "RRSP"}


def test_trades_outside_the_window_or_undated_are_ignored() -> None:
    """Old or undated fills never count as recent activity."""
    summary = summarize_recent_trades(
        [fill("sell", 5, "2026-09-01"), fill("sell", 5, None), fill("sell", 5, "not-a-date")], TODAY)
    assert summary == {"window_days": RECENT_TRADE_DAYS, "sold_shares": 0, "bought_shares": 0, "count": 0, "last": None}


def test_no_trades_gives_an_empty_summary_and_no_context() -> None:
    """Nothing recent means nothing to say about the action."""
    summary = summarize_recent_trades([], TODAY)
    assert summary["count"] == 0
    assert trade_context("TRIM", summary) == {"status": "NONE", "note": ""}


@pytest.mark.parametrize("action,trades,status,fragment", [
    ("TRIM", [fill("sell", 3, "2026-10-06")], "ACTED", "Sold 3 shares"),
    ("EXIT", [fill("sell", 3, "2026-10-06")], "ACTED", "Sold 3 shares"),
    ("ACCUMULATE", [fill("buy", 2.5, "2026-10-07")], "ACTED", "Bought 2.5 shares"),
    ("TRIM", [fill("buy", 4, "2026-10-05")], "OPPOSED", "Bought 4 shares"),
    ("ACCUMULATE", [fill("sell", 1, "2026-10-05")], "OPPOSED", "Sold 1 share "),
    ("MAINTAIN", [fill("sell", 1, "2026-10-05")], "RECENT", "Sold 1 share "),
    ("TRIM", [fill("sell", 3, "2026-10-06"), fill("buy", 1, "2026-10-07")], "ACTED", "Sold 3 shares"),
])
def test_context_says_whether_recent_trades_already_follow_the_action(action, trades, status, fragment) -> None:
    """A TRIM that was just trimmed is marked as acted on; the opposite trade is called out."""
    context = trade_context(action, summarize_recent_trades(trades, TODAY))
    assert context["status"] == status
    assert fragment in context["note"]
    assert "2026-10-0" in context["note"]
