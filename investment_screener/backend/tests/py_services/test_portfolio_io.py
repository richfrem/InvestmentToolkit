"""
Tests for portfolio_io.py — shared safe I/O layer for all portfolio scripts.

Key invariant under test (Wave 3+):
  load_portfolio_state() delegates entirely to
  domain_model.portfolio_repository.load_portfolio_state_from_db(). The
  authoritative total is computed exactly once, in portfolio_repository.py's
  get_portfolio_total_value() (an account-level rollup) -- never recomputed
  ad hoc in this module, and never read from portfolio.json (that JSON-era
  contract, including the PORTFOLIO_WITH_TOTALS/PORTFOLIO_FLAT fixtures below,
  was retired by the Wave 3 cutover; see
  test_load_portfolio_state_reads_from_sqlite_not_json).

Test tier: Category A (pure) + Category B (subprocess / file I/O) + Category C (sqlite).
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


# ── load_portfolio_state: SQLite-backed (Wave 3+) ────────────────────────────
#
# The four tests below replace the pre-Wave-3 JSON-fixture tests
# (test_load_portfolio_state_returns_broker_total,
# test_load_portfolio_state_broker_total_differs_from_computed,
# test_load_portfolio_state_shares_map, test_load_portfolio_state_flat_list_fallback).
# Those tested a portfolio.json-specific contract (totals.totalUSD,
# flat-list fallback) that no longer exists once load_portfolio_state()
# delegates to SQLite — see docstring above. PORTFOLIO_WITH_TOTALS and
# PORTFOLIO_FLAT fixtures are kept on disk only for historical reference; they
# are intentionally unused now.

def _build_test_db(tmp_path, rows):
    """Build a throwaway domain_model.sqlite with the given (account, symbol,
    qty, price) rows and return its path. Shared helper for the SQLite-backed
    load_portfolio_state tests below.
    """
    from domain_model.db_client import initialize_db
    from domain_model.account_repository import upsert_account
    from domain_model.investment_repository import resolve_investment
    from domain_model.investment_price_repository import upsert_investment_price
    from domain_model.account_investment_repository import upsert_account_investment

    db_path = str(tmp_path / "test.sqlite")
    conn = initialize_db(db_path)
    seen_accounts: set[str] = set()
    for account_id, symbol, qty, price in rows:
        if account_id not in seen_accounts:
            upsert_account(conn, account_id, account_id, account_id)
            seen_accounts.add(account_id)
        inv_id = resolve_investment(conn, symbol, asset_class="EQUITY", currency="USD")
        upsert_investment_price(conn, inv_id, price=price, currency="USD", fetched_at="2026-07-20T00:00:00Z")
        upsert_account_investment(
            conn, account_id, inv_id, quantity=qty, average_cost=price,
            book_value=qty * price, currency="USD", last_synced_at="2026-07-20T00:00:00Z",
        )
    conn.close()
    return db_path


def test_load_portfolio_state_total_is_account_rollup_not_ad_hoc(tmp_path, monkeypatch):
    """total_usd must equal the SUM of per-account market values (the single,
    authoritative computation in portfolio_repository.get_portfolio_total_value),
    never a separately re-derived shares×price sum computed inside portfolio_io.
    """
    sys.path.insert(0, str(PY_SERVICES))
    import portfolio_io
    from domain_model.db_client import initialize_db
    from domain_model.portfolio_repository import get_portfolio_total_value

    db_path = _build_test_db(tmp_path, [("TFSA", "AAPL", 10, 150.0), ("RRSP", "MSFT", 5, 400.0)])
    monkeypatch.setattr(portfolio_io, "_DB_PATH", db_path)

    state = portfolio_io.load_portfolio_state(Path("unused.json"))

    conn = initialize_db(db_path)
    try:
        expected_total = get_portfolio_total_value(conn)
    finally:
        conn.close()

    assert state["total_usd"] == expected_total
    assert state["total_usd"] == 10 * 150.0 + 5 * 400.0


def test_load_portfolio_state_total_reflects_multi_account_positions(tmp_path, monkeypatch):
    """Positions in different accounts for different symbols must all roll up
    into a single portfolio-wide total_usd — not just the first account seen.
    """
    sys.path.insert(0, str(PY_SERVICES))
    import portfolio_io

    db_path = _build_test_db(tmp_path, [("TFSA", "AAPL", 10, 150.0), ("RRSP", "AAPL", 5, 150.0)])
    monkeypatch.setattr(portfolio_io, "_DB_PATH", db_path)

    state = portfolio_io.load_portfolio_state(Path("unused.json"))
    assert state["total_usd"] == 15 * 150.0


def test_load_portfolio_state_shares_map(tmp_path, monkeypatch):
    """shares map must include all holdings, aggregated by symbol across accounts."""
    sys.path.insert(0, str(PY_SERVICES))
    import portfolio_io

    db_path = _build_test_db(tmp_path, [("TFSA", "AAPL", 10, 150.0), ("RRSP", "MSFT", 5, 400.0)])
    monkeypatch.setattr(portfolio_io, "_DB_PATH", db_path)

    state = portfolio_io.load_portfolio_state(Path("unused.json"))
    assert state["shares"]["AAPL"] == 10.0
    assert state["shares"]["MSFT"] == 5.0


def test_load_portfolio_state_empty_db_returns_empty_not_crash(tmp_path, monkeypatch):
    """An empty (freshly initialized) domain_model.sqlite must return empty
    shares/prices and a zero total, not raise.
    """
    sys.path.insert(0, str(PY_SERVICES))
    import portfolio_io

    db_path = _build_test_db(tmp_path, [])
    monkeypatch.setattr(portfolio_io, "_DB_PATH", db_path)

    state = portfolio_io.load_portfolio_state(Path("unused.json"))
    assert state["shares"] == {}
    assert state["prices"] == {}
    assert state["total_usd"] == 0


def test_load_portfolio_state_reads_from_sqlite_not_json(tmp_path, monkeypatch):
    """After Wave 3's cutover, load_portfolio_state() must read domain_model.sqlite,
    not portfolio.json -- even if a stale portfolio.json still exists on disk.
    """
    sys.path.insert(0, str(PY_SERVICES))
    from domain_model.db_client import initialize_db
    from domain_model.account_repository import upsert_account
    from domain_model.investment_repository import resolve_investment
    from domain_model.investment_price_repository import upsert_investment_price
    from domain_model.account_investment_repository import upsert_account_investment

    db_path = str(tmp_path / "test.sqlite")
    conn = initialize_db(db_path)
    upsert_account(conn, "TFSA", "TFSA", "TFSA")
    aapl_id = resolve_investment(conn, "AAPL", asset_class="EQUITY", currency="USD")
    upsert_investment_price(conn, aapl_id, price=200.0, currency="USD", fetched_at="2026-07-20T00:00:00Z")
    upsert_account_investment(
        conn, "TFSA", aapl_id, quantity=5, average_cost=180.0,
        book_value=900.0, currency="USD", last_synced_at="2026-07-20T00:00:00Z",
    )
    conn.close()

    import portfolio_io
    monkeypatch.setattr(portfolio_io, "_DB_PATH", db_path)

    # A stale portfolio.json exists but must NOT be read.
    stale_json = tmp_path / "portfolio.json"
    stale_json.write_text('{"holdings": [{"symbol": "MSFT", "shares": 999, "price": 1.0}]}')

    state = portfolio_io.load_portfolio_state(stale_json)
    assert state["shares"] == {"AAPL": 5}
    assert "MSFT" not in state["shares"]


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


# ── target weight loading (Wave 8) ──────────────────────────────────────────

def test_load_target_weights_reads_investment_target_weight(tmp_path):
    """load_target_weights() must read investment.target_weight from SQLite,
    replacing the several duplicate direct reads of target-portfolio.json's
    targetWeight field (generate_review_json.py, validate_weights.py, etc.)."""
    sys.path.insert(0, str(PY_SERVICES))
    from domain_model.db_client import initialize_db
    from domain_model.investment_repository import resolve_investment, update_investment_fields
    from portfolio_io import load_target_weights

    db_path = tmp_path / "test.sqlite"
    conn = initialize_db(str(db_path))
    nvda_id = resolve_investment(conn, "NVDA", asset_class="EQUITY")
    update_investment_fields(conn, nvda_id, target_weight=5.5)
    msft_id = resolve_investment(conn, "MSFT", asset_class="EQUITY")
    update_investment_fields(conn, msft_id, target_weight=0)
    conn.close()

    weights = load_target_weights(str(db_path))
    assert weights == {"NVDA": 5.5}


def test_load_target_weights_returns_empty_for_no_targets(tmp_path):
    sys.path.insert(0, str(PY_SERVICES))
    from domain_model.db_client import initialize_db
    from portfolio_io import load_target_weights

    db_path = tmp_path / "empty.sqlite"
    initialize_db(str(db_path)).close()
    assert load_target_weights(str(db_path)) == {}


def test_load_thesis_holdings_reads_investment_columns(tmp_path):
    """Wave 8: load_thesis_holdings() replaces per-script direct reads of
    target-portfolio.json's `holdings` array."""
    sys.path.insert(0, str(PY_SERVICES))
    from domain_model.db_client import initialize_db
    from domain_model.investment_repository import resolve_investment, update_investment_fields
    from domain_model.pillar_repository import resolve_pillar
    from portfolio_io import load_thesis_holdings

    db_path = tmp_path / "test.sqlite"
    conn = initialize_db(str(db_path))
    resolve_pillar(conn, "compute", "Compute", target_weight=40.0)
    nvda_id = resolve_investment(conn, "NVDA", asset_class="EQUITY")
    update_investment_fields(
        conn, nvda_id, target_weight=10.0, pillar_id="compute",
        lifecycle_status="accumulate", thesis_for_inclusion="AI leader.",
        agent_rationale="DCF BUY.",
    )
    # Not a thesis holding -- no target_weight set.
    resolve_investment(conn, "MSFT", asset_class="EQUITY")
    conn.close()

    holdings = load_thesis_holdings(str(db_path))
    assert len(holdings) == 1
    nvda = holdings[0]
    assert nvda["ticker"] == "NVDA"
    assert nvda["targetWeight"] == 10.0
    assert nvda["pillarId"] == "compute"
    assert nvda["role"] == "accumulate"
    assert nvda["thesisForInclusion"] == "AI leader."


def test_load_thesis_holdings_returns_empty_for_no_holdings(tmp_path):
    sys.path.insert(0, str(PY_SERVICES))
    from domain_model.db_client import initialize_db
    from portfolio_io import load_thesis_holdings

    db_path = tmp_path / "empty.sqlite"
    initialize_db(str(db_path)).close()
    assert load_thesis_holdings(str(db_path)) == []
