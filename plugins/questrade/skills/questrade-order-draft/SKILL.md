---
name: questrade-order-draft
description: "Draft an equity or options order in Questrade via MCP and request Human-in-the-Loop (HITL) mobile push approval."
argument-hint: "[--ticker TICKER --action BUY|SELL --shares SHARES --price PRICE]"
allowed-tools: Bash, Read, Write
---

# Questrade Order Draft & HITL Push Approval Skill

## Purpose
Enforces **Rule #17 (No Autonomous Execution)** by formatting structured trade drafts using Questrade MCP tools `Preview Order Instruction` and `Create Order Instruction`.

## Prerequisites & Pre-Flight Check
1. Verify Questrade MCP session is active via `List Accounts`.
2. If unauthenticated, prompt user to run `/questrade:questrade-setup` (`/mcp` -> `questrade` -> `Log in`).

## Workflow
1. **Staging**: Build the structured order preview (Account, Symbol, Action BUY/SELL, Quantity, Order Type Limit/Market, Limit Price, Estimated Commission).
2. **MCP Preview**: Call `Preview Order Instruction` to verify margin impact and buying power without placing the order.
3. **MCP Draft**: Call `Create Order Instruction` to trigger the official mobile Push Notification to the user's phone (Questrade App v2.0.0+).
4. **Execution Gate**: The live order remains in pending draft state until the human user explicitly taps **Approve** on their mobile device.

## Continuous Self-Evolution Policy
Per `.agent/rules/self-evolution-policy.md`:
Whenever actual MCP tool schema responses reveal unexpected parameter names, response fields, or missing attributes during live execution, agents MUST immediately refine this `SKILL.md` to document the exact parameter shapes and optimize subsequent agent executions.
