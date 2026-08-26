---
name: questrade-get-positions
description: "Direct skill wrapper for Questrade MCP tools to retrieve and display open security positions."
argument-hint: "[account_id]"
allowed-tools: Bash, Read
---

# Questrade Get Positions Skill

## Purpose
Directly queries the Questrade MCP `Get Positions` (and `List Accounts`) tool to display open securities, share counts, average price, and current market value without modifying database records.

## Workflow

1. If no `account_id` is specified:
   - Call MCP tool `List Accounts`.
2. For each account:
   - Call MCP tool `Get Positions(accountId=...)`.
3. Format as a clean markdown table:
   - Account
   - Symbol
   - Open Quantity
   - Average Entry Price
   - Current Market Price
   - Total Market Value
   - Unrealized P&L
