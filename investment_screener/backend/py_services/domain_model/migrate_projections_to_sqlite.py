"""Migrates `projections/{TICKER}.json` array-entries into the v3.2
`projection_version`/`projection_scenario` tables (ADR-029).

**Two run modes, sharing the exact same migration code path (`_migrate_all`):**

- `run_dry_run(projections_dir)` — always operates against an in-memory (`:memory:`)
  SQLite connection. Never touches a real file. This was the only mode that existed
  through Wave 1 Task 2/3 (dry-run analysis, gated user approval of the real numbers).
- `run_real_migration(projections_dir, db_path)` — Wave 1 Task 4. Opens (creating if
  absent) the real `db_path` SQLite file via `db_client.initialize_db` and performs the
  exact same insert/upsert calls dry-run only simulated. Insert-only against SQLite: this
  module never reads back or deletes source `projections/*.json` files, so it cannot
  modify or remove them.

The CLI entry point (`main`, `python -m domain_model.migrate_projections_to_sqlite`)
defaults to dry-run and requires an explicit `--write` flag to invoke
`run_real_migration`, following this repo's existing `--dry-run`/`--write` convention
(see `lock_and_normalize_targets.py`).

Shape handling in `parse_projection_entry`
-------------------------------------------
Real-data survey (all 82 files / 132 entries in
`investment_screener/backend/data/projections/` as of 2026-07-19, a mix of the oldest
files by git history — DXYZ, DRAM, HUMN, KOID, ETHA — and the newest — TSLA, ZS, OKLO,
INTC, IONQ, plus mid-range files FOTO, IBIT, WQTM, APLD, AAPL) found:

- 130/132 entries use only the current nested shape: `aiThesis.fairValue` /
  `aiThesis.action`.
- 0/132 entries use only the legacy top-level shape (`fairValue`/`action` with no
  `aiThesis`). That shape is exercised only by this task's fixture tests
  (`LEGACY_ENTRY`, `NO_SCENARIOS_ENTRY`) — real support for it is kept because the
  interface contract requires it and older archived data or future callers may still
  produce it, but it was not observed live in the current corpus.
- 2/132 entries (`IONQ.json`, `QBTS.json`, both `version: 1`, both saved 2026-05-04) carry
  **both** a top-level `fairValue`/`action` and a nested `aiThesis.fairValue`/`action` —
  a third shape not covered by the task brief's two named shapes. In one of these
  (`IONQ.json`) the two `fairValue` values actively disagree (10.24 top-level vs. 8.54
  nested; `action` agrees as `SELL` in both).

  Precedence is **timestamp-driven, not a blanket "aiThesis wins" rule**. Each shape's
  write path stamps its own real timestamp (`apply_catalyst.py` `main()`): writing the
  top-level fields sets `entry["updatedAt"]`; writing the nested fields sets
  `aiThesis["analyzedAt"]`. `parse_projection_entry` compares the two and prefers
  whichever was genuinely written more recently. For IONQ.json, `updatedAt`
  (2026-05-13T15:02:10Z) is later than `aiThesis.analyzedAt` (2026-05-04T15:09:22Z), and
  `catalystUpdates[0].thesisImpact` literally documents the transition "FV
  $8.54->$10.24. Action: SELL->SELL." — i.e. the top-level `10.24` is the newer,
  catalyst-corrected value and the earlier `aiThesis`-wins-always rule would have
  migrated the stale pre-catalyst `8.54` into `projection_version.fair_value`. QBTS.json's
  two shapes already agree, so precedence doesn't affect it either way. When one or both
  timestamps are missing/unparseable, the code falls back to preferring `aiThesis` (the
  only real conflicting-shape pair this default affects both had `aiThesis` present).
  Proven by `test_parse_projection_entry_prefers_top_level_when_updated_at_is_newer`,
  `test_parse_projection_entry_prefers_ai_thesis_when_analyzed_at_is_newer`, and
  `test_parse_projection_entry_falls_back_to_ai_thesis_when_timestamps_missing` in the
  test file.
"""

import argparse
import datetime
import json
import sqlite3
from pathlib import Path

from domain_model.investment_repository import resolve_investment
from domain_model.projection_repository import (
    add_projection_scenario,
    save_projection_version,
)


