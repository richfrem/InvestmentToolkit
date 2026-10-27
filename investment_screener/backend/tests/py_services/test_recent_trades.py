"""Purpose: contract tests for the canonical recent-trade context on recommendations.

Layer: Business-logic unit tests. Key Functions: summary, action context and window cases.
Key Input Dependencies: recent_trades.py pure functions; no database or network.
"""
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if (p / "investment_screener").is_dir()) / "investment_screener/backend/py_services"))
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


# ── A call may not reverse what the owner just did (flip_hold_note) ─────────────────────────
from datetime import date as _date  # noqa: E402

from recent_trades import FLIP_HOLD_DAYS, flip_hold_note  # noqa: E402

_TODAY = _date(2026, 10, 17)
_BUY = [{"action": "buy", "shares": 3, "trade_date": "2026-10-12T15:00:00-04:00"}]
_SELL = [{"action": "sell", "shares": 43, "trade_date": "2026-10-15T11:02:08-04:00"}]


def test_trim_or_exit_is_held_back_after_a_recent_buy():
    for action in ("TRIM", "EXIT"):
        out = flip_hold_note(action, _BUY, _TODAY)
        assert out["held"] is True and "Bought on 2026-10-12" in out["note"]


def test_accumulate_or_initiate_is_held_back_after_a_recent_sale():
    for action in ("ACCUMULATE", "INITIATE"):
        out = flip_hold_note(action, _SELL, _TODAY)
        assert out["held"] is True and "Sold on 2026-10-15" in out["note"]


def test_calls_that_follow_the_trade_are_untouched():
    assert flip_hold_note("ACCUMULATE", _BUY, _TODAY) is None
    assert flip_hold_note("TRIM", _SELL, _TODAY) is None
    assert flip_hold_note("MAINTAIN", _BUY, _TODAY) is None


def test_hold_expires_after_the_window():
    old = [{"action": "buy", "shares": 1, "trade_date": "2026-09-01"}]
    assert (_TODAY - _date(2026, 9, 1)).days > FLIP_HOLD_DAYS
    assert flip_hold_note("TRIM", old, _TODAY) is None


def test_new_facts_lift_the_hold_and_say_so():
    breaker = flip_hold_note("EXIT", _BUY, _TODAY, breaker_triggered=True)
    assert breaker["held"] is False and "thesis breaker triggered" in breaker["note"]
    reval = flip_hold_note("TRIM", _BUY, _TODAY, new_evidence_date="2026-10-16T09:00:00+00:00")
    assert reval["held"] is False and "2026-10-16" in reval["note"]


def test_valuation_dated_before_the_trade_does_not_lift_the_hold():
    out = flip_hold_note("TRIM", _BUY, _TODAY, new_evidence_date="2026-10-08T19:35:43+00:00")
    assert out["held"] is True


def test_breaker_does_not_lift_a_hold_on_buying_back_after_a_sale():
    assert flip_hold_note("INITIATE", _SELL, _TODAY, breaker_triggered=True)["held"] is True
