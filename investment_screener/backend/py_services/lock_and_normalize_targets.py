#!/usr/bin/env python3
"""
lock_and_normalize_targets.py - Precision target weight modifier with locks and custom adjusts.

Purpose:
    Reads the current target weights from domain_model.sqlite, then:
    1. zeroes the tickers in --zeros,
    2. locks the TICKER=WEIGHT pairs in --locks,
    3. applies the TICKER=WEIGHT pairs in --adjusts,
    4. rescales the remaining unlocked, non-zero tickers so the whole book sums to exactly 100%.
    Nothing is written without --write; with --write the weights are saved to
    investment.target_weight and one portfolio_change_log entry is recorded.
    Compliant with Gate 7 actual broker-weight locks and the Aschenbrenner 13F exit adjustments.

Layer:
    Backend / Python Services

Usage Examples:
    python3 lock_and_normalize_targets.py --zeros INTC --locks GOOG=25 --adjusts MSFT=15
    python3 lock_and_normalize_targets.py --zeros INTC,BE --write
    python3 lock_and_normalize_targets.py --locks AAPL=10 --db /path/to/domain_model.sqlite

Key Functions (Index):
    - save_weights(): save the final weights and record the change
    - parse_pairs(): TICKER=WEIGHT strings to a dict
    - parse_tickers(): ticker strings to a set
    - main(): command line

Key Input Dependencies:
    - investment_screener/backend/data/domain_model.sqlite (--db): current target weights

Key Output Dependencies:
    - investment.target_weight and portfolio_change_log (only with --write)
"""
import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "investment_screener" / "backend" / "py_services"))
from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.investment_repository import (  # noqa: E402
    list_investments,
    resolve_investment,
    update_investment_fields,
)
from domain_model.portfolio_change_log_repository import record_change  # noqa: E402
from portfolio_io import load_thesis_holdings  # noqa: E402

DB_PATH = REPO_ROOT / "investment_screener" / "backend" / "data" / "domain_model.sqlite"


def save_weights(weights: dict[str, float], note: str, db_path: Path = DB_PATH) -> None:
    """Save each ticker's final weight to ``investment.target_weight`` and record one change-log entry."""
    conn = initialize_db(str(db_path))
    try:
        for ticker, weight in weights.items():
            update_investment_fields(conn, resolve_investment(conn, ticker), target_weight=weight)
        record_change(conn, note)
    finally:
        conn.close()


def parse_pairs(args_list: list[str] | None) -> dict[str, float]:
    """Parse a list of TICKER=WEIGHT strings (comma or space separated) into a dict."""
    if not args_list:
        return {}
    res = {}
    for item in args_list:
        for part in item.split(","):
            if not part.strip():
                continue
            if "=" not in part:
                print(f"ERROR: Invalid pair '{part}' (format: TICKER=WEIGHT)", file=sys.stderr)
                sys.exit(1)
            t, w = part.split("=", 1)
            res[t.strip().upper()] = float(w.strip())
    return res


def parse_tickers(args_list: list[str] | None) -> set[str]:
    """Parse a list of ticker strings (comma or space separated) into a set."""
    if not args_list:
        return set()
    return {part.strip().upper() for item in args_list for part in item.split(",") if part.strip()}


def _fail(message: str) -> None:
    """Print an error to stderr and exit 1."""
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(1)


def _redistribute(current: dict[str, float], set_weights: dict[str, float]) -> dict[str, float]:
    """Final weights: the explicit ones, plus the unlocked non-zero tickers scaled to fill the rest of 100."""
    remaining = 100.0 - sum(set_weights.values())
    unlocked = {t: w for t, w in current.items() if t not in set_weights and w > 0}
    final = dict(current)
    final.update(set_weights)
    print("\n-- Target Sizing & Locking ---------------------")
    print(f"  Sum of locked/adjusted targets: {sum(set_weights.values()):.4f}%")
    print(f"  Remaining weight to distribute: {remaining:.4f}%")
    if unlocked and remaining > 0:
        factor = remaining / sum(unlocked.values())
        print(f"  Normalization multiplier for unlocked: {factor:.6f}")
        for ticker, old in unlocked.items():
            final[ticker] = round(old * factor, 4)
            print(f"  ~ {ticker:<8} {old:>10.4f}% -> {final[ticker]:.4f}% (normalized)")
    elif remaining > 0:
        print("  WARNING: No unlocked non-zero tickers found to absorb remaining weight!", file=sys.stderr)
    return final


def main():
    """Command line entry point."""
    parser = argparse.ArgumentParser(description="Precision target weight modifier with locking and normalisation.")
    parser.add_argument("--zeros", nargs="*", help="Tickers to set to 0.0% target weight (comma/space-separated)")
    parser.add_argument("--locks", nargs="*", help="Locked TICKER=WEIGHT pairs (comma/space-separated)")
    parser.add_argument("--adjusts", nargs="*", help="Adjusted TICKER=WEIGHT pairs (comma/space-separated)")
    parser.add_argument("--write", action="store_true", help="Save to investment.target_weight and log the change")
    parser.add_argument("--db", default=str(DB_PATH), help="Path to domain_model.sqlite")
    args = parser.parse_args()

    zeros, locks, adjusts = parse_tickers(args.zeros), parse_pairs(args.locks), parse_pairs(args.adjusts)
    if not (zeros or locks or adjusts):
        _fail("nothing to change: pass --zeros, --locks and/or --adjusts")
    if not Path(args.db).exists():
        _fail(f"database not found: {args.db}")

    set_weights = {t: 0.0 for t in zeros}
    set_weights.update(locks)
    set_weights.update(adjusts)
    if sum(set_weights.values()) > 100.0:
        _fail(f"Sum of locked/adjusted weights ({sum(set_weights.values()):.4f}%) exceeds 100.0%")

    conn = initialize_db(args.db)
    try:
        known = {row["symbol"] for row in list_investments(conn)}
    finally:
        conn.close()
    unknown = sorted(set(set_weights) - known)
    if unknown:
        _fail(f"unknown ticker(s) not in domain_model.sqlite: {', '.join(unknown)}")

    current = {h["ticker"]: float(h["targetWeight"] or 0) for h in load_thesis_holdings(args.db)}
    final = _redistribute(current, set_weights)
    print(f"\n  Final target sum: {sum(final.values()):.4f}%")

    if args.write:
        note = f"lock_and_normalize_targets.py: zeros={sorted(zeros)} locks={locks} adjusts={adjusts}"
        save_weights(final, note, Path(args.db))
        print(f"Wrote normalised weights to {args.db} (investment.target_weight)")
    else:
        print("  [DRY RUN - pass --write to persist changes]")


if __name__ == "__main__":
    main()
