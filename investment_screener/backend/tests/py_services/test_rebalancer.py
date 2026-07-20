"""Tests for rebalancer.py — E2 rebalancer v2 (Phase 3, sub-spec 4)."""
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from rebalancer import DEFAULT_BAND_CONFIG, compute_bands  # noqa: E402
from rebalancer import (  # noqa: E402
    get_latest_valuation_action,
    compute_candidate_orders,
)
from rebalancer import load_account_positions  # noqa: E402
from rebalancer import compute_account_routing  # noqa: E402
from rebalancer import compute_capital_gains_estimate  # noqa: E402
from rebalancer import compute_risk_budget_check  # noqa: E402
from rebalancer import compute_breaker_warnings  # noqa: E402
from rebalancer import compute_rebalance_plan  # noqa: E402


def test_compute_bands_in_band_when_drift_within_band():
    # target 5.5%, band = max(5.5*0.20, 1.5) = 1.5pp; current 4.5% -> drift -1.0pp, in band
    bands = compute_bands({"NBIS": 4.5}, {"NBIS": 5.5}, DEFAULT_BAND_CONFIG)
    assert bands["NBIS"]["inBand"] is True
    assert bands["NBIS"]["bandPct"] == pytest.approx(1.5)
    assert bands["NBIS"]["driftPct"] == pytest.approx(-1.0)


def test_compute_bands_out_of_band_when_drift_exceeds_band():
    # target 5.5%, band 1.5pp; current 2.1% -> drift -3.4pp, out of band
    bands = compute_bands({"NBIS": 2.1}, {"NBIS": 5.5}, DEFAULT_BAND_CONFIG)
    assert bands["NBIS"]["inBand"] is False


def test_compute_bands_relative_band_dominates_for_large_targets():
    # target 20% -> relative band = 20*0.20 = 4.0pp > 1.5pp absolute floor
    bands = compute_bands({"BIG": 16.5}, {"BIG": 20.0}, DEFAULT_BAND_CONFIG)
    assert bands["BIG"]["bandPct"] == pytest.approx(4.0)
    assert bands["BIG"]["inBand"] is True  # drift -3.5pp within 4.0pp band


def test_compute_bands_boundary_drift_equal_to_band_is_in_band():
    bands = compute_bands({"X": 4.0}, {"X": 5.5}, DEFAULT_BAND_CONFIG)  # drift exactly -1.5pp
    assert bands["X"]["inBand"] is True


def test_compute_bands_ticker_missing_from_one_side_defaults_to_zero():
    bands = compute_bands({"ORPHAN": 2.0}, {}, DEFAULT_BAND_CONFIG)
    assert bands["ORPHAN"]["targetWeight"] == 0.0
    assert bands["ORPHAN"]["bandPct"] == pytest.approx(1.5)  # absolute floor, target*rel=0


def _domain_db(tmp_path) -> Path:
    """Path to this tmp_path's (not-yet-created) domain_model.sqlite fixture DB."""
    return tmp_path / "domain_model.sqlite"


def _write_projection(tmp_path: Path, ticker: str, action: str) -> Path:
    """Insert a single AI_AGENT-sourced projection_version row for `ticker`.

    Wave 1 Task 7A: replaces the old `projections/{TICKER}.json` fixture writer —
    `get_latest_valuation_action`/`_has_any_projection` now read the domain model
    SQLite DB, never the flat-file JSON. Returns the DB path so callers can pass it
    straight through as `db_path`.
    """
    from domain_model.db_client import initialize_db  # noqa: PLC0415
    from domain_model.investment_repository import resolve_investment  # noqa: PLC0415
    from domain_model.projection_repository import save_projection_version  # noqa: PLC0415

    db_path = _domain_db(tmp_path)
    conn = initialize_db(str(db_path))
    investment_id = resolve_investment(conn, ticker)
    save_projection_version(
        conn, investment_id, version=1, saved_at="2026-07-01T00:00:00Z",
        action=action, source="AI_AGENT",
    )
    conn.close()
    return db_path


def test_get_latest_valuation_action_reads_latest_ai_agent_entry(tmp_path):
    db_path = _write_projection(tmp_path, "NBIS", "ACCUMULATE")
    assert get_latest_valuation_action("NBIS", db_path) == "ACCUMULATE"


def test_get_latest_valuation_action_missing_file_returns_none(tmp_path):
    assert get_latest_valuation_action("NOPE", _domain_db(tmp_path)) is None


