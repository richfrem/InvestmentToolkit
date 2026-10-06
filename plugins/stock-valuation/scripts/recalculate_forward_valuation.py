#!/usr/bin/env python3
"""Purpose: reproduce a sourced annual FCFF valuation and persistence payload.

Layer: Stock valuation orchestration; no live writes or network requests.
Usage: python3 recalculate_forward_valuation.py --model MODEL.json --output DIR
Key Functions: calculate, sensitivity, stress_cases, earnings_cross_check,
    projection_document, write_artifacts, main.
Key Input Dependencies: dated model JSON, canonical dcf_scenarios, reverse_dcf,
    recommendation.recommend and validate_projection; all dollar inputs are USD.
"""
import argparse
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from dcf_scenarios import run
from recommendation import recommend
from reverse_dcf import solve_implied_growth
from validate_projection import validate_projection


# Delegate every valuation calculation to the shared engine.
def calculate(model: dict[str, Any], scenarios: dict | None = None, rate: float | None = None) -> dict:
    """Compute scenario values with explicit balance-sheet and SBC conventions."""
    params = deepcopy(scenarios or model["scenarios"])
    for scenario in params.values():
        scenario.update(model["bridge"])
        scenario.update(method="annual_fcff", sbcTreatment="expensed_in_operating_margin")
    result = run(model["ticker"], model["baseRevenue"], model["shares"], params,
                 discount_rate=rate if rate is not None else model["discountRate"],
                 horizon=len(params["base"]["annualForecast"]), price=model["price"])
    if not result["validation"]["valid"]:
        raise ValueError(result["validation"]["errors"])
    result["method"] = "annual_fcff"
    result["sources"] = model["sources"]
    result["asOf"] = model["asOf"]
    result["recommendation"] = recommend(held=True, upside_pct=result["upsidePct"])
    return result


# Calculate the discount/terminal-growth matrix without a second DCF formula.
def sensitivity(model: dict[str, Any]) -> list[dict]:
    """Return nine probability-weighted valuations at the specified rates."""
    results = []
    for rate in model["rates"]:
        for growth in model["terminalGrowthRates"]:
            scenarios = deepcopy(model["scenarios"])
            for scenario in scenarios.values():
                scenario["terminalGrowth"] = growth
            value = calculate(model, scenarios, rate)
            results.append({"discountRate": rate, "terminalGrowth": growth,
                            "fairValue": value["weightedFairValue"],
                            "action": value["recommendation"]["action"]})
    return results


# Make material assumption shocks visible independently of scenario weights.
def stress_cases(model: dict[str, Any]) -> list[dict]:
    """Apply disclosed margin, capital-spending and share-overhang stresses."""
    results = []
    for name in ("operating_margin_minus_10pp", "capex_plus_25pct", "shares_plus_15pct"):
        trial = deepcopy(model)
        if name == "shares_plus_15pct":
            trial["shares"] *= 1.15
        else:
            for scenario in trial["scenarios"].values():
                for row in [*scenario["annualForecast"], scenario["terminalForecast"]]:
                    if name == "operating_margin_minus_10pp":
                        row["operatingMarginPct"] -= 10
                    else:
                        row["capex"] *= 1.25
        value = calculate(trial)
        results.append({"stress": name, "fairValue": value["weightedFairValue"],
                        "action": value["recommendation"]["action"]})
    if model.get("convertibleStress"):
        trial = deepcopy(model)
        conversion = trial["convertibleStress"]
        trial["bridge"]["debt"] -= conversion["debtCarryingValue"]
        trial["shares"] += conversion["maximumShares"]
        value = calculate(trial)
        results.append({"stress": "convertible_converted", "fairValue": value["weightedFairValue"],
                        "action": value["recommendation"]["action"],
                        "assumption": conversion["description"]})
    return results


# Use the established reverse earnings calculator as a disclosed alternate lens.
def earnings_cross_check(model: dict, result: dict) -> dict:
    """Invert normalized terminal earnings; this is not an independent peer study."""
    scenarios = result["scenarios"]
    terminal = scenarios["base"]["terminalForecast"]
    margin = terminal["nopat"] / terminal["revenue"] * 100
    horizon = scenarios["base"]["annualForecast"][-1]["discountPeriod"]
    reverse = solve_implied_growth(model["price"], model["shares"], model["discountRate"],
                                  horizon, margin, model["reverseEarningsPE"], 1,
                                  model["baseRevenue"], scenarios["bear"]["growthRate"],
                                  scenarios["base"]["growthRate"], scenarios["bull"]["growthRate"])
    reverse.update(method="discounted_terminal_earnings", exitPE=model["reverseEarningsPE"],
                   netMarginProxyPct=margin,
                   limitation="Unlevered NOPAT proxy, no cash bridge or annual distributions. Shares assumptions with FCFF; peer data insufficient. Diagnostic only.")
    return reverse


