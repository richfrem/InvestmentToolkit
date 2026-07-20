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


def _load_ai_upside(ticker: str, db_path) -> float | None:
    """Load latest AI projection upside for ticker. Returns None on any failure.

    Storage backend (Wave 1 Task 7A): reads `projection_version` via
    `domain_model.projection_repository`, not `projections/{TICKER}.json`
    directly (ADR-029). Prefers the latest `AI_AGENT`-sourced row
    (`get_latest_projection_by_source`) over plain `MAX(version)` (Task 6
    finding: version numbers are not always chronological), falling back to
    `get_latest_projection` (any source) when no `AI_AGENT` row exists —
    mirroring the original file-based code's `projs[0]` fallback for a
    projection file with no `source == "AI_AGENT"` entry.
    """
    try:
        import json
        import sys
        from pathlib import Path

        sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "investment_screener/backend/py_services"))
        from domain_model.db_client import initialize_db
        from domain_model.projection_repository import get_latest_projection, get_latest_projection_by_source

        conn = initialize_db(str(db_path))
        try:
            row = conn.execute("SELECT investment_id FROM investment WHERE symbol = ?;", (ticker,)).fetchone()
            if row is None:
                return None
            investment_id = row[0]
            entry = get_latest_projection_by_source(conn, investment_id, "AI_AGENT")
            if entry is None:
                entry = get_latest_projection(conn, investment_id)
            if entry is None:
                return None
            snap = json.loads(entry["snapshot_json"]) if entry.get("snapshot_json") else {}
            if entry.get("action") in ("BUY", "ACCUMULATE", "INITIATE"):
                fv = entry.get("fair_value")
                curr = snap.get("price")
                if fv and curr and curr > 0:
                    return ((fv - curr) / curr) * 100
        finally:
            conn.close()
    except Exception:
        pass
    return None


def _load_target_weights(db_path) -> dict:
    """Load per-symbol target weights from ``investment.target_weight`` (Wave 2 rewire).

    Replaces the old ``validate_weights.compute_target(target_json)`` JSON read —
    target weights are now sourced from the domain-model repository
    (``investment_repository.list_investments``) instead of
    ``target-portfolio.json`` directly, mirroring the ``validate_weights.py``
    Task 9 write-path cutover on the read side.
    """
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "investment_screener/backend/py_services"))
    from domain_model.db_client import initialize_db
    from domain_model.investment_repository import list_investments

    conn = initialize_db(str(db_path))
    try:
        rows = list_investments(conn)
    finally:
        conn.close()

    result = {}
    for row in rows:
        weight = row.get("target_weight") or 0
        if weight and weight > 0:
            result[row["symbol"]] = round(weight, 4)
    return result


if __name__ == "__main__":
    import argparse, json, sys
    from pathlib import Path

    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true", required=True)
    parser.add_argument("--portfolio", required=True)
    parser.add_argument(
        "--target",
        required=True,
        help="Legacy target-portfolio.json path, kept for CLI back-compat; "
             "no longer read directly. Target weights now come from the "
             "domain-model sqlite DB (see --db).",
    )
    parser.add_argument(
        "--db",
        default=str(Path(__file__).resolve().parents[3] / "investment_screener/backend/data/domain_model.sqlite"),
        help="Path to domain_model.sqlite (source of target weights + AI upside).",
    )
    args = parser.parse_args()

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from validate_weights import compute_current

    ch = compute_current(args.portfolio)["holdings"]
    th = _load_target_weights(args.db)
    all_tickers = set(list(ch.keys()) + list(th.keys()))

    result = {
        t: derive_action(t, ch.get(t, 0.0), th.get(t, 0.0), ai_upside=_load_ai_upside(t, args.db))
        for t in all_tickers
    }
    print(json.dumps(result))
