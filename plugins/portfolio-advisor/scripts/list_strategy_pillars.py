#!/usr/bin/env python3
"""
list_strategy_pillars.py — Canonical CLI tool to inspect portfolio strategy pillars and sub-strategies.
======================================================================================================

Purpose:
    Provides a standardized, versioned interface to query active strategy pillars, target allocations,
    and child sub-strategies from domain_model.sqlite using domain_model.pillar_repository.
    Eliminates ad-hoc inline SQL queries across agent skills and CLI workflows.

Layer:
    Plugins / Portfolio Advisor / Scripts

Key Input Dependencies:
    - investment_screener/backend/data/domain_model.sqlite (via domain_model.pillar_repository)

Usage:
    python3 plugins/portfolio-advisor/scripts/list_strategy_pillars.py [--json]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# ── Path Resolution ────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parents[3]
DB_PATH = REPO_ROOT / "investment_screener/backend/data/domain_model.sqlite"

sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))
from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.pillar_repository import list_pillars, list_sub_strategies  # noqa: E402


def get_pillars_and_strategies():
    if not DB_PATH.exists():
        return []
    conn = initialize_db(str(DB_PATH))
    try:
        pillars = list_pillars(conn)
        sub_strats = list_sub_strategies(conn)
        
        # Group sub-strategies by pillar
        sub_map = {}
        for sub in sub_strats:
            p_id = sub["pillar_id"]
            if p_id not in sub_map:
                sub_map[p_id] = []
            sub_map[p_id].append(sub)

        results = []
        for p in pillars:
            p_id = p["pillar_id"]
            results.append({
                "pillar_id": p_id,
                "name": p["name"],
                "target_weight": p.get("target_weight"),
                "sub_strategies": sub_map.get(p_id, []),
            })
        return sorted(results, key=lambda x: (x["target_weight"] or 0), reverse=True)
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="List portfolio strategy pillars and sub-strategies")
    parser.add_argument("--json", action="store_true", help="Output JSON format")
    args = parser.parse_args()

    data = get_pillars_and_strategies()

    if args.json or not sys.stdout.isatty():
        print(json.dumps(data, indent=2))
        return

    print("\n🏛️  ACTIVE PORTFOLIO STRATEGY PILLARS (domain_model.sqlite)\n" + "═" * 65)
    for p in data:
        weight_str = f"{p['target_weight']:.2f}%" if p['target_weight'] is not None else "Unset"
        print(f"• [{p['pillar_id']}] {p['name']} (Target: {weight_str})")
        for sub in p["sub_strategies"]:
            print(f"    ↳ Sub-Strategy: {sub['name']} ({sub['sub_strategy_id']})")
    print("═" * 65 + "\n")


if __name__ == "__main__":
    main()
