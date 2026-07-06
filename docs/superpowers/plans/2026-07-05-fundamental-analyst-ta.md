# Phase 2b — Fundamental Analyst + Local TA Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the investment-framework scoring doc executable (`framework_score.py`),
automate peer benchmarking on top of it (`peer_bench.py`), and add a headless local TA
engine (`technicals.py`) that cross-validates against the TradingView Data Window scrape.

**Architecture:** Three new `py_services/` scripts (pure functions + argparse CLI +
`--json`/`--pretty` output), one small `market_data.py` data-layer extension
(`ebitda`/`currentRatio`/`freeCashflow`, yfinance-only), one new `--validate` mode on the
existing `ta_sweep_batch.py`, and one new optional-field check in `validate_projection.py`.
All three engines are informational — none of them change `check_accumulate_gate()`.

**Tech Stack:** Python 3, pandas, numpy (both already in `requirements.in` — no
pip-compile needed), pytest.

## Global Constraints

- TDD non-negotiable: every step below writes the failing test before the implementation.
- No inline financial math anywhere outside `py_services/` — every number the agent states
  must be reproducible by re-running a script with logged inputs.
- Dual-layer docs on every non-trivial function (external comment + docstring), file
  header on every new file, full type hints, snake_case, refactor at 50+ lines or 3+
  nesting levels — per `.agent/rules/coding-conventions.md`.
- Never coerce a missing/NaN upstream value to zero — omit the field or return `None`,
  matching the existing convention in `market_data.py`.
- Symlinks only via `symlink_manager.py` — never raw `ln -s`.
- Spec: `docs/superpowers/specs/2026-07-05-fundamental-analyst-ta-design.md` — read it
  before Task 2 if anything below is ambiguous; the design doc is the tie-breaker.

## Documented simplifications (carried forward from design; not open questions)

1. **Rule of 40 Method B** uses the same forward-growth figure as Method A (no 3-year
   historical revenue series is exposed by `market_data.py` in this pass) combined with
   EBITDA margin instead of FCF margin — the differentiator the doc cares about for
   `chips_ai` is the margin basis, not the growth basis.
2. **FCF Yield** uses yfinance's `freeCashflow` (already net of capex) as-is, **not**
   SBC-adjusted — no stock-based-compensation source exists in the data layer, the same
   documented scope boundary `comps_valuation.py` already uses for EV/EBITDA.
3. **Invested Capital** (for ROIC) = `totalDebt + marketCap - cash`, using market cap as
   the equity proxy — this matches `wacc.py`'s existing capital-structure convention
   (market cap, not book equity) rather than introducing a new equity source.
4. **ROIIC** is reported as `null` always (requires multi-year invested-capital deltas
   not in the data layer) — supplementary field, never in the composite anyway.

---

### Task 1: `market_data.py` — add `ebitda`, `currentRatio`, `freeCashflow` fields

**Files:**
- Modify: `investment_screener/backend/py_services/market_data.py` (`_YF_ONLY_FUNDAMENTALS_FIELDS`, line ~251)
- Test: `investment_screener/backend/tests/py_services/test_market_data_fundamentals.py`

**Interfaces:**
- Produces: `get_fundamentals(ticker, cik=None)` now may include `"ebitda"`,
  `"currentRatio"`, `"freeCashflow"` keys, each shaped
  `{"value": float, "source": "yfinance", "asOf": str}` when present in yfinance's
  `.info`, and simply absent from the dict when not (never zeroed) — same contract as
  the existing `totalDebt`/`cashAndEquivalents`/`interestExpense` fields.

- [ ] **Step 1: Write the failing test**

Open `investment_screener/backend/tests/py_services/test_market_data_fundamentals.py` and
add:

```python
def test_get_fundamentals_includes_ebitda_current_ratio_and_free_cash_flow():
    """New yfinance-only fields needed by framework_score.py (Phase 2b)."""
    fake_info = {
        "totalRevenue": 1_000_000.0,
        "ebitda": 250_000.0,
        "currentRatio": 1.8,
        "freeCashflow": 120_000.0,
    }
    with patch("market_data._safe_yf_info", return_value=fake_info), \
         patch("market_data._safe_edgar_facts", return_value={}), \
         patch("market_data.cache_get", return_value=None), \
         patch("market_data.cache_set"):
        result = get_fundamentals("TEST", cik=None)

    assert result["ebitda"]["value"] == 250_000.0
    assert result["ebitda"]["source"] == "yfinance"
    assert result["currentRatio"]["value"] == 1.8
    assert result["freeCashflow"]["value"] == 120_000.0


def test_get_fundamentals_omits_ebitda_when_absent_from_yfinance():
    """A ticker with no ebitda in yfinance .info must not get a zeroed field."""
    fake_info = {"totalRevenue": 1_000_000.0}
    with patch("market_data._safe_yf_info", return_value=fake_info), \
         patch("market_data._safe_edgar_facts", return_value={}), \
         patch("market_data.cache_get", return_value=None), \
         patch("market_data.cache_set"):
        result = get_fundamentals("TEST", cik=None)

    assert "ebitda" not in result
```

Check the top of the test file already has `from unittest.mock import patch` and the
`sys.path.insert` / `from market_data import get_fundamentals` block other tests in this
file use — add the two tests alongside the existing `totalDebt`/`interestExpense` tests
(same file, same patching pattern).

- [ ] **Step 2: Run test to verify it fails**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_market_data_fundamentals.py -v -k "ebitda"`
Expected: FAIL — `KeyError: 'ebitda'` (field doesn't exist yet).

- [ ] **Step 3: Write minimal implementation**

In `py_services/market_data.py`, find the `_YF_ONLY_FUNDAMENTALS_FIELDS` dict (~line 251)
and update it:

```python
# Balance-sheet/income-statement fields with no EDGAR tag mapping in this
# pass — yfinance-only, a deliberate scope boundary (the inverse of
# operatingIncome's EDGAR-only boundary below). Needed by wacc.py (cost of
# debt, capital-structure weighting), comps_valuation.py (enterprise value),
# and framework_score.py (Debt/EBITDA, Current Ratio, FCF Yield — Phase 2b).
_YF_ONLY_FUNDAMENTALS_FIELDS = {
    "totalDebt": "totalDebt",
    "cashAndEquivalents": "totalCash",
    "interestExpense": "interestExpense",
    "ebitda": "ebitda",
    "currentRatio": "currentRatio",
    "freeCashflow": "freeCashflow",
}
```

No other change is needed — the existing loop over `_YF_ONLY_FUNDAMENTALS_FIELDS` in
`get_fundamentals()` already handles arbitrary dict entries generically.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_market_data_fundamentals.py -v`
Expected: PASS (all tests in the file, not just the two new ones — confirm no regression).

- [ ] **Step 5: Commit**

```bash
git add investment_screener/backend/py_services/market_data.py investment_screener/backend/tests/py_services/test_market_data_fundamentals.py
git commit -m "feat: add ebitda/currentRatio/freeCashflow fields to market_data.get_fundamentals"
```

---

### Task 2: `framework_score.py` — metric computation + weighted composite

**Files:**
- Create: `investment_screener/backend/py_services/framework_score.py`
- Test: `investment_screener/backend/tests/py_services/test_framework_score.py`

**Interfaces:**
- Consumes: `market_data.get_fundamentals(ticker, cik=None) -> dict`,
  `market_data.get_estimates(ticker) -> dict` (keys `y1RevEstimate`, `y2RevEstimate`),
  `market_data.get_quote([ticker]) -> dict`,
  `comps_valuation.load_latest_projection(ticker, projections_dir) -> dict | None`,
  `comps_valuation.compute_ev(price, shares, debt, cash) -> float`.
- Produces:
  - `compute_raw_metrics(ticker: str, sector: str, projections_dir: str, cik: str | None = None) -> dict`
    — one dict of raw (unscored) metric values, reused by `peer_bench.py` in Task 4.
  - `score_higher_better(value: float | None, strong: float, consider: float) -> int | None`
  - `score_lower_better(value: float | None, strong: float, consider: float) -> int | None`
  - `compute_framework_score(ticker: str, sector: str, projections_dir: str, qualitative: dict | None = None, cik: str | None = None) -> dict`
    — the full scored + composited result, shaped as in the design doc's
    `analyticsLog.framework` example.

- [ ] **Step 1: Write the failing tests**

Create `investment_screener/backend/tests/py_services/test_framework_score.py`:

