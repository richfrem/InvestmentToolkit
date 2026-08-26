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
- **Real param names** (both `preview_order_instruction` and `create_order_instruction`): `accountId` (uuid), `instrument` (symbol string, e.g. `"BTDR"` — NOT `symbol`), `qty` (NOT `quantity`), `side`: `"buy"|"sell"` (NOT `action`), `type`: `"market"|"limit"|"stop"|"stoplimit"` (NOT `orderType`), `limitPrice`/`stopPrice` as needed, `duration`: `"day"|"gtc"` (default `"day"`). `create_order_instruction` additionally takes `operation`: `"create"|"modify"|"cancel"` (required), and `orderId` for modify/cancel.
- **Account Selection**:
  - If `--account` (e.g. `TFSA`, `RRSP`, or specific account number) is provided, target that account directly.
  - If not specified, or the ticker is already held in more than one account (common: TFSA + RRSP mirror positions), **ask the user explicitly** which account before previewing — don't guess. Show existing holdings per account (via `get_positions`) as context.
- **Preview Output (Zero Push / Desktop Safe)**:
  - `preview_order_instruction` returns `estimatedTotal`, buying-power delta, `isFractionalSharesEligible`, and `warnings`/`errors` arrays. Present as a table: Symbol, Side, Quantity, Order Type, Price, Trade Value, Commission, New Buying Power, Errors.
  - Works on desktop with zero mobile requirements — always call this before `create_order_instruction`.
- **Draft & Mobile Push Device Requirement**:
  - `create_order_instruction` requires an enrolled **trusted mobile device** on Questrade's **QuestMobile** or **EdgeMobile** app under Security / Push Approval settings.
  - **No Browser Popups**: There is no browser/desktop approval mechanism — users on a computer must still switch to the mobile app to approve. If no trusted device is enrolled, the call errors: *"Could not send an approval request to your mobile device..."*.
  - **Recovery path (confirmed working)**: tell the user to open the mobile app and enroll/confirm a trusted device, then once they say it's open, **retry the identical `create_order_instruction` call** — do not treat the first failure as terminal or fall back to any other confirmation path.
  - **Success response**: `{"status":"placed","orderId":"<uuid>"}`. Report the `orderId` back to the user as live confirmation.
- **Day order default (pitfall #22)**: orders submit as **Day** unless `duration:"gtc"` is explicitly passed. `modify` can change qty/price but not duration — GTC must be decided before `create`, or changed manually in the app afterward. Always flag Day-vs-GTC in the final confirmation to the user.

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
