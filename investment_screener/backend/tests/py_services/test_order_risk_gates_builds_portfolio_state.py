"""Tests for order_risk_gates.py — build_portfolio_state_for_order() (5E-fix).

Constructs the portfolio_state dict check_mrc_limit()/check_cluster_variance()
require ({"holdings": {ticker: {"weight_pct", "pillar_id"}}, "total_value"})
from the REAL data files (target-portfolio.json + portfolio.json), reusing
portfolio_io.load_portfolio_state()/compute_weights() and risk_engine.py's
compute_risk_snapshot() pillar_map pattern exactly — no weight math is
reimplemented here.

Tests pass real constructed temp fixture files (via tmp_path), matching this
project's established pattern (see test_portfolio_io.py) — no mocking of the
pure file-read logic under test.
"""
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from order_risk_gates import build_portfolio_state_for_order  # noqa: E402


def _write_json(path: Path, data) -> Path:
    path.write_text(json.dumps(data))
    return path


def test_missing_files_degrade_to_empty_state(tmp_path):
    """Neither target-portfolio.json nor portfolio.json exist -> {"holdings": {},
    "total_value": 0.0}, never raises."""
    missing_target = tmp_path / "no-target-portfolio.json"
    missing_portfolio = tmp_path / "no-portfolio.json"

    result = build_portfolio_state_for_order(
        target_portfolio_path=missing_target, portfolio_path=missing_portfolio
    )

    assert result == {"holdings": {}, "total_value": 0.0}


def test_malformed_target_portfolio_json_degrades_to_empty_state(tmp_path):
    """Malformed JSON in target-portfolio.json degrades gracefully."""
    target = tmp_path / "target-portfolio.json"
    target.write_text("{not valid json")
    portfolio = tmp_path / "portfolio.json"
    _write_json(portfolio, {"holdings": [], "totals": {"totalUSD": 0.0}})

    result = build_portfolio_state_for_order(target_portfolio_path=target, portfolio_path=portfolio)

    assert result == {"holdings": {}, "total_value": 0.0}


def test_realistic_two_holding_fixture_produces_correct_weight_and_pillar(tmp_path):
    """A realistic 2-holding fixture -> correct weight_pct/pillar_id per ticker."""
    target = _write_json(tmp_path / "target-portfolio.json", {
        "holdings": [
            {"ticker": "AAPL", "pillarId": "core-compounders"},
            {"ticker": "MSFT", "pillarId": "core-compounders"},
        ]
    })
    portfolio = _write_json(tmp_path / "portfolio.json", {
        "holdings": [
            {"symbol": "AAPL", "shares": 10, "price": 150.0},
            {"symbol": "MSFT", "shares": 5, "price": 400.0},
        ],
        "totals": {"totalUSD": 4000.0},
    })

    result = build_portfolio_state_for_order(target_portfolio_path=target, portfolio_path=portfolio)

    assert result["total_value"] == 4000.0
    # AAPL: 10*150/4000*100 = 37.5%; MSFT: 5*400/4000*100 = 50.0%
    assert abs(result["holdings"]["AAPL"]["weight_pct"] - 37.5) < 0.01
    assert result["holdings"]["AAPL"]["pillar_id"] == "core-compounders"
    assert abs(result["holdings"]["MSFT"]["weight_pct"] - 50.0) < 0.01
    assert result["holdings"]["MSFT"]["pillar_id"] == "core-compounders"


def test_ticker_with_no_pillar_assignment_falls_back_to_unassigned(tmp_path):
    """A ticker held in portfolio.json but absent from target-portfolio.json's
    holdings gets pillar_id="unassigned" (matches E1's own convention)."""
    target = _write_json(tmp_path / "target-portfolio.json", {"holdings": []})
    portfolio = _write_json(tmp_path / "portfolio.json", {
        "holdings": [{"symbol": "NBIS", "shares": 20, "price": 50.0}],
        "totals": {"totalUSD": 1000.0},
    })

    result = build_portfolio_state_for_order(target_portfolio_path=target, portfolio_path=portfolio)

    assert result["holdings"]["NBIS"]["pillar_id"] == "unassigned"
    assert abs(result["holdings"]["NBIS"]["weight_pct"] - 100.0) < 0.01


def test_ticker_with_pillar_but_no_portfolio_weight_gets_zero_weight(tmp_path):
    """A ticker in target-portfolio.json's holdings but not actually held (no
    weight) still appears with weight_pct=0.0, not omitted."""
    target = _write_json(tmp_path / "target-portfolio.json", {
        "holdings": [{"ticker": "PLTR", "pillarId": "ai-thesis"}]
    })
    portfolio = _write_json(tmp_path / "portfolio.json", {
        "holdings": [],
        "totals": {"totalUSD": 1000.0},
    })

    result = build_portfolio_state_for_order(target_portfolio_path=target, portfolio_path=portfolio)

    assert result["holdings"]["PLTR"]["weight_pct"] == 0.0
    assert result["holdings"]["PLTR"]["pillar_id"] == "ai-thesis"
