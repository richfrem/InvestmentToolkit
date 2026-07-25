"""All ``portfolio_policy`` table reads and writes live here (ADR-029 anti-duplication rule).

Singleton table (one row, policy_id='default'): the account/portfolio-level policy
config Wave 5E migrates from account_policy.json (accountPreferenceRules, psuFundingRule,
riskBudgetCaps, bandConfig) plus target-portfolio.json's globalSettings sub-object
(rebalanceFrequency, portfolioValueUSD). The two JSON rule-blob columns
(account_preference_rules_json, psu_funding_rule_json) are the approved retained-JSON
exception per spec §2.14/§2.17 -- variable-shape rule lists, not column-queried.
"""

import sqlite3
from datetime import datetime, timezone

POLICY_ID = "default"

_UPDATABLE_FIELDS = {
    "rebalance_frequency",
    "portfolio_value_usd_target",
    "max_marginal_risk_contribution_pct",
    "max_cluster_variance_contribution_pct",
    "rebalance_band_relative_pct",
    "rebalance_band_absolute_pct",
    "rebalance_band_critical_multiplier",
    "account_preference_rules_json",
    "psu_funding_rule_json",
}


def upsert_portfolio_policy(conn: sqlite3.Connection, **fields) -> None:
    """Insert or partially update the single portfolio_policy row.

    Only the passed fields are changed -- an omitted field on an update leaves the
    existing value untouched (matches investment_repository.py::update_investment_fields'
    partial-update contract). On first insert, unset fields default to NULL.

    Raises ValueError on an unrecognized field name -- fail loud rather than silently
    no-op.
    """
    unknown = set(fields) - _UPDATABLE_FIELDS
    if unknown:
        raise ValueError(f"Unknown portfolio_policy field(s): {sorted(unknown)}")

    now = datetime.now(timezone.utc).isoformat()
    existing = conn.execute(
        "SELECT policy_id FROM portfolio_policy WHERE policy_id = ?;", (POLICY_ID,)
    ).fetchone()

    if existing is None:
        columns = ["policy_id", "updated_at", *fields.keys()]
        placeholders = ", ".join("?" for _ in columns)
        values = [POLICY_ID, now, *fields.values()]
        conn.execute(
            f"INSERT INTO portfolio_policy ({', '.join(columns)}) VALUES ({placeholders});",
            values,
        )
    else:
        if fields:
            set_clause = ", ".join(f"{key} = ?" for key in fields)
            conn.execute(
                f"UPDATE portfolio_policy SET {set_clause}, updated_at = ? "
                f"WHERE policy_id = ?;",
                [*fields.values(), now, POLICY_ID],
            )
        else:
            conn.execute(
                "UPDATE portfolio_policy SET updated_at = ? WHERE policy_id = ?;",
                (now, POLICY_ID),
            )
    conn.commit()


def get_portfolio_policy(conn: sqlite3.Connection) -> dict | None:
    """Return the single portfolio_policy row as a dict, or None if never written."""
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT * FROM portfolio_policy WHERE policy_id = ?;", (POLICY_ID,)
    ).fetchone()
    return dict(row) if row else None
