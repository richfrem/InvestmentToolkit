---
name: questrade-get-balances
description: "Direct skill wrapper for Questrade MCP tools to retrieve and display account balances and CAD/USD cash splits."
argument-hint: "[account_id]"
allowed-tools: Bash, Read
---

# Questrade Get Balances Skill

## Purpose
Directly queries the Questrade MCP `Get Balances` (and `List Accounts`) tool to display account equity, cash balances, and currency splits without modifying or writing any database records.

## Workflow

1. If no `account_id` is specified:
   - Call MCP tool `List Accounts` to list active accounts.
2. For each account:
   - Call MCP tool `Get Balances(accountId=...)`.
3. Format the result in a clean markdown table:
   - Account Number & Type (TFSA, RRSP, Margin)
   - Total Equity (CAD & USD equivalent)
   - Cash Balance (CAD)
   - Cash Balance (USD)
   - Market Value of Securities
   - Buying Power