def test_candidate_orders_sell_when_overweight(tmp_path):
    bands = {"CRWD": {"currentWeight": 7.8, "targetWeight": 4.0, "bandPct": 1.5, "driftPct": 3.8, "inBand": False}}
    target_data = {"holdings": [{"ticker": "CRWD", "targetWeight": 4.0}]}
    candidates, skipped = compute_candidate_orders(bands, target_data, {"CRWD": 100.0}, 10000.0, _domain_db(tmp_path))
    assert skipped == []
    assert candidates[0]["ticker"] == "CRWD"
    assert candidates[0]["action"] == "sell"
    assert candidates[0]["shares"] == math.floor(0.038 * 10000.0 / 100.0)


def test_candidate_orders_buy_when_underweight_and_clean(tmp_path):
    db_path = _write_projection(tmp_path, "NBIS", "ACCUMULATE")
    bands = {"NBIS": {"currentWeight": 2.1, "targetWeight": 5.5, "bandPct": 1.5, "driftPct": -3.4, "inBand": False}}
    target_data = {"holdings": [{"ticker": "NBIS", "targetWeight": 5.5}]}
    candidates, skipped = compute_candidate_orders(bands, target_data, {"NBIS": 20.0}, 10000.0, db_path)
    assert skipped == []
    assert candidates[0]["action"] == "buy"


def test_candidate_orders_skips_exit_rated_underweight(tmp_path):
    db_path = _write_projection(tmp_path, "INTC", "EXIT")
    bands = {"INTC": {"currentWeight": 1.0, "targetWeight": 4.0, "bandPct": 1.5, "driftPct": -3.0, "inBand": False}}
    target_data = {"holdings": [{"ticker": "INTC", "targetWeight": 4.0}]}
    candidates, skipped = compute_candidate_orders(bands, target_data, {"INTC": 30.0}, 10000.0, db_path)
    assert candidates == []
    assert skipped[0]["ticker"] == "INTC"
    assert "EXIT" in skipped[0]["reason"]


def test_candidate_orders_skips_above_target_entry_price(tmp_path):
    bands = {"SNDK": {"currentWeight": 4.2, "targetWeight": 6.0, "bandPct": 1.5, "driftPct": -1.8, "inBand": False}}
    target_data = {"holdings": [{"ticker": "SNDK", "targetWeight": 6.0, "targetEntryPrice": 1350.0}]}
    candidates, skipped = compute_candidate_orders(bands, target_data, {"SNDK": 1741.0}, 10000.0, _domain_db(tmp_path))
    assert candidates == []
    assert "targetEntryPrice" in skipped[0]["reason"]


def test_candidate_orders_skips_when_standing_decision_conflicts(tmp_path):
    bands = {"VST": {"currentWeight": 1.0, "targetWeight": 2.27, "bandPct": 1.5, "driftPct": -1.27, "inBand": False}}
    target_data = {"holdings": [{
        "ticker": "VST", "targetWeight": 2.27,
        "standingDecision": {"type": "SA_LP_EXIT_OVERRIDE", "reason": "DO NOT ADD"},
    }]}
    candidates, skipped = compute_candidate_orders(bands, target_data, {"VST": 50.0}, 10000.0, _domain_db(tmp_path))
    assert candidates == []
    assert "Standing decision" in skipped[0]["reason"]


def test_candidate_orders_skips_zero_share_orders(tmp_path):
    # Tiny drift dollar amount rounds down to 0 shares — must not emit a phantom order.
    bands = {"TINY": {"currentWeight": 0.01, "targetWeight": 1.5, "bandPct": 1.5, "driftPct": -1.49, "inBand": False}}
    target_data = {"holdings": [{"ticker": "TINY", "targetWeight": 1.5}]}
    candidates, skipped = compute_candidate_orders(bands, target_data, {"TINY": 5000.0}, 100.0, _domain_db(tmp_path))
    assert candidates == []


def _write_portfolio_with_tvsnapshot(path: Path, accounts: list[dict]) -> None:
    path.write_text(json.dumps({
        "holdings": [], "totals": {"totalUSD": 1000.0},
        "tvSnapshot": {"snapshots": accounts},
    }))


