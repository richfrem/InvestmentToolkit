---
name: questrade-activities
description: "Retrieve and display account cash flow ledger events (dividends, interest, deposits, withdrawals, trades) via Questrade MCP."
argument-hint: "[--days 30|90] [account_id]"
allowed-tools: Bash, Read
---

# Questrade Cash Flow & Activity Ledger Skill

## Purpose
Directly queries the Questrade MCP `Get Account Activities` tool to retrieve, categorize, and display cash flow events (dividends, interest, deposits, withdrawals, fees) in chat. **Read-only, chat-display only — this skill never writes to `domain_model.sqlite` or any other database.** Any future DB ingestion path is a separate, explicitly-approved skill, not this one.

## Prerequisites & Pre-Flight Check
1. Verify Questrade MCP session is active via `List Accounts`.
2. If unauthenticated, prompt user to run `/questrade:questrade-setup` (`/mcp` -> `questrade` -> `Log in`).

## Schema Reference
See `references/questrade-tool-schemas.md` (`get_account_activities` section) for exact params (`fromDate`/`toDate` are plain dates, `transactionTypes` enum) and the trade-noise behavior that drives the filtering rule below.

## Workflow

1. **Resolve Date Window**:
   - Default window: past 30 days (or 90 days if `--days 90` is passed).
   - Compute `fromDate`/`toDate` as `YYYY-MM-DD`.
2. **Resolve Transaction Types**:
   - Cash-flow ledger view (default intent of this skill): `["Dividends", "Interest", "Deposits", "Withdrawals", "Fees and rebates", "Dividend reinvestment"]`.
   - If the user explicitly asks for trade history instead, use `["Trades"]` and expect to page through `metadata.totalPages`.
3. **Fetch Activities**:
   - If no `account_id` specified, iterate active accounts from `List Accounts`.
   - Call MCP tool `Get Account Activities(accountId=..., fromDate=..., toDate=..., transactionTypes=[...])`.
   - Check `metadata.totalPages` — only page further if `> 1` (the filtered cash-flow view is typically small enough to fit on one page).
4. **Categorize & Format Output**:
   - Group by `transactionType`, chronological within group.
   - Present a clean markdown table with columns: `Date`, `Type`, `Description`, `Amount`, `Currency`.
   - Flag any large or unusual single event (e.g. a `Withdrawals`/`Deregistration` line) explicitly rather than letting it blend into the table — confirm with the user it's expected.

## Continuous Self-Evolution Policy
Per `.agent/rules/self-evolution-policy.md`:
Whenever actual MCP tool schema responses reveal unexpected parameter names, response fields, or missing attributes during live execution, agents MUST immediately refine this `SKILL.md` to document the exact parameter shapes and optimize subsequent agent executions.
