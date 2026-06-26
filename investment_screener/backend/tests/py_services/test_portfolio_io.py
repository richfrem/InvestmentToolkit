"""
Tests for portfolio_io.py — shared safe I/O layer for all portfolio scripts.

Key invariant under test:
  load_portfolio_state() MUST use totals.totalUSD as the denominator for weights.
  It must NEVER compute total from shares×price (produces different result when
  cash/USD positions are held outside individual holdings, or when broker total
  differs from sum-of-parts).

Test tier: Category A (pure) + Category B (subprocess / file I/O).
"""

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT     = Path(__file__).resolve().parents[4]
PY_SERVICES   = REPO_ROOT / "investment_screener/backend/py_services"
PORTFOLIO_IO  = PY_SERVICES / "portfolio_io.py"
FIXTURES      = REPO_ROOT / "investment_screener/backend/tests/fixtures"

PORTFOLIO_WITH_TOTALS = FIXTURES / "portfolio_with_totals.test.json"
PORTFOLIO_FLAT        = FIXTURES / "portfolio.test.json"

sys.path.insert(0, str(PY_SERVICES))


# ── module importability ───────────────────────────────────────────────────────

def test_portfolio_io_is_importable():
    """portfolio_io.py must be importable without error."""
    import importlib
    spec = importlib.util.spec_from_file_location("portfolio_io", PORTFOLIO_IO)
    assert spec is not None, f"Cannot locate {PORTFOLIO_IO}"
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert hasattr(mod, "load_portfolio_state"), "Missing load_portfolio_state"
    assert hasattr(mod, "compute_weights"),      "Missing compute_weights"
    assert hasattr(mod, "replace_block"),        "Missing replace_block"


# ── load_portfolio_state: broker total as denominator ────────────────────────

def test_load_portfolio_state_returns_broker_total():
    """total_usd must come from totals.totalUSD, NOT from summing shares×price."""
    from portfolio_io import load_portfolio_state
    state = load_portfolio_state(PORTFOLIO_WITH_TOTALS)

    # totals.totalUSD = 4500 in fixture; shares×price sum = 10×150 + 5×400 + 100×10 = 4500
    # NOTE: fixture was crafted so sums match — the KEY test is the SOURCE, not the value.
    # We verify by checking the test fixture JSON directly.
    raw = json.loads(PORTFOLIO_WITH_TOTALS.read_text())
    expected_total = raw["totals"]["totalUSD"]

    assert state["total_usd"] == expected_total, (
        f"total_usd={state['total_usd']} but broker total is {expected_total}. "
        "load_portfolio_state must read totals.totalUSD, not compute from shares×price."
    )


