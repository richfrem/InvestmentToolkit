"""
Purpose: test canonical valuation persistence and audited rate consistency.
Layer: CLI integration. Key Input Dependencies: real persistence scripts and SQLite repositories.
Key Functions: audited_payload; rate-audit round trip and conflict tests;
    cash-flow audit preservation and persistence happy-path tests.
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
from domain_model.projection_repository import get_latest_projection


def audited_payload(tmp_path):
    """Produce a real calculator artifact and matching synthetic projection."""
    inputs = {"method": "terminal_earnings", "asOf": "2026-10-07", "currency": "USD",
              "riskFreeRate": 0.04, "beta": 1, "erp": 0.06, "marketCap": 800,
              "totalDebt": 200, "costOfDebtPreTax": 0.05, "taxShieldRate": 0,
              "rationale": "Synthetic fixture rationale",
              "sources": [{"date": "2026-10-07", "url": "https://example.org/fixture", "use": "Synthetic inputs"}]}
    input_file = tmp_path / "rate_inputs.json"
    input_file.write_text(json.dumps(inputs))
    calculator = subprocess.run([sys.executable, str(PERSIST_SCRIPT.with_name("wacc.py")),
                                 "--inputs", str(input_file)], capture_output=True, text=True)
    assert calculator.returncode == 0, calculator.stderr
    audit = json.loads(calculator.stdout)
    audit_file = tmp_path / "rate_audit.json"
    audit_file.write_text(json.dumps(audit))
    payload = {"symbol": "AUDIT", "projection": {
        "fair_value": 30, "current_price": 30, "discount_rate": 0.10,
        "researchReport": "AUDIT_2026-10-07.md",
        "valuationModel": {"method": "terminal_earnings", "existingField": "retained"},
        "scenarios": {"base": {"weight": 1, "price": 30}}}}
    return payload, audit, audit_file


def test_rate_audit_cli_round_trip(tmp_path):
    """Python calculator -> persistence CLI -> actual SQLite repository retains evidence."""
    payload, audit, audit_file = audited_payload(tmp_path)
    db_path = str(tmp_path / "audit.sqlite")
    result = subprocess.run([sys.executable, str(PERSIST_SCRIPT), "--payload", json.dumps(payload),
                             "--rate-audit", str(audit_file), "--db", db_path, "--json"],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    conn = initialize_db(db_path)
    row = get_latest_projection(conn, "AUDIT")
    saved = json.loads(row["analytics_log_json"])["valuationModel"]
    assert saved["discountRateAudit"] == audit
    assert saved["existingField"] == "retained"
    assert json.loads(row["snapshot_json"])["discountRate"] == 0.10
    assert json.loads(row["snapshot_json"])["researchReport"] == "AUDIT_2026-10-07.md"
    conn.close()


def test_rate_audit_rejects_inconsistent_write_before_opening_database(tmp_path):
    """Mismatched rate, method or tampered arithmetic cannot create a valuation version."""
    payload, audit, audit_file = audited_payload(tmp_path)
    cases = [("discount_rate", 0.1277), ("method", "annual_fcff"), ("tamper", 0.1277),
             ("nested_rate", 0.1277), ("scenario_method", "annual_fcff"),
             ("model_label", "annual_fcff")]
    for field, value in cases:
        invalid = json.loads(json.dumps(payload))
        invalid_audit = dict(audit)
        if field == "method":
            invalid["projection"]["valuationModel"]["method"] = value
        elif field == "nested_rate":
            invalid["projection"]["valuationModel"]["discountRate"] = value
        elif field == "scenario_method":
            invalid["projection"]["scenarios"]["base"]["method"] = value
        elif field == "model_label":
            invalid["projection"]["model"] = value
        elif field == "tamper":
            invalid_audit["selectedRate"] = value
        else:
            invalid["projection"][field] = value
        audit_file.write_text(json.dumps(invalid_audit))
        db_path = tmp_path / f"invalid-{field}.sqlite"
        result = subprocess.run([sys.executable, str(PERSIST_SCRIPT), "--payload", json.dumps(invalid),
                                 "--rate-audit", str(audit_file), "--db", str(db_path)],
                                capture_output=True, text=True)
        assert result.returncode != 0, field
        assert not db_path.exists(), field


def test_preserve_cash_flow_audit_and_standing_decision(tmp_path):
    """Persist computed FCFF evidence, zero upside and scenario metadata intact."""
    db_path = str(tmp_path / "domain_model.sqlite")
    conn = initialize_db(db_path)
    resolve_investment(conn, "MU", name="Micron")
    conn.execute("UPDATE investment SET standing_decision_type = 'MAINTAIN_TRIM_EXTREME', target_weight = 3 WHERE symbol = 'MU'")
    conn.commit()
    model = {"method": "annual_fcff", "annualForecast": [{"freeCashFlow": 12}], "terminalGrowth": 0.03}
    payload = {"symbol": "MU", "projection": {
        "weightedFairValue": 100, "currentPrice": 100, "upsidePct": 0,
        "discountRate": 0.12, "action": "HOLD", "valuationModel": model,
        "scenarios": {"base": {"weight": 1, "presentValue": 100,
                               "qualityMultiplier": 1, "shareChange": 0,
                               "rationale": "Forward cash flow", "risks": ["Capex"]}}}}
    result = subprocess.run([sys.executable, str(PERSIST_SCRIPT), "--payload", json.dumps(payload),
                             "--db", db_path, "--json"], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    row = conn.execute("SELECT snapshot_json, analytics_log_json FROM projection_version WHERE investment_id='MU'").fetchone()
    assert json.loads(row[0])["discountRate"] == 0.12
    assert json.loads(row[0])["upsidePct"] == 0
    assert json.loads(row[1])["valuationModel"] == model
    scenario = conn.execute("SELECT scenario_price, rationale, risks_json FROM projection_scenario").fetchone()
    assert tuple(scenario) == (100, "Forward cash flow", '["Capex"]')
    standing = conn.execute("SELECT standing_decision_type, target_weight FROM investment WHERE symbol='MU'").fetchone()
    assert tuple(standing) == ("MAINTAIN_TRIM_EXTREME", 3)
    conn.close()


def test_persist_valuation_happy_path(tmp_path):
    """Save all scenario and price-level fields and increment versions safely."""
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
