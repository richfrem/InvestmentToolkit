---
name: questrade-activities
plugin: questrade
description: Retrieve and display account cash flow ledger events (dividends, interest, deposits, withdrawals, trades) via Questrade MCP. Trigger on /questrade-activities or "show my questrade dividend history".
allowed-tools: Bash, Read
---

# Questrade Activities

Queries the Questrade MCP activity ledger to display cash flow events and trade histories in chat.

## Contents

- [Constraints](#constraints)
- [Quick start](#quick-start)
- [Workflow](#workflow)
- [Verification](#verification)
- [References](#references)

## Constraints

- **Read-only interface**: Chat display only; this skill never modifies `domain_model.sqlite` or any other database. To save executed trades to the Trade Log, use `questrade-sync-portfolio`, which imports them with `questrade_trades_import.py`.
- **Active session check**: Must confirm active session with `List Accounts` before querying activity history.
- **Date boundary**: Default search window is 30 days unless `--days` is explicitly specified.

## Quick start

Retrieve recent cash flows across all accounts:

```text
Query Questrade Get Account Activities(fromDate=YYYY-MM-DD, toDate=YYYY-MM-DD, transactionTypes=["Dividends", "Interest", "Deposits", "Withdrawals"])
```

## Workflow

1. **Resolve Date Window**:
   Default past 30 days (`YYYY-MM-DD` to `YYYY-MM-DD`), or 90 days with `--days 90`.
2. **Resolve Transaction Types**:
   - Cash flows: `["Dividends", "Interest", "Deposits", "Withdrawals", "Fees and rebates", "Dividend reinvestment"]`.
   - Trades: `["Trades"]` (page through `metadata.totalPages` if $>1$).
3. **Execute Query**:
   Call MCP tool `Get Account Activities` for target account(s).
4. **Format Presentation**:
   Render Markdown table with columns: `Date`, `Type`, `Description`, `Amount`, `Currency`.

## Verification

- Confirm table output is rendered without database mutations.
- Validate test cases against `evals/evals.json`.

## References

- [Questrade Tool Schemas](references/questrade-tool-schemas.md): Parameter shapes for `get_account_activities`.
