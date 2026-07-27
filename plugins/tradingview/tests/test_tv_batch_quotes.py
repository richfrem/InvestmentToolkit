"""
Tests for tv_batch_quotes.py — TradingView-first, yfinance-fallback batch quoting.

Session-aware price selection: TradingView's watchlist row exposes a regular
"last" price/change plus, when the symbol is outside regular trading hours, a
separate extended-hours change% (rendered in the DOM via a "prePostMarket*"
cell) alongside a session label (e.g. "Overnight via BOATS", "Pre-market").
_select_effective_price() picks the right price per the 3-tier priority:
regular hours -> extended hours -> overnight/BOATS -> regular last as a
last-resort default.

Run:
    python3 -m pytest plugins/tradingview/tests/test_tv_batch_quotes.py -v
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "plugins/tradingview/scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import tv_client  # noqa: E402
import tv_batch_quotes  # noqa: E402


def test_select_effective_price_uses_regular_last_when_no_session_label():
    """Regular trading hours: no extended/overnight label present -> use the
    regular last price and change% unchanged."""
    result = tv_batch_quotes._select_effective_price(
        regular_price=206.84, regular_change_pct=-0.55,
        extended_change_pct=None, session_label=None,
    )
    assert result == {"price": 206.84, "changePercent": -0.55, "session": "regular"}


def test_select_effective_price_uses_boats_overnight_when_flagged():
    """Markets closed, TV flags 'Overnight via BOATS' with a separate
    extended change% cell -> effective price must be derived from the
    regular last price adjusted by that extended change%, matching TV's own
    stacked-quote math (187.77 * 1.0408 ~= 195.43, close to TV's displayed
    195.45 which reflects a live tick beyond this snapshot's inputs)."""
    result = tv_batch_quotes._select_effective_price(
        regular_price=187.77, regular_change_pct=-15.02,
        extended_change_pct=4.08, session_label="Overnight via BOATS",
    )
    assert result["session"] == "overnight_boats"
    assert round(result["price"], 2) == 195.43
    assert result["changePercent"] == 4.08


def test_select_effective_price_uses_extended_hours_when_flagged():
    """Pre/post-market session (not overnight/BOATS) also uses the extended
    change% cell to compute the effective price."""
    result = tv_batch_quotes._select_effective_price(
        regular_price=100.0, regular_change_pct=1.0,
        extended_change_pct=-2.0, session_label="Post-market",
    )
    assert result["session"] == "extended_hours"
    assert round(result["price"], 2) == 98.0


def test_select_effective_price_falls_back_to_regular_if_extended_pct_missing():
    """Session label present but no parsable extended change% -> fall back to
    the regular last price rather than guessing."""
    result = tv_batch_quotes._select_effective_price(
        regular_price=50.0, regular_change_pct=0.5,
        extended_change_pct=None, session_label="Overnight via BOATS",
    )
    assert result == {"price": 50.0, "changePercent": 0.5, "session": "regular"}


def test_tv_watchlist_prices_opens_tv_full_watchlist_only(monkeypatch):
    """_tv_watchlist_prices() must open exactly one watchlist — 'TV-Full
    Watchlist' — regardless of time of day."""
    opened_names: list[str] = []

    def fake_tv_call(*args):
        if args[:2] == ("watchlist", "open"):
            opened_names.append(args[2])
            return {"success": True}
        if args[:2] == ("watchlist", "get"):
            return {"success": True, "items": [{"symbol": "NVDA", "price": 206.84, "changePercent": -0.55}]}
        raise AssertionError(f"Unexpected tv_call: {args}")

    monkeypatch.setattr(tv_client, "tv_call", fake_tv_call)
    monkeypatch.setattr(tv_client, "is_tv_running", lambda: True)

    prices = tv_batch_quotes._tv_watchlist_prices()

    assert opened_names == ["TV-Full Watchlist"]
    assert prices["NVDA"]["price"] == 206.84


def test_tv_watchlist_prices_applies_boats_overnight_price(monkeypatch):
    """When the CDP watchlist item carries extended-session fields, the
    resolved price must be the BOATS-adjusted effective price, not the
    frozen regular last price."""

    def fake_tv_call(*args):
        if args[:2] == ("watchlist", "open"):
            return {"success": True}
        if args[:2] == ("watchlist", "get"):
            return {"success": True, "items": [{
                "symbol": "NBIS",
                "price": 187.77,
                "changePercent": -15.02,
                "extendedChangePercent": 4.08,
                "sessionLabel": "Overnight via BOATS",
            }]}
        raise AssertionError(f"Unexpected tv_call: {args}")

    monkeypatch.setattr(tv_client, "tv_call", fake_tv_call)
    monkeypatch.setattr(tv_client, "is_tv_running", lambda: True)

    prices = tv_batch_quotes._tv_watchlist_prices()

    assert round(prices["NBIS"]["price"], 2) == 195.43
    assert prices["NBIS"]["session"] == "overnight_boats"


def test_batch_quotes_summary_keys_unchanged(monkeypatch):
    """summary dict shape is unaffected by session-aware pricing."""
    monkeypatch.setattr(tv_batch_quotes, "_tv_watchlist_prices", lambda: {})
    result = tv_batch_quotes.batch_quotes(["ZZZZ_NONEXISTENT_TICKER"])
    assert set(result["summary"].keys()) == {"total", "tradingview", "fallback", "errors"}