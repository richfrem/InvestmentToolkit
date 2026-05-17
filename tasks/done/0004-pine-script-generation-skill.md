3# 0004: Pine Script AI Generation Skill

## Objective
Create a dedicated Pine Script generation and analysis skill within our agent framework. This skill should have deep understanding and awareness of Pine Script v6, enabling it to write, read, and analyze TradingView custom indicators and strategies.

## Context & References
Pine Script v6 is the latest version of TradingView's domain-specific programming language used to build custom indicators and trading strategies. 

**Key References:**
- [Pine Script® v6 User Manual](https://www.tradingview.com/pine-script-docs)
- [Pine Script® v6 Reference Manual](https://www.tradingview.com/pine-script-reference/v6/)

**Core Concepts:**
- **Execution Model:** Scripts execute on a time-series model (bar-by-bar from left to right). `close`, `high`, `low`, etc., return the current bar's values. Historical values are referenced using the `[]` operator (e.g., `close[1]`).
- **Indicators vs Strategies:**
  - **Indicators (`indicator()`):** Focus on technical calculations and visual plotting. Cannot backtest or simulate broker orders. They are lightweight and fast.
  - **Strategies (`strategy()`):** Incorporate order execution logic (`strategy.entry`, `strategy.close`) to simulate trades. Used for historical backtesting and forward testing with the built-in broker emulator.
- **Built-in Functions:** Leverage built-ins like `ta.ema()`, `ta.macd()` over manual calculations to optimize performance.
- **Advanced Types:** v6 includes user-defined types (objects, methods), maps, matrices, arrays, and a strict type system distinguishing between `series` (changing per bar) and `simple` (constant after bar 0).

## Expected Capabilities
1. Generate complete, syntactically correct Pine Script v6 indicators and strategies from natural language descriptions.
2. Review and modernize legacy Pine Script code (v4/v5) to the new v6 standard.
3. Understand the difference between `indicator()` and `strategy()` constructs to properly route user requests.
4. Interface with the planned Phase 2 Pine Script injection via TradingView CDP (Chrome DevTools Protocol).