```python
"""Tests for framework_score.py — sector-aware weighted composite score (Phase 2b)."""
import json
import sys
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from framework_score import (  # noqa: E402
    compute_framework_score,
    compute_raw_metrics,
    score_higher_better,
    score_lower_better,
)


def _write_projection(dirpath, ticker, price, shares):
    proj = [{
        "ticker": ticker, "source": "AI_AGENT", "savedAt": "2026-01-01T00:00:00Z",
        "snapshot": {"price": price, "shares": shares},
    }]
    (dirpath / f"{ticker}.json").write_text(json.dumps(proj))


def _fundamentals_fixture(**overrides):
    base = {
        "revenue": {"value": 1_000_000_000.0, "source": "edgar", "asOf": "2026-01-01"},
        "operatingIncome": {"value": 200_000_000.0, "source": "edgar", "asOf": "2026-01-01"},
        "totalDebt": {"value": 300_000_000.0, "source": "yfinance", "asOf": "2026-01-01"},
        "cashAndEquivalents": {"value": 150_000_000.0, "source": "yfinance", "asOf": "2026-01-01"},
        "interestExpense": {"value": 20_000_000.0, "source": "yfinance", "asOf": "2026-01-01"},
        "ebitda": {"value": 250_000_000.0, "source": "yfinance", "asOf": "2026-01-01"},
        "currentRatio": {"value": 1.8, "source": "yfinance", "asOf": "2026-01-01"},
        "freeCashflow": {"value": 80_000_000.0, "source": "yfinance", "asOf": "2026-01-01"},
    }
    base.update(overrides)
    return base


# ── score_higher_better / score_lower_better ─────────────────────────────────

def test_score_higher_better_bands():
    assert score_higher_better(0.25, strong=0.20, consider=0.05) == 90
    assert score_higher_better(0.10, strong=0.20, consider=0.05) == 60
    assert score_higher_better(0.01, strong=0.20, consider=0.05) == 30


def test_score_higher_better_boundary_is_inclusive():
    """Exactly at the strong threshold must score 90, not 60 (design decision)."""
    assert score_higher_better(0.40, strong=0.40, consider=0.30) == 90


def test_score_lower_better_bands():
    assert score_lower_better(8.0, strong=10.0, consider=15.0) == 90
    assert score_lower_better(12.0, strong=10.0, consider=15.0) == 60
    assert score_lower_better(20.0, strong=10.0, consider=15.0) == 30


def test_score_returns_none_for_none_input():
    assert score_higher_better(None, strong=0.2, consider=0.05) is None
    assert score_lower_better(None, strong=10.0, consider=15.0) is None


# ── compute_raw_metrics ───────────────────────────────────────────────────────

def test_compute_raw_metrics_computes_expected_values(tmp_path):
    _write_projection(tmp_path, "TEST", price=100.0, shares=10_000_000.0)
    estimates = {"y1RevEstimate": 1_000_000_000.0, "y2RevEstimate": 1_300_000_000.0}
    with patch("framework_score.get_fundamentals", return_value=_fundamentals_fixture()), \
         patch("framework_score.get_estimates", return_value=estimates):
        metrics = compute_raw_metrics("TEST", "chips_ai", str(tmp_path))

    # marketCap = 100 * 10M = 1_000_000_000
    # investedCapital = 300M + 1_000_000_000 - 150M = 1_150_000_000
    # NOPAT = 200M * (1 - 0.21) = 158_000_000
    assert metrics["revenueGrowth"] == 0.3  # (1.3B / 1.0B) - 1
    assert round(metrics["roic"], 4) == round(158_000_000.0 / 1_150_000_000.0, 4)
    assert round(metrics["operatingMargin"], 4) == 0.2  # 200M / 1B
    assert round(metrics["evSales"], 4) == round((1_000_000_000.0 + 300_000_000.0 - 150_000_000.0) / 1_000_000_000.0, 4)
    assert round(metrics["debtEbitda"], 4) == round(300_000_000.0 / 250_000_000.0, 4)
    assert round(metrics["interestCoverage"], 4) == round(200_000_000.0 / 20_000_000.0, 4)
    assert metrics["currentRatio"] == 1.8
    assert round(metrics["fcfYield"], 4) == round(80_000_000.0 / 1_000_000_000.0, 4)


def test_compute_raw_metrics_returns_none_for_missing_projection(tmp_path):
    with patch("framework_score.get_fundamentals", return_value=_fundamentals_fixture()), \
         patch("framework_score.get_estimates", return_value={}):
        metrics = compute_raw_metrics("MISSING", "chips_ai", str(tmp_path))
    assert metrics["revenueGrowth"] is None
    assert metrics["roic"] is None  # no shares -> no market cap -> no invested capital


# ── compute_framework_score — composite ──────────────────────────────────────

def test_compute_framework_score_saas_cyber_composite(tmp_path):
    _write_projection(tmp_path, "SAAS", price=100.0, shares=10_000_000.0)
    estimates = {"y1RevEstimate": 1_000_000_000.0, "y2RevEstimate": 1_250_000_000.0}
    fundamentals = _fundamentals_fixture(
        freeCashflow={"value": 60_000_000.0, "source": "yfinance", "asOf": "2026-01-01"},
    )
    with patch("framework_score.get_fundamentals", return_value=fundamentals), \
         patch("framework_score.get_estimates", return_value=estimates):
        result = compute_framework_score("SAAS", "saas_cyber", str(tmp_path))

    assert result["sector"] == "saas_cyber"
    assert result["metrics"]["revenueGrowth"]["raw"] == 0.25
    assert result["metrics"]["revenueGrowth"]["score"] == 90  # >=20%
    assert result["composite"] > 0
    assert result["band"] in {"STRONG_BUY", "CONSIDER", "AVOID"}
    assert result["excludedMetrics"] == ["competitiveMoat", "newsImpact"]
    assert result["reweighted"] is True


def test_compute_framework_score_boundary_ro40_exactly_40_scores_90(tmp_path):
    """Design decision: exactly at the sector threshold scores the top band (>=, not >)."""
    _write_projection(tmp_path, "BOUND", price=50.0, shares=1_000_000.0)
    # Ro40 Method A = revenueGrowth + fcfMargin (FCF / revenue), must equal exactly
    # 40.0 for saas_cyber. revenueGrowth = 0.30 (30%), fcfMargin must be 0.10 (10%)
    # of the 100_000_000 revenue below -> fcf = 10_000_000.
    estimates = {"y1RevEstimate": 100_000_000.0, "y2RevEstimate": 130_000_000.0}
    fundamentals = _fundamentals_fixture(
        revenue={"value": 100_000_000.0, "source": "edgar", "asOf": "2026-01-01"},
        freeCashflow={"value": 10_000_000.0, "source": "yfinance", "asOf": "2026-01-01"},
    )
    with patch("framework_score.get_fundamentals", return_value=fundamentals), \
         patch("framework_score.get_estimates", return_value=estimates):
        result = compute_framework_score("BOUND", "saas_cyber", str(tmp_path))

    assert result["metrics"]["ruleOf40"]["raw"] == 40.0
    assert result["metrics"]["ruleOf40"]["score"] == 90


def test_compute_framework_score_reweights_when_qualitative_missing(tmp_path):
    _write_projection(tmp_path, "RW", price=100.0, shares=10_000_000.0)
    estimates = {"y1RevEstimate": 1_000_000_000.0, "y2RevEstimate": 1_200_000_000.0}
    with patch("framework_score.get_fundamentals", return_value=_fundamentals_fixture()), \
         patch("framework_score.get_estimates", return_value=estimates):
        no_qual = compute_framework_score("RW", "chips_ai", str(tmp_path))
        with_qual = compute_framework_score(
            "RW", "chips_ai", str(tmp_path),
            qualitative={
                "competitiveMoat": {"rating": "high", "source": "10-K", "asOf": "2026-01-01"},
                "newsImpact": {"rating": "positive", "source": "call", "asOf": "2026-01-01"},
            },
        )

    assert no_qual["excludedMetrics"] == ["competitiveMoat", "newsImpact"]
    assert with_qual["excludedMetrics"] == []
    assert with_qual["reweighted"] is False
    # Composite must differ once moat/news are included with real scores.
    assert no_qual["composite"] != with_qual["composite"]


def test_compute_framework_score_composite_invariant_to_dict_ordering(tmp_path):
    """Property test: reordering metrics dict keys must not change the composite."""
    _write_projection(tmp_path, "ORD", price=100.0, shares=10_000_000.0)
    estimates = {"y1RevEstimate": 1_000_000_000.0, "y2RevEstimate": 1_200_000_000.0}
    fundamentals = _fundamentals_fixture()
    reversed_fundamentals = dict(reversed(list(fundamentals.items())))
    with patch("framework_score.get_estimates", return_value=estimates):
        with patch("framework_score.get_fundamentals", return_value=fundamentals):
            result_a = compute_framework_score("ORD", "chips_ai", str(tmp_path))
        with patch("framework_score.get_fundamentals", return_value=reversed_fundamentals):
            result_b = compute_framework_score("ORD", "chips_ai", str(tmp_path))

    assert result_a["composite"] == result_b["composite"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_framework_score.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'framework_score'`.

- [ ] **Step 3: Write minimal implementation**

Create `investment_screener/backend/py_services/framework_score.py`:

