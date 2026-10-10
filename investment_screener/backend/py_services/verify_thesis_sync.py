#!/usr/bin/env python3
"""
verify_thesis_sync.py - Python utility script.

Purpose:
    verify_thesis_sync.py — Automated Portfolio & Thesis Synchronization Checker.

Performs three core sanity checks:
  1. Holding Mismatches: Every thesis holding must be mentioned in investment_thesis.md. Holdings come
     from domain_model.sqlite's investment table.
  2. Valuation Projections: Every active ticker with a target weight > 0 or in an active role
     (accumulate, trim, exit, initiate) must have a saved projection (projection_version in
     domain_model.sqlite).
  3. Total Weights Guard: Asserts that target weights sum to exactly 100% (within 0.1% tolerance).

Exits with 0 on success, 1 on failure.

Key Input Dependencies:
    - investment_screener/backend/data/domain_model.sqlite (investment and projection_version tables)
    - investment_screener/backend/data/theses/investment_thesis.md (generated thesis blueprint)
    - Optional overrides: --thesis-md, --db

Layer:
    Backend / Python Services

Usage Examples:
    python3 verify_thesis_sync.py
    python3 verify_thesis_sync.py --db /path/to/domain_model.sqlite

Key Functions (Index):
    - main()
    - log_ok()
    - log_fail()
    - log_warn()

Key Output Dependencies:
    - Pass/fail report on stdout; exit code 0 on success, 1 on failure (writes no files)
"""
import re
import sys
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
PY_SERVICES_DIR = Path(__file__).resolve().parent
REPO_ROOT       = PY_SERVICES_DIR.parents[2]

THESIS_MD   = REPO_ROOT / "investment_screener" / "backend" / "data" / "theses" / "investment_thesis.md"
DB_PATH     = REPO_ROOT / "investment_screener" / "backend" / "data" / "domain_model.sqlite"

sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))
from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.investment_repository import list_investments  # noqa: E402
from domain_model.projection_repository import get_latest_projection  # noqa: E402

ACTIVE_ROLES = {"accumulate", "trim", "exit", "initiate"}


def _load_holdings_from_db(db_path: Path) -> list[dict]:
    """Load thesis holdings from domain_model.sqlite's investment table as
    ticker/targetWeight/role/subStrategyId dicts, so the weight-sum, markdown-mention and
    projection checks share one path.

    Field mapping: "role" -> lifecycle_status, "targetWeight" -> target_weight,
    "subStrategyId" -> sub_strategy_id.

    Pure watchlist entries (no target weight and no active lifecycle status) are excluded: a
    ticker that is only watched was never a target holding and needs no thesis documentation.
    A ticker with a real target weight or active status is included even if also watchlisted.
    """
    conn = initialize_db(str(db_path))
    try:
        investments = list_investments(conn)
    finally:
        conn.close()
    return [
        {
            "ticker": inv.get("symbol"),
            "targetWeight": inv.get("target_weight") or 0,
            "role": inv.get("lifecycle_status") or "",
            "subStrategyId": inv.get("sub_strategy_id"),
        }
        for inv in investments
        if inv.get("symbol")
        and ((inv.get("target_weight") or 0) > 0 or (inv.get("lifecycle_status") and inv.get("lifecycle_status") not in ("watchlist", "avoid", "exit")))
    ]


def _projection_exists_in_db(db_path: Path, ticker: str) -> bool:
    """True when ``ticker`` has a saved projection in domain_model.sqlite's projection_version."""
    conn = initialize_db(str(db_path))
    try:
        row = conn.execute(
            "SELECT investment_id FROM investment WHERE symbol = ?;", (ticker,)
        ).fetchone()
        if row is None:
            return False
        return get_latest_projection(conn, row[0]) is not None
    finally:
        conn.close()

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Automated Portfolio & Thesis Synchronization Checker")
    parser.add_argument("--thesis-md", type=str, help="Path to investment_thesis.md")
    parser.add_argument("--db", type=str, help="Path to domain_model.sqlite")
    args = parser.parse_args()

    thesis_md_path = Path(args.thesis_md) if args.thesis_md else THESIS_MD
    db_path = Path(args.db) if args.db else DB_PATH

    print("==================================================================")
    print("   Portfolio & Thesis Sync Verification Suite")
    print("==================================================================")
    print(f"Thesis source: {db_path} (domain_model.sqlite)")
    print(f"Thesis MD:   {thesis_md_path}")
    print(f"Projections source: {db_path} (domain_model.sqlite)\n")

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

    # ── 1. Validate holdings ground truth (SQLite) ────────────────────────────
    print("Checking domain_model.sqlite ground truth...")
    try:
        holdings = _load_holdings_from_db(db_path)
        log_ok(f"Successfully loaded holdings from {db_path}")
    except Exception as e:
        log_fail(f"Failed to load holdings from domain_model.sqlite: {e}")
        sys.exit(1)

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
            if not _projection_exists_in_db(db_path, ticker):
                active_missing_projections.append(ticker)

    proj_source_desc = f"{db_path} (domain_model.sqlite)"
    log_ok(f"Found {total_active} active equity/business thesis holdings requiring DCF projections.")
    if active_missing_projections:
        log_fail(f"The following active tickers are missing DCF projections in {proj_source_desc}: {active_missing_projections}")
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
