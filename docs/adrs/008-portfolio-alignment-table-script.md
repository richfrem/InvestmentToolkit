# ADR 008: Portfolio Alignment Table Generation Script

## Status
Obsolete (Replaced by Python-based financial services in `investment-screener`)

## Context
To enable robust, repeatable portfolio-thesis alignment analysis, we need a reliable way to aggregate holdings across all accounts, compare actual allocations to thesis targets, and output a standardized markdown table for LLM analysis and recommendations.

## Decision
- A new script will be created in `scripts/` (e.g., `generate_portfolio_alignment_table.ts`).
- The script will:
  - Read `backend/exportedData.json`.
  - Aggregate holdings across all accounts (grand total shares, average value, % of total portfolio value per ticker/pillar).
  - Compare actual allocations to thesis target percentages.
  - Highlight gaps, overweights, underweights, and thesis breakers.
  - Output a JSON file to `TargetPortfolio/portfolio_thesis_alignment_report.json` as the primary format for LLM analysis and automation.
    - Optionally, output a markdown or CSV table for human review and reporting.
- The LLM prompt will analyze the JSON output, provide recommendations, and update target values/gaps as needed. Markdown/CSV outputs may be used for human review and reporting.
- This approach ensures reliability, versioning, and repeatability for all thesis alignment reports.
- Ajv is used for runtime validation of the output JSON against the portfolio alignment schema, ensuring strict compliance and reliability for downstream LLM analysis and automation.

## Consequences
- Heavy data processing is handled by code, not the LLM, improving reliability and speed.
- The workflow is documented and versioned for future review and decision tracking.
- The LLM prompt focuses on analysis and recommendations, not raw data aggregation.

---

**Related Requirements:**
- UR22: LLM-Driven Portfolio Analysis Workflow
- UR23: Portfolio Alignment Table Generation Script
