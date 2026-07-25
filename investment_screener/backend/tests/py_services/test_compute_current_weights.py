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


def test_compute_current_from_db_reads_domain_model_sqlite_not_portfolio_json(tmp_path):
    """Wave 7: main()'s --mode current/both without an explicit --portfolio
    override must compute weights from domain_model.sqlite, not the real,
    frozen portfolio.json (Wave 3 stopped writing that file entirely)."""
    sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))
    from domain_model.db_client import initialize_db
    from domain_model.investment_repository import resolve_investment
    from domain_model.account_repository import upsert_account
    from domain_model.account_investment_repository import upsert_account_investment
    from domain_model.investment_price_repository import upsert_investment_price
    import validate_weights

    db_path = tmp_path / "test.sqlite"
    conn = initialize_db(str(db_path))
    now = "2026-07-25T00:00:00Z"
    upsert_account(conn, "TFSA", "TFSA", "TFSA")
    aapl_id = resolve_investment(conn, "AAPL", asset_class="EQUITY", currency="USD")
    msft_id = resolve_investment(conn, "MSFT", asset_class="EQUITY", currency="USD")
    upsert_account_investment(conn, "TFSA", aapl_id, quantity=10, average_cost=150, book_value=1500, currency="USD", last_synced_at=now)
    upsert_account_investment(conn, "TFSA", msft_id, quantity=5, average_cost=200, book_value=1000, currency="USD", last_synced_at=now)
    upsert_investment_price(conn, aapl_id, price=150, currency="USD", fetched_at=now)
    upsert_investment_price(conn, msft_id, price=200, currency="USD", fetched_at=now)
    conn.close()

    result = validate_weights.compute_current_from_db(db_path)

    assert abs(result["holdings"]["AAPL"] - (1500 / 2500 * 100)) < 0.0001
    assert abs(result["holdings"]["MSFT"] - (1000 / 2500 * 100)) < 0.0001
    assert result["total_value"] == 2500


def test_main_current_mode_without_portfolio_override_uses_db_not_real_file(tmp_path):
    """Regression guard: running `--mode current` with no --portfolio flag must
    not touch the real portfolio.json — it must read --db instead."""
    sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))
    from domain_model.db_client import initialize_db

    db_path = tmp_path / "empty.sqlite"
    initialize_db(str(db_path)).close()

    proc = subprocess.run(
        ["python3", str(SCRIPT_PATH), "--mode", "current", "--db", str(db_path)],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 0, proc.stderr
    result = json.loads(proc.stdout)["current"]
    # Empty db -> zero holdings, proving this did NOT fall back to reading a
    # real, populated portfolio.json off disk.
    assert result == {"total": 0.0, "holdings": {}, "total_value": 0.0}
