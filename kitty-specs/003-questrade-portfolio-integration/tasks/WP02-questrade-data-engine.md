---
work_package_id: WP02
title: Questrade Data Engine
lane: "for_review"
dependencies: []
subtasks: [T003, T004]
agent: "Antigravity"
shell_pid: "34920"
---

# WP02: Questrade Data Engine

## Objective
Implement the core Python logic for fetching all account holdings from Questrade and aggregating them into a unified portfolio view.

## Context
Following the **Architecture Report**, the system must discover all sub-accounts (TFSA, RRSP, etc.), fetch their current positions, and aggregate them by ticker symbol.

## Guidance

### T003: Implement Questrade API Client
- **Goal**: Create a Python service to interact with the Questrade API.
- **Details**:
  - Use `requests` to call the `/v1/accounts` and `/v1/accounts/{id}/positions` endpoints.
  - Integrate with the `TokenManager` (WP01) to handle bearer tokens and automatic rotation on 401 errors.
- **Files**: `tools/investment-screener/backend/src/utils/QuestradeAPIClient.py`

### T004: Implement Portfolio Aggregation & Normalization
- **Goal**: Aggregate positions across accounts and compute final quantities and weighted average costs.
- **Details**:
  - Normalize ticker symbols (e.g., removing ".TO" suffixes for consistency if required).
  - Handle multiple currencies (USD/CAD) using Questrade's exchange rates.
  - Overwrite manual data in `tools/investment-screener/frontend/src/data/portfolio.json`.
- **Validation**: Compare script output against official Questrade web portal balances.

## Definition of Done
- [ ] Data engine can fetch positions across multiple accounts.
- [ ] Holdings are correctly aggregated by ticker.
- [ ] `portfolio.json` is successfully updated with Questrade-sourced data.

## Activity Log

- 2026-02-13T18:45:14Z – Antigravity – shell_pid=34920 – lane=doing – Started implementation via workflow command
- 2026-02-13T18:50:24Z – Antigravity – shell_pid=34920 – lane=for_review – Core data engine and aggregation logic complete and verified with mock tests.
