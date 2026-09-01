#!/usr/bin/env python3
"""
audit_all_strategies.py
=====================================

Purpose:
    Audits all active investments in domain_model.sqlite to verify that each ticker's
    assigned Strategy Pillar and Sub-Strategy match canonical investment thesis definitions.

Layer:
    Backend / py_services / Diagnostic

Usage:
    python3 investment_screener/backend/py_services/audit_all_strategies.py

Key Functions:
    - audit_strategies(db_path: Path) -> dict: Performs taxonomy validation across all investment records.
    - main() -> None: CLI entry point.

Key Input Dependencies:
    - investment_screener/backend/data/domain_model.sqlite (strategy_pillar, sub_strategy, investment tables)
"""

import sqlite3
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Any

_HERE = Path(__file__).resolve().parent
DB_PATH = _HERE / ".." / "data" / "domain_model.sqlite"


def audit_strategies(db_path: Path = DB_PATH) -> Dict[str, Any]:
    """
    Validates all investment entries against strategy_pillar and sub_strategy definitions.

    Args:
        db_path: Path to domain_model.sqlite database.

    Returns:
        Dictionary containing audit counts, mismatches, and untagged tickers.
    """
    if not db_path.exists():
        raise FileNotFoundError(f"Database {db_path} not found.")

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    try:
        # Fetch all registered pillars and sub-strategies
        cur.execute("SELECT pillar_id, name FROM strategy_pillar ORDER BY pillar_id")
        pillars: Dict[str, str] = {r["pillar_id"]: r["name"] for r in cur.fetchall()}

        cur.execute("SELECT sub_strategy_id, pillar_id, name FROM sub_strategy ORDER BY sub_strategy_id")
        sub_strats: Dict[str, Tuple[str, str]] = {r["sub_strategy_id"]: (r["pillar_id"], r["name"]) for r in cur.fetchall()}

        # Fetch all investments
        cur.execute("""
            SELECT symbol, name, asset_class, lifecycle_status, target_weight, pillar_id, sub_strategy_id, sector, industry
            FROM investment
            ORDER BY symbol ASC
        """)
        rows = cur.fetchall()

        unaligned: List[Tuple[str, str, str, str]] = []
        missing_strat: List[Tuple[str, str, str]] = []
        records: List[Dict[str, Any]] = []

        for r in rows:
            sym = r["symbol"]
            name = (r["name"] or "")[:26]
            p_id = r["pillar_id"] or "—"
            s_id = r["sub_strategy_id"] or "—"
            tgt = f"{r['target_weight']:.2f}%" if r["target_weight"] is not None else "0.00%"
            sec_ind = f"{r['sector'] or ''} / {r['industry'] or ''}"[:35]

            # Check alignment
            if s_id in sub_strats:
                expected_pillar = sub_strats[s_id][0]
                if p_id != expected_pillar and p_id not in ("other", "—"):
                    unaligned.append((sym, p_id, s_id, expected_pillar))
            elif s_id in ("—", "other", None) and sym not in ("CASH_USD", "USD_CASH"):
                missing_strat.append((sym, p_id, sec_ind))

            records.append({
                "symbol": sym,
                "name": name,
                "pillar_id": p_id,
                "sub_strategy_id": s_id,
                "target_weight": tgt,
                "sector_industry": sec_ind
            })

        return {
            "total_count": len(rows),
            "pillars": pillars,
            "sub_strategies": sub_strats,
            "records": records,
            "unaligned": unaligned,
            "missing_strat": missing_strat
        }
    finally:
        conn.close()


def main() -> None:
    """CLI execution entrypoint."""
    results = audit_strategies(DB_PATH)

    print(f"Total Investments in domain_model.sqlite: {results['total_count']}")
    print(f"Valid Pillars: {list(results['pillars'].keys())}")
    print(f"Valid Sub-Strategies ({len(results['sub_strategies'])}): {list(results['sub_strategies'].keys())}")
    print("=" * 120)
    print(f"{'TICKER':<10} {'NAME':<28} {'PILLAR':<16} {'SUB-STRATEGY':<22} {'TARGET%':<9} {'SECTOR / INDUSTRY'}")
    print("=" * 120)

    for r in results["records"]:
        print(f"{r['symbol']:<10} {r['name']:<28} {r['pillar_id']:<16} {r['sub_strategy_id']:<22} {r['target_weight']:<9} {r['sector_industry']}")

    print("=" * 120)
    print("Audit Summary:")
    print(f"  • Total Tickers Checked: {results['total_count']}")
    print(f"  • Tickers with Pillar-SubStrategy Mismatch: {len(results['unaligned'])}")
    for sym, p_id, s_id, exp in results["unaligned"]:
        print(f"    ⚠️  {sym}: Pillar '{p_id}' != Expected '{exp}' for strategy '{s_id}'")
    print(f"  • Tickers with Missing/Generic Sub-Strategy: {len(results['missing_strat'])}")
    for sym, p_id, sec in results["missing_strat"][:15]:
        print(f"    ℹ️  {sym} ({p_id}): {sec}")
    if len(results["missing_strat"]) > 15:
        print(f"    ... and {len(results['missing_strat']) - 15} more.")


if __name__ == "__main__":
    main()
