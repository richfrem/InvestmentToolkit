"""All `projection_version`/`projection_scenario` table reads and writes live here
(ADR-029 anti-duplication rule, mirrors investment_repository.py's pattern from Wave 0).
"""

import sqlite3


def save_projection_version(
    conn: sqlite3.Connection,
    investment_id: str,
    version: int,
    saved_at: str,
    analyzed_at: str | None = None,
    model: str | None = None,
    fair_value: float | None = None,
    action: str | None = None,
    rationale: str | None = None,
    research_event_id: str | None = None,
    snapshot_json: str | None = None,
    analytics_log_json: str | None = None,
) -> str:
    """Insert or update a projection version row.

    Upsert on ``(investment_id, version)``: this function persists whatever version
    number it is given and does not compute the next version itself — that
    responsibility stays with the caller, mirroring ``ProjectionService.ts``'s existing
    upsert-by-id-then-version-increment split.
    """
    projection_id = f"{investment_id}:{version}"
    conn.execute(
        "INSERT INTO projection_version "
        "(projection_id, investment_id, version, saved_at, analyzed_at, model, fair_value, "
        "action, rationale, research_event_id, snapshot_json, analytics_log_json) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(investment_id, version) DO UPDATE SET "
        "saved_at=excluded.saved_at, analyzed_at=excluded.analyzed_at, model=excluded.model, "
        "fair_value=excluded.fair_value, action=excluded.action, rationale=excluded.rationale, "
        "research_event_id=excluded.research_event_id, snapshot_json=excluded.snapshot_json, "
        "analytics_log_json=excluded.analytics_log_json;",
        (
            projection_id, investment_id, version, saved_at, analyzed_at, model, fair_value,
            action, rationale, research_event_id, snapshot_json, analytics_log_json,
        ),
    )
    conn.commit()
    return projection_id


def get_latest_projection(conn: sqlite3.Connection, investment_id: str) -> dict | None:
    """Return the highest-version projection row for an investment, or ``None``."""
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(
        "SELECT * FROM projection_version WHERE investment_id = ? "
        "ORDER BY version DESC LIMIT 1;",
        (investment_id,),
    )
    row = cursor.fetchone()
    return dict(row) if row else None


def list_projection_versions(conn: sqlite3.Connection, investment_id: str) -> list[dict]:
    """Return all projection versions for an investment, ascending by version.

    Mirrors ``ProjectionService.getProjections()``'s full-array return shape.
    """
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(
        "SELECT * FROM projection_version WHERE investment_id = ? ORDER BY version ASC;",
        (investment_id,),
    )
    return [dict(row) for row in cursor.fetchall()]


def add_projection_scenario(
    conn: sqlite3.Connection,
    projection_id: str,
    scenario_name: str,
    weight: float | None = None,
    growth_rate: float | None = None,
    net_margin: float | None = None,
    exit_pe: float | None = None,
    quality_multiplier: float | None = None,
    share_change: float | None = None,
    rationale: str | None = None,
    moat_score: int | None = None,
    management_score: int | None = None,
    year5_revenue: float | None = None,
    year5_net_income: float | None = None,
    year5_eps: float | None = None,
    scenario_price: float | None = None,
    risks_json: str | None = None,
) -> str:
    """Insert or update a projection scenario row. Upsert on ``(projection_id, scenario_name)``."""
    scenario_id = f"{projection_id}:{scenario_name}"
    conn.execute(
        "INSERT INTO projection_scenario "
        "(scenario_id, projection_id, scenario_name, weight, growth_rate, net_margin, exit_pe, "
        "quality_multiplier, share_change, rationale, moat_score, management_score, "
        "year5_revenue, year5_net_income, year5_eps, scenario_price, risks_json) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(projection_id, scenario_name) DO UPDATE SET "
        "weight=excluded.weight, growth_rate=excluded.growth_rate, "
        "net_margin=excluded.net_margin, exit_pe=excluded.exit_pe, "
        "quality_multiplier=excluded.quality_multiplier, share_change=excluded.share_change, "
        "rationale=excluded.rationale, moat_score=excluded.moat_score, "
        "management_score=excluded.management_score, year5_revenue=excluded.year5_revenue, "
        "year5_net_income=excluded.year5_net_income, year5_eps=excluded.year5_eps, "
        "scenario_price=excluded.scenario_price, risks_json=excluded.risks_json;",
        (
            scenario_id, projection_id, scenario_name, weight, growth_rate, net_margin, exit_pe,
            quality_multiplier, share_change, rationale, moat_score, management_score,
            year5_revenue, year5_net_income, year5_eps, scenario_price, risks_json,
        ),
    )
    conn.commit()
    return scenario_id


def get_projection_scenarios(conn: sqlite3.Connection, projection_id: str) -> list[dict]:
    """Return all scenario rows for a projection. Empty list, not an error, for legacy
    projections that have no ``scenarios`` block (apply_catalyst.py:176-179)."""
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(
        "SELECT * FROM projection_scenario WHERE projection_id = ?;", (projection_id,),
    )
    return [dict(row) for row in cursor.fetchall()]
