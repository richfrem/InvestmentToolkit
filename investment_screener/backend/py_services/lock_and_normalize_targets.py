#!/usr/bin/env python3
"""
lock_and_normalize_targets.py - Python utility script.

Purpose:
    lock_and_normalize_targets.py — Precision target weight modifier with support for locks and custom adjusts.

Designed to:
1. Zero out specified tickers.
2. Lock specified tickers to exact target weights.
3. Apply custom adjusted weights to certain tickers.
4. Auto-normalize the REMAINING unlocked non-zero tickers so the entire portfolio sums to exactly 100.0%.

This is compliant with Gate 7 actual broker-weight locks and the Aschenbrenner 13F exit adjustments.

Key Input Dependencies:
    - investment_screener/backend/data/theses/target-portfolio.json (Locks weights)

Layer:
    Backend / Python Services

Usage Examples:
    TBD

Key Functions (Index):
    - load_portfolio()
    - save_portfolio()
    - parse_pairs()
    - parse_tickers()
    - main()

Key Input Dependencies:
    None

Key Output Dependencies:
    None
"""
import argparse
import json
import sys
from pathlib import Path

# Add root directory to sys.path so we can import domain_model repositories
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "investment_screener" / "backend" / "py_services"))
from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.investment_repository import (  # noqa: E402
    resolve_investment,
    update_investment_fields,
)

DB_PATH = REPO_ROOT / "investment_screener" / "backend" / "data" / "domain_model.sqlite"

def load_portfolio(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)

def save_portfolio(data: dict, db_path: Path = DB_PATH) -> None:
    """Persist each holding's rescaled ``targetWeight`` via the domain-model
    repository (``investment.target_weight``) instead of rewriting
    target-portfolio.json in place (Wave 2 Task 10 producer cutover).
    """
    conn = initialize_db(str(db_path))
    try:
        for h in data["holdings"]:
            investment_id = resolve_investment(conn, h["ticker"])
            weight = h.get("targetWeight", 0) or 0
            update_investment_fields(conn, investment_id, target_weight=weight)
    finally:
        conn.close()

def parse_pairs(args_list: list[str] | None) -> dict[str, float]:
    """Parse list of TICKER=WEIGHT strings into a dict."""
    if not args_list:
        return {}
    res = {}
    for item in args_list:
        # Support comma-separated or space-separated list
        parts = item.split(",")
        for part in parts:
            if not part.strip():
                continue
            if "=" not in part:
                print(f"ERROR: Invalid pair '{part}' (format: TICKER=WEIGHT)", file=sys.stderr)
                sys.exit(1)
            t, w = part.split("=", 1)
            res[t.strip().upper()] = float(w.strip())
    return res

def parse_tickers(args_list: list[str] | None) -> set[str]:
    """Parse list of TICKER strings into a set."""
    if not args_list:
        return set()
    res = set()
    for item in args_list:
        parts = item.split(",")
        for part in parts:
            if part.strip():
                res.add(part.strip().upper())
    return res

def main():
    parser = argparse.ArgumentParser(description="Precision target weight modifier with locking and normalisation.")
    parser.add_argument("--target-file", required=True, help="Path to target-portfolio.json")
    parser.add_argument("--zeros", nargs="*", help="List of tickers to set to 0.0% target weight (comma/space-separated)")
    parser.add_argument("--locks", nargs="*", help="List of locked TICKER=WEIGHT pairs (comma/space-separated)")
    parser.add_argument("--adjusts", nargs="*", help="List of adjusted TICKER=WEIGHT pairs (comma/space-separated)")
    parser.add_argument("--write", action="store_true", help="Write changes to the target file")
    parser.add_argument("--db", default=str(DB_PATH), help="Path to domain_model.sqlite")

    args = parser.parse_args()

    target_path = Path(args.target_file)
    if not target_path.exists():
        print(f"ERROR: Target file {target_path} does not exist", file=sys.stderr)
        sys.exit(1)

    data = load_portfolio(target_path)
    zeros = parse_tickers(args.zeros)
    locks = parse_pairs(args.locks)
    adjusts = parse_pairs(args.adjusts)

    # 1. Apply zeros, locks, and adjusts first
    locked_keys = set(locks.keys())
    adjusted_keys = set(adjusts.keys())
    
    # We treat locks and adjusts as locked (their target weight is set and will not be normalized)
    set_weights = {}
    for t in zeros:
        set_weights[t] = 0.0
    for t, w in locks.items():
        set_weights[t] = w
    for t, w in adjusts.items():
        set_weights[t] = w

    sum_locked = sum(w for t, w in set_weights.items())
    remaining_weight = 100.0 - sum_locked

    if remaining_weight < 0:
        print(f"ERROR: Sum of locked/adjusted weights ({sum_locked:.4f}%) exceeds 100.0%", file=sys.stderr)
        sys.exit(1)

    # 2. Identify the unlocked, non-zero tickers
    unlocked_holdings = []
    sum_unlocked_current = 0.0

    for h in data["holdings"]:
        ticker = h["ticker"]
        # Apply the explicit set weights
        if ticker in set_weights:
            h["targetWeight"] = set_weights[ticker]
            # If set to 0, mark as speculative or untracked
            if set_weights[ticker] == 0.0:
                h["role"] = "untracked"
        else:
            # Ticker is unlocked
            w = h.get("targetWeight", 0) or 0
            if w > 0:
                unlocked_holdings.append(h)
                sum_unlocked_current += w

    # 3. Normalize the remaining unlocked tickers
    print("\n── Target Sizing & Locking ─────────────────────")
    print(f"  Sum of locked/adjusted targets: {sum_locked:.4f}%")
    print(f"  Remaining weight to distribute: {remaining_weight:.4f}%")
    
    if sum_unlocked_current > 0 and remaining_weight > 0:
        factor = remaining_weight / sum_unlocked_current
        print(f"  Normalization multiplier for unlocked: {factor:.6f}")
        for h in unlocked_holdings:
            old_w = h["targetWeight"]
            new_w = round(old_w * factor, 4)
            h["targetWeight"] = new_w
            print(f"  ~ {h['ticker']:<8} {old_w:>10.4f}% → {new_w:.4f}% (normalized)")
    elif remaining_weight > 0:
        print("  WARNING: No unlocked non-zero tickers found to absorb remaining weight!", file=sys.stderr)

    # Clean up roles
    for h in data["holdings"]:
        w = h.get("targetWeight", 0) or 0
        if w == 0.0:
            h["role"] = "untracked"

    # Verify total sum
    total_sum = sum(h.get("targetWeight", 0) or 0 for h in data["holdings"])
    print(f"\n  Final target sum: {total_sum:.4f}%")

    if args.write:
        save_portfolio(data, Path(args.db))
        print(f"✅ Wrote normalised weights to {args.db} (investment.target_weight)!")
    else:
        print("  [DRY RUN — pass --write to persist changes]")

if __name__ == "__main__":
    main()
