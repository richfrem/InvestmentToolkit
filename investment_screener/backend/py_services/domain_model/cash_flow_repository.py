"""All ``cash_flow`` and ``cash_flow_baseline`` table reads and writes live here.

Sentinel-account decision (Task 4, documented for Task 6's migration script to reuse):
the real source file (``data/cash_flows.json``) stores ``starting_balance_cad`` /
``starting_date`` as TOP-LEVEL fields — a single global baseline — while individual
cash-flow rows each carry a per-flow ``account`` (e.g. "TFSA"). The ``cash_flow_baseline``
DDL's primary key is ``account`` (per-account), so there is a genuine shape mismatch
between the JSON source (one global baseline) and the table (keyed per account).

Re-reading ``ytd_return.py::calculate_twr`` (the sole real consumer of this baseline)
confirms it reads ``flows_data.get("starting_balance_cad", 0.0)`` as one global scalar
and feeds ALL cash-flow rows (regardless of their individual ``account`` field) into a
single simple-return / TWR calculation — the balance math is never disambiguated per
account, even though the flow rows themselves carry an ``account`` tag for record-keeping.

Decision: the global baseline is stored under the sentinel account value ``"ALL"``.
``get_cash_flow_baseline(conn, "ALL")`` is the one baseline row Task 6's migration script
should write from ``cash_flows.json``'s top-level fields. Individual ``cash_flow`` rows
keep their real per-account values (``"TFSA"``, etc.) — only the baseline is collapsed to
the sentinel, matching the real JSON's actual (lack of) structure instead of inventing a
per-account baseline the source data doesn't have.
"""

import sqlite3

CASH_FLOW_BASELINE_SENTINEL_ACCOUNT = "ALL"


def insert_cash_flow(conn: sqlite3.Connection, flow: dict) -> str:
    """Idempotent upsert of a single cash_flow row, keyed on flow_id.

    ``flow`` is a dict keyed by DDL columns: flow_id, flow_date, flow_type,
    amount_cad, portfolio_value_before_flow_cad, account. The JSON source has no
    ``flow_id`` — the caller (migration script) is responsible for generating one.
    """
    conn.execute(
        "INSERT INTO cash_flow "
        "(flow_id, flow_date, flow_type, amount_cad, portfolio_value_before_flow_cad, account) "
        "VALUES (?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(flow_id) DO UPDATE SET "
        "flow_date=excluded.flow_date, flow_type=excluded.flow_type, "
        "amount_cad=excluded.amount_cad, "
        "portfolio_value_before_flow_cad=excluded.portfolio_value_before_flow_cad, "
        "account=excluded.account;",
        (
            flow["flow_id"],
            flow.get("flow_date"),
            flow.get("flow_type"),
            flow.get("amount_cad"),
            flow.get("portfolio_value_before_flow_cad"),
            flow.get("account"),
        ),
    )
    conn.commit()
    return flow["flow_id"]


def list_cash_flows(conn: sqlite3.Connection, account: str | None = None) -> list[dict]:
    conn.row_factory = sqlite3.Row
    query = "SELECT * FROM cash_flow WHERE 1=1"
    params: list = []
    if account:
        query += " AND account = ?"
        params.append(account)
    cursor = conn.execute(query, params)
    return [dict(row) for row in cursor.fetchall()]


def get_cash_flow_baseline(conn: sqlite3.Connection, account: str) -> dict | None:
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(
        "SELECT * FROM cash_flow_baseline WHERE account = ?;", (account,)
    )
    row = cursor.fetchone()
    return dict(row) if row else None


def upsert_cash_flow_baseline(
    conn: sqlite3.Connection,
    account: str,
    starting_balance_cad: float,
    starting_date: str,
) -> None:
    conn.execute(
        "INSERT INTO cash_flow_baseline (account, starting_balance_cad, starting_date) "
        "VALUES (?, ?, ?) "
        "ON CONFLICT(account) DO UPDATE SET "
        "starting_balance_cad=excluded.starting_balance_cad, "
        "starting_date=excluded.starting_date;",
        (account, starting_balance_cad, starting_date),
    )
    conn.commit()
