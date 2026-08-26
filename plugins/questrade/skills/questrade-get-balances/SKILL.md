---
name: questrade-get-balances
description: "Direct skill wrapper for Questrade MCP tools to retrieve and display account balances and CAD/USD cash splits."
argument-hint: "[account_id]"
allowed-tools: Bash, Read
---

# Questrade Get Balances Skill

## Purpose
Directly queries the Questrade MCP `Get Balances` (and `List Accounts`) tool to display account equity, cash balances, and currency splits without modifying or writing any database records.

## Prerequisites & Pre-Flight Check
1. Verify Questrade MCP session is active via `List Accounts`.
2. If unauthenticated, prompt user to run `/questrade:questrade-setup` (`/mcp` -> `questrade` -> `Log in`).

## Schema Reference
See `references/questrade-tool-schemas.md` (`get_balances` section) — each balance/profit leaf is a `{cad, usd, combinedCad, combinedUsd}` object of pre-formatted currency strings (e.g. `"$131.08"`), not raw numbers.

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
   - Buying Power (Combined CAD)
   - Day P&L (USD/CAD)

## Continuous Self-Evolution Policy
Per `.agent/rules/self-evolution-policy.md`:
Whenever actual MCP tool schema responses reveal unexpected parameter names, response fields, or missing attributes during live execution, agents MUST immediately refine this `SKILL.md` to document the exact parameter shapes and optimize subsequent agent executions.
