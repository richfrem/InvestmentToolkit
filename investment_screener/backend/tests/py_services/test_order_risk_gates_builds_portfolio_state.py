"""Tests for order_risk_gates.py — build_portfolio_state_for_order() (5E-fix).

Constructs the portfolio_state dict check_mrc_limit()/check_cluster_variance()
require ({"holdings": {ticker: {"weight_pct", "pillar_id"}}, "total_value"})
from the REAL data sources: domain_model.sqlite's `investment` table
(ticker -> pillar_id, Wave 2 consumer cutover — previously target-portfolio.json's
"pillarId" field) + portfolio.json (actual weights via portfolio_io), reusing
portfolio_io.load_portfolio_state()/compute_weights() unchanged — no weight
math is reimplemented here.

Tests pass real constructed temp fixture files/DBs (via tmp_path), matching
this project's established pattern (see test_portfolio_io.py) — no mocking of
the pure file-read logic under test.
"""
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from order_risk_gates import build_portfolio_state_for_order  # noqa: E402
from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.investment_repository import (  # noqa: E402
    resolve_investment,
    update_investment_fields,
)
from domain_model.pillar_repository import resolve_pillar  # noqa: E402


def _write_json(path: Path, data) -> Path:
    path.write_text(json.dumps(data))
    return path


def _make_db(tmp_path: Path, holdings: list[tuple[str, str]]) -> Path:
    """holdings: list of (ticker, pillar_id)."""
    db_path = tmp_path / "domain_model.sqlite"
    conn = initialize_db(str(db_path))
    for ticker, pillar_id in holdings:
        resolve_pillar(conn, pillar_id, name=pillar_id)
        investment_id = resolve_investment(conn, ticker)
        update_investment_fields(conn, investment_id, pillar_id=pillar_id)
    conn.close()
    return db_path


def test_missing_files_degrade_to_empty_state(tmp_path):
    """Neither domain_model.sqlite nor portfolio.json exist -> {"holdings": {},
    "total_value": 0.0}, never raises. A missing DB path is initialized fresh
    (empty) by initialize_db(), so the pillar map degrades to {}."""
    missing_db = tmp_path / "no-domain-model.sqlite"
    missing_portfolio = tmp_path / "no-portfolio.json"

    result = build_portfolio_state_for_order(
        db_path=missing_db, portfolio_path=missing_portfolio
    )

    assert result == {"holdings": {}, "total_value": 0.0}


def test_malformed_portfolio_json_degrades_to_empty_state(tmp_path):
    """Malformed JSON in portfolio.json degrades gracefully."""
    db_path = _make_db(tmp_path, [])
    portfolio = tmp_path / "portfolio.json"
    portfolio.write_text("{not valid json")

    result = build_portfolio_state_for_order(db_path=db_path, portfolio_path=portfolio)

    assert result == {"holdings": {}, "total_value": 0.0}


def test_realistic_two_holding_fixture_produces_correct_weight_and_pillar(tmp_path):
    """A realistic 2-holding fixture -> correct weight_pct/pillar_id per ticker."""
    db_path = _make_db(tmp_path, [
        ("AAPL", "core-compounders"),
        ("MSFT", "core-compounders"),
    ])
    portfolio = _write_json(tmp_path / "portfolio.json", {
        "holdings": [
            {"symbol": "AAPL", "shares": 10, "price": 150.0},
            {"symbol": "MSFT", "shares": 5, "price": 400.0},
        ],
        "totals": {"totalUSD": 4000.0},
    })

    result = build_portfolio_state_for_order(db_path=db_path, portfolio_path=portfolio)

    assert result["total_value"] == 4000.0
    # AAPL: 10*150/4000*100 = 37.5%; MSFT: 5*400/4000*100 = 50.0%
    assert abs(result["holdings"]["AAPL"]["weight_pct"] - 37.5) < 0.01
    assert result["holdings"]["AAPL"]["pillar_id"] == "core-compounders"
    assert abs(result["holdings"]["MSFT"]["weight_pct"] - 50.0) < 0.01
    assert result["holdings"]["MSFT"]["pillar_id"] == "core-compounders"


def test_ticker_with_no_pillar_assignment_falls_back_to_unassigned(tmp_path):
    """A ticker held in portfolio.json but absent from the investment table
    gets pillar_id="unassigned" (matches E1's own convention)."""
    db_path = _make_db(tmp_path, [])
    portfolio = _write_json(tmp_path / "portfolio.json", {
        "holdings": [{"symbol": "NBIS", "shares": 20, "price": 50.0}],
        "totals": {"totalUSD": 1000.0},
    })

    result = build_portfolio_state_for_order(db_path=db_path, portfolio_path=portfolio)

    assert result["holdings"]["NBIS"]["pillar_id"] == "unassigned"
    assert abs(result["holdings"]["NBIS"]["weight_pct"] - 100.0) < 0.01


def test_ticker_with_pillar_but_no_portfolio_weight_gets_zero_weight(tmp_path):
    """A ticker in the investment table but not actually held (no weight)
    still appears with weight_pct=0.0, not omitted."""
    db_path = _make_db(tmp_path, [("PLTR", "ai-thesis")])
    portfolio = _write_json(tmp_path / "portfolio.json", {
        "holdings": [],
        "totals": {"totalUSD": 1000.0},
    })

    result = build_portfolio_state_for_order(db_path=db_path, portfolio_path=portfolio)

    assert result["holdings"]["PLTR"]["weight_pct"] == 0.0
    assert result["holdings"]["PLTR"]["pillar_id"] == "ai-thesis"
