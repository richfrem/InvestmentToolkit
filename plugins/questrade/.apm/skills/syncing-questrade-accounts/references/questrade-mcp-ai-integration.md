# Questrade Model Context Protocol (MCP) Integration Overview

- **Source**: [Connect your Questrade account to AI (Questrade Learning)](https://www.questrade.com/learning/using-questrade/connect-your-questrade-account-to-ai)
- **Documented**: August 2026
- **Audience**: Personal Broker Integration Note (Questrade Users)

---

## 1. Overview
Questrade provides a native **Model Context Protocol (MCP)** server endpoint that allows supported AI agents (Claude Code, Claude Web/Desktop, ChatGPT, Cursor, VS Code Copilot, Codex CLI) to connect directly to your brokerage account. 

### Core Safety Principles:
1. **Zero Credential Exposure**: Authentication occurs on Questrade's OAuth login page; AI agents never see passwords or sensitive credentials.
2. **Mandatory Human-in-the-Loop (HITL) Push Approval**: Agents can only **draft** order previews (`Create Order Instruction`, `Create Option Instruction`). Live execution requires explicit Push Approval via the Questrade Mobile App (v2.0.0+). The AI cannot autonomously place, modify, or cancel orders.
3. **Read-First Security**: Read operations (balances, positions, 90-day history, option chains) are segregated from transactional order drafting permissions.

---

## 2. Complete 24-Tool Matrix

| # | Tool Name | Type | Access Scope | Purpose / Description |
|---|---|---|---|---|
| 1 | **List Accounts** | `read-only` | `open-world` | Returns all account numbers, account types (TFSA, RRSP, Margin), and statuses. |
| 2 | **Get Balances** | `read-only` | `open-world` | Returns total equity, cash in CAD, cash in USD, market value, and buying power. |
| 3 | **Get Positions** | `read-only` | `open-world` | Lists all open security positions, quantities, average entry cost, current price, and P&L. |
| 4 | **Get Portfolio** | `read-only` | `open-world` | Returns complete portfolio summary joining balances and positions. |
| 5 | **Get Order History** | `read-only` | `open-world` | Retrieves order execution history, pending orders, and cancelled orders (90-day window). |
| 6 | **Get Account Activities** | `read-only` | `open-world` | Returns cash flow events: deposits, withdrawals, dividends, interest, and fee charges. |
| 7 | **Get Quotes** | `read-only` | `open-world` | Real-time / delayed market bid, ask, last price, volume, and day range for securities. |
| 8 | **Search Symbols** | `read-only` | `open-world` | Symbol search resolving tickers, CUSIPs, exchange identifiers (TSX, NYSE, NASDAQ). |
| 9 | **Get Option Expiries** | `read-only` | `open-world` | Returns available option contract expiration dates for an underlying equity. |
| 10 | **Get Option Chain** | `read-only` | `open-world` | Returns full strike prices, puts/calls, Greeks, bid/ask, and volume for an expiry. |
| 11 | **Get Historical Data** | `read-only` | `open-world` | Retrieves OHLCV historical candle data over custom date intervals. |
| 12 | **List Watchlists** | `read-only` | `open-world` | Lists all user-created Questrade watchlists. |
| 13 | **Get Watchlist** | `read-only` | `open-world` | Retrieves tickers and quotes within a specific watchlist. |
| 14 | **Preview Order Instruction** | `read-only` | `open-world` | Previews equity order costs, estimated commissions, and buying power impact without sending. |
| 15 | **Create Order Instruction** | `action` | `open-world` | **Drafts** an equity order and sends a mobile Push Approval request to the Questrade App. |
| 16 | **Preview Option Instruction** | `read-only` | `open-world` | Previews option contract order costs and margin requirements. |
| 17 | **Create Option Instruction** | `action` | `open-world` | **Drafts** an options trade and sends a mobile Push Approval request to your phone. |
| 18 | **Preview Custom Index** | `read-only` | `open-world` | Previews custom index basket weighting and rebalance calculations. |
| 19 | **Create Custom Index** | `action` | `open-world` | Creates a personalized thematic index basket in Questrade. |
| 20 | **List Custom Indexes** | `read-only` | `open-world` | Lists all active custom index baskets in the account. |
| 21 | **Get Custom Index** | `read-only` | `open-world` | Retrieves constituent weights and performance of a custom index. |
| 22 | **Edit Custom Index** | `action` | `open-world` | Modifies constituent allocations or rebalances a custom index. |
| 23 | **Create Watchlist** | `action` | `open-world` | Creates a new watchlist in Questrade. |
| 24 | **Edit Watchlist** | `action` | `open-world` | Adds or removes tickers from an existing Questrade watchlist. |

---

## 3. Server Configuration

- **MCP Server URL**: `https://mcp.questrade.com/v1/brokerage/mcp`
- **Transport**: HTTP / Server-Sent Events (SSE)

### Setup in Claude Code:
```bash
claude mcp add --transport http questrade https://mcp.questrade.com/v1/brokerage/mcp
```
*Run `/mcp` -> `questrade` -> `Log in` to authorize via browser OAuth.*

---

## 4. Architectural Relationship to InvestmentToolkit
- **Broker-Assisted Workflow**: Directly supports multi-account management (TFSA + RRSP cash sourcing, PSU-U.TO rebalancing).
- **Rule #17 Compliance**: 100% compliant with `.agent/rules/trade-execution-policy.md` because `Create Order Instruction` strictly requires mobile Push Approval before hitting the market.
