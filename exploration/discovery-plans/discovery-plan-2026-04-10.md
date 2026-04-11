# Discovery Plan — 2026-04-10

## Problem Statement
The InvestmentToolkit app has a table view and heatmap for individual positions, but no single page showing overall portfolio health. The user needs an at-a-glance Portfolio Summary page that answers "How is my portfolio doing this year?" — showing YTD performance, book vs. market value, and totals in both USD and CAD.

## Stakeholders
- **Sole user and decision-maker:** Richard (personal investment tracking across two Questrade accounts)

## Success Criteria
Opening the Portfolio Summary page immediately shows:
- YTD performance from a known starting value to today's total (positions + cash, both accounts)
- Book value vs. market value with unrealized gain/loss
- All key numbers displayed in both USD and CAD
- Dollar and percentage changes in both currencies
- Clean, luxury dark mode styling consistent with the rest of the app — no clicking around required

## Must-Have Requirements
1. YTD performance metric — compare starting portfolio value of $34,126.27 CAD (Jan 1, 2026) to current total market value (sum of all positions x shares + cash across both accounts). Display % change and $ change in both CAD and USD.
2. Book vs. Market value — show total book cost of all current holdings vs. total current market value, with unrealized gain/loss in both currencies.
3. USD/CAD dual currency display — use the Jan 1, 2026 exchange rate (1 USD = 1.3723 CAD) for YTD baseline conversions, and a live exchange rate for current values. Show all key totals and changes in both USD and CAD.

## Constraints and Rules
1. The YTD starting value ($34,126.27 CAD) and Jan 1 exchange rate (1.3723 CAD/USD) are known constants — can be hardcoded or stored in config.
2. Must use existing Questrade sync data already flowing through the backend — no new brokerage API integrations.
3. Must match the luxury dark mode visual style of the existing app.
4. All holdings are US stocks priced in USD; Questrade account values are reported in CAD.
5. Focus on must-haves only — no historical charts, per-account breakdowns, or sector views for now.

## Resolved Decisions
1. **Exchange rate source:** ExchangeRate-API (exchangerate-api.com) — pair endpoint `GET /v6/{key}/pair/USD/CAD`. API key stored in root `.env` as `EXCHANGE_RATE_API_KEY`. Tested and confirmed working 2026-04-10 (1 USD = 1.3824 CAD).
2. **Cash balances:** Use last-synced values from portfolio.json (decided: keep it simple for v1).
3. **Refresh:** Load on navigation (no manual refresh button for now).

## Open Questions
(none remaining)
