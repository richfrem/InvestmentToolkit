# Roadmap

## V1: Manual Holdings Fetch to Local .ts
- Manual OAuth2 auth with refresh token flow.
- Fetch holdings on button click.
- Display in table.
- Store in backend/src/data/currentHoldings.ts.
- Automated refresh token management: .env updated after each token exchange.
- API error handling and user feedback for token issues.

## V2: Spreadsheet Integration
- Save holdings to portfolio.xlsx using xlsx library.
- Add /api/update-spreadsheet endpoint.
- UI for spreadsheet export and download.

## V3: Rebalancing Calculator
- Add UI for rebalancing logic (no trades).
- Integrate with holdings data.

## V4: Charts and Advanced UI
- Integrate charts for holdings visualization.
- Dashboard for portfolio analytics.

## V5: Token Management & Security Enhancements
- UI for viewing and managing refresh token status.
- Enhanced error handling and logging.
- Option for secure secrets storage (beyond .env).

## V6: Local Caching & Performance
- Integrate SQLite for local caching of holdings and API responses.
- Optimize data fetch and UI responsiveness.