def test_load_account_positions_reads_tvsnapshot_per_account(tmp_path):
    portfolio_path = tmp_path / "portfolio.json"
    _write_portfolio_with_tvsnapshot(portfolio_path, [
        {
            "accountType": "TFSA",
            "positions": [{"symbol": "NBIS", "quantity": 10, "avgFillPrice": 20.0}],
            "balances": {"cashUSDCombined": 500.0},
        },
        {
            "accountType": "RRSP",
            "positions": [{"symbol": "NBIS", "quantity": 3, "avgFillPrice": 22.0}],
            "balances": {"cashUSDCombined": 100.0},
        },
    ])
    positions, cash, source = load_account_positions(portfolio_path)
    assert positions["TFSA"]["NBIS"] == {"shares": 10.0, "costBasis": 20.0}
    assert positions["RRSP"]["NBIS"] == {"shares": 3.0, "costBasis": 22.0}
    assert cash["TFSA"] == 500.0
    assert cash["RRSP"] == 100.0
    assert source == {"TFSA": "tvSnapshot", "RRSP": "tvSnapshot"}


def test_load_account_positions_falls_back_to_heuristic_when_rrsp_missing(tmp_path):
    portfolio_path = tmp_path / "portfolio.json"
    _write_portfolio_with_tvsnapshot(portfolio_path, [
        {
            "accountType": "TFSA",
            "positions": [{"symbol": "NBIS", "quantity": 9, "avgFillPrice": 20.0}],
            "balances": {"cashUSDCombined": 500.0},
        },
    ])
    positions, cash, source = load_account_positions(portfolio_path)
    assert positions["RRSP"]["NBIS"]["shares"] == 3.0  # floor(9/3)
    assert cash["RRSP"] == 0.0
    assert source["RRSP"] == "heuristic_1_3_mirror"


def test_load_account_positions_no_tvsnapshot_returns_empty(tmp_path):
    portfolio_path = tmp_path / "portfolio.json"
    portfolio_path.write_text(json.dumps({"holdings": [], "totals": {"totalUSD": 1000.0}}))
    positions, cash, source = load_account_positions(portfolio_path)
    assert positions == {}
    assert cash == {}
    assert source == {}


def test_routing_sells_go_to_the_account_that_holds_shares():
    candidates = [{"ticker": "CRWD", "action": "sell", "shares": 10, "currentWeight": 7.0, "targetWeight": 4.0}]
    positions = {"TFSA": {"CRWD": {"shares": 15.0, "costBasis": 100.0}}}
    cash = {"TFSA": 0.0}
    policy = {"accountPreferenceRules": [{"match": "default", "prefer": "TFSA"}], "psuFundingRule": {"ticker": "PSU-U.TO"}}
    routed = compute_account_routing(candidates, positions, cash, policy, {"holdings": []}, {"CRWD": 100.0})
    assert routed[0]["account"] == "TFSA"
    assert routed[0]["shares"] == 10


def test_routing_splits_sell_proportionally_across_two_accounts():
    candidates = [{"ticker": "CRWD", "action": "sell", "shares": 12, "currentWeight": 7.0, "targetWeight": 4.0}]
    positions = {
        "TFSA": {"CRWD": {"shares": 9.0, "costBasis": 100.0}},
        "RRSP": {"CRWD": {"shares": 3.0, "costBasis": 100.0}},
    }
    cash = {"TFSA": 0.0, "RRSP": 0.0}
    policy = {"accountPreferenceRules": [{"match": "default", "prefer": "TFSA"}], "psuFundingRule": {"ticker": "PSU-U.TO"}}
    routed = compute_account_routing(candidates, positions, cash, policy, {"holdings": []}, {"CRWD": 100.0})
    tfsa_order = next(o for o in routed if o["account"] == "TFSA")
    rrsp_order = next(o for o in routed if o["account"] == "RRSP")
    assert tfsa_order["shares"] + rrsp_order["shares"] == 12
    assert tfsa_order["shares"] > rrsp_order["shares"]  # TFSA held more


def test_routing_buy_uses_preferred_account_from_policy():
    candidates = [{"ticker": "NBIS", "action": "buy", "shares": 5, "currentWeight": 2.1, "targetWeight": 5.5}]
    positions = {"TFSA": {}}
    cash = {"TFSA": 5000.0}
    policy = {
        "accountPreferenceRules": [{"match": "highGrowthEquity", "prefer": "TFSA"}, {"match": "default", "prefer": "TFSA"}],
        "psuFundingRule": {"ticker": "PSU-U.TO"},
    }
    target_data = {"holdings": [{"ticker": "NBIS", "role": "highGrowthEquity"}]}
    routed = compute_account_routing(candidates, positions, cash, policy, target_data, {"NBIS": 20.0})
    assert routed[-1]["account"] == "TFSA"


