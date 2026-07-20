"""Tests for generate_reports.py report generator."""
import sys
import os
from pathlib import Path
import json

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "plugins/portfolio-advisor/scripts"))

from generate_reports import generate_report, load_target_holdings_from_db  # noqa: E402

sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))
from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.investment_repository import resolve_investment, update_investment_fields  # noqa: E402
from domain_model.pillar_repository import resolve_pillar, resolve_sub_strategy  # noqa: E402


def test_load_target_holdings_from_db(tmp_path):
    """Wave 2 rewire: target holdings must come from investment.target_weight
    et al. via the domain-model repository, not target-portfolio.json."""
    db_path = tmp_path / "domain_model.sqlite"
    conn = initialize_db(str(db_path))
    try:
        resolve_pillar(conn, "ai-compute", "AI Compute")
        resolve_sub_strategy(conn, "sa-asi-race", "ai-compute", "SA / ASI Race")
        goog_id = resolve_investment(conn, "GOOG", asset_class="EQUITY", name="Alphabet Inc.")
        update_investment_fields(
            conn, goog_id,
            pillar_id="ai-compute", sub_strategy_id="sa-asi-race",
            target_weight=4.9237, lifecycle_status="accumulate",
            thesis_for_inclusion="Hyperscaler with vertically integrated AI stack.",
        )
        # Watchlist-only row (no pillar_id) must be excluded.
        wl_id = resolve_investment(conn, "ZZZZ", asset_class="EQUITY")
        update_investment_fields(conn, wl_id, is_watchlisted=True)
    finally:
        conn.close()

    result = load_target_holdings_from_db(str(db_path))
    tickers = {h["ticker"] for h in result["holdings"]}
    assert tickers == {"GOOG"}
    goog = next(h for h in result["holdings"] if h["ticker"] == "GOOG")
    assert goog["subStrategyId"] == "sa-asi-race"
    assert goog["targetWeight"] == 4.9237
    assert goog["role"] == "accumulate"
    assert goog["name"] == "Alphabet Inc."


def test_load_target_holdings_from_db_missing_file_returns_empty(tmp_path):
    result = load_target_holdings_from_db(str(tmp_path / "does_not_exist.sqlite"))
    assert result == {}


def test_generate_report(tmp_path):
    # Create mock template
    template_content = "Value: {{PORTFOLIO_VALUE}} Macro: {{MACRO_REGIME}} Strategy: {{SUB_STRATEGY_SECTION}}"
    template_file = tmp_path / "test_report.md.template"
    template_file.write_text(template_content)

    # Mock daily brief JSON data
    brief_data = {
        "date": "2026-07-18",
        "total_equity": 28287.33,
        "macro_regime": {"regime": "RISK-ON", "score": 2},
        "conviction_scores": [
            {
                "ticker": "GOOG",
                "total": 1,
                "band": "HOLD",
                "target_weight": 4.9237,
                "actual_weight": 5.05,
                "dcf_action": "ACCUMULATE",
                "pct_to_fv": 49.8,
                "rsi": 35.3,
                "adx": 49.6,
                "vol_bias": 50.8,
                "flags": []
            }
        ],
        "recommendations": [
            {"ticker": "GOOG", "recommendation": "ACCUMULATE", "signal": "HOLD", "score": 1, "rationale": "Test rationale"}
        ]
    }

    # Mock target-portfolio JSON data
    target_portfolio_data = {
        "holdings": [
            {
                "ticker": "GOOG",
                "name": "Alphabet Inc.",
                "subStrategyId": "sa-asi-race",
                "targetWeight": 4.9237,
                "role": "accumulate"
            }
        ]
    }

    # Mock portfolio JSON data
    portfolio_data = {
        "holdings": [
            {
                "symbol": "GOOG",
                "shares": 4,
                "price": 345.75,
                "market_value": 1383.00
            }
        ],
        "totals": {
            "totalUSD": 28287.33
        }
    }

    # Run generation
    output = generate_report(
        brief_data=brief_data,
        target_portfolio_data=target_portfolio_data,
        portfolio_data=portfolio_data,
        template_path=str(template_file)
    )

    assert "28,287.33" in output
    assert "RISK-ON" in output
    assert "SA-ASI-RACE" in output
