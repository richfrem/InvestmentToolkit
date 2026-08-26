---
name: questrade-get-positions
description: "Direct skill wrapper for Questrade MCP tools to retrieve and display open security positions."
argument-hint: "[account_id]"
allowed-tools: Bash, Read
---

# Questrade Get Positions Skill

## Purpose
Directly queries the Questrade MCP `Get Positions` (and `List Accounts`) tool to display open securities, share counts, and average cost basis without modifying database records.

## Prerequisites & Pre-Flight Check
1. Verify Questrade MCP session is active via `List Accounts`.
2. If unauthenticated, prompt user to run `/questrade:questrade-setup` (`/mcp` -> `questrade` -> `Log in`).

## Schema Reference
See `references/questrade-tool-schemas.md` (`get_positions` section) for exact field names — the symbol lives in `instrument`, not `symbol`, and there is no per-row market price or P&L.

## Workflow

1. If no `account_id` is specified:
   - Call MCP tool `List Accounts`.
2. For each account:
   - Call MCP tool `Get Positions(accountId=...)`.
3. Format as a clean markdown table:
   - Account Number & Type (TFSA, RRSP, Margin)
   - Symbol
   - Open Quantity
   - Average Entry Price (USD/CAD)
4. Account-level totals (total market value, day P&L) are retrieved via `/questrade:questrade-get-balances`.

## Continuous Self-Evolution Policy
Per `.agent/rules/self-evolution-policy.md`:
Whenever actual MCP tool schema responses reveal unexpected parameter names, response fields, or missing attributes during live execution, agents MUST immediately refine this `SKILL.md` to document the exact parameter shapes and optimize subsequent agent executions.
