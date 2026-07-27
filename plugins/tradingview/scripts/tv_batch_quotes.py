#!/usr/bin/env python3
"""
tv_batch_quotes.py — Batch price resolver: TradingView first, yfinance fallback.

Price source priority (in order):
  1. TradingView watchlist DOM via CDP — reads the live "TV-Full Watchlist".
     Each row carries a regular last price/change plus, outside regular hours,
     a separate extended-hours change% and a session label (e.g. "Pre-market",
     "Overnight via BOATS"). _select_effective_price() picks which price is
     "current" per a 3-tier priority: regular hours -> extended hours ->
     overnight/BOATS -> regular last as the safe default.
  2. yfinance fast_info.last_price — reflects extended-hours prices when market is closed.
     Used when TradingView is not running (port 9222 unreachable) or ticker not in watchlist.

Usage:
    python3 tv_batch_quotes.py '["CRWV", "NVDA", "INTC"]'

Output (JSON):
    {
      "quotes": {
        "CRWV": { "price": 115.26, "changePercent": -6.07, "source": "tradingview" },
        "NVDA":  { "price": 205.19, "changePercent":  1.23, "source": "tradingview" },
        "INTC":  { "price":  22.14, "changePercent": -0.41, "source": "yfinance" }
      },
      "summary": {
        "total": 3,
        "tradingview": 2,
        "fallback": 1,
        "errors": 0
      }
    }
"""
from __future__ import annotations

import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional

TV_WATCHLIST_NAME = "TV-Full Watchlist"


def _find_scripts_dir() -> Path:
    here = Path(__file__).resolve().parent
    for candidate in [here, *here.parents]:
        if (candidate / "tv_client.py").exists():
            return candidate
        if (candidate / "scripts" / "tv_client.py").exists():
            return candidate / "scripts"
    raise ImportError("tv_client.py not found — check plugin installation or set TV_CDP_DIR.")


def _select_effective_price(
    regular_price: float,
    regular_change_pct: float,
    extended_change_pct: Optional[float],
    session_label: Optional[str],
) -> dict:
    """Pick the current tradable price per the 3-tier session priority.

    TradingView's watchlist row freezes its regular "last" price outside
    regular trading hours and instead surfaces the extended move (pre/post
    market or overnight-via-BOATS) as a separate change% cell alongside a
    session label. The effective price is derived the same way TradingView's
    own stacked quote does: regular_price * (1 + extended_change_pct / 100).

    Args:
        regular_price: Regular-session last price.
        regular_change_pct: Regular-session daily change percent.
        extended_change_pct: Change percent from the extended/overnight cell,
            or None if that cell is absent (i.e. currently regular hours).
        session_label: TradingView's session status text (e.g. "Pre-market",
            "Post-market", "Overnight via BOATS"), or None if absent.

    Returns:
        Dict with price, changePercent, and session ("regular", "extended_hours",
        or "overnight_boats").
    """
    if extended_change_pct is None or not session_label:
        return {"price": regular_price, "changePercent": regular_change_pct, "session": "regular"}

    session = "overnight_boats" if "boats" in session_label.lower() or "overnight" in session_label.lower() \
        else "extended_hours"
    effective_price = regular_price * (1 + extended_change_pct / 100)
    return {"price": effective_price, "changePercent": extended_change_pct, "session": session}