# Build the existing projection validation contract without changing action rules.
def projection_document(model: dict, result: dict) -> dict:
    """Package the canonical action, calculation and forward audit for validation."""
    scenarios = deepcopy(result["scenarios"])
    for scenario in scenarios.values():
        scenario["scenarioPrice"] = scenario["presentValue"]
    return {"ticker": model["ticker"], "id": f"{model['ticker']}-forward-{model['asOf']}",
            "source": "AI_AGENT", "schemaVersion": "2.0", "version": 1,
            "savedAt": model["asOf"], "rationale": model["rationale"],
            "snapshot": {"price": model["price"], "currency": "USD", "shares": model["shares"],
                         "revenue": model["baseRevenue"], "lastActualPS": None},
            "scenarios": scenarios, "aiThesis": {"action": result["recommendation"]["action"],
                                                  "confidenceScore": 0.65, "rationale": model["rationale"]},
            "globalSettings": {"discountRate": model["discountRate"]},
            "analyticsLog": {"dcf": result, "reverseDcf": result["reverseEarnings"],
                             "comps": {"status": "insufficient_peer_data", "peersUsed": []},
                             "outlookAudit": model["outlookAudit"]}}


# Write reproducible review artifacts; persistence is a separate canonical CLI call.
def write_artifacts(model: dict, output: Path) -> dict:
    """Validate and emit the model result, projection and live-DB payload."""
    result = calculate(model)
    result["sensitivity"] = sensitivity(model)
    result["stressCases"] = stress_cases(model)
    result["reverseEarnings"] = earnings_cross_check(model, result)
    projection = projection_document(model, result)
    errors = validate_projection(projection)
    if errors:
        raise ValueError(errors)
    payload = {"symbol": model["ticker"], "name": model["name"], "analyzed_at": model["asOf"],
               "projection": {**result, "model": "annual_fcff", "source": "AI_AGENT",
                              "rationale": model["rationale"], "outlookAudit": model["outlookAudit"],
                              "valuationModel": result}}
    output.mkdir(parents=True, exist_ok=True)
    for name, data in (("valuation", result), ("projection", projection), ("payload", payload)):
        (output / f"{name}.json").write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")
    source_lines = "\n".join(
        f"- {source['date']}: [{source['type']}]({source['url']}) — {source['use']}"
        for source in model["sources"]
    )
    scenario_lines = "\n".join(
        f"| {name.title()} | ${scenario['presentValue']:,.2f} | {scenario['weight']:.0%} | "
        f"{scenario.get('terminalValuePct', 0):.1f}% |"
        for name, scenario in result["scenarios"].items()
    )
    stress_lines = "\n".join(
        f"| {stress['stress']} | ${stress['fairValue']:,.2f} | {stress['action']} |"
        for stress in result["stressCases"]
    )
    (output / "review.md").write_text(
        f"# {model['ticker']} forward cash-flow valuation\n\n"
        f"As of {model['asOf']}; price ${model['price']:,.2f}. Weighted fair value "
        f"${result['weightedFairValue']:,.2f} ({result['upsidePct']:+.1f}%); "
        f"canonical portfolio action **{result['recommendation']['action']}**.\n\n"
        f"## Scenarios\n\n| Case | Fair value/share | Weight | Terminal value share of EV |\n"
        f"|---|---:|---:|---:|\n{scenario_lines}\n\n"
        f"## Sensitivities\n\n| Stress | Fair value/share | Valuation action |\n|---|---:|---|\n{stress_lines}\n\n"
        f"## Model scope and limits\n\n{model['rationale']}\n\n"
        f"{model['outlookAudit']['strategicAssessment']}\n\n"
        f"Backlog and pipeline: {model['outlookAudit']['backlogPipeline']}\n\n"
        f"Adversarial risks: {'; '.join(model['outlookAudit']['adversarialRisks'])}.\n\n"
        f"Existing decision context: {model.get('reviewOverlay', 'No standing-decision change is included in this valuation update.')}\n\n"
        f"Consensus figures are provider estimates, not company guidance. Scenario values are "
        f"assumption-driven; they do not change standing decisions or authorize trades.\n\n"
        f"## Sources\n\n{source_lines}\n"
    )
    return result


# Keep CLI I/O separate from financial formulas.
def main() -> None:
    """Read explicit model inputs and emit validated artifacts."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    model = json.loads(args.model.read_text())
    result = write_artifacts(model, args.output)
    print(json.dumps({"ticker": result["ticker"], "fairValue": result["weightedFairValue"],
                      "upsidePct": result["upsidePct"], "action": result["recommendation"]["action"]}))


if __name__ == "__main__":
    main()