def test_routing_psu_funding_rule_triggers_when_cash_insufficient():
    candidates = [{"ticker": "NBIS", "action": "buy", "shares": 100, "currentWeight": 2.1, "targetWeight": 5.5}]
    positions = {"TFSA": {"PSU-U.TO": {"shares": 50.0, "costBasis": 100.0}}}
    cash = {"TFSA": 100.0}
    policy = {
        "accountPreferenceRules": [{"match": "default", "prefer": "TFSA"}],
        "psuFundingRule": {"ticker": "PSU-U.TO", "sameAccountOnly": True, "sharesFormula": "ceil(N * price / 100)"},
    }
    target_data = {"holdings": [{"ticker": "NBIS"}]}
    prices = {"NBIS": 20.0, "PSU-U.TO": 100.0}  # buy costs $2000, only $100 cash -> needs PSU trim
    routed = compute_account_routing(candidates, positions, cash, policy, target_data, prices)
    psu_sell = next(o for o in routed if o["ticker"] == "PSU-U.TO")
    nbis_buy = next(o for o in routed if o["ticker"] == "NBIS")
    assert psu_sell["action"] == "sell"
    assert psu_sell["account"] == "TFSA"  # same account as the buy it's funding
    assert nbis_buy["account"] == "TFSA"


def test_routing_no_shares_held_produces_no_sell_order():
    # Defensive: a candidate sell for a ticker not actually held in any account must not crash.
    candidates = [{"ticker": "GHOST", "action": "sell", "shares": 5, "currentWeight": 3.0, "targetWeight": 1.0}]
    positions = {"TFSA": {}}
    cash = {"TFSA": 0.0}
    policy = {"accountPreferenceRules": [{"match": "default", "prefer": "TFSA"}], "psuFundingRule": {"ticker": "PSU-U.TO"}}
    routed = compute_account_routing(candidates, positions, cash, policy, {"holdings": []}, {"GHOST": 10.0})
    assert routed == []


def test_routing_caps_sell_at_actual_held_shares_when_candidate_requests_more():
    # order["shares"]=10 but only 6 actually held (e.g. stale drift-derived request vs real tvSnapshot data)
    candidates = [{"ticker": "CRWD", "action": "sell", "shares": 10, "currentWeight": 7.0, "targetWeight": 4.0}]
    positions = {"TFSA": {"CRWD": {"shares": 6.0, "costBasis": 100.0}}}
    cash = {"TFSA": 0.0}
    policy = {"accountPreferenceRules": [{"match": "default", "prefer": "TFSA"}], "psuFundingRule": {"ticker": "PSU-U.TO"}}
    routed = compute_account_routing(candidates, positions, cash, policy, {"holdings": []}, {"CRWD": 100.0})
    assert routed[0]["account"] == "TFSA"
    assert routed[0]["shares"] == 6  # capped at actually-held amount, not the requested 10


def test_routing_caps_each_account_at_its_own_held_shares_in_multi_account_oversell():
    # order requests 20 shares of CRWD but TFSA holds 9 and RRSP holds 3 (12 total)
    candidates = [{"ticker": "CRWD", "action": "sell", "shares": 20, "currentWeight": 7.0, "targetWeight": 4.0}]
    positions = {
        "TFSA": {"CRWD": {"shares": 9.0, "costBasis": 100.0}},
        "RRSP": {"CRWD": {"shares": 3.0, "costBasis": 100.0}},
    }
    cash = {"TFSA": 0.0, "RRSP": 0.0}
    policy = {"accountPreferenceRules": [{"match": "default", "prefer": "TFSA"}], "psuFundingRule": {"ticker": "PSU-U.TO"}}
    routed = compute_account_routing(candidates, positions, cash, policy, {"holdings": []}, {"CRWD": 100.0})
    tfsa_order = next(o for o in routed if o["account"] == "TFSA")
    rrsp_order = next(o for o in routed if o["account"] == "RRSP")
    assert tfsa_order["shares"] <= 9  # never more than TFSA actually holds
    assert rrsp_order["shares"] <= 3  # never more than RRSP actually holds
    assert tfsa_order["shares"] + rrsp_order["shares"] == 12  # full aggregate held is still routed


