"""Dry-run + real migration of trade-log.json/orders_executed.jsonl/cash_flows.json
into the v3.2 domain model (Wave 4 Task 6).

Non-negotiable per this migration's global constraints: --write must never run
without a --dry-run report first being reviewed and explicitly approved by the
user (tied to a real data-loss incident from before this corrective effort began).

Real confirmed shapes:
- trade-log.json: JSON list of {id, ticker, action, shares, price, totalCost,
  account, orderType, limitPrice, date, notes, status, source, priority,
  loggedAt, extendedHours, tvOrderId}. extendedHours/tvOrderId have no
  corresponding trade_log_entry DDL column and are intentionally dropped
  (documented in trade_log_entry_repository.py's own module docstring).
- orders_executed.jsonl: JSONL, one record per line:
  {timestamp, order: {ticker, side, shares, price}, decision, gate_result,
  trade_execution_result}. No stable id -- execution_id is derived
  deterministically from the record's own content (sha256, content-addressed)
  so re-running --write is idempotent. trade_execution_result has no
  corresponding order_execution DDL column and is intentionally dropped.
- cash_flows.json: {starting_balance_cad, starting_date, cash_flows: [
  {date, type, amount_cad, portfolio_value_before_flow_cad, account}, ...]}.
  starting_balance_cad/starting_date are a single global baseline, written to
  cash_flow_baseline under CASH_FLOW_BASELINE_SENTINEL_ACCOUNT ("ALL") per the
  decision documented in cash_flow_repository.py's module docstring.
"""

import argparse
import hashlib
import json

from domain_model.db_client import initialize_db
from domain_model.investment_repository import resolve_investment
from domain_model.account_repository import upsert_account
from domain_model.trade_log_entry_repository import upsert_trade_log_entry
from domain_model.order_execution_repository import insert_order_execution
from domain_model.cash_flow_repository import (
    insert_cash_flow,
    upsert_cash_flow_baseline,
    CASH_FLOW_BASELINE_SENTINEL_ACCOUNT,
)


def _load_json(path: str):
    with open(path) as f:
        return json.load(f)


def _load_jsonl(path: str) -> list[dict]:
    records = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def _content_hash_id(record: dict) -> str:
    """Deterministic id derived from a record's own content, for sources
    (orders_executed.jsonl, cash_flows.json's flows) that carry no stable id.
    Using a content hash (not uuid4) is what makes repeated --write runs
    idempotent -- the same source record always yields the same id.
    """
    blob = json.dumps(record, sort_keys=True).encode()
    return hashlib.sha256(blob).hexdigest()[:16]


def build_dry_run_report(
    trade_log_path: str,
    orders_executed_path: str,
    cash_flows_path: str,
) -> dict:
    trade_log = _load_json(trade_log_path)
    orders_executed = _load_jsonl(orders_executed_path)
    cash_flows_doc = _load_json(cash_flows_path)

    warnings = []

    trade_log_would_insert = 0
    for i, entry in enumerate(trade_log):
        if not entry.get("ticker"):
            warnings.append(
                f"trade_log[{i}] entry_id={entry.get('id')}: missing ticker field, "
                "will be skipped by execute_migration"
            )
            continue
        trade_log_would_insert += 1

    order_executions_would_insert = 0
    for i, record in enumerate(orders_executed):
        order_executions_would_insert += 1
        if record.get("trade_execution_result") is not None:
            warnings.append(
                f"orders_executed[{i}] timestamp={record.get('timestamp')}: "
                "non-null trade_execution_result has no corresponding "
                "order_execution DDL column, will be dropped silently"
            )

    cash_flows = cash_flows_doc.get("cash_flows", []) if isinstance(cash_flows_doc, dict) else []
    cash_flows_would_insert = 0
    for i, flow in enumerate(cash_flows):
        if not flow.get("account"):
            warnings.append(f"cash_flows[{i}] date={flow.get('date')}: missing account field")
        cash_flows_would_insert += 1

    cash_flow_baseline_present = bool(
        isinstance(cash_flows_doc, dict)
        and cash_flows_doc.get("starting_balance_cad") is not None
        and cash_flows_doc.get("starting_date") is not None
    )

    return {
        "trade_log_entries_count": len(trade_log),
        "trade_log_entries_would_insert_count": trade_log_would_insert,
        "order_executions_count": len(orders_executed),
        "order_executions_would_insert_count": order_executions_would_insert,
        "cash_flows_count": len(cash_flows),
        "cash_flows_would_insert_count": cash_flows_would_insert,
        "cash_flow_baseline_present": cash_flow_baseline_present,
        "warnings": warnings,
    }


