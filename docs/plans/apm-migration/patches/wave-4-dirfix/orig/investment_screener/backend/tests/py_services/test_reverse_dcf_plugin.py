"""Tests for reverse_dcf.py — solve_implied_growth()'s convergence handling.

Regression coverage for a bug found via external review + independent verification: the final
return block computed and returned impliedGrowth/impliedGrowthVsBaseCase/impliedGrowthVsGuidance
unconditionally, even when the bisection loop exhausted MAX_ITERATIONS without converging — only
the separate OUT_OF_BRACKET_RANGE early-return correctly nulled these fields. A non-converged
numeric value could silently satisfy check_accumulate_gate()'s impliedGrowth lens.
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = REPO_ROOT / "plugins/stock-valuation/scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from reverse_dcf import solve_implied_growth  # noqa: E402


def test_solve_implied_growth_nulls_fields_when_not_converged(monkeypatch):
    """Force iteration-exhausted non-convergence by patching MAX_ITERATIONS to 1 —
    the loop runs once (assigning `mid`, a real in-bracket number) but with a
    550pp bracket there's no way a single bisection step satisfies the
    tolerance, so `converged` stays False. Before the fix, this in-bracket
    non-convergence case would still return numeric growth fields."""
    monkeypatch.setattr("reverse_dcf.MAX_ITERATIONS", 1)

    result = solve_implied_growth(
        price=185.50,
        base_shares=100_000_000,
        discount_rate=0.10,
        horizon=5,
        margin=25.0,
        exit_pe=30.0,
        quality_multiplier=1.0,
        base_revenue=1_000_000_000,
        bear_growth=10.0,
        base_growth=22.0,
        bull_growth=35.0,
    )

    assert result["converged"] is False
    assert result["impliedGrowth"] is None
    assert result["impliedGrowthVsBaseCase"] is None
    assert result["impliedGrowthVsGuidance"] is None


def test_solve_implied_growth_still_nulls_with_guidance_when_not_converged(monkeypatch):
    monkeypatch.setattr("reverse_dcf.MAX_ITERATIONS", 1)

    result = solve_implied_growth(
        price=185.50,
        base_shares=100_000_000,
        discount_rate=0.10,
        horizon=5,
        margin=25.0,
        exit_pe=30.0,
        quality_multiplier=1.0,
        base_revenue=1_000_000_000,
        bear_growth=10.0,
        base_growth=22.0,
        bull_growth=35.0,
        guided_growth=20.0,
    )

    assert result["converged"] is False
    assert result["impliedGrowthVsGuidance"] is None


def test_solve_implied_growth_still_returns_numeric_fields_when_converged():
    """Sanity check: the fix must not null fields on the normal, converged path."""
    result = solve_implied_growth(
        price=185.50,
        base_shares=100_000_000,
        discount_rate=0.10,
        horizon=5,
        margin=25.0,
        exit_pe=30.0,
        quality_multiplier=1.0,
        base_revenue=1_000_000_000,
        bear_growth=10.0,
        base_growth=22.0,
        bull_growth=35.0,
    )

    assert result["converged"] is True
    assert result["impliedGrowth"] is not None
    assert result["impliedGrowthVsBaseCase"] is not None


def test_solve_implied_growth_zero_iterations_does_not_crash(monkeypatch):
    """Regression for a crash found while writing the non-convergence test above:
    with MAX_ITERATIONS patched to 0, the loop body never executes, so `mid` was
    previously unassigned when the post-loop code tried to read it (UnboundLocalError).
    `mid` is now initialized before the loop, so this degrades to a null result
    instead of crashing."""
    monkeypatch.setattr("reverse_dcf.MAX_ITERATIONS", 0)

    result = solve_implied_growth(
        price=185.50,
        base_shares=100_000_000,
        discount_rate=0.10,
        horizon=5,
        margin=25.0,
        exit_pe=30.0,
        quality_multiplier=1.0,
        base_revenue=1_000_000_000,
        bear_growth=10.0,
        base_growth=22.0,
        bull_growth=35.0,
    )

    assert result["converged"] is False
    assert result["impliedGrowth"] is None


def test_solve_implied_growth_out_of_bracket_still_nulls_as_before():
    """Existing OUT_OF_BRACKET_RANGE behavior must be unchanged by this fix."""
    result = solve_implied_growth(
        price=1e12,  # absurdly high price, unreachable within the bracket
        base_shares=100_000_000,
        discount_rate=0.10,
        horizon=5,
        margin=25.0,
        exit_pe=30.0,
        quality_multiplier=1.0,
        base_revenue=1_000_000_000,
        bear_growth=10.0,
        base_growth=22.0,
        bull_growth=35.0,
    )

    assert result["verdict"] == "OUT_OF_BRACKET_RANGE"
    assert result["converged"] is False
    assert result["impliedGrowth"] is None
