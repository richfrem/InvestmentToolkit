# 🤖 Pine Script™ v6 Agent Skill Definition & Workflow

**Purpose:** This document defines the execution pattern, strict best practices, and linting workflow for AI agents generating or reviewing TradingView Pine Script v6. It is designed to act as a structural memory layer (L2) reference.

---

## 1. 🔄 Core Agent Workflow
When tasked with creating, reviewing, or translating code into Pine Script v6, follow this execution loop:

1. **Determine Script Type:** Force `//@version=6` at the top. Choose exactly one declaration: `indicator()`, `strategy()`, or `library()`.
2. **Group Configurations:** Declare all `input.*` variables early in the script to ensure UI grouping is consistent in the TradingView interface.
3. **Apply Repainting Safeguards:** Implement strict lookahead guidance (see Section 3). 
4. **Optimize State:** Use `var` and `varip` appropriately, precompute constants, and cap array sizes to avoid execution timeouts.
5. **Linting (Pre-Delivery):** If instructed, run `pinescript-lint` as a pre-validation step before handing the code off.

---

## 2. 🧠 State & Execution Model
Understanding TradingView's execution engine is critical. Scripts run once per historical bar update, but *realtime bars* can update multiple times per tick.

* **`var`:** Use for one-time initialization and persistent state across historical bars (e.g., drawing objects).
* **`varip`:** Use when tracking real-time updates within a single active bar.
* **Reassignment (`:=`):** Always prefer `:=` over recreating variables to preserve type stability.
* **Drawings:** *Never* recreate drawing objects (labels, lines) on every bar. Initialize them once with `var` and update their coordinates, or delete old ones explicitly.

---

## 3. 🛡️ Repainting & Lookahead Safety (Critical)
Agents must prevent logic that "repaints" (changes historical signals after the fact).

* **Confirmed Data:** Rely on confirmed data for trade signals. Use `barstate.isconfirmed` for close-only logic.
* **Offsets:** Use `[1]` offsets for confirmed values (e.g., `close[1]` instead of `close`).
* **Higher Timeframes (`request.security`):** Prevent future data leakage. 
  * *Safe:* `request.security(sym, tf, series[1], lookahead=barmerge.lookahead_on)`
  * *Alternative:* `request.security(sym, tf, series, lookahead=barmerge.lookahead_off)`
* **Order Logic:** Keep strategy entry/exit logic completely free of repainting values.

---

## 4. ⚙️ Generation & Determinism Rules
When generating Pine Script from other languages (like Python or TypeScript) or drafting architectural logic:

* **Deterministic Naming:** Generate highly deterministic and traceable names for plots, lines, and labels. This allows easy tracking of generator source elements during automated improvement loops.
* **Explicit Typing:** Always use explicit types for inputs (`input.int`, `input.float`, `input.bool`) to prevent compiler ambiguity.
* **Formatting:** Maintain consistent 4-space indentation. 
* **Defaults:** When building higher timeframe logic, always provide an option via `input` to override the default lookahead behavior.

---

## 5. 🧹 Linting & Validation
Pine Script compiles exclusively on TradingView servers, so static analysis catches structural problems before hitting the TV compiler.

* **Pre-Injection Lint (required):** Run `pine_linter.py` before every inject attempt.
  * Command: `python3 plugins/tradingview/skills/author-pine-script/scripts/pine_linter.py <path>`
  * Exit 0 = pass (warnings are informational). Exit 1 = fail — fix errors before injecting.
* **What the linter catches:** missing `//@version=6`, duplicate or missing declarations, `request.security()` without `lookahead=`, boolean expressions in `na()`/`nz()`, drawing objects missing `var`/`varip`.
* **What it does NOT catch:** semantic logic errors, strategy profitability issues, runtime execution errors. Those surface in TradingView's Pine Editor after injection.
* **After injection:** If the TV compiler still rejects the script, treat the error message as the authoritative signal and fix + re-lint before retrying (max 3 attempts).
