"""
Tests standardize_metrics.py's net_income/profit_margin derivation.

fetch_financials.py does not always include a raw "net_income" key (e.g. PLTR) —
some tickers only provide "profit_margin" and "pe_ratio" in metrics. The script
must derive net_income from profit_margin x revenue in that case, instead of
silently defaulting to 0 and reporting a profitable company as 0% margin.
"""

import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_PATH = REPO_ROOT / "plugins/stock-valuation/skills/stock_valuation/scripts/standardize_metrics.py"


def _run_standardize(raw_data: dict) -> dict:
    proc = subprocess.run(
        ["python3", str(SCRIPT_PATH), "-"],
        input=json.dumps(raw_data), text=True, capture_output=True, cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def test_derives_net_income_from_profit_margin_when_net_income_missing():
    """PLTR-shaped raw data: no 'net_income' key, but 'profit_margin' and 'pe_ratio' present."""
    raw_data = {
        "symbol": "PLTR",
        "metrics": {
            "price": 130.96,
            "revenue": 4475446000.0,
            "market_cap": 313952010240.0,
            "shares_diluted": 2296071334.0,
            "pe_ratio": 147.14607,
            "profit_margin": 43.67,
            "currency": "USD",
        },
    }

    result = _run_standardize(raw_data)

    assert result["ratios"]["profit_margin"] > 0, "profit_margin must not default to 0 when raw data has it"
    assert result["snapshot"]["net_income"] > 0, "net_income must be derived, not defaulted to 0"

    expected_net_income = 4475446000.0 * 0.4367
    assert abs(result["snapshot"]["net_income"] - expected_net_income) / expected_net_income < 0.01
