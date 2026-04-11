# Backend API Endpoint — /api/portfolio/summary

Added to `investment_screener/backend/src/index.ts`.

## Route
`GET /api/portfolio/summary`

## Logic
- Reads portfolio.json, sums market value (shares x price) and book value (shares x book_price) in USD
- Fetches live USD/CAD rate from ExchangeRate-API pair endpoint
- Computes YTD change from $34,126.27 CAD starting value (Jan 1 rate: 1.3723)
- Computes unrealized gain/loss (book vs market)
- Returns all values in both USD and CAD

## Response shape
```json
{
  "positionCount": 27,
  "totalMarketValueUSD": 25824.50,
  "totalMarketValueCAD": 35699.85,
  "totalBookValueUSD": 27493.10,
  "totalBookValueCAD": 38006.37,
  "ytdStartValueCAD": 34126.27,
  "ytdStartValueUSD": 24868.58,
  "ytdChangeCAD": 1573.58,
  "ytdChangePctCAD": 4.61,
  "ytdChangeUSD": 955.92,
  "ytdChangePctUSD": 3.84,
  "unrealizedGainUSD": -1668.60,
  "unrealizedGainPctUSD": -6.07,
  "unrealizedGainCAD": -2306.52,
  "unrealizedGainPctCAD": -6.07,
  "liveUsdCadRate": 1.3824,
  "jan1UsdCadRate": 1.3723,
  "lastUpdated": "2026-04-10T..."
}
```

## Status: COMPLETE
