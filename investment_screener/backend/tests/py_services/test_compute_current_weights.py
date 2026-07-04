"""
Tests validate_weights.py::compute_current()'s weight denominator.

Split-brain audit (2026-07-02) found 5 independent "actual weight %" implementations
across Python and TypeScript. compute_current() always recomputed its own
sum(shares*price) as the denominator, ignoring portfolio.json's persisted
totals.totalUSD (which is TV-broker-authoritative when available — see
portfolioSnapshot.ts::buildPortfolioSnapshot/preserveAuthoritativeTotal). Must use the
same formula the canonical TS computeWeightsMap() uses: prefer totals.totalUSD when
present and > 0, only fall back to sum(shares*price) when it's absent or zero.
"""

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_PATH = REPO_ROOT / "plugins/portfolio-advisor/scripts/validate_weights.py"

sys.path.insert(0, str(SCRIPT_PATH.parent))


def _run_compute_current(portfolio_path: Path) -> dict:
    proc = subprocess.run(
        ["python3", str(SCRIPT_PATH), "--mode", "current", "--portfolio", str(portfolio_path)],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)["current"]


def test_uses_persisted_total_usd_over_recomputed_sum(tmp_path):
    """totals.totalUSD (e.g. 50000, TV-authoritative) must be the denominator, not the
    holdings' own shares*price sum (3300 here)."""
    portfolio_data = {
        "holdings": [
            {"symbol": "AAPL", "shares": 10, "price": 150.0},
            {"symbol": "MSFT", "shares": 5, "price": 200.0},
        ],
        "totals": {"totalUSD": 50000, "totalSource": "tv_authoritative"},
    }
    portfolio_file = tmp_path / "portfolio.json"
    portfolio_file.write_text(json.dumps(portfolio_data))

    result = _run_compute_current(portfolio_file)

    assert abs(result["holdings"]["AAPL"] - (1500 / 50000 * 100)) < 0.0001
    assert abs(result["holdings"]["MSFT"] - (1000 / 50000 * 100)) < 0.0001
    assert result["total_value"] == 50000


def test_falls_back_to_recomputed_sum_when_totals_missing(tmp_path):
    portfolio_data = {
        "holdings": [
            {"symbol": "AAPL", "shares": 10, "price": 150.0},
            {"symbol": "MSFT", "shares": 5, "price": 200.0},
        ]
    }
    portfolio_file = tmp_path / "portfolio.json"
    portfolio_file.write_text(json.dumps(portfolio_data))

    result = _run_compute_current(portfolio_file)

    assert abs(result["holdings"]["AAPL"] - (1500 / 2500 * 100)) < 0.0001
    assert abs(result["holdings"]["MSFT"] - (1000 / 2500 * 100)) < 0.0001


def test_falls_back_to_recomputed_sum_when_total_usd_is_zero(tmp_path):
    portfolio_data = {
        "holdings": [{"symbol": "AAPL", "shares": 10, "price": 150.0}],
        "totals": {"totalUSD": 0},
    }
    portfolio_file = tmp_path / "portfolio.json"
    portfolio_file.write_text(json.dumps(portfolio_data))

    result = _run_compute_current(portfolio_file)

    assert result["holdings"]["AAPL"] == 100.0


def test_parity_with_typescript_compute_weights_map(tmp_path):
    """Cross-language parity: Python compute_current() and TS computeWeightsMap()
    must produce identical weight percentages for the same fixture — mirrors the
    existing test_math_parity.py pattern for DCF math."""
    holdings = [
        {"symbol": "AAPL", "shares": 10, "price": 150.0},
        {"symbol": "MSFT", "shares": 5, "price": 200.0},
        {"symbol": "NVDA", "shares": 3, "price": 900.0},
    ]
    totals = {
        "holdingsUSD": 0, "cashUSD": 0, "totalUSD": 50000, "totalCAD": 69000,
        "exchangeRate": 1.38, "timestamp": "2026-07-02T00:00:00Z", "totalSource": "tv_authoritative",
    }

    portfolio_file = tmp_path / "portfolio.json"
    portfolio_file.write_text(json.dumps({"holdings": holdings, "totals": totals}))
    py_result = _run_compute_current(portfolio_file)["holdings"]

    ts_script = f"""
    import {{ computeWeightsMap }} from '{REPO_ROOT}/investment_screener/backend/src/utils/portfolioSnapshot';
    const holdings = {json.dumps(holdings)};
    const totals = {json.dumps(totals)};
    console.log(JSON.stringify(computeWeightsMap(holdings, totals as any)));
    """
    ts_proc = subprocess.run(
        ["npx", "tsx", "-e", ts_script],
        capture_output=True, text=True,
        cwd=str(REPO_ROOT / "investment_screener/backend"),
    )
    assert ts_proc.returncode == 0, ts_proc.stderr
    ts_result = json.loads(ts_proc.stdout.strip().splitlines()[-1])

    for ticker in ("AAPL", "MSFT", "NVDA"):
        assert abs(py_result[ticker] - ts_result[ticker]) < 0.01, (
            f"{ticker}: python={py_result[ticker]} ts={ts_result[ticker]}"
        )
