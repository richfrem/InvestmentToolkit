#!/usr/bin/env python3
"""
audit_staleness.py — Audits all active portfolio holdings and targets in domain_model.sqlite
for projection freshness (days since last DCF or ETF analysis).
"""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path("investment_screener/backend/data/domain_model.sqlite")

def main():
    if not DB_PATH.exists():
        print(f"Error: Database {DB_PATH} not found.")
        return

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT i.symbol, i.name, i.asset_class, i.lifecycle_status, i.target_weight, i.target_action,
               MAX(pv.saved_at) as last_projection_date, pv.source, pv.fair_value, pv.action
        FROM investment i
        LEFT JOIN projection_version pv ON i.investment_id = pv.investment_id
        WHERE (i.target_weight > 0 OR i.lifecycle_status IN ('core', 'accumulate', 'trim'))
          AND i.symbol NOT IN ('USD_CASH', 'CASH_USD')
        GROUP BY i.symbol
        ORDER BY last_projection_date ASC
    """)
    rows = cur.fetchall()

    print(f"Total Active Portfolio Holdings/Targets: {len(rows)}")
    print("=" * 105)
    print(f"{'TICKER':<10} {'TYPE':<8} {'TARGET%':<9} {'ACTION':<12} {'FAIR VALUE':<12} {'LAST ANALYZED':<25} {'FRESHNESS STATUS'}")
    print("=" * 105)

    now = datetime.now(timezone.utc)
    stale_count = 0
    fresh_count = 0

    for r in rows:
        last_d = r["last_projection_date"]
        if not last_d:
            status = "🚨 MISSING / NO ANALYSIS"
            stale_count += 1
        else:
            try:
                clean_d = last_d.replace("Z", "+00:00")
                d = datetime.fromisoformat(clean_d)
                days_ago = (now - d).days
                if days_ago > 30:
                    status = f"⚠️ STALE ({days_ago}d ago)"
                    stale_count += 1
                else:
                    status = f"✅ FRESH ({days_ago}d ago)"
                    fresh_count += 1
            except Exception:
                status = "❓ UNKNOWN FORMAT"
                stale_count += 1

        fv_str = f"${r['fair_value']:.2f}" if r["fair_value"] is not None else "—"
        act_str = r["action"] or r["target_action"] or "—"
        tgt_str = f"{r['target_weight']:.2f}%" if r["target_weight"] is not None else "0.00%"

        print(f"{r['symbol']:<10} {r['asset_class']:<8} {tgt_str:<9} {act_str:<12} {fv_str:<12} {str(last_d or 'Never'):<25} {status}")

    print("=" * 105)
    print(f"Summary: {fresh_count} Fresh, {stale_count} Stale/Missing out of {len(rows)} Active Portfolio Holdings.")

if __name__ == "__main__":
    main()
