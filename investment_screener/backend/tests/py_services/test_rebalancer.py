"""Tests for rebalancer.py — E2 rebalancer v2 (Phase 3, sub-spec 4)."""
import json
import math
import sys
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


def _write_projection(path: Path, ticker: str, action: str) -> None:
    (path / f"{ticker}.json").write_text(json.dumps([{
        "source": "AI_AGENT", "savedAt": "2026-07-01T00:00:00Z",
        "aiThesis": {"action": action},
    }]))


def test_get_latest_valuation_action_reads_latest_ai_agent_entry(tmp_path):
    _write_projection(tmp_path, "NBIS", "ACCUMULATE")
    assert get_latest_valuation_action("NBIS", tmp_path) == "ACCUMULATE"


def test_get_latest_valuation_action_missing_file_returns_none(tmp_path):
    assert get_latest_valuation_action("NOPE", tmp_path) is None


def test_candidate_orders_sell_when_overweight(tmp_path):
    bands = {"CRWD": {"currentWeight": 7.8, "targetWeight": 4.0, "bandPct": 1.5, "driftPct": 3.8, "inBand": False}}
    target_data = {"holdings": [{"ticker": "CRWD", "targetWeight": 4.0}]}
    candidates, skipped = compute_candidate_orders(bands, target_data, {"CRWD": 100.0}, 10000.0, tmp_path)
    assert skipped == []
    assert candidates[0]["ticker"] == "CRWD"
    assert candidates[0]["action"] == "sell"
    assert candidates[0]["shares"] == math.floor(0.038 * 10000.0 / 100.0)


def test_candidate_orders_buy_when_underweight_and_clean(tmp_path):
    _write_projection(tmp_path, "NBIS", "ACCUMULATE")
    bands = {"NBIS": {"currentWeight": 2.1, "targetWeight": 5.5, "bandPct": 1.5, "driftPct": -3.4, "inBand": False}}
    target_data = {"holdings": [{"ticker": "NBIS", "targetWeight": 5.5}]}
    candidates, skipped = compute_candidate_orders(bands, target_data, {"NBIS": 20.0}, 10000.0, tmp_path)
    assert skipped == []
    assert candidates[0]["action"] == "buy"


def test_candidate_orders_skips_exit_rated_underweight(tmp_path):
    _write_projection(tmp_path, "INTC", "EXIT")
    bands = {"INTC": {"currentWeight": 1.0, "targetWeight": 4.0, "bandPct": 1.5, "driftPct": -3.0, "inBand": False}}
    target_data = {"holdings": [{"ticker": "INTC", "targetWeight": 4.0}]}
    candidates, skipped = compute_candidate_orders(bands, target_data, {"INTC": 30.0}, 10000.0, tmp_path)
    assert candidates == []
    assert skipped[0]["ticker"] == "INTC"
    assert "EXIT" in skipped[0]["reason"]


def test_candidate_orders_skips_above_target_entry_price(tmp_path):
    bands = {"SNDK": {"currentWeight": 4.2, "targetWeight": 6.0, "bandPct": 1.5, "driftPct": -1.8, "inBand": False}}
    target_data = {"holdings": [{"ticker": "SNDK", "targetWeight": 6.0, "targetEntryPrice": 1350.0}]}
    candidates, skipped = compute_candidate_orders(bands, target_data, {"SNDK": 1741.0}, 10000.0, tmp_path)
    assert candidates == []
    assert "targetEntryPrice" in skipped[0]["reason"]


def test_candidate_orders_skips_when_standing_decision_conflicts(tmp_path):
    bands = {"VST": {"currentWeight": 1.0, "targetWeight": 2.27, "bandPct": 1.5, "driftPct": -1.27, "inBand": False}}
    target_data = {"holdings": [{
        "ticker": "VST", "targetWeight": 2.27,
        "standingDecision": {"type": "SA_LP_EXIT_OVERRIDE", "reason": "DO NOT ADD"},
    }]}
    candidates, skipped = compute_candidate_orders(bands, target_data, {"VST": 50.0}, 10000.0, tmp_path)
    assert candidates == []
    assert "Standing decision" in skipped[0]["reason"]


def test_candidate_orders_skips_zero_share_orders(tmp_path):
    # Tiny drift dollar amount rounds down to 0 shares — must not emit a phantom order.
    bands = {"TINY": {"currentWeight": 0.01, "targetWeight": 1.5, "bandPct": 1.5, "driftPct": -1.49, "inBand": False}}
    target_data = {"holdings": [{"ticker": "TINY", "targetWeight": 1.5}]}
    candidates, skipped = compute_candidate_orders(bands, target_data, {"TINY": 5000.0}, 100.0, tmp_path)
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
