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
    - _parse_money()                 : Parses a Questrade-formatted currency string (e.g. "$3,317.07") or raw number into a float.
    - _parse_account_type_and_number(): Splits a Questrade account name (e.g. "TFSA - 53408189") into (type, number).
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
# _HERE resolves through the skills/questrade-sync-portfolio/scripts/ symlink
# to this canonical file at plugins/questrade/scripts/ — parents[2] from there
# is repo root (parents[1] was plugins/, which silently broke every import).
_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parents[2]
_PY_SERVICES = _REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(_PY_SERVICES))

from ticker_aliases import normalize_ticker  # noqa: E402
from domain_model.account_repository import upsert_account  # noqa: E402
from domain_model.account_investment_repository import (  # noqa: E402
    upsert_account_investment,
    delete_stale_account_investments,
)
from domain_model.investment_repository import resolve_investment  # noqa: E402
from domain_model.broker_reported_total_repository import upsert_broker_reported_total  # noqa: E402
from domain_model.exchange_rate_repository import upsert_exchange_rate  # noqa: E402

_DEFAULT_DB_PATH = str(_REPO_ROOT / "investment_screener/backend/data/domain_model.sqlite")


def _parse_money(value: Any) -> float:
    """Parse a Questrade-formatted currency string (e.g. "$3,317.07") or raw number into a float.

    Live get_balances/get_positions responses return currency leaves as
    pre-formatted strings ("$131.08"), not raw numbers — see
    references/questrade-tool-schemas.md.
    """
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    cleaned = str(value).replace("$", "").replace(",", "").strip()
    if not cleaned or cleaned in {"-", "N/A"}:
        return 0.0
    return float(cleaned)


def _parse_account_type_and_number(name: str) -> tuple[str, str]:
    """Split a live list_accounts `name` (e.g. "TFSA - 53408189") into (type, number).

    list_accounts has no separate type/number fields — both are embedded in
    `name` — see references/questrade-tool-schemas.md.
    """
    if " - " in name:
        acc_type, _, acc_number = name.partition(" - ")
        return acc_type.strip(), acc_number.strip()
    return "UNKNOWN", name.strip()


def _resolve_canonical_account_ids(accounts: list[dict]) -> dict[str, str]:
    """Map each Questrade account's own `id` (uuid) to the canonical account_id.

    The rest of the system (TradingView sync in fetch_broker_data.py, the
    dashboard, thesis roles) keys account_investment by plain account-type
    strings ("TFSA"/"RRSP"/"CASH") — see fetch_broker_data.py's
    `account_id = snap.get("accountType")`. Questrade's own uuid is never used
    as account_id here; using it silently forked a second, duplicate set of
    rows for every position (found 2026-08-26 — every held symbol had both a
    'TFSA'/'RRSP' row and a uuid-keyed row for the same real position).
    """
    return {
        str(acc.get("id") or acc.get("accountId")): _parse_account_type_and_number(str(acc.get("name", "")))[0].upper()
        for acc in accounts
    }


def persist_questrade_data_to_db(
    conn: sqlite3.Connection,
    accounts: list[dict],
    balances: Optional[dict[str, Any]] = None,
    positions: Optional[dict[str, list[dict]]] = None,
) -> int:
    """Upsert accounts, uninvested cash, and security positions into SQLite.

    A full sync is authoritative for each account's *complete* current holding
    set: every symbol not present in this call's positions[account] is treated
    as fully sold and its stale row removed (see delete_stale_account_investments).

    Args:
        conn: Open SQLite connection to domain_model.sqlite.
        accounts: List of account dicts from list_accounts: {id, name, productType, supportTrading}.
        balances: Dict mapping accountId (the `id` from list_accounts) -> the
            `balances` sub-object from get_balances: {cash, totalEquity, ...},
            each leaf a {cad, usd, combinedCad, combinedUsd} currency-string object.
        positions: Dict mapping accountId -> list of position dicts from
            get_positions: {id, instrument, qty, side, avgPrice}.

    Returns:
        Total number of account_investment and cash rows written (excludes deletions).
    """
    now = datetime.now(timezone.utc).isoformat()
    written = 0

    balances = balances or {}
    positions = positions or {}
    canonical_id_by_source_id = _resolve_canonical_account_ids(accounts)

    # 1. Upsert Accounts, keyed by canonical account_id (not Questrade's uuid)
    for acc in accounts:
        source_id = str(acc.get("id") or acc.get("accountId"))
        canonical_id = canonical_id_by_source_id[source_id]
        _, acc_number = _parse_account_type_and_number(str(acc.get("name", "")))
        acc_name = acc.get("name") or f"{canonical_id} ({acc_number})"
        upsert_account(
            conn=conn,
            account_id=canonical_id,
            account_name=acc_name,
            account_type=canonical_id,
            base_currency="CAD",
        )

    # 2. Upsert Uninvested Cash as synthetic CASH_USD position; aggregate the
    #    broker-reported total ACROSS accounts before the single singleton write
    #    (broker_reported_total is one row, id=1 — a prior per-account call here
    #    silently overwrote itself down to just the last account processed).
    aggregate_total_usd = 0.0
    aggregate_total_cad = 0.0
    for source_id, bal in balances.items():
        acc_id = canonical_id_by_source_id.get(source_id, source_id)
        cash_leaf = bal.get("cash") or {}
        cash_usd = _parse_money(cash_leaf.get("usd"))
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

        total_equity_leaf = bal.get("totalEquity") or {}
        aggregate_total_usd += _parse_money(total_equity_leaf.get("combinedUsd"))
        aggregate_total_cad += _parse_money(total_equity_leaf.get("combinedCad"))

    if aggregate_total_usd > 0 and aggregate_total_cad > 0:
        inferred_rate = aggregate_total_cad / aggregate_total_usd
        upsert_exchange_rate(conn, inferred_rate, now)
        upsert_broker_reported_total(
            conn=conn,
            total_usd=aggregate_total_usd,
            total_cad=aggregate_total_cad,
            synced_at=now,
            source="Questrade MCP",
        )

    # 3. Upsert Security Positions, then clear anything stale for that account
    for source_id, pos_list in positions.items():
        acc_id = canonical_id_by_source_id.get(source_id, source_id)
        synced_symbols: set[str] = set()
        for pos in pos_list:
            raw_sym = pos.get("instrument") or pos.get("symbol") or ""
            if not raw_sym:
                continue

            symbol = normalize_ticker(raw_sym)
            synced_symbols.add(symbol)
            resolve_investment(conn, symbol, asset_class="EQUITY", currency="USD")
            qty = _parse_money(pos.get("qty") if pos.get("qty") is not None else pos.get("openQuantity"))
            avg_cost = _parse_money(pos.get("avgPrice"))
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

        cash_leaf = (balances.get(source_id) or {}).get("cash") or {}
        if _parse_money(cash_leaf.get("usd")) != 0.0:
            synced_symbols.add("CASH_USD")
        delete_stale_account_investments(conn, acc_id, keep_investment_ids=synced_symbols)

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