def test_routing_rounding_remainder_never_pushes_account_past_its_own_held_shares():
    # Fractional holdings across 3 accounts where proportional floor() rounding loses a
    # combined 1.5 shares; the remainder redistribution must top up each account only up
    # to its own held_shares headroom, never past it (largest holder first).
    candidates = [{"ticker": "CRWD", "action": "sell", "shares": 14.5, "currentWeight": 7.0, "targetWeight": 4.0}]
    positions = {
        "TFSA": {"CRWD": {"shares": 9.5, "costBasis": 100.0}},
        "RRSP": {"CRWD": {"shares": 3.5, "costBasis": 100.0}},
        "MARGIN": {"CRWD": {"shares": 1.5, "costBasis": 100.0}},
    }
    cash = {"TFSA": 0.0, "RRSP": 0.0, "MARGIN": 0.0}
    policy = {"accountPreferenceRules": [{"match": "default", "prefer": "TFSA"}], "psuFundingRule": {"ticker": "PSU-U.TO"}}
    routed = compute_account_routing(candidates, positions, cash, policy, {"holdings": []}, {"CRWD": 100.0})
    tfsa_order = next(o for o in routed if o["account"] == "TFSA")
    rrsp_order = next(o for o in routed if o["account"] == "RRSP")
    margin_order = next(o for o in routed if o["account"] == "MARGIN")
    assert tfsa_order["shares"] <= 9.5
    assert rrsp_order["shares"] <= 3.5
    assert margin_order["shares"] <= 1.5
    assert tfsa_order["shares"] + rrsp_order["shares"] + margin_order["shares"] == 14.5


def test_capital_gains_computed_for_cash_account_with_cost_basis():
    positions = {"Cash": {"AAPL": {"shares": 50.0, "costBasis": 100.0}}}
    gain = compute_capital_gains_estimate("AAPL", "Cash", 10.0, 150.0, positions)
    assert gain == pytest.approx(500.0)  # (150-100)*10


def test_capital_gains_none_for_tfsa_or_rrsp():
    positions = {"TFSA": {"AAPL": {"shares": 50.0, "costBasis": 100.0}}}
    assert compute_capital_gains_estimate("AAPL", "TFSA", 10.0, 150.0, positions) is None


def test_capital_gains_none_when_cost_basis_unavailable():
    positions = {"Cash": {"AAPL": {"shares": 50.0, "costBasis": None}}}
    assert compute_capital_gains_estimate("AAPL", "Cash", 10.0, 150.0, positions) is None


def test_capital_gains_zero_cost_basis_is_not_treated_as_unavailable():
    # costBasis == 0.0 is a valid (if rare) value — e.g. gifted/DRIP shares with no
    # recorded purchase price. A naive `if not cost_basis` check would misclassify
    # this as "unavailable" and silently drop a real capital-gains figure.
    positions = {"Cash": {"AAPL": {"shares": 50.0, "costBasis": 0.0}}}
    gain = compute_capital_gains_estimate("AAPL", "Cash", 10.0, 150.0, positions)
    assert gain == pytest.approx(1500.0)  # (150-0)*10


def test_risk_budget_warns_when_projected_mrc_exceeds_cap():
    routed = [{"ticker": "NBIS", "action": "buy", "account": "TFSA", "shares": 50}]
    bands = {"NBIS": {"currentWeight": 2.0, "targetWeight": 5.5, "bandPct": 1.5, "driftPct": -3.5, "inBand": False}}
    risk_snapshot = {"marginalRiskContribution": {"NBIS": 0.10}, "clusterExposure": []}  # 10% MRC today
    policy = {"riskBudgetCaps": {"maxMarginalRiskContributionPct": 25, "maxClusterVarianceContributionPct": 60}}
    target_data = {"holdings": [{"ticker": "NBIS", "pillarId": "ai_infra"}]}
    warnings = compute_risk_budget_check(routed, bands, risk_snapshot, policy, target_data)
    # projected = 10% * (5.5/2.0) = 27.5% > 25% cap
    assert "NBIS" in warnings
    assert any("MRC" in w for w in warnings["NBIS"])


def test_risk_budget_no_warning_when_under_cap():
    routed = [{"ticker": "NBIS", "action": "buy", "account": "TFSA", "shares": 10}]
    bands = {"NBIS": {"currentWeight": 4.0, "targetWeight": 4.5, "bandPct": 1.5, "driftPct": -0.5, "inBand": False}}
    risk_snapshot = {"marginalRiskContribution": {"NBIS": 0.10}, "clusterExposure": []}
    policy = {"riskBudgetCaps": {"maxMarginalRiskContributionPct": 25, "maxClusterVarianceContributionPct": 60}}
    target_data = {"holdings": [{"ticker": "NBIS", "pillarId": "ai_infra"}]}
    assert compute_risk_budget_check(routed, bands, risk_snapshot, policy, target_data) == {}


