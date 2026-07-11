"""
Batch quote fetcher — returns bid/ask/price/change for a list of tickers.
Usage: python3 fetch_quotes.py INTC,AMD,NVDA
Output: JSON dict keyed by ticker

Price source priority:
  1. TradingView watchlist via CDP (live, includes BOATS extended-hours feed)
  2. yfinance fast_info.last_price (extended-hours aware)
  3. yfinance 1-min history bar
  4. yfinance previous_close

info.get('bid') / info.get('ask') are intentionally NOT used — they return
stale cached values from Yahoo Finance that can be wildly incorrect during
market hours. Instead, bid/ask are derived from the last trade price.

Key Input Dependencies:
    - investment_screener/backend/data/portfolio.json (Queries current yfinance prices)
"""
import sys
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import yfinance as yf

# TV batch price cache — populated once per process invocation
_tv_prices: dict = {}
_tv_loaded: bool = False

def _load_tv_prices(tickers: list[str]) -> None:
    """Populate _tv_prices from TradingView watchlist (best-effort, silent on failure)."""
    global _tv_prices, _tv_loaded
    if _tv_loaded:
        return
    _tv_loaded = True
    try:
        tv_scripts = str(Path(__file__).resolve().parents[3] / "plugins/tradingview/scripts")
        if tv_scripts not in sys.path:
            sys.path.insert(0, tv_scripts)
        from tv_batch_quotes import batch_quotes  # type: ignore[import]
        result = batch_quotes(tickers)
        for sym, q in result.get("quotes", {}).items():
            if q.get("source") == "tradingview":
                _tv_prices[sym] = q
    except Exception:
        pass

def fetch_one(ticker: str) -> dict:
    try:
        # 1. TradingView live price (populated by _load_tv_prices before fetch_one calls)
        tv_q = _tv_prices.get(ticker)
        tv_price = tv_q["price"] if tv_q else None

        t = yf.Ticker(ticker)
        fi = t.fast_info

        # 2. yfinance fast_info.last_price (extended-hours aware)
        yf_price = getattr(fi, 'last_price', None)

        # 3. Fallback: last 1-min bar close
        if not yf_price:
            hist = t.history(period='1d', interval='1m')
            if not hist.empty:
                yf_price = round(float(hist['Close'].iloc[-1]), 4)

        # 4. Fallback: previous close
        if not yf_price:
            yf_price = getattr(fi, 'previous_close', None)

        price = tv_price if tv_price else yf_price

        # Fallback: last 1-min bar close
        if not price:
            hist = t.history(period='1d', interval='1m')
            if not hist.empty:
                price = round(float(hist['Close'].iloc[-1]), 4)

        # Fallback: previous close
        if not price:
            price = getattr(fi, 'previous_close', None)

        prev_close = getattr(fi, 'previous_close', None)
        # Use TV change% when available (accurate for BOATS session)
        if tv_q and tv_q.get("changePercent") is not None:
            day_change_pct = round(tv_q["changePercent"], 2)
        elif price and prev_close and prev_close > 0:
            day_change_pct = round((price - prev_close) / prev_close * 100, 2)
        else:
            day_change_pct = None

        # Derive bid/ask from last price — tight realistic spread
        # Better than yfinance info.bid/ask which are often hours stale
        bid = ask = None
        if price:
            spread = max(0.01, round(price * 0.001, 4))  # ~0.1% spread
            bid = round(price - spread / 2, 4)
            ask = round(price + spread / 2, 4)

        # Market state from fast_info
        market_state = None
        try:
            info = t.info or {}
            market_state = info.get('marketState')
            currency = info.get('currency', 'USD')
            volume = info.get('regularMarketVolume')
            day_change_abs = info.get('regularMarketChange')
        except Exception:
            currency = 'USD'
            volume = None
            day_change_abs = None

        return {
            'ticker': ticker,
            'price': price,
            'bid': bid,
            'ask': ask,
            'bidSize': None,
            'askSize': None,
            'dayChangePct': day_change_pct,
            'dayChangeAbs': day_change_abs,
            'volume': volume,
            'currency': currency,
            'marketState': market_state,
        }
    except Exception as e:
        return {'ticker': ticker, 'error': str(e)}

def main():
    if len(sys.argv) < 2 or not sys.argv[1].strip():
        print(json.dumps({}))
        return

    tickers = [t.strip().upper() for t in sys.argv[1].split(',') if t.strip()]
    if not tickers:
        print(json.dumps({}))
        return

    # Load TV prices once (batch) before parallel yfinance fallback calls
    _load_tv_prices(tickers)

    result = {}
    max_workers = min(len(tickers), 8)

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(fetch_one, t): t for t in tickers}
        for future in as_completed(futures, timeout=20):
            data = future.result()
            result[data['ticker']] = data

    print(json.dumps(result))

if __name__ == '__main__':
    main()
