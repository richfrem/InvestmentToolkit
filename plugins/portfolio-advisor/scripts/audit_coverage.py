#!/usr/bin/env python3
"""
audit_coverage.py - Portfolio & Watchlist AI Analysis Coverage Auditor.
=======================================================================

Purpose:
    Audits the entire portfolio and watchlist database in domain_model.sqlite
    to classify equities by analysis completeness (Fully Analyzed with AI DCF/TA,
    Partial, or Unanalyzed Gaps). Produces structured gap reports and actionable
    batch intake queues.

Layer:
    Portfolio Advisor / Scripts

Usage Examples:
    python3 audit_coverage.py
    python3 audit_coverage.py --json
    python3 audit_coverage.py --gaps-only

Key Functions (Index):
    - get_db_connection(db_path) -> sqlite3.Connection
    - audit_portfolio_coverage(db_path) -> dict[str, Any]
    - main() -> CLI parser and reporter

Key Input Dependencies:
    - investment_screener/backend/data/domain_model.sqlite

Key Output Dependencies:
    - Formatted terminal report or structured JSON summary
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

# Default path to the SQLite single source of truth
_HERE: Path = Path(__file__).resolve().parent
_DEFAULT_DB: Path = _HERE.parents[1] / "investment_screener" / "backend" / "data" / "domain_model.sqlite"
if not _DEFAULT_DB.exists():
    _DEFAULT_DB = _HERE / ".." / "data" / "domain_model.sqlite"


# Dual-layer docs: get_db_connection helper
def get_db_connection(db_path: str | Path | None = None) -> sqlite3.Connection:
    """Establish and return an active sqlite3 connection configured with Row factory.

    Args:
        db_path: Optional explicit file path to SQLite database.

    Returns:
        sqlite3.Connection: Active database connection.
    """
    path = Path(db_path) if db_path else _DEFAULT_DB
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


# Dual-layer docs: audit_portfolio_coverage function
def audit_portfolio_coverage(db_path: str | Path | None = None) -> dict[str, Any]:
    """Audit domain_model.sqlite to classify equities by analysis readiness.

    Args:
        db_path: Optional database file path.

    Returns:
        dict[str, Any]: Classification summary with lists of fully analyzed, partial, and gap equities.
    """
    conn = get_db_connection(db_path)
    try:
        cur = conn.execute(
            """
            SELECT i.symbol, i.name, i.lifecycle_status, i.is_watchlisted,
                   i.pillar_id, i.sub_strategy_id, i.target_weight,
                   ip.price,
                   pv.fair_value, pv.action, pv.source AS proj_source
            FROM investment i
            LEFT JOIN investment_price ip ON i.investment_id = ip.investment_id
            LEFT JOIN projection_version pv ON i.latest_projection_id = pv.projection_id
            WHERE i.lifecycle_status != 'exit' OR i.is_watchlisted = 1
            ORDER BY i.symbol ASC
            """
        )
        rows = [dict(r) for r in cur.fetchall()]

        fully_analyzed: list[dict[str, Any]] = []
        valuation_only: list[dict[str, Any]] = []
        needs_analysis: list[dict[str, Any]] = []

        for r in rows:
            has_price = r.get("price") is not None and float(r["price"] or 0) > 0
            has_proj = r.get("fair_value") is not None and float(r["fair_value"] or 0) > 0
            
            item = {
                "symbol": r["symbol"],
                "name": r["name"],
                "price": r.get("price") or 0.0,
                "fair_value": r.get("fair_value"),
                "action": r.get("action") or "WATCHLIST",
                "lifecycle_status": r["lifecycle_status"],
                "is_watchlisted": r["is_watchlisted"],
                "pillar_id": r.get("pillar_id") or "Unassigned",
            }

            if has_price and has_proj:
                fully_analyzed.append(item)
            elif has_proj and not has_price:
                valuation_only.append(item)
            else:
                needs_analysis.append(item)

        return {
            "total_count": len(rows),
            "fully_analyzed_count": len(fully_analyzed),
            "needs_analysis_count": len(needs_analysis),
            "fully_analyzed": fully_analyzed,
            "valuation_only": valuation_only,
            "needs_analysis": needs_analysis,
        }
    finally:
        conn.close()


# Dual-layer docs: CLI entrypoint
def main() -> None:
    """Parse CLI flags and run the coverage audit report."""
    parser = argparse.ArgumentParser(description="Audit AI valuation and research coverage across portfolio and watchlist.")
    parser.add_argument("--json", action="store_true", help="Output audit results as structured JSON")
    parser.add_argument("--gaps-only", action="store_true", help="Output only equities requiring AI intake")
    args = parser.parse_args()

    report = audit_portfolio_coverage()

    if args.json:
        print(json.dumps(report, indent=2))
        return

    if args.gaps_only:
        print(f"🚨 Tickers Requiring AI Intake ({len(report['needs_analysis'])}):")
        for it in report["needs_analysis"]:
            print(f"  • {it['symbol']:<6} | {it['name'][:25]:<25} | Pillar: {it['pillar_id']}")
        return

    print("=" * 70)
    print("📊 Portfolio & Watchlist Coverage Audit")
    print("=" * 70)
    print(f"Total Equities:        {report['total_count']}")
    print(f"✅ Fully Analyzed:     {report['fully_analyzed_count']} (Live Price + DCF Model)")
    print(f"🚨 Needs Intake/Gaps:  {report['needs_analysis_count']} (Unanalyzed / No DCF)")
    print("-" * 70)
    
    if report["needs_analysis"]:
        print(f"\nTop Gaps Requiring `/stock-intake`:")
        for it in report["needs_analysis"][:15]:
            print(f"  • {it['symbol']:<6} | {it['name'][:25]:<25} | Status: {it['lifecycle_status']}")
        if len(report["needs_analysis"]) > 15:
            print(f"  ... and {len(report['needs_analysis']) - 15} more.")
    print("=" * 70)


if __name__ == "__main__":
    main()
