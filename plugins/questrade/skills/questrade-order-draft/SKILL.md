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

## Schema Reference
See `references/questrade-tool-schemas.md` for the exact `preview_order_instruction`/`create_order_instruction` param names, the mobile-push-only approval behavior and its confirmed recovery path, the Day/GTC default (pitfall #22), and the success response shape (`{"status":"placed","orderId":...}`).

## Skill-Specific Behavior
- **Account Selection**: If `--account` (e.g. `TFSA`, `RRSP`, or specific account number) is provided, target that account directly. If not specified, or the ticker is already held in more than one account (common: TFSA + RRSP mirror positions), **ask the user explicitly** which account before previewing — don't guess. Show existing holdings per account (via `get_positions`) as context.
- **Always preview before create**: `preview_order_instruction` is side-effect-free and desktop-safe — always call it and show the user the economics table before touching `create_order_instruction`, which is a real, phone-approved trade action.

## Workflow
1. **Resolve Account**: Identify target account (ask explicitly if ambiguous — see above).
2. **Staging & Economics Preview**:
   - Call `preview_order_instruction(accountId, instrument, qty, side, type, limitPrice?, stopPrice?, duration?)`.
   - Display economics table (Commission, Trade Value, New Buying Power, Errors).
3. **Draft Order Confirmation**:
   - Prompt user to confirm sending the draft to their phone — this is a real trade action, always confirm explicitly first.
   - On confirmation, call `create_order_instruction(operation:"create", accountId, instrument, qty, side, type, limitPrice?, stopPrice?, duration?)`.
   - On mobile-device error: instruct the user to open the app / enroll a trusted device, then retry the identical call once they confirm.
4. **Execution Gate**: On `{"status":"placed","orderId":...}`, confirm the order is live, report the `orderId`, and explicitly flag Day-vs-GTC duration.

## Continuous Self-Evolution Policy
Per `.agent/rules/self-evolution-policy.md`:
Whenever actual MCP tool schema responses reveal unexpected parameter names, response fields, or missing attributes during live execution, agents MUST immediately refine this `SKILL.md` to document the exact parameter shapes and optimize subsequent agent executions.
