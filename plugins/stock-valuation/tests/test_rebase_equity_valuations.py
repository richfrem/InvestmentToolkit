"""Purpose: re-basing a saved earnings-multiple valuation for debt, without touching its assumptions.

Layer: Orchestration tests on a temporary SQLite database; no network (rate facts are passed in).
Key Functions: read both saved formats, raise the rate, shift weights, refuse what cannot be reproduced, persist.
Key Input Dependencies: rebase_equity_valuations.py, dcf_scenarios.run, persist_valuation, domain_model repositories.
"""
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))
sys.path.insert(0, str(REPO_ROOT / "plugins/stock-valuation/scripts"))

from dcf_scenarios import run  # noqa: E402
from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.projection_repository import get_latest_projection_by_source, get_projection_scenarios  # noqa: E402
from persist_valuation import persist_valuation  # noqa: E402
from rebase_equity_valuations import projection_payload, rebase, saved_inputs  # noqa: E402

SCENARIOS = {
    "bear": {"weight": 0.30, "growthRate": 18, "netMargin": 10, "exitPE": 16, "qualityMultiplier": 0.95, "shareChange": 2.5},
    "base": {"weight": 0.50, "growthRate": 36, "netMargin": 22, "exitPE": 26, "qualityMultiplier": 1.05, "shareChange": 1.5},
    "bull": {"weight": 0.20, "growthRate": 55, "netMargin": 28, "exitPE": 35, "qualityMultiplier": 1.15, "shareChange": 1.0},
}
REVENUE, SHARES, OLD_RATE = 5_131_000_000, 458_871_690, 0.0816
HEAVY_DEBT = {"totalDebt": 48e9, "cash": 3e9, "ebitda": 3.7e9, "currentRatio": 0.46}
NO_DEBT = {"totalDebt": 0, "cash": 1e9, "ebitda": 5e9, "currentRatio": 2.0}


def saved(tmp_path, rate=OLD_RATE, scenarios=SCENARIOS, valuation_model=None):
    """Persist a valuation the way the app does and read it back."""
    db = str(tmp_path / "domain_model.sqlite")
    result = run("CRWV", REVENUE, SHARES, scenarios, rate, 5, 81.23)
    projection = {"fair_value": result["weightedFairValue"], "action": "ACCUMULATE", "model": "legacy", "rationale": "Thesis.",
                  "current_price": 81.23, "discount_rate": rate, "horizon": 5, "base_revenue": REVENUE, "base_shares": SHARES,
                  "scenarios": {n: {**result["scenarios"][n], "price": result["scenarios"][n]["presentValue"]} for n in result["scenarios"]}}
    if valuation_model:
        projection["valuationModel"] = valuation_model
    persist_valuation({"symbol": "CRWV", "projection": projection}, db)
    conn = initialize_db(db)
    entry = get_latest_projection_by_source(conn, "CRWV", "AI_AGENT")
    rows = get_projection_scenarios(conn, entry["projection_id"])
    conn.close()
    return db, entry, rows, result


def test_reads_a_saved_valuation_back_into_calculator_inputs(tmp_path):
    _, entry, rows, _ = saved(tmp_path)
    inputs = saved_inputs(entry, rows)
    assert (inputs["revenue"], inputs["shares"], inputs["rate"], inputs["horizon"]) == (REVENUE, SHARES, OLD_RATE, 5)
    assert inputs["scenarios"]["base"]["exitPE"] == 26 and inputs["scenarios"]["bear"]["weight"] == 0.30


def test_reads_the_older_format_that_keeps_the_rate_as_a_percentage(tmp_path):
    _, entry, rows, _ = saved(tmp_path)
    legacy = {**entry, "snapshot_json": json.dumps({"price": 81.23, "shares": SHARES, "revenue": REVENUE}),
              "raw_json": json.dumps({"globalSettings": {"discountRate": 8.16, "timeHorizon": 5}})}
    inputs = saved_inputs(legacy, rows)
    assert (inputs["revenue"], inputs["shares"], round(inputs["rate"], 4)) == (REVENUE, SHARES, OLD_RATE)


def test_audited_and_firm_cash_flow_valuations_are_left_alone(tmp_path):
    _, entry, rows, _ = saved(tmp_path)
    audited = {**entry, "analytics_log_json": json.dumps({"valuationModel": {"discountRateAudit": {"selectedRate": 0.1275}}})}
    assert saved_inputs(audited, rows) is None
    assert saved_inputs({**entry, "model": "annual_fcff"}, rows) is None
    assert saved_inputs(entry, rows[:2]) is None   # a scenario is missing


def test_a_leveraged_company_gets_the_cost_of_equity_and_more_weight_on_the_bear_case(tmp_path):
    _, entry, rows, before = saved(tmp_path)
    outcome = rebase("CRWV", saved_inputs(entry, rows), 81.23, risk_free=0.0523, beta=2.557, erp=0.045, fundamentals=HEAVY_DEBT)
    assert outcome["status"] == "REBASED"
    assert outcome["boundedBeta"] == 2.0 and outcome["costOfEquity"] == 0.1423    # Blume 2.04, bounded to 2.0
    assert (outcome["old"]["rate"], outcome["new"]["rate"]) == (OLD_RATE, 0.1423)
    assert outcome["leverage"]["tier"] == "SEVERE"
    assert outcome["new"]["weights"] == {"bear": 0.40, "base": 0.50, "bull": 0.10}
    assert outcome["old"]["fairValue"] == before["weightedFairValue"]
    assert outcome["new"]["fairValue"] < 0.6 * outcome["old"]["fairValue"]
    assert outcome["rateBasis"]["status"] == "MISMATCH"


