"""Migrate portfolio.json (gitignored, real broker/account holdings) into
account_investment/investment_price. Dry-run by default; --write is gated,
same discipline as migrate_target_portfolio_to_sqlite.py (Wave 2).

Per ADR-030 and Task 0's real-shape finding: per-account attribution comes
from tvSnapshot.snapshots[].positions[] (real accountType/accountId, real
quantity/avgFillPrice) -- NOT from the flat, cross-account-aggregated
holdings[] array, which carries no per-account field in real data. Cash
(balances.cashUSD/cashCAD per account) becomes CASH_USD/CASH_CAD
account_investment rows per Wave 0's resolved decision 5, not a separate
table. The current market price for each symbol still comes from the flat
holdings[] array (the only place a live per-symbol price appears), joined
by symbol.
"""

import argparse
import json
from datetime import datetime, timezone

from domain_model.account_repository import upsert_account
from domain_model.account_investment_repository import upsert_account_investment
from domain_model.investment_price_repository import upsert_investment_price
from domain_model.investment_repository import resolve_investment
from domain_model.db_client import initialize_db
from domain_model.seed_real_accounts import seed_real_accounts


def _load_portfolio_json(portfolio_path: str) -> dict:
    with open(portfolio_path) as f:
        return json.load(f)


def _load_snapshots(data: dict) -> list[dict]:
    return data.get("tvSnapshot", {}).get("snapshots", [])


def _load_prices_by_symbol(data: dict) -> dict[str, float]:
    prices = {}
    for h in data.get("holdings", []):
        symbol = h.get("symbol") or h.get("ticker")
        price = float(h.get("price") or h.get("book_price") or 0)
        if symbol and price > 0:
            prices[symbol] = price
    return prices


def run_dry_run_migration(portfolio_path: str) -> dict:
    data = _load_portfolio_json(portfolio_path)
    snapshots = _load_snapshots(data)
    accounts_found = {s["accountType"] for s in snapshots}
    positions_count = sum(len(s.get("positions", [])) for s in snapshots)
    return {
        "positions_count": positions_count,
        "accounts_found": accounts_found,
    }


def run_real_migration(portfolio_path: str, db_path: str) -> dict:
    data = _load_portfolio_json(portfolio_path)
    snapshots = _load_snapshots(data)
    prices_by_symbol = _load_prices_by_symbol(data)
    conn = initialize_db(db_path)
    seed_real_accounts(conn)

    now = datetime.now(timezone.utc).isoformat()
    positions_written = 0
    for snap in snapshots:
        account_id = snap["accountType"]
        if account_id not in ("TFSA", "RRSP", "CASH"):
            continue  # Only the three real, seeded broker sub-accounts (TFSA/RRSP/CASH)
            # are in scope; anything else is unrecognized and intentionally skipped.
        upsert_account(conn, account_id, account_id, account_id)

        cash_usd = float(snap.get("balances", {}).get("cashUSD") or 0)
        if cash_usd > 0:
            cash_id = resolve_investment(conn, "CASH_USD", asset_class="CASH", currency="USD")
            upsert_account_investment(
                conn, account_id, cash_id, quantity=cash_usd, average_cost=1.0,
                book_value=cash_usd, currency="USD", last_synced_at=now,
            )

        for pos in snap.get("positions", []):
            quantity = float(pos.get("quantity") or 0)
            if quantity <= 0:
                continue  # closed/flattened position in a stale snapshot -- no noise row
            symbol = pos["symbol"]
            investment_id = resolve_investment(conn, symbol, asset_class="EQUITY", currency="USD")
            price = prices_by_symbol.get(symbol, 0)
            if price > 0:
                upsert_investment_price(conn, investment_id, price=price, currency="USD", fetched_at=now)
            upsert_account_investment(
                conn,
                account_id,
                investment_id,
                quantity=quantity,
                average_cost=pos.get("avgFillPrice"),
                book_value=None,
                currency="USD",
                last_synced_at=now,
            )
            positions_written += 1

    return {"account_investments_written": positions_written}


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate portfolio.json into account_investment/investment_price.")
    parser.add_argument("--portfolio-path", default="investment_screener/backend/data/portfolio.json")
    parser.add_argument("--db-path", default="investment_screener/backend/data/domain_model.sqlite")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    if args.write:
        report = run_real_migration(args.portfolio_path, args.db_path)
        print("[WRITE MODE]", json.dumps(report, indent=2, default=list))
    else:
        report = run_dry_run_migration(args.portfolio_path)
        print("[DRY RUN]", json.dumps(report, indent=2, default=list))


if __name__ == "__main__":
    main()
