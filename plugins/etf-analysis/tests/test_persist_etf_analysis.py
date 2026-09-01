"""Tests for persist_etf_analysis.py's Wave 1 Task 7B rewire of the
Dashboard-facing projection sync onto domain_model.sqlite (ADR-029). The
data/etf_analysis/ versions-file write is unaffected and out of scope — only the
second "dual-write" half (pitfall #8) that used to write
data/projections/{TICKER}.json moved to SQLite. All tests run against a
`tmp_path`-backed SQLite database via `initialize_db` — never the real
`data/domain_model.sqlite` file.
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = REPO_ROOT / "plugins/etf-analysis/skills/etf_analysis/scripts"
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))

from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.projection_repository import (  # noqa: E402
    get_latest_projection_by_source,
    get_projection_scenarios,
)

import persist_etf_analysis  # noqa: E402


SAMPLE_ETF = {
    "ticker": "DXYZ",
    "name": "Destiny Tech100",
    "fundType": "THEMATIC_ETF",
    "savedAt": "2026-07-19T00:00:00Z",
    "action": "INITIATE",
    "rationale": "AI/private-tech exposure thesis.",
    "actionRationale": "Undervalued vs NAV.",
    "snapshot": {"price": 40.24, "currency": "USD"},
    "holdingsAnalysis": {
        "thesisAlignmentScore": 72,
        "topHoldings": [{"symbol": "SPACEX", "holdingPct": 20, "alignment": "core", "note": "n/a"}],
    },
    "upsideCatalysts": ["IPO wave"],
    "risks": ["Illiquidity"],
}


def _write_etf_versions_file(monkeypatch, tmp_path):
    data_dir = tmp_path / "etf_analysis"
    monkeypatch.setattr(persist_etf_analysis, "DATA_DIR", data_dir)
    return data_dir


def test_persist_writes_etf_analysis_projection_to_db(tmp_path, monkeypatch):
    _write_etf_versions_file(monkeypatch, tmp_path)
    db_path = tmp_path / "test.sqlite"

    persist_etf_analysis.persist(dict(SAMPLE_ETF), dry_run=False, db_path=db_path)

    conn = initialize_db(str(db_path))
    try:
        investment_id = conn.execute(
            "SELECT investment_id FROM investment WHERE symbol = ?;", ("DXYZ",)
        ).fetchone()[0]
        row = get_latest_projection_by_source(conn, investment_id, "ETF_ANALYSIS")
        assert row is not None
        assert row["action"] == "INITIATE"
        snapshot = json.loads(row["snapshot_json"])
        assert snapshot["price"] == 40.24

        scenarios = get_projection_scenarios(conn, row["projection_id"])
        names = {s["scenario_name"] for s in scenarios}
        assert names == {"bear", "base", "bull"}
    finally:
        conn.close()


def test_persist_replaces_prior_etf_analysis_row_not_duplicates(tmp_path, monkeypatch):
    _write_etf_versions_file(monkeypatch, tmp_path)
    db_path = tmp_path / "test.sqlite"

    persist_etf_analysis.persist(dict(SAMPLE_ETF), dry_run=False, db_path=db_path)
    updated = dict(SAMPLE_ETF)
    updated["action"] = "ACCUMULATE"
    persist_etf_analysis.persist(updated, dry_run=False, db_path=db_path)

    conn = initialize_db(str(db_path))
    try:
        investment_id = conn.execute(
            "SELECT investment_id FROM investment WHERE symbol = ?;", ("DXYZ",)
        ).fetchone()[0]
        all_rows = conn.execute(
            "SELECT version, action, source FROM projection_version WHERE investment_id = ?;",
            (investment_id,),
        ).fetchall()
        etf_rows = [r for r in all_rows if r[2] == "ETF_ANALYSIS"]
        assert len(etf_rows) == 1  # replaced in place, not duplicated
        assert etf_rows[0][1] == "ACCUMULATE"
    finally:
        conn.close()


def test_persist_dry_run_does_not_write_db(tmp_path, monkeypatch):
    _write_etf_versions_file(monkeypatch, tmp_path)
    db_path = tmp_path / "test.sqlite"

    persist_etf_analysis.persist(dict(SAMPLE_ETF), dry_run=True, db_path=db_path)

    assert not db_path.exists()


def test_persist_new_etf_version_does_not_collide_with_existing_ai_agent_version(tmp_path, monkeypatch):
    """A prior AI_AGENT projection at version 3 must not be overwritten by an
    ETF_ANALYSIS sync — the new ETF row gets its own version number."""
    _write_etf_versions_file(monkeypatch, tmp_path)
    db_path = tmp_path / "test.sqlite"

    conn = initialize_db(str(db_path))
    try:
        from domain_model.investment_repository import resolve_investment
        from domain_model.projection_repository import save_projection_version

        investment_id = resolve_investment(conn, "DXYZ", asset_class="ETF")
        save_projection_version(
            conn, investment_id, version=3, saved_at="2026-06-01T00:00:00Z",
            fair_value=41.0, action="HOLD", source="AI_AGENT",
        )
    finally:
        conn.close()

    persist_etf_analysis.persist(dict(SAMPLE_ETF), dry_run=False, db_path=db_path)

    conn = initialize_db(str(db_path))
    try:
        investment_id = conn.execute(
            "SELECT investment_id FROM investment WHERE symbol = ?;", ("DXYZ",)
        ).fetchone()[0]
        ai_row = get_latest_projection_by_source(conn, investment_id, "AI_AGENT")
        etf_row = get_latest_projection_by_source(conn, investment_id, "ETF_ANALYSIS")
        assert ai_row["version"] == 3
        assert ai_row["fair_value"] == 41.0  # untouched
        assert etf_row["version"] == 4
    finally:
        conn.close()


def test_persist_updates_investment_table_fields(tmp_path, monkeypatch):
    """Verify persist_etf_analysis also synchronizes the investment table's
    target_action, agent_rationale, and last_deep_analysis_at fields."""
    _write_etf_versions_file(monkeypatch, tmp_path)
    db_path = tmp_path / "test.sqlite"

    etf_payload = dict(SAMPLE_ETF)
    etf_payload["agentRationale"] = "ETF_ANALYSIS: INITIATE | alignment 72% | SpaceX exposure | analyzed 2026-07-19"
    persist_etf_analysis.persist(etf_payload, dry_run=False, db_path=db_path)

    conn = initialize_db(str(db_path))
    try:
        from domain_model.investment_repository import get_investment, resolve_investment
        inv_id = resolve_investment(conn, "DXYZ", asset_class="ETF")
        inv = get_investment(conn, inv_id)
        assert inv is not None
        assert inv["target_action"] == "INITIATE"
        assert "SpaceX exposure" in (inv["agent_rationale"] or "")
        assert inv["last_deep_analysis_at"] is not None
    finally:
        conn.close()

