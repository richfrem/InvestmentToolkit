# Connectors — stock-valuation

This plugin operates in **Supercharged** mode: it works standalone (with manual data input) but gains full capability when the backend data pipeline is connected.

## Tool Connector Matrix

| Category | Examples | Used By | Required? |
|----------|----------|---------|-----------|
| `~~financial-data-fetcher` | `fetch_financials.py` (yfinance), Alpha Vantage API, Polygon.io | `update-stock-analysis` SKILL (renamed 2026-08-28 from `stock_valuation`) | Supercharged |
| `~~projection-store` | `persist_projection.py`, SQLite, PostgreSQL | `update-stock-analysis` SKILL (renamed 2026-08-28 from `stock_valuation`) | Supercharged |
| `~~research-report-store` | Local filesystem (`data/research/`), S3, Notion | `update-stock-analysis` SKILL (renamed 2026-08-28 from `stock_valuation`) | Supercharged |
| `~~backend-health-check` | `curl http://localhost:3001/health`, K8s liveness probe | `evaluate-stock` command | Supercharged |

## Degradation Contract

| Mode | Condition | Behaviour |
|------|-----------|-----------|
| **Full** | Backend running + `~~financial-data-fetcher` available | Full autonomous pipeline: fetch → analyse → persist → report |
| **Standalone** | No backend / no fetcher | Agent requests user paste raw financial data as JSON; analysis and Q&A still fully functional; persistence skipped with explicit notice |

> **Note**: The `~~financial-data-fetcher` and `~~projection-store` connectors are currently bound to the Investment Screener web app scripts. Do NOT move or duplicate those scripts into this plugin — they are shared infrastructure. See `plugin.json` → `external_dependencies`.
