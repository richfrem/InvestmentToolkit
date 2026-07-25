#!/usr/bin/env python3
"""
validate_weights.py — Portfolio weight validator and normaliser.

Two independent computations:
  --mode current  → reads portfolio.json (actual broker holdings)
                    computes shares×price / total for each holding
                    reports sum and per-holding actual %
  --mode target   → reads target-portfolio.json (thesis targets)
                    sums targetWeight fields
                    reports sum and per-holding target %
  --mode both     → runs both and returns combined JSON (default)

  --normalize     → rescale targetWeight values in target-portfolio.json
                    so they sum to exactly 100%, then write the file

Usage:
  python3 validate_weights.py                         # dry-run both, JSON to stdout
  python3 validate_weights.py --mode current          # current holdings only
  python3 validate_weights.py --mode target           # target weights only
  python3 validate_weights.py --normalize --write     # fix and write target-portfolio.json
"""

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT     = Path(__file__).resolve().parents[3]
TARGET_JSON      = REPO_ROOT / "investment_screener/backend/data/theses/target-portfolio.json"
DB_PATH          = REPO_ROOT / "investment_screener/backend/data/domain_model.sqlite"

sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))
from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.investment_repository import (  # noqa: E402
    resolve_investment,
    update_investment_fields,
)


# ---------------------------------------------------------------------------
# Current holdings — computed from portfolio.json (market_value / total)
#
# Denominator mirrors the canonical TS computeWeightsMap() in portfolioSnapshot.ts:
# prefer the persisted totals.totalUSD (TV-broker-authoritative when available —
# see buildPortfolioSnapshot/preserveAuthoritativeTotal) over a locally recomputed
# sum(shares*price), which can diverge (missing cash, stale pricing). Cross-language
# parity is enforced by test_compute_current_weights.py.
# ---------------------------------------------------------------------------
def compute_current(portfolio_path: Path) -> dict:
    with open(portfolio_path) as f:
        raw = json.load(f)
    holdings = raw if isinstance(raw, list) else raw.get("holdings", [])
    totals = {} if isinstance(raw, list) else (raw.get("totals") or {})

    def market_value(h: dict) -> float:
        return h.get("shares", 0) * h.get("price", 0)

    persisted_total = totals.get("totalUSD", 0) or 0
    total_value = persisted_total if persisted_total > 0 else sum(market_value(h) for h in holdings)
    if total_value == 0:
        return {"total": 0.0, "holdings": {}, "total_value": 0.0}

    result: dict[str, float] = {}
    for h in holdings:
        sym = h.get("symbol") or h.get("ticker")
        if not sym:
            continue
        result[sym] = round(market_value(h) / total_value * 100, 4)

    total = round(sum(result.values()), 4)
    return {"total": total, "holdings": result, "total_value": round(total_value, 2)}


# ---------------------------------------------------------------------------
# Current holdings — computed live from domain_model.sqlite (Wave 7)
#
# Real bug this replaces: main()'s --portfolio arg defaulted to the real
# investment_screener/backend/data/portfolio.json, which Wave 3 stopped
# writing entirely once sync cut over to SQLite-only writes — every run of
# `validate_weights.py` (--mode current/both, the default) without an
# explicit --portfolio override silently computed weights against a frozen,
# increasingly stale snapshot. compute_current() itself is unchanged (still
# used by its own isolated fixture-based test suite via explicit --portfolio
# overrides) — only main()'s no-override default now calls this instead.
# ---------------------------------------------------------------------------
def compute_current_from_db(db_path: Path) -> dict:
    # portfolio_io.load_portfolio_state()'s own path param is documented as
    # unused (always reads its own hardcoded default DB file) -- call the
    # lower-level, real-path-respecting function directly instead so this
    # honors the --db argument rather than silently reading the real,
    # production domain_model.sqlite regardless of what path was requested.
    from domain_model.db_client import initialize_db
    from domain_model.portfolio_repository import load_portfolio_state_from_db

    conn = initialize_db(str(db_path))
    try:
        state = load_portfolio_state_from_db(conn)
    finally:
        conn.close()
    shares = state["shares"]
    prices = state["prices"]
    total_value = state["total_usd"]
    if total_value == 0:
        return {"total": 0.0, "holdings": {}, "total_value": 0.0}

    result: dict[str, float] = {}
    for sym, qty in shares.items():
        px = prices.get(sym, 0)
        result[sym] = round(qty * px / total_value * 100, 4)

    total = round(sum(result.values()), 4)
    return {"total": total, "holdings": result, "total_value": round(total_value, 2)}


