#!/usr/bin/env python3
"""
review_gate.py — the daily/weekly review cycle: nothing followed is left unanalysed.

Purpose:
    Start of every daily loop, weekly review or analysis session: `begin` resets every holding
    and watchlist name to NEEDS_ANALYSIS and runs the deterministic triage, leaving a queue of
    names that need a fresh look. Work the queue (re-value with /update-stock-analysis, or
    `mark` an age-only name with a written reason). End of the session: `verify` must exit 0.
Layer:
    Portfolio advisor / review discipline (writes investment.review_*).
Usage:
    python3 investment_screener/backend/py_services/review_gate.py begin          # start + triage, prints the queue
    python3 investment_screener/backend/py_services/review_gate.py mark --ticker MU --reason "..."
    python3 investment_screener/backend/py_services/review_gate.py verify         # exit 1 while any name is NEEDS_ANALYSIS
    python3 investment_screener/backend/py_services/review_gate.py status
    Add --json for machine-readable output, --db for another database, --no-earnings to skip the fetch.
Key Functions:
    last_earnings_date(symbol)  most recent reported earnings date (yfinance), or None
Key Input Dependencies:
    domain_model.sqlite via review_cycle.py; thesis breakers via recommendation._triggered_tickers.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_REPO / "investment_screener/backend/py_services"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from domain_model.db_client import initialize_db  # noqa: E402
import review_cycle  # noqa: E402

_DB = str(_REPO / "investment_screener/backend/data/domain_model.sqlite")
REPORT_LAG_DAYS = 45


def last_earnings_date(symbol: str, today: date | None = None) -> str | None:
    """Most recent earnings report before today; None when the security has none (ETF/fund).

    Uses the quote's earningsCallTimestampStart (most recent call) and earningsTimestamp (latest or
    scheduled report), keeping the latest that falls before today. Raises LookupError when the lookup
    fails, so triage never treats "unknown" as "nothing new".
    """
    from datetime import datetime, timezone
    today = today or date.today()
    try:
        import yfinance as yf
        info = yf.Ticker(symbol).info or {}
    except Exception as exc:  # network or API failure
        raise LookupError(f"{symbol}: {exc}") from exc
    days = []
    for key in ("earningsCallTimestampStart", "earningsTimestamp"):
        ts = info.get(key)
        if isinstance(ts, (int, float)) and ts > 0:
            d = datetime.fromtimestamp(ts, tz=timezone.utc).date()
            if d < today:
                days.append(d)
    if days:
        return max(days).isoformat()
    if not any(info.get(k) for k in ("earningsTimestamp", "earningsTimestampStart", "mostRecentQuarter")):
        return None  # no earnings at all (ETF, fund)
    # Only a future report is listed: estimate the last report as the latest reported fiscal
    # quarter-end plus REPORT_LAG_DAYS (an upper bound on the usual reporting lag).
    try:
        cols = yf.Ticker(symbol).quarterly_income_stmt.columns
        q_end = max(c.date() for c in cols)
    except Exception as exc:
        raise LookupError(f"{symbol}: no past earnings date and no quarterly statement ({exc})") from exc
    return min(q_end + timedelta(days=REPORT_LAG_DAYS), today - timedelta(days=1)).isoformat()


def _breakers(db: str) -> set[str]:
    try:
        from recommendation import _triggered_tickers
        return _triggered_tickers(db)
    except Exception:
        return set()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Daily/weekly review cycle")
    ap.add_argument("command", choices=["begin", "mark", "verify", "status"])
    ap.add_argument("--ticker"); ap.add_argument("--reason")
    ap.add_argument("--json", action="store_true"); ap.add_argument("--db", default=_DB)
    ap.add_argument("--no-earnings", action="store_true", help="skip the last-earnings fetch (offline)")
    a = ap.parse_args(argv)
    conn = initialize_db(a.db)
    try:
        if a.command == "begin":
            n = review_cycle.start(conn)
            queue = review_cycle.triage(conn, date.today(), None if a.no_earnings else last_earnings_date, _breakers(a.db))
            out = {"reset": n, "queue": queue, **review_cycle.status(conn)}
            if a.json:
                print(json.dumps(out, indent=2))
            else:
                unknown = sum(any("earnings date unavailable" in r for r in q["reasons"]) for q in queue)
                if unknown:
                    print(f"⚠ last earnings date unavailable for {unknown} name(s); they can't be auto-cleared")
                print(f"Reset {n}; {out['reviewed']} cleared by triage; {len(queue)} need analysis:")
                for q in queue:
                    print(f"  {'HELD ' if q['held'] else 'watch'} {q['symbol']:<9}{'HARD ' if q['hard'] else 'age  '} {'; '.join(q['reasons'])}")
            return 0
        if a.command == "mark":
            if not a.ticker or not a.reason:
                ap.error("mark needs --ticker and --reason")
            res = review_cycle.mark(conn, a.ticker.upper(), a.reason, date.today(), _breakers(a.db))
            print(json.dumps(res) if a.json else (f"✓ {res['symbol']} reviewed" if res["ok"] else f"✗ {res['symbol']}: {res['error']}"))
            return 0 if res["ok"] else 1
        if a.command == "verify":
            left = review_cycle.verify(conn)
            if a.json:
                print(json.dumps({"ok": not left, "needs_analysis": left}, indent=2))
            elif left:
                print(f"✗ {len(left)} name(s) still NEEDS_ANALYSIS: " + ", ".join(("*" if x["held"] else "") + x["symbol"] for x in left) + "  (* = held)")
            else:
                print("✓ Every holding and watchlist name has been reviewed this cycle.")
            return 1 if left else 0
        print(json.dumps(review_cycle.status(conn), indent=2))
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
