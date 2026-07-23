#!/usr/bin/env python3
"""One-time real-data correction: merge the PSU.U.TO/PSU-U.TO investment_id split
in account_investment into the canonical PSU-U.TO row, and backfill a price row
for CASH_USD (price=1.0, matching the average_cost already used for cash
positions elsewhere in this codebase).

Root cause (2026-07-22): the most recent real broker sync (19:09 UTC) ran against
a compiled backend build that predated tickerAliases.ts's normalizeTicker() being
wired into the account_investment write path, so PSU shares were recorded under
the broker's raw 'PSU.U.TO' investment_id instead of canonical 'PSU-U.TO'.
Meanwhile CASH_USD has never had a price row at all. Because
PortfolioRepository.getAccountMarketValues() uses an INNER JOIN against
investment_price, both silently contributed $0 to the computed portfolio total —
a ~$3,000 USD (~$4,200 CAD) understatement.

Usage:
    python3 fix_psu_alias_and_cash_price.py --dry-run
    python3 fix_psu_alias_and_cash_price.py --write
"""
import argparse
import sqlite3
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB_PATH = REPO_ROOT / "investment_screener/backend/data/domain_model.sqlite"

BROKER_SYMBOL = "PSU.U.TO"
CANONICAL_SYMBOL = "PSU-U.TO"
CASH_SYMBOL = "CASH_USD"


def run(db_path: Path, psu_price: float, dry_run: bool = True) -> dict:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    report: dict = {}

    broker_rows = conn.execute(
        "SELECT * FROM account_investment WHERE investment_id = ?", (BROKER_SYMBOL,)
    ).fetchall()
    report["broker_alias_rows_found"] = [dict(r) for r in broker_rows]

    canonical_rows = conn.execute(
        "SELECT * FROM account_investment WHERE investment_id = ?", (CANONICAL_SYMBOL,)
    ).fetchall()
    report["canonical_rows_before"] = [dict(r) for r in canonical_rows]

    cash_price_row = conn.execute(
        "SELECT * FROM investment_price WHERE investment_id = ?", (CASH_SYMBOL,)
    ).fetchone()
    report["cash_price_row_before"] = dict(cash_price_row) if cash_price_row else None

    psu_price_row = conn.execute(
        "SELECT * FROM investment_price WHERE investment_id = ?", (CANONICAL_SYMBOL,)
    ).fetchone()
    report["psu_price_row_before"] = dict(psu_price_row) if psu_price_row else None

    report["psu_live_price_to_write"] = psu_price

    if dry_run:
        conn.close()
        return report

    now_rows = conn.execute(
        "SELECT datetime('now') AS now"
    ).fetchone()
    now = now_rows["now"] + "Z"

    for row in broker_rows:
        # Re-point each broker-alias row at the canonical investment_id. If a
        # canonical row already exists for this account, merge quantities
        # (ON CONFLICT), never silently overwrite or duplicate.
        conn.execute(
            """
            INSERT INTO account_investment
                (account_investment_id, account_id, investment_id, quantity, average_cost, book_value, currency, last_synced_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(account_investment_id) DO UPDATE SET
                quantity = excluded.quantity,
                average_cost = excluded.average_cost,
                last_synced_at = excluded.last_synced_at
            """,
            (
                f"{row['account_id']}:{CANONICAL_SYMBOL}",
                row["account_id"],
                CANONICAL_SYMBOL,
                row["quantity"],
                row["average_cost"],
                row["book_value"],
                row["currency"],
                now,
            ),
        )
        conn.execute(
            "DELETE FROM account_investment WHERE account_investment_id = ?",
            (row["account_investment_id"],),
        )

    conn.execute(
        """
        INSERT INTO investment_price (investment_id, price, currency, fetched_at)
        VALUES (?, ?, 'USD', ?)
        ON CONFLICT(investment_id) DO UPDATE SET
            price = excluded.price, currency = excluded.currency, fetched_at = excluded.fetched_at
        """,
        (CANONICAL_SYMBOL, psu_price, now),
    )
    conn.execute(
        """
        INSERT INTO investment_price (investment_id, price, currency, fetched_at)
        VALUES (?, 1.0, 'USD', ?)
        ON CONFLICT(investment_id) DO UPDATE SET
            price = excluded.price, currency = excluded.currency, fetched_at = excluded.fetched_at
        """,
        (CASH_SYMBOL, now),
    )

    conn.commit()

    canonical_rows_after = conn.execute(
        "SELECT * FROM account_investment WHERE investment_id = ?", (CANONICAL_SYMBOL,)
    ).fetchall()
    report["canonical_rows_after"] = [dict(r) for r in canonical_rows_after]

    remaining_broker_rows = conn.execute(
        "SELECT * FROM account_investment WHERE investment_id = ?", (BROKER_SYMBOL,)
    ).fetchall()
    report["broker_alias_rows_remaining"] = [dict(r) for r in remaining_broker_rows]

    total = conn.execute(
        """
        SELECT SUM(market_value) FROM (
            SELECT ai.account_id, SUM(ai.quantity * ip.price) AS market_value
            FROM account_investment ai
            JOIN investment_price ip ON ip.investment_id = ai.investment_id
            GROUP BY ai.account_id
        )
        """
    ).fetchone()[0]
    report["recomputed_total_usd"] = total

    conn.close()
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--psu-price", type=float, required=True, help="Real live PSU-U.TO price to write")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true")
    group.add_argument("--write", action="store_true")
    args = parser.parse_args()

    import json
    report = run(Path(args.db_path), args.psu_price, dry_run=args.dry_run)
    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