def _parse_iso8601(value: object) -> "datetime.datetime | None":
    """Parse an ISO8601 timestamp string (e.g. `2026-05-04T15:09:22Z`) into a comparable
    `datetime`, or `None` if `value` is missing/not a string/unparseable."""
    if not isinstance(value, str):
        return None
    try:
        return datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def parse_projection_entry(entry: dict) -> dict:
    """Normalize one `projections/{TICKER}.json` array-entry into the flat kwargs
    `save_projection_version`/`add_projection_scenario` expect.

    Handles three observed shapes (see module docstring for the real-data survey behind
    this):
      1. Legacy top-level: `fairValue`/`action` at the entry's top level, no `aiThesis`.
      2. Current nested: `aiThesis.fairValue`/`aiThesis.action` (the common case).
      3. Both present (2/132 real entries): each shape carries its own real write
         timestamp (`entry["updatedAt"]` for top-level writes, `aiThesis["analyzedAt"]`
         for nested writes — see `apply_catalyst.py` `main()`), so whichever timestamp is
         genuinely more recent wins. IONQ.json proves this can go either way: its
         top-level `fairValue=10.24`/`updatedAt=2026-05-13...` is the newer,
         catalyst-corrected value over the stale `aiThesis.fairValue=8.54` from
         `analyzedAt=2026-05-04...` (see `catalystUpdates[0].thesisImpact`: "FV
         $8.54->$10.24"). If either timestamp is missing/unparseable, fall back to
         "aiThesis wins" — the only real conflicting-shape pair this affects (2/132
         entries) both had aiThesis present, so that remains the safer default when a
         genuine comparison isn't possible.
    """
    ai_thesis = entry.get("aiThesis")
    ai_thesis = ai_thesis if isinstance(ai_thesis, dict) else {}
    has_ai_thesis = "fairValue" in ai_thesis or "action" in ai_thesis
    has_top_level = "fairValue" in entry or "action" in entry

    if has_ai_thesis and has_top_level:
        updated_at = _parse_iso8601(entry.get("updatedAt"))
        analyzed_at_ts = _parse_iso8601(ai_thesis.get("analyzedAt"))
        prefer_top_level = (
            updated_at is not None
            and analyzed_at_ts is not None
            and updated_at > analyzed_at_ts
        )
        use_ai_thesis = not prefer_top_level
    else:
        use_ai_thesis = has_ai_thesis

    if use_ai_thesis:
        fair_value = ai_thesis.get("fairValue")
        action = ai_thesis.get("action")
        analyzed_at = ai_thesis.get("analyzedAt")
        model = ai_thesis.get("model")
        rationale = ai_thesis.get("rationale")
    else:
        fair_value = entry.get("fairValue")
        action = entry.get("action")
        analyzed_at = None
        model = None
        rationale = entry.get("rationale")

    snapshot = entry.get("snapshot")
    analytics_log = entry.get("analyticsLog")
    catalyst_updates = entry.get("catalystUpdates")

    parsed = {
        "id": entry.get("id"),
        "ticker": entry.get("ticker"),
        "version": entry.get("version"),
        "source": entry.get("source"),
        "saved_at": entry.get("savedAt"),
        "analyzed_at": analyzed_at,
        "model": model,
        "fair_value": fair_value,
        "action": action,
        "rationale": rationale,
        "snapshot_json": json.dumps(snapshot) if snapshot is not None else None,
        "analytics_log_json": json.dumps(analytics_log) if analytics_log is not None else None,
        "scenarios": entry.get("scenarios"),
        "last_grok_sweep": entry.get("lastGrokSweep"),
        "catalyst_updates_json": (
            json.dumps(catalyst_updates) if catalyst_updates is not None else None
        ),
    }
    return parsed


def migrate_ticker_file(conn: sqlite3.Connection, ticker: str, entries: list[dict]) -> dict:
    """Migrate every array-entry of one `projections/{TICKER}.json` file into `conn`.

    Returns a per-ticker result summary:
    `{"ticker": ..., "versions_migrated": int, "scenarios_migrated": int, "errors": list[str]}`.
    A parse/write failure on one entry is recorded in `errors` and does not stop the
    remaining entries in the file from being processed.
    """
    result = {
        "ticker": ticker,
        "versions_migrated": 0,
        "scenarios_migrated": 0,
        "errors": [],
    }

    investment_id = resolve_investment(conn, ticker)

    for entry in entries:
        try:
            parsed = parse_projection_entry(entry)
            version = parsed.get("version")
            if version is None:
                raise ValueError(f"entry missing 'version' field: id={entry.get('id')!r}")

            projection_id = save_projection_version(
                conn,
                investment_id,
                version=version,
                saved_at=parsed["saved_at"],
                analyzed_at=parsed["analyzed_at"],
                model=parsed["model"],
                fair_value=parsed["fair_value"],
                action=parsed["action"],
                rationale=parsed["rationale"],
                snapshot_json=parsed["snapshot_json"],
                analytics_log_json=parsed["analytics_log_json"],
                source=parsed["source"],
                last_grok_sweep=parsed["last_grok_sweep"],
                catalyst_updates_json=parsed["catalyst_updates_json"],
            )
            result["versions_migrated"] += 1

            scenarios = parsed.get("scenarios") or {}
            for scenario_name, scenario in scenarios.items():
                if not isinstance(scenario, dict):
                    continue
                add_projection_scenario(
                    conn,
                    projection_id,
                    scenario_name,
                    weight=scenario.get("weight"),
                    growth_rate=scenario.get("growthRate"),
                    net_margin=scenario.get("netMargin"),
                    exit_pe=scenario.get("exitPE"),
                    quality_multiplier=scenario.get("qualityMultiplier"),
                    share_change=scenario.get("shareChange"),
                    rationale=scenario.get("rationale"),
                    moat_score=scenario.get("moatScore"),
                    management_score=scenario.get("managementScore"),
                    year5_revenue=scenario.get("year5Revenue"),
                    year5_net_income=scenario.get("year5NetIncome"),
                    year5_eps=scenario.get("year5EPS"),
                    scenario_price=scenario.get("scenarioPrice"),
                    risks_json=json.dumps(scenario["risks"]) if "risks" in scenario else None,
                )
                result["scenarios_migrated"] += 1
        except Exception as exc:  # noqa: BLE001 - a real per-entry error must be reported
            entry_id = entry.get("id") if isinstance(entry, dict) else None
            entry_version = entry.get("version") if isinstance(entry, dict) else None
            result["errors"].append(
                f"{ticker} entry id={entry_id!r} version={entry_version!r}: {exc}"
            )

    return result


