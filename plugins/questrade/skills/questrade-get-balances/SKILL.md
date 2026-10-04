---
name: questrade-get-balances
plugin: questrade
description: Direct skill wrapper for Questrade MCP tools to retrieve and display account balances and CAD/USD cash splits. Trigger on /questrade-get-balances or "check questrade balances".
allowed-tools: Bash, Read
---

# Questrade Get Balances

Directly queries Questrade MCP balances tools to display account equity, cash balances, and currency splits.

## Contents

- [Constraints](#constraints)
- [Quick start](#quick-start)
- [Workflow](#workflow)
- [Verification](#verification)
- [References](#references)

## Constraints

- **Read-only query**: Never write balance snapshots or currency splits to local database records from this skill.
- **Session verification**: Validate active session via `List Accounts` before querying balances.
- **String parsing**: Note that leaf values in Questrade MCP balance responses are formatted currency strings (e.g. `"$131.08"`), not raw floats.

## Quick start

Query account equity and cash splits across active accounts:

```text
Query Questrade List Accounts -> Get Balances(accountId)
```

## Workflow

1. **Enumerate Accounts**:
   Call MCP tool `List Accounts` to obtain active account numbers and account types.
2. **Retrieve Balances**:
   Call MCP tool `Get Balances(accountId=...)` for each resolved account.
3. **Format Markdown Table**:
   Display table with columns: `Account`, `Total Equity (CAD/USD)`, `Cash CAD`, `Cash USD`, `Market Value`, `Buying Power`.

## Verification

- Confirm balance summary is presented in chat without local disk side-effects.
- Validate test cases against `evals/evals.json`.

## References

- [Questrade Tool Schemas](references/questrade-tool-schemas.md): Exact return schemas for `get_balances`.
