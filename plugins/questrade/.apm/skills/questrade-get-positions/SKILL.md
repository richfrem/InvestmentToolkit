---
name: questrade-get-positions
plugin: questrade
description: Direct skill wrapper for Questrade MCP tools to retrieve and display open security positions. Trigger on /questrade-get-positions or "check questrade positions".
allowed-tools: Bash, Read
---

# Questrade Get Positions

Directly queries Questrade MCP position tools to display open securities, share counts, and cost basis.

## Contents

- [Constraints](#constraints)
- [Quick start](#quick-start)
- [Workflow](#workflow)
- [Verification](#verification)
- [References](#references)

## Constraints

- **Read-only**: Never modify holdings in `domain_model.sqlite` from this skill (use `questrade-sync-portfolio` for database ingestion).
- **Session check**: Verify active session via `List Accounts` before querying positions.
- **Symbol attribute**: Questrade MCP position records store the ticker in `instrument`, not `symbol`.

## Quick start

Query open security positions:

```text
Query Questrade List Accounts -> Get Positions(accountId)
```

## Workflow

1. **Resolve Accounts**:
   Call MCP tool `List Accounts` (or filter by user-specified `account_id`).
2. **Fetch Positions**:
   Call MCP tool `Get Positions(accountId=...)` for each account.
3. **Format Table**:
   Render Markdown table with columns: `Account`, `Symbol`, `Quantity`, `Average Entry Price`.

## Verification

- Confirm position list renders without altering local database state.
- Validate test cases against `evals/evals.json`.

## References

- [Questrade Tool Schemas](references/questrade-tool-schemas.md): Schema definitions for `get_positions`.
