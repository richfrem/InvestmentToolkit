"""
Tests for tv_batch_quotes.py — TradingView-first, yfinance-fallback batch quoting.

BOATS session support was removed (TradingView charts now natively support 24h
quoting) — these tests confirm the single-watchlist path uses the current real
TradingView watchlist name and that boats_session no longer appears anywhere.

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


def test_is_boats_active_removed():
    """BOATS session detection is gone entirely — no longer a real concept."""
    assert not hasattr(tv_batch_quotes, "is_boats_active")


def test_tv_watchlist_prices_opens_tv_full_watchlist_only(monkeypatch):
    """_tv_watchlist_prices() must open exactly one watchlist — 'TV-Full
    Watchlist' — regardless of time of day, with no BOATS fallback branch."""
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


def test_batch_quotes_summary_has_no_boats_session_key(monkeypatch):
    """summary dict must not carry the removed boats_session field."""
    monkeypatch.setattr(tv_batch_quotes, "_tv_watchlist_prices", lambda: {})
    result = tv_batch_quotes.batch_quotes(["ZZZZ_NONEXISTENT_TICKER"])
    assert "boats_session" not in result["summary"]
    assert set(result["summary"].keys()) == {"total", "tradingview", "fallback", "errors"}
