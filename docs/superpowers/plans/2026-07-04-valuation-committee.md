# Valuation Committee (Phase 2a) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the single flat-10%-discount-rate DCF signal with four independent valuation lenses (WACC-adjusted DCF, reverse-DCF implied growth, sensitivity/Monte Carlo, peer comps), gated behind a 2-of-3 lens-agreement rule before `aiThesis.action` can be `ACCUMULATE`.

**Architecture:** Four new single-purpose CLI scripts (`wacc.py`, `reverse_dcf.py`, `dcf_sensitivity.py`, `comps_valuation.py`) live canonically in `plugins/stock-valuation/scripts/`, symlinked into `investment_screener/backend/py_services/` and `plugins/stock-valuation/skills/stock_valuation/scripts/` — the same pattern already used for `dcf_scenarios.py`. `market_data.py`'s `get_fundamentals()` waterfall gains three yfinance-only fields (`totalDebt`, `cashAndEquivalents`, `interestExpense`) that `wacc.py` and `comps_valuation.py` both depend on. `validate_projection.py` gains a gate function enforcing lens agreement. All outputs land in `projections/{TICKER}.json`'s existing `analyticsLog` (already untyped passthrough — no schema migration needed).

**Tech Stack:** Python 3.11, `numpy` (already in `requirements.in`), `pytest`. No new dependencies, no frontend/TypeScript changes.

## Global Constraints

