#!/usr/bin/env python3
"""
verify_thesis_sync.py - Python utility script.

Purpose:
    verify_thesis_sync.py — Automated Portfolio & Thesis Synchronization Checker.

Performs three core sanity checks:
  1. Holding Mismatches: Every ticker in target-portfolio.json must be mentioned in investment_thesis.md.
  2. Valuation Projections: Every active ticker with a target weight > 0 or in an active role
     (core, hedge, speculative, reserve) must have a corresponding projection JSON.
  3. Total Weights Guard: Asserts that target weights sum to exactly 100% (within 0.1% tolerance).

Exits with 0 on success, 1 on failure.

Key Input Dependencies:
    - investment_screener/backend/data/portfolio.json (Audits thesis and holdings alignment)

Layer:
    Backend / Python Services

Usage Examples:
    TBD

Key Functions (Index):
    - main()
    - log_ok()
    - log_fail()
    - log_warn()

Key Input Dependencies:
    None

Key Output Dependencies:
    None
"""
import json
import re
import sys
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
PY_SERVICES_DIR = Path(__file__).resolve().parent
REPO_ROOT       = PY_SERVICES_DIR.parents[2]

THESIS_JSON = REPO_ROOT / "investment_screener" / "backend" / "data" / "theses" / "target-portfolio.json"
THESIS_MD   = REPO_ROOT / "investment_screener" / "backend" / "data" / "theses" / "investment_thesis.md"
PROJ_DIR    = REPO_ROOT / "investment_screener" / "backend" / "data" / "projections"

ACTIVE_ROLES = {"core", "hedge", "speculative", "reserve"}

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Automated Portfolio & Thesis Synchronization Checker")
    parser.add_argument("--thesis-json", type=str, help="Path to target-portfolio.json")
    parser.add_argument("--thesis-md", type=str, help="Path to investment_thesis.md")
    parser.add_argument("--projections-dir", type=str, help="Path to projections directory")
    args = parser.parse_args()

    thesis_json_path = Path(args.thesis_json) if args.thesis_json else THESIS_JSON
    thesis_md_path = Path(args.thesis_md) if args.thesis_md else THESIS_MD
    proj_dir_path = Path(args.projections_dir) if args.projections_dir else PROJ_DIR

    print("==================================================================")
    print("   Portfolio & Thesis Sync Verification Suite")
    print("==================================================================")
    print(f"Thesis JSON: {thesis_json_path}")
    print(f"Thesis MD:   {thesis_md_path}")
    print(f"Proj Dir:    {proj_dir_path}\n")

    errors = []
    warnings = []

    def log_ok(msg):
        print(f"  ✓ {msg}")

    def log_fail(msg):
        errors.append(msg)
        print(f"  ✗ ERROR: {msg}")

    def log_warn(msg):
        warnings.append(msg)
        print(f"  ⚠ WARNING: {msg}")

    # ── 1. Validate target-portfolio.json Existence & Weights ─────────────────
    print("Checking target-portfolio.json ground truth...")
    if not thesis_json_path.exists():
        log_fail(f"target-portfolio.json not found at {thesis_json_path}")
        sys.exit(1)

    try:
        with open(thesis_json_path) as f:
            thesis = json.load(f)
        log_ok("Successfully loaded target-portfolio.json")
    except Exception as e:
        log_fail(f"Failed to parse target-portfolio.json: {e}")
        sys.exit(1)

    holdings = thesis.get("holdings", [])
    log_ok(f"Found {len(holdings)} holdings in target portfolio.")

    # Sum weights
    total_weight = sum(h.get("targetWeight", 0) for h in holdings)
    if abs(total_weight - 100.0) > 0.1:
        log_fail(f"Total target weight sums to {total_weight:.4f}% (must be 100% ± 0.1%)")
    else:
        log_ok(f"Total target weight sums to {total_weight:.4f}% (within acceptable range)")

    # ── 2. Validate investment_thesis.md Mention ──────────────────────────────
    print("\nChecking investment_thesis.md and sub-strategies ticker alignment...")
    if not thesis_md_path.exists():
        log_fail(f"investment_thesis.md not found at {thesis_md_path}")
    else:
        try:
            md_text = thesis_md_path.read_text()
            
            # Optionally aggregate all sub-strategy markdown texts if directory exists
            sub_strategies_dir = thesis_md_path.parent / "sub_strategies"
            if sub_strategies_dir.exists() and sub_strategies_dir.is_dir():
                for sub_file in sub_strategies_dir.glob("*.md"):
                    try:
                        md_text += "\n\n" + sub_file.read_text()
                    except Exception:
                        pass

            log_ok("Successfully loaded investment_thesis.md and sub-strategy files")

            missing_tickers = []
            for h in holdings:
                ticker = h["ticker"]
                # Match dots and dashes interchangeably (e.g. PSU.U.TO or PSU-U.TO)
                ticker_pattern = re.escape(ticker).replace(r"\.", r"[\.-]")
                pattern = rf"\b{ticker_pattern}\b"
                if not re.search(pattern, md_text):
                    missing_tickers.append(ticker)

            if missing_tickers:
                log_fail(f"The following tickers exist in target portfolio but are missing in thesis documentation: {missing_tickers}")
            else:
                log_ok("All portfolio tickers are successfully documented in the thesis/sub-strategy markdown files.")
        except Exception as e:
            log_fail(f"Failed to read/verify thesis markdown files: {e}")

    # ── 3. Validate Valuation Projections ──────────────────────────────────────
    print("\nChecking valuation projections for active tickers...")
    active_missing_projections = []
    total_active = 0

    for h in holdings:
        ticker = h["ticker"]
        weight = h.get("targetWeight", 0)
        role = h.get("role", "").lower()

        # Exempt spot ETFs (e.g. BTC, ETH) and cash reserves from standard DCF check
        is_spot_or_cash = (h.get("subStrategyId") == "cash") or (ticker in ("ETHA", "IBIT", "SOLZ"))
        
        is_active = ((weight > 0) or (role in ACTIVE_ROLES)) and not is_spot_or_cash
        if is_active:
            total_active += 1
            proj_path = proj_dir_path / f"{ticker}.json"
            if not proj_path.exists():
                active_missing_projections.append(ticker)

    log_ok(f"Found {total_active} active equity/business thesis holdings requiring DCF projections.")
    if active_missing_projections:
        log_fail(f"The following active tickers are missing DCF projections in {proj_dir_path}: {active_missing_projections}")
    else:
        log_ok("All active thesis holdings have active projections on file.")

    # ── Summary ─────────────────────────────────────────────────────────────
    print("\n==================================================================")
    print("   Sync Results Summary")
    print("==================================================================")
    if warnings:
        print(f"Warnings ({len(warnings)}):")
        for w in warnings:
            print(f"  - {w}")
    if errors:
        print(f"Errors ({len(errors)}):")
        for e in errors:
            print(f"  - {e}")
        print("\n❌  Sync Verification FAILED. Please resolve the issues above.")
        sys.exit(1)
    else:
        print("\n✅  All Synchronization Checks Passed successfully! Perfect alignment.")
        sys.exit(0)

if __name__ == "__main__":
    main()
