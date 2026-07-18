"""Tests for generate_reports.py report generator."""
import sys
import os
from pathlib import Path
import json

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "plugins/portfolio-advisor/scripts"))

from generate_reports import generate_report  # noqa: E402


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
