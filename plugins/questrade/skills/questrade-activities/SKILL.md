---
name: questrade-activities
description: "Retrieve and display account cash flow ledger events (dividends, interest, deposits, withdrawals, trades) via Questrade MCP."
argument-hint: "[--days 30|90] [account_id]"
allowed-tools: Bash, Read
---

# Questrade Cash Flow & Activity Ledger Skill

## Purpose
Directly queries the Questrade MCP `Get Account Activities` tool to retrieve, categorize, and display cash deposits, dividend receipts, corporate actions, and fee events in chat without modifying any database records.

## Prerequisites & Pre-Flight Check
1. Verify Questrade MCP session is active via `List Accounts`.
2. If unauthenticated, prompt user to run `/questrade:questrade-setup` (`/mcp` -> `questrade` -> `Log in`).

## Workflow

1. **Resolve Date Window**:
   - Default window: past 30 days (or 90 days if `--days 90` is passed).
   - Format ISO date range: `startTime` (e.g. `2026-07-27T00:00:00Z`) to `endTime` (now).
2. **Fetch Activities**:
   - If no `account_id` specified, iterate active accounts from `List Accounts`.
   - Call MCP tool `Get Account Activities(accountId=..., startTime=..., endTime=...)`.
3. **Categorize & Format Output**:
   - Group events by category:
     - **Dividends & Income**: Cash inflows from held securities (symbol, amount, currency).
     - **Deposits & Transfers**: Electronic transfers, contributions.
     - **Trades**: Executed buy/sell transactions.
     - **Fees & Interest**: Borrow fees, account fees, margin interest.
   - Present a clean chronological markdown table with columns: `Date`, `Account`, `Type`, `Symbol`, `Gross Amount`, `Currency`, `Description`.

## Continuous Self-Evolution Policy
Per `.agent/rules/self-evolution-policy.md`:
Whenever actual MCP tool schema responses reveal unexpected parameter names, response fields, or missing attributes during live execution, agents MUST immediately refine this `SKILL.md` to document the exact parameter shapes and optimize subsequent agent executions.
