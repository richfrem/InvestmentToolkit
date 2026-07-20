"""Tests for apply_catalyst.py's Wave 1 Task 6 rewire to
domain_model.projection_repository (ADR-029). All tests run against a `tmp_path`-backed
SQLite database via `initialize_db` — never the real `data/domain_model.sqlite` file.
"""

import argparse
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.investment_repository import resolve_investment  # noqa: E402
from domain_model.projection_repository import (  # noqa: E402
    save_projection_version,
    add_projection_scenario,
    get_latest_projection_by_source,
    get_projection_scenarios,
)

import apply_catalyst  # noqa: E402


def _seed_ai_agent_projection(conn, ticker="MSFT", version=1, fair_value=300.0,
                               action="ACCUMULATE", price=280.0, with_scenarios=True):
    """Seed one AI_AGENT-sourced projection_version row (+ optional scenarios) for
    `ticker`, mirroring the shape a real migrated/saved row has."""
    investment_id = resolve_investment(conn, ticker, asset_class="EQUITY", currency="USD")
    snapshot_json = json.dumps({"price": price})
    save_projection_version(
        conn, investment_id, version=version, saved_at="2026-07-01T00:00:00Z",
        analyzed_at="2026-07-01T00:00:00Z", model="gemini-2.5-pro", fair_value=fair_value,
        action=action, rationale="seed rationale", snapshot_json=snapshot_json,
        source="AI_AGENT",
    )
    projection_id = f"{investment_id}:{version}"
    if with_scenarios:
        add_projection_scenario(conn, projection_id, "bear", weight=0.2, scenario_price=200.0,
                                 growth_rate=5.0, rationale="bear case")
        add_projection_scenario(conn, projection_id, "base", weight=0.5, scenario_price=300.0,
                                 growth_rate=10.0, rationale="base case")
        add_projection_scenario(conn, projection_id, "bull", weight=0.3, scenario_price=400.0,
                                 growth_rate=15.0, rationale="bull case")
    return investment_id, projection_id


def _args(**overrides):
    defaults = dict(
        ticker="MSFT", catalyst_type=None, shift_bull=None, shift_bear=None, note=None,
        date="2026-07-19", dry_run=False, write=False, update_thesis=False,
        record_sweep=False,
    )
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


# ---------------------------------------------------------------------------
# --record-sweep mode
# ---------------------------------------------------------------------------

