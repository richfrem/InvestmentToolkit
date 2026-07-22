#!/usr/bin/env python3
"""
relabel_actions.py (Python Service)
=====================================

Purpose:
    Drives the re-derivation of correct action verbs (INITIATE, ACCUMULATE, TRIM, etc.) for recommendation JSONs.
    Compares live brokerage holdings against proposed targets to ensure actions reflect actual portfolio state.

Layer: Backend / Python Services / Rebalancing

Usage Examples:
    python3 relabel_actions.py --recs 2026-05-11-Recommendations.json --threshold 0.5

Key Functions:
    - assign_action() - Core logic for mapping weight deltas to specific investment action verbs
    - main() - CLI orchestrator that computes actual weights and updates recommendation files in-place

Key Input Dependencies:
    - investment_screener/backend/data/portfolio.json (Internal state database)
"""

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
PY_SERVICES = REPO_ROOT / "investment_screener/backend/py_services"
DEFAULT_PORTFOLIO = REPO_ROOT / "investment_screener/backend/data/portfolio.json"
MAINTAIN_THRESHOLD = 0.5  # pp — within this band = MAINTAIN


def build_actual_pct_map() -> dict[str, float]:
    """Return {ticker: actual weight %} sourced from domain_model.sqlite.

    Wave 3 cutover (ADR-030): shares/prices/total_usd come from
    ``portfolio_io.load_portfolio_state()`` (already aggregated per-symbol across
    accounts) and the weight-% formula is delegated to
    ``portfolio_io.compute_weights()`` — no shares×price re-computation from a
    JSON file here, and no second denominator computation.
    """
    sys.path.insert(0, str(PY_SERVICES))
    from portfolio_io import load_portfolio_state, compute_weights

    state = load_portfolio_state(None)  # path arg retained for compat, unused
    return compute_weights(state["shares"], state["prices"], state["total_usd"])


def assign_action(
    ticker: str,
    actual_pct: float,
    recommended_pct: float,
    current_action: str,
    threshold: float,
) -> tuple[str, str]:
    """Return (new_action, reason)."""

    # Preserve explicit EXIT — thesis breaker, not weight-driven
    if current_action == "EXIT":
        return "EXIT", "thesis breaker — preserved"

    held = actual_pct > 0
    delta = recommended_pct - actual_pct  # positive = need to buy more

    if not held:
        if recommended_pct > 0 and delta > 0:
            return "INITIATE", f"not held, target={recommended_pct:.2f}%"
        else:
            return "WATCHLIST", f"not held, no buy signal"

    # Held — compare actual vs recommended
    if delta > threshold:
        return "ACCUMULATE", f"held {actual_pct:.2f}% → target {recommended_pct:.2f}% (+{delta:.2f}pp)"
    elif delta < -threshold:
        return "TRIM", f"held {actual_pct:.2f}% → target {recommended_pct:.2f}% ({delta:.2f}pp)"
    else:
        return "MAINTAIN", f"held {actual_pct:.2f}% ≈ target {recommended_pct:.2f}% (within {threshold}pp)"


def main():
    parser = argparse.ArgumentParser(description="Re-label recommendation actions based on actual holdings")
    parser.add_argument("--recs", required=True, help="Path to recommendations JSON file")
    parser.add_argument("--portfolio", default=str(DEFAULT_PORTFOLIO),
                        help="Legacy portfolio.json path; kept for CLI back-compat. "
                             "Actual holdings now come from domain_model.sqlite.")
    parser.add_argument("--threshold", type=float, default=MAINTAIN_THRESHOLD,
                        help=f"pp band within which position is MAINTAIN (default {MAINTAIN_THRESHOLD})")
    parser.add_argument("--dry-run", action="store_true", help="Print changes without writing")
    args = parser.parse_args()

    recs_path = Path(args.recs)

    if not recs_path.exists():
        print(f"❌ Recommendations file not found: {recs_path}", file=sys.stderr)
        sys.exit(1)

    with open(recs_path) as f:
        recs = json.load(f)

    # Build actual pct map from domain_model.sqlite (Wave 3 cutover, ADR-030)
    actual_pct_map = build_actual_pct_map()

    print(f"\n{'TICKER':<8} {'ACTUAL%':>8} {'REC_TGT%':>9} {'DELTA':>7}  {'OLD':<14} {'NEW':<14} NOTE")
    print("─" * 90)

    changes = 0
    for holding in recs.get("holdings", []):
        ticker = holding["ticker"]
        rec_target = holding.get("recommendedTarget", holding.get("currentTarget", 0))
        actual_pct = actual_pct_map.get(ticker, 0.0)
        old_action = holding.get("action", "")
        delta = rec_target - actual_pct

        new_action, reason = assign_action(ticker, actual_pct, rec_target, old_action, args.threshold)

        changed = "✏️ " if new_action != old_action else "   "
        if new_action != old_action:
            changes += 1
        print(f"{ticker:<8} {actual_pct:>8.2f} {rec_target:>9.2f} {delta:>+7.2f}  {old_action:<14} {new_action:<14} {changed}{reason}")

        if not args.dry_run:
            holding["action"] = new_action
            holding["actualPct"] = round(actual_pct, 4)
            holding["actualDelta"] = round(rec_target - actual_pct, 4)

    print(f"\n{changes} action(s) relabeled")

    if args.dry_run:
        print("(dry-run — no file written)")
    else:
        with open(recs_path, "w") as f:
            json.dump(recs, f, indent=2)
        print(f"✅ Written: {recs_path}")


if __name__ == "__main__":
    main()
