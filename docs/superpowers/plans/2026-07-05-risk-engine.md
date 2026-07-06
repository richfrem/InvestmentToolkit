# Phase 3, Sub-Spec 1 — Portfolio Risk Engine (E1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `risk_engine.py` — a portfolio risk snapshot (correlation, annualized vol/beta,
marginal risk contribution, concentration, pillar cluster exposure, 2022 stress replay,
parametric+historical VaR/CVaR) computed from current actual weights — and wire a compact
`RISK:` line into the `/daily` morning brief.

**Architecture:** One new `py_services/risk_engine.py` (real file, not a plugin symlink —
matches `macro_regime.py`/`framework_score.py`/`technicals.py` precedent for cross-cutting
portfolio analytics with no single plugin owner). Pure `compute_*` functions, each
independently testable with hand-verifiable fixtures, composed by one orchestrator
(`compute_risk_snapshot()`) that reads `target-portfolio.json` + `portfolio.json`, fetches
prices via the existing `market_data.get_prices()`, and writes `data/risk_snapshot.json`.
One small wiring change to `daily_brief.py`'s `run()`/`render()`.

**Tech Stack:** Python 3, pandas (already in `requirements.in`), `math` stdlib (no scipy —
VaR/CVaR z-scores and normal-PDF are hardcoded/hand-computed to avoid a new dependency,
same "avoid heavyweight libs" philosophy `technicals.py` already documents), pytest.

## Global Constraints

- TDD non-negotiable: every task writes the failing test before the implementation.
- No inline financial math anywhere outside `py_services/` — every number must be
  reproducible by re-running `risk_engine.py` with logged inputs.
- Dual-layer docs on every non-trivial function (external comment + docstring), file header,
  full type hints, snake_case, refactor at 50+ lines or 3+ nesting levels — per
  `.agent/rules/coding-conventions.md`.
- Never coerce a missing/NaN upstream value to zero or fabricate a return for a missing
  price day — omit/exclude with a `warnings` entry, matching `framework_score.py`'s
  reweighting convention.
