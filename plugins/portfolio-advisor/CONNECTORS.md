# Connectors: portfolio-advisor

This plugin operates in **Supercharged** mode: strategic analysis, drift classification and valuation always work offline from pasted data; live portfolio data and persistence need the backend and the data fetcher.

## Tool Connector Matrix

| Category | Examples | Used By | Required? |
|----------|----------|---------|-----------|
| `~~portfolio-api` | `GET /api/theses/:id/health`, Portfolio DB | `setting-portfolio-targets` (portfolio-health mode) | Supercharged |
| `~~thesis-store` | `GET /api/theses`, thesis records in `domain_model.sqlite` | `setting-portfolio-targets` | Supercharged |
| `~~valuation-source` | `valuing-investments` output, `projection_version` rows | Conflict detection in `setting-portfolio-targets` | Optional |
| `~~financial-data-fetcher` | `fetch_financials.py` (yfinance), Alpha Vantage API, Polygon.io | `valuing-investments` (update-analysis, research-sweep) | Supercharged |
| `~~projection-store` | `persist_valuation.py`, SQLite | `valuing-investments` (update-analysis) | Supercharged |
| `~~research-report-store` | Research ledger (`intelligence.sqlite`) through `persist_research.py` | `valuing-investments` | Supercharged |
| `~~backend-health-check` | `curl http://localhost:3001/api/health` | `valuing-investments`, `setting-portfolio-targets` | Supercharged |

## Degradation Contract

| Mode | Condition | Behaviour |
|------|-----------|-----------|
| **Full** | Backend running and `~~financial-data-fetcher` available | Full autonomous pipeline: fetch, analyse, persist, report |
| **Standalone** | No backend or no fetcher | The agent asks the user to paste portfolio, thesis or raw financial data as JSON; analysis and Q&A still work; persistence is skipped with an explicit notice |

> **Note**: the `~~financial-data-fetcher` and `~~projection-store` connectors are bound to the Investment Screener's Python services in `investment_screener/backend/py_services/`. They are shared infrastructure: do not duplicate those scripts into a skill.
