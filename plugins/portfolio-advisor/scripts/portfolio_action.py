"""
portfolio_action.py — Canonical action label logic.

Single source of truth for deriving portfolio actions from current % vs target %.
Used by generate_portfolio_blueprint.py, validate_weights.py, and the backend API.
The frontend must never recompute actions — it receives them from the backend.

Rules:
  current=0, target=0  → WATCHLIST
  current=0, target>0  → INITIATE
  current>0, target=0  → EXIT
  current>0, target>0, ratio < 0.85  → ACCUMULATE
  current>0, target>0, ratio > 1.15  → TRIM
  current>0, target>0                → MAINTAIN

CLI usage (called by backend):
  python3 portfolio_action.py --all --portfolio <path> --target <path>
  → prints JSON: { "ZS": "TRIM", "INTC": "MAINTAIN", ... }
"""

ACTION_EMOJI = {
    "INITIATE":   "🟢",
    "ACCUMULATE": "🔵",
    "MAINTAIN":   "⚪",
    "TRIM":       "🟡",
    "EXIT":       "🔴",
    "WATCHLIST":  "👁️",
}


def derive_action(current_pct: float, target_pct: float) -> str:
    c = current_pct or 0.0
    t = target_pct  or 0.0
    if c == 0 and t == 0:
        return "WATCHLIST"
    if c == 0 and t > 0:
        return "INITIATE"
    if c > 0 and t == 0:
        return "EXIT"
    ratio = c / t
    if ratio < 0.85:
        return "ACCUMULATE"
    if ratio > 1.15:
        return "TRIM"
    return "MAINTAIN"


if __name__ == "__main__":
    import argparse, json, sys
    from pathlib import Path

    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true", required=True)
    parser.add_argument("--portfolio", required=True)
    parser.add_argument("--target", required=True)
    args = parser.parse_args()

    sys.path.insert(0, str(Path(__file__).parent))
    from validate_weights import compute_current, compute_target

    ch = compute_current(args.portfolio)["holdings"]
    th = compute_target(args.target)["holdings"]
    all_tickers = set(list(ch.keys()) + list(th.keys()))
    result = {t: derive_action(ch.get(t, 0.0), th.get(t, 0.0)) for t in all_tickers}
    print(json.dumps(result))