def _tv_watchlist_prices() -> dict[str, dict]:
    """Read live prices from the active TradingView watchlist via CDP.

    Opens TV_WATCHLIST_NAME ("TV-Full Watchlist") and applies session-aware
    price selection per item via _select_effective_price() — regular hours
    use the regular last price; outside regular hours, the extended/BOATS
    price is used instead so stale post-close prices aren't reported as current.

    Returns:
        Dict mapping plain ticker → {price, changePercent, session}.
        Empty dict if TradingView is unreachable or watchlist read fails.
    """
    sys.path.insert(0, str(_find_scripts_dir()))
    from tv_client import tv_call, is_tv_running  # type: ignore[import]

    if not is_tv_running():
        return {}

    try:
        open_res = tv_call("watchlist", "open", TV_WATCHLIST_NAME)
        if not open_res.get("success"):
            return {}

        get_res = tv_call("watchlist", "get")
        if not get_res.get("success"):
            return {}

        prices: dict[str, dict] = {}
        for item in get_res.get("items", []):
            raw_sym = item.get("symbol", "")
            # Strip exchange prefix if present: "NASDAQ:AAPL" → "AAPL"
            sym = raw_sym.split(":")[-1].upper() if ":" in raw_sym else raw_sym.upper()
            price = item.get("price", 0.0)
            change_pct = item.get("changePercent", 0.0)
            if sym and price:
                prices[sym] = _select_effective_price(
                    regular_price=price,
                    regular_change_pct=change_pct,
                    extended_change_pct=item.get("extendedChangePercent"),
                    session_label=item.get("sessionLabel"),
                )
        return prices

    except Exception:
        return {}


def _yf_fast_quote(ticker: str) -> Optional[dict]:
    """Fetch single-ticker quote via yfinance fast_info (extended-hours aware).

    Args:
        ticker: Plain ticker symbol (no exchange prefix).

    Returns:
        Dict with price, changePercent, or None on failure.
    """
    try:
        import yfinance as yf
        yf_ticker = ticker
        if ".U.TO" in ticker:
            yf_ticker = ticker.replace(".U.TO", "-U.TO")
        t = yf.Ticker(yf_ticker)
        fi = t.fast_info
        price = getattr(fi, "last_price", None)
        prev = getattr(fi, "previous_close", None)
        if not price or not prev or prev <= 0:
            return None
        change_pct = round((price - prev) / prev * 100, 4)
        return {"price": round(price, 4), "changePercent": change_pct}
    except Exception:
        return None


def batch_quotes(tickers: list[str]) -> dict:
    """Resolve prices for multiple tickers: TradingView first, yfinance fallback.

    Args:
        tickers: List of plain ticker symbols (no exchange prefix).

    Returns:
        Dict with 'quotes', 'errors', and 'summary' keys.
    """
    tv_prices = _tv_watchlist_prices()

    quotes: dict[str, dict] = {}
    errors: dict[str, str] = {}
    tv_count = 0
    yf_tickers: list[str] = []

    for t in tickers:
        if t in tv_prices:
            quotes[t] = {**tv_prices[t], "source": "tradingview"}
            tv_count += 1
        else:
            yf_tickers.append(t)

    # Parallel yfinance fallback for tickers not in TV watchlist
    if yf_tickers:
        with ThreadPoolExecutor(max_workers=min(len(yf_tickers), 8)) as pool:
            futures = {pool.submit(_yf_fast_quote, t): t for t in yf_tickers}
            for future in as_completed(futures, timeout=30):
                sym = futures[future]
                try:
                    result = future.result()
                    if result:
                        quotes[sym] = {**result, "source": "yfinance"}
                    else:
                        errors[sym] = "no price data"
                except Exception as e:
                    errors[sym] = str(e)

    return {
        "quotes": quotes,
        "errors": errors,
        "summary": {
            "total": len(tickers),
            "tradingview": tv_count,
            "fallback": len(quotes) - tv_count,
            "errors": len(errors),
        },
    }


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Batch price resolver — TV first, yfinance fallback.")
    parser.add_argument("tickers", help='JSON array e.g. \'["NVDA","AAPL"]\'')
    args = parser.parse_args()
    try:
        tickers = json.loads(args.tickers)
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"Invalid JSON: {e}"}), file=sys.stderr)
        sys.exit(1)
    if not isinstance(tickers, list):
        print(json.dumps({"error": "Input must be a JSON array"}), file=sys.stderr)
        sys.exit(1)
    print(json.dumps(batch_quotes(tickers), indent=2))


if __name__ == "__main__":
    main()
