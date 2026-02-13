# ADR 016: Investment Screener Architecture

## Status
Proposed (Inferred from existing codebase)

## Context
The project requires a high-performance investment analysis tool that combines modern UI responsiveness with robust financial data processing. We need a modular architecture that supports local execution and easy extensibility.

## Decision
Adopt a **Monorepo Architecture** with the following layers:
1. **Frontend**: React-based SPA focusing on interactive visualizations (Heatmaps, Charts, Valuation Models).
2. **Backend**: Node.js (Express) serving as an orchestration layer and providing a REST API.
3. **Services**: Specialized Python scripts (invoked via Node.js `child_process`) for financial data retrieval (`yfinance`) and complex data transformations (`pandas`).

## Consequences
- **Pros**:
    - Separation of concerns between UI, orchestration, and data processing.
    - Leverages Python's superior financial libraries while maintaining a responsive React UI.
    - Unified startup and dependency management.
- **Cons**:
    - Increased overhead for managing dual-language dependencies (npm and pip).
    - Latency for spawning child processes (mitigated by local execution).
