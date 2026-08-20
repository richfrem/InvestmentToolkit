# TradingView Terms of Use & Trade Execution Policy

## 1. Context & Background
TradingView’s Terms of Use strictly prohibit **non-display usage** of its platform data, charts, webhooks, and third-party tools. Automated order generation, third-party API trade execution, and headless algorithmic trading without direct, interactive human display interaction are expressly prohibited.

---

## 2. Mandatory Rules for All AI Agents

1. **NO AUTONOMOUS TRADE EXECUTION**:
   - AI agents must **never** execute, place, modify, or cancel live orders directly through headless scripts, broker APIs, or automated CDP execution tools (`place_order.py`, `modify_order.py`, `cancel_order.py`).
   - Any automated script execution that bypasses human-in-the-loop manual confirmation is strictly forbidden.

2. **HUMAN-IN-THE-LOOP (HITL) ONLY**:
   - All trade suggestions from AI agents (e.g. from `/daily`, `/rebalance`, or the Screener table) are strictly **informational and educational recommendations**.
   - The human user must review the proposed order parameters (ticker, side, quantity, limit price) and **manually execute the order directly inside their authorized broker terminal or official TradingView Desktop application**.

3. **READ-ONLY / DISPLAY COMPLIANCE**:
   - CDP and Python automation are restricted to:
     - Reading technical indicators and Data Window values for display analysis.
     - Synchronizing portfolio balances and share counts for personal portfolio tracking (`/tv-portfolio-sync`).
     - Real-time quote polling for personal dashboard display (`/tv-price-refresh`).

4. **ORDER PREPARATION STAGING**:
   - Tools like `TradePrepModal` or staging scripts may format and calculate suggested share sizes or limit order prices for the user's convenience, but must terminate with a clear instruction for the user to execute manually.