```python
#!/usr/bin/env python3
"""
framework_score.py (Python Service)
=====================================

Purpose:
    Executable version of the sector-aware weighted composite score defined
    in definitive_professional_investment_framework.md §5. Encodes revenue
    growth, Rule of 40 (Method A/B), operating margin, ROIC, EV/Sales,
    FCF yield, balance-sheet health, and two agent-supplied qualitative
    inputs (competitive moat, news impact) into one composite 0-100 score
    with a STRONG_BUY/CONSIDER/AVOID band. Informational only — does not
    feed check_accumulate_gate() (see docs/superpowers/specs/
    2026-07-05-fundamental-analyst-ta-design.md).

    Documented simplifications (not gaps to silently fill later):
    - Rule of 40 Method B reuses Method A's forward-growth figure (no 3yr
      historical revenue series in market_data.py yet) combined with
      EBITDA margin instead of FCF margin.
    - FCF Yield uses yfinance's raw freeCashflow, not SBC-adjusted (no SBC
      source in the data layer — same scope boundary as EV/EBITDA in
      comps_valuation.py).
    - Invested Capital for ROIC uses market cap as the equity proxy,
      matching wacc.py's existing capital-structure convention.
    - ROIIC is always null (needs multi-year invested-capital deltas not
      in the data layer); reported for context, never scored/composited.

Layer: Backend / Python Services / Valuation Math

Usage:
    python3 framework_score.py --ticker NVDA --sector chips_ai \
        --projections-dir investment_screener/backend/data/projections --pretty
    python3 framework_score.py --ticker NVDA --sector chips_ai \
        --projections-dir DIR --qualitative-file qual.json --pretty

Key Functions:
    - compute_raw_metrics() - Pulls every raw (unscored) metric value for one ticker
    - score_higher_better() / score_lower_better() - 90/60/30 band scoring, inclusive top boundary
    - compute_framework_score() - Primary orchestrator: raw metrics -> scored -> composite
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from market_data import get_fundamentals, get_estimates  # noqa: E402
from comps_valuation import load_latest_projection, compute_ev  # noqa: E402

DEFAULT_TAX_RATE = 0.21

# Composite weights — must sum to 1.00, matches the doc's §5 formula exactly.
COMPOSITE_WEIGHTS = {
    "revenueGrowth": 0.25,
    "ruleOf40": 0.20,
    "operatingMargin": 0.15,
    "roic": 0.10,
    "valuation": 0.10,
    "fcfYield": 0.10,
    "balanceSheet": 0.05,
    "competitiveMoat": 0.05,
    "newsImpact": 0.05,
}

# Sector-specific score bands, transcribed verbatim from the doc's §5 scoring
# guidelines. (strong, consider) — value >= strong scores 90, >= consider
# scores 60, else 30 (score_higher_better); the reverse for score_lower_better.
SECTOR_THRESHOLDS = {
    "saas_cyber": {
        "ruleOf40": (0.40, 0.30), "evSales": (10.0, 15.0), "debtEbitda": (2.0, 4.0),
    },
    "chips_ai": {
        "ruleOf40": (0.30, 0.20), "evSales": (8.0, 12.0), "debtEbitda": (2.5, 4.0),
    },
    "energy_infra": {
        "ruleOf40": (0.20, 0.10), "evSales": (3.0, 5.0), "debtEbitda": (3.0, 5.0),
    },
}
RULE_OF_40_METHOD = {"saas_cyber": "A", "chips_ai": "B", "energy_infra": "A"}

# Flat (non-sector-specific) bands from the doc's §5 guideline.
FLAT_THRESHOLDS = {
    "operatingMargin": (0.20, 0.10),
    "roic": (0.15, 0.08),
    "fcfYield": (0.05, 0.02),
    "interestCoverage": (5.0, 2.0),
    "currentRatio": (1.5, 1.0),
}
QUALITATIVE_RATING_SCORE = {"high": 90, "medium": 60, "low": 30,
                            "positive": 90, "neutral": 60, "negative": 30}


def score_higher_better(value: float | None, strong: float, consider: float) -> int | None:
    """Score a metric where a larger value is better (90/60/30, top boundary inclusive).

    Args:
        value: Raw metric value, or None if unavailable.
        strong: Threshold at/above which the metric scores 90.
        consider: Threshold at/above which the metric scores 60 (below scores 30).

    Returns:
        90, 60, 30, or None if value is None.
    """
    if value is None:
        return None
    if value >= strong:
        return 90
    if value >= consider:
        return 60
    return 30


def score_lower_better(value: float | None, strong: float, consider: float) -> int | None:
    """Score a metric where a smaller value is better (90/60/30, top boundary inclusive).

    Args:
        value: Raw metric value, or None if unavailable.
        strong: Threshold at/below which the metric scores 90.
        consider: Threshold at/below which the metric scores 60 (above scores 30).

    Returns:
        90, 60, 30, or None if value is None.
    """
    if value is None:
        return None
    if value <= strong:
        return 90
    if value <= consider:
        return 60
    return 30


def _score_qualitative(qualitative: dict | None, field: str) -> tuple[float | None, int | None]:
    """Look up an agent-supplied qualitative rating and its 90/60/30 score.

    Args:
        qualitative: The --qualitative-file dict, or None.
        field: "competitiveMoat" or "newsImpact".

    Returns:
        (rating_string_or_None, score_or_None) — None/None when the field is
        absent from the qualitative file, never guessed.
    """
    if not qualitative or field not in qualitative:
        return None, None
    rating = qualitative[field].get("rating")
    return rating, QUALITATIVE_RATING_SCORE.get(rating)


def compute_raw_metrics(
    ticker: str, sector: str, projections_dir: str, cik: str | None = None
) -> dict[str, Any]:
    """Pull every raw (unscored) fundamental metric needed for the composite.

    Shares/price come from the ticker's persisted projection snapshot (the
    same agent-curated source comps_valuation.py already reads) since
    market_data.py has no shares-outstanding getter. A ticker with no
    projection on disk yields an all-None metrics dict rather than raising —
    peer_bench.py (Task 4) relies on this to skip peers with no usable data.

    Args:
        ticker: Ticker symbol.
        sector: One of "saas_cyber", "chips_ai", "energy_infra".
        projections_dir: Path to the projections directory.
        cik: SEC CIK for EDGAR-preferred fundamentals, or None.

    Returns:
        Dict of raw metric values (float or None): revenueGrowth, ruleOf40Raw,
        ruleOf40Method, operatingMargin, roic, evSales, fcfYield, debtEbitda,
        interestCoverage, currentRatio.
    """
    projection = load_latest_projection(ticker, projections_dir)
    snapshot = (projection or {}).get("snapshot", {})
    price = snapshot.get("price")
    shares = snapshot.get("shares")

    fundamentals = get_fundamentals(ticker, cik=cik)
    estimates = get_estimates(ticker)

    def _val(field: str) -> float | None:
        return fundamentals.get(field, {}).get("value")

    revenue = _val("revenue")
    operating_income = _val("operatingIncome")
    total_debt = _val("totalDebt") or 0.0
    cash = _val("cashAndEquivalents") or 0.0
    interest_expense = _val("interestExpense")
    ebitda = _val("ebitda")
    current_ratio = _val("currentRatio")
    free_cash_flow = _val("freeCashflow")

    y1 = estimates.get("y1RevEstimate")
    y2 = estimates.get("y2RevEstimate")
    revenue_growth = (y2 / y1 - 1) if y1 and y2 and y1 > 0 else None

    market_cap = price * shares if price and shares else None
    ev = compute_ev(price, shares, total_debt, cash) if price and shares else None

    operating_margin = operating_income / revenue if operating_income is not None and revenue else None
    invested_capital = (total_debt + market_cap - cash) if market_cap is not None else None
    nopat = operating_income * (1 - DEFAULT_TAX_RATE) if operating_income is not None else None
    roic = nopat / invested_capital if nopat is not None and invested_capital and invested_capital > 0 else None
    ev_sales = ev / revenue if ev is not None and revenue else None
    fcf_yield = free_cash_flow / market_cap if free_cash_flow is not None and market_cap else None
    debt_ebitda = total_debt / ebitda if ebitda else None
    interest_coverage = operating_income / interest_expense if operating_income is not None and interest_expense else None

    # Rule of 40 Method A uses FCF MARGIN (FCF / revenue) — distinct from the
    # composite's own "fcfYield" slot (FCF / market cap, from the doc's
    # separate Cash Flow Profitability section). Do not conflate the two.
    method = RULE_OF_40_METHOD[sector]
    fcf_margin = free_cash_flow / revenue if free_cash_flow is not None and revenue else None
    ebitda_margin = ebitda / revenue if ebitda and revenue else None
    margin = fcf_margin if method == "A" else ebitda_margin
    rule_of_40 = revenue_growth + margin if revenue_growth is not None and margin is not None else None

    return {
        "revenueGrowth": revenue_growth,
        "ruleOf40Raw": rule_of_40,
        "ruleOf40Method": method,
        "operatingMargin": operating_margin,
        "roic": roic,
        "evSales": ev_sales,
        "fcfYield": fcf_yield,
        "debtEbitda": debt_ebitda,
        "interestCoverage": interest_coverage,
        "currentRatio": current_ratio,
    }


def compute_framework_score(
    ticker: str,
    sector: str,
    projections_dir: str,
    qualitative: dict | None = None,
    cik: str | None = None,
) -> dict[str, Any]:
    """Compute the full sector-aware weighted composite framework score.

    Any metric with no data (raw value None, or a qualitative field absent
    from `qualitative`) is excluded from the composite and its weight is
    redistributed proportionally across the remaining present metrics —
    never guessed, never zero-filled. `excludedMetrics`/`reweighted` make
    this always visible in the output.

    Args:
        ticker: Ticker symbol.
        sector: One of "saas_cyber", "chips_ai", "energy_infra".
        projections_dir: Path to the projections directory.
        qualitative: Parsed --qualitative-file dict, or None.
        cik: SEC CIK for EDGAR-preferred fundamentals, or None.

    Returns:
        {"sector", "metrics": {...per-metric raw/score...}, "composite",
         "band", "excludedMetrics", "reweighted"}.
    """
    raw = compute_raw_metrics(ticker, sector, projections_dir, cik=cik)
    thresholds = SECTOR_THRESHOLDS[sector]

    moat_rating, moat_score = _score_qualitative(qualitative, "competitiveMoat")
    news_rating, news_score = _score_qualitative(qualitative, "newsImpact")

    metrics = {
        "revenueGrowth": {"raw": raw["revenueGrowth"], "score": score_higher_better(raw["revenueGrowth"], 0.20, 0.05)},
        "ruleOf40": {"method": raw["ruleOf40Method"], "raw": raw["ruleOf40Raw"],
                     "score": score_higher_better(raw["ruleOf40Raw"], *thresholds["ruleOf40"])},
        "operatingMargin": {"raw": raw["operatingMargin"],
                             "score": score_higher_better(raw["operatingMargin"], *FLAT_THRESHOLDS["operatingMargin"])},
        "roic": {"raw": raw["roic"], "score": score_higher_better(raw["roic"], *FLAT_THRESHOLDS["roic"])},
        "valuation": {"metric": "evSales", "raw": raw["evSales"],
                      "score": score_lower_better(raw["evSales"], *thresholds["evSales"])},
        "fcfYield": {"raw": raw["fcfYield"], "score": score_higher_better(raw["fcfYield"], *FLAT_THRESHOLDS["fcfYield"])},
        "balanceSheet": _balance_sheet_score(raw, thresholds),
        "competitiveMoat": {"raw": moat_rating, "score": moat_score},
        "newsImpact": {"raw": news_rating, "score": news_score},
    }

    composite, excluded = _weighted_composite(metrics)

    return {
        "sector": sector,
        "metrics": metrics,
        "composite": round(composite, 2) if composite is not None else None,
        "band": _composite_band(composite),
        "excludedMetrics": excluded,
        "reweighted": len(excluded) > 0,
    }


def _balance_sheet_score(raw: dict, thresholds: dict) -> dict:
    """Average Debt/EBITDA, Interest Coverage, and Current Ratio scores into one slot.

    Args:
        raw: Output of compute_raw_metrics().
        thresholds: This sector's SECTOR_THRESHOLDS entry.

    Returns:
        {"debtEbitda": {...}, "interestCoverage": {...}, "currentRatio": {...}, "score": float|None}.
    """
    debt_ebitda_score = score_lower_better(raw["debtEbitda"], *thresholds["debtEbitda"])
    interest_score = score_higher_better(raw["interestCoverage"], *FLAT_THRESHOLDS["interestCoverage"])
    current_ratio_score = score_higher_better(raw["currentRatio"], *FLAT_THRESHOLDS["currentRatio"])
    present = [s for s in (debt_ebitda_score, interest_score, current_ratio_score) if s is not None]
    return {
        "debtEbitda": {"raw": raw["debtEbitda"], "score": debt_ebitda_score},
        "interestCoverage": {"raw": raw["interestCoverage"], "score": interest_score},
        "currentRatio": {"raw": raw["currentRatio"], "score": current_ratio_score},
        "score": round(sum(present) / len(present), 2) if present else None,
    }


def _weighted_composite(metrics: dict) -> tuple[float | None, list[str]]:
    """Compute the reweighted composite score, excluding any metric with no score.

    Args:
        metrics: The `metrics` dict built by compute_framework_score().

    Returns:
        (composite_or_None, sorted_list_of_excluded_metric_names).
    """
    present_weight = 0.0
    weighted_sum = 0.0
    excluded = []
    for name, weight in COMPOSITE_WEIGHTS.items():
        score = metrics[name]["score"]
        if score is None:
            excluded.append(name)
            continue
        weighted_sum += weight * score
        present_weight += weight
    if present_weight == 0:
        return None, sorted(excluded)
    return weighted_sum / present_weight, sorted(excluded)


def _composite_band(composite: float | None) -> str | None:
    """Map a composite score to STRONG_BUY / CONSIDER / AVOID (top boundary inclusive)."""
    if composite is None:
        return None
    if composite >= 80:
        return "STRONG_BUY"
    if composite >= 50:
        return "CONSIDER"
    return "AVOID"


def main() -> None:
    parser = argparse.ArgumentParser(description="Sector-aware weighted composite framework score")
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--sector", required=True, choices=list(SECTOR_THRESHOLDS))
    parser.add_argument("--projections-dir", required=True)
    parser.add_argument("--qualitative-file", default=None)
    parser.add_argument("--cik", default=None)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    qualitative = None
    if args.qualitative_file:
        with open(args.qualitative_file) as f:
            qualitative = json.load(f)

    result = compute_framework_score(
        args.ticker, args.sector, args.projections_dir, qualitative=qualitative, cik=args.cik
    )
    print(json.dumps(result, indent=2 if args.pretty else None))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_framework_score.py -v`
