"""Prices for a refresh come from TradingView quotes only: yfinance is never a price source."""
import sys
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))
sys.path.insert(0, str(REPO_ROOT / "plugins/tradingview/scripts"))

import fetch_portfolio_heatmap as heatmap  # noqa: E402
import tv_batch_quotes  # noqa: E402

INFO = {"shortName": "Name", "sector": "Technology", "industry": "Software", "currentPrice": 111.0,
        "regularMarketPrice": 111.0, "_fastLastPrice": 111.0}


def _run(items, tv_prices, **kwargs):
    """Run fetch_portfolio_data with yfinance metadata stubbed (carrying a different price) and TV quotes given."""
    def fake_batch(tickers, allow_fallback=True):
        quotes = {t: {"price": p, "changePercent": 1.5, "source": "tradingview"} for t, p in tv_prices.items() if t in tickers}
        return {"quotes": quotes, "errors": {}, "summary": {}}

    with patch.object(heatmap, "prefetch_info", side_effect=lambda syms, bust_cache=False: {s: dict(INFO) for s in syms}), \
         patch.object(heatmap, "prefetch_history"), \
         patch.object(heatmap.HistoricalPriceStore, "calc_changes", return_value={}), \
         patch.object(tv_batch_quotes, "batch_quotes", side_effect=fake_batch) as batch:
        result = heatmap.fetch_portfolio_data(items, bust_cache=True, **kwargs)
    return result, batch


def test_tradingview_only_uses_the_tradingview_price_not_the_yfinance_one():
    result, batch = _run([{"symbol": "NVDA", "shares": 2}], {"NVDA": 200.0}, tradingview_only=True)
    stock = result["stocks"][0]
    assert stock["price"] == 200.0 and stock["change_pct"] == 1.5
    assert result["price_source"] == "tradingview" and result["missing_prices"] == []
    assert batch.call_args.kwargs["allow_fallback"] is False


def test_a_symbol_tradingview_cannot_quote_is_missing_not_priced_from_yfinance_or_the_stored_price():
    result, _ = _run([{"symbol": "NVDA", "shares": 2}, {"symbol": "ZZZZ", "shares": 1, "price": 42.0}],
                     {"NVDA": 200.0}, tradingview_only=True)
    zzzz = next(s for s in result["stocks"] if s["symbol"] == "ZZZZ")
    assert zzzz["price"] == 0 and zzzz["error"] == "no TradingView quote"
    assert result["missing_prices"] == ["ZZZZ"] and result["price_source"] == "tradingview_partial"
    assert result["total_value"] == 400.0


def test_the_default_mode_is_unchanged_and_still_allows_the_fallback():
    result, batch = _run([{"symbol": "NVDA", "shares": 2}], {"NVDA": 200.0})
    assert batch.call_args.kwargs["allow_fallback"] is True
    assert "missing_prices" not in result


def test_batch_quotes_without_fallback_never_calls_yfinance():
    with patch.object(tv_batch_quotes, "_tv_watchlist_prices", return_value={"NVDA": {"price": 200.0, "changePercent": 1.0, "session": "regular"}}), \
         patch.object(tv_batch_quotes, "_yf_fast_quote") as yf_quote:
        result = tv_batch_quotes.batch_quotes(["NVDA", "ZZZZ"], allow_fallback=False)
    yf_quote.assert_not_called()
    assert result["quotes"]["NVDA"]["source"] == "tradingview"
    assert result["errors"] == {"ZZZZ": "no TradingView quote"}
    assert result["summary"]["fallback"] == 0 and result["summary"]["errors"] == 1


def test_batch_quotes_default_still_falls_back():
    with patch.object(tv_batch_quotes, "_tv_watchlist_prices", return_value={}), \
         patch.object(tv_batch_quotes, "_yf_fast_quote", return_value={"price": 9.0, "changePercent": 0.1}) as yf_quote:
        result = tv_batch_quotes.batch_quotes(["ZZZZ"])
    yf_quote.assert_called_once()
    assert result["quotes"]["ZZZZ"]["source"] == "yfinance"