def _migrate_all(conn: sqlite3.Connection, projections_dir: Path) -> dict:
    """Walk every `*.json` file in `projections_dir`, migrate its entries into `conn`
    (whatever connection the caller opened — in-memory or a real file), and return an
    aggregate report. Shared by both `run_dry_run` and `run_real_migration` so the two
    modes are guaranteed to execute the identical migration logic."""
    report = {
        "total_files": 0,
        "total_versions": 0,
        "total_scenarios": 0,
        "legacy_shape_count": 0,
        "missing_scenarios_count": 0,
        "both_shapes_count": 0,
        "per_ticker": [],
        "file_errors": [],
    }

    for path in sorted(Path(projections_dir).glob("*.json")):
        report["total_files"] += 1
        ticker = path.stem

        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except Exception as exc:  # noqa: BLE001 - a real per-file error must be reported
            report["file_errors"].append(f"{path.name}: failed to read/parse JSON: {exc}")
            continue

        entries = data if isinstance(data, list) else [data]

        for entry in entries:
            try:
                ai_thesis = entry.get("aiThesis")
                has_ai_thesis = isinstance(ai_thesis, dict) and (
                    "fairValue" in ai_thesis or "action" in ai_thesis
                )
                has_top_level = "fairValue" in entry or "action" in entry
                if has_top_level and has_ai_thesis:
                    report["both_shapes_count"] += 1
                elif has_top_level and not has_ai_thesis:
                    report["legacy_shape_count"] += 1
                if not entry.get("scenarios"):
                    report["missing_scenarios_count"] += 1
            except Exception as exc:  # noqa: BLE001 - a real per-file error must be reported
                report["file_errors"].append(
                    f"{path.name}: malformed entry in shape tally: {exc}"
                )

        result = migrate_ticker_file(conn, ticker, entries)
        report["total_versions"] += result["versions_migrated"]
        report["total_scenarios"] += result["scenarios_migrated"]
        report["per_ticker"].append(result)
        for err in result["errors"]:
            report["file_errors"].append(f"{path.name}: {err}")

    return report


def run_dry_run(projections_dir: Path) -> dict:
    """Walk every `*.json` file in `projections_dir`, migrate its entries against an
    **in-memory** SQLite connection, and return an aggregate report.

    Never touches the real `domain_model.sqlite` file — this is analysis only.
    """
    from domain_model.db_client import initialize_db

    conn = initialize_db(":memory:")
    try:
        return _migrate_all(conn, projections_dir)
    finally:
        conn.close()


def run_real_migration(projections_dir: Path, db_path: str) -> dict:
    """Walk every `*.json` file in `projections_dir`, migrate its entries into the real
    SQLite database at `db_path` (created if absent, via `db_client.initialize_db`), and
    return the same aggregate report shape as `run_dry_run`.

    Insert-only against SQLite (upsert on `(investment_id, version)` inside
    `save_projection_version`/`add_projection_scenario`). Never reads back, modifies, or
    deletes any file under `projections_dir` — the source JSON files are untouched by
    this function.
    """
    from domain_model.db_client import initialize_db

    conn = initialize_db(db_path)
    try:
        return _migrate_all(conn, projections_dir)
    finally:
        conn.close()


def main() -> None:
    """CLI entry point. Defaults to dry-run (in-memory, prints the report, writes
    nothing real); pass `--write` to run the real migration against `--db-path`.

    Follows this repo's existing `--dry-run`/`--write` convention (see
    `lock_and_normalize_targets.py`): dry-run is the safe default, `--write` is opt-in.
    """
    parser = argparse.ArgumentParser(
        description="Migrate projections/*.json into projection_version/projection_scenario."
    )
    parser.add_argument(
        "--projections-dir",
        default="investment_screener/backend/data/projections",
        help="Directory containing {TICKER}.json projection files.",
    )
    parser.add_argument(
        "--db-path",
        default="investment_screener/backend/data/domain_model.sqlite",
        help="Path to the real domain_model.sqlite file (created if absent).",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Execute the real migration against --db-path. Without this flag, runs a "
        "safe in-memory dry run and prints the report without touching any real file.",
    )
    args = parser.parse_args()

    projections_dir = Path(args.projections_dir)

    if args.write:
        report = run_real_migration(projections_dir, args.db_path)
        print(f"[WRITE MODE] Migrated into real database: {args.db_path}")
    else:
        report = run_dry_run(projections_dir)
        print("[DRY RUN — pass --write to persist changes to --db-path]")

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