- **TDD, failing test first, every script** (CLAUDE.md rule 1) — every task below writes the test before the implementation.
- **No inline Python math** (CLAUDE.md rule 2) — all valuation math lives in the versioned scripts below, never computed ad hoc.
- **Google-style docstrings, type hints, snake_case** (CLAUDE.md rule 3).
- **Symlinks ONLY via `symlink_manager.py`, never raw `ln -s`** (CLAUDE.md rule 5) — every new script needs two symlinks created this way (see Task 2's Step 5 for the exact commands; Tasks 3–5 repeat the same pattern).
- **Backend-only phase** — no frontend/TypeScript work. `dcf_scenarios.py`'s `compute_scenario()` function signature and math are unchanged (only the CLI-layer discount-rate resolution changes), so the existing cross-language parity mirror (`investment_screener/frontend/src/utils/valuationMath.ts`) and `investment_screener/backend/tests/py_services/test_math_parity.py` remain valid untouched.
- **Test locations:** `wacc.py`, `reverse_dcf.py`, `dcf_sensitivity.py`, `comps_valuation.py`, and the `dcf_scenarios.py`/`market_data.py` extensions are tested under `investment_screener/backend/tests/py_services/` — this matches the existing precedent for this specific DCF-adjacent script family (`dcf_scenarios.py` is tested there via `test_math_parity.py`, and `market_data.py` is tested there directly), even though the scripts themselves canonically live under `plugins/stock-valuation/scripts/`. `validate_projection.py` has no such precedent, so its tests follow CLAUDE.md's general "Plugin scripts → `plugins/<plugin>/tests/`" rule, at `plugins/stock-valuation/tests/`.
- **`projections/*.json` are git-tracked, not gitignored** — safe to edit directly as part of this work (unlike `portfolio.json`/`target-portfolio.json`, which are gitignored user data and off-limits without explicit approval).
- **Run `python3 run_tests.py` before every commit** that touches a symlinked file, to catch symlink/path regressions early.

---

### Task 1: `market_data.py` — add `totalDebt`, `cashAndEquivalents`, `interestExpense`

**Files:**
- Modify: `investment_screener/backend/py_services/market_data.py:242-245`, `:460-468`
- Test: `investment_screener/backend/tests/py_services/test_market_data_fundamentals.py` (append)

**Interfaces:**
- Consumes: nothing new — extends the existing `get_fundamentals(ticker, cik=None) -> dict` waterfall.
- Produces: `get_fundamentals()` result dict may now include `"totalDebt"`, `"cashAndEquivalents"`, `"interestExpense"` keys, each shaped `{"value": float, "source": "yfinance", "asOf": iso_str}`. Tasks 2 and 5 (`wacc.py`, `comps_valuation.py`) read these keys.

- [ ] **Step 1: Write the failing tests**

Append to `investment_screener/backend/tests/py_services/test_market_data_fundamentals.py`:

```python
def test_get_fundamentals_includes_debt_cash_interest_from_yfinance(tmp_path, monkeypatch):
    monkeypatch.setattr("cache.CACHE_DIR", tmp_path)
    fake_yf = MagicMock()
    fake_yf.info = {
        "totalRevenue": 395000000000.0,
        "netIncomeToCommon": 94000000000.0,
        "totalDebt": 120000000000.0,
        "totalCash": 65000000000.0,
        "interestExpense": 3900000000.0,
    }
    fake_yf.financials = _fake_yf_financials_df()
    with patch("market_data.get_company_facts", return_value=_fake_edgar_facts()), \
         patch("market_data.yf.Ticker", return_value=fake_yf):
        result = get_fundamentals("AAPL", cik="0000320193")

    assert result["totalDebt"]["value"] == 120000000000.0
    assert result["totalDebt"]["source"] == "yfinance"
    assert result["cashAndEquivalents"]["value"] == 65000000000.0
    assert result["cashAndEquivalents"]["source"] == "yfinance"
    assert result["interestExpense"]["value"] == 3900000000.0
    assert result["interestExpense"]["source"] == "yfinance"


def test_get_fundamentals_omits_debt_cash_interest_when_yfinance_lacks_them(tmp_path, monkeypatch):
    monkeypatch.setattr("cache.CACHE_DIR", tmp_path)
    fake_yf = MagicMock()
    fake_yf.info = {"totalRevenue": 395000000000.0, "netIncomeToCommon": 94000000000.0}
    fake_yf.financials = _fake_yf_financials_df()
    with patch("market_data.get_company_facts", return_value=_fake_edgar_facts()), \
         patch("market_data.yf.Ticker", return_value=fake_yf):
        result = get_fundamentals("AAPL", cik="0000320193")

    assert "totalDebt" not in result
    assert "cashAndEquivalents" not in result
    assert "interestExpense" not in result
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_market_data_fundamentals.py -v -k "debt_cash_interest"`
Expected: FAIL — `KeyError: 'totalDebt'` (first test) and the second test currently passes trivially since the keys already don't exist, but run both to confirm the first one fails.

- [ ] **Step 3: Add the yfinance-only field map**

Modify `investment_screener/backend/py_services/market_data.py:242-245` — the existing block:

```python
_YF_FUNDAMENTALS_FIELDS = {
    "revenue": "totalRevenue",
    "netIncome": "netIncomeToCommon",
}
```

becomes:

```python
_YF_FUNDAMENTALS_FIELDS = {
    "revenue": "totalRevenue",
    "netIncome": "netIncomeToCommon",
}

# Balance-sheet/income-statement fields with no EDGAR tag mapping in this
# pass — yfinance-only, a deliberate scope boundary (the inverse of
# operatingIncome's EDGAR-only boundary below). Needed by wacc.py (cost of
# debt, capital-structure weighting) and comps_valuation.py (enterprise value).
_YF_ONLY_FUNDAMENTALS_FIELDS = {
    "totalDebt": "totalDebt",
    "cashAndEquivalents": "totalCash",
    "interestExpense": "interestExpense",
}
```

- [ ] **Step 4: Populate the new fields in `get_fundamentals()`**

Modify `investment_screener/backend/py_services/market_data.py:460-468` — the existing block:

```python
    # operatingIncome: EDGAR-only for this pass (see docstring for rationale).
    operating_field = edgar.get("operatingIncome")
    operating_value = _safe_float(operating_field.get("value")) if operating_field else None
    if operating_value is not None:
        result["operatingIncome"] = {
            "value": operating_value,
            "source": "edgar",
            "asOf": operating_field.get("asOf"),
        }
```

becomes:

```python
    # operatingIncome: EDGAR-only for this pass (see docstring for rationale).
    operating_field = edgar.get("operatingIncome")
    operating_value = _safe_float(operating_field.get("value")) if operating_field else None
    if operating_value is not None:
        result["operatingIncome"] = {
            "value": operating_value,
            "source": "edgar",
            "asOf": operating_field.get("asOf"),
        }

    # totalDebt / cashAndEquivalents / interestExpense: yfinance-only for this
    # pass (see _YF_ONLY_FUNDAMENTALS_FIELDS comment) — a metric absent from
    # yfinance is simply omitted, never zeroed.
    for metric, yf_key in _YF_ONLY_FUNDAMENTALS_FIELDS.items():
        yf_value = _safe_float(yf_info.get(yf_key))
        if yf_value is not None:
            result[metric] = {"value": yf_value, "source": "yfinance", "asOf": _now_iso()}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_market_data_fundamentals.py -v`
Expected: PASS — all tests, including the two new ones and every pre-existing test in the file (regression check).

- [ ] **Step 6: Commit**

```bash
git add investment_screener/backend/py_services/market_data.py investment_screener/backend/tests/py_services/test_market_data_fundamentals.py
git commit -m "feat: add totalDebt/cashAndEquivalents/interestExpense to market_data.get_fundamentals()"
```

---

### Task 2: `wacc.py` — per-company weighted average cost of capital

**Files:**
- Create: `plugins/stock-valuation/scripts/wacc.py`
- Test: `investment_screener/backend/tests/py_services/test_wacc.py`

**Interfaces:**
- Consumes: `market_data.get_prices(tickers, period, interval) -> dict[str, dict]` (Task 1 unchanged), `market_data.get_fundamentals(ticker, cik=None) -> dict` (Task 1, now includes `totalDebt`/`interestExpense`).
- Produces: `compute_wacc(ticker, market_cap, cik=None, erp=0.045, tax_rate=0.21, beta_override=None, cost_of_debt_override=None) -> dict` returning `{"wacc", "riskFreeRate", "beta", "erp", "costOfDebt", "capApplied", "floorApplied", "betaWarning", "source": {...}}`. Task 6 (`dcf_scenarios.py --wacc-file`) consumes the `"wacc"` key from this function's JSON CLI output.

- [ ] **Step 1: Write the failing tests**

Create `investment_screener/backend/tests/py_services/test_wacc.py`:

```python
import math
import random
import sys
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from wacc import (  # noqa: E402
    compute_beta,
    compute_cost_of_debt,
    compute_risk_free_rate,
    compute_wacc,
    WACC_CAP,
    WACC_FLOOR,
)


def _make_price_series(closes: list[float]) -> list[dict]:
    start = date(2024, 1, 1)
    return [{"date": (start + timedelta(days=i)).isoformat(), "close": c} for i, c in enumerate(closes)]


def _closes_from_returns(start_price: float, returns: list[float]) -> list[float]:
    closes = [start_price]
    for r in returns:
        closes.append(closes[-1] * math.exp(r))
    return closes


def test_compute_beta_matches_known_multiplier():
    random.seed(42)
    spy_returns = [random.uniform(-0.02, 0.02) for _ in range(40)]
    ticker_returns = [2 * r for r in spy_returns]
    spy_prices = _make_price_series(_closes_from_returns(100.0, spy_returns))
    ticker_prices = _make_price_series(_closes_from_returns(50.0, ticker_returns))

    result = compute_beta(ticker_prices, spy_prices)

    assert result["usedFallback"] is False
    assert abs(result["beta"] - 2.0) < 0.05


def test_compute_beta_falls_back_with_insufficient_history():
    spy_prices = _make_price_series([100.0, 101.0, 99.5, 100.5, 102.0])
    ticker_prices = _make_price_series([50.0, 50.5, 49.8, 50.2, 51.0])

    result = compute_beta(ticker_prices, spy_prices)

    assert result["usedFallback"] is True
    assert result["beta"] == 1.2


def test_compute_cost_of_debt_normal_case():
    result = compute_cost_of_debt(interest_expense=50_000_000.0, total_debt=1_000_000_000.0, tax_rate=0.21)
    assert result["costOfDebt"] == 0.0395
    assert result["usedFallback"] is False


def test_compute_cost_of_debt_missing_total_debt_falls_back():
    result = compute_cost_of_debt(interest_expense=50_000_000.0, total_debt=None)
    assert result["usedFallback"] is True
    assert result["costOfDebt"] == 0.05


def test_compute_cost_of_debt_zero_total_debt_falls_back():
    result = compute_cost_of_debt(interest_expense=50_000_000.0, total_debt=0.0)
    assert result["usedFallback"] is True


def test_compute_risk_free_rate_divides_tnx_close_correctly():
    with patch("wacc.get_prices", return_value={
        "^TNX": {"data": [{"date": "2026-07-01", "close": 42.79}], "source": "yfinance", "asOf": "x"}
    }):
        result = compute_risk_free_rate()
    assert result["riskFreeRate"] == 0.04279
    assert result["usedFallback"] is False


def test_compute_risk_free_rate_falls_back_when_no_data():
    with patch("wacc.get_prices", return_value={}):
        result = compute_risk_free_rate()
    assert result["usedFallback"] is True
    assert result["riskFreeRate"] == 0.04


def test_compute_wacc_uses_overrides_and_returns_source_decomposition():
    with patch("wacc.compute_risk_free_rate", return_value={"riskFreeRate": 0.04, "usedFallback": False}), \
         patch("wacc.get_fundamentals", return_value={}):
        result = compute_wacc(
            ticker="TESTCO", market_cap=1_000_000_000.0,
            beta_override=1.0, cost_of_debt_override=0.03,
        )
    assert result["source"]["beta"] == "override"
    assert result["source"]["costOfDebt"] == "override"
    assert result["betaWarning"] is None


def test_compute_wacc_incorporates_debt_weighting():
    with patch("wacc.compute_risk_free_rate", return_value={"riskFreeRate": 0.04, "usedFallback": False}), \
         patch("wacc.get_fundamentals", return_value={
             "totalDebt": {"value": 200_000_000.0, "source": "yfinance", "asOf": "x"}
         }):
        result = compute_wacc(
            ticker="TESTCO", market_cap=800_000_000.0, erp=0.06,
            beta_override=1.0, cost_of_debt_override=0.05,
        )
    # cost_of_equity = 0.04 + 1.0*0.06 = 0.10; equity_weight=800/1000=0.8, debt_weight=0.2
    # wacc = 0.8*0.10 + 0.2*0.05 = 0.09
    assert result["wacc"] == 0.09
    assert result["capApplied"] is False
    assert result["floorApplied"] is False


def test_compute_wacc_caps_at_upper_bound():
    with patch("wacc.compute_risk_free_rate", return_value={"riskFreeRate": 0.04, "usedFallback": False}), \
         patch("wacc.get_fundamentals", return_value={}):
        result = compute_wacc(
            ticker="TESTCO", market_cap=1_000_000_000.0,
            beta_override=5.0, cost_of_debt_override=0.05, erp=0.045,
        )
    assert result["capApplied"] is True
    assert result["wacc"] == WACC_CAP
    assert result["betaWarning"] is not None


def test_compute_wacc_floors_at_lower_bound():
    with patch("wacc.compute_risk_free_rate", return_value={"riskFreeRate": 0.01, "usedFallback": False}), \
         patch("wacc.get_fundamentals", return_value={}):
        result = compute_wacc(
            ticker="TESTCO", market_cap=1_000_000_000.0,
            beta_override=0.1, cost_of_debt_override=0.01, erp=0.02,
        )
    assert result["floorApplied"] is True
    assert result["wacc"] == WACC_FLOOR
    assert result["betaWarning"] is not None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_wacc.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'wacc'`

- [ ] **Step 3: Write `plugins/stock-valuation/scripts/wacc.py`**

```python
#!/usr/bin/env python3
"""
wacc.py (Python Service)
=====================================

Purpose:
    Compute a per-company weighted average cost of capital (WACC) to replace
    dcf_scenarios.py's flat 10% discount-rate default with a risk-adjusted
    rate: risk-free rate (10Y Treasury), levered beta (local OLS regression
    vs SPY), equity risk premium, and after-tax cost of debt, weighted by
    market-cap/debt capital structure.

Layer: Backend / Python Services / Valuation Math

Usage:
    python3 wacc.py --ticker NVDA --market-cap 3200000000000 --cik 0001045810 --pretty
    python3 wacc.py --ticker NVDA --market-cap 3200000000000 --beta 1.8 --cost-of-debt 0.04

Key Functions:
    - compute_beta() - Local OLS slope of ticker log returns vs SPY log returns
    - compute_cost_of_debt() - After-tax cost of debt from interest expense / total debt
    - compute_risk_free_rate() - 10Y Treasury yield via market_data.get_prices(["^TNX"])
    - compute_wacc() - Primary orchestrator: combines all inputs into a capped/floored WACC
"""

import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from market_data import get_prices, get_fundamentals  # noqa: E402

WACC_FLOOR = 0.07
WACC_CAP = 0.14
DEFAULT_ERP = 0.045
DEFAULT_TAX_RATE = 0.21
FALLBACK_BETA = 1.2
FALLBACK_COST_OF_DEBT = 0.05
FALLBACK_RISK_FREE_RATE = 0.04
MIN_REGRESSION_OBSERVATIONS = 30


def compute_beta(ticker_prices: list[dict], spy_prices: list[dict]) -> dict:
    """Compute levered beta via OLS slope of ticker log returns vs SPY log returns.

    Args:
        ticker_prices: List of {"date","close",...} dicts (from market_data.get_prices()).
        spy_prices: Same shape, for SPY.

    Returns:
        {"beta": float, "usedFallback": bool, "nObservations": int}. Falls back
        to a fixed sector-average beta (never a garbage regression result) when
        fewer than 30 overlapping daily return observations are available —
        e.g. a recent IPO with no 2-year price history.
    """
    ticker_by_date = {row["date"]: row["close"] for row in ticker_prices}
    spy_by_date = {row["date"]: row["close"] for row in spy_prices}
    common_dates = sorted(set(ticker_by_date) & set(spy_by_date))

    ticker_closes = [ticker_by_date[d] for d in common_dates]
    spy_closes = [spy_by_date[d] for d in common_dates]

    ticker_returns = [
        math.log(ticker_closes[i] / ticker_closes[i - 1])
        for i in range(1, len(ticker_closes))
        if ticker_closes[i - 1] > 0 and ticker_closes[i] > 0
    ]
    spy_returns = [
        math.log(spy_closes[i] / spy_closes[i - 1])
        for i in range(1, len(spy_closes))
        if spy_closes[i - 1] > 0 and spy_closes[i] > 0
    ]

    n = min(len(ticker_returns), len(spy_returns))
    if n < MIN_REGRESSION_OBSERVATIONS:
        return {"beta": FALLBACK_BETA, "usedFallback": True, "nObservations": n}

    ticker_returns = ticker_returns[-n:]
    spy_returns = spy_returns[-n:]

    spy_mean = sum(spy_returns) / n
    ticker_mean = sum(ticker_returns) / n
    covariance = sum(
        (spy_returns[i] - spy_mean) * (ticker_returns[i] - ticker_mean) for i in range(n)
    ) / n
    variance = sum((r - spy_mean) ** 2 for r in spy_returns) / n

    if variance == 0:
        return {"beta": FALLBACK_BETA, "usedFallback": True, "nObservations": n}

    return {"beta": round(covariance / variance, 3), "usedFallback": False, "nObservations": n}


def compute_cost_of_debt(
    interest_expense: float | None, total_debt: float | None, tax_rate: float = DEFAULT_TAX_RATE
) -> dict:
    """After-tax cost of debt: interest_expense / total_debt * (1 - tax_rate).

    Returns:
        {"costOfDebt": float, "usedFallback": bool}. Falls back to a fixed
        5% pre-tax-equivalent estimate when debt or interest data is
        missing/zero — never divides by zero, never fabricates from partial data.
    """
    if not interest_expense or not total_debt or total_debt <= 0:
        return {"costOfDebt": FALLBACK_COST_OF_DEBT, "usedFallback": True}
    pre_tax = interest_expense / total_debt
    return {"costOfDebt": round(pre_tax * (1 - tax_rate), 4), "usedFallback": False}


def compute_risk_free_rate() -> dict:
    """Fetch the 10Y Treasury yield via market_data.get_prices(["^TNX"]).

    Yahoo Finance quotes ^TNX as the yield * 10 (e.g. close 42.79 = 4.279%
    yield = 0.04279 as a decimal fraction). Falls back to a fixed 4.0%
    estimate if no fresh quote is available.
    """
    prices = get_prices(["^TNX"], period="5d")
    rows = prices.get("^TNX", {}).get("data", [])
    if not rows:
        return {"riskFreeRate": FALLBACK_RISK_FREE_RATE, "usedFallback": True}
    latest_close = rows[-1]["close"]
    return {"riskFreeRate": round(latest_close / 1000, 5), "usedFallback": False}


def compute_wacc(
    ticker: str,
    market_cap: float,
    cik: str | None = None,
    erp: float = DEFAULT_ERP,
    tax_rate: float = DEFAULT_TAX_RATE,
    beta_override: float | None = None,
    cost_of_debt_override: float | None = None,
) -> dict:
    """Compute per-company WACC from risk-free rate, beta, ERP, and after-tax cost of debt.

    Capital structure weighting uses market_cap (equity) and totalDebt (debt)
    from market_data.get_fundamentals(). Result is capped/floored to
    [WACC_FLOOR, WACC_CAP] — pre-revenue/illiquid names can otherwise produce
    a garbage beta and an unusable discount rate.

    Args:
        ticker: Ticker symbol.
        market_cap: Equity market cap in dollars (caller-supplied — already
            computed upstream in the /evaluate-stock pipeline).
        cik: SEC CIK for EDGAR lookups in get_fundamentals(), or None.
        erp: Equity risk premium (decimal), default 4.5%.
        tax_rate: Marginal tax rate for the after-tax cost of debt, default 21%.
        beta_override: Skip the OLS regression and use this beta directly.
        cost_of_debt_override: Skip the fundamentals-derived cost of debt.

    Returns:
        {"wacc", "riskFreeRate", "beta", "erp", "costOfDebt", "capApplied",
         "floorApplied", "betaWarning", "source": {"riskFree","beta","costOfDebt"}}
    """
    rf = compute_risk_free_rate()

    if beta_override is not None:
        beta_result = {"beta": beta_override, "usedFallback": False}
    else:
        prices = get_prices([ticker, "SPY"], period="2y", interval="1d")
        beta_result = compute_beta(
            prices.get(ticker, {}).get("data", []),
            prices.get("SPY", {}).get("data", []),
        )

    fundamentals = get_fundamentals(ticker, cik=cik)
    total_debt = fundamentals.get("totalDebt", {}).get("value") or 0.0

    if cost_of_debt_override is not None:
        cod_result = {"costOfDebt": cost_of_debt_override, "usedFallback": False}
    else:
        interest_expense = fundamentals.get("interestExpense", {}).get("value")
        cod_result = compute_cost_of_debt(interest_expense, total_debt, tax_rate)

    beta = beta_result["beta"]
    cost_of_equity = rf["riskFreeRate"] + beta * erp

    total_value = market_cap + total_debt
    equity_weight = market_cap / total_value if total_value > 0 else 1.0
    debt_weight = 1.0 - equity_weight

    raw_wacc = equity_weight * cost_of_equity + debt_weight * cod_result["costOfDebt"]

    beta_warning = None
    if beta > 2.5 or beta < 0.2:
        beta_warning = f"beta {beta} outside typical range [0.2, 2.5] — pre-revenue or illiquid name?"

    cap_applied = raw_wacc > WACC_CAP
    floor_applied = raw_wacc < WACC_FLOOR
    final_wacc = min(max(raw_wacc, WACC_FLOOR), WACC_CAP)

    return {
        "wacc": round(final_wacc, 4),
        "riskFreeRate": rf["riskFreeRate"],
        "beta": beta,
        "erp": erp,
        "costOfDebt": cod_result["costOfDebt"],
        "capApplied": cap_applied,
        "floorApplied": floor_applied,
        "betaWarning": beta_warning,
        "source": {
            "riskFree": "fallback" if rf["usedFallback"] else "market_data:^TNX",
            "beta": "override" if beta_override is not None else (
                "fallback_sector_average" if beta_result["usedFallback"] else "local_ols_2y"
            ),
            "costOfDebt": "override" if cost_of_debt_override is not None else (
                "fallback" if cod_result["usedFallback"] else "market_data:get_fundamentals"
            ),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Per-company WACC calculator")
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--market-cap", type=float, required=True, help="Equity market cap in dollars")
    parser.add_argument("--cik", default=None, help="SEC CIK, omit for non-US tickers")
    parser.add_argument("--erp", type=float, default=DEFAULT_ERP)
    parser.add_argument("--tax-rate", type=float, default=DEFAULT_TAX_RATE)
    parser.add_argument("--beta", type=float, default=None, help="Override computed beta")
    parser.add_argument("--cost-of-debt", type=float, default=None, help="Override computed after-tax cost of debt")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    result = compute_wacc(
        ticker=args.ticker,
        market_cap=args.market_cap,
        cik=args.cik,
        erp=args.erp,
        tax_rate=args.tax_rate,
        beta_override=args.beta,
        cost_of_debt_override=args.cost_of_debt,
    )
    print(json.dumps(result, indent=2 if args.pretty else None))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_wacc.py -v`
Expected: PASS — all 10 tests.

- [ ] **Step 5: Create the two symlinks via `symlink_manager.py`**

Run from repo root:

```bash
python3 .agents/skills/symlink-manager/scripts/symlink_manager.py create \
  --src plugins/stock-valuation/scripts/wacc.py \
  --dst investment_screener/backend/py_services/wacc.py \
  --description "wacc.py canonical in plugin/scripts; py_services/ symlink for agent convenience"

python3 .agents/skills/symlink-manager/scripts/symlink_manager.py create \
  --src plugins/stock-valuation/scripts/wacc.py \
  --dst plugins/stock-valuation/skills/stock_valuation/scripts/wacc.py \
  --description "ADR-003: skill scripts/ symlink -> plugin root scripts/"
```

Verify: `ls -la investment_screener/backend/py_services/wacc.py plugins/stock-valuation/skills/stock_valuation/scripts/wacc.py` — both should show `->` symlink targets.

- [ ] **Step 6: Re-run the test suite through the symlink to confirm it resolves identically**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_wacc.py -v`
Expected: PASS (unchanged — `sys.path.insert` points at `py_services/`, which now contains the symlink).

- [ ] **Step 7: Commit**

```bash
git add plugins/stock-valuation/scripts/wacc.py investment_screener/backend/py_services/wacc.py \
  plugins/stock-valuation/skills/stock_valuation/scripts/wacc.py \
  investment_screener/backend/tests/py_services/test_wacc.py symlinks.json
git commit -m "feat: add wacc.py per-company discount rate calculator"
```

---

### Task 3: `reverse_dcf.py` — implied growth via bisection

**Files:**
- Create: `plugins/stock-valuation/scripts/reverse_dcf.py`
- Test: `investment_screener/backend/tests/py_services/test_reverse_dcf.py`

**Interfaces:**
- Consumes: `compute_scenario(base_revenue, base_shares, discount_rate, horizon, params) -> dict` from `dcf_scenarios.py` (existing, unchanged — see `investment_screener/backend/py_services/dcf_scenarios.py:40-80`).
- Produces: `solve_implied_growth(price, base_shares, discount_rate, horizon, margin, exit_pe, quality_multiplier, base_revenue, bear_growth, base_growth, bull_growth, guided_growth=None, share_change=0.0, weight=1.0, optionality_adjustment=0.0) -> dict` returning `{"impliedGrowth", "impliedGrowthVsBaseCase", "impliedGrowthVsGuidance", "verdict", "converged", "iterations"}`. Task 7's gate (`check_accumulate_gate`) reads `impliedGrowthVsBaseCase` from this output once persisted to `analyticsLog.reverseDcf`.

- [ ] **Step 1: Write the failing tests**

Create `investment_screener/backend/tests/py_services/test_reverse_dcf.py`:

```python
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from dcf_scenarios import compute_scenario  # noqa: E402
from reverse_dcf import solve_implied_growth  # noqa: E402

BASE_PARAMS = {
    "weight": 1.0, "netMargin": 25.0, "exitPE": 30.0,
    "qualityMultiplier": 1.0, "shareChange": 0.0,
}


def _pv_for_growth(growth: float) -> float:
    return compute_scenario(
        base_revenue=1_000_000_000.0, base_shares=100_000_000.0,
        discount_rate=0.10, horizon=5,
        params={**BASE_PARAMS, "growthRate": growth},
    )["presentValue"]


def test_reverse_dcf_recovers_input_growth_within_tolerance():
    price = _pv_for_growth(22.0)

    result = solve_implied_growth(
        price=price, base_shares=100_000_000.0, discount_rate=0.10, horizon=5,
        margin=25.0, exit_pe=30.0, quality_multiplier=1.0, base_revenue=1_000_000_000.0,
        bear_growth=10.0, base_growth=22.0, bull_growth=35.0,
    )

    assert result["converged"] is True
    assert abs(result["impliedGrowth"] - 22.0) < 0.1


def test_reverse_dcf_verdict_below_bear_when_price_under_bear_pv():
    price = _pv_for_growth(10.0) * 0.9

    result = solve_implied_growth(
        price=price, base_shares=100_000_000.0, discount_rate=0.10, horizon=5,
        margin=25.0, exit_pe=30.0, quality_multiplier=1.0, base_revenue=1_000_000_000.0,
        bear_growth=10.0, base_growth=22.0, bull_growth=35.0,
    )

    assert result["verdict"] == "BELOW_BEAR"
    assert result["converged"] is True


def test_reverse_dcf_verdict_between_base_and_bull():
    price = (_pv_for_growth(22.0) + _pv_for_growth(35.0)) / 2

    result = solve_implied_growth(
        price=price, base_shares=100_000_000.0, discount_rate=0.10, horizon=5,
        margin=25.0, exit_pe=30.0, quality_multiplier=1.0, base_revenue=1_000_000_000.0,
        bear_growth=10.0, base_growth=22.0, bull_growth=35.0,
    )

    assert result["verdict"] == "BETWEEN_BASE_AND_BULL"


def test_reverse_dcf_verdict_pricing_in_more_than_bull_when_price_over_bull_pv():
    price = _pv_for_growth(35.0) * 1.1

    result = solve_implied_growth(
        price=price, base_shares=100_000_000.0, discount_rate=0.10, horizon=5,
        margin=25.0, exit_pe=30.0, quality_multiplier=1.0, base_revenue=1_000_000_000.0,
        bear_growth=10.0, base_growth=22.0, bull_growth=35.0,
    )

    assert result["verdict"] == "PRICING_IN_MORE_THAN_BULL"


def test_reverse_dcf_out_of_bracket_range_returns_not_converged():
    result = solve_implied_growth(
        price=999_999_999_999.0, base_shares=100_000_000.0, discount_rate=0.10, horizon=5,
        margin=25.0, exit_pe=30.0, quality_multiplier=1.0, base_revenue=1_000_000_000.0,
        bear_growth=10.0, base_growth=22.0, bull_growth=35.0,
    )

    assert result["converged"] is False
    assert result["verdict"] == "OUT_OF_BRACKET_RANGE"
    assert result["impliedGrowth"] is None


def test_reverse_dcf_computes_vs_guidance_when_provided():
    price = _pv_for_growth(22.0)

    result = solve_implied_growth(
        price=price, base_shares=100_000_000.0, discount_rate=0.10, horizon=5,
        margin=25.0, exit_pe=30.0, quality_multiplier=1.0, base_revenue=1_000_000_000.0,
        bear_growth=10.0, base_growth=22.0, bull_growth=35.0, guided_growth=18.0,
    )

    assert result["impliedGrowthVsGuidance"] is not None
    assert abs(result["impliedGrowthVsGuidance"] - 4.0) < 0.1


def test_reverse_dcf_vs_guidance_is_none_when_not_provided():
    price = _pv_for_growth(22.0)

    result = solve_implied_growth(
        price=price, base_shares=100_000_000.0, discount_rate=0.10, horizon=5,
        margin=25.0, exit_pe=30.0, quality_multiplier=1.0, base_revenue=1_000_000_000.0,
        bear_growth=10.0, base_growth=22.0, bull_growth=35.0,
    )

    assert result["impliedGrowthVsGuidance"] is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_reverse_dcf.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'reverse_dcf'`

- [ ] **Step 3: Write `plugins/stock-valuation/scripts/reverse_dcf.py`**

```python
#!/usr/bin/env python3
"""
reverse_dcf.py (Python Service)
=====================================

Purpose:
    Invert dcf_scenarios.py's compute_scenario(): instead of "what is fair
    value given my growth guess," ask "what 5-year revenue CAGR is *priced
    in* at the current quote." Bisection-solves for the growth rate that
    reproduces the current price as presentValue, holding margin/exitPE/
    qualityMultiplier/shareChange fixed at the base-case values.

Layer: Backend / Python Services / Valuation Math

Usage:
    python3 reverse_dcf.py --price 185.50 --revenue 1000000000 --shares 100000000 \
        --margin 25 --exit-pe 30 --quality-multiplier 1.0 \
        --bear-growth 10 --base-growth 22 --bull-growth 35 --pretty

Key Functions:
    - solve_implied_growth() - Bisection solve + verdict classification (the
      round-trip inverse of dcf_scenarios.compute_scenario())
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dcf_scenarios import compute_scenario  # noqa: E402

BRACKET_LOW_GROWTH = -50.0
BRACKET_HIGH_GROWTH = 500.0
MAX_ITERATIONS = 200
RELATIVE_TOLERANCE = 1e-4


def solve_implied_growth(
    price: float,
    base_shares: float,
    discount_rate: float,
    horizon: int,
    margin: float,
    exit_pe: float,
    quality_multiplier: float,
    base_revenue: float,
    bear_growth: float,
    base_growth: float,
    bull_growth: float,
    guided_growth: float | None = None,
    share_change: float = 0.0,
    weight: float = 1.0,
    optionality_adjustment: float = 0.0,
) -> dict:
    """Bisection-solve the 5yr revenue CAGR the market is pricing in at `price`.

    Inverts compute_scenario(): holds margin, exitPE, qualityMultiplier,
    shareChange, discountRate, horizon fixed, and solves for the growthRate
    that reproduces `price` as presentValue. bear/base/bull growth define
    the verdict bands; guided_growth (company's own guidance) is optional.

    Returns:
        {"impliedGrowth": float | None, "impliedGrowthVsBaseCase": float | None,
         "impliedGrowthVsGuidance": float | None,
         "verdict": "PRICING_IN_MORE_THAN_BULL" | "BETWEEN_BASE_AND_BULL"
                   | "BETWEEN_BEAR_AND_BASE" | "BELOW_BEAR" | "OUT_OF_BRACKET_RANGE",
         "converged": bool, "iterations": int}
    """
    params = {
        "weight": weight, "netMargin": margin, "exitPE": exit_pe,
        "qualityMultiplier": quality_multiplier, "shareChange": share_change,
        "optionalityAdjustment": optionality_adjustment,
    }

    def pv_at(growth: float) -> float:
        trial = {**params, "growthRate": growth}
        return compute_scenario(base_revenue, base_shares, discount_rate, horizon, trial)["presentValue"]

    lo, hi = BRACKET_LOW_GROWTH, BRACKET_HIGH_GROWTH
    pv_lo, pv_hi = pv_at(lo), pv_at(hi)

    if price < pv_lo or price > pv_hi:
        return {
            "impliedGrowth": None, "impliedGrowthVsBaseCase": None,
            "impliedGrowthVsGuidance": None, "verdict": "OUT_OF_BRACKET_RANGE",
            "converged": False, "iterations": 0,
        }

    tolerance = RELATIVE_TOLERANCE * max(price, 1.0)
    iterations = 0
    mid = (lo + hi) / 2
    converged = False
    while iterations < MAX_ITERATIONS:
        mid = (lo + hi) / 2
        pv_mid = pv_at(mid)
        if abs(pv_mid - price) < tolerance:
            converged = True
            break
        if pv_mid < price:
            lo = mid
        else:
            hi = mid
        iterations += 1

    implied_growth = round(mid, 4)

    if implied_growth >= bull_growth:
        verdict = "PRICING_IN_MORE_THAN_BULL"
    elif implied_growth >= base_growth:
        verdict = "BETWEEN_BASE_AND_BULL"
    elif implied_growth >= bear_growth:
        verdict = "BETWEEN_BEAR_AND_BASE"
    else:
        verdict = "BELOW_BEAR"

    return {
        "impliedGrowth": implied_growth,
        "impliedGrowthVsBaseCase": round(implied_growth - base_growth, 4),
        "impliedGrowthVsGuidance": (
            round(implied_growth - guided_growth, 4) if guided_growth is not None else None
        ),
        "verdict": verdict,
        "converged": converged,
        "iterations": iterations,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Reverse-DCF implied growth solver")
    parser.add_argument("--price", type=float, required=True)
    parser.add_argument("--revenue", type=float, required=True, help="TTM base revenue in dollars")
    parser.add_argument("--shares", type=float, required=True)
    parser.add_argument("--margin", type=float, required=True, help="Base-case net margin, percent")
    parser.add_argument("--exit-pe", type=float, required=True)
    parser.add_argument("--quality-multiplier", type=float, default=1.0)
    parser.add_argument("--share-change", type=float, default=0.0)
    parser.add_argument("--discount-rate", type=float, default=0.10)
    parser.add_argument("--horizon", type=int, default=5)
    parser.add_argument("--bear-growth", type=float, required=True)
    parser.add_argument("--base-growth", type=float, required=True)
    parser.add_argument("--bull-growth", type=float, required=True)
    parser.add_argument("--guided-growth", type=float, default=None)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    result = solve_implied_growth(
        price=args.price, base_shares=args.shares, discount_rate=args.discount_rate,
        horizon=args.horizon, margin=args.margin, exit_pe=args.exit_pe,
        quality_multiplier=args.quality_multiplier, base_revenue=args.revenue,
        bear_growth=args.bear_growth, base_growth=args.base_growth, bull_growth=args.bull_growth,
        guided_growth=args.guided_growth, share_change=args.share_change,
    )
    print(json.dumps(result, indent=2 if args.pretty else None))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_reverse_dcf.py -v`
Expected: PASS — all 7 tests, including the round-trip property test.

- [ ] **Step 5: Create the two symlinks**

```bash
python3 .agents/skills/symlink-manager/scripts/symlink_manager.py create \
  --src plugins/stock-valuation/scripts/reverse_dcf.py \
  --dst investment_screener/backend/py_services/reverse_dcf.py \
  --description "reverse_dcf.py canonical in plugin/scripts; py_services/ symlink for agent convenience"

python3 .agents/skills/symlink-manager/scripts/symlink_manager.py create \
  --src plugins/stock-valuation/scripts/reverse_dcf.py \
  --dst plugins/stock-valuation/skills/stock_valuation/scripts/reverse_dcf.py \
  --description "ADR-003: skill scripts/ symlink -> plugin root scripts/"
```

- [ ] **Step 6: Re-run tests through the symlink**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_reverse_dcf.py -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add plugins/stock-valuation/scripts/reverse_dcf.py investment_screener/backend/py_services/reverse_dcf.py \
  plugins/stock-valuation/skills/stock_valuation/scripts/reverse_dcf.py \
  investment_screener/backend/tests/py_services/test_reverse_dcf.py symlinks.json
git commit -m "feat: add reverse_dcf.py implied-growth bisection solver"
```

---

### Task 4: `dcf_sensitivity.py` — grid + Monte Carlo

**Files:**
- Create: `plugins/stock-valuation/scripts/dcf_sensitivity.py`
- Test: `investment_screener/backend/tests/py_services/test_dcf_sensitivity.py`

**Interfaces:**
- Consumes: `compute_scenario(...)` from `dcf_scenarios.py` (same as Task 3).
- Produces: `sensitivity_grid(base_scenario, discount_rate, horizon, base_revenue, base_shares, growth_step=5.0, growth_points=3, pe_step=4.0, pe_points=3) -> dict` returning `{"grid": [{"growthRate","exitPE","fairValue"}, ...]}`; `monte_carlo(bear, base, bull, discount_rate, horizon, base_revenue, base_shares, current_price, n=5000, seed=None) -> dict` returning `{"p10","p50","p90","probabilityOvervalued","n","seed"}`. Task 8 persists both into `analyticsLog.sensitivity` / `analyticsLog.monteCarlo`.

- [ ] **Step 1: Write the failing tests**

Create `investment_screener/backend/tests/py_services/test_dcf_sensitivity.py`:

```python
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from dcf_sensitivity import sensitivity_grid, monte_carlo  # noqa: E402

BEAR = {"growthRate": 10.0, "netMargin": 15.0, "exitPE": 20.0, "qualityMultiplier": 1.0, "shareChange": 0.0}
BASE = {"growthRate": 22.0, "netMargin": 25.0, "exitPE": 30.0, "qualityMultiplier": 1.0, "shareChange": 0.0}
BULL = {"growthRate": 35.0, "netMargin": 32.0, "exitPE": 40.0, "qualityMultiplier": 1.0, "shareChange": 0.0}


def test_sensitivity_grid_dimensions_and_bounds():
    result = sensitivity_grid(
        BASE, discount_rate=0.10, horizon=5,
        base_revenue=1_000_000_000.0, base_shares=100_000_000.0,
    )

    assert len(result["grid"]) == 7 * 7  # default growth_points=3, pe_points=3 -> 7 values each axis
    growths = sorted({row["growthRate"] for row in result["grid"]})
    assert growths[0] == 7.0    # 22 - 3*5
    assert growths[-1] == 37.0  # 22 + 3*5
    pes = sorted({row["exitPE"] for row in result["grid"]})
    assert pes[0] == 18.0   # 30 - 3*4
    assert pes[-1] == 42.0  # 30 + 3*4
    assert all(isinstance(row["fairValue"], float) for row in result["grid"])


def test_sensitivity_grid_fair_value_increases_with_growth_at_fixed_pe():
    result = sensitivity_grid(
        BASE, discount_rate=0.10, horizon=5,
        base_revenue=1_000_000_000.0, base_shares=100_000_000.0,
    )
    at_center_pe = sorted(
        (row for row in result["grid"] if row["exitPE"] == 30.0),
        key=lambda r: r["growthRate"],
    )
    fair_values = [row["fairValue"] for row in at_center_pe]
    assert fair_values == sorted(fair_values)


def test_monte_carlo_is_deterministic_with_fixed_seed():
    result_a = monte_carlo(
        BEAR, BASE, BULL, discount_rate=0.10, horizon=5,
        base_revenue=1_000_000_000.0, base_shares=100_000_000.0,
        current_price=50.0, n=500, seed=42,
    )
    result_b = monte_carlo(
        BEAR, BASE, BULL, discount_rate=0.10, horizon=5,
        base_revenue=1_000_000_000.0, base_shares=100_000_000.0,
        current_price=50.0, n=500, seed=42,
    )
    assert result_a == result_b


def test_monte_carlo_percentiles_are_ordered_and_probability_is_valid():
    result = monte_carlo(
        BEAR, BASE, BULL, discount_rate=0.10, horizon=5,
        base_revenue=1_000_000_000.0, base_shares=100_000_000.0,
        current_price=50.0, n=2000, seed=7,
    )
    assert result["p10"] <= result["p50"] <= result["p90"]
    assert 0.0 <= result["probabilityOvervalued"] <= 1.0
    assert result["n"] == 2000
    assert result["seed"] == 7


def test_monte_carlo_high_price_yields_high_overvalued_probability():
    result = monte_carlo(
        BEAR, BASE, BULL, discount_rate=0.10, horizon=5,
        base_revenue=1_000_000_000.0, base_shares=100_000_000.0,
        current_price=1_000_000.0, n=1000, seed=1,
    )
    assert result["probabilityOvervalued"] > 0.95
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_dcf_sensitivity.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'dcf_sensitivity'`

- [ ] **Step 3: Write `plugins/stock-valuation/scripts/dcf_sensitivity.py`**

```python
#!/usr/bin/env python3
"""
dcf_sensitivity.py (Python Service)
=====================================

Purpose:
    Two views of DCF fair-value uncertainty: a 2D sensitivity grid across
    (growthRate x exitPE), and a Monte Carlo simulation sampling growth/
    margin/exitPE from triangular distributions anchored on the existing
    bear/base/bull scenario params, producing P10/P50/P90 fair value and
    P(fairValue < currentPrice).

Layer: Backend / Python Services / Valuation Math

Usage:
    python3 dcf_sensitivity.py --scenarios scenarios.json --revenue 1000000000 \
        --shares 100000000 --price 45.00 --mode grid --pretty
    python3 dcf_sensitivity.py --scenarios scenarios.json --revenue 1000000000 \
        --shares 100000000 --price 45.00 --mode montecarlo --n 5000 --seed 42 --pretty

Key Functions:
    - sensitivity_grid() - Fair value across (growthRate +/- step*points) x (exitPE +/- step*points)
    - monte_carlo() - Triangular-distribution sampling -> P10/P50/P90 + P(overvalued)
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dcf_scenarios import compute_scenario  # noqa: E402


def sensitivity_grid(
    base_scenario: dict,
    discount_rate: float,
    horizon: int,
    base_revenue: float,
    base_shares: float,
    growth_step: float = 5.0,
    growth_points: int = 3,
    pe_step: float = 4.0,
    pe_points: int = 3,
) -> dict:
    """2D grid of fair value across (growthRate +/- growth_step*growth_points)
    x (exitPE +/- pe_step*pe_points), holding margin/qualityMultiplier/
    shareChange fixed at base_scenario's values.

    Args:
        base_scenario: dict with at least growthRate, netMargin, exitPE,
            qualityMultiplier, shareChange (the DCF `base` case).
        discount_rate: Annual discount rate (decimal).
        horizon: Years to project.
        base_revenue: TTM base revenue in dollars.
        base_shares: Base share count.
        growth_step: pp step size for the growth axis.
        growth_points: Number of steps on each side of center for growth.
        pe_step: Step size (PE turns) for the exit-PE axis.
        pe_points: Number of steps on each side of center for exit PE.

    Returns:
        {"grid": [{"growthRate": float, "exitPE": float, "fairValue": float}, ...]}
    """
    center_growth = base_scenario["growthRate"]
    center_pe = base_scenario["exitPE"]
    growths = [center_growth + i * growth_step for i in range(-growth_points, growth_points + 1)]
    pes = [center_pe + i * pe_step for i in range(-pe_points, pe_points + 1)]

    grid = []
    for g in growths:
        for pe in pes:
            if pe <= 0:
                continue
            trial = {**base_scenario, "growthRate": g, "exitPE": pe}
            fair_value = compute_scenario(base_revenue, base_shares, discount_rate, horizon, trial)[
                "presentValue"
            ]
            grid.append({"growthRate": round(g, 2), "exitPE": round(pe, 2), "fairValue": fair_value})

    return {"grid": grid}


def monte_carlo(
    bear: dict,
    base: dict,
    bull: dict,
    discount_rate: float,
    horizon: int,
    base_revenue: float,
    base_shares: float,
    current_price: float,
    n: int = 5000,
    seed: int | None = None,
) -> dict:
    """Monte Carlo fair-value distribution: growth/margin/exitPE sampled
    independently from triangular(bear, base, bull) distributions, holding
    qualityMultiplier and shareChange fixed at `base`'s values.

    Args:
        bear: Bear-case scenario params (min of each triangular distribution).
        base: Base-case scenario params (mode of each triangular distribution).
        bull: Bull-case scenario params (max of each triangular distribution).
        discount_rate: Annual discount rate (decimal).
        horizon: Years to project.
        base_revenue: TTM base revenue in dollars.
        base_shares: Base share count.
        current_price: Current market price, for the P(overvalued) calc.
        n: Number of Monte Carlo samples.
        seed: RNG seed for reproducibility (None = nondeterministic).

    Returns:
        {"p10": float, "p50": float, "p90": float,
         "probabilityOvervalued": float, "n": int, "seed": int | None}
    """
    rng = np.random.default_rng(seed)
    fair_values = []
    for _ in range(n):
        growth = rng.triangular(bear["growthRate"], base["growthRate"], bull["growthRate"])
        margin = rng.triangular(bear["netMargin"], base["netMargin"], bull["netMargin"])
        exit_pe = rng.triangular(bear["exitPE"], base["exitPE"], bull["exitPE"])
        trial = {
            "weight": 1.0, "growthRate": growth, "netMargin": margin, "exitPE": exit_pe,
            "qualityMultiplier": base["qualityMultiplier"], "shareChange": base["shareChange"],
        }
        fair_values.append(
            compute_scenario(base_revenue, base_shares, discount_rate, horizon, trial)["presentValue"]
        )

    p10 = float(np.percentile(fair_values, 10))
    p50 = float(np.percentile(fair_values, 50))
    p90 = float(np.percentile(fair_values, 90))
    probability_overvalued = sum(1 for fv in fair_values if fv < current_price) / n

    return {
        "p10": round(p10, 2), "p50": round(p50, 2), "p90": round(p90, 2),
        "probabilityOvervalued": round(probability_overvalued, 4),
        "n": n, "seed": seed,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="DCF sensitivity grid + Monte Carlo")
    parser.add_argument("--scenarios", required=True, help="Path to scenarios JSON (bear/base/bull keys)")
    parser.add_argument("--revenue", type=float, required=True)
    parser.add_argument("--shares", type=float, required=True)
    parser.add_argument("--price", type=float, required=True)
    parser.add_argument("--discount-rate", type=float, default=0.10)
    parser.add_argument("--horizon", type=int, default=5)
    parser.add_argument("--mode", choices=["grid", "montecarlo"], required=True)
    parser.add_argument("--n", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    with open(args.scenarios) as f:
        scenarios = json.load(f)

    if args.mode == "grid":
        result = sensitivity_grid(
            scenarios["base"], args.discount_rate, args.horizon, args.revenue, args.shares
        )
    else:
        result = monte_carlo(
            scenarios["bear"], scenarios["base"], scenarios["bull"],
            args.discount_rate, args.horizon, args.revenue, args.shares,
            args.price, n=args.n, seed=args.seed,
        )

    print(json.dumps(result, indent=2 if args.pretty else None))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_dcf_sensitivity.py -v`
Expected: PASS — all 5 tests.

- [ ] **Step 5: Create the two symlinks**

```bash
python3 .agents/skills/symlink-manager/scripts/symlink_manager.py create \
  --src plugins/stock-valuation/scripts/dcf_sensitivity.py \
  --dst investment_screener/backend/py_services/dcf_sensitivity.py \
  --description "dcf_sensitivity.py canonical in plugin/scripts; py_services/ symlink for agent convenience"

python3 .agents/skills/symlink-manager/scripts/symlink_manager.py create \
  --src plugins/stock-valuation/scripts/dcf_sensitivity.py \
  --dst plugins/stock-valuation/skills/stock_valuation/scripts/dcf_sensitivity.py \
  --description "ADR-003: skill scripts/ symlink -> plugin root scripts/"
```

- [ ] **Step 6: Re-run tests through the symlink**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_dcf_sensitivity.py -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add plugins/stock-valuation/scripts/dcf_sensitivity.py investment_screener/backend/py_services/dcf_sensitivity.py \
  plugins/stock-valuation/skills/stock_valuation/scripts/dcf_sensitivity.py \
  investment_screener/backend/tests/py_services/test_dcf_sensitivity.py symlinks.json
git commit -m "feat: add dcf_sensitivity.py grid + Monte Carlo fair-value distribution"
```

---

### Task 5: `comps_valuation.py` — peer EV/Sales cross-check

**Files:**
- Create: `plugins/stock-valuation/scripts/comps_valuation.py`
- Test: `investment_screener/backend/tests/py_services/test_comps_valuation.py`

**Interfaces:**
- Consumes: `market_data.get_fundamentals(ticker, cik=None) -> dict` (Task 1, for `totalDebt`/`cashAndEquivalents`); reads `projections/{TICKER}.json` directly (existing versioned-list format).
- Produces: `comps_implied_range(ticker, peer_tickers, projections_dir) -> dict` returning `{"status": "ok"|"insufficient_peer_data", "impliedPriceRange": {"low","high"}, "peersUsed": [...], "evSalesMedian": float}`. Task 7's gate reads `impliedPriceRange` (via its midpoint) from this output once persisted to `analyticsLog.comps`.

- [ ] **Step 1: Write the failing tests**

Create `investment_screener/backend/tests/py_services/test_comps_valuation.py`:

```python
import json
import sys
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from comps_valuation import comps_implied_range, compute_ev, load_latest_projection  # noqa: E402


def _write_projection(dirpath, ticker, price, shares, revenue, source="AI_AGENT", saved_at="2026-01-01T00:00:00Z"):
    proj = [{
        "ticker": ticker, "source": source, "savedAt": saved_at,
        "snapshot": {"price": price, "shares": shares, "revenue": revenue},
    }]
    (dirpath / f"{ticker}.json").write_text(json.dumps(proj))


def test_compute_ev_combines_market_cap_debt_and_cash():
    ev = compute_ev(price=100.0, shares=10_000_000.0, debt=200_000_000.0, cash=50_000_000.0)
    assert ev == 100.0 * 10_000_000.0 + 200_000_000.0 - 50_000_000.0


def test_load_latest_projection_prefers_ai_agent_entry(tmp_path):
    proj = [
        {"ticker": "T", "source": "USER", "savedAt": "2026-01-01T00:00:00Z", "snapshot": {"price": 1}},
        {"ticker": "T", "source": "AI_AGENT", "savedAt": "2026-02-01T00:00:00Z", "snapshot": {"price": 2}},
    ]
    (tmp_path / "T.json").write_text(json.dumps(proj))
    result = load_latest_projection("T", str(tmp_path))
    assert result["snapshot"]["price"] == 2


def test_load_latest_projection_returns_none_when_file_missing(tmp_path):
    assert load_latest_projection("MISSING", str(tmp_path)) is None


def test_comps_implied_range_computes_median_ev_sales(tmp_path):
    _write_projection(tmp_path, "TARGET", price=100.0, shares=10_000_000.0, revenue=500_000_000.0)
    _write_projection(tmp_path, "PEERA", price=50.0, shares=20_000_000.0, revenue=400_000_000.0)
    _write_projection(tmp_path, "PEERB", price=80.0, shares=15_000_000.0, revenue=600_000_000.0)

    with patch("comps_valuation.get_fundamentals", return_value={}):
        result = comps_implied_range("TARGET", ["PEERA", "PEERB"], str(tmp_path))

    assert result["status"] == "ok"
    assert result["peersUsed"] == ["PEERA", "PEERB"]
    # PEERA EV/Sales = (50*20M)/400M = 2.5 ; PEERB EV/Sales = (80*15M)/600M = 2.0 ; median = 2.25
    assert result["evSalesMedian"] == 2.25


def test_comps_implied_range_insufficient_with_zero_peers(tmp_path):
    _write_projection(tmp_path, "TARGET", price=100.0, shares=10_000_000.0, revenue=500_000_000.0)
    result = comps_implied_range("TARGET", [], str(tmp_path))
    assert result["status"] == "insufficient_peer_data"
    assert result["peersUsed"] == []


def test_comps_implied_range_insufficient_with_only_one_usable_peer(tmp_path):
    _write_projection(tmp_path, "TARGET", price=100.0, shares=10_000_000.0, revenue=500_000_000.0)
    _write_projection(tmp_path, "PEERA", price=50.0, shares=20_000_000.0, revenue=400_000_000.0)
    with patch("comps_valuation.get_fundamentals", return_value={}):
        result = comps_implied_range("TARGET", ["PEERA", "MISSINGPEER"], str(tmp_path))
    assert result["status"] == "insufficient_peer_data"
    assert result["peersUsed"] == ["PEERA"]


def test_comps_implied_range_incorporates_target_debt_and_cash(tmp_path):
    _write_projection(tmp_path, "TARGET", price=100.0, shares=10_000_000.0, revenue=500_000_000.0)
    _write_projection(tmp_path, "PEERA", price=50.0, shares=20_000_000.0, revenue=400_000_000.0)
    _write_projection(tmp_path, "PEERB", price=80.0, shares=15_000_000.0, revenue=600_000_000.0)

    def fake_fundamentals(ticker, cik=None):
        if ticker == "TARGET":
            return {
                "totalDebt": {"value": 100_000_000.0, "source": "yfinance", "asOf": "x"},
                "cashAndEquivalents": {"value": 300_000_000.0, "source": "yfinance", "asOf": "x"},
            }
        return {}

    with patch("comps_valuation.get_fundamentals", side_effect=fake_fundamentals):
        result = comps_implied_range("TARGET", ["PEERA", "PEERB"], str(tmp_path))

    # evSalesMedian=2.25 -> impliedEV=2.25*500M=1125M
    # impliedPrice = (1125M - 100M + 300M)/10M = 132.5
    assert result["impliedPriceRange"]["low"] == round(132.5 * 0.9, 2)
    assert result["impliedPriceRange"]["high"] == round(132.5 * 1.1, 2)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_comps_valuation.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'comps_valuation'`

- [ ] **Step 3: Write `plugins/stock-valuation/scripts/comps_valuation.py`**

```python
#!/usr/bin/env python3
"""
comps_valuation.py (Python Service)
=====================================

Purpose:
    Peer-multiple cross-check for DCF fair value: computes EV/Sales for a
    curated peer set and applies the peer-median multiple to the target
    ticker's own revenue to derive an implied price range. EV/EBITDA comps
    is deliberately out of scope for this pass — no EBITDA source exists
    anywhere in the current data layer (see docs/architecture/ADR-valuation-committee.md).

Layer: Backend / Python Services / Valuation Math

Usage:
    python3 comps_valuation.py --ticker NVDA --peers AMD,AVGO,QCOM \
        --projections-dir investment_screener/backend/data/projections --pretty

Key Functions:
    - load_latest_projection() - Reads the latest AI_AGENT (or [0]) entry from a
      versioned projections/{TICKER}.json file
    - compute_ev() - Enterprise value from price * shares + debt - cash
    - comps_implied_range() - Primary orchestrator: peer-median EV/Sales -> implied price range
"""

import argparse
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from market_data import get_fundamentals  # noqa: E402


def load_latest_projection(ticker: str, projections_dir: str) -> dict | None:
    """Load the latest AI_AGENT entry (or the only entry) from projections/{TICKER}.json.

    Mirrors portfolio_action.py._load_ai_upside()'s established read pattern
    for this repo's versioned-list projection file format.

    Args:
        ticker: Ticker symbol.
        projections_dir: Path to the projections directory.

    Returns:
        The latest projection dict, or None if the file doesn't exist or is empty.
    """
    path = Path(projections_dir) / f"{ticker}.json"
    if not path.exists():
        return None
    with open(path) as f:
        projs = json.load(f)
    if isinstance(projs, list):
        if not projs:
            return None
        ai = [p for p in projs if p.get("source") == "AI_AGENT"]
        return max(ai, key=lambda x: x.get("savedAt", "")) if ai else projs[0]
    return projs


def compute_ev(price: float, shares: float, debt: float, cash: float) -> float:
    """Enterprise value: market cap (price * shares) + debt - cash."""
    return price * shares + debt - cash


def _peer_ev_sales(ticker: str, projections_dir: str) -> float | None:
    """EV/Sales for one peer ticker, or None if its data is unusable."""
    proj = load_latest_projection(ticker, projections_dir)
    if proj is None:
        return None
    snapshot = proj.get("snapshot", {})
    price = snapshot.get("price")
    shares = snapshot.get("shares")
    revenue = snapshot.get("revenue")
    if not price or not shares or not revenue or revenue <= 0:
        return None

    fundamentals = get_fundamentals(ticker)
    debt = fundamentals.get("totalDebt", {}).get("value") or 0.0
    cash = fundamentals.get("cashAndEquivalents", {}).get("value") or 0.0

    return compute_ev(price, shares, debt, cash) / revenue


def comps_implied_range(ticker: str, peer_tickers: list[str], projections_dir: str) -> dict:
    """Peer-median EV/Sales applied to the target's own revenue -> implied price range.

    Args:
        ticker: Target ticker.
        peer_tickers: Curated peer ticker list (from projections/{TICKER}.json's `peers` field).
        projections_dir: Path to the projections directory.

    Returns:
        {"status": "ok", "impliedPriceRange": {"low": float, "high": float},
         "peersUsed": [...], "evSalesMedian": float}
        or {"status": "insufficient_peer_data", "peersUsed": [...]} when fewer
        than 2 peers have usable data.
    """
    target_proj = load_latest_projection(ticker, projections_dir)
    if target_proj is None:
        return {"status": "insufficient_peer_data", "peersUsed": []}

    snapshot = target_proj.get("snapshot", {})
    target_shares = snapshot.get("shares")
    target_revenue = snapshot.get("revenue")
    if not target_shares or not target_revenue:
        return {"status": "insufficient_peer_data", "peersUsed": []}

    peer_multiples = {}
    for peer in peer_tickers:
        multiple = _peer_ev_sales(peer, projections_dir)
        if multiple is not None:
            peer_multiples[peer] = multiple

    if len(peer_multiples) < 2:
        return {"status": "insufficient_peer_data", "peersUsed": list(peer_multiples)}

    ev_sales_median = statistics.median(peer_multiples.values())

    fundamentals = get_fundamentals(ticker)
    target_debt = fundamentals.get("totalDebt", {}).get("value") or 0.0
    target_cash = fundamentals.get("cashAndEquivalents", {}).get("value") or 0.0

    implied_ev = ev_sales_median * target_revenue
    implied_price = (implied_ev - target_debt + target_cash) / target_shares

    # +/-10% band around the point estimate — a single multiple from a small
    # peer set is not precise enough to present as one number.
    return {
        "status": "ok",
        "impliedPriceRange": {
            "low": round(implied_price * 0.9, 2),
            "high": round(implied_price * 1.1, 2),
        },
        "peersUsed": list(peer_multiples),
        "evSalesMedian": round(ev_sales_median, 3),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Peer-multiple (EV/Sales) comps cross-check")
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--peers", required=True, help="Comma-separated peer tickers")
    parser.add_argument("--projections-dir", required=True)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    peer_tickers = [p.strip() for p in args.peers.split(",") if p.strip()]
    result = comps_implied_range(args.ticker, peer_tickers, args.projections_dir)
    print(json.dumps(result, indent=2 if args.pretty else None))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_comps_valuation.py -v`
Expected: PASS — all 7 tests.

- [ ] **Step 5: Create the two symlinks**

```bash
python3 .agents/skills/symlink-manager/scripts/symlink_manager.py create \
  --src plugins/stock-valuation/scripts/comps_valuation.py \
  --dst investment_screener/backend/py_services/comps_valuation.py \
  --description "comps_valuation.py canonical in plugin/scripts; py_services/ symlink for agent convenience"

python3 .agents/skills/symlink-manager/scripts/symlink_manager.py create \
  --src plugins/stock-valuation/scripts/comps_valuation.py \
  --dst plugins/stock-valuation/skills/stock_valuation/scripts/comps_valuation.py \
  --description "ADR-003: skill scripts/ symlink -> plugin root scripts/"
```

- [ ] **Step 6: Re-run tests through the symlink**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_comps_valuation.py -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add plugins/stock-valuation/scripts/comps_valuation.py investment_screener/backend/py_services/comps_valuation.py \
  plugins/stock-valuation/skills/stock_valuation/scripts/comps_valuation.py \
  investment_screener/backend/tests/py_services/test_comps_valuation.py symlinks.json
git commit -m "feat: add comps_valuation.py peer EV/Sales cross-check"
```

---

### Task 6: `dcf_scenarios.py` — `--wacc-file` CLI wiring

**Files:**
- Modify: `plugins/stock-valuation/scripts/dcf_scenarios.py` (canonical; symlinked into `investment_screener/backend/py_services/dcf_scenarios.py` and `plugins/stock-valuation/skills/stock_valuation/scripts/dcf_scenarios.py` — editing the canonical file updates both)
- Test: `investment_screener/backend/tests/py_services/test_dcf_scenarios_wacc_file.py`

**Interfaces:**
- Consumes: a JSON file at the path given by `--wacc-file`, shaped like `wacc.py`'s CLI output (must contain a `"wacc"` key).
- Produces: `_resolve_discount_rate(explicit_rate, wacc_file) -> float` — the CLI-layer precedence rule (`--discount-rate` explicit > `--wacc-file` > 0.10 default). `run()`'s existing signature and `compute_scenario()`'s math are unchanged.

- [ ] **Step 1: Write the failing tests**

Create `investment_screener/backend/tests/py_services/test_dcf_scenarios_wacc_file.py`:

```python
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from dcf_scenarios import _resolve_discount_rate  # noqa: E402


def test_resolve_discount_rate_uses_explicit_override_when_given(tmp_path):
    wacc_file = tmp_path / "wacc.json"
    wacc_file.write_text(json.dumps({"wacc": 0.12}))
    assert _resolve_discount_rate(0.08, str(wacc_file)) == 0.08


def test_resolve_discount_rate_uses_wacc_file_when_no_explicit_override(tmp_path):
    wacc_file = tmp_path / "wacc.json"
    wacc_file.write_text(json.dumps({"wacc": 0.12}))
    assert _resolve_discount_rate(None, str(wacc_file)) == 0.12


def test_resolve_discount_rate_defaults_to_ten_percent_when_neither_given():
    assert _resolve_discount_rate(None, None) == 0.10
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_dcf_scenarios_wacc_file.py -v`
Expected: FAIL — `ImportError: cannot import name '_resolve_discount_rate'`

- [ ] **Step 3: Add `_resolve_discount_rate()` and wire it into `main()`**

Modify `plugins/stock-valuation/scripts/dcf_scenarios.py`. Find the `main()` function (currently at the end of the file, per the existing `--discount-rate` argument):

```python
    parser.add_argument("--discount-rate", type=float, default=0.10)
```

Replace that single line with:

```python
    parser.add_argument(
        "--discount-rate", type=float, default=None,
        help="Explicit discount rate override — wins over --wacc-file. Defaults to 0.10 if neither is given.",
    )
    parser.add_argument(
        "--wacc-file", default=None,
        help="Path to wacc.py's JSON output; used as the discount rate unless --discount-rate is explicitly set.",
    )
```

Then find where `args.discount_rate` is passed to `run(...)`:

```python
    result = run(
        ticker=ticker,
        base_revenue=revenue,
        base_shares=shares,
        scenario_params=scenario_params,
        discount_rate=args.discount_rate,
        horizon=args.horizon,
        price=price,
    )
```

Replace with:

```python
    discount_rate = _resolve_discount_rate(args.discount_rate, args.wacc_file)

    result = run(
        ticker=ticker,
        base_revenue=revenue,
        base_shares=shares,
        scenario_params=scenario_params,
        discount_rate=discount_rate,
        horizon=args.horizon,
        price=price,
    )
```

Add the new function just above `main()`:

```python
def _resolve_discount_rate(explicit_rate: float | None, wacc_file: str | None) -> float:
    """CLI-layer discount-rate resolution: --discount-rate (explicit) wins over
    --wacc-file (derived) wins over the 0.10 default — preserves old-run
    reproducibility while letting wacc.py drive the rate when no explicit
    override is given.

    Args:
        explicit_rate: Value of --discount-rate, or None if not passed.
        wacc_file: Path to a wacc.py JSON output file, or None.

    Returns:
        The resolved discount rate as a decimal fraction.
    """
    if explicit_rate is not None:
        return explicit_rate
    if wacc_file:
        with open(wacc_file) as f:
            wacc_data = json.load(f)
        return wacc_data["wacc"]
    return 0.10
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_dcf_scenarios_wacc_file.py -v`
Expected: PASS — all 3 tests.

- [ ] **Step 5: Run the existing math-parity test to confirm no regression**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_math_parity.py -v`
Expected: PASS (unchanged) — this test never passes `--discount-rate` or `--wacc-file`, so it still gets the 0.10 default via `_resolve_discount_rate(None, None)`.

- [ ] **Step 6: Commit**

```bash
git add plugins/stock-valuation/scripts/dcf_scenarios.py investment_screener/backend/tests/py_services/test_dcf_scenarios_wacc_file.py
git commit -m "feat: wire --wacc-file into dcf_scenarios.py, keep --discount-rate for reproducibility"
```

---

### Task 7: `validate_projection.py` — 2-of-3 ACCUMULATE gate

**Files:**
- Modify: `plugins/stock-valuation/scripts/validate_projection.py`
- Test: `plugins/stock-valuation/tests/test_validate_projection.py` (new directory)

**Interfaces:**
- Consumes: a full projection dict with `aiThesis.action`, `snapshot.price`, and `analyticsLog.{dcf,comps,reverseDcf}` (as produced by Tasks 2–6, merged by Task 8's pipeline wiring).
- Produces: `check_accumulate_gate(projection: dict) -> dict` returning `{"gatePassed","lensesAgreeing","lensResults":{"dcf","comps","impliedGrowth"},"spreadPct","disagreementNoteRequired"}`. `validate_projection()`'s existing `errors: list[str]` return type is unchanged — a failed gate appends one more `"[FAIL] ..."` string to it, and a required-but-missing disagreement note is printed as a `[WARN]` to stderr (non-blocking, matching the spec's "surface, don't block" framing for spread disagreement specifically, versus the gate itself which does block).

- [ ] **Step 1: Write the failing tests**

Create the new test directory and file `plugins/stock-valuation/tests/test_validate_projection.py`:

```python
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = REPO_ROOT / "plugins/stock-valuation/scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from validate_projection import check_accumulate_gate, validate_projection  # noqa: E402


def _projection(action, dcf_upside=None, comps_status="ok", comps_low=None, comps_high=None,
                 implied_growth_vs_base=None, current_price=100.0, dcf_fair_value=None):
    analytics = {}
    if dcf_upside is not None:
        analytics["dcf"] = {"upsidePct": dcf_upside}
        if dcf_fair_value is not None:
            analytics["dcf"]["weightedFairValue"] = dcf_fair_value
    if comps_status == "ok":
        analytics["comps"] = {
            "status": "ok",
            "impliedPriceRange": {"low": comps_low, "high": comps_high},
        }
    else:
        analytics["comps"] = {"status": "insufficient_peer_data"}
    if implied_growth_vs_base is not None:
        analytics["reverseDcf"] = {"impliedGrowthVsBaseCase": implied_growth_vs_base}

    return {
        "aiThesis": {"action": action},
        "snapshot": {"price": current_price},
        "analyticsLog": analytics,
        "rationale": "placeholder rationale",
    }


def test_gate_passes_when_all_three_lenses_agree():
    proj = _projection(
        action="ACCUMULATE", dcf_upside=20.0, comps_low=110.0, comps_high=130.0,
        implied_growth_vs_base=-3.0, current_price=100.0,
    )
    result = check_accumulate_gate(proj)
    assert result["gatePassed"] is True
    assert result["lensesAgreeing"] == 3
    assert result["lensResults"] == {"dcf": True, "comps": True, "impliedGrowth": True}


def test_gate_passes_when_exactly_two_of_three_agree():
    proj = _projection(
        action="ACCUMULATE", dcf_upside=20.0, comps_low=110.0, comps_high=130.0,
        implied_growth_vs_base=5.0,  # disagrees (market pricing in MORE than base case)
        current_price=100.0,
    )
    result = check_accumulate_gate(proj)
    assert result["gatePassed"] is True
    assert result["lensesAgreeing"] == 2


def test_gate_blocks_when_only_one_of_three_agrees():
    proj = _projection(
        action="ACCUMULATE", dcf_upside=20.0, comps_low=70.0, comps_high=90.0,  # comps disagrees
        implied_growth_vs_base=5.0,  # impliedGrowth disagrees
        current_price=100.0,
    )
    result = check_accumulate_gate(proj)
    assert result["gatePassed"] is False
    assert result["lensesAgreeing"] == 1


def test_gate_blocks_when_zero_lenses_agree():
    proj = _projection(
        action="ACCUMULATE", dcf_upside=5.0, comps_low=70.0, comps_high=90.0,
        implied_growth_vs_base=5.0, current_price=100.0,
    )
    result = check_accumulate_gate(proj)
    assert result["gatePassed"] is False
    assert result["lensesAgreeing"] == 0


def test_gate_is_trivially_passed_for_non_accumulate_actions():
    proj = _projection(
        action="HOLD", dcf_upside=5.0, comps_low=70.0, comps_high=90.0,
        implied_growth_vs_base=5.0, current_price=100.0,
    )
    result = check_accumulate_gate(proj)
    assert result["gatePassed"] is True


def test_gate_treats_insufficient_comps_data_as_comps_lens_disagreeing():
    proj = _projection(
        action="ACCUMULATE", dcf_upside=20.0, comps_status="insufficient_peer_data",
        implied_growth_vs_base=-3.0, current_price=100.0,
    )
    result = check_accumulate_gate(proj)
    # Only dcf + impliedGrowth can agree = 2 of 3 -> still passes
    assert result["lensResults"]["comps"] is False
    assert result["gatePassed"] is True


def test_disagreement_note_required_above_25_percent_spread():
    proj = _projection(
        action="ACCUMULATE", dcf_upside=20.0, dcf_fair_value=150.0,
        comps_low=100.0, comps_high=100.0,  # comps midpoint 100, dcf fair value 150 -> 50% spread
        implied_growth_vs_base=-3.0, current_price=100.0,
    )
    result = check_accumulate_gate(proj)
    assert result["spreadPct"] > 25.0
    assert result["disagreementNoteRequired"] is True


def test_disagreement_note_not_required_within_25_percent_spread():
    proj = _projection(
        action="ACCUMULATE", dcf_upside=20.0, dcf_fair_value=110.0,
        comps_low=105.0, comps_high=115.0,  # comps midpoint 110, dcf fair value 110 -> 0% spread
        implied_growth_vs_base=-3.0, current_price=100.0,
    )
    result = check_accumulate_gate(proj)
    assert result["disagreementNoteRequired"] is False


def test_validate_projection_appends_gate_failure_to_errors():
    proj = _projection(
        action="ACCUMULATE", dcf_upside=5.0, comps_low=70.0, comps_high=90.0,
        implied_growth_vs_base=5.0, current_price=100.0,
    )
    # Fill in the other required top-level fields validate_projection() checks
    proj.update({
        "ticker": "TEST", "id": "11111111-1111-1111-1111-111111111111", "source": "AI_AGENT",
        "schemaVersion": "1.2", "version": 1, "savedAt": "2026-07-04T00:00:00Z",
        "globalSettings": {"discountRate": 10, "timeHorizon": 5},
        "scenarios": {
            "bear": {"weight": 0.2, "growthRate": 5, "netMargin": 10, "exitPE": 15,
                     "qualityMultiplier": 1.0, "shareChange": 0, "scenarioPrice": 50},
            "base": {"weight": 0.5, "growthRate": 15, "netMargin": 20, "exitPE": 25,
                     "qualityMultiplier": 1.0, "shareChange": 0, "scenarioPrice": 100},
            "bull": {"weight": 0.3, "growthRate": 25, "netMargin": 30, "exitPE": 35,
                     "qualityMultiplier": 1.0, "shareChange": 0, "scenarioPrice": 150},
        },
    })
    errors = validate_projection(proj)
    assert any("ACCUMULATE requires" in e for e in errors)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd plugins/stock-valuation/tests && python3 -m pytest test_validate_projection.py -v`
Expected: FAIL — `ImportError: cannot import name 'check_accumulate_gate'`

- [ ] **Step 3: Add `check_accumulate_gate()` to `validate_projection.py`**

Modify `plugins/stock-valuation/scripts/validate_projection.py`. Add this constant and function above `validate_projection()`:

```python
ACCUMULATE_SPREAD_THRESHOLD_PCT = 25.0
ACCUMULATE_DCF_UPSIDE_THRESHOLD_PCT = 15.0


def check_accumulate_gate(projection: dict) -> dict:
    """Gate check: ACCUMULATE requires >=2 of 3 valuation lenses agreeing.

    Lenses: (1) DCF upside > 15% (analyticsLog.dcf.upsidePct), (2) comps
    implied price (midpoint of analyticsLog.comps.impliedPriceRange) >
    current price, (3) implied growth < base-case growth
    (analyticsLog.reverseDcf.impliedGrowthVsBaseCase < 0 — the market is
    pricing in less optimism than our own base case, a margin-of-safety
    signal). A projection whose aiThesis.action isn't ACCUMULATE always
    passes trivially — this gate only constrains that one action.

    Args:
        projection: Full projection dict (aiThesis, snapshot, analyticsLog).

    Returns:
        {"gatePassed": bool, "lensesAgreeing": int,
         "lensResults": {"dcf": bool, "comps": bool, "impliedGrowth": bool},
         "spreadPct": float, "disagreementNoteRequired": bool}
    """
    analytics = projection.get("analyticsLog", {}) or {}
    action = projection.get("aiThesis", {}).get("action")
    current_price = projection.get("snapshot", {}).get("price")

    dcf_upside_pct = analytics.get("dcf", {}).get("upsidePct")
    dcf_lens = bool(dcf_upside_pct is not None and dcf_upside_pct > ACCUMULATE_DCF_UPSIDE_THRESHOLD_PCT)

    comps = analytics.get("comps", {}) or {}
    comps_price = None
    if comps.get("status") == "ok" and current_price:
        implied_range = comps.get("impliedPriceRange", {})
        comps_price = (implied_range.get("low", 0) + implied_range.get("high", 0)) / 2
    comps_lens = bool(comps_price is not None and current_price and comps_price > current_price)

    reverse_dcf = analytics.get("reverseDcf", {}) or {}
    implied_growth_vs_base = reverse_dcf.get("impliedGrowthVsBaseCase")
    implied_growth_lens = bool(implied_growth_vs_base is not None and implied_growth_vs_base < 0)

    lenses_agreeing = sum([dcf_lens, comps_lens, implied_growth_lens])
    gate_passed = (action != "ACCUMULATE") or (lenses_agreeing >= 2)

    prices = [p for p in [analytics.get("dcf", {}).get("weightedFairValue"), comps_price] if p is not None]
    spread_pct = 0.0
    if len(prices) >= 2 and min(prices) > 0:
        spread_pct = round((max(prices) - min(prices)) / min(prices) * 100, 2)

    return {
        "gatePassed": gate_passed,
        "lensesAgreeing": lenses_agreeing,
        "lensResults": {"dcf": dcf_lens, "comps": comps_lens, "impliedGrowth": implied_growth_lens},
        "spreadPct": spread_pct,
        "disagreementNoteRequired": spread_pct > ACCUMULATE_SPREAD_THRESHOLD_PCT,
    }
```

Then, inside `validate_projection()`, just before the existing `if verbose:` block at the end of the function, add:

```python
    # --- Valuation-committee gate (Phase 2a) ---
    gate = check_accumulate_gate(data)
    if not gate["gatePassed"]:
        errors.append(
            f"[FAIL] aiThesis.action: ACCUMULATE requires >=2 of 3 valuation lenses "
            f"agreeing, only {gate['lensesAgreeing']} do ({gate['lensResults']})"
        )
    if gate["disagreementNoteRequired"]:
        print(
            f"[WARN] valuation lenses disagree by {gate['spreadPct']}% (>25%) — "
            "document this disagreement in rationale before finalizing.",
            file=sys.stderr,
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd plugins/stock-valuation/tests && python3 -m pytest test_validate_projection.py -v`
Expected: PASS — all 9 tests.

- [ ] **Step 5: Sync the `.agents/` mirror copy**

`plugins/stock-valuation/scripts/validate_projection.py` has a non-symlinked duplicate at `.agents/skills/stock_valuation/scripts/validate_projection.py` (pre-existing, not introduced by this task). **`.agents/` is entirely gitignored** (`.gitignore:65`) — this file is not tracked by git at all, so it must be copied for local consistency but never `git add`-ed. Copy the updated file to keep both in sync:

```bash
cp plugins/stock-valuation/scripts/validate_projection.py .agents/skills/stock_valuation/scripts/validate_projection.py
diff plugins/stock-valuation/scripts/validate_projection.py .agents/skills/stock_valuation/scripts/validate_projection.py
```
Expected: `diff` produces no output (files identical).

- [ ] **Step 6: Commit**

```bash
git add plugins/stock-valuation/scripts/validate_projection.py \
  plugins/stock-valuation/tests/test_validate_projection.py
git commit -m "feat: add 2-of-3 valuation-lens gate to validate_projection.py"
```

Note: do not `git add` the `.agents/` copy — it is gitignored by design and the `cp` in Step 5 is a local-sync convenience only, not a version-controlled change.

---

### Task 8: Integration — peer seeding, skill instructions, ADR, migration audit

**Files:**
- Modify: `investment_screener/backend/data/projections/{CORZ,PANW,CRWV,NBIS,BE,SNDK,CEG,OKLO,APLD,MSFT}.json` (add `"peers"` field to the latest entry in each)
- Modify: `plugins/stock-valuation/skills/stock_valuation/SKILL.md` (add a new step between the existing Step 3 and Step 4)
- Create: `docs/architecture/ADR-valuation-committee.md`
- Create: `investment_screener/backend/tests/py_services/test_accumulate_gate_migration.py`

**Interfaces:**
- Consumes: every script from Tasks 1–7.
- Produces: nothing new consumed downstream — this is the final integration/documentation task for Phase 2a.

- [ ] **Step 1: Add `peers` to the current portfolio holdings' latest projection entry**

For each of the 10 tickers below, open `investment_screener/backend/data/projections/{TICKER}.json`, and add a top-level `"peers": [...]` key to the **last** entry in the list (the file is a JSON array — this schema is `.passthrough()` at the top level in `zod-schemas.ts`, so no migration is needed). Use exactly these curated peer lists (best-effort sector comps — flagged for the user/agent to sanity-check on first real use, per the design spec §8):

| Ticker | `peers` |
|---|---|
| CORZ | `["IREN", "CIFR", "WULF"]` |
| PANW | `["CRWD", "FTNT", "ZS"]` |
| CRWV | `["NBIS", "APLD", "ORCL"]` |
| NBIS | `["CRWV", "APLD", "ORCL"]` |
| BE | `["PLUG", "FCEL"]` |
| SNDK | `["MU", "WDC"]` |
| CEG | `["VST", "NRG"]` |
| OKLO | `["SMR", "NNE"]` |
| APLD | `["CRWV", "NBIS", "IREN"]` |
| MSFT | `["GOOGL", "AMZN", "AAPL"]` |

Note: **CBRS is deliberately skipped** — no confident sector-peer knowledge for this holding exists in this pass. Its `comps_valuation.py` calls will correctly return `{"status": "insufficient_peer_data"}` until a peer list is curated later; this is the script's designed behavior for an unseeded ticker, not a bug.

Run all 10 of these exactly as written (one `python3 -c` invocation per ticker):

```bash
python3 -c "
import json
path = 'investment_screener/backend/data/projections/CORZ.json'
with open(path) as f: data = json.load(f)
data[-1]['peers'] = ['IREN', 'CIFR', 'WULF']
with open(path, 'w') as f: json.dump(data, f, indent=2)
"
python3 -c "
import json
path = 'investment_screener/backend/data/projections/PANW.json'
with open(path) as f: data = json.load(f)
data[-1]['peers'] = ['CRWD', 'FTNT', 'ZS']
with open(path, 'w') as f: json.dump(data, f, indent=2)
"
python3 -c "
import json
path = 'investment_screener/backend/data/projections/CRWV.json'
with open(path) as f: data = json.load(f)
data[-1]['peers'] = ['NBIS', 'APLD', 'ORCL']
with open(path, 'w') as f: json.dump(data, f, indent=2)
"
python3 -c "
import json
path = 'investment_screener/backend/data/projections/NBIS.json'
with open(path) as f: data = json.load(f)
data[-1]['peers'] = ['CRWV', 'APLD', 'ORCL']
with open(path, 'w') as f: json.dump(data, f, indent=2)
"
python3 -c "
import json
path = 'investment_screener/backend/data/projections/BE.json'
with open(path) as f: data = json.load(f)
data[-1]['peers'] = ['PLUG', 'FCEL']
with open(path, 'w') as f: json.dump(data, f, indent=2)
"
python3 -c "
import json
path = 'investment_screener/backend/data/projections/SNDK.json'
with open(path) as f: data = json.load(f)
data[-1]['peers'] = ['MU', 'WDC']
with open(path, 'w') as f: json.dump(data, f, indent=2)
"
python3 -c "
import json
path = 'investment_screener/backend/data/projections/CEG.json'
with open(path) as f: data = json.load(f)
data[-1]['peers'] = ['VST', 'NRG']
with open(path, 'w') as f: json.dump(data, f, indent=2)
"
python3 -c "
import json
path = 'investment_screener/backend/data/projections/OKLO.json'
with open(path) as f: data = json.load(f)
data[-1]['peers'] = ['SMR', 'NNE']
with open(path, 'w') as f: json.dump(data, f, indent=2)
"
python3 -c "
import json
path = 'investment_screener/backend/data/projections/APLD.json'
with open(path) as f: data = json.load(f)
data[-1]['peers'] = ['CRWV', 'NBIS', 'IREN']
with open(path, 'w') as f: json.dump(data, f, indent=2)
"
python3 -c "
import json
path = 'investment_screener/backend/data/projections/MSFT.json'
with open(path) as f: data = json.load(f)
data[-1]['peers'] = ['GOOGL', 'AMZN', 'AAPL']
with open(path, 'w') as f: json.dump(data, f, indent=2)
"
```

Verify all 10 landed correctly:

```bash
for t in CORZ PANW CRWV NBIS BE SNDK CEG OKLO APLD MSFT; do
  python3 -c "import json; d=json.load(open('investment_screener/backend/data/projections/$t.json')); print('$t', d[-1].get('peers'))"
done
```

- [ ] **Step 2: Write the migration-audit test**

Create `investment_screener/backend/tests/py_services/test_accumulate_gate_migration.py`:

```python
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
PLUGIN_SCRIPTS_DIR = REPO_ROOT / "plugins/stock-valuation/scripts"
PROJECTIONS_DIR = REPO_ROOT / "investment_screener/backend/data/projections"
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(PLUGIN_SCRIPTS_DIR))

from validate_projection import check_accumulate_gate  # noqa: E402


def test_document_existing_accumulate_projections_against_new_gate(capsys):
    """Not a pass/fail gate on old data — a documentation pass. Prints every
    currently-ACCUMULATE projection that would fail the new 2-of-3 gate, so
    the agent can re-review each one (never silently auto-corrected, per the
    design spec's migration acceptance criterion)."""
    would_fail = []
    for path in sorted(PROJECTIONS_DIR.glob("*.json")):
        if path.name.endswith(".pylock"):
            continue
        try:
            with open(path) as f:
                entries = json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if not isinstance(entries, list) or not entries:
            continue
        latest = entries[-1]
        if latest.get("aiThesis", {}).get("action") != "ACCUMULATE":
            continue
        gate = check_accumulate_gate(latest)
        if not gate["gatePassed"]:
            would_fail.append((path.stem, gate["lensesAgreeing"]))

    if would_fail:
        print(f"\n{len(would_fail)} existing ACCUMULATE projection(s) would fail the new gate "
              "(pre-Phase-2a data has no analyticsLog.{dcf,comps,reverseDcf} yet, so this is "
              "expected until each is re-run through /evaluate-stock):")
        for ticker, n in would_fail:
            print(f"  - {ticker}: only {n}/3 lenses agree")

    # Documentation only — always passes. The printed list above is the
    # actual deliverable (captured by `capsys` here just to keep the test
    # from being silently swallowed; run with `-s` to see it directly).
    captured = capsys.readouterr()
    assert True
```

- [ ] **Step 3: Run the migration-audit test and capture its output**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_accumulate_gate_migration.py -v -s`
Expected: PASS (always — it's a documentation pass, not a hard gate). Note the printed list of any currently-ACCUMULATE tickers lacking `analyticsLog` lens data — this is expected for every existing projection until it's re-run through `/evaluate-stock` with the new pipeline, per the design spec's Success Criterion #5. Do not attempt to silently fix these; just confirm the list prints correctly.

- [ ] **Step 4: Update the `stock_valuation` skill instructions**

Modify `plugins/stock-valuation/skills/stock_valuation/SKILL.md`. Find the existing `## Step 3: Cognitive Analysis — Define Scenarios, Then Run DCF Calculator` section and the `## Step 4: Validate & Repair` section that follows it. Insert a new section between them:

```markdown
## Step 3.5: Valuation Committee — Additional Lenses (Phase 2a)

After the canonical DCF calculator runs (Step 3), run the four additional
valuation-committee scripts before persisting. Each one is optional to run
standalone but all four are required before Step 4's validator, since the
2-of-3 ACCUMULATE gate needs their output in `analyticsLog`.

```bash
# 1. Per-company discount rate (replaces the flat 10% default)
python3 investment_screener/backend/py_services/wacc.py \
  --ticker TICKER --market-cap <market_cap_from_metrics> --cik <cik_or_omit> --pretty
# -> analyticsLog.wacc

# 2. Re-run DCF with the computed WACC (instead of the default --discount-rate)
python3 investment_screener/backend/py_services/dcf_scenarios.py \
  --raw <raw_financials.json> --scenarios <scenarios.json> --wacc-file <wacc_output.json> --pretty

# 3. Reverse-DCF implied growth
python3 investment_screener/backend/py_services/reverse_dcf.py \
  --price <current_price> --revenue <base_revenue> --shares <base_shares> \
  --margin <base_margin> --exit-pe <base_exit_pe> \
  --bear-growth <bear_growth> --base-growth <base_growth> --bull-growth <bull_growth> --pretty
# -> analyticsLog.reverseDcf

# 4. Sensitivity grid + Monte Carlo
python3 investment_screener/backend/py_services/dcf_sensitivity.py \
  --scenarios <scenarios.json> --revenue <base_revenue> --shares <base_shares> \
  --price <current_price> --mode grid --pretty
python3 investment_screener/backend/py_services/dcf_sensitivity.py \
  --scenarios <scenarios.json> --revenue <base_revenue> --shares <base_shares> \
  --price <current_price> --mode montecarlo --pretty
# -> analyticsLog.sensitivity, analyticsLog.monteCarlo

# 5. Comps cross-check (only if projections/{TICKER}.json already has a peers list)
python3 investment_screener/backend/py_services/comps_valuation.py \
  --ticker TICKER --peers <comma_separated_peers> \
  --projections-dir investment_screener/backend/data/projections --pretty
# -> analyticsLog.comps ; {"status": "insufficient_peer_data"} is expected and fine
# for any ticker without a curated peers list yet — do not fabricate one.
```

Merge all five outputs (`wacc`, `reverseDcf`, `sensitivity`, `monteCarlo`, `comps`) into the
projection's `analyticsLog` object before Step 4. If DCF upside, comps upside,
and implied-growth-vs-base disagree by more than 25%, say so explicitly in the
conversational summary (Step 8) and in `rationale` — never average the
disagreement away.
```

- [ ] **Step 5: Update Step 4's description to mention the new gate**

In the same `SKILL.md` file, find the existing `## Step 4: Validate & Repair` section's introductory sentence and add one sentence noting the new gate:

```markdown
## Step 4: Validate & Repair

Run the pre-persistence validator. This now also enforces the Phase 2a
valuation-committee gate: `aiThesis.action = ACCUMULATE` requires at least 2
of the 3 lenses (DCF upside, comps upside, implied-growth-below-base-case)
to agree — a validation error if fewer than 2 agree, forcing either the
action to be revised or a re-check of the underlying lens data before
persistence.
```

- [ ] **Step 6: Write the ADR**

Create `docs/architecture/ADR-valuation-committee.md`:

```markdown
# ADR: Valuation Committee (Phase 2a)

**Status:** Accepted
**Date:** 2026-07-04
**Context:** Fable5 Elevation Guide Phase 2a — see `docs/superpowers/specs/2026-07-04-valuation-committee-design.md`

## Decision

`aiThesis.action = "ACCUMULATE"` now requires at least 2 of 3 independent
valuation lenses to agree:

1. **DCF upside** — `analyticsLog.dcf.upsidePct > 15%` (the existing BUY threshold).
2. **Comps upside** — the peer-median EV/Sales-implied price range's midpoint
   exceeds the current price (`analyticsLog.comps`).
3. **Implied growth below base case** — the market's reverse-DCF-implied
   5-year revenue CAGR is *less* than our own base-case growth assumption
   (`analyticsLog.reverseDcf.impliedGrowthVsBaseCase < 0`) — a margin-of-safety signal.

This is enforced in `validate_projection.py`'s `check_accumulate_gate()`,
which blocks (validation error, non-persistable) any projection where fewer
than 2 of 3 lenses agree for an ACCUMULATE action. All other actions
(`INITIATE`, `MAINTAIN`, `TRIM`, `EXIT`, `WATCHLIST`, `BUY`, `HOLD`, `SELL`)
are unaffected by this gate.

Additionally, whenever the three lenses' implied prices disagree by more
than 25% (`analyticsLog` DCF fair value vs. comps midpoint), a warning is
printed requiring the disagreement to be documented in `rationale` — this
is a warning, not a blocking error, since disagreement itself is valuable
information the agent must surface, not resolve by picking a side.

## Why 4 lenses instead of 1

A single DCF-weighted fair value is a single point of failure: if its
growth/margin/exit-PE assumptions are wrong, nothing catches it, because
nothing else is being asked. Four independent lenses — forward DCF,
reverse-DCF (what the market is pricing in), Monte Carlo (a probability
distribution, not one number), and peer comps (an entirely different
methodology) — catch a wrong DCF assumption when at least one of the other
three doesn't corroborate it. Requiring 2-of-3 agreement (not 3-of-3, and
not just "average them") reflects that any single lens can be wrong for
idiosyncratic reasons (bad peer set, thin regression data for beta, a
temporarily depressed comps sector) without invalidating the whole signal —
while still blocking the case where only one lens supports the recommended
action.

## Scope boundaries taken in this pass

- **EV/EBITDA comps deferred.** No EBITDA source exists anywhere in the
  current data layer (`market_data.get_fundamentals()` has no clean raw
  EBITDA field, and `fetch_financials.py`'s `expert_metrics.rule_of_40.ebitda_margin`
  is a derived ratio, not a raw figure suitable for EV/EBITDA). `comps_valuation.py`
  computes **EV/Sales only** this pass.
- **`totalDebt`/`cashAndEquivalents`/`interestExpense` are yfinance-only.**
  No EDGAR XBRL tag mapping exists for these yet in `edgar_facts.py` —
  mirrors the existing `operatingIncome`-is-EDGAR-only precedent, inverted.
- **Peer lists are seeded only for the ~10 actively-held tickers** with
  confident sector-peer knowledge as of this pass (see the design spec §8
  and the implementation plan's Task 8). New tickers get a `peers` list
  the next time they go through `/evaluate-stock`; an unseeded ticker
  correctly returns `{"status": "insufficient_peer_data"}`, not a fabricated range.
- **Capital-structure weighting for WACC** uses market cap (equity) and
  `totalDebt` (debt) only — no preferred stock or minority-interest
  adjustments in this pass.

## Consequences

- Existing `projections/*.json` entries with `aiThesis.action = ACCUMULATE`
  predate this gate and have no `analyticsLog.{dcf,comps,reverseDcf}` data —
  they are **not retroactively invalidated**, but the migration-audit test
  (`test_accumulate_gate_migration.py`) documents which ones would currently
  fail the gate, as a re-review list for the agent.
- `dcf_scenarios.py`'s discount rate is no longer always 10% — any tooling
  or documentation that assumed a flat rate must account for `--wacc-file`
  now being the normal path (an explicit `--discount-rate` still overrides
  it for reproducing old runs).
```

- [ ] **Step 7: Run the full backend test suite plus `run_tests.py` to confirm no regressions**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/ -v`
Expected: PASS — every test file in `tests/py_services/`, old and new.

Run: `cd /Users/richardfremmerlid/Projects/InvestmentToolkit && python3 run_tests.py`
Expected: `All gates passed.` (T0 TypeScript/Python/Node syntax, path regression, symlink/CWD invariance, map debt, T0.5 bridge smoke — none of these tasks touched anything those gates check beyond new syntactically-valid Python files and new symlinks, both of which the gates are designed to catch if broken).

- [ ] **Step 8: Commit**

```bash
git add investment_screener/backend/data/projections/CORZ.json investment_screener/backend/data/projections/PANW.json \
  investment_screener/backend/data/projections/CRWV.json investment_screener/backend/data/projections/NBIS.json \
  investment_screener/backend/data/projections/BE.json investment_screener/backend/data/projections/SNDK.json \
  investment_screener/backend/data/projections/CEG.json investment_screener/backend/data/projections/OKLO.json \
  investment_screener/backend/data/projections/APLD.json investment_screener/backend/data/projections/MSFT.json \
  plugins/stock-valuation/skills/stock_valuation/SKILL.md docs/architecture/ADR-valuation-committee.md \
  investment_screener/backend/tests/py_services/test_accumulate_gate_migration.py
git commit -m "feat: seed comps peer lists, wire valuation-committee skill steps, add ADR"
```

---

## Post-Plan: Branch & Handoff (per this repo's established Phase 1 pattern)

After Task 8's whole-branch review passes (see `superpowers:subagent-driven-development`'s review cadence), follow the same git policy documented in `start_here.md`:

1. Merge the completed work to local `main`.
2. Push a dedicated backup branch: `git push origin main:feature/fable5-phase2a-valuation-committee` (or check out a branch named `feature/fable5-phase2a-valuation-committee` first, then push it — do not push directly to `origin/main`).
3. **Stop there.** Report the branch is ready. Do not merge or open a PR into `origin/main` — the user reviews and merges via GitHub's PR flow on their own timing, per the standing policy set after Phase 1.
