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
from wacc import DEFAULT_TAX_RATE  # noqa: E402

# Composite weights — must sum to 1.00, matches the doc's §5 formula exactly.
# NOTE: the doc's own §5 formula lists fcfYield at 0.10, which sums to 1.05
# (an arithmetic error in the source doc). Corrected here to 0.05 so the
# total is exactly 1.00 — a deliberate, traced divergence from the doc text.
COMPOSITE_WEIGHTS = {
    "revenueGrowth": 0.25,
    "ruleOf40": 0.20,
    "operatingMargin": 0.15,
    "roic": 0.10,
    "valuation": 0.10,
    "fcfYield": 0.05,
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


def _score_qualitative(qualitative: dict | None, field: str) -> tuple[str | None, int | None]:
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

    # Single-year step (y2 vs y1), not a multi-year CAGR — get_estimates() only
    # exposes current- and next-fiscal-year revenue estimates, not the full
    # 2025-2028 guidance window the doc describes. Same class of documented
    # simplification as Rule of 40 Method B / FCF Yield / invested capital above.
    y1 = estimates.get("y1RevEstimate")
    y2 = estimates.get("y2RevEstimate")
    revenue_growth = (y2 - y1) / y1 if y1 and y2 and y1 > 0 else None

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
