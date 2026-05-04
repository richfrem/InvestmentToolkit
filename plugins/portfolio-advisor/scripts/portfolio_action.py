"""
portfolio_action.py — Canonical action label logic.

Single source of truth for deriving portfolio actions from current % vs target %.
Used by generate_portfolio_blueprint.py, validate_weights.py, and the backend API.
The frontend must never recompute actions — it receives them from the backend.

Rules:
  current=0, target=0  → WATCHLIST
  current=0, target>0  → INITIATE
  current>0, target=0  → EXIT (or REVIEW if AI Upside > 10%)
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
    "REVIEW":     "🔥",
}


def derive_action(ticker: str, current_pct: float, target_pct: float) -> str:
    c = current_pct or 0.0
    t = target_pct  or 0.0
    
    action = "MAINTAIN"
    if c == 0 and t == 0:
        action = "WATCHLIST"
    elif c == 0 and t > 0:
        action = "INITIATE"
    elif c > 0 and t == 0:
        action = "EXIT"
    else:
        ratio = c / t
        if ratio < 0.85:
            action = "ACCUMULATE"
        elif ratio > 1.15:
            action = "TRIM"
            
    # --- AI CONFLICT OVERRIDE ---
    # If the thesis formula says EXIT or TRIM, but the AI says BUY with > 10% upside,
    # override to REVIEW to prevent blindly dumping massive AI conviction.
    if action in ("EXIT", "TRIM") and ticker != "_meta":
        try:
            from pathlib import Path
            import json
            proj_path = Path(__file__).resolve().parents[3] / f"investment_screener/backend/data/projections/{ticker}.json"
            if proj_path.exists():
                with open(proj_path) as f:
                    projs = json.load(f)
                    if isinstance(projs, list) and len(projs) > 0:
                        ai = [p for p in projs if p.get("source") == "AI_AGENT"]
                        proj = max(ai, key=lambda x: x.get("savedAt", "")) if ai else projs[0]
                    else:
                        proj = projs
                        
                    pf = proj.get("aiThesis", {})
                    sn = proj.get("snapshot", {})
                    if pf.get("action") in ("BUY", "ACCUMULATE", "INITIATE"):
                        fv = pf.get("fairValue")
                        curr = sn.get("price") or pf.get("currentPrice")
                        if fv and curr and curr > 0:
                            upside = ((fv - curr) / curr) * 100
                            if upside > 10:
                                return "REVIEW"
        except Exception:
            pass
            
    return action


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
    result = {t: derive_action(t, ch.get(t, 0.0), th.get(t, 0.0)) for t in all_tickers}
    print(json.dumps(result))
