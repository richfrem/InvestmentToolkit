---
name: questrade-order-draft
description: "Draft an equity or options order in Questrade via MCP and request Human-in-the-Loop (HITL) mobile push approval."
argument-hint: "[--ticker TICKER --action BUY|SELL --shares SHARES --price PRICE]"
allowed-tools: Bash, Read, Write
---

# Questrade Order Draft & HITL Push Approval Skill

## Purpose
Enforces **Rule #17 (No Autonomous Execution)** by formatting structured trade drafts using Questrade MCP tools `Preview Order Instruction` and `Create Order Instruction`.

## Workflow
1. Staging: Build the preview (Symbol, Action, Quantity, Limit Price, Estimated Commission).
2. MCP Preview: Call `Preview Order Instruction` to verify margin impact and buying power.
3. MCP Draft: Call `Create Order Instruction` to trigger mobile Push Notification to the user's phone.
4. Execution Gate: Live order remains pending until user taps **Approve** in the Questrade mobile app.
