"""Tests for generate_portfolio_blueprint.py's Wave 1 Task 7C rewire of the two
projections/{TICKER}.json read sites onto domain_model.sqlite (ADR-029):
`_get_latest_ai_projection` (used in generate_section's AI Signal / Upside
column) and `_get_latest_ai_agent_projection` (used by update_section_tables's
`get_ai_signal`, which must stay strictly AI_AGENT-only, no fallback).

Also covers the Wave 2 rewire of `build_thesis_map`, which used to read
`target-portfolio.json` holdings directly and now reads per-investment thesis
fields (target_weight, lifecycle_status, thesis_for_inclusion, sub_strategy_id/
pillar_id) via `domain_model.investment_repository.list_investments`.

All tests run against a `tmp_path`-backed SQLite database via `initialize_db` —
never the real `data/domain_model.sqlite` file.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "plugins/portfolio-advisor/scripts"))
sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))

from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.investment_repository import (  # noqa: E402
    resolve_investment,
    update_investment_fields,
)
from domain_model.pillar_repository import resolve_pillar, resolve_sub_strategy  # noqa: E402
from domain_model.projection_repository import save_projection_version  # noqa: E402

import generate_portfolio_blueprint as gpb  # noqa: E402


def test_build_thesis_map_reads_from_sqlite_not_json(tmp_path):
    """build_thesis_map must source targetPct/role/thesisNote/subStrategyId
    from investment columns, not target-portfolio.json."""
    db_path = tmp_path / "test.sqlite"
    conn = initialize_db(str(db_path))
    try:
        resolve_pillar(conn, "ai-compute", "AI Compute")
        resolve_sub_strategy(conn, "sa-asi-race", "ai-compute", "SA / ASI Race")
        nvda_id = resolve_investment(conn, "NVDA", asset_class="EQUITY")
        update_investment_fields(
            conn, nvda_id,
            pillar_id="ai-compute", sub_strategy_id="sa-asi-race",
            target_weight=5.5, lifecycle_status="accumulate",
            thesis_for_inclusion="Highest-conviction BUY.",
        )
        # Watchlist-only row (no pillar_id) must be excluded, matching the
        # original JSON read's implicit scope (thesis.holdings only).
        wl_id = resolve_investment(conn, "ZZZZ", asset_class="EQUITY")
        update_investment_fields(conn, wl_id, is_watchlisted=True)
    finally:
        conn.close()

    thesis_map = gpb.build_thesis_map(db_path)
    assert thesis_map["NVDA"] == {
        "subStrategyId": "sa-asi-race",
        "targetPct": 5.5,
        "role": "accumulate",
        "thesisNote": "Highest-conviction BUY.",
        "thesisBreakers": [],
    }
    assert "ZZZZ" not in thesis_map


def test_get_latest_ai_projection_returns_none_for_unknown_ticker(tmp_path):
    db_path = tmp_path / "test.sqlite"
    initialize_db(str(db_path)).close()
    assert gpb._get_latest_ai_projection("ZZZZ", db_path=db_path) is None


def test_get_latest_ai_projection_prefers_ai_agent_source(tmp_path):
    """AI_AGENT row must win even when a newer non-AI_AGENT row exists."""
    db_path = tmp_path / "test.sqlite"
    conn = initialize_db(str(db_path))
    try:
        investment_id = resolve_investment(conn, "NVDA", asset_class="EQUITY")
        save_projection_version(
            conn, investment_id, version=1, saved_at="2026-06-01T00:00:00Z",
            fair_value=300.0, action="ACCUMULATE", source="AI_AGENT",
        )
        save_projection_version(
            conn, investment_id, version=2, saved_at="2026-07-01T00:00:00Z",
            fair_value=310.0, action="TRIM", source="USER",
        )
    finally:
        conn.close()

    entry = gpb._get_latest_ai_projection("NVDA", db_path=db_path)
    assert entry is not None
    assert entry["fair_value"] == 300.0
    assert entry["action"] == "ACCUMULATE"


def test_get_latest_ai_projection_falls_back_to_any_source(tmp_path):
    """No AI_AGENT row for this ticker -> falls back to MAX(version) of any source."""
    db_path = tmp_path / "test.sqlite"
    conn = initialize_db(str(db_path))
    try:
        investment_id = resolve_investment(conn, "DXYZ", asset_class="ETF")
        save_projection_version(
            conn, investment_id, version=1, saved_at="2026-07-01T00:00:00Z",
            fair_value=40.0, action="INITIATE", source="ETF_ANALYSIS",
        )
    finally:
        conn.close()

    entry = gpb._get_latest_ai_projection("DXYZ", db_path=db_path)
    assert entry is not None
    assert entry["fair_value"] == 40.0
    assert entry["action"] == "INITIATE"


def test_get_latest_ai_agent_projection_strict_no_fallback(tmp_path):
    """get_ai_signal's helper must return None (not fall back) when no AI_AGENT
    row exists, even if other-sourced rows exist — matches the original file-based
    code's `[p for p in projs if p.get("source") == "AI_AGENT"]` with no fallback."""
    db_path = tmp_path / "test.sqlite"
    conn = initialize_db(str(db_path))
    try:
        investment_id = resolve_investment(conn, "DXYZ", asset_class="ETF")
        save_projection_version(
            conn, investment_id, version=1, saved_at="2026-07-01T00:00:00Z",
            fair_value=40.0, action="INITIATE", source="ETF_ANALYSIS",
        )
    finally:
        conn.close()

    assert gpb._get_latest_ai_agent_projection("DXYZ", db_path=db_path) is None


