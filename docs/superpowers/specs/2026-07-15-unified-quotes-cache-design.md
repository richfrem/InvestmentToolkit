# Design Spec: Unified Quotes Cache System

This design specification details the architecture and implementation details for a unified quotes cache system in the InvestmentToolkit workspace. 

---

## 1. Goal & Context
Currently, the front-end pages (Screener, Portfolio Table, Heatmap) trigger slow python subprocesses (`fetch_portfolio_heatmap.py` or `fetch_quotes.py`) on page mount to resolve live pricing details. This creates substantial latency and redundant integrations. 

We will introduce a central price reference catalog, `backend/data/quotes-cache.json`, written only during price refresh actions and read instantly by all pages upon mount.

---

## 2. Architecture & Data Flow

```
[TV CDP / yfinance]
       │ (writes on sync/refresh)
       ▼
[quotes-cache.json]
       │
       ├───────────────────────────────┐
       ▼                               ▼
[GET /api/screener/all-holdings]  [GET /api/portfolio-heatmap]
       │                               │
       ▼                               ▼
[Screener / Portfolio Table]      [Portfolio Heatmap]
```

### File Schema: `quotes-cache.json`
```json
{
  "refreshedAt": "2026-07-15T13:24:08Z",
  "source": "tradingview",
  "quotes": {
    "NVDA": {
      "price": 212.15,
      "changePercent": 3.48
    },
    "INTC": {
      "price": 112.63,
      "changePercent": 6.96
    }
  }
}
```

---

## 3. Proposed Changes

### Component 1: Express Backend Service & Endpoints

#### [MODIFY] [screener.ts](file:///Users/richardfremmerlid/Projects/InvestmentToolkit/investment_screener/backend/src/routes/screener.ts)
* Update `GET /api/screener/all-holdings` to read `quotes-cache.json`.
* Merge the cached `price` and `change_1d` directly into each holdings/watchlist ticker row.

#### [MODIFY] [stock.ts](file:///Users/richardfremmerlid/Projects/InvestmentToolkit/investment_screener/backend/src/routes/stock.ts)
* Update `GET /api/portfolio-heatmap` (or `POST /api/portfolio-heatmap`) to read directly from `quotes-cache.json` and compile the sector hierarchy instead of spawning `fetch_portfolio_heatmap.py` on page load.

### Component 2: Frontend UI Components

#### [MODIFY] [ScreenerTable.tsx](file:///Users/richardfremmerlid/Projects/InvestmentToolkit/investment_screener/frontend/src/components/ScreenerTable.tsx)
* Remove the POST call to `/api/portfolio-heatmap` from `fetchData()`.
* Read pricing, change %, and overall gain/loss metrics directly from `/api/screener/all-holdings` payloads.

#### [MODIFY] [PortfolioTable.tsx](file:///Users/richardfremmerlid/Projects/InvestmentToolkit/investment_screener/frontend/src/components/PortfolioTable.tsx)
* Remove the POST call to `/api/portfolio-heatmap` from `fetchData()`.
* Pull pricing data from the consolidated backend payload.

---

## 4. Verification Plan

### Automated Tests
* Run `npm run build -w backend` to verify backend compiling.
* Run `npm run build -w frontend` to verify frontend compiling.

### Manual Verification
* Navigate to the Screener and Portfolio Table pages. Verify that pricing and performance values populate instantly without invoking Python subprocesses.
* Trigger a manual refresh. Verify that `quotes-cache.json` updates and all three views automatically reload to show the refreshed values.
