# Portfolio Summary Page — Prototype

This prototype adds a Portfolio Summary page showing YTD performance, book vs market value, and USD/CAD dual currency display.

## How to test

From `investment_screener/`:
1. `npm run build -w backend` (rebuild backend with new API endpoint)
2. `npm run dev -w backend` (start backend on port 3001)
3. `npm run dev -w frontend` (start frontend on port 5173)
4. Navigate to http://localhost:5173/portfolio-summary

## Files created/modified

### New files:
- `frontend/src/components/PortfolioSummaryCards.tsx` — headline metric cards
- `frontend/src/components/PortfolioBreakdown.tsx` — detailed USD/CAD breakdown table
- `frontend/src/pages/PortfolioSummaryPage.tsx` — page wrapper

### Modified files:
- `backend/src/index.ts` — added `GET /api/portfolio/summary` endpoint
- `frontend/src/services/api.ts` — added `fetchPortfolioSummary` + `PortfolioSummary` interface
- `frontend/src/App.tsx` — added `/portfolio-summary` route
- `frontend/src/components/Sidebar.tsx` — added nav link