def test_risk_budget_warns_on_cluster_cap_breach():
    routed = [{"ticker": "NBIS", "action": "buy", "account": "TFSA", "shares": 1}]
    bands = {"NBIS": {"currentWeight": 4.0, "targetWeight": 4.1, "bandPct": 1.5, "driftPct": -0.1, "inBand": False}}
    risk_snapshot = {
        "marginalRiskContribution": {"NBIS": 0.05},
        "clusterExposure": [{"pillarId": "ai_infra", "weight": 0.6, "varianceContributionPct": 72.0}],
    }
    policy = {"riskBudgetCaps": {"maxMarginalRiskContributionPct": 25, "maxClusterVarianceContributionPct": 60}}
    target_data = {"holdings": [{"ticker": "NBIS", "pillarId": "ai_infra"}]}
    warnings = compute_risk_budget_check(routed, bands, risk_snapshot, policy, target_data)
    assert any("cluster" in w.lower() for w in warnings["NBIS"])


def test_risk_budget_degrades_gracefully_when_snapshot_missing():
    routed = [{"ticker": "NBIS", "action": "buy", "account": "TFSA", "shares": 10}]
    bands = {"NBIS": {"currentWeight": 2.0, "targetWeight": 5.5, "bandPct": 1.5, "driftPct": -3.5, "inBand": False}}
    assert compute_risk_budget_check(routed, bands, None, {}, {"holdings": []}) == {}


def test_risk_budget_ignores_sell_orders():
    routed = [{"ticker": "CRWD", "action": "sell", "account": "TFSA", "shares": 10}]
    bands = {"CRWD": {"currentWeight": 7.8, "targetWeight": 4.0, "bandPct": 1.5, "driftPct": 3.8, "inBand": False}}
    risk_snapshot = {"marginalRiskContribution": {"CRWD": 0.99}, "clusterExposure": []}
    policy = {"riskBudgetCaps": {"maxMarginalRiskContributionPct": 1, "maxClusterVarianceContributionPct": 1}}
    assert compute_risk_budget_check(routed, bands, risk_snapshot, policy, {"holdings": []}) == {}


def test_risk_budget_no_crash_when_current_weight_zero():
    # A fresh INITIATE buy has currentWeight == 0.0 (no prior position), so the
    # target/current weight ratio used to project MRC is mathematically undefined.
    # A naive `mrc * (target / current)` would raise ZeroDivisionError here — the
    # function must guard against that and simply skip the MRC projection (it has
    # no denominator to scale from) rather than crash or fabricate a warning.
    routed = [{"ticker": "NEWCO", "action": "buy", "account": "TFSA", "shares": 25}]
    bands = {"NEWCO": {"currentWeight": 0.0, "targetWeight": 3.0, "bandPct": 1.5, "driftPct": -3.0, "inBand": False}}
    risk_snapshot = {"marginalRiskContribution": {"NEWCO": 0.08}, "clusterExposure": []}
    policy = {"riskBudgetCaps": {"maxMarginalRiskContributionPct": 25, "maxClusterVarianceContributionPct": 60}}
    target_data = {"holdings": [{"ticker": "NEWCO", "pillarId": "ai_infra"}]}
    warnings = compute_risk_budget_check(routed, bands, risk_snapshot, policy, target_data)
    assert warnings == {}


def test_risk_budget_no_warning_when_pillar_absent_from_cluster_exposure():
    # clusterExposure lists other pillars but not this ticker's own pillarId —
    # cluster lookup must miss cleanly (no warning, no KeyError) rather than
    # match the wrong entry or raise.
    routed = [{"ticker": "NBIS", "action": "buy", "account": "TFSA", "shares": 1}]
    bands = {"NBIS": {"currentWeight": 4.0, "targetWeight": 4.1, "bandPct": 1.5, "driftPct": -0.1, "inBand": False}}
    risk_snapshot = {
        "marginalRiskContribution": {"NBIS": 0.05},
        "clusterExposure": [{"pillarId": "semiconductors", "weight": 0.3, "varianceContributionPct": 90.0}],
    }
    policy = {"riskBudgetCaps": {"maxMarginalRiskContributionPct": 25, "maxClusterVarianceContributionPct": 60}}
    target_data = {"holdings": [{"ticker": "NBIS", "pillarId": "ai_infra"}]}
    assert compute_risk_budget_check(routed, bands, risk_snapshot, policy, target_data) == {}


def test_breaker_warnings_flags_triggered_breaker_on_buy():
    routed = [{"ticker": "NBIS", "action": "buy", "account": "TFSA", "shares": 6}]
    state = {"holdings": {"NBIS": {"nbis-rsi-breaker": {
        "status": "TRIGGERED", "currentValue": 78, "currentStreak": 3,
    }}}}
    warnings = compute_breaker_warnings(routed, state)
    assert "NBIS" in warnings
    assert "TRIGGERED" in warnings["NBIS"][0]


