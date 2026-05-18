"""
Batch quote fetcher — returns bid/ask/price/change for a list of tickers.
Usage: python3 fetch_quotes.py INTC,AMD,NVDA
Output: JSON dict keyed by ticker

Uses yfinance fast_info + 1-min history for accurate real-time prices.
info.get('bid') / info.get('ask') are intentionally NOT used — they return
stale cached values from Yahoo Finance that can be wildly incorrect during
market hours. Instead, bid/ask are derived from the last trade price.
"""
import sys
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import yfinance as yf

def fetch_one(ticker: str) -> dict:
    try:
        t = yf.Ticker(ticker)
        fi = t.fast_info

        # Primary price: fast_info.last_price is real-time during market hours
        price = getattr(fi, 'last_price', None)

        # Fallback: last 1-min bar close
        if not price:
            hist = t.history(period='1d', interval='1m')
            if not hist.empty:
                price = round(float(hist['Close'].iloc[-1]), 4)

        # Fallback: previous close
        if not price:
            price = getattr(fi, 'previous_close', None)

        prev_close = getattr(fi, 'previous_close', None)
        day_change_pct = None
        if price and prev_close and prev_close > 0:
            day_change_pct = round((price - prev_close) / prev_close * 100, 2)

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
