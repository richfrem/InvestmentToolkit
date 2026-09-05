# TradingView Terms of Use & Trade Execution Policy

## 1. Context & Background
TradingView’s Terms of Use explicitly prohibit **non-display usage** of its platform data, charts, webhooks, and third-party tools. This specifically restricts headless, unattended algorithmic bots and unmonitored automated trade execution without direct, human display interaction.

---

## 2. Permitted vs. Prohibited Usage Matrix

| Operation Category | Permitted / Prohibited | Compliance Architecture in InvestmentToolkit |
| :--- | :--- | :--- |
| **Headless / Unattended Auto-Trading** | ❌ **STRICTLY PROHIBITED** | Background scripts and AI agents must **never** execute trades autonomously without an active human operator reviewing the order on screen. |
| **Interactive Human-in-the-Loop (HITL) Staging** | ✅ **PERMITTED** | User views the live chart/screener on screen, opens `TradePrepModal`, reviews the staged calculation (shares, limit price, sizing), and **explicitly confirms the action**. |
| **Display-Driven CDP Desktop Automation** | ✅ **PERMITTED** | Automation assists the active user's local TradingView Desktop GUI display (reading indicators, synchronizing account positions for personal tracking, framing order dialogues under direct human supervision). |
| **Advisory & Analytical Recommendations** | ✅ **PERMITTED** | AI agents formulate investment theses, DCF models, and triage cards (e.g. `/daily`, `/rebalance`), providing decision support that the user evaluates. |

---

## 3. Mandatory Rules for All AI Agents

1. **NO UNATTENDED AUTONOMOUS EXECUTION**:
   - AI agents are strictly forbidden from placing, modifying, or cancelling live broker orders autonomously in the background.
   - All trade execution is strictly **Human-in-the-Loop (HITL)**.

2. **HUMAN SUPERVISION & CONFIRMATION**:
   - All agent recommendations are advisory. 
   - Trade staging tools (such as `TradePrepModal` or staging scripts) format and calculate parameters on screen for the human operator to inspect, adjust, and approve.
   - The human user retains 100% final authorization and control over every order submitted to the broker.

3. **DISPLAY INTEGRITY**:
   - Local CDP automation operates in conjunction with an active, visible TradingView Desktop application session on the user's licensed workstation.