def test_breaker_warnings_ignores_ok_and_watching_status():
    routed = [{"ticker": "NBIS", "action": "buy", "account": "TFSA", "shares": 6}]
    state = {"holdings": {"NBIS": {"nbis-rsi-breaker": {"status": "WATCHING", "currentStreak": 2}}}}
    assert compute_breaker_warnings(routed, state) == {}


def test_breaker_warnings_ignores_sell_orders():
    routed = [{"ticker": "CRWD", "action": "sell", "account": "TFSA", "shares": 10}]
    state = {"holdings": {"CRWD": {"some-breaker": {"status": "TRIGGERED", "currentStreak": 5}}}}
    assert compute_breaker_warnings(routed, state) == {}


def test_breaker_warnings_degrades_gracefully_when_state_missing():
    routed = [{"ticker": "NBIS", "action": "buy", "account": "TFSA", "shares": 6}]
    assert compute_breaker_warnings(routed, None) == {}


# ── compute_rebalance_plan() — orchestrator integration ─────────────────────

def _fresh_timestamp() -> str:
    # NOTE: intentionally computed at fixture-write time, not hardcoded — a
    # fixed literal (e.g. "2026-07-09T13:00:00Z") ages past the 60-minute
    # staleness threshold as soon as real wall-clock time moves past it,
    # which would flakily/permanently trip DATA_STALE regardless of what a
    # test is actually trying to exercise.
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _write_full_fixture(tmp_path):
    target_path = tmp_path / "target-portfolio.json"
    portfolio_path = tmp_path / "portfolio.json"
    risk_path = tmp_path / "risk_snapshot.json"
    breaker_path = tmp_path / "thesis_breaker_state.json"
    policy_path = tmp_path / "account_policy.json"

    target_path.write_text(json.dumps({
        "holdings": [
            {"ticker": "CRWD", "targetWeight": 4.0, "pillarId": "cyber"},
            {"ticker": "NBIS", "targetWeight": 5.5, "pillarId": "ai_infra"},
            {"ticker": "PSU-U.TO", "targetWeight": 90.5, "pillarId": "cash"},
        ],
    }))
    portfolio_path.write_text(json.dumps({
        "holdings": [
            {"ticker": "CRWD", "shares": 15.0, "price": 100.0},
            {"ticker": "NBIS", "shares": 1.0, "price": 20.0},
            {"ticker": "PSU-U.TO", "shares": 90.0, "price": 100.0},
        ],
        "totals": {"totalUSD": 10500.0, "timestamp": _fresh_timestamp()},
        "tvSnapshot": {"snapshots": [{
            "accountType": "TFSA",
            "positions": [
                {"symbol": "CRWD", "quantity": 15.0, "avgFillPrice": 90.0},
                {"symbol": "NBIS", "quantity": 1.0, "avgFillPrice": 18.0},
                {"symbol": "PSU-U.TO", "quantity": 90.0, "avgFillPrice": 100.0},
            ],
            "balances": {"cashUSDCombined": 500.0},
        }]},
    }))
    risk_path.write_text(json.dumps({"marginalRiskContribution": {}, "clusterExposure": []}))
    breaker_path.write_text(json.dumps({"holdings": {}}))
    policy_path.write_text(json.dumps({
        "accountPreferenceRules": [{"match": "default", "prefer": "TFSA"}],
        "psuFundingRule": {"ticker": "PSU-U.TO", "sameAccountOnly": True, "sharesFormula": "ceil(N * price / 100)"},
        "riskBudgetCaps": {"maxMarginalRiskContributionPct": 25, "maxClusterVarianceContributionPct": 60},
        "bandConfig": {"relativePct": 20.0, "absolutePct": 1.5, "criticalMultiplier": 2.0},
    }))
    # All three thesis holdings need a projection row in the DB, or the
    # >30%-missing no-trade check (_check_no_trade_conditions) blocks the plan
    # before any of the "happy path" assertions below get a chance to run — a
    # 1-of-3 missing count is already 33% in this tiny fixture.
    _write_projection(tmp_path, "CRWD", "MAINTAIN")
    _write_projection(tmp_path, "NBIS", "ACCUMULATE")
    db_path = _write_projection(tmp_path, "PSU-U.TO", "MAINTAIN")
    return target_path, portfolio_path, risk_path, breaker_path, policy_path, db_path