def test_record_sweep_stamps_last_grok_sweep_without_shifting_weights(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    investment_id, _ = _seed_ai_agent_projection(conn)

    args = _args(record_sweep=True, date="2026-07-19")
    apply_catalyst._run_record_sweep(conn, args)

    row = get_latest_projection_by_source(conn, investment_id, "AI_AGENT")
    assert row["last_grok_sweep"] == "2026-07-19"
    assert row["fair_value"] == 300.0  # unchanged — no catalyst applied
    assert row["action"] == "ACCUMULATE"  # unchanged


def test_record_sweep_updates_in_place_not_duplicated(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    investment_id, _ = _seed_ai_agent_projection(conn)

    apply_catalyst._run_record_sweep(conn, _args(record_sweep=True, date="2026-07-19"))

    count = conn.execute(
        "SELECT COUNT(*) FROM projection_version WHERE investment_id = ?;", (investment_id,)
    ).fetchone()[0]
    assert count == 1  # upsert-in-place, not a new version row


def test_record_sweep_raises_for_ticker_with_no_ai_agent_entries(tmp_path):
    """Real-data finding: 8/82 real tickers have zero AI_AGENT-sourced projections
    (only ETF_ANALYSIS). This must still raise, matching the original tool's behavior
    of erroring when no AI_AGENT entry exists."""
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    investment_id = resolve_investment(conn, "DRAM", asset_class="EQUITY", currency="USD")
    save_projection_version(
        conn, investment_id, version=1, saved_at="2026-05-14T16:42:00Z",
        fair_value=5.0, action="HOLD", source="ETF_ANALYSIS",
    )

    with pytest.raises(ValueError, match="No AI_AGENT entries"):
        apply_catalyst._run_record_sweep(conn, _args(ticker="DRAM", record_sweep=True))


def test_record_sweep_exits_for_unknown_ticker(tmp_path, capsys):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    with pytest.raises(SystemExit) as exc_info:
        apply_catalyst._run_record_sweep(conn, _args(ticker="NOPE", record_sweep=True))
    assert exc_info.value.code == 1


# ---------------------------------------------------------------------------
# --write with a preset catalyst type
# ---------------------------------------------------------------------------

def test_write_applies_preset_and_updates_row_in_place(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    investment_id, projection_id = _seed_ai_agent_projection(conn)

    preset = apply_catalyst.PRESETS["major_contract"]
    args = _args(catalyst_type="major_contract", note="Cloud expansion deal", write=True,
                 date="2026-07-19")
    apply_catalyst._run_apply_catalyst(conn, args, preset["bull"], preset["bear"])

    count = conn.execute(
        "SELECT COUNT(*) FROM projection_version WHERE investment_id = ?;", (investment_id,)
    ).fetchone()[0]
    assert count == 1  # updated in place, not duplicated

    row = get_latest_projection_by_source(conn, investment_id, "AI_AGENT")
    assert row["projection_id"] == projection_id
    assert row["fair_value"] != 300.0  # weights shifted, FV recomputed
    assert row["last_grok_sweep"] == "2026-07-19"

    catalyst_updates = json.loads(row["catalyst_updates_json"])
    assert len(catalyst_updates) == 1
    assert catalyst_updates[0]["type"] == "major_contract"
    assert catalyst_updates[0]["events"] == ["Cloud expansion deal"]


def test_write_shifts_scenario_weights_and_preserves_other_scenario_fields(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    investment_id, projection_id = _seed_ai_agent_projection(conn)

    preset = apply_catalyst.PRESETS["earnings_beat"]
    args = _args(catalyst_type="earnings_beat", note="Beat estimates", write=True)
    apply_catalyst._run_apply_catalyst(conn, args, preset["bull"], preset["bear"])

    scenarios = {
        s["scenario_name"]: s for s in get_projection_scenarios(conn, projection_id)
    }
    # weight shifted
    assert scenarios["bull"]["weight"] != 0.3
    assert scenarios["bear"]["weight"] != 0.2
    # non-weight fields preserved (not wiped by the upsert)
    assert scenarios["bull"]["rationale"] == "bull case"
    assert scenarios["bull"]["growth_rate"] == 15.0
    assert scenarios["bear"]["rationale"] == "bear case"


def test_dry_run_does_not_write(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    investment_id, _ = _seed_ai_agent_projection(conn)

    preset = apply_catalyst.PRESETS["thesis_breaker"]
    args = _args(catalyst_type="thesis_breaker", note="GAA delay", dry_run=True)
    apply_catalyst._run_apply_catalyst(conn, args, preset["bull"], preset["bear"])

    row = get_latest_projection_by_source(conn, investment_id, "AI_AGENT")
    assert row["fair_value"] == 300.0
    assert row["action"] == "ACCUMULATE"
    assert row["last_grok_sweep"] is None


def test_no_write_no_dry_run_does_not_persist(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    investment_id, _ = _seed_ai_agent_projection(conn)

    preset = apply_catalyst.PRESETS["design_win"]
    args = _args(catalyst_type="design_win", note="New contract")  # neither --write nor --dry-run
    apply_catalyst._run_apply_catalyst(conn, args, preset["bull"], preset["bear"])

    row = get_latest_projection_by_source(conn, investment_id, "AI_AGENT")
    assert row["fair_value"] == 300.0
    assert row["last_grok_sweep"] is None


def test_legacy_format_with_no_scenarios_only_appends_catalyst_note(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    investment_id, projection_id = _seed_ai_agent_projection(conn, with_scenarios=False)

    preset = apply_catalyst.PRESETS["partnership"]
    args = _args(catalyst_type="partnership", note="New partner", write=True)
    apply_catalyst._run_apply_catalyst(conn, args, preset["bull"], preset["bear"])

    row = get_latest_projection_by_source(conn, investment_id, "AI_AGENT")
    assert row["fair_value"] == 300.0  # unchanged — no scenarios to shift
    assert row["action"] == "ACCUMULATE"  # unchanged
    catalyst_updates = json.loads(row["catalyst_updates_json"])
    assert len(catalyst_updates) == 1  # note still appended


def test_write_appends_to_existing_catalyst_updates_log(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    investment_id, _ = _seed_ai_agent_projection(conn)

    preset = apply_catalyst.PRESETS["earnings_beat"]
    apply_catalyst._run_apply_catalyst(
        conn, _args(catalyst_type="earnings_beat", note="Q1 beat", write=True, date="2026-07-01"),
        preset["bull"], preset["bear"],
    )
    apply_catalyst._run_apply_catalyst(
        conn, _args(catalyst_type="partnership", note="New deal", write=True, date="2026-07-19"),
        apply_catalyst.PRESETS["partnership"]["bull"], apply_catalyst.PRESETS["partnership"]["bear"],
    )

    row = get_latest_projection_by_source(conn, investment_id, "AI_AGENT")
    catalyst_updates = json.loads(row["catalyst_updates_json"])
    assert len(catalyst_updates) == 2
    assert catalyst_updates[0]["events"] == ["Q1 beat"]
    assert catalyst_updates[1]["events"] == ["New deal"]


def test_write_raises_for_ticker_with_no_ai_agent_entries(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    investment_id = resolve_investment(conn, "IBIT", asset_class="ETF", currency="USD")
    save_projection_version(
        conn, investment_id, version=1, saved_at="2026-06-21T20:00:00Z",
        fair_value=50.0, action="HOLD", source="ETF_ANALYSIS",
    )
    preset = apply_catalyst.PRESETS["major_contract"]
    with pytest.raises(ValueError, match="No AI_AGENT entries"):
        apply_catalyst._run_apply_catalyst(
            conn, _args(ticker="IBIT", catalyst_type="major_contract", note="x", write=True),
            preset["bull"], preset["bear"],
        )


# ---------------------------------------------------------------------------
# source/latest-entry equivalence (the investigated real-data gap)
# ---------------------------------------------------------------------------

def test_latest_by_source_ignores_higher_version_non_ai_agent_row(tmp_path):
    """Real-data finding: get_latest_projection (MAX(version)) is NOT equivalent to
    _find_latest_ai_agent (source-filtered, latest by saved_at). A higher-version row
    that is not AI_AGENT-sourced must not be picked over a lower-version AI_AGENT row —
    this is exactly the BW/CLSK/LITE real-ticker pattern (non-chronological versions)."""
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    investment_id = resolve_investment(conn, "BW", asset_class="EQUITY", currency="USD")
    # AI_AGENT entry at version 1, saved later than the version-3 USER entry
    save_projection_version(
        conn, investment_id, version=1, saved_at="2026-05-02T21:57:03Z",
        fair_value=8.83, action="SELL", source="AI_AGENT",
    )
    # A non-AI_AGENT entry that happens to carry a HIGHER version number but an EARLIER
    # saved_at — get_latest_projection's MAX(version) would wrongly prefer this.
    save_projection_version(
        conn, investment_id, version=3, saved_at="2026-05-02T17:50:00Z",
        fair_value=27.13, action="BUY", source="USER",
    )

    from domain_model.projection_repository import get_latest_projection
    naive = get_latest_projection(conn, investment_id)
    assert naive["version"] == 3  # proves the naive MAX(version) query picks the wrong row

    row = apply_catalyst._find_latest_ai_agent(conn, investment_id)
    assert row["fair_value"] == 8.83
    assert row["action"] == "SELL"
    assert row["source"] == "AI_AGENT"


def test_latest_by_source_picks_latest_saved_at_among_ai_agent_rows(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    investment_id = resolve_investment(conn, "NVDA", asset_class="EQUITY", currency="USD")
    save_projection_version(
        conn, investment_id, version=2, saved_at="2026-02-15T04:54:49Z",
        fair_value=120.0, action="MAINTAIN", source="AI_AGENT",
    )
    save_projection_version(
        conn, investment_id, version=3, saved_at="2026-05-02T23:05:00Z",
        fair_value=180.0, action="BUY", source="AI_AGENT",
    )
    row = apply_catalyst._find_latest_ai_agent(conn, investment_id)
    assert row["version"] == 3
    assert row["fair_value"] == 180.0


# ---------------------------------------------------------------------------
# --update-thesis (Wave 2 Task 10 cutover): agentRationale now becomes an
# append-only investment_note row + investment.agent_rationale refresh,
# instead of a string-concatenated write into target-portfolio.json.
# ---------------------------------------------------------------------------

def test_update_thesis_adds_note_and_refreshes_agent_rationale(tmp_path):
    from domain_model.investment_note_repository import list_notes
    from domain_model.investment_repository import get_investment

    conn = initialize_db(str(tmp_path / "test.sqlite"))
    investment_id, _ = _seed_ai_agent_projection(conn)

    preset = apply_catalyst.PRESETS["major_contract"]
    args = _args(catalyst_type="major_contract", note="Cloud expansion deal", write=True,
                 update_thesis=True, date="2026-07-19")
    apply_catalyst._run_apply_catalyst(conn, args, preset["bull"], preset["bear"])

    notes = list_notes(conn, investment_id)
    assert len(notes) == 1
    assert notes[0]["note_type"] == "AGENT_RATIONALE"
    assert notes[0]["source"] == "apply_catalyst.py"
    assert "Cloud expansion deal" in notes[0]["body"]

    row = get_investment(conn, investment_id)
    assert "Cloud expansion deal" in row["agent_rationale"]


def test_update_thesis_skips_duplicate_note(tmp_path):
    from domain_model.investment_note_repository import list_notes

    conn = initialize_db(str(tmp_path / "test.sqlite"))
    investment_id, _ = _seed_ai_agent_projection(conn)

    preset = apply_catalyst.PRESETS["earnings_beat"]
    args = _args(catalyst_type="earnings_beat", note="Beat estimates", write=True,
                 update_thesis=True, date="2026-07-19")
    apply_catalyst._run_apply_catalyst(conn, args, preset["bull"], preset["bear"])
    # Re-running _run_apply_catalyst a second time re-seeds a fresh AI_AGENT row is not
    # realistic here (in-place update), but the dedup check reads investment.agent_rationale
    # directly, so calling update_thesis logic twice with the same note must not duplicate.
    args2 = _args(catalyst_type="earnings_beat", note="Beat estimates", write=True,
                  update_thesis=True, date="2026-07-19")
    apply_catalyst._run_apply_catalyst(conn, args2, preset["bull"], preset["bear"])

    notes = list_notes(conn, investment_id)
    assert len(notes) == 1  # second call detected duplicate note text, skipped insert

def test_cli_flags_still_present():
    import subprocess
    result = subprocess.run(
        [sys.executable, str(SCRIPT_DIR / "apply_catalyst.py"), "--help"],
        capture_output=True, text=True,
    )
    help_text = result.stdout
    for flag in ("--dry-run", "--write", "--record-sweep", "--update-thesis", "--ticker",
                 "--type", "--shift-bull", "--shift-bear", "--note", "--date"):
        assert flag in help_text, f"{flag} missing from CLI surface"
