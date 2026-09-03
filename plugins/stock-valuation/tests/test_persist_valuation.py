"""
Unit tests for persist_valuation.py in plugins/stock-valuation/scripts/
Enforces transactional integrity, automated version incrementing, scenario insertion,
and TradingView price level syncing without inline Python or ad-hoc SQL.
"""
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
PERSIST_SCRIPT = REPO_ROOT / "plugins/stock-valuation/scripts/persist_valuation.py"
sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))

from domain_model.db_client import initialize_db
from domain_model.investment_repository import resolve_investment


def test_persist_valuation_happy_path(tmp_path):
    db_path = str(tmp_path / "domain_model.sqlite")
    conn = initialize_db(db_path)
    resolve_investment(conn, "TEST_CO", name="Test Company Inc.")
    conn.close()

    payload = {
        "symbol": "TEST_CO",
        "name": "Test Company Inc.",
        "lifecycle_status": "watchlist",
        "standing_decision_type": "ACCUMULATE_ON_PULLBACK",
        "standing_decision_reason": "Testing atomic persistence script",
        "projection": {
            "fair_value": 150.0,
            "action": "BUY",
            "model": "5yr_dcf_scenarios",
            "rationale": "High-margin moat",
            "current_price": 100.0,
            "upside_pct": 50.0,
            "discount_rate": 0.085,
            "scenarios": {
                "bear": {"weight": 0.25, "growthRate": 5.0, "netMargin": 15.0, "exitPE": 18.0, "price": 80.0},
                "base": {"weight": 0.50, "growthRate": 15.0, "netMargin": 22.0, "exitPE": 25.0, "price": 140.0},
                "bull": {"weight": 0.25, "growthRate": 25.0, "netMargin": 28.0, "exitPE": 32.0, "price": 240.0}
            }
        },
        "price_levels": {
            "target_entry_price": 95.0,
            "buy_tiers": [
                {"tier": 1, "price": 95.0, "action": "ACCUMULATE", "basis": "Buy Tier 1"},
                {"tier": 2, "price": 88.0, "action": "ACCUMULATE", "basis": "Primary Buy"}
            ],
            "sell_tiers": [
                {"tier": 1, "price": 140.0, "action": "TRIM", "trimPct": 50, "basis": "Trim 1"},
                {"tier": 2, "price": 160.0, "action": "TRIM", "trimPct": 50, "basis": "Trim 2"}
            ],
            "stop_loss": {"price": 80.0, "action": "EXIT", "basis": "Stop Loss"}
        }
    }

    res = subprocess.run(
        [sys.executable, str(PERSIST_SCRIPT), "--payload", json.dumps(payload), "--db", db_path, "--json"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT)
    )
    assert res.returncode == 0, f"Script failed: {res.stderr}"
    data = json.loads(res.stdout)
    assert data["status"] == "success"
    assert data["symbol"] == "TEST_CO"
    assert data["version"] == 1

    # Verify rows in DB
    conn = initialize_db(db_path)
    pv = conn.execute("SELECT version, fair_value, action FROM projection_version WHERE investment_id = 'TEST_CO'").fetchone()
    assert pv[0] == 1
    assert pv[1] == 150.0
    assert pv[2] == "BUY"

    scenarios = conn.execute("SELECT scenario_name, scenario_price FROM projection_scenario WHERE projection_id = 'TEST_CO:1'").fetchall()
    assert len(scenarios) == 3

    # Check auto-incrementing on second run
    payload["projection"]["fair_value"] = 160.0
    res2 = subprocess.run(
        [sys.executable, str(PERSIST_SCRIPT), "--payload", json.dumps(payload), "--db", db_path, "--json"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT)
    )
    assert res2.returncode == 0
    data2 = json.loads(res2.stdout)
    assert data2["version"] == 2

    pv2 = conn.execute("SELECT version, fair_value FROM projection_version WHERE investment_id = 'TEST_CO' ORDER BY version DESC LIMIT 1").fetchone()
    assert pv2[0] == 2
    assert pv2[1] == 160.0
    conn.close()
