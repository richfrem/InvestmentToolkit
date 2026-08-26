---
name: questrade-order-draft
description: "Draft an equity or options order in Questrade via MCP and request Human-in-the-Loop (HITL) mobile push approval."
argument-hint: "[--ticker TICKER --action BUY|SELL --shares SHARES --price PRICE --account TFSA|RRSP|Cash]"
allowed-tools: Bash, Read, Write
---

# Questrade Order Draft & HITL Push Approval Skill

## Purpose
Enforces **Rule #17 (No Autonomous Execution)** by formatting structured trade drafts using Questrade MCP tools `Preview Order Instruction` and `Create Order Instruction`.

## Prerequisites & Pre-Flight Check
1. Verify Questrade MCP session is active via `List Accounts`.
2. If unauthenticated, prompt user to run `/questrade:questrade-setup` (`/mcp` -> `questrade` -> `Log in`).

## Discovered Schema & API Behavior
- **Account Selection**:
  - If `--account` (e.g. `TFSA`, `RRSP`, or specific account number) is provided, target that account directly.
  - If not specified, prompt the user with interactive account selection (displaying existing shares held and available cash).
- **Preview Output (Zero Push / Desktop Safe)**:
  - `Preview Order Instruction` returns structured economics: `Symbol`, `Side` (Buy/Sell), `Quantity`, `Order Type` (Limit/Market, Day/GTC), `Limit Price`, `Trade Value`, `Commission`, `New Buying Power`, and `Errors/Warnings`.
  - Works on desktop with zero mobile requirements.
- **Draft & Mobile Push Device Requirement**:
  - `Create Order Instruction` requires an enrolled **trusted mobile device** on Questrade's **QuestMobile** or **EdgeMobile** app (v2.0.0+) under Security / Push Approval settings.
  - **No Browser Popups**: There is no browser popup approval mechanism. If no trusted mobile device is enrolled, `Create Order Instruction` returns an error: *"no trusted device is currently enrolled for approvals"*.
  - In that case, keep the order as a **preview only** and instruct the user to place the trade manually in the Questrade desktop / web UI or enroll their phone.

## Workflow
1. **Resolve Account**: Identify target account (TFSA primary default, RRSP mirror, or Cash).
2. **Staging & Economics Preview**:
   - Call `Preview Order Instruction(accountId=..., symbol=..., action=..., quantity=..., orderType=..., limitPrice=...)`.
   - Display economics table (Commission, Trade Value, New Buying Power).
3. **Draft Order Confirmation**:
   - Prompt user to confirm sending the draft to their phone.
   - On confirmation, call `Create Order Instruction`.
4. **Execution Gate**: Explicitly remind user that the order is pending in their mobile app for final HITL authorization.

## Continuous Self-Evolution Policy
Per `.agent/rules/self-evolution-policy.md`:
Whenever actual MCP tool schema responses reveal unexpected parameter names, response fields, or missing attributes during live execution, agents MUST immediately refine this `SKILL.md` to document the exact parameter shapes and optimize subsequent agent executions.
