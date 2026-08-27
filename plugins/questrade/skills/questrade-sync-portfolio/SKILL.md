---
name: questrade-sync-portfolio
description: "Directly syncs Questrade account balances, holdings, and cash splits into domain_model.sqlite."
argument-hint: "[--dry-run]"
allowed-tools: Bash, Read, Write
---

# Questrade Direct Portfolio Sync Skill

## Purpose
Directly queries the Questrade MCP tools (`List Accounts`, `Get Balances`, `Get Positions`) and syncs account metadata, uninvested cash (`CASH_USD`), exchange rates, and open security quantities directly into `domain_model.sqlite`.

Triggers `refresh_all.py` upon completion to update target weights and thesis role badges.

## Prerequisites & Pre-Flight Check
1. Verify Questrade MCP session is active via `List Accounts`.
2. If unauthenticated, prompt user to run `/questrade:questrade-setup` (`/mcp` -> `questrade` -> `Log in`).

## Schema Reference
See `references/questrade-tool-schemas.md` — specifically the "domain_model.sqlite account_id convention" section. `questrade_sync.py` resolves each Questrade account to the canonical `"TFSA"`/`"RRSP"`/`"CASH"` account_id itself (never the Questrade uuid) and clears any stale position no longer present in the sync — you do not need to do either of those manually when staging the payload.

## Workflow

1. **Query MCP Data**:
   - Call `List Accounts` to get active account IDs.
   - For each account, call `Get Balances(accountId=...)` and `Get Positions(accountId=...)`.
2. **Stage Payload**:
   - Construct a temporary JSON payload at `temp/questrade_sync_payload.json` containing:
     ```json
     {
       "accounts": [...],
       "balances": { "accountId": {...} },
       "positions": { "accountId": [...] }
     }
     ```
3. **Execute Persistence Script**:
   - Run the canonical Python service:
     ```bash
     python3 plugins/questrade/skills/questrade-sync-portfolio/scripts/questrade_sync.py --payload temp/questrade_sync_payload.json
     ```
4. **Clean up & Verify**:
   - Remove temporary JSON payload.
   - Run `python3 investment_screener/backend/py_services/verify_portfolio_invariants.py` to confirm invariant totals match.
   - Display a summary of updated accounts, cash balances, and holdings in chat.

## See also
This skill only syncs holdings/balances/cash — it never writes current market prices (`investment_price` is untouched). For a live market price refresh, use the separate `questrade-refresh-prices` skill.

## Continuous Self-Evolution Policy
Per `.agent/rules/self-evolution-policy.md`:
Whenever actual MCP tool schema responses reveal unexpected parameter names, response fields, or missing attributes during live execution, agents MUST immediately refine this `SKILL.md` to document the exact parameter shapes and optimize subsequent agent executions.