def test_compute_rebalance_plan_full_shape(tmp_path):
    target_path, portfolio_path, risk_path, breaker_path, policy_path, db_path = _write_full_fixture(tmp_path)
    plan = compute_rebalance_plan(
        target_portfolio_path=target_path, portfolio_path=portfolio_path,
        risk_snapshot_path=risk_path, thesis_breaker_state_path=breaker_path,
        account_policy_path=policy_path, db_path=db_path,
    )
    expected_keys = {"generatedAt", "blockedReason", "bands", "orders", "skippedRestores", "accountDataSource", "warnings"}
    assert expected_keys <= set(plan.keys())
    assert plan["blockedReason"] is None
    tickers_in_orders = {o["ticker"] for o in plan["orders"]}
    assert "CRWD" in tickers_in_orders  # overweight (14.3% actual vs 4.0% target) -> sell
    assert "NBIS" in tickers_in_orders  # underweight (0.19% actual vs 5.5% target) -> buy
    assert plan["accountDataSource"] == {"TFSA": "tvSnapshot", "RRSP": "heuristic_1_3_mirror"}


def test_compute_rebalance_plan_blocked_when_targets_dont_sum_to_100(tmp_path):
    target_path, portfolio_path, risk_path, breaker_path, policy_path, db_path = _write_full_fixture(tmp_path)
    target_path.write_text(json.dumps({"holdings": [{"ticker": "CRWD", "targetWeight": 4.0, "pillarId": "cyber"}]}))
    plan = compute_rebalance_plan(
        target_portfolio_path=target_path, portfolio_path=portfolio_path,
        risk_snapshot_path=risk_path, thesis_breaker_state_path=breaker_path,
        account_policy_path=policy_path, db_path=db_path,
    )
    assert plan["blockedReason"] is not None
    assert "TARGETS_INVALID" in plan["blockedReason"]
    assert plan["orders"] == []


def test_compute_rebalance_plan_blocked_when_portfolio_stale(tmp_path):
    target_path, portfolio_path, risk_path, breaker_path, policy_path, db_path = _write_full_fixture(tmp_path)
    stale = json.loads(portfolio_path.read_text())
    stale["totals"]["timestamp"] = "2020-01-01T00:00:00Z"
    portfolio_path.write_text(json.dumps(stale))
    plan = compute_rebalance_plan(
        target_portfolio_path=target_path, portfolio_path=portfolio_path,
        risk_snapshot_path=risk_path, thesis_breaker_state_path=breaker_path,
        account_policy_path=policy_path, db_path=db_path,
    )
    assert "DATA_STALE" in plan["blockedReason"]


def test_compute_rebalance_plan_degrades_when_risk_snapshot_missing(tmp_path):
    target_path, portfolio_path, risk_path, breaker_path, policy_path, db_path = _write_full_fixture(tmp_path)
    risk_path.unlink()
    plan = compute_rebalance_plan(
        target_portfolio_path=target_path, portfolio_path=portfolio_path,
        risk_snapshot_path=risk_path, thesis_breaker_state_path=breaker_path,
        account_policy_path=policy_path, db_path=db_path,
    )
    assert plan["blockedReason"] is None
    assert any("risk_snapshot" in w for w in plan["warnings"])


def test_compute_rebalance_plan_order_carries_risk_and_breaker_warnings(tmp_path):
    target_path, portfolio_path, risk_path, breaker_path, policy_path, db_path = _write_full_fixture(tmp_path)
    risk_path.write_text(json.dumps({
        "marginalRiskContribution": {"NBIS": 0.20},
        "clusterExposure": [{"pillarId": "ai_infra", "weight": 0.3, "varianceContributionPct": 30.0}],
    }))
    breaker_path.write_text(json.dumps({"holdings": {"NBIS": {"b1": {"status": "TRIGGERED", "currentValue": 80, "currentStreak": 4}}}}))
    plan = compute_rebalance_plan(
        target_portfolio_path=target_path, portfolio_path=portfolio_path,
        risk_snapshot_path=risk_path, thesis_breaker_state_path=breaker_path,
        account_policy_path=policy_path, db_path=db_path,
    )
    nbis_order = next(o for o in plan["orders"] if o["ticker"] == "NBIS")
    assert len(nbis_order["riskGateWarnings"]) >= 1  # cap-breaching, deliberately not vetoed
    assert len(nbis_order["breakerWarnings"]) >= 1
    assert nbis_order in plan["orders"]  # still present, not excluded