def test_the_rate_is_never_lowered_and_an_unleveraged_company_keeps_its_weights(tmp_path):
    _, entry, rows, _ = saved(tmp_path, rate=0.16)
    outcome = rebase("CRWV", saved_inputs(entry, rows), 81.23, 0.0523, 1.1, 0.045, NO_DEBT)
    assert outcome["status"] == "UNCHANGED" and outcome["new"]["rate"] == 0.16
    assert outcome["new"]["weights"] == outcome["old"]["weights"] and outcome["leverage"]["tier"] == "LOW"


def test_a_low_beta_stock_is_never_discounted_below_the_market_rate(tmp_path):
    _, entry, rows, _ = saved(tmp_path)
    assert rebase("CRWV", saved_inputs(entry, rows), 81.23, 0.05, 0.4, 0.045, NO_DEBT)["costOfEquity"] == 0.095


def test_an_older_valuation_the_calculator_cannot_reproduce_is_scaled_by_discount_factor(tmp_path):
    """Saved by an earlier engine: its prices are re-based by the change in discount factor, and marked."""
    _, entry, rows, _ = saved(tmp_path)
    exact = rebase("CRWV", saved_inputs(entry, rows), 81.23, 0.0523, 2.557, 0.045, HEAVY_DEBT)
    altered = [{**row, "scenario_price": round(row["scenario_price"] * 1.25, 2)} for row in rows]
    outcome = rebase("CRWV", saved_inputs(entry, altered), 81.23, 0.0523, 2.557, 0.045, HEAVY_DEBT)
    assert exact["reproduced"] is True and outcome["reproduced"] is False and outcome["status"] == "REBASED"
    factor = (1.0816 / 1.1423) ** 5
    for name, row in zip(("bear", "base", "bull"), sorted(altered, key=lambda r: ("bear", "base", "bull").index(r["scenario_name"]))):
        assert outcome["result"]["scenarios"][name]["presentValue"] == round(row["scenario_price"] * factor, 2)
    assert abs(outcome["new"]["fairValue"] / exact["new"]["fairValue"] - 1.25) < 0.002


def test_scaling_matches_a_full_recomputation_for_a_reproducible_valuation(tmp_path):
    _, entry, rows, _ = saved(tmp_path)
    outcome = rebase("CRWV", saved_inputs(entry, rows), 81.23, 0.0523, 2.557, 0.045, NO_DEBT)
    recomputed = run("CRWV", REVENUE, SHARES, SCENARIOS, outcome["new"]["rate"], 5, 81.23)
    assert abs(outcome["new"]["fairValue"] - recomputed["weightedFairValue"]) < 0.05
    assert outcome["result"]["action"] == recomputed["action"]


def test_writing_adds_a_version_that_records_what_changed_and_keeps_the_old_one(tmp_path):
    db, entry, rows, _ = saved(tmp_path)
    inputs = saved_inputs(entry, rows)
    outcome = rebase("CRWV", inputs, 81.23, 0.0523, 2.557, 0.045, HEAVY_DEBT)
    persist_valuation(projection_payload("CRWV", entry, inputs, outcome, "2026-10-08"), db)
    conn = initialize_db(db)
    latest = get_latest_projection_by_source(conn, "CRWV", "AI_AGENT")
    new_rows = {row["scenario_name"]: row for row in get_projection_scenarios(conn, latest["projection_id"])}
    versions = conn.execute("SELECT COUNT(*) FROM projection_version;").fetchone()[0]
    conn.close()
    model = json.loads(latest["analytics_log_json"])["valuationModel"]
    assert (versions, latest["version"], latest["fair_value"]) == (2, entry["version"] + 1, outcome["new"]["fairValue"])
    assert model["leverage"]["tier"] == "SEVERE" and model["rateBasis"]["status"] == "OK"
    assert model["rateBasis"]["rateType"] == "COST_OF_EQUITY" and "not a sourced rate audit" in model["rateBasis"]["basis"]
    assert model["rebasedFrom"] == {"version": entry["version"], "discountRate": OLD_RATE, "asOf": "2026-10-08",
                                    "weights": {"bear": 0.30, "base": 0.50, "bull": 0.20}, "fairValue": outcome["old"]["fairValue"]}
    assert new_rows["bear"]["weight"] == 0.40 and new_rows["base"]["exit_pe"] == 26
    assert "Re-based 2026-10-08" in latest["rationale"] and json.loads(latest["snapshot_json"])["discountRate"] == 0.1423
    assert saved_inputs(latest, list(new_rows.values())) is not None   # can be re-based again later


def test_running_it_again_does_not_shift_the_weights_a_second_time(tmp_path):
    db, entry, rows, _ = saved(tmp_path)
    inputs = saved_inputs(entry, rows)
    first = rebase("CRWV", inputs, 81.23, 0.0523, 2.557, 0.045, HEAVY_DEBT)
    persist_valuation(projection_payload("CRWV", entry, inputs, first, "2026-10-08"), db)
    conn = initialize_db(db)
    latest = get_latest_projection_by_source(conn, "CRWV", "AI_AGENT")
    again = rebase("CRWV", saved_inputs(latest, get_projection_scenarios(conn, latest["projection_id"])),
                   81.23, 0.0523, 2.557, 0.045, HEAVY_DEBT)
    conn.close()
    assert again["status"] == "UNCHANGED" and again["new"]["weights"] == {"bear": 0.40, "base": 0.50, "bull": 0.10}
    assert again["new"]["fairValue"] == first["new"]["fairValue"]