# ---------------------------------------------------------------------------
# Target weights — summed from target-portfolio.json targetWeight fields
# ---------------------------------------------------------------------------
def compute_target(target_path: Path) -> dict:
    with open(target_path) as f:
        data = json.load(f)

    result = {}
    for h in data.get("holdings", []):
        ticker = h["ticker"]
        weight = h.get("targetWeight", 0) or 0
        if weight > 0:
            result[ticker] = round(weight, 4)

    total = round(sum(result.values()), 4)
    return {"total": total, "holdings": result}


# ---------------------------------------------------------------------------
# Normalise target weights so they sum to exactly 100%
# ---------------------------------------------------------------------------
def normalize_target(target_path: Path) -> tuple:
    with open(target_path) as f:
        data = json.load(f)

    total = sum(h.get("targetWeight", 0) or 0 for h in data["holdings"])
    if total == 0:
        print("ERROR: all targetWeights are 0 — nothing to normalize", file=sys.stderr)
        sys.exit(1)

    factor = 100.0 / total
    for h in data["holdings"]:
        w = h.get("targetWeight", 0) or 0
        if w > 0:
            h["targetWeight"] = round(w * factor, 4)

    new_total = sum(h.get("targetWeight", 0) or 0 for h in data["holdings"])
    return data, round(new_total, 4)


def write_normalized_weights_to_db(data: dict, db_path: Path = DB_PATH) -> None:
    """Persist normalised ``targetWeight`` values via the domain-model repository.

    Replaces the old direct-JSON-write path (Wave 2 Task 9 producer cutover):
    every holding's rescaled targetWeight is written to
    ``investment.target_weight`` via ``update_investment_fields`` instead of
    rewriting target-portfolio.json in place.
    """
    conn = initialize_db(str(db_path))
    try:
        for h in data["holdings"]:
            ticker = h["ticker"]
            weight = h.get("targetWeight", 0) or 0
            investment_id = resolve_investment(conn, ticker)
            update_investment_fields(conn, investment_id, target_weight=weight)
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Validate and normalise portfolio weights")
    parser.add_argument("--mode",      choices=["current", "target", "both"], default="both")
    parser.add_argument("--normalize", action="store_true", help="Rescale targetWeights to sum to 100%")
    parser.add_argument("--write",     action="store_true", help="Write normalised weights back to target-portfolio.json")
    parser.add_argument(
        "--portfolio", default=None,
        help="Optional: compute current-holdings weights from this portfolio.json "
             "fixture instead of live domain_model.sqlite (tests only — production "
             "runs should omit this and let --mode current/both read SQLite).",
    )
    parser.add_argument("--target",    default=str(TARGET_JSON))
    parser.add_argument("--db",        default=str(DB_PATH), help="Path to domain_model.sqlite")
    args = parser.parse_args()

    output = {}

    if args.normalize:
        normalised_data, new_total = normalize_target(Path(args.target))
        if args.write:
            write_normalized_weights_to_db(normalised_data, Path(args.db))
            print(
                f"✅ Wrote normalised weights to {args.db} (investment.target_weight, "
                f"sum={new_total:.4f}%)",
                file=sys.stderr,
            )
        output["normalised_total"] = new_total
        output["target"] = compute_target(Path(args.target))
    else:
        if args.mode in ("current", "both"):
            output["current"] = (
                compute_current(Path(args.portfolio)) if args.portfolio
                else compute_current_from_db(Path(args.db))
            )
        if args.mode in ("target", "both"):
            output["target"] = compute_target(Path(args.target))

    print(json.dumps(output))


if __name__ == "__main__":
    main()