Expected: PASS — all tests green. If the boundary or reweighting tests fail, check
`score_higher_better`/`score_lower_better` use `>=`/`<=` (not `>`/`<`), and that
`_weighted_composite` renormalizes over `present_weight`, not a fixed 1.0.

- [ ] **Step 5: Commit**

```bash
git add investment_screener/backend/py_services/framework_score.py investment_screener/backend/tests/py_services/test_framework_score.py
git commit -m "feat: add framework_score.py — executable sector-aware composite score"
```

---

### Task 3: Rename framework doc, add symlink, add header

**Files:**
- Create: `plugins/portfolio-advisor/references/definitive_professional_investment_framework.md` (renamed from the typo'd filename — copy content, do not hand-retype)
- Modify: symlink at the old path via `symlink_manager.py`
- Modify: new file's header (first lines) to add the "executable version" note

**Interfaces:** None (documentation-only task; no code interface).

- [ ] **Step 1: Copy content to the corrected filename**

```bash
cd /Users/richardfremmerlid/Projects/InvestmentToolkit
git mv plugins/portfolio-advisor/references/defininitive_professional_investment_framework.md \
       plugins/portfolio-advisor/references/definitive_professional_investment_framework.md
```

- [ ] **Step 2: Add the executable-version header note**

Edit the new file's first line block (right after the `# The Definitive Professional
Investment Framework (v3.1)` title, before `## Guiding Philosophy`) to insert:

```markdown
> **Executable version:** `investment_screener/backend/py_services/framework_score.py`
> implements this framework's §5 composite score. Changes to the scoring formula,
> weights, or sector thresholds below require a matching change to that script — this
> doc and the script must never drift apart.
```

- [ ] **Step 3: Recreate the old path as a symlink**

```bash
python3 .agents/skills/symlink-manager/scripts/symlink_manager.py create \
  --src plugins/portfolio-advisor/references/definitive_professional_investment_framework.md \
  --dst plugins/portfolio-advisor/references/defininitive_professional_investment_framework.md \
  --description "Compat symlink — typo'd filename kept for any hardcoded references, Phase 2b rename"
```

- [ ] **Step 4: Verify the symlink resolves and grep for hardcoded old-path references**

```bash
ls -la plugins/portfolio-advisor/references/defininitive_professional_investment_framework.md
grep -rl "defininitive_professional_investment_framework" --include="*.md" --include="*.py" . \
  | grep -v "plugins/portfolio-advisor/references/defininitive_professional_investment_framework.md"
```
Expected: `ls` shows a symlink (`l` permission bit) pointing at the new filename; `grep`
returns no hits outside the symlink itself (if it does, leave those references as-is —
the symlink keeps them working — this is just a sanity check, not a required edit).

- [ ] **Step 5: Commit**

```bash
git add -A plugins/portfolio-advisor/references/
git commit -m "docs: rename definitive_professional_investment_framework.md (fix typo), keep compat symlink"
```

---

### Task 4: `peer_bench.py` — peer benchmarking table (Z-scores/percentiles)

**Files:**
- Create: `investment_screener/backend/py_services/peer_bench.py`
- Test: `investment_screener/backend/tests/py_services/test_peer_bench.py`

**Interfaces:**
- Consumes: `framework_score.compute_raw_metrics(ticker, sector, projections_dir, cik=None) -> dict`.
- Produces: `compute_peer_benchmark(ticker: str, peers: list[str], sector: str, projections_dir: str) -> dict`.

- [ ] **Step 1: Write the failing tests**

Create `investment_screener/backend/tests/py_services/test_peer_bench.py`:

```python
"""Tests for peer_bench.py — peer benchmarking table with Z-scores/percentiles (Phase 2b)."""
import sys
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from peer_bench import compute_peer_benchmark  # noqa: E402


def _metrics(revenue_growth):
    """A minimal compute_raw_metrics()-shaped dict varying only revenueGrowth."""
    return {
        "revenueGrowth": revenue_growth, "ruleOf40Raw": None, "ruleOf40Method": "A",
        "operatingMargin": None, "roic": None, "evSales": None, "fcfYield": None,
        "debtEbitda": None, "interestCoverage": None, "currentRatio": None,
    }


def test_compute_peer_benchmark_computes_zscore_and_percentile():
    values = {"TARGET": 0.30, "PEERA": 0.10, "PEERB": 0.20}

    def fake_raw_metrics(ticker, sector, projections_dir, cik=None):
        return _metrics(values[ticker])

    with patch("peer_bench.compute_raw_metrics", side_effect=fake_raw_metrics):
        result = compute_peer_benchmark("TARGET", ["PEERA", "PEERB"], "chips_ai", "/fake/dir")

    assert result["status"] == "ok"
    assert result["peersUsed"] == ["PEERA", "PEERB"]
    row = next(r for r in result["table"] if r["metric"] == "revenueGrowth")
    assert row["ticker"] == 0.30
    assert row["peerMedian"] == 0.15  # median of [0.10, 0.20]
    assert row["percentile"] == 100  # highest of the three values


def test_compute_peer_benchmark_insufficient_peer_data():
    def fake_raw_metrics(ticker, sector, projections_dir, cik=None):
        return _metrics(0.30) if ticker == "TARGET" else _metrics(None)

    with patch("peer_bench.compute_raw_metrics", side_effect=fake_raw_metrics):
        result = compute_peer_benchmark("TARGET", ["PEERA", "PEERB"], "chips_ai", "/fake/dir")

    assert result["status"] == "insufficient_peer_data"
    assert result["peersUsed"] == []


def test_compute_peer_benchmark_skips_metrics_with_no_target_value():
    def fake_raw_metrics(ticker, sector, projections_dir, cik=None):
        m = _metrics(0.30 if ticker == "TARGET" else 0.10)
        return m  # operatingMargin stays None for everyone

    with patch("peer_bench.compute_raw_metrics", side_effect=fake_raw_metrics):
        result = compute_peer_benchmark("TARGET", ["PEERA", "PEERB"], "chips_ai", "/fake/dir")

    metric_names = {r["metric"] for r in result["table"]}
    assert "operatingMargin" not in metric_names
    assert "revenueGrowth" in metric_names
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_peer_bench.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'peer_bench'`.

- [ ] **Step 3: Write minimal implementation**

Create `investment_screener/backend/py_services/peer_bench.py`:

```python
#!/usr/bin/env python3
"""
peer_bench.py (Python Service)
=====================================

Purpose:
    Automates the framework doc's Phase-2 "Peer Benchmarking" table: for
    each raw metric compute_raw_metrics() produces, computes the target
    ticker's value alongside the peer-set median, Z-score, and percentile
    rank. Reuses framework_score.compute_raw_metrics() as the single source
    of truth for every metric formula — never re-derives them.

Layer: Backend / Python Services / Valuation Math

Usage:
    python3 peer_bench.py --ticker NVDA --peers AMD,AVGO,QCOM --sector chips_ai \
        --projections-dir investment_screener/backend/data/projections --pretty

Key Functions:
    - compute_peer_benchmark() - Primary orchestrator: target + peer raw metrics -> benchmarking table
"""

import argparse
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from framework_score import compute_raw_metrics  # noqa: E402

MIN_USABLE_PEERS = 2


def compute_peer_benchmark(
    ticker: str, peers: list[str], sector: str, projections_dir: str
) -> dict:
    """Build the peer benchmarking table: target value + peer median/Z-score/percentile.

    A metric is included in the table only if the target ticker has a value
    for it AND at least MIN_USABLE_PEERS peers also have a value — never
    fabricated from a smaller set. A percentile of 0 std-dev peer sets
    (all peers identical) reports zScore 0.0 rather than dividing by zero.

    Args:
        ticker: Target ticker.
        peers: Curated peer ticker list (from projections/{TICKER}.json's `peers` field).
        sector: One of "saas_cyber", "chips_ai", "energy_infra".
        projections_dir: Path to the projections directory.

    Returns:
        {"status": "ok", "peersUsed": [...], "table": [{"metric", "ticker",
         "peerMedian", "zScore", "percentile"}, ...]} or
        {"status": "insufficient_peer_data", "peersUsed": []} when fewer
        than MIN_USABLE_PEERS peers have any usable metric at all.
    """
    target_metrics = compute_raw_metrics(ticker, sector, projections_dir)
    peer_metrics = {p: compute_raw_metrics(p, sector, projections_dir) for p in peers}

    peers_used = sorted({
        p for p, m in peer_metrics.items() if any(v is not None for v in m.values())
    })
    if len(peers_used) < MIN_USABLE_PEERS:
        return {"status": "insufficient_peer_data", "peersUsed": []}

    table = []
    for metric_name, target_value in target_metrics.items():
        if target_value is None or not isinstance(target_value, (int, float)):
            continue
        peer_values = [
            peer_metrics[p][metric_name] for p in peers_used
            if isinstance(peer_metrics[p].get(metric_name), (int, float))
        ]
        if len(peer_values) < MIN_USABLE_PEERS:
            continue

        peer_median = statistics.median(peer_values)
        all_values = peer_values + [target_value]
        mean = statistics.mean(all_values)
        stdev = statistics.pstdev(all_values)
        z_score = (target_value - mean) / stdev if stdev > 0 else 0.0
        rank = sorted(all_values).index(target_value) + 1
        percentile = round(rank / len(all_values) * 100)

        table.append({
            "metric": metric_name,
            "ticker": target_value,
            "peerMedian": round(peer_median, 4),
            "zScore": round(z_score, 3),
            "percentile": percentile,
        })

    return {"status": "ok", "peersUsed": peers_used, "table": table}


def main() -> None:
    parser = argparse.ArgumentParser(description="Peer benchmarking table (Z-scores/percentiles)")
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--peers", required=True, help="Comma-separated peer tickers")
    parser.add_argument("--sector", required=True, choices=["saas_cyber", "chips_ai", "energy_infra"])
    parser.add_argument("--projections-dir", required=True)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    peer_tickers = [p.strip() for p in args.peers.split(",") if p.strip()]
    result = compute_peer_benchmark(args.ticker, peer_tickers, args.sector, args.projections_dir)
    print(json.dumps(result, indent=2 if args.pretty else None))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_peer_bench.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add investment_screener/backend/py_services/peer_bench.py investment_screener/backend/tests/py_services/test_peer_bench.py
git commit -m "feat: add peer_bench.py — Z-score/percentile peer benchmarking table"
```

---

### Task 5: `technicals.py` part 1 — RSI, EMA, MACD, ATR, ADX

**Files:**
- Create: `investment_screener/backend/py_services/technicals.py`
- Test: `investment_screener/backend/tests/py_services/test_technicals.py`

**Interfaces:**
- Produces (module-level, reused by Task 6):
  - `_wilder_smooth(series: "pd.Series", period: int) -> "pd.Series"`
  - `compute_rsi(closes: "pd.Series", period: int = 14) -> float | None`
  - `compute_ema(closes: "pd.Series", period: int) -> float | None`
  - `compute_macd(closes: "pd.Series") -> dict` — `{"line", "signal", "histogram"}`
  - `compute_atr(highs, lows, closes: "pd.Series", period: int = 14) -> float | None`
  - `compute_adx(highs, lows, closes: "pd.Series", period: int = 14) -> dict` — `{"adx14", "plusDI", "minusDI"}`

- [ ] **Step 1: Write the failing tests**

Create `investment_screener/backend/tests/py_services/test_technicals.py`:

```python
"""Tests for technicals.py — local TA engine, hand-rolled indicators (Phase 2b)."""
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from technicals import compute_adx, compute_atr, compute_ema, compute_macd, compute_rsi  # noqa: E402


def _constant_series(value: float, n: int = 60) -> pd.Series:
    return pd.Series([value] * n)


def _uptrend_series(start: float, step: float, n: int = 60) -> pd.Series:
    return pd.Series([start + step * i for i in range(n)])


# ── RSI ────────────────────────────────────────────────────────────────────

def test_rsi_is_bounded_0_to_100_property():
    closes = pd.Series([100, 102, 101, 105, 103, 108, 107, 110, 106, 112,
                         115, 111, 118, 116, 120, 119, 122, 121, 125, 124] * 3)
    rsi = compute_rsi(closes, period=14)
    assert 0.0 <= rsi <= 100.0


def test_rsi_all_gains_scores_100():
    closes = _uptrend_series(start=100, step=1, n=20)
    rsi = compute_rsi(closes, period=14)
    assert rsi == 100.0


def test_rsi_returns_none_for_insufficient_data():
    closes = pd.Series([100, 101, 102])
    assert compute_rsi(closes, period=14) is None


# ── EMA ────────────────────────────────────────────────────────────────────

def test_ema_converges_to_price_under_constant_series():
    closes = _constant_series(150.0, n=250)
    assert compute_ema(closes, period=21) == 150.0
    assert compute_ema(closes, period=200) == 150.0


# ── MACD ───────────────────────────────────────────────────────────────────

def test_macd_returns_line_signal_histogram_shape():
    closes = _uptrend_series(start=100, step=0.5, n=60)
    macd = compute_macd(closes)
    assert set(macd.keys()) == {"line", "signal", "histogram"}
    assert round(macd["line"] - macd["signal"], 6) == round(macd["histogram"], 6)


def test_macd_line_is_zero_under_constant_series():
    closes = _constant_series(150.0, n=60)
    macd = compute_macd(closes)
    assert macd["line"] == 0.0


# ── ATR ────────────────────────────────────────────────────────────────────

def test_atr_is_non_negative_property():
    highs = _uptrend_series(105, 1, n=30)
    lows = _uptrend_series(95, 1, n=30)
    closes = _uptrend_series(100, 1, n=30)
    atr = compute_atr(highs, lows, closes, period=14)
    assert atr >= 0.0


def test_atr_is_zero_under_flat_no_range_series():
    highs = _constant_series(100.0, n=30)
    lows = _constant_series(100.0, n=30)
    closes = _constant_series(100.0, n=30)
    assert compute_atr(highs, lows, closes, period=14) == 0.0


# ── ADX ────────────────────────────────────────────────────────────────────

def test_adx_returns_shape_and_bounded_range():
    highs = _uptrend_series(105, 1.5, n=40)
    lows = _uptrend_series(95, 1.5, n=40)
    closes = _uptrend_series(100, 1.5, n=40)
    result = compute_adx(highs, lows, closes, period=14)
    assert set(result.keys()) == {"adx14", "plusDI", "minusDI"}
    assert 0.0 <= result["adx14"] <= 100.0
    assert result["plusDI"] > result["minusDI"]  # clean uptrend -> +DI dominates
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_technicals.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'technicals'`.

- [ ] **Step 3: Write minimal implementation**

Create `investment_screener/backend/py_services/technicals.py`:

```python
#!/usr/bin/env python3
"""
technicals.py (Python Service)
=====================================

Purpose:
    Headless local TA engine — hand-rolled implementations (no TA libraries)
    of RSI(14) Wilder, EMA 21/50/200, MACD, ADX(14), ATR(14), Bollinger/
    Keltner squeeze, anchored VWAP, 20d volume ratio, and relative strength
    vs. a benchmark. Computes from OHLCV supplied by market_data.get_prices()
    (yfinance-backed) — never TradingView CDP, which can only read the
    currently-active chart (pitfall #7 in CLAUDE.md) and has no batch/
    background history endpoint. TV is used only as the trust-check, via
    ta_sweep_batch.py --validate (Phase 2b, separate task).

Layer: Backend / Python Services / Technical Analysis

Usage:
    python3 technicals.py --ticker NVDA --timeframe D --period 1y --benchmark SPY --pretty
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from market_data import get_prices  # noqa: E402


def _wilder_smooth(series: pd.Series, period: int) -> pd.Series:
    """Wilder's smoothing: seed with a simple mean of the first `period` values,
    then recursively blend as (prev * (period - 1) + current) / period.

    Args:
        series: Raw per-bar values to smooth (e.g. gains, losses, true range).
        period: Smoothing period (e.g. 14).

    Returns:
        A pandas Series of the same length, with NaN for the first
        `period - 1` bars (insufficient data to seed the average).
    """
    result = pd.Series(index=series.index, dtype=float)
    if len(series) < period:
        return result
    result.iloc[period - 1] = series.iloc[:period].mean()
    for i in range(period, len(series)):
        result.iloc[i] = (result.iloc[i - 1] * (period - 1) + series.iloc[i]) / period
    return result


def compute_rsi(closes: pd.Series, period: int = 14) -> float | None:
    """RSI(14) with Wilder smoothing — the standard, non-EMA-smoothed formula.

    Args:
        closes: Close prices, oldest first.
        period: RSI lookback period, default 14.

    Returns:
        Latest RSI value in [0, 100], or None if fewer than period+1 bars.
    """
    if len(closes) < period + 1:
        return None
    delta = closes.diff().dropna()
    gains = delta.clip(lower=0)
    losses = -delta.clip(upper=0)
    avg_gain = _wilder_smooth(gains, period).iloc[-1]
    avg_loss = _wilder_smooth(losses, period).iloc[-1]
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)


def compute_ema(closes: pd.Series, period: int) -> float | None:
    """Exponential moving average, latest value.

    Args:
        closes: Close prices, oldest first.
        period: EMA span (e.g. 21, 50, 200).

    Returns:
        Latest EMA value, or None if fewer than `period` bars.
    """
    if len(closes) < period:
        return None
    return round(closes.ewm(span=period, adjust=False).mean().iloc[-1], 4)


def compute_macd(closes: pd.Series) -> dict:
    """MACD(12,26,9): fast EMA minus slow EMA, plus a signal EMA of that line.

    Args:
        closes: Close prices, oldest first.

    Returns:
        {"line": float, "signal": float, "histogram": float}, using whatever
        data is available (no minimum-length guard beyond what ewm() itself
        requires — MACD degrades gracefully on shorter series).
    """
    ema12 = closes.ewm(span=12, adjust=False).mean()
    ema26 = closes.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    histogram = macd_line - signal_line
    return {
        "line": round(macd_line.iloc[-1], 4),
        "signal": round(signal_line.iloc[-1], 4),
        "histogram": round(histogram.iloc[-1], 4),
    }


def _true_range(highs: pd.Series, lows: pd.Series, closes: pd.Series) -> pd.Series:
    """Per-bar true range: max(high-low, |high-prev_close|, |low-prev_close|)."""
    prev_close = closes.shift(1)
    return pd.concat([
        highs - lows,
        (highs - prev_close).abs(),
        (lows - prev_close).abs(),
    ], axis=1).max(axis=1)


def compute_atr(highs: pd.Series, lows: pd.Series, closes: pd.Series, period: int = 14) -> float | None:
    """Average True Range (Wilder-smoothed), latest value.

    Args:
        highs: High prices, oldest first.
        lows: Low prices, oldest first.
        closes: Close prices, oldest first.
        period: ATR lookback period, default 14.

    Returns:
        Latest ATR value (>= 0), or None if fewer than period+1 bars.
    """
    if len(closes) < period + 1:
        return None
    tr = _true_range(highs, lows, closes).dropna()
    atr = _wilder_smooth(tr, period).iloc[-1]
    return round(float(atr), 4)


def compute_adx(highs: pd.Series, lows: pd.Series, closes: pd.Series, period: int = 14) -> dict:
    """ADX(14) with +DI/-DI, Wilder-smoothed throughout.

    Args:
        highs: High prices, oldest first.
        lows: Low prices, oldest first.
        closes: Close prices, oldest first.
        period: ADX lookback period, default 14.

    Returns:
        {"adx14": float|None, "plusDI": float|None, "minusDI": float|None}.
        None across all three if fewer than 2*period bars (ADX needs a
        smoothed DX series on top of the smoothed DM/TR series).
    """
    if len(closes) < period * 2:
        return {"adx14": None, "plusDI": None, "minusDI": None}

    up_move = highs.diff()
    down_move = -lows.diff()
    plus_dm = pd.Series(np.where((up_move > down_move) & (up_move > 0), up_move, 0.0), index=highs.index)
    minus_dm = pd.Series(np.where((down_move > up_move) & (down_move > 0), down_move, 0.0), index=highs.index)
    tr = _true_range(highs, lows, closes)

    smoothed_tr = _wilder_smooth(tr.dropna(), period)
    smoothed_plus_dm = _wilder_smooth(plus_dm.dropna(), period)
    smoothed_minus_dm = _wilder_smooth(minus_dm.dropna(), period)

    plus_di = 100 * smoothed_plus_dm / smoothed_tr
    minus_di = 100 * smoothed_minus_dm / smoothed_tr
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    adx = _wilder_smooth(dx.dropna(), period)

    return {
        "adx14": round(float(adx.iloc[-1]), 2),
        "plusDI": round(float(plus_di.iloc[-1]), 2),
        "minusDI": round(float(minus_di.iloc[-1]), 2),
    }


def main() -> None:
    """CLI entry point — wired fully in Task 6 once squeeze/VWAP/RS are added."""
    parser = argparse.ArgumentParser(description="Local TA engine")
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--timeframe", default="D", choices=["D", "W"])
    parser.add_argument("--period", default="1y")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    interval = "1d" if args.timeframe == "D" else "1wk"
    prices = get_prices([args.ticker], period=args.period, interval=interval)
    rows = prices.get(args.ticker, {}).get("data", [])
    df = pd.DataFrame(rows)
    result = {
        "ticker": args.ticker,
        "timeframe": args.timeframe,
        "rsi14": compute_rsi(df["close"]) if not df.empty else None,
        "ema21": compute_ema(df["close"], 21) if not df.empty else None,
        "ema50": compute_ema(df["close"], 50) if not df.empty else None,
        "ema200": compute_ema(df["close"], 200) if not df.empty else None,
        "macd": compute_macd(df["close"]) if not df.empty else None,
        "atr14": compute_atr(df["high"], df["low"], df["close"]) if not df.empty else None,
        **(compute_adx(df["high"], df["low"], df["close"]) if not df.empty else
           {"adx14": None, "plusDI": None, "minusDI": None}),
    }
    print(json.dumps(result, indent=2 if args.pretty else None))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_technicals.py -v`
Expected: PASS. If `test_adx_returns_shape_and_bounded_range` fails with a `+DI == -DI`
assertion, increase the uptrend `step` in the test fixture — a too-gentle synthetic slope
can produce a near-symmetric +DM/-DM split.

- [ ] **Step 5: Commit**

```bash
git add investment_screener/backend/py_services/technicals.py investment_screener/backend/tests/py_services/test_technicals.py
git commit -m "feat: add technicals.py — RSI/EMA/MACD/ATR/ADX (part 1 of local TA engine)"
```

---

### Task 6: `technicals.py` part 2 — squeeze, anchored VWAP, volume ratio, relative strength, full CLI

**Files:**
- Modify: `investment_screener/backend/py_services/technicals.py`
- Test: `investment_screener/backend/tests/py_services/test_technicals.py` (append)

**Interfaces:**
- Consumes: `earnings_calendar.get_earnings_calendar(days_threshold=...) -> list[EarningsEntry]` (for the default VWAP anchor date — reads each entry's `.ticker`/`.earnings_date`).
- Produces:
  - `compute_bollinger_keltner_squeeze(closes, highs, lows, atr14: float) -> dict` — `{"bollinger": {...}, "keltner": {...}, "squeeze": bool}`
  - `compute_anchored_vwap(highs, lows, closes, volumes: pd.Series, dates: pd.Series, anchor_date: str | None) -> float | None`
  - `compute_volume_ratio(volumes: pd.Series, period: int = 20) -> float | None`
  - `compute_relative_strength(closes: pd.Series, benchmark_closes: pd.Series) -> dict` — `{"ratio", "slope63d"}`
  - `compute_technical_snapshot(ticker: str, timeframe: str, period: str, benchmark: str, anchor_date: str | None) -> dict` — the full `TechnicalSnapshot`, used directly by `ta_sweep_batch.py --validate` in Task 8.

- [ ] **Step 1: Write the failing tests**

Append to `investment_screener/backend/tests/py_services/test_technicals.py`:

```python
from unittest.mock import patch  # add to existing imports at top of file

from technicals import (  # noqa: E402
    compute_anchored_vwap,
    compute_bollinger_keltner_squeeze,
    compute_relative_strength,
    compute_technical_snapshot,
    compute_volume_ratio,
)


# ── Bollinger/Keltner squeeze ─────────────────────────────────────────────────

def test_squeeze_true_when_bollinger_inside_keltner():
    # Very low volatility closes -> tight Bollinger bands, squeezed inside Keltner.
    closes = _constant_series(100.0, n=30) + pd.Series([0.01 * (i % 2) for i in range(30)])
    highs = closes + 0.05
    lows = closes - 0.05
    result = compute_bollinger_keltner_squeeze(closes, highs, lows, atr14=0.5)
    assert result["squeeze"] is True


def test_squeeze_false_when_bollinger_outside_keltner():
    closes = _uptrend_series(100, 3, n=30)  # wide bands from a strong trend
    highs = closes + 1.0
    lows = closes - 1.0
    result = compute_bollinger_keltner_squeeze(closes, highs, lows, atr14=0.5)
    assert result["squeeze"] is False


# ── Anchored VWAP ──────────────────────────────────────────────────────────────

def test_anchored_vwap_computes_from_anchor_date_forward():
    dates = pd.Series(["2026-01-01", "2026-01-02", "2026-01-03"])
    highs = pd.Series([102.0, 104.0, 106.0])
    lows = pd.Series([98.0, 100.0, 102.0])
    closes = pd.Series([100.0, 102.0, 104.0])
    volumes = pd.Series([1000.0, 1000.0, 1000.0])
    vwap = compute_anchored_vwap(highs, lows, closes, volumes, dates, anchor_date="2026-01-02")
    # Only bars on/after 2026-01-02 count: typical prices (104+100+102)/3=102, (106+102+104)/3=104
    expected = (102.0 * 1000 + 104.0 * 1000) / (1000 + 1000)
    assert round(vwap, 4) == round(expected, 4)


def test_anchored_vwap_returns_none_when_anchor_date_not_found():
    dates = pd.Series(["2026-01-01", "2026-01-02"])
    highs = pd.Series([102.0, 104.0])
    lows = pd.Series([98.0, 100.0])
    closes = pd.Series([100.0, 102.0])
    volumes = pd.Series([1000.0, 1000.0])
    assert compute_anchored_vwap(highs, lows, closes, volumes, dates, anchor_date="2099-01-01") is None


# ── Volume ratio ───────────────────────────────────────────────────────────────

def test_volume_ratio_above_one_on_volume_spike():
    volumes = pd.Series([1000.0] * 20 + [3000.0])
    assert compute_volume_ratio(volumes, period=20) == 3.0


def test_volume_ratio_returns_none_for_insufficient_data():
    volumes = pd.Series([1000.0] * 5)
    assert compute_volume_ratio(volumes, period=20) is None


# ── Relative strength ──────────────────────────────────────────────────────────

def test_relative_strength_ratio_above_one_when_outperforming():
    ticker_closes = _uptrend_series(100, 2, n=70)
    benchmark_closes = _uptrend_series(100, 0.5, n=70)
    result = compute_relative_strength(ticker_closes, benchmark_closes)
    assert result["ratio"] > 1.0
    assert result["slope63d"] > 0


# ── Full snapshot orchestration ────────────────────────────────────────────────

def test_compute_technical_snapshot_shape():
    rows = [
        {"date": f"2026-01-{i+1:02d}", "open": 100 + i, "high": 102 + i,
         "low": 98 + i, "close": 100 + i, "volume": 1000.0}
        for i in range(60)
    ]
    fake_prices = {"NVDA": {"data": rows}, "SPY": {"data": rows}}
    with patch("technicals.get_prices", return_value=fake_prices), \
         patch("technicals.get_earnings_calendar", return_value=[]):
        snapshot = compute_technical_snapshot("NVDA", "D", "1y", "SPY", anchor_date=None)

    expected_keys = {
        "ticker", "timeframe", "asOf", "rsi14", "ema21", "ema50", "ema200",
        "macd", "adx14", "plusDI", "minusDI", "atr14", "bollinger", "keltner",
        "squeeze", "anchoredVwap", "volumeRatio20d", "relativeStrength",
    }
    assert expected_keys <= set(snapshot.keys())
    assert snapshot["ticker"] == "NVDA"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_technicals.py -v -k "squeeze or vwap or volume_ratio or relative_strength or snapshot"`
Expected: FAIL — `ImportError` for the not-yet-defined functions.

- [ ] **Step 3: Write minimal implementation**

Append to `investment_screener/backend/py_services/technicals.py` (before `def main():`,
replacing the existing `main()` entirely per Step 3b below):

```python
def compute_bollinger_keltner_squeeze(
    closes: pd.Series, highs: pd.Series, lows: pd.Series, atr14: float, period: int = 20
) -> dict:
    """Bollinger(20,2) and Keltner(20, 1.5xATR14) bands, plus squeeze detection.

    Squeeze is True when the Bollinger Bands sit entirely inside the Keltner
    Channel — the standard TTM Squeeze definition, signaling a volatility
    contraction that often precedes a breakout.

    Args:
        closes: Close prices, oldest first.
        highs: High prices, oldest first (unused directly, kept for interface symmetry).
        lows: Low prices, oldest first (unused directly, kept for interface symmetry).
        atr14: Precomputed ATR(14) value, used as the Keltner band width.
        period: SMA/EMA period for both bands' midline, default 20.

    Returns:
        {"bollinger": {"upper","mid","lower"}, "keltner": {"upper","mid","lower"}, "squeeze": bool}.
    """
    sma = closes.rolling(period).mean().iloc[-1]
    std = closes.rolling(period).std().iloc[-1]
    bollinger = {"upper": round(sma + 2 * std, 4), "mid": round(sma, 4), "lower": round(sma - 2 * std, 4)}

    ema = closes.ewm(span=period, adjust=False).mean().iloc[-1]
    keltner_width = 1.5 * atr14
    keltner = {"upper": round(ema + keltner_width, 4), "mid": round(ema, 4), "lower": round(ema - keltner_width, 4)}

    squeeze = bollinger["upper"] < keltner["upper"] and bollinger["lower"] > keltner["lower"]
    return {"bollinger": bollinger, "keltner": keltner, "squeeze": squeeze}


def compute_anchored_vwap(
    highs: pd.Series, lows: pd.Series, closes: pd.Series, volumes: pd.Series,
    dates: pd.Series, anchor_date: str | None,
) -> float | None:
    """Volume-weighted average price from `anchor_date` forward.

    Args:
        highs, lows, closes, volumes: OHLCV columns, oldest first, same length as `dates`.
        dates: ISO date strings ("YYYY-MM-DD"), same index alignment as the OHLCV columns.
        anchor_date: The date to anchor from (inclusive), or None to skip.

    Returns:
        VWAP from the anchor date onward, or None if anchor_date is None or
        not present in `dates`.
    """
    if anchor_date is None or anchor_date not in set(dates):
        return None
    mask = dates >= anchor_date
    typical_price = (highs[mask] + lows[mask] + closes[mask]) / 3
    vol = volumes[mask]
    if vol.sum() == 0:
        return None
    return round(float((typical_price * vol).sum() / vol.sum()), 4)


def compute_volume_ratio(volumes: pd.Series, period: int = 20) -> float | None:
    """Latest volume divided by the trailing `period`-bar average volume.

    Args:
        volumes: Volume series, oldest first.
        period: Lookback window for the average, default 20.

    Returns:
        Ratio (>1.0 = above-average volume), or None if fewer than period+1 bars.
    """
    if len(volumes) < period + 1:
        return None
    avg = volumes.iloc[-(period + 1):-1].mean()
    if avg == 0:
        return None
    return round(float(volumes.iloc[-1] / avg), 3)


def compute_relative_strength(closes: pd.Series, benchmark_closes: pd.Series) -> dict:
    """Cumulative-return ratio vs. a benchmark, plus its 63-day slope.

    Args:
        closes: Ticker close prices, oldest first.
        benchmark_closes: Benchmark (e.g. SPY) close prices, same length/alignment.

    Returns:
        {"ratio": float, "slope63d": float}. Ratio > 1.0 means the ticker has
        outperformed the benchmark since the start of the supplied window;
        slope63d is the least-squares slope of the ratio series over its
        trailing 63 bars (positive = improving relative strength).
    """
    ticker_cum = closes / closes.iloc[0]
    benchmark_cum = benchmark_closes / benchmark_closes.iloc[0]
    ratio_series = (ticker_cum / benchmark_cum).dropna()
    ratio = float(ratio_series.iloc[-1])

    window = ratio_series.iloc[-63:]
    x = np.arange(len(window))
    if len(window) < 2 or np.var(x) == 0:
        slope = 0.0
    else:
        slope = float(np.cov(x, window.values, bias=True)[0, 1] / np.var(x))

    return {"ratio": round(ratio, 4), "slope63d": round(slope, 6)}


def compute_technical_snapshot(
    ticker: str, timeframe: str, period: str, benchmark: str, anchor_date: str | None,
) -> dict:
    """Primary orchestrator — one TechnicalSnapshot per ticker/timeframe.

    If `anchor_date` is not supplied, defaults to the ticker's most recent
    past earnings date from earnings_calendar.py; if neither is available,
    anchoredVwap is None rather than guessed.

    Args:
        ticker: Ticker symbol.
        timeframe: "D" or "W".
        period: yfinance period string (e.g. "1y") passed to market_data.get_prices().
        benchmark: Benchmark ticker for relative strength (e.g. "SPY").
        anchor_date: ISO date string to anchor VWAP from, or None for auto-detection.

    Returns:
        Full TechnicalSnapshot dict — see docs/superpowers/specs/
        2026-07-05-fundamental-analyst-ta-design.md for the field-by-field shape.
    """
    interval = "1d" if timeframe == "D" else "1wk"
    prices = get_prices([ticker, benchmark], period=period, interval=interval)
    rows = prices.get(ticker, {}).get("data", [])
    benchmark_rows = prices.get(benchmark, {}).get("data", [])
    df = pd.DataFrame(rows)
    benchmark_df = pd.DataFrame(benchmark_rows)

    if anchor_date is None:
        anchor_date = _default_earnings_anchor(ticker)

    atr14 = compute_atr(df["high"], df["low"], df["close"]) or 0.0
    adx_result = compute_adx(df["high"], df["low"], df["close"])

    return {
        "ticker": ticker,
        "timeframe": timeframe,
        "asOf": df["date"].iloc[-1] if not df.empty else None,
        "rsi14": compute_rsi(df["close"]),
        "ema21": compute_ema(df["close"], 21),
        "ema50": compute_ema(df["close"], 50),
        "ema200": compute_ema(df["close"], 200),
        "macd": compute_macd(df["close"]),
        **adx_result,
        "atr14": atr14,
        **compute_bollinger_keltner_squeeze(df["close"], df["high"], df["low"], atr14),
        "anchoredVwap": compute_anchored_vwap(
            df["high"], df["low"], df["close"], df["volume"], df["date"], anchor_date
        ),
        "volumeRatio20d": compute_volume_ratio(df["volume"]),
        "relativeStrength": (
            compute_relative_strength(df["close"], benchmark_df["close"])
            if not benchmark_df.empty else {"ratio": None, "slope63d": None}
        ),
    }


def _default_earnings_anchor(ticker: str) -> str | None:
    """Most recent past earnings date for `ticker`, or None if unavailable.

    earnings_calendar.py only forecasts upcoming events by design (see its
    module docstring) — this walks its entries defensively and returns None
    on any shape it doesn't recognize rather than raising, since a missing
    anchor is a normal, expected case (see compute_anchored_vwap's None path).
    Calls the module-level `get_earnings_calendar` (imported at the top of
    this file, not locally) so tests can `patch("technicals.get_earnings_calendar", ...)`
    — a function-local import would make that patch target a name that
    doesn't exist in this module's namespace, and unittest.mock.patch would
    raise AttributeError instead of substituting the stub.
    """
    try:
        entries = get_earnings_calendar()
        for entry in entries:
            if getattr(entry, "ticker", None) == ticker:
                return getattr(entry, "earnings_date", None)
    except Exception:  # noqa: BLE001 - any failure here just means "no anchor available"
        return None
    return None
```

- [ ] **Step 3a: Add the module-level `get_earnings_calendar` import**

At the top of `technicals.py`, in the existing import block (right after
`from market_data import get_prices  # noqa: E402`), add:

```python
from earnings_calendar import get_earnings_calendar  # noqa: E402
```

This must be a top-level, module-scope import (not inside `_default_earnings_anchor`) —
see the docstring above for why: `unittest.mock.patch("technicals.get_earnings_calendar", ...)`
in the Task 6 test only works if that name is resolvable as a `technicals` module
attribute.

- [ ] **Step 3b: Replace the Task 5 placeholder `main()` with the full CLI**

Replace the entire `def main():` block at the bottom of `technicals.py` (the one written
in Task 5, Step 3) with:

```python
def main() -> None:
    parser = argparse.ArgumentParser(description="Local TA engine — full TechnicalSnapshot")
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--timeframe", default="D", choices=["D", "W"])
    parser.add_argument("--period", default="1y")
    parser.add_argument("--benchmark", default="SPY")
    parser.add_argument("--anchor-date", default=None, help="YYYY-MM-DD, omit to auto-detect from earnings")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    result = compute_technical_snapshot(
        args.ticker, args.timeframe, args.period, args.benchmark, args.anchor_date
    )
    print(json.dumps(result, indent=2 if args.pretty else None))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_technicals.py -v`
Expected: PASS — full file, both Task 5 and Task 6 tests green.

- [ ] **Step 5: Commit**

```bash
git add investment_screener/backend/py_services/technicals.py investment_screener/backend/tests/py_services/test_technicals.py
git commit -m "feat: add squeeze/anchored-VWAP/volume-ratio/relative-strength to technicals.py, wire full CLI"
```

---

### Task 7: `validate_projection.py` — optional `sector` enum check

**Files:**
- Modify: `plugins/stock-valuation/scripts/validate_projection.py` (and its two symlinked
  copies resolve automatically — do not edit those paths directly, only the real file)
- Test: find the existing test file covering `validate_projection.py` (search
  `find . -iname "test_validate_projection.py"` from repo root — if none exists yet,
  create `plugins/stock-valuation/tests/test_validate_projection.py` following the same
  `sys.path.insert` + import pattern used in `test_comps_valuation.py`)

**Interfaces:**
- Modifies: `validate_projection(data: dict, verbose: bool = False) -> list[str]` — adds
  one new check, no signature change.

- [ ] **Step 1: Write the failing test**

```bash
find /Users/richardfremmerlid/Projects/InvestmentToolkit -iname "test_validate_projection.py"
```

If a file is found, add the two tests below to it (matching its existing import style —
check the top of that file for how it imports `validate_projection`). If none is found,
create `plugins/stock-valuation/tests/test_validate_projection.py`:

```python
"""Tests for validate_projection.py's optional sector field check."""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = REPO_ROOT / "plugins/stock-valuation/scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from validate_projection import validate_projection  # noqa: E402


def _base_projection(**overrides):
    proj = {
        "ticker": "TEST", "id": "abc", "source": "AI_AGENT", "schemaVersion": "1.2",
        "version": 1, "savedAt": "2026-01-01T00:00:00Z", "rationale": "test",
        "snapshot": {"price": 100.0},
        "scenarios": {
            "bear": {"weight": 0.3, "growthRate": 5, "scenarioPrice": 80},
            "base": {"weight": 0.4, "growthRate": 15, "scenarioPrice": 100},
            "bull": {"weight": 0.3, "growthRate": 25, "scenarioPrice": 130},
        },
        "aiThesis": {"action": "HOLD"},
        "globalSettings": {},
    }
    proj.update(overrides)
    return proj


def test_valid_sector_enum_passes():
    proj = _base_projection(sector="chips_ai")
    errors = validate_projection(proj)
    assert not any("sector" in e for e in errors)


def test_invalid_sector_enum_fails():
    proj = _base_projection(sector="not_a_real_sector")
    errors = validate_projection(proj)
    assert any("sector" in e for e in errors)


def test_missing_sector_is_not_an_error():
    proj = _base_projection()  # no "sector" key at all
    errors = validate_projection(proj)
    assert not any("sector" in e for e in errors)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/richardfremmerlid/Projects/InvestmentToolkit && python3 -m pytest plugins/stock-valuation/tests/test_validate_projection.py -v -k sector`
Expected: FAIL on `test_invalid_sector_enum_fails` (no check exists yet, so no error is produced).

- [ ] **Step 3: Write minimal implementation**

In `plugins/stock-valuation/scripts/validate_projection.py`, add this near the top
(alongside `ACCUMULATE_SPREAD_THRESHOLD_PCT` and friends):

```python
VALID_SECTORS = {"saas_cyber", "chips_ai", "energy_infra"}
```

Then inside `validate_projection()`, right after the `# --- Confidence score ---` block
(before the `# --- Valuation-committee gate (Phase 2a) ---` comment), add:

```python
    # --- Sector enum (Phase 2b, optional field) ---
    sector = data.get("sector")
    if sector is not None:
        check(sector in VALID_SECTORS, "sector",
              f"Must be one of {sorted(VALID_SECTORS)}, got '{sector}'", errors)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/richardfremmerlid/Projects/InvestmentToolkit && python3 -m pytest plugins/stock-valuation/tests/test_validate_projection.py -v`
Expected: PASS — all tests in the file, including any pre-existing ones (confirm no
regression to `check_accumulate_gate` tests if they live in the same file).

- [ ] **Step 5: Commit**

```bash
git add plugins/stock-valuation/scripts/validate_projection.py plugins/stock-valuation/tests/test_validate_projection.py
git commit -m "feat: add optional sector enum check to validate_projection.py"
```

---

### Task 8: `ta_sweep_batch.py --validate` — local vs. TV Data Window cross-check

**Files:**
- Modify: `plugins/tradingview/scripts/ta_sweep_batch.py`
- Test: `plugins/tradingview/tests/test_ta_sweep_batch.py`

**Interfaces:**
- Consumes: `technicals.compute_technical_snapshot(ticker, "D", "3mo", "SPY", None) -> dict`
  (imported cross-package — add `investment_screener/backend/py_services` to `sys.path`
  at the top of `ta_sweep_batch.py`, same pattern already used for intra-package imports).
- Produces: `add_local_validation(result: dict, snapshot_fn=compute_technical_snapshot) -> dict`
  — pure function, injectable snapshot source for testing.

- [ ] **Step 1: Write the failing test**

Add to `plugins/tradingview/tests/test_ta_sweep_batch.py` (append near the other
Category-A pure-function tests):

```python
import sys as _sys
_sys.path.insert(0, str(SCRIPT_DIR))
from ta_sweep_batch import add_local_validation  # noqa: E402


def test_add_local_validation_flags_divergence_over_2pts():
    result = {"ticker": "NVDA", "rsi": 57.9, "adx": 30.1}

    def fake_snapshot(ticker, timeframe, period, benchmark, anchor_date):
        return {"rsi14": 58.2, "adx14": 27.3}

    enriched = add_local_validation(result, snapshot_fn=fake_snapshot)

    assert enriched["localValidation"]["rsi"]["local"] == 58.2
    assert enriched["localValidation"]["rsi"]["tv"] == 57.9
    assert enriched["localValidation"]["rsi"]["flag"] is False  # 0.3pt divergence
    assert enriched["localValidation"]["adx"]["divergencePts"] == 2.8
    assert enriched["localValidation"]["adx"]["flag"] is True  # 2.8pt > 2.0pt threshold


def test_add_local_validation_handles_missing_tv_values():
    result = {"ticker": "NVDA"}  # no "rsi"/"adx" keys from the TV scrape

    def fake_snapshot(ticker, timeframe, period, benchmark, anchor_date):
        return {"rsi14": 58.2, "adx14": 27.3}

    enriched = add_local_validation(result, snapshot_fn=fake_snapshot)
    assert enriched["localValidation"]["rsi"]["tv"] is None
    assert enriched["localValidation"]["rsi"]["flag"] is False  # can't flag without a TV value
```

Confirm `SCRIPT_DIR` is already defined near the top of the test file as
`REPO_ROOT / "plugins/tradingview/scripts"` (it is, per the existing file header) — reuse
it, don't redefine.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/richardfremmerlid/Projects/InvestmentToolkit && python3 -m pytest plugins/tradingview/tests/test_ta_sweep_batch.py -v -k local_validation`
Expected: FAIL — `ImportError: cannot import name 'add_local_validation'`.

- [ ] **Step 3: Write minimal implementation**

In `plugins/tradingview/scripts/ta_sweep_batch.py`, add near the top (after the existing
`REPO_ROOT`/path constants block):

```python
DIVERGENCE_THRESHOLD_PTS = 2.0

sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))
from technicals import compute_technical_snapshot  # noqa: E402
```

Then add this function (near `add_dcf_flags`, in the "Enrichment" section):

```python
def add_local_validation(result: dict[str, Any], snapshot_fn: Any = compute_technical_snapshot) -> dict[str, Any]:
    """Cross-check TV Data Window rsi/adx against technicals.py's local computation.

    Args:
        result: Per-ticker sweep result dict (must have "ticker"; "rsi"/"adx"
            keys are the TV-scraped values, absent or None if the scrape
            didn't produce them).
        snapshot_fn: Injectable — defaults to the real technicals.py call;
            tests pass a stub instead of hitting the network.

    Returns:
        A new dict (result plus a "localValidation" block) — does not mutate
        the input, matching validate_adx()'s existing copy-on-write pattern.
    """
    snapshot = snapshot_fn(result["ticker"], "D", "3mo", "SPY", None)
    result = {**result}
    result["localValidation"] = {}
    for tv_key, local_key in (("rsi", "rsi14"), ("adx", "adx14")):
        tv_value = result.get(tv_key)
        local_value = snapshot.get(local_key)
        divergence = abs(local_value - tv_value) if (local_value is not None and tv_value is not None) else None
        result["localValidation"][tv_key] = {
            "local": local_value,
            "tv": tv_value,
            "divergencePts": round(divergence, 2) if divergence is not None else None,
            "flag": bool(divergence is not None and divergence > DIVERGENCE_THRESHOLD_PTS),
        }
    return result
```

Then wire the CLI flag — add to `main()`'s argparse block:
```python
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Cross-check TV rsi/adx against technicals.py's local computation, flag >2pt divergence",
    )
```
And in `main()`, right after the existing `scan_results = enrich_results(scan_results, target_map)` line:
```python
    if args.validate:
        scan_results = [add_local_validation(r) for r in scan_results]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/richardfremmerlid/Projects/InvestmentToolkit && python3 -m pytest plugins/tradingview/tests/test_ta_sweep_batch.py -v`
Expected: PASS — full file, no regression to the existing `parseNum`/save-results tests.

- [ ] **Step 5: Commit**

```bash
git add plugins/tradingview/scripts/ta_sweep_batch.py plugins/tradingview/tests/test_ta_sweep_batch.py
git commit -m "feat: add --validate mode to ta_sweep_batch.py, cross-checks local TA vs TV Data Window"
```

---

### Task 9: Wire SKILL.md Step 3.6 documentation

**Files:**
- Modify: `plugins/stock-valuation/skills/stock_valuation/SKILL.md`

**Interfaces:** None (documentation-only task).

- [ ] **Step 1: Insert the new section**

In `plugins/stock-valuation/skills/stock_valuation/SKILL.md`, immediately after the
existing "## Step 3.5: Valuation Committee — Additional Lenses (Phase 2a)" section (ends
around the `comps_valuation.py` code block and its `analyticsLog.comps` merge note) and
before "## Step 4: Validate & Repair", insert:

```markdown
## Step 3.6: Fundamental Framework Score + Peer Benchmarking + Local TA (Phase 2b)

After Step 3.5's valuation-committee lenses, run these three additional scripts. Unlike
Step 3.5, none of these gate `aiThesis.action` — they are informational, surfaced in
`/evaluate-stock` output and `analyticsLog` for context.

```bash
# 1. Sector-aware weighted composite score (requires a `sector` field on the
#    projection — set it once, agent-curated, same pattern as `peers`)
python3 investment_screener/backend/py_services/framework_score.py \
  --ticker TICKER --sector {saas_cyber,chips_ai,energy_infra} \
  --projections-dir investment_screener/backend/data/projections \
  [--qualitative-file <qualitative.json>] --pretty
# -> analyticsLog.framework

# 2. Peer benchmarking table (only if projections/{TICKER}.json already has peers)
python3 investment_screener/backend/py_services/peer_bench.py \
  --ticker TICKER --peers <comma_separated_peers> --sector <same_sector_as_above> \
  --projections-dir investment_screener/backend/data/projections --pretty
# -> analyticsLog.peerBench ; {"status": "insufficient_peer_data"} is expected and fine

# 3. Local TA snapshot (independent of TV CDP — works headless)
python3 investment_screener/backend/py_services/technicals.py \
  --ticker TICKER --timeframe D --period 1y --benchmark SPY --pretty
# -> analyticsLog.technicals
```

Merge all three outputs (`framework`, `peerBench`, `technicals`) into the projection's
`analyticsLog` object before Step 4. If `--qualitative-file` isn't supplied,
`framework_score.py`'s output will show `excludedMetrics: ["competitiveMoat",
"newsImpact"]` — this is expected, not an error; fill the file in only when you have
sourced, dated research for those fields (never guess a moat/news rating).
```

- [ ] **Step 2: Verify the doc renders sensibly**

```bash
grep -n "Step 3.6\|Step 4: Validate" plugins/stock-valuation/skills/stock_valuation/SKILL.md
```
Expected: "Step 3.6" appears once, immediately before "Step 4: Validate & Repair" —
confirms correct insertion order.

- [ ] **Step 3: Commit**

```bash
git add plugins/stock-valuation/skills/stock_valuation/SKILL.md
git commit -m "docs: wire framework_score/peer_bench/technicals into SKILL.md Step 3.6"
```

---

## Final verification (after all 9 tasks)

Run the full backend test suite to confirm no cross-task regressions before the
whole-branch review:

```bash
cd /Users/richardfremmerlid/Projects/InvestmentToolkit/investment_screener/backend
python3 -m pytest tests/py_services/ -v
cd /Users/richardfremmerlid/Projects/InvestmentToolkit
python3 -m pytest plugins/tradingview/tests/test_ta_sweep_batch.py plugins/stock-valuation/tests/test_validate_projection.py -v
```
Expected: 100% pass, zero regressions to any Phase 1/2a test.
