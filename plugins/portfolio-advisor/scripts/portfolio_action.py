"""
portfolio_action.py — Compatibility shim over the canonical recommendation.

The one implementation of TRIM / EXIT / ACCUMULATE / INITIATE / MAINTAIN /
WATCHLIST lives in recommendation.py (valuation + explicit exit signal; target
weights play no part because recommendations come BEFORE targets). This module
only keeps the long-standing ``derive_action`` call signature and CLI so the
backend and report scripts keep working. The frontend must never recompute actions.

CLI usage (called by backend):
  python3 portfolio_action.py --all --portfolio <path> --target <path>
  -> prints JSON: { "ZS": "TRIM", "INTC": "WATCHLIST", ... }

Key Input Dependencies:
    - recommendation.py (canonical logic)
    - investment_screener/backend/data/domain_model.sqlite
"""
import sys
from functools import lru_cache
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from recommendation import ACTION_EMOJI, recommend, recommend_all  # noqa: E402,F401


@lru_cache(maxsize=4)
def _records(db_path: str | None) -> dict:
    """Canonical per-ticker recommendation records (cached per process)."""
    return recommend_all(db_path)


def derive_action(ticker: str, current_pct: float, target_pct: float | None = None,
                  ai_upside: float | None = None, db_path: str | None = None) -> str:
    """Return the canonical action for ``ticker``.

    ``target_pct`` is accepted for call-site compatibility and ignored.
    Pass ``ai_upside`` to decide purely from a caller-supplied upside; otherwise
    the latest projection and holdings are read from domain_model.sqlite.
    """
    held = (current_pct or 0.0) > 0
    if ai_upside is not None:
        return recommend(held, ai_upside)["action"]
    rec = _records(db_path).get(ticker)
    return rec["action"] if rec else recommend(held, None)["action"]


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
    parser.add_argument(
        "--portfolio", required=True,
        help="Legacy portfolio.json path, kept for CLI back-compat; no longer "
             "read directly. Actual holdings now come from domain_model.sqlite.",
    )
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
        help="Path to domain_model.sqlite (source of holdings, target weights + AI upside).",
    )
    args = parser.parse_args()

    print(json.dumps({t: r["action"] for t, r in recommend_all(args.db).items()}))
