import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from domain_model.migrate_projections_to_sqlite import (  # noqa: E402
    parse_projection_entry,
    migrate_ticker_file,
    run_dry_run,
)
from domain_model.db_client import initialize_db  # noqa: E402


LEGACY_ENTRY = {
    "id": "legacy-1", "ticker": "OLDCO", "version": 2, "source": "AI_AGENT",
    "savedAt": "2026-01-01T00:00:00Z", "fairValue": 100.0, "action": "HOLD",
    "snapshot": {"price": 95.0},
}

CURRENT_ENTRY = {
    "id": "current-1", "ticker": "AAPL", "version": 3, "source": "AI_AGENT",
    "savedAt": "2026-07-01T00:00:00Z",
    "aiThesis": {"fairValue": 190.0, "action": "MAINTAIN", "analyzedAt": "2026-07-01T00:00:00Z",
                 "model": "gemini-2.5-pro", "rationale": "test"},
    "snapshot": {"price": 180.0},
    "scenarios": {
        "bear": {"weight": 0.2, "scenarioPrice": 150.0},
        "base": {"weight": 0.5, "scenarioPrice": 190.0},
        "bull": {"weight": 0.3, "scenarioPrice": 230.0},
    },
}

NO_SCENARIOS_ENTRY = {
    "id": "no-scenarios-1", "ticker": "OLDCO", "version": 1, "source": "USER",
    "savedAt": "2025-06-01T00:00:00Z", "fairValue": 80.0, "action": "MAINTAIN",
    "snapshot": {"price": 82.0},
}

# Third shape variant, confirmed against real data: 2 of 132 real entries (across 82 files in
# investment_screener/backend/data/projections/, IONQ.json and QBTS.json, both version-1 /
# early-May-2026 entries) carry BOTH a top-level fairValue/action AND a nested
# aiThesis.fairValue/action. In IONQ.json's case the two fairValue values disagree
# (top-level 10.24 vs aiThesis 8.54; action agrees as SELL in both). Since 130/132 real entries
# use the nested aiThesis shape exclusively, and the top-level fields on these 2 stragglers read
# as stale leftovers from an older write path, parse_projection_entry treats aiThesis as
# authoritative whenever it is present, even if legacy top-level fields also exist and disagree.
BOTH_SHAPES_CONFLICTING_ENTRY = {
    "id": "both-1", "ticker": "IONQ", "version": 1, "source": "AI_AGENT",
    "savedAt": "2026-05-04T15:09:22Z",
    "fairValue": 10.24, "action": "SELL",
    "aiThesis": {"fairValue": 8.54, "action": "SELL", "analyzedAt": "2026-05-04T15:09:22Z",
                 "model": "gemini-2.5-pro", "rationale": "test"},
    "snapshot": {"price": 9.0},
}


def test_parse_projection_entry_handles_legacy_top_level_shape():
    parsed = parse_projection_entry(LEGACY_ENTRY)
    assert parsed["fair_value"] == 100.0
    assert parsed["action"] == "HOLD"


def test_parse_projection_entry_handles_current_nested_ai_thesis_shape():
    parsed = parse_projection_entry(CURRENT_ENTRY)
    assert parsed["fair_value"] == 190.0
    assert parsed["action"] == "MAINTAIN"
    assert parsed["model"] == "gemini-2.5-pro"


def test_parse_projection_entry_handles_missing_scenarios_block():
    parsed = parse_projection_entry(NO_SCENARIOS_ENTRY)
    assert parsed.get("scenarios") in (None, {})


def test_parse_projection_entry_prefers_ai_thesis_when_both_shapes_present():
    """Real-data finding: 2/132 real entries carry both top-level and nested fairValue/action,
    with the nested aiThesis version being the authoritative one written by the current code
    path. aiThesis must win, not the stale top-level field."""
    parsed = parse_projection_entry(BOTH_SHAPES_CONFLICTING_ENTRY)
    assert parsed["fair_value"] == 8.54
    assert parsed["action"] == "SELL"


def test_migrate_ticker_file_against_in_memory_db():
    conn = initialize_db(":memory:")
    result = migrate_ticker_file(conn, "AAPL", [CURRENT_ENTRY])
    assert result["versions_migrated"] == 1
    assert result["scenarios_migrated"] == 3
    assert result["errors"] == []


def test_migrate_ticker_file_with_no_scenarios_reports_zero_not_error():
    conn = initialize_db(":memory:")
    result = migrate_ticker_file(conn, "OLDCO", [NO_SCENARIOS_ENTRY])
    assert result["versions_migrated"] == 1
    assert result["scenarios_migrated"] == 0
    assert result["errors"] == []


def test_run_dry_run_against_real_fixture_directory(tmp_path):
    ticker_file = tmp_path / "AAPL.json"
    ticker_file.write_text('[' + str(CURRENT_ENTRY).replace("'", '"') + ']')
    report = run_dry_run(tmp_path)
    assert report["total_files"] == 1
    assert report["total_versions"] >= 1
