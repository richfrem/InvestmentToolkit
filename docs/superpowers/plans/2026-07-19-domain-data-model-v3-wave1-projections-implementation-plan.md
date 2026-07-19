# Domain Data Model v3.2 — Wave 1: Projections Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate `investment_screener/backend/data/projections/*.json` (144 files) into the v3.2
`projection_version`/`projection_scenario` SQLite tables built in Wave 0, cut over both real
producers and all real consumers to read/write SQLite, and archive the JSON directory — the first
wave that actually reduces JSON file count, per this migration's Non-Negotiable Goal Statement.

**Architecture:** Two real producers today — `ProjectionService.ts` (TS, via
`routes/projections.ts`) and `apply_catalyst.py` (Python, bypasses the service entirely). Both
must write through a repository layer: `investment_screener/backend/py_services/domain_model/
projection_repository.py` (Python side, mirrors Wave 0's `investment_repository.py` pattern) and a
new `investment_screener/backend/src/services/ProjectionRepository.ts` (TS side, using
`better-sqlite3` — **already an installed, currently-unused dependency**, confirmed by grep
returning zero usages in `src/` as of this plan's authoring). No script or route opens its own
SQLite connection outside these two repository modules.

**Tech Stack:** Python 3.13 `sqlite3` (Wave 0 pattern), Node `better-sqlite3` (already in
`investment_screener/backend/package.json`, dependency `^12.11.1`, unused today), pytest
(`tmp_path`), Mocha + `ts-node/register` (confirmed the real TS test runner via
`package.json`'s `"test": "mocha -r ts-node/register 'tests/**/*.spec.ts'"` — **not** Jest,
**not** supertest-against-an-exported-app, which a prior effort's plan wrongly assumed and which
caused a dispatch failure; verified fresh for this plan).

## Global Constraints

(Carried from the spec and the Wave 0 plan — every task below implicitly includes these.)

- **This is a pivot, not an addition.** By the end of this wave, `projections/*.json` must no
  longer be read or written by any live code path.
- **No permanent hybrid.** A transitional dual-write window is allowed only inside this wave,
  with a named exit — not a resting state.
- **A domain is migrated only when:** producer writes SQLite + every real consumer reads SQLite +
  old file archived via `git mv`. Table existence or data copying alone do not count.
- **No script opens its own SQLite connection outside the owning repository/service layer** —
  restated because this is the first wave that tests it under real, 18-consumer rewiring pressure
  (see the original plan's Wave 1 roadmap entry).
- **Every wave reports the Wave KPI table** (JSON files before/after, reads/writes removed,
  producers/consumers migrated, context-bundle files removed, remaining exceptions named).
- **Archive convention:** `ARCHIVE/<mirrored source path>` via `git mv`.
- **No real data migration runs without a prior dry-run report and explicit user approval** — this
  is the same standing rule the prior SQLite effort's own corrective documents established
  (`master-status-and-outstanding-work.md` §4, §8) after real data loss occurred from skipping this
  step. Task 3 below is a hard gate for exactly this reason.

## What Was Freshly Re-Verified Before Writing This Plan (not trusted from the spec/prior docs)

Per the original implementation plan's explicit instruction ("re-read `ProjectionService.ts`,
`routes/projections.ts`, and `apply_catalyst.py` fresh... do not trust this document's producer
description as gospel"), the following was read directly from the current repository, not copied
from `migration-inventory-and-strategy.md`:

- **`ProjectionService.ts`** (`investment_screener/backend/src/services/ProjectionService.ts`):
  `saveProjection()` does read-modify-write-by-`id`, not blind append — if `req.body.id` matches
  an existing entry in the ticker's array, it increments that entry's `version` server-side and
  replaces it in place; otherwise it appends a new entry with `version = 1`. This upsert-by-id
  semantics must be replicated exactly by the SQLite-backed replacement (Task 5), not simplified to
  a naive insert.
- **Dual field-shape reality, confirmed in both `apply_catalyst.py` and the real Zod schema
  (`zod-schemas.ts:123-165`):** some projection entries carry `fairValue`/`action` at the
  **top level** (legacy shape, `apply_catalyst.py:100-104`'s `_get_fv_action()` handles both), the
  current schema nests them at `aiThesis.fairValue`/`aiThesis.action`. The migration script (Task 2)
  must handle both shapes per-entry, not assume the current schema shape applies to all 144 files
  uniformly — this is the exact class of bug (`researchReport` field-shape assumption) that caused
  the prior effort's corrective rewrite.
- **`scenarios` block is sometimes entirely absent** (`apply_catalyst.py:176-179`: "legacy
  format" branch) — `projection_scenario` rows are 0-3 per `projection_version`, not always 3.
- **`apply_catalyst.py` also writes `investment_screener/backend/data/theses/target-portfolio.json`**
  (not bare `target-portfolio.json` — confirmed the real path includes a `theses/` subdirectory,
  via `THESIS_JSON` constant at `apply_catalyst.py:44` and independently via
  `compute_conviction_scores.py:69`'s `TARGET_PATH` constant). This is a Wave 2 concern, noted here
  because it surfaced during this wave's fresh-read requirement — not a Wave 1 action item.
- **`better-sqlite3` is already a `package.json` dependency, unused in `src/`** (`grep -rl
  "better-sqlite3" investment_screener/backend/src/` → zero matches). This resolves the "confirm
  against `ProjectionService.ts`'s existing dependencies" open item from the original plan's Tech
  Stack line — the driver is available, just never wired up.
- **Real `ProjectionSchema` fields** (`zod-schemas.ts:123-165`), used to size `projection_repository.py`'s
  function signatures in Task 1: `ticker`, `id` (uuid), `source` (`USER`/`SYSTEM`/`AI_AGENT`),
  `schemaVersion`, `version`, `savedAt`, `updatedAt`, `name`, `rationale`, `snapshot` (`price`,
  `currency`, `shares`, `revenue`, `lastActualPS`, `fiscalPeriod`, `analystGrowthEstimate`,
  `analystMarginEstimate`), `dataPreferences` (`growthBasis`, `marginBasis`), `scenarios.{bear,base,bull}`
  (each a `ScenarioSchema`: `weight`, `growthRate`, `netMargin`, `exitPE`, `qualityMultiplier`,
  `shareChange`, `rationale`, `moatScore`, `managementScore`, `year5Revenue`, `year5NetIncome`,
  `year5EPS`, `scenarioPrice`, `risks`), `aiThesis` (optional: `model`, `rationale`, `fairValue`,
  `action`, `analyzedAt`, `researchReport`), `globalSettings` (`discountRate`, `timeHorizon`),
  `analyticsLog` (free-form record). `.passthrough()` on both `ProjectionSchema` and
  `ScenarioSchema` means unknown fields are preserved on save — the migration's `snapshot_json`/
  `analytics_log_json` columns must round-trip the full object, not a hand-picked subset.
- **Consumer file paths, confirmed to exist** (`find` run against the real repo, not assumed):
  `compute_conviction_scores.py`, `rebalancer.py`, `framework_score.py`, `generate_grok_prompt.py`,
  `peer_bench.py`, `comps_valuation.py`, `portfolio_action.py` at
  `investment_screener/backend/py_services/`; `persist_etf_analysis.py` at
  `plugins/etf-analysis/skills/etf_analysis/scripts/`; `ta_sweep_batch.py`, `watchlist_manager.py`
  at `plugins/tradingview/scripts/`; `generate_review.py`, `consolidate_research.py`,
  `scan_opportunities.py`, `verify_refresh.py`, `update_price_levels.py` at
  `plugins/portfolio-advisor/scripts/` (each also has one or more symlinked copies inside
  individual skill directories per this repo's symlink-manager convention — the canonical script
  path is the one to edit; symlinks resolve automatically).
- **`compute_conviction_scores.py`'s actual read pattern** (grepped directly):
  `PROJECTIONS_DIR = REPO_ROOT / "investment_screener/backend/data/projections"` (line 68), then
  `json.load(f)` at lines 338, 362, 383, 405 against `PROJECTIONS_DIR / f"{ticker}.json"` — a
  representative example of the swap every Python consumer in Task 7 needs, but **not** assumed to
  be identical in every other file; Task 7 requires each file's actual call site to be re-read
  before editing.

---

## Task 1: `projection_repository.py`

**Files:**
- Create: `investment_screener/backend/py_services/domain_model/projection_repository.py`
- Test: `investment_screener/backend/tests/py_services/test_projection_repository.py`

**Interfaces:**
- Consumes: `domain_model.db_client.initialize_db` (Wave 0 Task 1),
  `domain_model.investment_repository.resolve_investment` (Wave 0 Task 2, for test seeding).
- Produces:
  - `save_projection_version(conn, investment_id, version, saved_at, analyzed_at=None, model=None, fair_value=None, action=None, rationale=None, research_event_id=None, snapshot_json=None, analytics_log_json=None) -> str` — returns the generated `projection_id` (`f"{investment_id}:{version}"`). Upsert on `(investment_id, version)` — matches `ProjectionService.ts`'s confirmed upsert-by-id-then-version-increment semantics: **this function itself does not compute the next version number** (that's the caller's job, mirroring the TS service's existing responsibility split) — it persists whatever version it's given, upserting if that exact `(investment_id, version)` pair already exists.
  - `get_latest_projection(conn, investment_id) -> dict | None` — `ORDER BY version DESC LIMIT 1`.
  - `list_projection_versions(conn, investment_id) -> list[dict]` — all versions for a ticker, ascending by version (mirrors `ProjectionService.getProjections()`'s full-array return shape).
  - `add_projection_scenario(conn, projection_id, scenario_name, weight=None, growth_rate=None, net_margin=None, exit_pe=None, quality_multiplier=None, share_change=None, rationale=None, moat_score=None, management_score=None, year5_revenue=None, year5_net_income=None, year5_eps=None, scenario_price=None, risks_json=None) -> str` — upsert on `(projection_id, scenario_name)`.
  - `get_projection_scenarios(conn, projection_id) -> list[dict]`.

- [ ] **Step 1: Write the failing test**

```python
# investment_screener/backend/tests/py_services/test_projection_repository.py
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.investment_repository import resolve_investment  # noqa: E402
from domain_model.projection_repository import (  # noqa: E402
    save_projection_version,
    get_latest_projection,
    list_projection_versions,
    add_projection_scenario,
    get_projection_scenarios,
)


def _seed_investment(conn):
    return resolve_investment(conn, "AAPL", asset_class="EQUITY", currency="USD")


def test_save_and_get_latest_projection(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    investment_id = _seed_investment(conn)
    save_projection_version(
        conn, investment_id, version=1, saved_at="2026-07-01T00:00:00Z",
        fair_value=180.0, action="ACCUMULATE",
    )
    save_projection_version(
        conn, investment_id, version=2, saved_at="2026-07-10T00:00:00Z",
        fair_value=190.0, action="MAINTAIN",
    )
    latest = get_latest_projection(conn, investment_id)
    assert latest["version"] == 2
    assert latest["fair_value"] == 190.0
    assert latest["action"] == "MAINTAIN"


def test_save_projection_version_upserts_on_investment_and_version(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    investment_id = _seed_investment(conn)
    id_1 = save_projection_version(
        conn, investment_id, version=1, saved_at="2026-07-01T00:00:00Z", fair_value=180.0,
    )
    id_2 = save_projection_version(
        conn, investment_id, version=1, saved_at="2026-07-01T01:00:00Z", fair_value=185.0,
    )
    assert id_1 == id_2
    versions = list_projection_versions(conn, investment_id)
    assert len(versions) == 1
    assert versions[0]["fair_value"] == 185.0


def test_list_projection_versions_returns_all_ascending(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    investment_id = _seed_investment(conn)
    save_projection_version(conn, investment_id, version=1, saved_at="2026-07-01T00:00:00Z")
    save_projection_version(conn, investment_id, version=2, saved_at="2026-07-10T00:00:00Z")
    versions = list_projection_versions(conn, investment_id)
    assert [v["version"] for v in versions] == [1, 2]


def test_projection_with_no_scenarios_block(tmp_path):
    """Legacy-format projections have no 'scenarios' block at all (confirmed real,
    apply_catalyst.py:176-179's 'legacy format' branch) — get_projection_scenarios must
    return an empty list, not raise, for a projection_id with zero scenario rows."""
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    investment_id = _seed_investment(conn)
    projection_id = save_projection_version(
        conn, investment_id, version=1, saved_at="2026-07-01T00:00:00Z",
    )
    assert get_projection_scenarios(conn, projection_id) == []


def test_add_and_get_projection_scenarios(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    investment_id = _seed_investment(conn)
    projection_id = save_projection_version(
        conn, investment_id, version=1, saved_at="2026-07-01T00:00:00Z",
    )
    add_projection_scenario(
        conn, projection_id, "bear", weight=0.2, growth_rate=5.0, net_margin=10.0,
        exit_pe=15.0, quality_multiplier=1.0, share_change=0.0, scenario_price=150.0,
    )
    add_projection_scenario(
        conn, projection_id, "base", weight=0.5, growth_rate=10.0, net_margin=15.0,
        exit_pe=20.0, quality_multiplier=1.0, share_change=0.0, scenario_price=180.0,
    )
    add_projection_scenario(
        conn, projection_id, "bull", weight=0.3, growth_rate=15.0, net_margin=20.0,
        exit_pe=25.0, quality_multiplier=1.2, share_change=-1.0, scenario_price=220.0,
    )
    scenarios = get_projection_scenarios(conn, projection_id)
    assert {s["scenario_name"] for s in scenarios} == {"bear", "base", "bull"}


def test_add_projection_scenario_upserts_on_projection_and_name(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    investment_id = _seed_investment(conn)
    projection_id = save_projection_version(
        conn, investment_id, version=1, saved_at="2026-07-01T00:00:00Z",
    )
    add_projection_scenario(conn, projection_id, "bear", weight=0.2, scenario_price=150.0)
    add_projection_scenario(conn, projection_id, "bear", weight=0.25, scenario_price=155.0)
    scenarios = get_projection_scenarios(conn, projection_id)
    assert len(scenarios) == 1
    assert scenarios[0]["weight"] == 0.25
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_projection_repository.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'domain_model.projection_repository'`

- [ ] **Step 3: Write minimal implementation**

```python
# investment_screener/backend/py_services/domain_model/projection_repository.py
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
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(
        "SELECT * FROM projection_version WHERE investment_id = ? "
        "ORDER BY version DESC LIMIT 1;",
        (investment_id,),
    )
    row = cursor.fetchone()
    return dict(row) if row else None


def list_projection_versions(conn: sqlite3.Connection, investment_id: str) -> list[dict]:
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
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(
        "SELECT * FROM projection_scenario WHERE projection_id = ?;", (projection_id,),
    )
    return [dict(row) for row in cursor.fetchall()]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_projection_repository.py -v`
Expected: `6 passed`

- [ ] **Step 5: Commit**

```bash
git add investment_screener/backend/py_services/domain_model/projection_repository.py \
        investment_screener/backend/tests/py_services/test_projection_repository.py
git commit -m "feat: add projection_repository (projection_version + projection_scenario)"
```

---

## Task 2: Migration script — dry-run only

**Files:**
- Create: `investment_screener/backend/py_services/domain_model/migrate_projections_to_sqlite.py`
- Test: `investment_screener/backend/tests/py_services/test_migrate_projections_to_sqlite.py`

**Interfaces:**
- Consumes: `domain_model.investment_repository.resolve_investment`,
  `domain_model.projection_repository.save_projection_version`/`add_projection_scenario`
  (Tasks 1, and Wave 0 Task 2).
- Produces:
  - `parse_projection_entry(entry: dict) -> dict` — normalizes one array-entry from a
    `projections/{TICKER}.json` file into the flat kwargs `save_projection_version` expects,
    **handling both the legacy top-level `fairValue`/`action` shape and the current
    `aiThesis.fairValue`/`aiThesis.action` nested shape** (this is the specific bug class this
    whole migration corrects — get this function's dual-shape handling right, with a test for
    each shape, not just the current one).
  - `migrate_ticker_file(conn, ticker: str, entries: list[dict]) -> dict` — returns a per-ticker
    result summary: `{"ticker": ..., "versions_migrated": int, "scenarios_migrated": int,
    "errors": list[str]}`.
  - `run_dry_run(projections_dir: Path) -> dict` — walks every real `*.json` file in
    `projections_dir`, calls `parse_projection_entry`/`migrate_ticker_file` **against an
    in-memory `:memory:` SQLite connection**, never touching the real `domain_model.sqlite`, and
    returns an aggregate report: total files, total versions, total scenarios, list of any
    per-file parse errors (a real error must be reported per file, not swallowed — if any file
    fails to parse under both known shapes, that's a real finding for the dry-run report, not a
    silent skip).

**This task does NOT touch the real `domain_model.sqlite` and does NOT write anywhere.** It is a
pure read + in-memory-verify + report step, per the Global Constraints' standing rule that no real
migration runs without a prior dry-run report and explicit approval (Task 3).

- [ ] **Step 1: Write the failing test**

```python
# investment_screener/backend/tests/py_services/test_migrate_projections_to_sqlite.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_migrate_projections_to_sqlite.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'domain_model.migrate_projections_to_sqlite'`

- [ ] **Step 3: Write the implementation**

This step is intentionally NOT given complete code here, unlike Task 1. `parse_projection_entry`
must handle real-world messiness beyond what the 3 fixture entries above cover — before writing
this function, **read at least 10 real files from `investment_screener/backend/data/projections/`
directly** (pick a mix: some old, some recent, by `git log --format=%ai -1 -- <file>` or file
mtime) to confirm the dual-shape assumption holds across real data, not just the two shapes this
task's test fixtures describe. If a third shape variant is found, add a test for it before writing
the handling — do not special-case it silently in the implementation without a test proving the
case exists.

Implement `parse_projection_entry`, `migrate_ticker_file`, and `run_dry_run` to satisfy the tests
above, following the `save_projection_version`/`add_projection_scenario` signatures from Task 1
exactly (do not invent new parameter names). `run_dry_run` must use `sqlite3.connect(":memory:")`
(via `initialize_db(":memory:")`) — never a real file path — since this task's whole purpose is to
prove the migration logic works before touching real data.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_migrate_projections_to_sqlite.py -v`
Expected: all tests pass (count depends on any additional shape-variant tests added in Step 3)

- [ ] **Step 5: Run the dry run against the REAL `projections/` directory and write a report**

```bash
python3 -c "
import sys
sys.path.insert(0, 'investment_screener/backend/py_services')
from pathlib import Path
from domain_model.migrate_projections_to_sqlite import run_dry_run
import json
report = run_dry_run(Path('investment_screener/backend/data/projections'))
print(json.dumps(report, indent=2))
"
```

Save this real output to `docs/superpowers/status/wave1-projections-migration-dry-run-report.md`
— total files found (must be 144, or explain the delta if the real count has changed since the
spec was written), total versions, total scenarios, and the full list of any per-file errors. If
any file errors, this is a real finding to fix in Task 2 before proceeding (re-run Steps 3-5), not
something to skip.

- [ ] **Step 6: Commit**

```bash
git add investment_screener/backend/py_services/domain_model/migrate_projections_to_sqlite.py \
        investment_screener/backend/tests/py_services/test_migrate_projections_to_sqlite.py \
        docs/superpowers/status/wave1-projections-migration-dry-run-report.md
git commit -m "feat: add projections migration script (dry-run only, real 144-file report)"
```

---

## Task 3: HARD GATE — Dry-run review and explicit approval

**This is not a code task.** Present the dry-run report from Task 2 Step 5 to the user. Do not
proceed to Task 4 (the real migration) without explicit approval. This mirrors the standing rule
in the Global Constraints (no real migration runs without a prior dry-run report and explicit
user approval) and the exact corrective instruction that followed the prior effort's data-loss
incident.

---

## Task 4: Execute real migration (only after Task 3's approval)

**Files:**
- Modify: `investment_screener/backend/py_services/domain_model/migrate_projections_to_sqlite.py`
  (add a `--write` real-run mode to the script's CLI entry point, gated behind the same approval
  Task 3 secured)
- Create: `docs/superpowers/status/wave1-projections-migration-execution-report.md`

**This task runs the real migration against the real `domain_model.sqlite` file** (not
`:memory:`), populating `projection_version`/`projection_scenario` from all real
`projections/*.json` files. This does NOT delete or modify the source JSON files — insert-only
into SQLite, source files remain untouched pending Task 8's archive step, so this task is
reversible by simply deleting/rebuilding the SQLite file if a problem is found.

- [ ] **Step 1:** Run the real migration:

```bash
python3 -c "
import sys
sys.path.insert(0, 'investment_screener/backend/py_services')
from pathlib import Path
from domain_model.db_client import initialize_db
from domain_model.migrate_projections_to_sqlite import run_dry_run  # extend with a real-write variant per Step 3's design
# real-write invocation per the --write mode added in this task
"
```

(The exact CLI shape is this task's own design decision — follow the pattern of other real
migration scripts in this repo, e.g. `migrate_research_to_ledger.py`'s `--dry-run`/`--write`
flag convention, for consistency.)

- [ ] **Step 2:** Verify parity — for a sample of at least 20 tickers (not all 144, but a real
  cross-section including at least 3 with the legacy shape and 3 with missing `scenarios`),
  compare the SQLite row's `fair_value`/`action`/`version` against the source JSON file's latest
  entry, field by field. Record the comparison method and result in the execution report.

- [ ] **Step 3:** Write `docs/superpowers/status/wave1-projections-migration-execution-report.md`
  with: files migrated, versions migrated, scenarios migrated, parity-check sample results, any
  errors encountered and how they were resolved.

- [ ] **Step 4: Commit**

```bash
git add investment_screener/backend/py_services/domain_model/migrate_projections_to_sqlite.py \
        docs/superpowers/status/wave1-projections-migration-execution-report.md
git commit -m "feat: execute real projections migration (144 files, insert-only, source untouched)"
```

---

## Task 5: `ProjectionRepository.ts` + rewire `ProjectionService.ts`/`routes/projections.ts`

**Files:**
- Create: `investment_screener/backend/src/services/ProjectionRepository.ts`
- Modify: `investment_screener/backend/src/services/ProjectionService.ts`
- Test: `investment_screener/backend/tests/ProjectionRepository.spec.ts` (Mocha + `ts-node/register`,
  confirmed the real test runner — see this plan's Tech Stack section)

**This is the largest single task in this wave and the first real test of `better-sqlite3`
adoption.** Before writing code:

1. Confirm the domain-model SQLite file path convention this task should use — it must be a
   single, shared file across the Python `sqlite3` writer and this new Node `better-sqlite3`
   reader/writer (same file, WAL mode already enabled by `db_client.py`, which supports
   multi-process concurrent access). Do not create a second, divergent SQLite file.
2. `ProjectionService.getProjections()`/`getAllProjections()`/`deleteProjection()` must be
   reimplemented against SQL queries with **identical return shapes** to today's JSON-array
   return value — every consumer of this service (all 18, Task 7) expects the same `Projection[]`
   shape it gets today. `saveProjection()` must replicate the confirmed upsert-by-`id`-then-
   version-increment logic from this plan's "What Was Freshly Re-Verified" section exactly — read
   that section again before implementing, do not simplify it.
3. Zod validation (`ProjectionSchema.safeParse`) stays exactly as it is today — this task changes
   the persistence layer underneath the validation, not the validation itself.
4. Write real Mocha tests (matching the existing `tests/**/*.spec.ts` convention) against a real
   temp SQLite file (via `better-sqlite3`'s in-memory `:memory:` mode or a `tmp`-directory file),
   not mocks.

**Do not write this task's detailed TDD steps as pre-scripted code in this plan document** — the
exact `better-sqlite3` API surface and the existing `tests/` directory's real Mocha setup
(`before`/`after` hooks, fixture conventions) need to be read fresh at the moment this task is
implemented, per the same discipline this whole migration is built on. Follow this outline:

- [ ] Read the existing `tests/**/*.spec.ts` directory structure and one representative existing
  service test (if one exists for a comparable file-backed service) to match real conventions.
- [ ] Write failing Mocha tests for `ProjectionRepository.ts`'s `saveProjectionVersion`/
  `getLatestProjection`/`getAllProjections` methods (TypeScript-side equivalents of Task 1's
  Python functions — same upsert semantics, same table).
- [ ] Implement `ProjectionRepository.ts` using `better-sqlite3`, confirm tests pass.
- [ ] Rewrite `ProjectionService.ts` to delegate to `ProjectionRepository.ts` instead of
  `fs.promises.readFile`/`writeFile` — **keep the file-lock/atomic-write mechanics only if still
  needed** (SQLite's own transaction semantics likely replace `proper-lockfile`'s role for this
  table; confirm and remove the now-unnecessary lock dependency from this file if so, but do not
  touch `proper-lockfile`'s use elsewhere in the codebase).
- [ ] Confirm `routes/projections.ts` needs zero changes (it only calls `projectionService`
  methods, never touches the filesystem directly, confirmed by this plan's fresh read above) — if
  it does need changes, that's a signal this task's interface design deviated from the existing
  contract and should be reconsidered, not patched around.
- [ ] Run the full existing TS test suite (`npm test` in `investment_screener/backend`), not just
  the new file, to catch any consumer that breaks from a return-shape mismatch.
- [ ] Commit.

---

## Task 6: Rewire `apply_catalyst.py`

**Files:**
- Modify: `investment_screener/backend/py_services/apply_catalyst.py`
- Test: `investment_screener/backend/tests/py_services/test_apply_catalyst.py` (create if none
  exists — check first)

`apply_catalyst.py` currently does `json.loads(proj_path.read_text())` /
`locked_write_json(proj_path, out)` directly against `projections/{TICKER}.json`, bypassing
`ProjectionService.ts` entirely (confirmed real, second producer — see this plan's fresh-read
section). Rewire `_find_latest_ai_agent`, the `--record-sweep` branch, and the main write path to
use `projection_repository.get_latest_projection`/`save_projection_version` instead of
`proj_path.read_text()`/`locked_write_json`. Preserve every existing CLI flag and behavior
(`--dry-run`, `--write`, `--record-sweep`, `--update-thesis`) exactly — this task changes the
storage backend, not the tool's behavior or CLI surface.

**Note:** `--update-thesis`'s write to `investment_screener/backend/data/theses/target-portfolio.json`
is explicitly **out of scope for this task** — that file migrates in Wave 2, not Wave 1. Leave
that code path untouched.

- [ ] Read the current file fresh (already done for this plan — see "What Was Freshly
  Re-Verified" — but re-confirm nothing has changed since this plan was written before editing).
- [ ] Write failing tests covering: `--record-sweep` mode, a `--write` run with a preset catalyst
  type, and the legacy-vs-current shape handling (reuse Task 2's `parse_projection_entry` if the
  shapes overlap, or note if `apply_catalyst.py`'s own `_get_fv_action()` logic should be retired
  in favor of the shared parser instead of duplicated).
- [ ] Implement the rewire.
- [ ] Run tests, confirm pass.
- [ ] Commit.

---

## Task 7: Rewire Python/TS consumers (18 files, batched)

**Real file list, confirmed to exist** (from this plan's fresh-read section):
`compute_conviction_scores.py`, `rebalancer.py`, `framework_score.py`, `generate_grok_prompt.py`,
`peer_bench.py`, `comps_valuation.py`, `portfolio_action.py`,
`plugins/etf-analysis/skills/etf_analysis/scripts/persist_etf_analysis.py`,
`plugins/tradingview/scripts/ta_sweep_batch.py`, `plugins/tradingview/scripts/watchlist_manager.py`,
`plugins/portfolio-advisor/scripts/generate_review.py`,
`plugins/portfolio-advisor/scripts/consolidate_research.py`,
`plugins/portfolio-advisor/scripts/scan_opportunities.py`,
`plugins/portfolio-advisor/scripts/verify_refresh.py`,
`plugins/portfolio-advisor/scripts/update_price_levels.py`, `ThesisService.ts`
(version-history lookups, per the original plan's producer/consumer table),
`TradePrepModal.tsx`/`api.ts` (consume via the HTTP route only — confirmed **no direct file
access**, so these need zero changes once Task 5 lands; do not edit them, just confirm this
during Task 7's verification pass), `local_api.py` (confirmed **not a real consumer** —
docstring-only mention, per `migration-inventory-and-strategy.md`'s explicit finding, re-stated
here so this task doesn't waste a sub-task "fixing" a non-issue).

**This task is intentionally not pre-written with exact code**, for the same reason Task 5 isn't:
each file's real `json.load`/field-access call site must be read fresh before editing — this plan
confirmed `compute_conviction_scores.py`'s pattern (`PROJECTIONS_DIR / f"{ticker}.json"` at 4 call
sites) as one representative example, not a template assumed identical everywhere.

Split into 3 sub-tasks by risk/complexity, each following this per-file loop:
1. Read the file's actual `projections`/`PROJECTIONS_DIR` reference(s).
2. Identify what fields it actually accesses (not all 18 consumers need every field —
   `watchlist_manager.py` likely only needs `action`/`fairValue`, while `comps_valuation.py`
   likely needs the full `scenarios` block; confirm per file, don't assume).
3. Replace the `json.load`/file-read call with `projection_repository.get_latest_projection`/
   `list_projection_versions` (add `domain_model` to `sys.path` following the established
   convention from Wave 0/Task 1-6 files).
4. Run that file's existing tests (if any) or add a minimal one confirming the swap didn't change
   behavior.
5. Commit per sub-task batch (not per individual file — group by the 3 sub-task batches below to
   keep commit count reasonable while still keeping each commit's diff reviewable).

**Sub-task 7A (Python, portfolio-construction scripts):** `compute_conviction_scores.py`,
`rebalancer.py`, `framework_score.py`, `portfolio_action.py`, `comps_valuation.py`.

**Sub-task 7B (Python, plugin scripts):** `persist_etf_analysis.py`, `ta_sweep_batch.py`,
`watchlist_manager.py`, `generate_review.py`, `consolidate_research.py`, `scan_opportunities.py`,
`verify_refresh.py`, `update_price_levels.py`, `generate_grok_prompt.py`, `peer_bench.py`.

**Sub-task 7C (TypeScript):** `ThesisService.ts` — confirm its exact version-history read pattern
fresh (it wasn't grepped for this plan; do so before writing 7C's own task brief).

- [ ] Sub-task 7A: read all 5 files, rewire, test, commit.
- [ ] Sub-task 7B: read all 10 files, rewire, test, commit.
- [ ] Sub-task 7C: read `ThesisService.ts` fresh, rewire, test, commit.
- [ ] Verification: `grep -rn "data/projections" investment_screener plugins` returns zero
  matches representing real file I/O (doc/comment mentions excluded, each verified individually)
  — this is the archive-readiness gate for Task 8.

---

## Task 8: Archive `projections/` directory

**Only after Tasks 1-7 are complete and Task 7's verification grep returns clean.**

- [ ] Confirm one more time: `grep -rn "data/projections" investment_screener plugins` — zero real
  I/O matches.
- [ ] `git mv investment_screener/backend/data/projections
  ARCHIVE/investment_screener/backend/data/projections` (per this migration's archive convention,
  spec §2.19 — `projections/*.json` is git-tracked, not gitignored, so this is a real `git mv`
  with full history preserved, not a local-only copy).
- [ ] Run the full test suite + `python3 run_tests.py` one more time to confirm nothing still
  references the now-archived path.
- [ ] Commit: `git commit -m "refactor: archive projections/ after Wave 1 SQLite cutover (144 files)"`.

---

## Task 9: Wave 1 exit report

**Files:**
- Create: `docs/superpowers/status/wave1-projections-report.md`

Fill in, with real numbers gathered from Tasks 1-8 (not estimates):

- **Wave KPI table** (spec's template): active JSON files before (144 + other domains, report the
  delta) → after (0 for this domain), files archived (144), JSON reads removed, JSON writes
  removed, producers migrated (2/2), consumers migrated (18/18 — or the real count confirmed
  during Task 7's fresh reads, if it differs from this plan's assumption), plugin/skill/agent
  references updated (per the original plan's §4 table — `daily-loop-agent.md`,
  `single-stock-advisor.md`, `13f-analyze`, `adversarial-review`, `portfolio-health`,
  `set-thesis-breakers`, `strategic-review`, `thesis-challenge-bundler`, `x-news-sweep`,
  `stock-research`, `stock_valuation`, `alert-sync`, `ta-snapshot`,
  `technical-analysis-expert` — confirm each still references `projections/*.json` by path
  before claiming it "updated"; some may only reference it conceptually in prose and need no
  change), context-bundle files removed.
- **Hybrid Exit Criteria**: confirm no dual-write state remains — both producers write SQLite
  only, both are verified via the grep in Task 7/8.
- **Definition of Done** (all 9 items from the original plan, with real evidence per item — not
  "N/A" this time, since this is a real cutover wave, unlike Wave 0).
- **Rollback note**: since `projections/` was git-tracked and archived via `git mv` (not deleted),
  rollback is `git mv ARCHIVE/... investment_screener/backend/data/projections` plus reverting
  Tasks 1, 4-8's commits — record this explicitly, don't just reference the general policy.

---

## Self-Review

**1. Spec coverage:** Task 1 fully implements the spec's `projection_version`/
`projection_scenario` design (§2.5, §3). Tasks 2-4 implement the migration-with-approval-gate
pattern the spec's Global Constraints and Anti-Regression Lessons require. Task 5-6 cover both
real producers (spec §2.5's corrected 2-producer count). Task 7 covers all 18 real consumers.
Task 8 implements the archive rule (§2.19 for git-tracked files). Task 9 implements the Wave KPI
table, Hybrid Exit Criteria, and Definition of Done the spec requires per wave.

**2. Placeholder scan:** Task 1 contains complete, real code (mirrors Wave 0's Task 1-4 pattern,
already proven to pass review). Tasks 2, 5, 6, 7 are deliberately NOT pre-written with exact code
beyond their test fixtures and interface signatures — each explicitly states why (real data
shape verification needed, real TS test conventions needed, real per-file read needed) rather
than silently omitting detail. This is the same honest pattern the original plan used for whole
waves, applied here at sub-task granularity because this wave's research (done fresh for this
plan) went deep enough to fully specify Tasks 1-4 and 8-9, but not deep enough to safely
pre-script Tasks 5-7's exact code without re-reading each file at implementation time.

**3. Type consistency:** `save_projection_version`'s parameter names in Task 1 (`investment_id`,
`version`, `saved_at`, `fair_value`, `action`, etc.) are used identically in Task 2's
`parse_projection_entry`/`migrate_ticker_file` interface description and Task 6's rewire
instructions — no renamed fields across tasks.