def test_get_latest_ai_agent_projection_returns_latest_by_saved_at(tmp_path):
    """Picks latest by saved_at, not MAX(version), matching the original
    `max(ai, key=lambda x: x.get("savedAt", ""))` semantics."""
    db_path = tmp_path / "test.sqlite"
    conn = initialize_db(str(db_path))
    try:
        investment_id = resolve_investment(conn, "AMD", asset_class="EQUITY")
        save_projection_version(
            conn, investment_id, version=2, saved_at="2026-05-01T00:00:00Z",
            fair_value=180.0, action="MAINTAIN", source="AI_AGENT",
        )
        save_projection_version(
            conn, investment_id, version=1, saved_at="2026-07-01T00:00:00Z",
            fair_value=200.0, action="BUY", source="AI_AGENT",
        )
    finally:
        conn.close()

    entry = gpb._get_latest_ai_agent_projection("AMD", db_path=db_path)
    assert entry is not None
    assert entry["action"] == "BUY"
    assert entry["fair_value"] == 200.0


def test_get_ai_signal_no_real_io(tmp_path, monkeypatch):
    """update_section_tables's nested get_ai_signal must resolve through the DB
    helper, not read projections/{TICKER}.json."""
    db_path = tmp_path / "test.sqlite"
    conn = initialize_db(str(db_path))
    try:
        investment_id = resolve_investment(conn, "MSFT", asset_class="EQUITY")
        save_projection_version(
            conn, investment_id, version=1, saved_at="2026-06-01T00:00:00Z",
            fair_value=500.0, action="ACCUMULATE", source="AI_AGENT",
        )
    finally:
        conn.close()

    monkeypatch.setattr(gpb, "DOMAIN_DB", db_path)

    content = (
        "| Ticker | Role | Conviction Note |\n"
        "| :--- | :--- | :--- |\n"
        "| **MSFT** | CORE | Cloud + AI |\n"
    )
    current_data = {"holdings": {"MSFT": 5.0}}
    target_data = {"holdings": {"MSFT": 6.0}}

    updated = gpb.update_section_tables(content, current_data, target_data)
    assert "ACCUMULATE" in updated
