# 0006: Adversarial TA Review & Structured Thesis Loop

## Objective
Ensure all Technical Analysis (TA) recommendations are rigorous, defensible, and thoroughly vetted before being presented to the user. This task introduces a structured template for TA rationale and an autonomous adversarial "Red Team" review loop.

## Context
When the Technical Analysis Expert (`tv-ta-deep`) generates entry/exit/trim recommendations based on TradingView CDP data, it currently presents them directly to the user. To increase conviction and reduce AI hallucination or weak analysis, the agent must document its rationale and defend it against an independent, adversarial sub-agent (e.g., using `gemini-cli-agent` or `claude-cli-agent`) acting as a Skeptical Risk Manager.

## Required Capabilities

### 1. Structured TA Thesis Template
The TA agent must populate a standardized template including:
- Asset/Stock
- Key Data Points (Timeframes, Indicator Values from Data Window)
- Proposed Action (Buy/Sell/Trim/Accumulate/Hold)
- Limit Prices
- Defensible Rationale / Strategy

### 2. Adversarial "Red Team" Sub-Agent
A separate agent persona that consumes the drafted TA thesis. Its job is to find flaws:
- Are the timeframes contradicting each other?
- Is the momentum actually diverging from price?
- Is the risk/reward ratio on the limit prices justified?
- **Output:** It must output either `[APPROVED]` or `[REJECTED]` along with specific critical feedback.

### 3. Autonomous Iteration Loop
The primary TA agent must revise its analysis based on the Red Team's feedback. It cannot present the final recommendation to the user until the Red Team sub-agent explicitly outputs `[APPROVED]`.

## Relationship to Other Tasks
- This builds directly on **Task #0005 (TA Expert Agent)**. It modifies the output phase of that skill to insert the adversarial review loop before user presentation.