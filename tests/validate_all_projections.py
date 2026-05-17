#!/usr/bin/env python3
"""
validate_all_projections.py — DCF projection consistency checker.

Three hard-fail validations per projection file:
  1. Scenario weights sum to 1.0
  2. Stored aiThesis.action matches derived valuation signal (BUY/HOLD/SELL only)
  3. Stored aiThesis.fairValue matches recomputed weighted scenario price

Usage:
    python3 tests/validate_all_projections.py                      # validate all projections
    python3 tests/validate_all_projections.py --file path/to.json  # validate single file
    python3 tests/validate_all_projections.py --dir path/to/dir    # validate directory
"""

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PROJECTIONS_DIR = REPO_ROOT / "investment_screener/backend/data/projections"

FAIL = "\033[91m[FAIL]\033[0m"
PASS_MARK = "\033[92m[PASS]\033[0m"
WARN = "\033[93m[WARN]\033[0m"
SKIP = "\033[90m[SKIP]\033[0m"


def derive_valuation_signal(upside_pct: float) -> str:
    """Pure DCF valuation signal using analysis_prompt.md thresholds.

    Uses ±15% bands. NOT apply_catalyst.py action bands — those are different systems.
    """
    if upside_pct >= 15:
        return "BUY"
    if upside_pct >= -15:
        return "HOLD"
    return "SELL"


def validate_projection(proj: dict, source_file: Path) -> list[str]:
    """Run three hard-fail validations on one projection entry. Returns list of error strings."""
    errors: list[str] = []
    ticker = proj.get("ticker", source_file.stem)
    scenarios: dict = proj.get("scenarios", {})
    ai_thesis: dict = proj.get("aiThesis", {})
    snapshot: dict = proj.get("snapshot", {})

    # ── Validation 1: Scenario weights sum to 1.0 ──────────────────────────
    weights = [v.get("weight", 0) for v in scenarios.values() if isinstance(v, dict)]
    if weights:
        total_weight = sum(weights)
        if abs(total_weight - 1.0) > 0.001:
            errors.append(
                f"  [weights] {ticker}: scenario weights sum to {total_weight:.4f}, expected 1.0"
            )

    # ── Validation 2: action vs derived signal ─────────────────────────────
    stored_action = ai_thesis.get("action", "")
    if stored_action in ("BUY", "HOLD", "SELL"):
        stored_fv = ai_thesis.get("fairValue")
        current_price = snapshot.get("price")
        if stored_fv is not None and current_price and current_price > 0:
            upside_pct = (stored_fv - current_price) / current_price * 100
            expected_action = derive_valuation_signal(upside_pct)
            if expected_action != stored_action:
                errors.append(
                    f"  [action]  {ticker}: stored='{stored_action}' but "
                    f"derive_valuation_signal({upside_pct:.1f}%)='{expected_action}' "
                    f"(fv={stored_fv}, price={current_price})"
                )
        elif stored_action in ("BUY", "HOLD", "SELL"):
            # Can't verify without price/fv — warn but don't fail
            pass

    # ── Validation 3: stored fairValue vs recomputed weighted FV ───────────
    stored_fv = ai_thesis.get("fairValue")
    if stored_fv is not None and scenarios:
        computed_fv = sum(
            v.get("weight", 0) * v.get("scenarioPrice", 0)
            for v in scenarios.values()
            if isinstance(v, dict)
        )
        if abs(stored_fv - computed_fv) > 0.50:
            errors.append(
                f"  [fairval] {ticker}: stored fairValue={stored_fv:.2f} but "
                f"recomputed={computed_fv:.2f} (delta={abs(stored_fv - computed_fv):.2f})"
            )

    return errors


def validate_file(path: Path) -> tuple[int, int]:
    """Validate all projection entries in a file. Returns (pass_count, fail_count)."""
    try:
        with open(path) as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"{FAIL} {path.name}: cannot parse — {e}")
        return 0, 1

    entries = data if isinstance(data, list) else [data]
    passed = 0
    failed = 0

    for proj in entries:
        ticker = proj.get("ticker", path.stem)
        errors = validate_projection(proj, path)
        if errors:
            print(f"{FAIL} {ticker} ({path.name})")
            for err in errors:
                print(err)
            failed += 1
        else:
            passed += 1

    return passed, failed


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate DCF projection files")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--file", type=Path, help="Validate a single projection file")
    group.add_argument("--dir",  type=Path, help="Validate all .json files in directory")
    args = parser.parse_args()

    if args.file:
        files = [args.file]
    elif args.dir:
        files = sorted(args.dir.glob("*.json"))
    else:
        files = sorted(DEFAULT_PROJECTIONS_DIR.glob("*.json"))

    if not files:
        print(f"No projection files found.")
        sys.exit(0)

    total_pass = 0
    total_fail = 0
    for f in files:
        p, fail = validate_file(f)
        total_pass += p
        total_fail += fail

    print(f"\n{'─' * 50}")
    print(f"Projections validated: {total_pass + total_fail}")
    print(f"  {PASS_MARK} passed: {total_pass}")
    if total_fail:
        print(f"  {FAIL} failed: {total_fail}")
        sys.exit(1)
    else:
        print(f"\n\033[92mAll projections consistent.\033[0m")


if __name__ == "__main__":
    main()
