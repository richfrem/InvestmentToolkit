# Connectors — thesis-balancer

This plugin operates in **Supercharged** mode: strategic analysis and drift classification always work offline; live portfolio data requires the backend API.

## Tool Connector Matrix

| Category | Examples | Used By | Required? |
|----------|----------|---------|-----------|
| `~~portfolio-api` | `GET /api/theses/:id/health`, Portfolio DB | `thesis_balancer` SKILL | Supercharged |
| `~~thesis-store` | `GET /api/theses`, JSON thesis files | `thesis_balancer` SKILL | Supercharged |
| `~~valuation-source` | `stock-valuation` plugin output, `data/projections/` | Conflict detection logic | Optional |

## Degradation Contract

| Mode | Condition | Behaviour |
|------|-----------|-----------|
| **Full** | Backend running + theses + portfolio loaded | Full health check → drift analysis → strategic dialogue → rebalance suggestions |
| **Standalone** | Backend unavailable | Request user paste portfolio weights + thesis targets as JSON; complete drift calculation and strategic analysis manually; skip API calls |

> **`~~valuation-source`**: If AI valuations from `stock-valuation` are unavailable per holding, note missing valuations and prompt user to run `/evaluate-stock {TICKER}` for each uncovered position.
