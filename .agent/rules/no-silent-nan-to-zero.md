---
description: Missing or NaN financial data must never silently become $0 in a monetary calculation.
globs: ["investment_screener/backend/py_services/*.py", "plugins/**/scripts/*.py"]
---

# No Silent NaN → $0 in Financial Calculations

## The Problem This Rule Solves

`portfolio_performance.py` computed 1d/1w/1m portfolio returns via
`safe_float(price)`, which converted any `NaN` price to `0.0`. On 2026-07-02,
PSU-U.TO (TSX-listed) had no trading data for 2026-07-01 (Canada Day — TSX
closed, all US tickers traded normally). `safe_float(NaN)` silently zeroed out
an ~$8,000 position's contribution to *yesterday's* portfolio total, producing
a reported **+29.79% single-day gain** on the live dashboard — a number a user
caught immediately as impossible, but a smaller version of this exact bug
(a thinly-traded or foreign-exchange-listed ticker missing one day of data)
could easily have gone unnoticed and quietly corrupted a real trading decision.

**The general failure mode**: any code that maps `NaN`/`None`/missing → `0` for
a price, market value, or account balance is asserting "this position is
worth nothing today" — almost never true, and the error compounds silently
because `0.0` is a valid float, not an exception.

## The Law

> **A missing price is missing data, not a zero-dollar valuation.** Forward-fill
> from the last known price (or explicitly exclude/flag the position), and
> never let `NaN`-coalescing hide inside a generic "safe" numeric helper that
> gets reused across both display formatting (where 0 may be fine) and
> financial totals (where it is never fine).

## Non-Negotiables

1. **Forward-fill time series before computing point-in-time totals.**
   When reading historical price data (`yfinance`, TV CDP, or any batched
   source) for a *comparison* calculation (day/week/month change), call
   `.ffill()` (or equivalent) on the full series *before* selecting any
   single row — never after. See `portfolio_performance.py::compute_performance()`
   for the reference pattern.

2. **Known holiday/closure calendars are not edge cases — expect them.**
   TSX-listed tickers (`PSU-U.TO`, etc.) will have gaps on Canadian holidays
   even when NYSE/NASDAQ tickers in the same batch trade normally. Any
   multi-exchange batch price fetch must assume misaligned trading calendars
   as the normal case, not a rare exception.

3. **Separate "display default" from "financial total" NaN handling.**
   A generic `safe_float()`-style helper that returns `0.0` for `NaN` is fine
   for UI display fallbacks (e.g. "show $0 flags instead of crashing"). It is
   **not** fine to reuse that same helper inside a sum that becomes a
   portfolio total, a weight denominator, or a return percentage. If a
   function's output ever gets summed into a dollar total, missing data must
   be forward-filled or the position excluded — not zeroed.

4. **New financial-calculation code touching price series requires a test with
   an injected gap.** Per `.agent/rules/test-driven-development.md`, any new
   function that sums `shares * price` across a time series must have a test
   case where at least one ticker has a `NaN`/missing value on a middle date,
   asserting the result reflects the last known price — not zero, and not a
   wildly inflated change percentage. See
   `investment_screener/backend/tests/py_services/test_portfolio_performance.py`
   for the reference test shape.

5. **A single-day/week/month change beyond a sanity bound is a data-quality
   signal, not a fact.** Consider flagging (log a warning, or surface a
   `dataQualityFlag`) any computed period return whose magnitude exceeds a
   plausible bound (e.g. >15% in a single day for a diversified portfolio)
   rather than printing it as-is — this is a cheap circuit breaker that would
   have caught this exact bug before it reached the dashboard.

## Where This Applies

- `portfolio_performance.py` — fixed 2026-07-02, reference implementation.
- Any future script that fetches batched historical price data across
  multiple exchanges/currencies (yfinance, TV CDP) and sums it into a total.
- `computeWeightsMap()` / `buildPortfolioSnapshot()` (TypeScript) — same
  principle applies if either is ever extended to consume time-series data
  instead of point-in-time snapshots.
