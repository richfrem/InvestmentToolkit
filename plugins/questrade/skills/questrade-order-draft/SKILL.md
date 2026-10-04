---
name: questrade-order-draft
plugin: questrade
description: Draft an equity or options order in Questrade via MCP and request Human-in-the-Loop (HITL) mobile push approval. Trigger on /questrade-order-draft or "draft an order in questrade".
allowed-tools: Bash, Read, Write
---

# Questrade Order Draft

Drafts equity and options orders using Questrade MCP with mandatory Human-in-the-Loop (HITL) mobile approval.

## Contents

- [Constraints](#constraints)
- [Quick start](#quick-start)
- [Workflow](#workflow)
- [Verification](#verification)
- [References](#references)

## Constraints

- **No autonomous trade execution**: Strictly adheres to Rule #17; agents never execute live trades autonomously.
- **Mandatory preview first**: Always call `preview_order_instruction` and display economics before invoking `create_order_instruction`.
- **Account confirmation**: If account is unspecified or held in multiple accounts, explicitly prompt user for target account.
- **Explicit user consent**: Require explicit user confirmation in chat before dispatching push notification to mobile device.

## Quick start

Preview order economics:

```text
Call Questrade Preview Order Instruction(accountId, instrument, qty, side, type, limitPrice?)
```

## Workflow

1. **Resolve Account & Order Parameters**:
   Identify `accountId`, `instrument`, `qty`, `side` (BUY/SELL), and `type` (Limit/Market).
2. **Preview Economics**:
   Call MCP tool `preview_order_instruction` and present Commission, Total Value, and New Buying Power.
3. **HITL Authorization Gate**:
   Ask user for explicit confirmation to dispatch order draft to mobile device.
4. **Dispatch Mobile Instruction**:
   Call MCP tool `create_order_instruction` to send push notification to user's registered phone.
5. **Report Status**:
   Report `orderId` and order status to user upon successful submission.

## Verification

- Confirm user explicitly confirmed before `create_order_instruction` was dispatched.
- Validate test cases against `evals/evals.json`.

## References

- [Questrade Tool Schemas](references/questrade-tool-schemas.md): Parameter shapes for preview and create order instructions.
