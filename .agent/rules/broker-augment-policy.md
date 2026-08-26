---
description: Architectural policy establishing TradingView as the universal baseline and broker-specific MCPs as optional, non-breaking augments.
globs: ["plugins/**", "investment_screener/**", ".agent/**"]
---

# Broker Integration & Augment Policy

## 1. TradingView as the Universal Baseline
- **Universal Standard**: TradingView Desktop (running on CDP port 9222) is the primary, universal foundation of the InvestmentToolkit suite.
- **Core Coverage**: All real-time sub-second price discovery, technical indicator computations, batch daily TA sweeps (`/ta-daily-sweep`), alert reconciliations, and visual chart controls are natively powered via TradingView CDP.
- **Broker Independence**: The core repository and dashboard function 100% independently of any specific brokerage account.

## 2. Broker MCPs as Optional Augments
- **Role**: Specific brokerage plugins (such as `plugins/questrade`) are optional convenience extensions designed specifically for users of those brokerages.
- **Scope of Augment**:
  1. Direct chat inspection of multi-account CAD/USD cash balances.
  2. Direct chat inspection of open position share quantities and cost bases.
  3. Direct review of 90-day cash flow ledger events (dividends, interest, deposits).
  4. Human-in-the-Loop (HITL) order drafting with mobile Push Approval.
- **Zero Core Dependency**:
  - Core application routes, Python services, and SQLite database models must **NEVER** hardcode dependencies on optional broker plugins.
  - Non-users of a given broker must experience zero degraded functionality in the core suite.
