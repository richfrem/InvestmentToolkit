#!/usr/bin/env python3
"""
rebase_equity_valuations.py - Re-base saved earnings-multiple valuations for debt.

Purpose:
    Saved year-5 EPS x exit P/E valuations were discounted at a blended rate (WACC),
    which falls as a company borrows more, and had no adjustment for balance-sheet
    risk. This script recomputes each one with the same saved scenario assumptions
    but (1) the cost of equity as the discount rate and (2) scenario probabilities
    shifted toward the bear case for high leverage (leverage.py), then reports old
    against new. With --write it saves the result as a new projection version; the
    previous version is kept.

Layer:
    Stock valuation orchestration. Reads prices and fundamentals from the network.

Usage:
    python3 rebase_equity_valuations.py                  # held positions, report only
    python3 rebase_equity_valuations.py --tickers CRWV CORZ --json
    python3 rebase_equity_valuations.py --all            # every saved valuation, report only
    python3 rebase_equity_valuations.py --write          # save new versions

Key Functions:
    saved_inputs()   - Read one saved valuation into calculator inputs
    rebase()         - Pure recomputation from inputs, rate facts and fundamentals
    main()           - CLI: fetch, rebase, report, optionally persist

Key Input Dependencies:
    domain_model.sqlite projections; wacc.compute_wacc; market_data.get_fundamentals;
    dcf_scenarios.run; leverage.py.

Key Output Dependencies:
    With --write: new projection_version and projection_scenario rows via persist_valuation.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_REPO_ROOT / "investment_screener/backend/py_services"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from dcf_scenarios import SCENARIO_NAMES, run, valuation_signal  # noqa: E402
from leverage import apply_leverage_weights, leverage_profile, rate_basis_check  # noqa: E402

_DEFAULT_DB_PATH = str(_REPO_ROOT / "investment_screener/backend/data/domain_model.sqlite")
# Two-year regression betas overstate how risky a stock will stay, so the raw beta is
# pulled one third of the way to the market's 1.0 (Blume adjustment) and then bounded:
# a single stock is never treated as safer than the market, and an extreme reading from
# a short or volatile history is not taken at face value.
BLUME_WEIGHT = 0.67
BETA_BOUNDS = (1.0, 2.0)
# Saved scenario prices reproduced this closely came from the current calculator; older
# valuations that do not are still re-based (by discount-factor scaling) and marked.
REPRODUCTION_TOLERANCE = 0.03


def saved_inputs(entry: dict, scenario_rows: list[dict]) -> dict[str, Any] | None:
    """Read one saved valuation into calculator inputs, whichever format it was saved in.

    Returns:
        None when it is not an unaudited earnings-multiple valuation or lacks inputs,
        else {"revenue", "shares", "rate", "horizon", "scenarios", "savedPrices", "log"}.
    """
    snapshot = json.loads(entry.get("snapshot_json") or "{}")
    raw = json.loads(entry.get("raw_json") or "{}")
    log = json.loads(entry.get("analytics_log_json") or "{}")
    model = log.get("valuationModel") or {}
    settings = raw.get("globalSettings") or {}
    if model.get("discountRateAudit") or "annual_fcff" in (model.get("method"), entry.get("model")):
        return None
    revenue = snapshot.get("baseRevenue") or snapshot.get("revenue")
    shares = snapshot.get("baseShares") or snapshot.get("shares")
    rate = snapshot.get("discountRate")
    if rate is None and settings.get("discountRate") is not None:
        rate = settings["discountRate"] / 100
    rows = {row["scenario_name"]: row for row in scenario_rows}
    if not revenue or not shares or rate is None or any(name not in rows for name in SCENARIO_NAMES):
        return None
    scenarios = {name: {
        "weight": rows[name]["weight"], "growthRate": rows[name]["growth_rate"], "netMargin": rows[name]["net_margin"],
        "exitPE": rows[name]["exit_pe"], "qualityMultiplier": rows[name]["quality_multiplier"] or 1.0,
        "shareChange": rows[name]["share_change"] or 0.0, "rationale": rows[name].get("rationale"),
        "risks": json.loads(rows[name].get("risks_json") or "[]"),
    } for name in SCENARIO_NAMES}
    return {"revenue": float(revenue), "shares": float(shares), "rate": float(rate),
            "horizon": int(snapshot.get("horizon") or settings.get("timeHorizon") or 5), "scenarios": scenarios,
            "savedPrices": {name: rows[name]["scenario_price"] for name in SCENARIO_NAMES}, "log": log,
            "price": snapshot.get("currentPrice") or snapshot.get("price"),
            # Year-5 figures as saved: scenario assumptions are not recomputed.
            "savedRows": {name: {"year5Revenue": rows[name].get("year5_revenue"), "year5NetIncome": rows[name].get("year5_net_income"),
                                 "year5EPS": rows[name].get("year5_eps")} for name in SCENARIO_NAMES},
            # Weights before any earlier leverage shift, so re-running never shifts twice.
            "originalWeights": (model.get("rebasedFrom") or {}).get("weights")}


def rebase(ticker: str, inputs: dict, price: float | None, risk_free: float, beta: float, erp: float,
           fundamentals: dict[str, Any]) -> dict[str, Any]:
    """Re-base a saved valuation to the cost of equity with leverage-shifted weights.

    Each saved scenario price is a year-N value discounted at the old rate, so the price
    at the new rate is the saved price x ((1 + old) / (1 + new)) ** N. This is exact for
    valuations the calculator reproduces and holds to about 1% for older ones saved by an
    earlier engine (``reproduced`` is False for those), without needing their hidden inputs.

    Args:
        inputs: saved_inputs() result.
        price: Current price, for upside and market value.
        risk_free, beta, erp: CAPM inputs as decimals; beta is the raw regression beta,
            Blume-adjusted and bounded to BETA_BOUNDS here.
        fundamentals: {"totalDebt", "cash", "ebitda", "operatingIncome", "interestExpense", "currentRatio"}.

    Returns:
        {"status": REBASED|UNCHANGED, "reproduced", "old": {...}, "new": {...}, "leverage",
        "rateBasis", "costOfEquity", "beta", "result"}. The rate is never lowered.
    """
    scenarios, old_rate, saved_prices = inputs["scenarios"], inputs["rate"], inputs["savedPrices"]
    old_weights = {name: scenarios[name]["weight"] for name in SCENARIO_NAMES}
    old = {"rate": old_rate, "weights": old_weights,
           "fairValue": round(sum(old_weights[name] * (saved_prices[name] or 0) for name in SCENARIO_NAMES), 2)}
    check = run(ticker, inputs["revenue"], inputs["shares"], scenarios, old_rate, inputs["horizon"], price)
    drift = max(abs(check["scenarios"][name]["presentValue"] - (saved_prices[name] or 0))
                / max(abs(saved_prices[name] or 0), 1.0) for name in SCENARIO_NAMES)
    adjusted_beta = BLUME_WEIGHT * beta + (1 - BLUME_WEIGHT) * 1.0
    bounded_beta = round(min(max(adjusted_beta, BETA_BOUNDS[0]), BETA_BOUNDS[1]), 3)
    cost_of_equity = risk_free + bounded_beta * erp
    market_cap = price * inputs["shares"] if price else None
    profile = leverage_profile(fundamentals.get("totalDebt"), fundamentals.get("cash"), fundamentals.get("ebitda"),
                               fundamentals.get("operatingIncome"), fundamentals.get("interestExpense"),
                               fundamentals.get("currentRatio"), market_cap)
    basis = rate_basis_check("terminal_earnings", old_rate, cost_of_equity)
    new_rate = round(max(old_rate, cost_of_equity), 4)
    weights = apply_leverage_weights(inputs.get("originalWeights") or old_weights, profile["tier"])
    factor = ((1 + old_rate) / (1 + new_rate)) ** inputs["horizon"]
    prices = {name: round((saved_prices[name] or 0) * factor, 2) for name in SCENARIO_NAMES}
    fair_value = round(sum(weights[name] * prices[name] for name in SCENARIO_NAMES), 2)
    upside = (fair_value - price) / price * 100 if price else None
    new = {"rate": new_rate, "fairValue": fair_value, "weights": weights}
    result = {"scenarios": {name: {**scenarios[name], "weight": weights[name], "presentValue": prices[name]}
                            for name in SCENARIO_NAMES},
              "action": valuation_signal(upside) or "HOLD", "currentPrice": price,
              "upsidePct": round(upside, 1) if upside is not None else None}
    changed = new_rate != old_rate or weights != old_weights
    return {"status": "REBASED" if changed else "UNCHANGED", "reproduced": drift <= REPRODUCTION_TOLERANCE,
            "old": old, "new": new, "leverage": profile, "rateBasis": basis,
            "costOfEquity": round(cost_of_equity, 4), "beta": round(beta, 2), "boundedBeta": bounded_beta,
            "riskFreeRate": risk_free, "erp": erp, "result": result}


def projection_payload(ticker: str, entry: dict, inputs: dict, outcome: dict, as_of: str) -> dict[str, Any]:
    """Build the persist_valuation payload for a re-based valuation."""
    result, old, new = outcome["result"], outcome["old"], outcome["new"]
    saved_rows = inputs.get("savedRows") or {}
    scenarios = {name: {**saved_rows.get(name, {}), **result["scenarios"][name],
                        "price": result["scenarios"][name]["presentValue"]} for name in SCENARIO_NAMES}
    note = (f" Re-based {as_of}: discount rate {old['rate'] * 100:.2f}% -> {new['rate'] * 100:.2f}% (cost of equity), "
            f"leverage {outcome['leverage']['tier']}; fair value ${old['fairValue']:,.2f} -> ${new['fairValue']:,.2f}. "
            "Scenario assumptions unchanged.")
    model = {**(inputs["log"].get("valuationModel") or {}), "method": "terminal_earnings",
             "leverage": outcome["leverage"],
             "rateBasis": {**rate_basis_check("terminal_earnings", new["rate"], outcome["costOfEquity"]),
                           "rateType": "COST_OF_EQUITY", "costOfEquity": outcome["costOfEquity"],
                           "riskFreeRate": outcome["riskFreeRate"], "erp": outcome["erp"], "beta": outcome["beta"],
                           "boundedBeta": outcome["boundedBeta"], "reproduced": outcome["reproduced"],
                           "basis": "automated CAPM re-base; not a sourced rate audit" + (
                               "" if outcome["reproduced"] else "; saved by an earlier engine, scaled by discount factor")},
             "rebasedFrom": {"version": entry["version"], "discountRate": old["rate"],
                             "weights": inputs.get("originalWeights") or old["weights"],
                             "fairValue": old["fairValue"], "asOf": as_of}}
    projection = {"fair_value": new["fairValue"], "action": result["action"], "model": entry.get("model"),
                  "rationale": (entry.get("rationale") or "") + note, "current_price": result["currentPrice"],
                  "upside_pct": result["upsidePct"], "discount_rate": new["rate"], "horizon": inputs["horizon"],
                  "base_revenue": inputs["revenue"], "base_shares": inputs["shares"], "scenarios": scenarios,
                  "valuationModel": model, "source": "AI_AGENT"}
    if inputs["log"].get("outlookAudit"):
        projection["outlookAudit"] = inputs["log"]["outlookAudit"]
    return {"symbol": ticker, "analyzed_at": entry.get("analyzed_at"), "projection": projection}


def _fetch_facts(ticker: str, market_cap: float) -> tuple[dict, dict]:
    """Rate components and fundamentals for one ticker (network)."""
    from market_data import get_fundamentals
    from wacc import compute_wacc

    def value(data: dict, field: str) -> Any:
        return (data.get(field) or {}).get("value")
    rates = compute_wacc(ticker, market_cap)
    data = get_fundamentals(ticker)
    return rates, {"totalDebt": value(data, "totalDebt"), "cash": value(data, "cashAndEquivalents"),
                   "ebitda": value(data, "ebitda"), "operatingIncome": value(data, "operatingIncome"),
                   "interestExpense": value(data, "interestExpense"), "currentRatio": value(data, "currentRatio")}


def main() -> None:
    """CLI entry point: report (default) or save re-based valuations."""
    from datetime import date

    from domain_model.db_client import initialize_db
    from domain_model.investment_price_repository import get_investment_price
    from domain_model.projection_repository import get_latest_projection_by_source, get_projection_scenarios

    parser = argparse.ArgumentParser(description="Re-base saved earnings-multiple valuations for debt")
    parser.add_argument("--tickers", nargs="*", help="Symbols to re-base (default: every held position)")
    parser.add_argument("--all", action="store_true", help="Every symbol with a saved valuation, held or not")
    parser.add_argument("--db-path", default=_DEFAULT_DB_PATH)
    parser.add_argument("--write", action="store_true", help="Save each re-based valuation as a new version")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    conn = initialize_db(args.db_path)
    try:
        from domain_model.projection_repository import list_symbols_with_projections
        tickers = [t.upper() for t in args.tickers] if args.tickers else sorted(list_symbols_with_projections(conn)) if args.all else [row[0] for row in conn.execute(
            "SELECT DISTINCT i.symbol FROM account_investment a JOIN investment i USING(investment_id) "
            "WHERE a.quantity > 0 ORDER BY i.symbol;")]
        work = []
        for ticker in tickers:
            row = conn.execute("SELECT investment_id FROM investment WHERE symbol = ?;", (ticker,)).fetchone()
            entry = get_latest_projection_by_source(conn, row[0], "AI_AGENT") if row else None
            inputs = saved_inputs(entry, get_projection_scenarios(conn, entry["projection_id"])) if entry else None
            stored = get_investment_price(conn, row[0]) if row else None
            work.append((ticker, entry, inputs, (stored or {}).get("price") or (inputs or {}).get("price")))
    finally:
        conn.close()

    report = []
    for ticker, entry, inputs, price in work:
        if inputs is None:
            report.append({"ticker": ticker, "status": "SKIPPED",
                           "note": "No unaudited earnings-multiple valuation to re-base"})
            continue
        try:
            rates, fundamentals = _fetch_facts(ticker, (price or 0) * inputs["shares"] or 1.0)
            outcome = rebase(ticker, inputs, price, rates["riskFreeRate"], rates["beta"], rates["erp"], fundamentals)
        except Exception as error:  # noqa: BLE001 - one ticker's data failure must not stop the batch
            report.append({"ticker": ticker, "status": "ERROR", "note": str(error)})
            continue
        # An unchanged valuation is still saved once, so its debt grade and rate check are on record.
        recorded = bool((inputs["log"].get("valuationModel") or {}).get("leverage"))
        if args.write and (outcome["status"] == "REBASED" or not recorded):
            from persist_valuation import persist_valuation
            persist_valuation(projection_payload(ticker, entry, inputs, outcome, date.today().isoformat()), args.db_path)
            outcome["written"] = True
        outcome.pop("result", None)
        report.append({"ticker": ticker, "price": price, **outcome})

    if args.json:
        print(json.dumps(report, indent=2))
        return
    print(f"{'Ticker':<7}{'Status':<16}{'Rate':>15}{'Leverage':>10}{'Bear wt':>13}{'Fair value':>24}  Notes")
    for item in report:
        if "new" not in item:
            print(f"{item['ticker']:<7}{item['status']:<16}{'':>15}{'':>10}{'':>13}{'':>24}  {item.get('note', '')}")
            continue
        old, new = item["old"], item["new"]
        status = item["status"] + ("" if item.get("reproduced") else "~")
        print(f"{item['ticker']:<7}{status:<16}{old['rate'] * 100:>6.2f}% ->{new['rate'] * 100:>5.2f}%"
              f"{item['leverage']['tier']:>10}{old['weights']['bear'] * 100:>5.0f}% ->{new['weights']['bear'] * 100:>3.0f}%"
              f"{old['fairValue']:>11,.2f} ->{new['fairValue']:>10,.2f}  {'; '.join(item['leverage']['reasons'])}")


if __name__ == "__main__":
    main()