- Current weights always come from `portfolio_io.compute_weights()` against the
  broker-authoritative `total_usd` — never re-derived from raw shares×price (`CLAUDE.md`
  pitfall #27 / the standing portfolio-total-validation rule).
- `ticker` key, not `symbol`, when reading `target-portfolio.json` holdings.
- Spec: `docs/superpowers/specs/2026-07-05-risk-engine-design.md` — read it before Task 1 if
  anything below is ambiguous; the design doc is the tie-breaker.

## Documented simplifications (carried forward from design; not open questions)

1. **Benchmark is SPY only** — no QQQ dual-beta in this pass, matching `macro_regime.py`/
   `technicals.py`'s existing single-benchmark convention.
2. **Stress replay uses current weights held static** across the whole historical window
   (true historical weights aren't tracked anywhere in the system) — an explicit,
   documented approximation, not a bug.
3. **Cluster exposure uses the existing curated `pillarId` taxonomy** from
   `target-portfolio.json`, not a correlation-derived clustering algorithm.
4. **Correlation/vol/beta/MRC/VaR use a 2-year window; stress replay uses a separate 5-year
   fetch** — a 2y trailing window from today doesn't reach the named 2022 rate-shock
   scenario.
5. **VaR/CVaR z-scores and the normal PDF are hardcoded constants** (`Z_SCORES`,
   `_normal_pdf()`), not sourced from `scipy.stats` — scipy is not a declared dependency in
   `requirements.in` even though it may be present transitively in some environments; adding
   a new dependency isn't warranted for two constants and one closed-form PDF.
6. **This spec is backend-only** — `Risk.tsx` is an explicit fast-follow, not part of this
   plan (see design doc's Non-goals section).

---

### Task 1: `risk_engine.py` — returns matrix, correlation, portfolio vol/beta

**Files:**
- Create: `investment_screener/backend/py_services/risk_engine.py`
- Test: `investment_screener/backend/tests/py_services/test_risk_engine.py`

**Interfaces:**
- Consumes: nothing from other tasks (this is the foundational task).
- Produces (module-level, reused by every later task):
  - `_normalize_weights(weights: dict[str, float]) -> dict[str, float]`
  - `build_returns_matrix(prices: dict[str, dict], min_days: int = MIN_HISTORY_DAYS) -> tuple[pd.DataFrame, list[str]]`
  - `compute_correlation_matrix(returns: pd.DataFrame) -> dict[str, dict[str, float]]`
  - `_weighted_portfolio_returns(returns: pd.DataFrame, weights: dict[str, float], exclude: set[str] | None = None) -> pd.Series`
  - `compute_portfolio_vol_beta(returns: pd.DataFrame, weights: dict[str, float], benchmark: str) -> dict[str, float | None]`
  - Module constants: `MIN_HISTORY_DAYS = 60`, `Z_SCORES = {0.95: 1.645, 0.99: 2.326}`,
    `STRESS_WINDOWS = {"2022_rate_shock": ("2022-01-03", "2022-10-14")}`,
    `REPO_ROOT`, `DATA_DIR`, `TARGET_PATH`, `PORTFOLIO_PATH`, `RISK_SNAPSHOT_PATH`.

- [ ] **Step 1: Write the failing tests**

Create `investment_screener/backend/tests/py_services/test_risk_engine.py`:

```python
"""Tests for risk_engine.py — portfolio risk snapshot (Phase 3, E1)."""
import sys
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from risk_engine import (  # noqa: E402
    build_returns_matrix,
    compute_correlation_matrix,
    compute_portfolio_vol_beta,
)


def _price_rows(closes: list[float], start_day: int = 1) -> list[dict]:
    return [
        {"date": f"2026-01-{start_day + i:02d}", "open": c, "high": c, "low": c,
         "close": c, "volume": 1000.0}
        for i, c in enumerate(closes)
    ]


# ── build_returns_matrix ──────────────────────────────────────────────────────

def test_build_returns_matrix_aligns_and_computes_pct_change():
    closes_a = [100.0, 102.0, 101.0, 105.0, 104.0]
    closes_b = [50.0, 51.0, 50.5, 52.0, 51.5]
    prices = {"A": {"data": _price_rows(closes_a)}, "B": {"data": _price_rows(closes_b)}}

    returns, excluded = build_returns_matrix(prices, min_days=3)

    assert excluded == []
    assert set(returns.columns) == {"A", "B"}
    assert len(returns) == 4  # 5 closes -> 4 daily returns
    assert returns["A"].iloc[0] == pytest.approx((102.0 - 100.0) / 100.0)
    assert returns["B"].iloc[0] == pytest.approx((51.0 - 50.0) / 50.0)


def test_build_returns_matrix_excludes_short_history_ticker():
    long_history = _price_rows([100.0 + i for i in range(90)])
    short_history = _price_rows([50.0, 51.0, 49.0], start_day=1)
    prices = {"LONG": {"data": long_history}, "SHORT": {"data": short_history}}

    returns, excluded = build_returns_matrix(prices, min_days=60)

    assert excluded == ["SHORT"]
    assert "SHORT" not in returns.columns
    assert returns.empty  # only 1 ticker survives -> need 2+ to build a matrix


def test_build_returns_matrix_returns_empty_for_fewer_than_two_tickers():
    prices = {"ONLY": {"data": _price_rows([100.0] * 90)}}
    returns, excluded = build_returns_matrix(prices, min_days=60)
    assert returns.empty
    assert excluded == []


def test_build_returns_matrix_inner_joins_on_mismatched_dates():
    # A trades every day; B is missing 2026-01-03 (e.g. TSX holiday).
    rows_a = _price_rows([100.0, 101.0, 102.0, 103.0, 104.0], start_day=1)
    rows_b = [
        {"date": "2026-01-01", "open": 50.0, "high": 50.0, "low": 50.0, "close": 50.0, "volume": 1000.0},
        {"date": "2026-01-02", "open": 51.0, "high": 51.0, "low": 51.0, "close": 51.0, "volume": 1000.0},
        {"date": "2026-01-04", "open": 52.0, "high": 52.0, "low": 52.0, "close": 52.0, "volume": 1000.0},
        {"date": "2026-01-05", "open": 53.0, "high": 53.0, "low": 53.0, "close": 53.0, "volume": 1000.0},
    ]
    prices = {"A": {"data": rows_a}, "B": {"data": rows_b}}

    returns, excluded = build_returns_matrix(prices, min_days=3)

    assert excluded == []
    # 2026-01-03 dropped for both (B has no row that day) -> 3 aligned dates -> 2 returns
    assert len(returns) == 2


# ── compute_correlation_matrix ───────────────────────────────────────────────

def test_correlation_matrix_identical_series_is_one():
    returns = pd.DataFrame({"A": [0.01, -0.02, 0.03, 0.01], "B": [0.01, -0.02, 0.03, 0.01]})
    corr = compute_correlation_matrix(returns)
    assert corr["A"]["B"] == 1.0
    assert corr["B"]["A"] == 1.0
    assert "A" not in corr["A"]  # no self-entry


def test_correlation_matrix_inverse_series_is_negative_one():
    returns = pd.DataFrame({"A": [0.01, -0.02, 0.03, 0.01], "B": [-0.01, 0.02, -0.03, -0.01]})
    corr = compute_correlation_matrix(returns)
    assert corr["A"]["B"] == -1.0


def test_correlation_matrix_empty_for_single_ticker():
    returns = pd.DataFrame({"A": [0.01, -0.02, 0.03]})
    assert compute_correlation_matrix(returns) == {}


# ── compute_portfolio_vol_beta ───────────────────────────────────────────────

def test_vol_beta_beta_is_one_when_portfolio_matches_benchmark_exactly():
    spy_returns = [0.01, -0.02, 0.015, 0.005, -0.01, 0.02]
    returns = pd.DataFrame({"SPY": spy_returns, "A": spy_returns})
    result = compute_portfolio_vol_beta(returns, {"A": 1.0}, benchmark="SPY")

    assert result["beta"] == pytest.approx(1.0, abs=1e-6)
    expected_vol = pd.Series(spy_returns).std(ddof=1) * (252 ** 0.5)
    assert result["vol"] == pytest.approx(expected_vol, abs=1e-4)


def test_vol_beta_returns_none_when_benchmark_missing():
    returns = pd.DataFrame({"A": [0.01, -0.02, 0.03]})
    result = compute_portfolio_vol_beta(returns, {"A": 1.0}, benchmark="SPY")
    assert result == {"vol": None, "beta": None}


def test_vol_beta_ignores_tickers_with_no_weight():
    spy_returns = [0.01, -0.02, 0.015, 0.005, -0.01, 0.02]
    returns = pd.DataFrame({
        "SPY": spy_returns, "A": spy_returns,
        "B": [0.5, -0.5, 0.5, -0.5, 0.5, -0.5],
    })
    # No weight entry for B -> must not affect beta despite wild returns.
    result = compute_portfolio_vol_beta(returns, {"A": 1.0}, benchmark="SPY")
    assert result["beta"] == pytest.approx(1.0, abs=1e-6)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_risk_engine.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'risk_engine'`.

- [ ] **Step 3: Write minimal implementation**

Create `investment_screener/backend/py_services/risk_engine.py`:

```python
#!/usr/bin/env python3
"""
risk_engine.py (Python Service)
=====================================

Purpose:
    Portfolio-level risk snapshot: correlation matrix, annualized volatility
    and beta (current actual weights), marginal risk contribution per
    holding, concentration (HHI/top-3/effective N), pillar-level cluster
    exposure, historical stress replay (2022 rate shock + worst drawdown),
    and parametric + historical VaR/CVaR (95%/99%, 1-day horizon, labeled
    as estimates). Informational only — does not gate any action. See
    docs/superpowers/specs/2026-07-05-risk-engine-design.md.

Layer: Backend / Python Services / Risk

Usage:
    python3 risk_engine.py --pretty
    python3 risk_engine.py --benchmark SPY --no-save --pretty
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = REPO_ROOT / "investment_screener/backend/data"
TARGET_PATH = DATA_DIR / "theses/target-portfolio.json"
PORTFOLIO_PATH = DATA_DIR / "portfolio.json"
RISK_SNAPSHOT_PATH = DATA_DIR / "risk_snapshot.json"

MIN_HISTORY_DAYS = 60
Z_SCORES = {0.95: 1.645, 0.99: 2.326}
STRESS_WINDOWS = {"2022_rate_shock": ("2022-01-03", "2022-10-14")}


def _normalize_weights(weights: dict[str, float]) -> dict[str, float]:
    """Renormalize a weight subset to sum to 1.0.

    Used whenever a calc operates on a subset of holdings (e.g. after
    excluding tickers with insufficient price history) so the remaining
    weights still sum to 1.0 rather than silently understating exposure.

    Args:
        weights: {ticker: weight_fraction}, need not sum to 1.0.

    Returns:
        {ticker: weight_fraction} summing to 1.0, or {} if input is empty
        or sums to <= 0.
    """
    total = sum(weights.values())
    if total <= 0:
        return {}
    return {t: w / total for t, w in weights.items()}


def build_returns_matrix(
    prices: dict[str, dict], min_days: int = MIN_HISTORY_DAYS
) -> tuple[pd.DataFrame, list[str]]:
    """Build a date-aligned daily-return matrix from get_prices() output.

    Tickers with fewer than `min_days` price rows are excluded before
    alignment — a single short-history ticker (recent IPO, delisted) must
    never collapse everyone else's sample window down to its own. Excluded
    tickers are returned separately so callers can surface a warning rather
    than silently shrinking the window.

    Args:
        prices: get_prices() output, {ticker: {"data": [...]}}.
        min_days: Minimum row count to include a ticker.

    Returns:
        (returns_df, excluded_tickers) — returns_df has dates (ISO strings,
        sorted) as index, tickers as columns, no NaN values (inner join
        across included tickers' dates); empty DataFrame if fewer than 2
        tickers have enough history to align.
    """
    closes: dict[str, pd.Series] = {}
    excluded: list[str] = []
    for ticker, payload in prices.items():
        rows = payload.get("data", [])
        if len(rows) < min_days:
            excluded.append(ticker)
            continue
        df = pd.DataFrame(rows)[["date", "close"]].set_index("date")
        closes[ticker] = df["close"]

    if len(closes) < 2:
        return pd.DataFrame(), excluded

    combined = pd.DataFrame(closes).sort_index().dropna(how="any")
    returns = combined.pct_change().iloc[1:]
    return returns, excluded


def compute_correlation_matrix(returns: pd.DataFrame) -> dict[str, dict[str, float]]:
    """Ticker x ticker Pearson correlation of daily returns.

    Args:
        returns: Aligned daily-return DataFrame from build_returns_matrix().

    Returns:
        {ticker: {other_ticker: correlation}} excluding the diagonal (a
        ticker is never listed against itself); {} if fewer than 2 tickers.
    """
    if returns.shape[1] < 2:
        return {}
    corr = returns.corr()
    return {
        t: {u: round(float(corr.loc[t, u]), 4) for u in corr.columns if u != t}
        for t in corr.index
    }


def _weighted_portfolio_returns(
    returns: pd.DataFrame, weights: dict[str, float], exclude: set[str] | None = None
) -> pd.Series:
    """Build the weighted daily portfolio-return series from a returns matrix.

    Args:
        returns: Aligned daily-return DataFrame (may include a benchmark column).
        weights: {ticker: weight_fraction}, need not sum to 1.0 or cover
            every column in `returns` — only tickers present in both
            `returns.columns` and `weights` (minus `exclude`) contribute.
        exclude: Column names to never treat as holdings (e.g. the benchmark).

    Returns:
        A pandas Series of weighted daily returns, empty if no ticker qualifies.
    """
    exclude = exclude or set()
    tickers = [t for t in returns.columns if t in weights and t not in exclude]
    if not tickers:
        return pd.Series(dtype=float)
    normalized = _normalize_weights({t: weights[t] for t in tickers})
    if not normalized:
        return pd.Series(dtype=float)
    return sum(returns[t] * w for t, w in normalized.items())


def compute_portfolio_vol_beta(
    returns: pd.DataFrame, weights: dict[str, float], benchmark: str
) -> dict[str, float | None]:
    """Annualized portfolio volatility and beta vs. the benchmark.

    Args:
        returns: Aligned daily-return DataFrame, must include `benchmark`'s column.
        weights: {ticker: weight_fraction} for holdings (benchmark excluded automatically).
        benchmark: Benchmark ticker column name (e.g. "SPY").

    Returns:
        {"vol": annualized_stdev_or_None, "beta": beta_or_None}. None for
        either field if the benchmark is missing or fewer than 2 return
        observations are available.
    """
    portfolio_returns = _weighted_portfolio_returns(returns, weights, exclude={benchmark})
    if portfolio_returns.empty or benchmark not in returns.columns or len(portfolio_returns) < 2:
        return {"vol": None, "beta": None}

    vol = float(portfolio_returns.std(ddof=1) * (252 ** 0.5))
    bench_returns = returns[benchmark]
    bench_var = float(bench_returns.var(ddof=1))
    covariance = float(portfolio_returns.cov(bench_returns))
    beta = covariance / bench_var if bench_var > 0 else None

    return {
        "vol": round(vol, 4),
        "beta": round(beta, 3) if beta is not None else None,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_risk_engine.py -v`
Expected: PASS — all tests green.

- [ ] **Step 5: Commit**

```bash
git add investment_screener/backend/py_services/risk_engine.py investment_screener/backend/tests/py_services/test_risk_engine.py
git commit -m "feat: add risk_engine.py — returns matrix, correlation, portfolio vol/beta"
```

---

### Task 2: `risk_engine.py` — marginal risk contribution + concentration

**Files:**
- Modify: `investment_screener/backend/py_services/risk_engine.py`
- Modify: `investment_screener/backend/tests/py_services/test_risk_engine.py`

**Interfaces:**
- Consumes: `_normalize_weights(weights) -> dict[str, float]` (Task 1).
- Produces:
  - `compute_marginal_risk_contribution(returns: pd.DataFrame, weights: dict[str, float], benchmark: str) -> dict[str, float]`
  - `compute_concentration(weights: dict[str, float]) -> dict[str, float | None]`

- [ ] **Step 1: Write the failing tests**

Append to `investment_screener/backend/tests/py_services/test_risk_engine.py`:

```python
from risk_engine import (  # noqa: E402
    compute_concentration,
    compute_marginal_risk_contribution,
)


# ── compute_marginal_risk_contribution ───────────────────────────────────────

def test_mrc_sums_to_one_property():
    returns = pd.DataFrame({
        "A": [0.01, -0.02, 0.015, 0.005, -0.01, 0.02, 0.01, -0.005],
        "B": [0.02, -0.01, 0.005, 0.015, -0.02, 0.01, -0.005, 0.02],
        "C": [-0.01, 0.02, -0.015, 0.01, 0.005, -0.02, 0.015, -0.01],
    })
    weights = {"A": 0.5, "B": 0.3, "C": 0.2}
    mrc = compute_marginal_risk_contribution(returns, weights, benchmark="SPY")
    assert sum(mrc.values()) == pytest.approx(1.0, abs=1e-6)
    assert set(mrc.keys()) == {"A", "B", "C"}


def test_mrc_zero_variance_ticker_contributes_zero():
    returns = pd.DataFrame({
        "A": [0.01, -0.02, 0.015, 0.005, -0.01, 0.02],
        "FLAT": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    })
    weights = {"A": 0.7, "FLAT": 0.3}
    mrc = compute_marginal_risk_contribution(returns, weights, benchmark="SPY")
    assert mrc["FLAT"] == 0.0


def test_mrc_returns_empty_for_single_holding():
    returns = pd.DataFrame({"A": [0.01, -0.02, 0.015]})
    assert compute_marginal_risk_contribution(returns, {"A": 1.0}, benchmark="SPY") == {}


# ── compute_concentration ─────────────────────────────────────────────────────

def test_concentration_known_weights():
    weights = {"A": 0.5, "B": 0.3, "C": 0.2}
    result = compute_concentration(weights)
    assert result["hhi"] == pytest.approx(0.25 + 0.09 + 0.04)
    assert result["top3Weight"] == 1.0
    assert result["effectiveN"] == pytest.approx(1 / 0.38, abs=1e-2)


def test_concentration_renormalizes_non_100pct_input():
    weights = {"A": 50.0, "B": 30.0, "C": 20.0}  # e.g. raw 0-100 scale weights
    result = compute_concentration(weights)
    assert result["hhi"] == pytest.approx(0.25 + 0.09 + 0.04)


def test_concentration_empty_input_returns_none_shape():
    assert compute_concentration({}) == {"hhi": None, "top3Weight": None, "effectiveN": None}


def test_concentration_top3_with_more_than_three_holdings():
    weights = {"A": 0.4, "B": 0.3, "C": 0.15, "D": 0.15}
    result = compute_concentration(weights)
    assert result["top3Weight"] == pytest.approx(0.85)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_risk_engine.py -v -k "mrc or concentration"`
Expected: FAIL — `ImportError: cannot import name 'compute_marginal_risk_contribution'`.

- [ ] **Step 3: Write minimal implementation**

Append to `investment_screener/backend/py_services/risk_engine.py` (after `compute_portfolio_vol_beta`):

```python
def compute_marginal_risk_contribution(
    returns: pd.DataFrame, weights: dict[str, float], benchmark: str
) -> dict[str, float]:
    """Fraction of total portfolio variance contributed by each holding.

    MRC_i = w_i * (Sigma . w)_i / portfolio_variance, so the returned
    values always sum to 1.0 across included holdings (100% of variance
    decomposed) — this is the property that makes "MRC leader: NVDA 18%"
    a meaningful sentence rather than an arbitrary score.

    Args:
        returns: Aligned daily-return DataFrame, may include a benchmark column.
        weights: {ticker: weight_fraction}.
        benchmark: Benchmark column name to exclude from the holdings set.

    Returns:
        {ticker: fraction_of_variance}, {} if fewer than 2 holdings qualify
        or portfolio variance is 0.
    """
    tickers = [t for t in returns.columns if t in weights and t != benchmark]
    if len(tickers) < 2:
        return {}
    normalized = _normalize_weights({t: weights[t] for t in tickers})
    if not normalized:
        return {}

    cov_matrix = returns[tickers].cov() * 252  # annualize
    w = pd.Series(normalized).reindex(tickers)
    portfolio_variance = float(w @ cov_matrix @ w)
    if portfolio_variance <= 0:
        return {}

    marginal = cov_matrix @ w  # per-ticker (Sigma . w)
    contribution = (w * marginal) / portfolio_variance
    return {t: round(float(contribution[t]), 4) for t in tickers}


def compute_concentration(weights: dict[str, float]) -> dict[str, float | None]:
    """Herfindahl-Hirschman Index, top-3 weight, and effective N.

    Args:
        weights: {ticker: weight_fraction}, need not sum to 1.0 (renormalized
            internally so a partial/excluded-tickers input is still meaningful).

    Returns:
        {"hhi", "top3Weight", "effectiveN"} — all None if weights is empty
        or sums to <= 0.
    """
    normalized = _normalize_weights(weights)
    if not normalized:
        return {"hhi": None, "top3Weight": None, "effectiveN": None}

    values = sorted(normalized.values(), reverse=True)
    hhi = sum(w * w for w in values)
    top3 = sum(values[:3])
    effective_n = 1 / hhi if hhi > 0 else None

    return {
        "hhi": round(hhi, 4),
        "top3Weight": round(top3, 4),
        "effectiveN": round(effective_n, 2) if effective_n is not None else None,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_risk_engine.py -v`
Expected: PASS — all tests in the file, not just the new ones (confirm no regression).

- [ ] **Step 5: Commit**

```bash
git add investment_screener/backend/py_services/risk_engine.py investment_screener/backend/tests/py_services/test_risk_engine.py
git commit -m "feat: add marginal risk contribution + concentration to risk_engine.py"
```

---

### Task 3: `risk_engine.py` — pillar cluster exposure

**Files:**
- Modify: `investment_screener/backend/py_services/risk_engine.py`
- Modify: `investment_screener/backend/tests/py_services/test_risk_engine.py`

**Interfaces:**
- Consumes: `_normalize_weights(weights) -> dict[str, float]` (Task 1); the `mrc` dict shape
  produced by `compute_marginal_risk_contribution()` (Task 2) — `{ticker: fraction}`.
- Produces: `compute_cluster_exposure(weights: dict[str, float], pillar_map: dict[str, str], mrc: dict[str, float]) -> list[dict[str, Any]]`

- [ ] **Step 1: Write the failing tests**

Append to `investment_screener/backend/tests/py_services/test_risk_engine.py`:

```python
from risk_engine import compute_cluster_exposure  # noqa: E402


def test_cluster_exposure_groups_by_pillar():
    weights = {"NVDA": 0.4, "CRWV": 0.2, "PANW": 0.25, "CBRS": 0.15}
    pillar_map = {"NVDA": "ai_infra", "CRWV": "ai_infra", "PANW": "cyber", "CBRS": "cyber"}
    mrc = {"NVDA": 0.5, "CRWV": 0.22, "PANW": 0.2, "CBRS": 0.08}

    result = compute_cluster_exposure(weights, pillar_map, mrc)

    ai = next(r for r in result if r["pillarId"] == "ai_infra")
    cyber = next(r for r in result if r["pillarId"] == "cyber")
    assert ai["weight"] == pytest.approx(0.6)
    assert ai["varianceContributionPct"] == pytest.approx(72.0)
    assert cyber["weight"] == pytest.approx(0.4)
    assert cyber["varianceContributionPct"] == pytest.approx(28.0)
    assert result[0]["pillarId"] == "ai_infra"  # sorted by weight descending


def test_cluster_exposure_unassigned_pillar():
    result = compute_cluster_exposure({"NEWTICKER": 1.0}, pillar_map={}, mrc={"NEWTICKER": 1.0})
    assert result == [{"pillarId": "unassigned", "weight": 1.0, "varianceContributionPct": 100.0}]


def test_cluster_exposure_empty_weights_returns_empty_list():
    assert compute_cluster_exposure({}, {}, {}) == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_risk_engine.py -v -k cluster`
Expected: FAIL — `ImportError: cannot import name 'compute_cluster_exposure'`.

- [ ] **Step 3: Write minimal implementation**

Append to `investment_screener/backend/py_services/risk_engine.py`:

```python
from typing import Any  # add to the existing import block near the top of the file


def compute_cluster_exposure(
    weights: dict[str, float], pillar_map: dict[str, str], mrc: dict[str, float]
) -> list[dict[str, Any]]:
    """Pillar-level weight and variance-contribution exposure.

    Groups holdings by their existing target-portfolio.json `pillarId` (the
    curated taxonomy, not a correlation-derived cluster) and sums weight and
    marginal-risk-contribution within each pillar. Produces the "72% of
    portfolio variance from one cluster" sentence.

    Args:
        weights: {ticker: weight_fraction}, need not sum to 1.0.
        pillar_map: {ticker: pillarId}, from target-portfolio.json holdings.
        mrc: Output of compute_marginal_risk_contribution() — {ticker: fraction}.

    Returns:
        List of {"pillarId", "weight", "varianceContributionPct"}, sorted by
        weight descending. A ticker with no pillarId entry is grouped under
        "unassigned". Weight is renormalized over the supplied weights dict.
    """
    normalized = _normalize_weights(weights)
    if not normalized:
        return []

    pillar_weight: dict[str, float] = {}
    pillar_mrc: dict[str, float] = {}
    for ticker, weight in normalized.items():
        pillar = pillar_map.get(ticker, "unassigned")
        pillar_weight[pillar] = pillar_weight.get(pillar, 0.0) + weight
        pillar_mrc[pillar] = pillar_mrc.get(pillar, 0.0) + mrc.get(ticker, 0.0)

    result = [
        {
            "pillarId": pillar,
            "weight": round(pillar_weight[pillar], 4),
            "varianceContributionPct": round(pillar_mrc[pillar] * 100, 2),
        }
        for pillar in pillar_weight
    ]
    return sorted(result, key=lambda r: r["weight"], reverse=True)
```

Note: `Any` must be imported once at the top of `risk_engine.py` (`from typing import Any`)
— add it to the existing `import` block, not as a duplicate inline import.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_risk_engine.py -v`
Expected: PASS — all tests in the file.

- [ ] **Step 5: Commit**

```bash
git add investment_screener/backend/py_services/risk_engine.py investment_screener/backend/tests/py_services/test_risk_engine.py
git commit -m "feat: add pillar cluster exposure to risk_engine.py"
```

---

### Task 4: `risk_engine.py` — stress replay (2022 rate shock + worst drawdown)

**Files:**
- Modify: `investment_screener/backend/py_services/risk_engine.py`
- Modify: `investment_screener/backend/tests/py_services/test_risk_engine.py`

**Interfaces:**
- Consumes: `_weighted_portfolio_returns(returns, weights, exclude)` (Task 1), `STRESS_WINDOWS` constant (Task 1).
- Produces: `compute_stress_replay(returns_5y: pd.DataFrame, weights: dict[str, float], benchmark: str = "SPY") -> list[dict[str, Any]]`

- [ ] **Step 1: Write the failing tests**

Append to `investment_screener/backend/tests/py_services/test_risk_engine.py`:

```python
from risk_engine import compute_stress_replay  # noqa: E402


def _build_return_series(dates_closes: list[tuple[str, float]]) -> pd.DataFrame:
    dates = [d for d, _ in dates_closes]
    closes = [c for _, c in dates_closes]
    df = pd.DataFrame({"A": closes}, index=dates)
    return df.pct_change().iloc[1:]


def test_stress_replay_2022_rate_shock_window():
    dates_closes = [
        ("2022-01-03", 100.0), ("2022-04-01", 90.0),
        ("2022-07-01", 80.0), ("2022-10-14", 70.0), ("2023-01-01", 90.0),
    ]
    returns = _build_return_series(dates_closes)
    result = compute_stress_replay(returns, {"A": 1.0}, benchmark="SPY")

    shock = next(r for r in result if r["scenario"] == "2022_rate_shock")
    assert shock["window"] == ["2022-01-03", "2022-10-14"]
    assert shock["portfolioReturnPct"] == pytest.approx((70.0 / 100.0 - 1) * 100)


def test_stress_replay_worst_drawdown_finds_largest_decline():
    dates_closes = [
        ("2021-01-01", 100.0), ("2021-06-01", 120.0),   # peak
        ("2021-12-01", 60.0),                            # big trough (-50%)
        ("2022-06-01", 100.0), ("2022-10-14", 95.0),     # smaller decline inside named window
        ("2023-01-01", 110.0),
    ]
    returns = _build_return_series(dates_closes)
    result = compute_stress_replay(returns, {"A": 1.0}, benchmark="SPY")

    drawdown = next(r for r in result if r["scenario"] == "worst_drawdown")
    assert drawdown["window"] == ["2021-06-01", "2021-12-01"]
    assert drawdown["portfolioReturnPct"] == pytest.approx((60.0 / 120.0 - 1) * 100)


def test_stress_replay_omits_2022_scenario_when_data_doesnt_cover_it():
    dates_closes = [("2024-01-01", 100.0), ("2024-06-01", 110.0), ("2024-12-01", 105.0)]
    returns = _build_return_series(dates_closes)
    result = compute_stress_replay(returns, {"A": 1.0}, benchmark="SPY")
    assert not any(r["scenario"] == "2022_rate_shock" for r in result)
    assert any(r["scenario"] == "worst_drawdown" for r in result)


def test_stress_replay_empty_for_no_qualifying_holdings():
    returns = pd.DataFrame({"SPY": [0.01, -0.02, 0.03]})
    assert compute_stress_replay(returns, {"A": 1.0}, benchmark="SPY") == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_risk_engine.py -v -k stress`
Expected: FAIL — `ImportError: cannot import name 'compute_stress_replay'`.

- [ ] **Step 3: Write minimal implementation**

Append to `investment_screener/backend/py_services/risk_engine.py`:

```python
def compute_stress_replay(
    returns_5y: pd.DataFrame, weights: dict[str, float], benchmark: str = "SPY"
) -> list[dict[str, Any]]:
    """Portfolio P&L through the 2022 rate-shock window plus the worst
    drawdown found anywhere in the supplied 5-year return history.

    Current weights are held static across the whole replay window — a
    documented simplifying assumption (true historical weights aren't
    tracked anywhere in the system; see design doc).

    Args:
        returns_5y: Aligned daily-return DataFrame spanning ~5 years, must
            include `benchmark`'s column (excluded from holdings).
        weights: {ticker: weight_fraction} for current holdings.
        benchmark: Benchmark column name to exclude from holdings.

    Returns:
        List of scenario dicts: [{"scenario", "window": [start, end],
        "portfolioReturnPct"}, ...]. 2022_rate_shock is omitted entirely if
        the supplied data doesn't cover that window. worst_drawdown is
        omitted if the portfolio-return series is empty.
    """
    portfolio_returns = _weighted_portfolio_returns(returns_5y, weights, exclude={benchmark})
    if portfolio_returns.empty:
        return []

    results: list[dict[str, Any]] = []
    for scenario, (start, end) in STRESS_WINDOWS.items():
        window = portfolio_returns.loc[
            (portfolio_returns.index >= start) & (portfolio_returns.index <= end)
        ]
        if window.empty:
            continue
        window_cum = (1 + window).cumprod()
        pct_return = float((window_cum.iloc[-1] - 1) * 100)
        results.append({
            "scenario": scenario,
            "window": [start, end],
            "portfolioReturnPct": round(pct_return, 2),
        })

    cumulative = (1 + portfolio_returns).cumprod()
    running_max = cumulative.cummax()
    drawdown = (cumulative - running_max) / running_max
    trough_date = drawdown.idxmin()
    peak_date = cumulative.loc[:trough_date].idxmax()
    results.append({
        "scenario": "worst_drawdown",
        "window": [peak_date, trough_date],
        "portfolioReturnPct": round(float(drawdown.min() * 100), 2),
    })

    return results
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_risk_engine.py -v`
Expected: PASS — all tests in the file.

- [ ] **Step 5: Commit**

```bash
git add investment_screener/backend/py_services/risk_engine.py investment_screener/backend/tests/py_services/test_risk_engine.py
git commit -m "feat: add stress replay (2022 rate shock + worst drawdown) to risk_engine.py"
```

---

### Task 5: `risk_engine.py` — parametric + historical VaR/CVaR

**Files:**
- Modify: `investment_screener/backend/py_services/risk_engine.py`
- Modify: `investment_screener/backend/tests/py_services/test_risk_engine.py`

**Interfaces:**
- Consumes: `Z_SCORES` constant (Task 1). Takes a plain `pd.Series` (the caller builds it via
  `_weighted_portfolio_returns()`).
- Produces:
  - `_normal_pdf(z: float) -> float`
  - `compute_var_cvar(portfolio_returns: pd.Series, confidences: tuple[float, ...] = (0.95, 0.99)) -> dict[str, dict[str, dict[str, float]]]`

- [ ] **Step 1: Write the failing tests**

Append to `investment_screener/backend/tests/py_services/test_risk_engine.py`:

```python
from risk_engine import compute_var_cvar  # noqa: E402

_SAMPLE_RETURNS = [
    0.02, -0.03, 0.01, -0.05, 0.015, -0.01, 0.03, -0.02, 0.005, -0.04,
    0.01, -0.015, 0.025, -0.01, 0.005, -0.03, 0.02, -0.005, 0.01, -0.02,
]


def test_var_cvar_cvar_worse_than_var_property():
    result = compute_var_cvar(pd.Series(_SAMPLE_RETURNS))
    for method in ("parametric", "historical"):
        for level in ("p95", "p99"):
            assert result["cvar"][method][level] <= result["var"][method][level]


def test_var_cvar_p99_more_extreme_than_p95():
    result = compute_var_cvar(pd.Series(_SAMPLE_RETURNS))
    assert result["var"]["parametric"]["p99"] <= result["var"]["parametric"]["p95"]
    assert result["var"]["historical"]["p99"] <= result["var"]["historical"]["p95"]


def test_var_cvar_historical_matches_quantile_definition():
    portfolio_returns = pd.Series([
        0.05, 0.03, 0.01, -0.01, -0.03, -0.05, 0.02, -0.02, 0.04, -0.04,
        0.0, 0.015, -0.015, 0.025, -0.025, 0.035, -0.035, 0.045, -0.045, 0.005,
    ])
    result = compute_var_cvar(portfolio_returns)
    expected_p95 = round(float(portfolio_returns.quantile(0.05)), 4)
    assert result["var"]["historical"]["p95"] == pytest.approx(expected_p95)


def test_var_cvar_empty_for_insufficient_data():
    result = compute_var_cvar(pd.Series([0.01]))
    assert result["var"]["parametric"] == {}
    assert result["var"]["historical"] == {}
    assert result["cvar"]["parametric"] == {}
    assert result["cvar"]["historical"] == {}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_risk_engine.py -v -k var_cvar`
Expected: FAIL — `ImportError: cannot import name 'compute_var_cvar'`.

- [ ] **Step 3: Write minimal implementation**

Add `import math` to the top of `investment_screener/backend/py_services/risk_engine.py`
(alongside the existing `import sys` / `from pathlib import Path`), then append:

```python
def _normal_pdf(z: float) -> float:
    """Standard normal probability density at z (no scipy dependency — see
    design doc's documented simplification on avoiding a new dependency
    for two constants and one closed-form density).
    """
    return math.exp(-0.5 * z * z) / math.sqrt(2 * math.pi)


def compute_var_cvar(
    portfolio_returns: pd.Series, confidences: tuple[float, ...] = (0.95, 0.99)
) -> dict[str, dict[str, dict[str, float]]]:
    """Parametric and historical VaR/CVaR at the given confidence levels.

    Parametric assumes daily returns are normally distributed (mean, std of
    the supplied series); the expected-shortfall (CVaR) closed form is
    mean - std * (phi(z) / (1 - confidence)). Historical uses the empirical
    return distribution directly (no distributional assumption). Both are
    1-day-horizon figures — the caller (compute_risk_snapshot) is
    responsible for labeling them as estimates in the output, not this
    function, which has no opinion on presentation.

    Args:
        portfolio_returns: Daily weighted portfolio-return series (e.g.
            from _weighted_portfolio_returns()).
        confidences: Confidence levels to compute, e.g. (0.95, 0.99).

    Returns:
        {"var": {"parametric": {"p95": ..., "p99": ...}, "historical": {...}},
         "cvar": {"parametric": {...}, "historical": {...}}}. All values are
         negative-or-zero (a loss). Empty nested dicts if `portfolio_returns`
         has fewer than 2 observations.
    """
    empty = {
        "var": {"parametric": {}, "historical": {}},
        "cvar": {"parametric": {}, "historical": {}},
    }
    if len(portfolio_returns) < 2:
        return empty

    mean = float(portfolio_returns.mean())
    std = float(portfolio_returns.std(ddof=1))

    var_parametric: dict[str, float] = {}
    var_historical: dict[str, float] = {}
    cvar_parametric: dict[str, float] = {}
    cvar_historical: dict[str, float] = {}

    for c in confidences:
        key = f"p{int(c * 100)}"
        z = Z_SCORES[c]

        var_param = mean - z * std
        es_param = mean - std * (_normal_pdf(z) / (1 - c))
        var_parametric[key] = round(var_param, 4)
        cvar_parametric[key] = round(es_param, 4)

        var_hist = float(portfolio_returns.quantile(1 - c))
        tail = portfolio_returns[portfolio_returns <= var_hist]
        cvar_hist = float(tail.mean()) if not tail.empty else var_hist
        var_historical[key] = round(var_hist, 4)
        cvar_historical[key] = round(cvar_hist, 4)

    return {
        "var": {"parametric": var_parametric, "historical": var_historical},
        "cvar": {"parametric": cvar_parametric, "historical": cvar_historical},
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_risk_engine.py -v`
Expected: PASS — all tests in the file.

- [ ] **Step 5: Commit**

```bash
git add investment_screener/backend/py_services/risk_engine.py investment_screener/backend/tests/py_services/test_risk_engine.py
git commit -m "feat: add parametric + historical VaR/CVaR to risk_engine.py"
```

---

### Task 6: `risk_engine.py` — `compute_risk_snapshot()` orchestrator + CLI

**Files:**
- Modify: `investment_screener/backend/py_services/risk_engine.py`
- Modify: `investment_screener/backend/tests/py_services/test_risk_engine.py`

**Interfaces:**
- Consumes: every `compute_*`/`_weighted_portfolio_returns`/`build_returns_matrix` function
  from Tasks 1–5; `market_data.get_prices(tickers, period, interval="1d") -> dict[str, dict]`;
  `portfolio_io.load_portfolio_state(path) -> dict` and
  `portfolio_io.compute_weights(shares, prices, total_usd) -> dict[str, float]`;
  `TARGET_PATH`/`PORTFOLIO_PATH`/`RISK_SNAPSHOT_PATH` constants (Task 1).
- Produces:
  `compute_risk_snapshot(target_portfolio_path: Path = TARGET_PATH, portfolio_path: Path = PORTFOLIO_PATH, benchmark: str = "SPY") -> dict[str, Any]`
  — the full snapshot dict, matching the design doc's `risk_snapshot.json` shape. This is
  what Task 7 (`daily_brief.py` wiring) imports and calls.

- [ ] **Step 1: Write the failing tests**

Append to `investment_screener/backend/tests/py_services/test_risk_engine.py`:

```python
import json
from unittest.mock import patch

from risk_engine import compute_risk_snapshot  # noqa: E402


def _write_target_portfolio(path: Path, holdings: list[dict]) -> None:
    path.write_text(json.dumps({"holdings": holdings, "pillars": []}))


def _write_portfolio(path: Path, shares: dict, prices: dict, total_usd: float) -> None:
    payload = {
        "holdings": [{"ticker": t, "shares": q, "price": prices[t]} for t, q in shares.items()],
        "totals": {"totalUSD": total_usd},
    }
    path.write_text(json.dumps(payload))


def _bdate_rows(n: int, start_price: float, drift: float) -> list[dict]:
    dates = pd.bdate_range("2024-01-01", periods=n)
    return [
        {"date": d.strftime("%Y-%m-%d"), "open": start_price + drift * i,
         "high": start_price + drift * i, "low": start_price + drift * i,
         "close": start_price + drift * i, "volume": 1000.0}
        for i, d in enumerate(dates)
    ]


def test_compute_risk_snapshot_full_shape(tmp_path):
    target_path = tmp_path / "target-portfolio.json"
    portfolio_path = tmp_path / "portfolio.json"
    _write_target_portfolio(target_path, [
        {"ticker": "NVDA", "pillarId": "ai_infra"},
        {"ticker": "PANW", "pillarId": "cyber"},
    ])
    _write_portfolio(
        portfolio_path,
        shares={"NVDA": 10.0, "PANW": 20.0},
        prices={"NVDA": 100.0, "PANW": 50.0},
        total_usd=2000.0,
    )

    nvda_rows = _bdate_rows(120, 100.0, 0.1)
    panw_rows = _bdate_rows(120, 50.0, 0.05)
    spy_rows = _bdate_rows(120, 400.0, 0.2)

    def fake_get_prices(tickers, period, interval="1d"):
        data = {"NVDA": nvda_rows, "PANW": panw_rows, "SPY": spy_rows}
        return {t: {"data": data[t]} for t in tickers if t in data}

    with patch("risk_engine.get_prices", side_effect=fake_get_prices):
        snapshot = compute_risk_snapshot(
            target_portfolio_path=target_path, portfolio_path=portfolio_path, benchmark="SPY",
        )

    expected_keys = {
        "asOf", "benchmark", "portfolioVol", "portfolioBeta", "correlationMatrix",
        "marginalRiskContribution", "concentration", "clusterExposure",
        "stressReplay", "var", "cvar", "warnings",
    }
    assert expected_keys <= set(snapshot.keys())
    assert snapshot["benchmark"] == "SPY"
    assert snapshot["portfolioVol"] is not None
    assert snapshot["portfolioBeta"] is not None
    assert set(snapshot["marginalRiskContribution"].keys()) == {"NVDA", "PANW"}
    assert snapshot["var"]["estimate"] is True
    assert snapshot["var"]["horizonDays"] == 1
    assert snapshot["cvar"]["estimate"] is True
    assert snapshot["warnings"] == []


def test_compute_risk_snapshot_excludes_short_history_ticker_with_warning(tmp_path):
    target_path = tmp_path / "target-portfolio.json"
    portfolio_path = tmp_path / "portfolio.json"
    _write_target_portfolio(target_path, [
        {"ticker": "NVDA", "pillarId": "ai_infra"},
        {"ticker": "CBRS", "pillarId": "power"},
    ])
    _write_portfolio(
        portfolio_path,
        shares={"NVDA": 10.0, "CBRS": 3.0},
        prices={"NVDA": 100.0, "CBRS": 200.0},
        total_usd=1600.0,
    )

    nvda_rows = _bdate_rows(120, 100.0, 0.1)
    cbrs_rows = _bdate_rows(10, 200.0, 0.0)  # too short — below MIN_HISTORY_DAYS
    spy_rows = _bdate_rows(120, 400.0, 0.2)

    def fake_get_prices(tickers, period, interval="1d"):
        data = {"NVDA": nvda_rows, "CBRS": cbrs_rows, "SPY": spy_rows}
        return {t: {"data": data[t]} for t in tickers if t in data}

    with patch("risk_engine.get_prices", side_effect=fake_get_prices):
        snapshot = compute_risk_snapshot(
            target_portfolio_path=target_path, portfolio_path=portfolio_path, benchmark="SPY",
        )

    assert any("CBRS" in w for w in snapshot["warnings"])
    assert "CBRS" not in snapshot["marginalRiskContribution"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_risk_engine.py -v -k compute_risk_snapshot`
Expected: FAIL — `ImportError: cannot import name 'compute_risk_snapshot'`.

- [ ] **Step 3: Write minimal implementation**

Add these two imports to the top of `investment_screener/backend/py_services/risk_engine.py`
(alongside the existing ones), and append the orchestrator + CLI at the bottom of the file:

```python
import argparse
import json
from datetime import date

from market_data import get_prices  # noqa: E402
from portfolio_io import load_portfolio_state, compute_weights  # noqa: E402
```

```python
def compute_risk_snapshot(
    target_portfolio_path: Path = TARGET_PATH,
    portfolio_path: Path = PORTFOLIO_PATH,
    benchmark: str = "SPY",
) -> dict[str, Any]:
    """Primary orchestrator — builds the full portfolio risk snapshot.

    Loads current actual weights (never re-derived from raw shares x price
    — portfolio_io.compute_weights() against the broker-authoritative
    total), fetches 2y daily prices for correlation/vol/beta/MRC/VaR and a
    separate 5y fetch for stress replay (2y doesn't reach the 2022 rate-
    shock window), then assembles every compute_*() result into one dict.
    Does not write to disk — see main() for the CLI's --no-save-gated write.

    Args:
        target_portfolio_path: Path to target-portfolio.json (pillars/holdings).
        portfolio_path: Path to portfolio.json (actual broker state).
        benchmark: Benchmark ticker for beta/relative calcs.

    Returns:
        The full risk snapshot dict — see docs/superpowers/specs/
        2026-07-05-risk-engine-design.md for the field-by-field shape.
    """
    target_data = json.loads(Path(target_portfolio_path).read_text())
    pillar_map = {
        h["ticker"]: h.get("pillarId", "unassigned")
        for h in target_data.get("holdings", [])
    }

    state = load_portfolio_state(Path(portfolio_path))
    weights_pct = compute_weights(state["shares"], state["prices"], state["total_usd"])
    tickers = list(weights_pct.keys())
    weights_frac = {t: w / 100.0 for t, w in weights_pct.items()}

    warnings: list[str] = []

    prices_2y = get_prices(tickers + [benchmark], period="2y", interval="1d")
    returns_2y, excluded_2y = build_returns_matrix(prices_2y)
    for t in excluded_2y:
        if t != benchmark:
            warnings.append(f"{t} excluded from correlation/vol/beta/VaR: insufficient price history")

    prices_5y = get_prices(tickers + [benchmark], period="5y", interval="1d")
    returns_5y, excluded_5y = build_returns_matrix(prices_5y)
    for t in excluded_5y:
        if t != benchmark and t not in excluded_2y:
            warnings.append(f"{t} excluded from stress replay: insufficient price history")

    holdings_2y = [t for t in returns_2y.columns if t != benchmark]
    vol_beta = compute_portfolio_vol_beta(returns_2y, weights_frac, benchmark)
    correlation = (
        compute_correlation_matrix(returns_2y[holdings_2y]) if len(holdings_2y) >= 2 else {}
    )
    mrc = compute_marginal_risk_contribution(returns_2y, weights_frac, benchmark)
    concentration = compute_concentration(
        {t: weights_frac[t] for t in holdings_2y if t in weights_frac}
    )
    cluster = compute_cluster_exposure(weights_frac, pillar_map, mrc)
    stress = compute_stress_replay(returns_5y, weights_frac, benchmark)

    portfolio_returns_2y = _weighted_portfolio_returns(returns_2y, weights_frac, exclude={benchmark})
    var_cvar = compute_var_cvar(portfolio_returns_2y)

    return {
        "asOf": date.today().isoformat(),
        "benchmark": benchmark,
        "portfolioVol": vol_beta["vol"],
        "portfolioBeta": vol_beta["beta"],
        "correlationMatrix": correlation,
        "marginalRiskContribution": mrc,
        "concentration": concentration,
        "clusterExposure": cluster,
        "stressReplay": stress,
        "var": {**var_cvar["var"], "horizonDays": 1, "estimate": True},
        "cvar": {**var_cvar["cvar"], "estimate": True},
        "warnings": warnings,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Portfolio risk snapshot")
    parser.add_argument("--benchmark", default="SPY")
    parser.add_argument("--pretty", action="store_true")
    parser.add_argument("--no-save", action="store_true", help="Print only, skip writing risk_snapshot.json")
    args = parser.parse_args()

    snapshot = compute_risk_snapshot(benchmark=args.benchmark)
    if not args.no_save:
        RISK_SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(RISK_SNAPSHOT_PATH, "w") as f:
            json.dump(snapshot, f, indent=2)

    print(json.dumps(snapshot, indent=2 if args.pretty else None))


if __name__ == "__main__":
    main()
```

Note: `import json` and `from pathlib import Path` already exist at the top of the file from
Task 1 — do not duplicate them; only add `argparse`, `from datetime import date`, and the two
new `from ... import ...` lines shown above.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_risk_engine.py -v`
Expected: PASS — every test in the file (Tasks 1–6 combined), zero regressions.

- [ ] **Step 5: Manually smoke-test the CLI against real cached/live data**

```bash
cd investment_screener/backend/py_services
python3 risk_engine.py --no-save --pretty
```

Expected: valid JSON printed to stdout with all 12 top-level keys; no traceback. This exercises
the real `target-portfolio.json`/`portfolio.json` on disk and live `market_data.get_prices()` —
`--no-save` prevents writing `risk_snapshot.json` during this manual check.

- [ ] **Step 6: Commit**

```bash
git add investment_screener/backend/py_services/risk_engine.py investment_screener/backend/tests/py_services/test_risk_engine.py
git commit -m "feat: add compute_risk_snapshot() orchestrator + CLI to risk_engine.py"
```

---

### Task 7: Wire `RISK:` block into `/daily`'s morning brief

**Files:**
- Modify: `plugins/portfolio-advisor/scripts/daily_brief.py` (`run()` around line 173–189,
  `render()` around line 331–340)
- Create: `plugins/portfolio-advisor/tests/test_daily_brief_render.py` (new test directory —
  `daily_brief.py`'s `run()` has no existing unit tests anywhere in the repo today, since it
  orchestrates several live/heavy subsystems; this task follows that existing boundary and
  only unit-tests the pure, already-testable `render()` function's new block, not `run()`
  itself)

**Interfaces:**
- Consumes: `risk_engine.compute_risk_snapshot() -> dict[str, Any]` (Task 6).

- [ ] **Step 1: Write the failing test**

Create the test directory and file:

```bash
mkdir -p plugins/portfolio-advisor/tests
```

Create `plugins/portfolio-advisor/tests/test_daily_brief_render.py`:

```python
"""Tests for daily_brief.py's render() RISK-block wiring (Phase 3, E1)."""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "plugins/portfolio-advisor/scripts"))

from daily_brief import render  # noqa: E402


def _base_brief(risk_snapshot: dict | None = None) -> dict:
    return {
        "date": "2026-07-05",
        "macro_regime": {"regime": "NEUTRAL", "score": 0, "details": []},
        "score_deltas": {}, "pillar_deltas": {}, "conviction_scores": [],
        "earnings_flags": [], "pillar_health": [], "yesterday_date": None,
        "overnight_gaps": [],
        "risk_snapshot": risk_snapshot,
    }


def test_render_includes_risk_line_when_snapshot_present():
    risk_snapshot = {
        "portfolioVol": 0.28, "portfolioBeta": 1.4,
        "clusterExposure": [{"pillarId": "ai_infra", "weight": 0.61, "varianceContributionPct": 72.0}],
        "marginalRiskContribution": {"NVDA": 0.18, "PANW": 0.09},
    }
    output = render(_base_brief(risk_snapshot))
    assert "RISK:" in output
    assert "vol 28%" in output
    assert "beta 1.4" in output
    assert "top cluster 61%" in output
    assert "MRC leader: NVDA 18%" in output


def test_render_omits_risk_line_when_snapshot_absent():
    output = render(_base_brief(risk_snapshot=None))
    assert "RISK:" not in output
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/richardfremmerlid/Projects/InvestmentToolkit && python3 -m pytest plugins/portfolio-advisor/tests/test_daily_brief_render.py -v`
Expected: FAIL — `KeyError`/`AssertionError` (no RISK line exists in `render()` yet).

- [ ] **Step 3: Write minimal implementation**

In `plugins/portfolio-advisor/scripts/daily_brief.py`, inside `run()`, find this block
(around line 172–188):

```python
    # Dynamically import py_services modules
    sys.path.insert(0, str(PY_SERVICES))
    from macro_regime import get_macro_regime
    from earnings_calendar import get_earnings_calendar
    from compute_conviction_scores import compute_all
    from brief_recommendations import build_recommendations, load_standing_decisions
    from overnight_gaps import get_overnight_gaps

    # ── 0. Overnight gap scan ─────────────────────────────────────────────────
    print("▶ Overnight gap scan...", file=sys.stderr)
    try:
        gaps = get_overnight_gaps()
    except Exception:
        gaps = []

    # ── 1. Macro regime ───────────────────────────────────────────────────────
    print("▶ Macro regime...", file=sys.stderr)
    macro = get_macro_regime()
```

Replace it with (adds one import and one call, same pattern as `get_macro_regime`):

```python
    # Dynamically import py_services modules
    sys.path.insert(0, str(PY_SERVICES))
    from macro_regime import get_macro_regime
    from risk_engine import compute_risk_snapshot
    from earnings_calendar import get_earnings_calendar
    from compute_conviction_scores import compute_all
    from brief_recommendations import build_recommendations, load_standing_decisions
    from overnight_gaps import get_overnight_gaps

    # ── 0. Overnight gap scan ─────────────────────────────────────────────────
    print("▶ Overnight gap scan...", file=sys.stderr)
    try:
        gaps = get_overnight_gaps()
    except Exception:
        gaps = []

    # ── 1. Macro regime ───────────────────────────────────────────────────────
    print("▶ Macro regime...", file=sys.stderr)
    macro = get_macro_regime()

    # ── 1b. Portfolio risk snapshot ───────────────────────────────────────────
    print("▶ Risk snapshot...", file=sys.stderr)
    try:
        risk_snapshot = compute_risk_snapshot()
    except Exception:
        risk_snapshot = None
```

Then find the `brief: dict[str, Any] = {` assembly block (around line 269–284) and add
`"risk_snapshot": risk_snapshot,` alongside `"macro_regime": asdict(macro),`:

```python
    brief: dict[str, Any] = {
        "overnight_gaps": gaps,
        "date": date.today().isoformat(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "macro_regime": asdict(macro),
        "risk_snapshot": risk_snapshot,
        "ta_refreshed": ran_ta,
        "ta_skip_reason": ta_skip_reason,
        "conviction_scores": scores_raw,
        "recommendations": recommendations,
        "total_equity": total_equity,
        "score_deltas": deltas,
        "pillar_health": pillars,
        "pillar_deltas": pillar_deltas,
        "earnings_flags": earnings_raw,
        "yesterday_date": yesterday.get("date") if yesterday else None,
    }
```

Finally, in `render()`, find this block (around line 331–340):

```python
    # ── Macro ─────────────────────────────────────────────────────────────────
    regime = macro["regime"]
    icon   = {"RISK-ON": "✅", "NEUTRAL": "⚠️", "RISK-OFF": "🔴"}.get(regime, "")
    lines.append(f"\n{icon}  MACRO REGIME: {regime}  (score={macro['score']})")
    for d in macro["details"]:
        lines.append(f"    {d}")
    if regime == "RISK-OFF":
        lines.append("    ⛔  Gate all ACCUMULATE signals. Execute only REDUCE / EXIT today.")
    elif regime == "NEUTRAL":
        lines.append("    ⚠️  Only highest-conviction (+4 or above) ACCUMULATE actions.")
```

Add immediately after it:

```python
    # ── Portfolio risk snapshot ───────────────────────────────────────────────
    risk = brief.get("risk_snapshot")
    if risk:
        vol = risk.get("portfolioVol")
        beta = risk.get("portfolioBeta")
        cluster = risk.get("clusterExposure") or []
        top_cluster = max(cluster, key=lambda c: c["weight"], default=None)
        mrc = risk.get("marginalRiskContribution") or {}
        mrc_leader = max(mrc.items(), key=lambda kv: kv[1], default=None)

        vol_str = f"{vol * 100:.0f}%" if vol is not None else "—"
        beta_str = f"{beta:.1f}" if beta is not None else "—"
        cluster_str = f"{top_cluster['weight'] * 100:.0f}%" if top_cluster else "—"
        mrc_str = f"{mrc_leader[0]} {mrc_leader[1] * 100:.0f}%" if mrc_leader else "—"

        lines.append(
            f"\n📊  RISK: vol {vol_str} · beta {beta_str} · top cluster {cluster_str} "
            f"· MRC leader: {mrc_str}"
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/richardfremmerlid/Projects/InvestmentToolkit && python3 -m pytest plugins/portfolio-advisor/tests/test_daily_brief_render.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add plugins/portfolio-advisor/scripts/daily_brief.py plugins/portfolio-advisor/tests/test_daily_brief_render.py
git commit -m "feat: wire portfolio risk snapshot into /daily morning brief"
```

---

## Final verification (run once, after Task 7)

```bash
cd investment_screener/backend && python3 -m pytest tests/py_services/test_risk_engine.py -v
cd /Users/richardfremmerlid/Projects/InvestmentToolkit && python3 -m pytest plugins/portfolio-advisor/tests/test_daily_brief_render.py -v
```

Expected: all tests pass, zero regressions. This completes E1 (Phase 3, sub-spec 1 of 5).
Per the agreed build order, C2 (regime classifier) is next.
