"""Dry-run analysis for migrating `projections/{TICKER}.json` array-entries into the
v3.2 `projection_version`/`projection_scenario` tables (ADR-029, Wave 1 Task 2).

**This module never writes to a real `domain_model.sqlite` file.** `run_dry_run` always
operates against an in-memory (`:memory:`) SQLite connection created via
`db_client.initialize_db`. The real migration (writing to the actual database) is a
separate, later task (Wave 1 Task 4) gated on explicit user approval of this dry run's
report (Wave 1 Task 3) — no `--write` flag or real-file code path exists here on purpose.

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
  nested; `action` agrees as `SELL` in both). Since the overwhelming majority of real
  entries (130/132) use the nested shape exclusively, and both "both-shape" entries are
  old (`version: 1`, earliest analyzed dates in the corpus), the nested `aiThesis` fields
  are treated as authoritative whenever `aiThesis` is present — even when legacy
  top-level fields also exist and disagree with it. This is proven by
  `test_parse_projection_entry_prefers_ai_thesis_when_both_shapes_present` in the test
  file, added before this precedence rule was implemented.
"""

import json
import sqlite3
from pathlib import Path

from domain_model.investment_repository import resolve_investment
from domain_model.projection_repository import (
    add_projection_scenario,
    save_projection_version,
)


def parse_projection_entry(entry: dict) -> dict:
    """Normalize one `projections/{TICKER}.json` array-entry into the flat kwargs
    `save_projection_version`/`add_projection_scenario` expect.

    Handles three observed shapes (see module docstring for the real-data survey behind
    this):
      1. Legacy top-level: `fairValue`/`action` at the entry's top level, no `aiThesis`.
      2. Current nested: `aiThesis.fairValue`/`aiThesis.action` (the common case).
      3. Both present (2/132 real entries): `aiThesis` wins, even if the legacy
         top-level fields disagree with it.
    """
    ai_thesis = entry.get("aiThesis")
    has_ai_thesis = isinstance(ai_thesis, dict) and (
        "fairValue" in ai_thesis or "action" in ai_thesis
    )

    if has_ai_thesis:
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
            result["errors"].append(
                f"{ticker} entry id={entry.get('id')!r} version={entry.get('version')!r}: {exc}"
            )

    return result


def run_dry_run(projections_dir: Path) -> dict:
    """Walk every `*.json` file in `projections_dir`, migrate its entries against an
    **in-memory** SQLite connection, and return an aggregate report.

    Never touches the real `domain_model.sqlite` file — this is analysis only.
    """
    from domain_model.db_client import initialize_db

    conn = initialize_db(":memory:")

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

        result = migrate_ticker_file(conn, ticker, entries)
        report["total_versions"] += result["versions_migrated"]
        report["total_scenarios"] += result["scenarios_migrated"]
        report["per_ticker"].append(result)
        for err in result["errors"]:
            report["file_errors"].append(f"{path.name}: {err}")

    conn.close()
    return report
