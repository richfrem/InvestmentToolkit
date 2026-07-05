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

    assert result["metrics"]["ruleOf40"]["raw"] == 0.40
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
