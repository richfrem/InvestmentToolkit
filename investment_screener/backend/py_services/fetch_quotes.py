"""
Batch quote fetcher — returns bid/ask/price/change for a list of tickers.
Usage: python3 fetch_quotes.py INTC,AMD,NVDA
Output: JSON dict keyed by ticker
"""
import sys
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import yfinance as yf

def fetch_one(ticker: str) -> dict:
    try:
        t = yf.Ticker(ticker)
        info = t.info or {}
        price = (
            info.get('regularMarketPrice') or
            info.get('currentPrice') or
            info.get('navPrice') or
            info.get('previousClose')
        )
        prev_close = info.get('regularMarketPreviousClose') or info.get('previousClose')
        day_change_pct = None
        if price and prev_close and prev_close > 0:
            day_change_pct = round((price - prev_close) / prev_close * 100, 2)
        return {
            'ticker': ticker,
            'price': price,
            'bid': info.get('bid'),
            'ask': info.get('ask'),
            'bidSize': info.get('bidSize'),
            'askSize': info.get('askSize'),
            'dayChangePct': day_change_pct,
            'dayChangeAbs': info.get('regularMarketChange'),
            'volume': info.get('regularMarketVolume'),
            'currency': info.get('currency', 'USD'),
            'marketState': info.get('marketState'),
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
