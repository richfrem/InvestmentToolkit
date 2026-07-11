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

Key Input Dependencies:
    - investment_screener/backend/data/portfolio.json (Internal state database)
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


def derive_action(ticker: str, current_pct: float, target_pct: float, ai_upside: float | None = None) -> str:
    """Pure function: derives portfolio action from weights + optional pre-computed AI upside.

    ai_upside: caller-supplied upside % from the latest AI projection (pass None to skip override).
    """
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

    # AI CONFLICT OVERRIDE: if formula says EXIT/TRIM but AI has >10% upside, flag REVIEW.
    if action in ("EXIT", "TRIM") and ticker != "_meta" and ai_upside is not None and ai_upside > 10:
        return "REVIEW"

    return action


def _load_ai_upside(ticker: str, projections_dir) -> float | None:
    """Load latest AI projection upside for ticker. Returns None on any failure."""
    try:
        from pathlib import Path
        import json
        proj_path = Path(projections_dir) / f"{ticker}.json"
        if not proj_path.exists():
            return None
        with open(proj_path) as f:
            projs = json.load(f)
        if isinstance(projs, list):
            if not projs:
                return None
            ai = [p for p in projs if p.get("source") == "AI_AGENT"]
            proj: dict = max(ai, key=lambda x: x.get("savedAt", "")) if ai else projs[0]
        else:
            proj = projs
        pf = proj.get("aiThesis", {})
        sn = proj.get("snapshot", {})
        if pf.get("action") in ("BUY", "ACCUMULATE", "INITIATE"):
            fv = pf.get("fairValue")
            curr = sn.get("price") or pf.get("currentPrice")
            if fv and curr and curr > 0:
                return ((fv - curr) / curr) * 100
    except Exception:
        pass
    return None


if __name__ == "__main__":
    import argparse, json, sys
    from pathlib import Path

    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true", required=True)
    parser.add_argument("--portfolio", required=True)
    parser.add_argument("--target", required=True)
    args = parser.parse_args()

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from validate_weights import compute_current, compute_target

    ch = compute_current(args.portfolio)["holdings"]
    th = compute_target(args.target)["holdings"]
    all_tickers = set(list(ch.keys()) + list(th.keys()))

    projections_dir = Path(__file__).resolve().parents[3] / "investment_screener/backend/data/projections"
    result = {
        t: derive_action(t, ch.get(t, 0.0), th.get(t, 0.0), ai_upside=_load_ai_upside(t, projections_dir))
        for t in all_tickers
    }
    print(json.dumps(result))
