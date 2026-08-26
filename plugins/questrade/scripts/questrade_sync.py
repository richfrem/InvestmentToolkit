#!/usr/bin/env python3
"""
questrade_sync.py - Python Service for Questrade SQLite Synchronization.

Purpose:
    Directly ingests Questrade account balances, holdings, and cash splits into
    domain_model.sqlite without requiring TradingView CDP DOM scraping.
    Preserves the Mandatory Cash Invariant (Rule #18) and updates thesis roles.

Layer:
    Plugins / Questrade / Services

Usage Examples:
    # Direct payload sync from JSON file:
    python3 plugins/questrade/scripts/questrade_sync.py --payload payload.json

    # Dry-run validation:
    python3 plugins/questrade/scripts/questrade_sync.py --payload payload.json --dry-run

Key Functions (Index):
    - persist_questrade_data_to_db() : Upserts accounts, balances, and holdings into SQLite.
    - _run_portfolio_refresh()       : Triggers refresh_all.py to update thesis roles.
    - main()                         : CLI entrypoint for parsing JSON payloads.

Key Input Dependencies:
    - investment_screener/backend/data/domain_model.sqlite (Domain Database)
"""

import sys
import json
import sqlite3
import argparse
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Any

# ── path bootstrap ──────────────────────────────────────────────────────────
_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parents[1]
_PY_SERVICES = _REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(_PY_SERVICES))

from ticker_aliases import normalize_ticker  # noqa: E402
from domain_model.account_repository import upsert_account  # noqa: E402
from domain_model.account_investment_repository import upsert_account_investment  # noqa: E402
from domain_model.investment_repository import resolve_investment  # noqa: E402
from domain_model.broker_reported_total_repository import upsert_broker_reported_total  # noqa: E402
from domain_model.exchange_rate_repository import upsert_exchange_rate  # noqa: E402

_DEFAULT_DB_PATH = str(_REPO_ROOT / "investment_screener/backend/data/domain_model.sqlite")


def persist_questrade_data_to_db(
    conn: sqlite3.Connection,
    accounts: list[dict],
    balances: Optional[dict[str, Any]] = None,
    positions: Optional[dict[str, list[dict]]] = None,
) -> int:
    """Upsert accounts, uninvested cash, and security positions into SQLite.

    Args:
        conn: Open SQLite connection to domain_model.sqlite.
        accounts: List of account dicts from List Accounts.
        balances: Dict mapping accountId -> balance dict from Get Balances.
        positions: Dict mapping accountId -> list of position dicts from Get Positions.

    Returns:
        Total number of account_investment and cash rows written.
    """
    now = datetime.now(timezone.utc).isoformat()
    written = 0

    balances = balances or {}
    positions = positions or {}

    # 1. Upsert Accounts
    for acc in accounts:
        acc_id = str(acc.get("number") or acc.get("accountId") or acc.get("id"))
        acc_type = str(acc.get("type", "UNKNOWN"))
        acc_name = f"{acc_type} ({acc_id})"
        upsert_account(
            conn=conn,
            account_id=acc_id,
            account_name=acc_name,
            account_type=acc_type,
            base_currency="CAD",
        )

    # 2. Upsert Uninvested Cash as synthetic CASH_USD position
    for acc_id, bal in balances.items():
        cash_usd = float(bal.get("cashUSD", 0.0) or bal.get("cash", 0.0) or 0.0)
        if cash_usd != 0.0:
            resolve_investment(conn, "CASH_USD", asset_class="CASH", currency="USD", name="US Dollar Cash")
            upsert_account_investment(
                conn=conn,
                account_id=acc_id,
                investment_id="CASH_USD",
                quantity=cash_usd,
                average_cost=1.0,
                book_value=cash_usd,
                currency="USD",
                last_synced_at=now,
            )
            written += 1

        # Record exchange rate if both USD and CAD equity are provided
        total_usd = float(bal.get("totalEquityUSD", 0.0) or 0.0)
        total_cad = float(bal.get("totalEquityCAD", 0.0) or 0.0)
        if total_usd > 0 and total_cad > 0:
            inferred_rate = total_cad / total_usd
            upsert_exchange_rate(conn, inferred_rate, now)
            upsert_broker_reported_total(
                conn=conn,
                total_usd=total_usd,
                total_cad=total_cad,
                synced_at=now,
                source="Questrade MCP",
            )

    # 3. Upsert Security Positions
    for acc_id, pos_list in positions.items():
        for pos in pos_list:
            raw_sym = pos.get("symbol") or pos.get("instrument") or ""
            if not raw_sym:
                continue

            symbol = normalize_ticker(raw_sym)
            resolve_investment(conn, symbol, asset_class="EQUITY", currency="USD")
            qty = float(pos.get("openQuantity") or pos.get("qty") or pos.get("quantity") or 0.0)
            avg_cost = float(pos.get("avgPrice") or pos.get("averagePrice") or pos.get("costBasis") or 0.0)
            book_val = qty * avg_cost if avg_cost else None

            upsert_account_investment(
                conn=conn,
                account_id=acc_id,
                investment_id=symbol,
                quantity=qty,
                average_cost=avg_cost,
                book_value=book_val,
                currency="USD",
                last_synced_at=now,
            )
            written += 1

    return written


def _run_portfolio_refresh() -> None:
    """Run refresh_all.py after broker sync to update thesis metrics and target weights."""
    refresh_script = _REPO_ROOT / "plugins/portfolio-advisor/scripts/refresh_all.py"
    if refresh_script.exists():
        subprocess.run([sys.executable, str(refresh_script)], check=False)
    else:
        print(f"⚠ refresh_all.py not found at {refresh_script}", file=sys.stderr)


def main() -> None:
    """CLI entry point for syncing Questrade data from a JSON payload."""
    parser = argparse.ArgumentParser(description="Sync Questrade MCP data into domain_model.sqlite")
    parser.add_argument("--payload", type=str, required=True, help="Path to JSON payload file with accounts, balances, and positions")
    parser.add_argument("--db-path", type=str, default=_DEFAULT_DB_PATH, help="Path to SQLite database")
    parser.add_argument("--dry-run", action="store_true", help="Validate without writing to database")
    args = parser.parse_args()

    payload_path = Path(args.payload)
    if not payload_path.exists():
        print(f"Error: Payload file not found at {payload_path}", file=sys.stderr)
        sys.exit(1)

    with open(payload_path) as f:
        data = json.load(f)

    accounts = data.get("accounts", [])
    balances = data.get("balances", {})
    positions = data.get("positions", {})

    if args.dry_run:
        print(f"Dry run: Found {len(accounts)} accounts, {len(balances)} balance blocks, and {sum(len(v) for v in positions.values())} position(s).")
        return

    conn = sqlite3.connect(args.db_path)
    try:
        written = persist_questrade_data_to_db(conn, accounts, balances, positions)
        print(f"✓ Successfully synced {written} item(s) to domain_model.sqlite")
        _run_portfolio_refresh()
    finally:
        conn.close()


if __name__ == "__main__":
    main()