def test_load_portfolio_state_broker_total_differs_from_computed():
    """When broker total ≠ shares×price sum, load_portfolio_state uses broker total."""
    import tempfile, json
    from portfolio_io import load_portfolio_state

    # Craft portfolio where broker total (4999) != shares×price (3500)
    data = {
        "holdings": [
            {"symbol": "AAPL", "shares": 10, "price": 150.0},
            {"symbol": "MSFT", "shares": 5,  "price": 400.0},
        ],
        "totals": {"totalUSD": 4999.0, "holdingsUSD": 3500.0}
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        p = Path(f.name)

    try:
        state = load_portfolio_state(p)
        assert state["total_usd"] == 4999.0, (
            f"Expected broker total 4999.0, got {state['total_usd']}. "
            "Shares×price sum would be 3500.0 — wrong denominator."
        )
    finally:
        p.unlink()


def test_load_portfolio_state_shares_map():
    """shares map must include all holdings, with PSU.U.TO normalized to PSU-U.TO."""
    from portfolio_io import load_portfolio_state
    state = load_portfolio_state(PORTFOLIO_WITH_TOTALS)

    assert "AAPL" in state["shares"]
    assert "MSFT" in state["shares"]
    assert "PSU-U.TO" in state["shares"], "PSU.U.TO must be normalized to PSU-U.TO"
    assert "PSU.U.TO" not in state["shares"], "PSU.U.TO alias must be removed after normalization"
    assert state["shares"]["AAPL"] == 10.0
    assert state["shares"]["MSFT"] == 5.0


def test_load_portfolio_state_flat_list_fallback():
    """Flat list format (no totals key) must still work — total computed from shares×price."""
    from portfolio_io import load_portfolio_state
    state = load_portfolio_state(PORTFOLIO_FLAT)

    # Flat list: [{"symbol": "AAPL", "shares": 10, "price": 150}, {"symbol": "MSFT", ...}]
    # No totals.totalUSD — must fall back to computed total
    assert state["total_usd"] > 0, "Flat list fallback must produce non-zero total"
    assert "AAPL" in state["shares"]


# ── compute_weights ────────────────────────────────────────────────────────────

def test_compute_weights_uses_provided_total():
    """compute_weights must use the provided total_usd, never recompute it."""
    from portfolio_io import compute_weights
    shares = {"AAPL": 10.0, "MSFT": 5.0}
    prices = {"AAPL": 150.0, "MSFT": 400.0}
    total  = 4000.0  # intentionally larger than shares×price sum (3500)

    weights = compute_weights(shares, prices, total)

    # AAPL: 10×150/4000×100 = 37.5%
    assert abs(weights.get("AAPL", 0) - 37.5) < 0.01, (
        f"AAPL weight={weights.get('AAPL')}, expected 37.5% using total=4000 denominator"
    )
    # MSFT: 5×400/4000×100 = 50.0%
    assert abs(weights.get("MSFT", 0) - 50.0) < 0.01, (
        f"MSFT weight={weights.get('MSFT')}, expected 50.0% using total=4000 denominator"
    )


def test_compute_weights_skips_missing_prices():
    """Tickers with no price entry must be excluded from output (not crash)."""
    from portfolio_io import compute_weights
    shares = {"AAPL": 10.0, "GHOST": 5.0}
    prices = {"AAPL": 150.0}  # GHOST has no price

    weights = compute_weights(shares, prices, 1500.0)
    assert "AAPL" in weights
    assert "GHOST" not in weights  # no price → excluded, not zero-valued


# ── replace_block ──────────────────────────────────────────────────────────────

SAMPLE_MD = """# My Thesis

Some intro text.

<!-- AUTO_UPDATE_START: portfolio_blueprint -->
OLD CONTENT LINE 1
OLD CONTENT LINE 2
<!-- AUTO_UPDATE_END: portfolio_blueprint -->

## Next Section
"""

def test_replace_block_updates_existing():
    """replace_block must replace content between existing delimiters."""
    from portfolio_io import replace_block
    result = replace_block(SAMPLE_MD, "portfolio_blueprint", "NEW CONTENT")

    assert "NEW CONTENT" in result
    assert "OLD CONTENT LINE 1" not in result
    assert "OLD CONTENT LINE 2" not in result
    # Delimiters must be preserved
    assert "<!-- AUTO_UPDATE_START: portfolio_blueprint -->" in result
    assert "<!-- AUTO_UPDATE_END: portfolio_blueprint -->" in result
    # Content outside the block must be preserved
    assert "# My Thesis" in result
    assert "## Next Section" in result


def test_replace_block_appends_when_missing():
    """replace_block must append block when it doesn't exist in the document."""
    from portfolio_io import replace_block
    doc = "# My Thesis\n\nNo blocks here.\n"
    result = replace_block(doc, "new_block", "APPENDED CONTENT")

    assert "APPENDED CONTENT" in result
    assert "<!-- AUTO_UPDATE_START: new_block -->" in result
    assert "<!-- AUTO_UPDATE_END: new_block -->" in result
    assert "# My Thesis" in result  # original preserved


def test_replace_block_is_idempotent():
    """replace_block called twice with same content must produce same result."""
    from portfolio_io import replace_block
    first  = replace_block(SAMPLE_MD, "portfolio_blueprint", "STABLE CONTENT")
    second = replace_block(first, "portfolio_blueprint", "STABLE CONTENT")
    assert first == second, "replace_block must be idempotent"
