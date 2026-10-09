"""Tests validate_weights.py::compute_current_from_db()'s weight denominator.

Purpose:
    Current weight % is shares x price / total, with the total from the database (broker
    total when present, else equities plus cash), and it must match the canonical TypeScript
    computeWeightsMap() for the same inputs.

Key Input Dependencies: none (each test builds a real temporary SQLite database).
"""

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_PATH = REPO_ROOT / "plugins/portfolio-advisor/scripts/validate_weights.py"

sys.path.insert(0, str(SCRIPT_PATH.parent))
sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))
from domain_model.account_investment_repository import upsert_account_investment  # noqa: E402
from domain_model.account_repository import upsert_account  # noqa: E402
from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.investment_price_repository import upsert_investment_price  # noqa: E402
from domain_model.investment_repository import resolve_investment  # noqa: E402
import validate_weights  # noqa: E402


def _seed(tmp_path: Path, positions: dict) -> Path:
    """A database holding {symbol: (shares, price)} in one account."""
    db_path = tmp_path / "test.sqlite"
    conn = initialize_db(str(db_path))
    now = "2026-07-25T00:00:00Z"
    upsert_account(conn, "TFSA", "TFSA", "TFSA")
    for symbol, (qty, price) in positions.items():
        investment_id = resolve_investment(conn, symbol, asset_class="EQUITY", currency="USD")
        upsert_account_investment(conn, "TFSA", investment_id, quantity=qty, average_cost=price,
                                  book_value=qty * price, currency="USD", last_synced_at=now)
        upsert_investment_price(conn, investment_id, price=price, currency="USD", fetched_at=now)
    conn.close()
    return db_path


def test_weights_are_market_value_over_database_total(tmp_path):
    """AAPL 1500 and MSFT 1000 of a 2500 total weigh 60% and 40%."""
    result = validate_weights.compute_current_from_db(_seed(tmp_path, {"AAPL": (10, 150.0), "MSFT": (5, 200.0)}))
    assert abs(result["holdings"]["AAPL"] - 60.0) < 0.0001
    assert abs(result["holdings"]["MSFT"] - 40.0) < 0.0001
    assert result["total_value"] == 2500


def test_empty_database_gives_zero_not_a_file_fallback(tmp_path):
    """An empty database reports zero holdings; nothing else is consulted."""
    db_path = tmp_path / "empty.sqlite"
    initialize_db(str(db_path)).close()
    assert validate_weights.compute_current_from_db(db_path) == {"total": 0.0, "holdings": {}, "total_value": 0.0}


def test_main_current_mode_reads_the_requested_database(tmp_path):
    """`--mode current --db X` computes from X."""
    db_path = _seed(tmp_path, {"AAPL": (10, 150.0)})
    proc = subprocess.run(["python3", str(SCRIPT_PATH), "--mode", "current", "--db", str(db_path)],
                          capture_output=True, text=True, cwd=str(REPO_ROOT))
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout)["current"]["holdings"]["AAPL"] == 100.0


def test_parity_with_typescript_compute_weights_map(tmp_path):
    """Python and TS computeWeightsMap() give the same weights for the same holdings and total."""
    positions = {"AAPL": (10, 150.0), "MSFT": (5, 200.0), "NVDA": (3, 900.0)}
    py = validate_weights.compute_current_from_db(_seed(tmp_path, positions))
    holdings = [{"symbol": s, "shares": q, "price": p} for s, (q, p) in positions.items()]
    totals = {"holdingsUSD": 0, "cashUSD": 0, "totalUSD": py["total_value"], "totalCAD": 0,
              "exchangeRate": 1.38, "timestamp": "2026-07-02T00:00:00Z", "totalSource": "tv_authoritative"}
    ts_script = f"""
    import {{ computeWeightsMap }} from '{REPO_ROOT}/investment_screener/backend/src/utils/portfolioSnapshot';
    console.log(JSON.stringify(computeWeightsMap({json.dumps(holdings)}, {json.dumps(totals)} as any)));
    """
    ts_proc = subprocess.run(["npx", "tsx", "-e", ts_script], capture_output=True, text=True,
                             cwd=str(REPO_ROOT / "investment_screener/backend"))
    assert ts_proc.returncode == 0, ts_proc.stderr
    ts_result = json.loads(ts_proc.stdout.strip().splitlines()[-1])
    for ticker in positions:
        assert abs(py["holdings"][ticker] - ts_result[ticker]) < 0.01, f"{ticker}: py={py['holdings'][ticker]} ts={ts_result[ticker]}"