def execute_migration(
    conn,
    trade_log_path: str,
    orders_executed_path: str,
    cash_flows_path: str,
) -> dict:
    trade_log = _load_json(trade_log_path)
    orders_executed = _load_jsonl(orders_executed_path)
    cash_flows_doc = _load_json(cash_flows_path)

    known_accounts: set[str] = set()

    trade_log_entries_inserted = 0
    for entry in trade_log:
        ticker = entry.get("ticker")
        if not ticker:
            continue

        investment_id = resolve_investment(conn, ticker, asset_class="EQUITY", currency="USD")

        account = entry.get("account")
        if account and account not in known_accounts:
            upsert_account(conn, account, account, account)
            known_accounts.add(account)

        upsert_trade_log_entry(conn, {
            "entry_id": entry.get("id"),
            "investment_id": investment_id,
            "account_id": account,
            "action": entry.get("action"),
            "shares": entry.get("shares"),
            "price": entry.get("price"),
            "total_cost": entry.get("totalCost"),
            "order_type": entry.get("orderType"),
            "limit_price": entry.get("limitPrice"),
            "trade_date": entry.get("date"),
            "notes": entry.get("notes"),
            "status": entry.get("status"),
            "source": entry.get("source"),
            "priority": entry.get("priority"),
            "logged_at": entry.get("loggedAt"),
        })
        trade_log_entries_inserted += 1

    order_executions_inserted = 0
    for record in orders_executed:
        order = record.get("order", {}) or {}
        ticker = order.get("ticker")
        investment_id = None
        if ticker:
            investment_id = resolve_investment(conn, ticker, asset_class="EQUITY", currency="USD")

        execution_id = _content_hash_id(record)
        insert_order_execution(conn, {
            "execution_id": execution_id,
            "executed_at": record.get("timestamp"),
            "investment_id": investment_id,
            "side": order.get("side"),
            "shares": order.get("shares"),
            "price": order.get("price"),
            "decision": record.get("decision"),
            "gate_result_json": json.dumps(record.get("gate_result"))
            if record.get("gate_result") is not None else None,
        })
        order_executions_inserted += 1

    cash_flows = cash_flows_doc.get("cash_flows", []) if isinstance(cash_flows_doc, dict) else []
    cash_flows_inserted = 0
    for flow in cash_flows:
        flow_id = _content_hash_id(flow)
        insert_cash_flow(conn, {
            "flow_id": flow_id,
            "flow_date": flow.get("date"),
            "flow_type": flow.get("type"),
            "amount_cad": flow.get("amount_cad"),
            "portfolio_value_before_flow_cad": flow.get("portfolio_value_before_flow_cad"),
            "account": flow.get("account"),
        })
        cash_flows_inserted += 1

    cash_flow_baseline_written = False
    if isinstance(cash_flows_doc, dict) and cash_flows_doc.get("starting_balance_cad") is not None:
        upsert_cash_flow_baseline(
            conn,
            CASH_FLOW_BASELINE_SENTINEL_ACCOUNT,
            cash_flows_doc.get("starting_balance_cad"),
            cash_flows_doc.get("starting_date"),
        )
        cash_flow_baseline_written = True

    return {
        "trade_log_entries_inserted": trade_log_entries_inserted,
        "order_executions_inserted": order_executions_inserted,
        "cash_flows_inserted": cash_flows_inserted,
        "cash_flow_baseline_written": cash_flow_baseline_written,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--trade-log",
                         default="investment_screener/backend/data/trade-log.json")
    parser.add_argument("--orders-executed",
                         default="investment_screener/backend/data/orders_executed.jsonl")
    parser.add_argument("--cash-flows",
                         default="investment_screener/backend/data/cash_flows.json")
    parser.add_argument("--db-path",
                         default="investment_screener/backend/data/domain_model.sqlite")
    parser.add_argument("--write", action="store_true",
                         help="Perform the real migration. Requires reviewing a --dry-run "
                              "report first -- never run this without explicit user sign-off.")
    args = parser.parse_args()

    report = build_dry_run_report(args.trade_log, args.orders_executed, args.cash_flows)
    print(json.dumps(report, indent=2))

    if args.write:
        conn = initialize_db(args.db_path)
        summary = execute_migration(conn, args.trade_log, args.orders_executed, args.cash_flows)
        print("--- WRITE SUMMARY ---")
        print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
