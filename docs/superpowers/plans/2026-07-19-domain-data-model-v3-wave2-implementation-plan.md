# Domain Data Model v3.2 — Wave 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

## Execution Model Update (approved after plan review, supersedes any per-task review cadence implied below)

Wave 2 uses **conditional autonomy**, not a review-per-task cadence. The task breakdown below still
applies for structure/sequencing/commits, but:

- **Do not dispatch an independent review after every task.** Fix issues found along the way and
  continue executing the wave end-to-end.
- **Perform one comprehensive review at exactly two points:** (1) the dry-run gate (Task 6/7's
  "STOP — hard approval gate" step, before real data is touched), and (2) the Wave 2 exit report
  (Task 15), before the PR is opened.
- **Hard-stop conditions still apply in full** (see the overall implementation plan's Hard-Stop
  Conditions list, restated here for this wave): dry-run anomalies, a parity mismatch, any
  `standingDecision`/CLAUDE.md #8 regression risk, archive-readiness grep failure, a new (not
  pre-existing-baseline) test regression, or any script bypassing the repository/service layer to
  open its own SQLite connection. Stop immediately and report evidence if any of these occur —
  do not fix-and-continue past a hard-stop condition the way ordinary task-level issues are handled.
- This does not change what Task 15 already requires (Wave KPI table, producer/consumer cutover
  table, real bugs found and fixed, validation results, archive evidence, rollback instructions,
  commit list, handoff doc, PR, then **stop — do not start Wave 3**).

**Goal:** Migrate `target-portfolio.json` + `watchlist.json` + their embedded sub-domains (price
levels, investment notes/`agentRationale`, standing decision, thesis breaker state) plus
`tradingview_alerts_actual.json` into the v3.2 `investment`/`strategy_pillar`/`sub_strategy`/
`price_level_set`/`price_level_tier`/`investment_note`/`alert` tables (schema already created by
Wave 0), with every real producer/consumer cut over and the source JSON archived.

**Architecture:** New repository modules in the existing `investment_screener/backend/
py_services/domain_model/` package (mirrors Wave 1's `projection_repository.py` pattern — one
module per table, no script opens its own `sqlite3.connect()` against these tables). A single
migration script reads the real `target-portfolio.json`/`watchlist.json`/
`tradingview_alerts_actual.json`/`thesis_breaker_state.json` and populates the already-existing
`investment` rows (backfilled identity-only by Wave 0) with full fields, plus the new child rows.

**Tech Stack:** Python 3.13 `sqlite3` stdlib (repositories, migration script), TypeScript/Express
for `BrokerSyncService.ts`/`WatchlistService.ts`/`ThesisService.ts` producer-side cutover work in
later sub-waves.

## Global Constraints

(Copied verbatim from the spec/overall plan — every task below implicitly includes these.)

- **This is a pivot, not an addition.** SQLite/domain repositories become the primary persistence
  layer; JSON must not remain an active operational store without an explicit approved exception
  (spec §2.18).
- **No permanent hybrid.** `JSON + JSONL + SQLite` forever is a failed wave, not a resting state.
- **A domain is migrated only when:** producer writes SQLite + every real consumer reads SQLite +
  old file archived via `git mv`. Table existence, data copying, or a passing fixture test do not
  count.
- **No script opens its own SQLite connection outside the owning repository/service layer** — this
  applies to every new Python repository module in this plan and to any TS service class.
- **No generic `REMAINS_JSON_BY_DESIGN` label.** Any JSON this wave proposes to keep must complete
  the Retained-JSON Rationale Bar (spec §2.18) — no domain in this wave's scope is expected to
  need it (see "JSON Retirement Criteria" below), but the bar applies if one is ever proposed.
- **Dry-run before any real-data write, with an explicit approval gate.** The migration script must
  support `--dry-run` (default) producing a full report before `--write` runs against real
  `target-portfolio.json`/`watchlist.json`/`tradingview_alerts_actual.json`/
  `thesis_breaker_state.json`. **Do not run `--write` without presenting the dry-run report to the
  user and receiving explicit sign-off first** — non-negotiable, tied to a real data-loss incident
  from before this corrective effort began.
- **Archive only after producer + consumer cutover, archive-readiness grep clean, tests green.**
  `git mv` to `ARCHIVE/<mirrored path>`.
- **Every wave reports:** Wave KPI table, context-bundler impact, exit report — matching Wave 1's
  depth (`docs/superpowers/status/wave1-projections-report.md`).

## Investigation Findings Used As Confirmed Inputs (not optional notes)

- Real path of `target-portfolio.json`: `investment_screener/backend/data/theses/
  target-portfolio.json` (has a `theses/` subdirectory).
- Real path of `watchlist.json`: `investment_screener/backend/data/watchlist.json`.
- **11 producers confirmed correct** as originally listed in the spec: `BrokerSyncService.ts`,
  `market_regime.py`, `risk_engine.py`, `rebalancer.py`, `backtest_harness.py`,
  `thesis_breakers.py`, `ta_sweep_batch.py`, `daily_brief.py`, `update_thesis.py`,
  `validate_weights.py`, `update_price_levels.py`, plus `WatchlistService.ts` for `watchlist.json`.
- **Two stale-path bugs found, must be fixed as a preliminary Wave 2 task (Task 0 below), not
  silently ignored:**
  - `investment_screener/backend/py_services/backtest_harness.py:24,118` —
    `extract_historical_targets()` reads a historical git blob at the pre-move path
    `investment_screener/backend/data/target-portfolio.json` (no `theses/`). Classification:
    **non-breaking today** (only affects reading pre-move historical commits, which is
    semantically the point of a "historical" reader), but a **migration blocker if left
    unresolved** — once Wave 2 archives the current file, this function's purpose (reading
    historical snapshots of the target file across commits) must be explicitly re-verified against
    both path shapes or it silently produces wrong/empty results for post-move commits without
    any error.
  - `investment_screener/backend/py_services/order_risk_gates.py:174` — `TARGET_PORTFOLIO_PATH`
    module-level default constant is missing `theses/`. Classification: **non-breaking today**
    (line 260 always overrides it with `target_portfolio_path or TARGET_PORTFOLIO_PATH`, and no
    caller currently omits the argument), but a **migration blocker if left unresolved** — a latent
    landmine for any future caller that omits the argument, and it must not survive this wave's
    "no stale reference to the old JSON path" bar.
- **`portfolio_action.py` (6 copies across skills, symlinked from a canonical source) was missing
  from the spec's original consumer inventory — confirmed as a real active consumer, added to the
  Wave 2 consumer list below.** Per this repo's symlink convention (`symlink_manager.py`, CLAUDE.md
  rule #5): update the **canonical source only**, then verify each of the 6 skill-side symlinks
  resolves correctly — never edit a symlinked copy directly.
- **Real field shapes, confirmed against actual data** (used to size the repository/migration
  code below, not invented):
  - `holdings[].priceLevels` (8/75 holdings populated): nested object — `{schemaVersion,
    lastUpdated, lastUpdatedBy, note, buyTiers: [{tier, price, action, trimPct, orderType, basis,
    source, sourceDate, condition, status}], sellTiers: [...same shape...], stopLoss: {price,
    basis, source, sourceDate, type, status}}`.
  - `holdings[].targetEntryPrice` (2/75 populated): scalar float, mostly `null`.
  - `holdings[].agentRationale` (73/75 populated): plain string, historically hand-concatenated
    with inline date stamps (e.g. `IREN` has 5 embedded date-stamps) — this wave migrates it into
    one `investment_note` row per holding (`note_type='MIGRATED_LEGACY_RATIONALE'`, the full
    existing string as `body`, `note_date` = the file's own `holdings[].lastUpdated` field if
    present else migration-run timestamp) rather than attempting free-text date-parsing/splitting
    into multiple historical rows — splitting the embedded date-stamps is explicitly out of scope
    (would require unreliable prose parsing); `investment.agent_rationale` becomes a denormalized
    "latest note body" convenience column per the spec, populated from the same string.
  - `standingDecision` fields (`standing_decision_type`, `standing_decision_reason`,
    `standing_decision_source`, `standing_decision_review`) must preserve existing read/write
    behavior exactly — this is CLAUDE.md rule #8, the single highest-risk item in this wave.
  - `thesis_breaker_state.json` folds directly into `investment.thesis_breaker_status` (already a
    column) — no separate table, confirmed correct, no evidence found to the contrary.

## JSON Retirement Criteria (per spec §2.0/§2.18 — stated explicitly, not left implicit)

| File | Retirement trigger (all must be true before archive) |
|---|---|
| `target-portfolio.json` | All 11 producers write `investment`/`strategy_pillar`/`sub_strategy`/`price_level_set`/`price_level_tier`/`investment_note` exclusively; all 19 core consumers (18 original + `portfolio_action.py`) + `standingDecision`-specific tests read the same; `backtest_harness.py`/`order_risk_gates.py` stale-path bugs fixed; archive-readiness grep clean |
| `watchlist.json` | `WatchlistService.ts` producer + 6 consumers (`overnight_gaps.py`, `WatchlistService.ts` read-side, `paths.ts`, `weekly_review.py`, `watchlist_manager.py`, `tradingview-cdp/cli.js`) cut over to `investment.is_watchlisted`/`watchlist_added_at`; archive-readiness grep clean |
| `tradingview_alerts_actual.json` | `tv_list_alerts.py` (both copies) cut over to `alert` table; archive-readiness grep clean |
| `thesis_breaker_state.json` | `thesis_breakers.py` producer + 4 consumers (`order_risk_gates.py`, `rebalancer.py`, `harvest_predictions.py`, `risk_officer.py`) cut over to `investment.thesis_breaker_status`; archive-readiness grep clean |

No file in this wave's scope is expected to need the Retained-JSON Rationale Bar — every one has a
concrete retirement path stated above. If a wave-time discovery makes one impossible to retire, the
Rationale Bar (spec §2.18) must be completed before it is kept, not labeled by default.

---

## Task 0: Fix stale `target-portfolio.json` path references (preliminary, before any migration code)

**Why first:** these are real, confirmed bugs (not migration-created) that would otherwise survive
past this wave's archive step and silently break once the current file path stops being read by
anything else as a cross-check. Fixing them now, with tests, closes them before they can hide
inside a larger diff.

**Files:**
- Modify: `investment_screener/backend/py_services/backtest_harness.py:24,118`
- Modify: `investment_screener/backend/py_services/order_risk_gates.py:174`
- Test: `investment_screener/backend/tests/py_services/test_backtest_harness_historical_path.py`
- Test: `investment_screener/backend/tests/py_services/test_order_risk_gates_target_path_constant.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: nothing new — these are targeted bug fixes to existing functions/constants.

- [ ] **Step 1: Read both files fresh to confirm exact current line content**

Run: `sed -n '1,30p;110,125p' investment_screener/backend/py_services/backtest_harness.py`
Run: `sed -n '165,180p' investment_screener/backend/py_services/order_risk_gates.py`

Confirm the exact current string literal/constant value before editing — do not trust the
investigation summary's line numbers as gospel; they may have shifted since the grep was run.

- [ ] **Step 2: Write the failing test for `order_risk_gates.py`'s stale constant**

```python
# investment_screener/backend/tests/py_services/test_order_risk_gates_target_path_constant.py
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

import order_risk_gates  # noqa: E402


def test_target_portfolio_path_constant_includes_theses_subdirectory():
    """The real file lives at data/theses/target-portfolio.json (confirmed by
    compute_conviction_scores.py's TARGET_PATH and apply_catalyst.py's THESIS_JSON
    constants). order_risk_gates.py's TARGET_PORTFOLIO_PATH default was found stale
    (missing the theses/ subdirectory) during Wave 2 investigation — currently masked
    because every call site overrides it, but a latent landmine for any future caller
    that doesn't. This test locks in the correct value so it can't silently regress.
    """
    assert "theses" in str(order_risk_gates.TARGET_PORTFOLIO_PATH)
    assert str(order_risk_gates.TARGET_PORTFOLIO_PATH).endswith(
        "theses/target-portfolio.json"
    )
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_order_risk_gates_target_path_constant.py -v`
Expected: FAIL (assertion error — current constant lacks `theses/`)

- [ ] **Step 4: Fix `order_risk_gates.py`'s stale constant**

Edit line 174 (confirmed exact content in Step 1) to insert `theses/` into the path, matching the
exact construction pattern already used by `compute_conviction_scores.py::TARGET_PATH` (read that
file's constant definition first and mirror its exact `Path(...)`/string-join style — do not
introduce a second, differently-styled path-construction pattern).

- [ ] **Step 5: Run test to verify it passes**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_order_risk_gates_target_path_constant.py -v`
Expected: PASS

- [ ] **Step 6: Write the failing test for `backtest_harness.py`'s historical-blob reader**

```python
# investment_screener/backend/tests/py_services/test_backtest_harness_historical_path.py
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

import backtest_harness  # noqa: E402


def test_extract_historical_targets_tries_both_pre_and_post_move_paths():
    """extract_historical_targets() reads target-portfolio.json out of historical git
    blobs. The file moved from data/target-portfolio.json to data/theses/
    target-portfolio.json partway through this repo's history (Wave 2 investigation
    finding). A commit-SHA-agnostic historical reader must try both paths, since it
    has no way to know a priori whether a given historical commit predates the move.
    Silently trying only one path means every commit on the other side of the move
    returns empty/wrong data with no error — the exact failure mode this test guards.
    """
    candidate_paths = backtest_harness.candidate_target_portfolio_paths()
    assert "investment_screener/backend/data/target-portfolio.json" in candidate_paths
    assert (
        "investment_screener/backend/data/theses/target-portfolio.json"
        in candidate_paths
    )
```

- [ ] **Step 7: Run test to verify it fails**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_backtest_harness_historical_path.py -v`
Expected: FAIL with `AttributeError: module 'backtest_harness' has no attribute 'candidate_target_portfolio_paths'`

- [ ] **Step 8: Read `extract_historical_targets()`'s real current implementation, then fix**

Read `investment_screener/backend/py_services/backtest_harness.py` around lines 20-30 and 110-125
in full (not just the two line numbers) to see exactly how the historical git-blob read is
performed (e.g. `git show <sha>:<path>`). Add a small `candidate_target_portfolio_paths() ->
list[str]` function returning both the pre-move and post-move relative paths, and change
`extract_historical_targets()` to try the post-move path first, falling back to the pre-move path
on a `git show` failure (nonzero exit / `CalledProcessError` / empty stdout — match whatever error
shape the existing git-blob-read call already raises, confirmed by reading the code, not assumed).

- [ ] **Step 9: Run both tests to verify they pass**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_backtest_harness_historical_path.py tests/py_services/test_order_risk_gates_target_path_constant.py -v`
Expected: `2 passed`

- [ ] **Step 10: Run the full existing test files for both modules to confirm no regression**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/ -k "backtest_harness or order_risk_gates" -v`
Expected: all pass, no new failures beyond the documented pre-existing baseline.

- [ ] **Step 11: Commit**

```bash
git add investment_screener/backend/py_services/backtest_harness.py \
        investment_screener/backend/py_services/order_risk_gates.py \
        investment_screener/backend/tests/py_services/test_backtest_harness_historical_path.py \
        investment_screener/backend/tests/py_services/test_order_risk_gates_target_path_constant.py
git commit -m "fix: close two stale target-portfolio.json path references found during Wave 2 investigation"
```

---

## Task 1: `pillar_repository.py` (strategy_pillar + sub_strategy)

**Files:**
- Create: `investment_screener/backend/py_services/domain_model/pillar_repository.py`
- Test: `investment_screener/backend/tests/py_services/test_pillar_repository.py`

**Interfaces:**
- Consumes: `domain_model.db_client.initialize_db` (Wave 0, already exists).
- Produces:
  - `resolve_pillar(conn, pillar_id: str, name: str, target_weight: float | None = None) -> str` — idempotent upsert, returns `pillar_id`.
  - `resolve_sub_strategy(conn, sub_strategy_id: str, pillar_id: str, name: str) -> str` — idempotent upsert, returns `sub_strategy_id`.
  - `list_pillars(conn) -> list[dict]`
  - `list_sub_strategies(conn, pillar_id: str | None = None) -> list[dict]`

- [ ] **Step 1: Write the failing test**

```python
# investment_screener/backend/tests/py_services/test_pillar_repository.py
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.pillar_repository import (  # noqa: E402
    resolve_pillar,
    resolve_sub_strategy,
    list_pillars,
    list_sub_strategies,
)


def test_resolve_pillar_creates_and_is_idempotent(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    id_1 = resolve_pillar(conn, "AI_INFRA", "AI Infrastructure", target_weight=0.35)
    id_2 = resolve_pillar(conn, "AI_INFRA", "AI Infrastructure", target_weight=0.35)
    assert id_1 == id_2 == "AI_INFRA"
    rows = list_pillars(conn)
    assert len(rows) == 1
    assert rows[0]["target_weight"] == 0.35


def test_resolve_sub_strategy_creates_and_is_idempotent(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    resolve_pillar(conn, "AI_INFRA", "AI Infrastructure")
    id_1 = resolve_sub_strategy(conn, "AI_COMPUTE", "AI_INFRA", "AI Compute")
    id_2 = resolve_sub_strategy(conn, "AI_COMPUTE", "AI_INFRA", "AI Compute")
    assert id_1 == id_2 == "AI_COMPUTE"
    rows = list_sub_strategies(conn, pillar_id="AI_INFRA")
    assert len(rows) == 1


def test_resolve_pillar_updates_on_repeat_call_with_new_weight(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    resolve_pillar(conn, "AI_INFRA", "AI Infrastructure", target_weight=0.30)
    resolve_pillar(conn, "AI_INFRA", "AI Infrastructure", target_weight=0.35)
    rows = list_pillars(conn)
    assert rows[0]["target_weight"] == 0.35
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_pillar_repository.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'domain_model.pillar_repository'`

- [ ] **Step 3: Write minimal implementation**

```python
# investment_screener/backend/py_services/domain_model/pillar_repository.py
"""All ``strategy_pillar``/``sub_strategy`` table reads and writes live here
(ADR-029 anti-duplication rule, same as investment_repository.py/account_repository.py)."""

import sqlite3


def resolve_pillar(
    conn: sqlite3.Connection,
    pillar_id: str,
    name: str,
    target_weight: float | None = None,
) -> str:
    conn.execute(
        "INSERT INTO strategy_pillar (pillar_id, name, target_weight) VALUES (?, ?, ?) "
        "ON CONFLICT(pillar_id) DO UPDATE SET name=excluded.name, "
        "target_weight=excluded.target_weight;",
        (pillar_id, name, target_weight),
    )
    conn.commit()
    return pillar_id


def resolve_sub_strategy(
    conn: sqlite3.Connection,
    sub_strategy_id: str,
    pillar_id: str,
    name: str,
) -> str:
    conn.execute(
        "INSERT INTO sub_strategy (sub_strategy_id, pillar_id, name) VALUES (?, ?, ?) "
        "ON CONFLICT(sub_strategy_id) DO UPDATE SET pillar_id=excluded.pillar_id, "
        "name=excluded.name;",
        (sub_strategy_id, pillar_id, name),
    )
    conn.commit()
    return sub_strategy_id


def list_pillars(conn: sqlite3.Connection) -> list[dict]:
    conn.row_factory = sqlite3.Row
    cursor = conn.execute("SELECT * FROM strategy_pillar;")
    return [dict(row) for row in cursor.fetchall()]


def list_sub_strategies(
    conn: sqlite3.Connection, pillar_id: str | None = None
) -> list[dict]:
    conn.row_factory = sqlite3.Row
    if pillar_id:
        cursor = conn.execute(
            "SELECT * FROM sub_strategy WHERE pillar_id = ?;", (pillar_id,)
        )
    else:
        cursor = conn.execute("SELECT * FROM sub_strategy;")
    return [dict(row) for row in cursor.fetchall()]
```

Note: `strategy_pillar`/`sub_strategy` have no `ON CONFLICT` unique-name constraint issue here
because `pillar_id`/`sub_strategy_id` are the primary keys — the upsert conflicts on PK, which is
correct since IDs are stable slugs, not autoincrement.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_pillar_repository.py -v`
Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add investment_screener/backend/py_services/domain_model/pillar_repository.py \
        investment_screener/backend/tests/py_services/test_pillar_repository.py
git commit -m "feat: add pillar_repository (strategy_pillar + sub_strategy)"
```

---

## Task 2: `price_level_repository.py`

**Files:**
- Create: `investment_screener/backend/py_services/domain_model/price_level_repository.py`
- Test: `investment_screener/backend/tests/py_services/test_price_level_repository.py`

**Interfaces:**
- Consumes: `resolve_investment`/`get_investment` (Wave 0's `investment_repository.py`).
- Produces:
  - `replace_price_levels(conn, investment_id: str, schema_version: str | None, last_updated: str | None, last_updated_by: str | None, note: str | None, buy_tiers: list[dict], sell_tiers: list[dict], stop_loss: dict | None, target_entry_price: float | None) -> str` — deletes any existing `price_level_set`/`price_level_tier` rows for this investment and inserts fresh ones (full-replace semantics, matching the source JSON's own full-object-replace pattern — `update_price_levels.py` always rewrites the whole `priceLevels` object, never patches a single tier in place, confirmed by the real field shape investigation). Returns the new `price_level_set_id`. `target_entry_price`, if not `None`, is inserted as a `price_level_tier` row with `tier_kind='TARGET_ENTRY'` (per spec §2.2 — a genuine price level, not a scalar duplicate of buy tiers).
  - `get_price_levels(conn, investment_id: str) -> dict | None` — returns `{price_level_set: {...}, buy_tiers: [...], sell_tiers: [...], stop_loss: {...} | None, target_entry: {...} | None}` or `None` if the investment has no price level set.

- [ ] **Step 1: Write the failing test**

```python
# investment_screener/backend/tests/py_services/test_price_level_repository.py
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.investment_repository import resolve_investment  # noqa: E402
from domain_model.price_level_repository import (  # noqa: E402
    replace_price_levels,
    get_price_levels,
)


def _seed_investment(conn):
    return resolve_investment(conn, "SNDK", asset_class="EQUITY", currency="USD")


def test_replace_price_levels_creates_full_structure(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    investment_id = _seed_investment(conn)
    replace_price_levels(
        conn,
        investment_id,
        schema_version="1.0",
        last_updated="2026-07-01T00:00:00Z",
        last_updated_by="update_price_levels.py",
        note="Q2 revision",
        buy_tiers=[
            {"tier": 1, "price": 1048.0, "action": "BUY", "trimPct": None,
             "orderType": "LIMIT", "basis": "support", "source": "TA",
             "sourceDate": "2026-06-01", "condition": None, "status": "ACTIVE"},
            {"tier": 2, "price": 1070.0, "action": "BUY", "trimPct": None,
             "orderType": "LIMIT", "basis": "support", "source": "TA",
             "sourceDate": "2026-06-01", "condition": None, "status": "ACTIVE"},
        ],
        sell_tiers=[],
        stop_loss={"price": 950.0, "basis": "support", "source": "TA",
                    "sourceDate": "2026-06-01", "type": "HARD", "status": "ACTIVE"},
        target_entry_price=1350.0,
    )
    result = get_price_levels(conn, investment_id)
    assert result is not None
    assert len(result["buy_tiers"]) == 2
    assert result["buy_tiers"][0]["price"] == 1048.0
    assert result["stop_loss"]["price"] == 950.0
    assert result["target_entry"]["price"] == 1350.0
    # Real-data regression guard: SNDK's target entry (1350) must NOT collapse into
    # or overwrite a buy tier (1048/1070) — confirmed distinct real values from the
    # Wave 2 field-shape investigation.
    assert result["target_entry"]["price"] not in {1048.0, 1070.0}


def test_replace_price_levels_is_full_replace_not_append(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    investment_id = _seed_investment(conn)
    replace_price_levels(
        conn, investment_id, schema_version="1.0", last_updated=None,
        last_updated_by=None, note=None,
        buy_tiers=[{"tier": 1, "price": 100.0, "action": "BUY", "trimPct": None,
                     "orderType": "LIMIT", "basis": None, "source": None,
                     "sourceDate": None, "condition": None, "status": "ACTIVE"}],
        sell_tiers=[], stop_loss=None, target_entry_price=None,
    )
    replace_price_levels(
        conn, investment_id, schema_version="1.1", last_updated=None,
        last_updated_by=None, note=None,
        buy_tiers=[{"tier": 1, "price": 200.0, "action": "BUY", "trimPct": None,
                     "orderType": "LIMIT", "basis": None, "source": None,
                     "sourceDate": None, "condition": None, "status": "ACTIVE"}],
        sell_tiers=[], stop_loss=None, target_entry_price=None,
    )
    result = get_price_levels(conn, investment_id)
    assert len(result["buy_tiers"]) == 1  # not 2 — old set was replaced, not appended
    assert result["buy_tiers"][0]["price"] == 200.0


def test_get_price_levels_returns_none_for_investment_with_no_levels(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    investment_id = _seed_investment(conn)
    assert get_price_levels(conn, investment_id) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_price_level_repository.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# investment_screener/backend/py_services/domain_model/price_level_repository.py
"""All ``price_level_set``/``price_level_tier`` table reads and writes live here.

Full-replace semantics, matching the source JSON's own full-object-rewrite pattern:
``update_price_levels.py`` always rewrites the whole ``priceLevels`` object, never
patches a single tier in place (confirmed against real data during Wave 2
investigation). ``target_entry_price`` becomes a ``tier_kind='TARGET_ENTRY'`` row,
kept distinct from buy tiers per spec s2.2 (confirmed real divergence, e.g. SNDK:
target 1350 vs. buy tiers 1048/1070).
"""

import sqlite3
import uuid


def replace_price_levels(
    conn: sqlite3.Connection,
    investment_id: str,
    schema_version: str | None,
    last_updated: str | None,
    last_updated_by: str | None,
    note: str | None,
    buy_tiers: list[dict],
    sell_tiers: list[dict],
    stop_loss: dict | None,
    target_entry_price: float | None,
) -> str:
    existing = conn.execute(
        "SELECT price_level_set_id FROM price_level_set WHERE investment_id = ?;",
        (investment_id,),
    ).fetchone()
    if existing:
        old_set_id = existing[0]
        conn.execute(
            "DELETE FROM price_level_tier WHERE price_level_set_id = ?;", (old_set_id,)
        )
        conn.execute(
            "DELETE FROM price_level_set WHERE price_level_set_id = ?;", (old_set_id,)
        )

    price_level_set_id = f"{investment_id}-pls-{uuid.uuid4().hex[:8]}"
    conn.execute(
        "INSERT INTO price_level_set "
        "(price_level_set_id, investment_id, schema_version, last_updated, "
        "last_updated_by, note) VALUES (?, ?, ?, ?, ?, ?);",
        (price_level_set_id, investment_id, schema_version, last_updated,
         last_updated_by, note),
    )

    def _insert_tier(tier_kind: str, tier: dict) -> None:
        tier_id = f"{price_level_set_id}-{tier_kind}-{tier.get('tier', uuid.uuid4().hex[:6])}"
        conn.execute(
            "INSERT INTO price_level_tier "
            "(tier_id, price_level_set_id, tier_kind, tier_number, price, action, "
            "trim_pct, order_type, basis, source, source_date, condition, status) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);",
            (tier_id, price_level_set_id, tier_kind, tier.get("tier", 0),
             tier.get("price"), tier.get("action"), tier.get("trimPct"),
             tier.get("orderType"), tier.get("basis"), tier.get("source"),
             tier.get("sourceDate"), tier.get("condition"), tier.get("status")),
        )

    for tier in buy_tiers:
        _insert_tier("BUY_TIER", tier)
    for tier in sell_tiers:
        _insert_tier("SELL_TIER", tier)
    if stop_loss:
        tier_id = f"{price_level_set_id}-STOP_LOSS"
        conn.execute(
            "INSERT INTO price_level_tier "
            "(tier_id, price_level_set_id, tier_kind, tier_number, price, basis, "
            "source, source_date, condition, status) "
            "VALUES (?, ?, 'STOP_LOSS', 0, ?, ?, ?, ?, ?, ?);",
            (tier_id, price_level_set_id, stop_loss.get("price"),
             stop_loss.get("basis"), stop_loss.get("source"),
             stop_loss.get("sourceDate"), stop_loss.get("type"),
             stop_loss.get("status")),
        )
    if target_entry_price is not None:
        tier_id = f"{price_level_set_id}-TARGET_ENTRY"
        conn.execute(
            "INSERT INTO price_level_tier "
            "(tier_id, price_level_set_id, tier_kind, tier_number, price) "
            "VALUES (?, ?, 'TARGET_ENTRY', 0, ?);",
            (tier_id, price_level_set_id, target_entry_price),
        )

    conn.commit()
    return price_level_set_id


def get_price_levels(conn: sqlite3.Connection, investment_id: str) -> dict | None:
    conn.row_factory = sqlite3.Row
    set_row = conn.execute(
        "SELECT * FROM price_level_set WHERE investment_id = ?;", (investment_id,)
    ).fetchone()
    if not set_row:
        return None
    set_row = dict(set_row)
    tiers = conn.execute(
        "SELECT * FROM price_level_tier WHERE price_level_set_id = ? ORDER BY tier_number;",
        (set_row["price_level_set_id"],),
    ).fetchall()
    tiers = [dict(t) for t in tiers]
    return {
        "price_level_set": set_row,
        "buy_tiers": [t for t in tiers if t["tier_kind"] == "BUY_TIER"],
        "sell_tiers": [t for t in tiers if t["tier_kind"] == "SELL_TIER"],
        "stop_loss": next((t for t in tiers if t["tier_kind"] == "STOP_LOSS"), None),
        "target_entry": next((t for t in tiers if t["tier_kind"] == "TARGET_ENTRY"), None),
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_price_level_repository.py -v`
Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add investment_screener/backend/py_services/domain_model/price_level_repository.py \
        investment_screener/backend/tests/py_services/test_price_level_repository.py
git commit -m "feat: add price_level_repository (full-replace price_level_set/tier semantics)"
```

---

## Task 3: `investment_note_repository.py`

**Files:**
- Create: `investment_screener/backend/py_services/domain_model/investment_note_repository.py`
- Test: `investment_screener/backend/tests/py_services/test_investment_note_repository.py`

**Interfaces:**
- Consumes: `resolve_investment` (Wave 0).
- Produces:
  - `add_note(conn, investment_id: str, note_date: str, body: str, note_type: str = "AGENT_RATIONALE", source: str | None = None) -> str` — always inserts a new row (append-only history — this is the exact fix for the "un-queryable-history problem" the spec names, so it must never overwrite/replace like `price_level_repository`'s full-replace pattern).
  - `list_notes(conn, investment_id: str) -> list[dict]` — ordered by `note_date` ascending.
  - `get_latest_note(conn, investment_id: str) -> dict | None`

- [ ] **Step 1: Write the failing test**

```python
# investment_screener/backend/tests/py_services/test_investment_note_repository.py
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.investment_repository import resolve_investment  # noqa: E402
from domain_model.investment_note_repository import (  # noqa: E402
    add_note,
    list_notes,
    get_latest_note,
)


def _seed_investment(conn):
    return resolve_investment(conn, "IREN", asset_class="EQUITY", currency="USD")


def test_add_note_appends_does_not_replace(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    investment_id = _seed_investment(conn)
    add_note(conn, investment_id, "2026-01-01T00:00:00Z", "First rationale entry.")
    add_note(conn, investment_id, "2026-03-01T00:00:00Z", "Second rationale entry.")
    notes = list_notes(conn, investment_id)
    assert len(notes) == 2  # both preserved -- this is the whole point (queryable history)


def test_list_notes_ordered_by_date_ascending(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    investment_id = _seed_investment(conn)
    add_note(conn, investment_id, "2026-03-01T00:00:00Z", "Later entry.")
    add_note(conn, investment_id, "2026-01-01T00:00:00Z", "Earlier entry.")
    notes = list_notes(conn, investment_id)
    assert notes[0]["body"] == "Earlier entry."
    assert notes[1]["body"] == "Later entry."


def test_get_latest_note_returns_most_recent(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    investment_id = _seed_investment(conn)
    add_note(conn, investment_id, "2026-01-01T00:00:00Z", "Earlier entry.")
    add_note(conn, investment_id, "2026-03-01T00:00:00Z", "Later entry.")
    latest = get_latest_note(conn, investment_id)
    assert latest["body"] == "Later entry."


def test_get_latest_note_returns_none_when_no_notes(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    investment_id = _seed_investment(conn)
    assert get_latest_note(conn, investment_id) is None


def test_migrated_legacy_rationale_note_type(tmp_path):
    """Wave 2's migration script inserts the existing agentRationale string as one
    MIGRATED_LEGACY_RATIONALE-typed note per holding (not split by embedded date
    stamps -- that would require unreliable prose parsing, explicitly out of scope
    per the Wave 2 plan). This test locks in that the note_type is queryable/
    distinguishable from future real per-entry notes.
    """
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    investment_id = _seed_investment(conn)
    add_note(
        conn, investment_id, "2026-07-19T00:00:00Z",
        "DCF: INITIATE | FV $285 vs $421 price | -32.4% upside.",
        note_type="MIGRATED_LEGACY_RATIONALE", source="target-portfolio.json migration",
    )
    notes = list_notes(conn, investment_id)
    assert notes[0]["note_type"] == "MIGRATED_LEGACY_RATIONALE"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_investment_note_repository.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# investment_screener/backend/py_services/domain_model/investment_note_repository.py
"""All ``investment_note`` table reads and writes live here.

Append-only -- this table exists specifically to fix the "un-queryable history"
problem of agentRationale being a single hand-concatenated string (spec s2.3).
Never overwrite/replace an existing note row.
"""

import sqlite3
import uuid


def add_note(
    conn: sqlite3.Connection,
    investment_id: str,
    note_date: str,
    body: str,
    note_type: str = "AGENT_RATIONALE",
    source: str | None = None,
) -> str:
    note_id = f"{investment_id}-note-{uuid.uuid4().hex[:8]}"
    conn.execute(
        "INSERT INTO investment_note "
        "(note_id, investment_id, note_date, note_type, body, source) "
        "VALUES (?, ?, ?, ?, ?, ?);",
        (note_id, investment_id, note_date, note_type, body, source),
    )
    conn.commit()
    return note_id


def list_notes(conn: sqlite3.Connection, investment_id: str) -> list[dict]:
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(
        "SELECT * FROM investment_note WHERE investment_id = ? ORDER BY note_date ASC;",
        (investment_id,),
    )
    return [dict(row) for row in cursor.fetchall()]


def get_latest_note(conn: sqlite3.Connection, investment_id: str) -> dict | None:
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(
        "SELECT * FROM investment_note WHERE investment_id = ? "
        "ORDER BY note_date DESC LIMIT 1;",
        (investment_id,),
    )
    row = cursor.fetchone()
    return dict(row) if row else None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_investment_note_repository.py -v`
Expected: `5 passed`

- [ ] **Step 5: Commit**

```bash
git add investment_screener/backend/py_services/domain_model/investment_note_repository.py \
        investment_screener/backend/tests/py_services/test_investment_note_repository.py
git commit -m "feat: add investment_note_repository (append-only, fixes un-queryable rationale history)"
```

---

## Task 4: `alert_repository.py`

**Files:**
- Create: `investment_screener/backend/py_services/domain_model/alert_repository.py`
- Test: `investment_screener/backend/tests/py_services/test_alert_repository.py`

**Interfaces:**
- Consumes: `resolve_investment` (Wave 0).
- Produces:
  - `upsert_alert(conn, alert_id: str, investment_id: str | None, alert_type: str | None, message: str | None, price: float | None, condition_json: str | None, active: bool, resolution: str | None, created_at: str | None, last_fired_at: str | None, expiration_at: str | None, synced_at: str) -> str`
  - `list_alerts(conn, investment_id: str | None = None, active_only: bool = False) -> list[dict]`

- [ ] **Step 1: Write the failing test**

```python
# investment_screener/backend/tests/py_services/test_alert_repository.py
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.investment_repository import resolve_investment  # noqa: E402
from domain_model.alert_repository import upsert_alert, list_alerts  # noqa: E402


def _seed_investment(conn):
    return resolve_investment(conn, "NVDA", asset_class="EQUITY", currency="USD")


def test_upsert_alert_creates_and_is_idempotent(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    investment_id = _seed_investment(conn)
    id_1 = upsert_alert(
        conn, "alert-1", investment_id, "PRICE_ABOVE", "NVDA above 200", 200.0,
        None, True, None, "2026-07-01T00:00:00Z", None, None, "2026-07-19T00:00:00Z",
    )
    id_2 = upsert_alert(
        conn, "alert-1", investment_id, "PRICE_ABOVE", "NVDA above 200", 200.0,
        None, False, "TRIGGERED", "2026-07-01T00:00:00Z", "2026-07-19T00:00:00Z",
        None, "2026-07-19T01:00:00Z",
    )
    assert id_1 == id_2 == "alert-1"
    rows = list_alerts(conn, investment_id=investment_id)
    assert len(rows) == 1
    assert rows[0]["active"] == 0  # updated, not duplicated


def test_list_alerts_active_only_filter(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    investment_id = _seed_investment(conn)
    upsert_alert(conn, "a1", investment_id, "PRICE_ABOVE", "msg", 100.0, None,
                 True, None, "2026-07-01T00:00:00Z", None, None, "2026-07-19T00:00:00Z")
    upsert_alert(conn, "a2", investment_id, "PRICE_BELOW", "msg", 90.0, None,
                 False, "TRIGGERED", "2026-07-01T00:00:00Z", None, None,
                 "2026-07-19T00:00:00Z")
    active = list_alerts(conn, investment_id=investment_id, active_only=True)
    assert len(active) == 1
    assert active[0]["alert_id"] == "a1"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_alert_repository.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# investment_screener/backend/py_services/domain_model/alert_repository.py
"""All ``alert`` table reads and writes live here. TradingView is the upstream
authority; this table is the local synced mirror (spec s2.7 -- same "sync mirror"
reasoning as broker holdings, NOT a bare RETAIN_AS_EXTERNAL_CACHE exception)."""

import sqlite3


def upsert_alert(
    conn: sqlite3.Connection,
    alert_id: str,
    investment_id: str | None,
    alert_type: str | None,
    message: str | None,
    price: float | None,
    condition_json: str | None,
    active: bool,
    resolution: str | None,
    created_at: str | None,
    last_fired_at: str | None,
    expiration_at: str | None,
    synced_at: str,
) -> str:
    conn.execute(
        "INSERT INTO alert "
        "(alert_id, investment_id, alert_type, message, price, condition_json, "
        "active, resolution, created_at, last_fired_at, expiration_at, synced_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(alert_id) DO UPDATE SET "
        "investment_id=excluded.investment_id, alert_type=excluded.alert_type, "
        "message=excluded.message, price=excluded.price, "
        "condition_json=excluded.condition_json, active=excluded.active, "
        "resolution=excluded.resolution, last_fired_at=excluded.last_fired_at, "
        "expiration_at=excluded.expiration_at, synced_at=excluded.synced_at;",
        (alert_id, investment_id, alert_type, message, price, condition_json,
         int(active), resolution, created_at, last_fired_at, expiration_at, synced_at),
    )
    conn.commit()
    return alert_id


def list_alerts(
    conn: sqlite3.Connection,
    investment_id: str | None = None,
    active_only: bool = False,
) -> list[dict]:
    conn.row_factory = sqlite3.Row
    query = "SELECT * FROM alert WHERE 1=1"
    params: list = []
    if investment_id:
        query += " AND investment_id = ?"
        params.append(investment_id)
    if active_only:
        query += " AND active = 1"
    cursor = conn.execute(query, params)
    return [dict(row) for row in cursor.fetchall()]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_alert_repository.py -v`
Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
git add investment_screener/backend/py_services/domain_model/alert_repository.py \
        investment_screener/backend/tests/py_services/test_alert_repository.py
git commit -m "feat: add alert_repository (upsert_alert, list_alerts)"
```

---

## Task 5: Extend `investment_repository.py` with full-field update function

**Files:**
- Modify: `investment_screener/backend/py_services/domain_model/investment_repository.py` (Wave 0's file — add to it, don't replace `resolve_investment`/`get_investment`)
- Test: `investment_screener/backend/tests/py_services/test_investment_repository.py` (Wave 0's file — add new test functions)

**Interfaces:**
- Consumes: existing `resolve_investment`/`get_investment`.
- Produces:
  - `update_investment_fields(conn, investment_id: str, **fields) -> None` — accepts any subset of: `lifecycle_status`, `target_weight`, `target_action`, `standing_decision_type`, `standing_decision_reason`, `standing_decision_source`, `standing_decision_review`, `pillar_id`, `sub_strategy_id`, `thesis_for_inclusion`, `agent_rationale`, `is_watchlisted`, `watchlist_added_at`, `thesis_breaker_status`. Raises `ValueError` for any unknown field name (fail loud on a typo'd column name rather than silently no-op-ing — this table's `standing_decision_*` fields are the highest-risk item in this wave, per CLAUDE.md rule #8, so a silently-dropped update here must be impossible).

- [ ] **Step 1: Write the failing test (append to Wave 0's existing test file)**

```python
# append to investment_screener/backend/tests/py_services/test_investment_repository.py
from domain_model.investment_repository import update_investment_fields  # noqa: E402


def test_update_investment_fields_updates_only_specified_fields(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    investment_id = resolve_investment(conn, "AAPL", asset_class="EQUITY", currency="USD")
    update_investment_fields(
        conn, investment_id,
        lifecycle_status="active", target_weight=0.05, target_action="ACCUMULATE",
    )
    row = get_investment(conn, investment_id)
    assert row["lifecycle_status"] == "active"
    assert row["target_weight"] == 0.05
    assert row["target_action"] == "ACCUMULATE"
    assert row["symbol"] == "AAPL"  # untouched fields preserved


def test_update_investment_fields_preserves_standing_decision_on_partial_update(tmp_path):
    """The standingDecision anchor rule (CLAUDE.md #8) must never be silently
    clobbered by an update call that doesn't intend to touch it -- this is the
    single highest-risk item in this wave.
    """
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    investment_id = resolve_investment(conn, "PLTR", asset_class="EQUITY", currency="USD")
    update_investment_fields(
        conn, investment_id,
        standing_decision_type="HOLD",
        standing_decision_reason="DCF delta <15%, anchor holds",
        standing_decision_source="daily_brief.py",
    )
    # Unrelated later update -- must not touch standing_decision_* fields at all
    update_investment_fields(conn, investment_id, target_weight=0.03)
    row = get_investment(conn, investment_id)
    assert row["standing_decision_type"] == "HOLD"
    assert row["standing_decision_reason"] == "DCF delta <15%, anchor holds"
    assert row["target_weight"] == 0.03


def test_update_investment_fields_rejects_unknown_field(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    investment_id = resolve_investment(conn, "MSFT", asset_class="EQUITY", currency="USD")
    try:
        update_investment_fields(conn, investment_id, not_a_real_column="oops")
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "not_a_real_column" in str(exc)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_investment_repository.py -v`
Expected: FAIL with `ImportError: cannot import name 'update_investment_fields'`

- [ ] **Step 3: Write minimal implementation (append to existing file)**

```python
# append to investment_screener/backend/py_services/domain_model/investment_repository.py
_UPDATABLE_FIELDS = {
    "lifecycle_status", "target_weight", "target_action",
    "standing_decision_type", "standing_decision_reason",
    "standing_decision_source", "standing_decision_review",
    "pillar_id", "sub_strategy_id", "thesis_for_inclusion",
    "agent_rationale", "is_watchlisted", "watchlist_added_at",
    "thesis_breaker_status",
}


def update_investment_fields(conn: sqlite3.Connection, investment_id: str, **fields) -> None:
    """Update any subset of the named investment columns, leaving the rest untouched.

    Raises ValueError on an unrecognized field name -- fail loud rather than
    silently no-op, since a silently-dropped standing_decision_* update would
    violate CLAUDE.md rule #8 (the standingDecision anchor rule).
    """
    unknown = set(fields) - _UPDATABLE_FIELDS
    if unknown:
        raise ValueError(f"Unknown investment field(s): {sorted(unknown)}")
    if not fields:
        return
    set_clause = ", ".join(f"{key} = ?" for key in fields)
    params = list(fields.values()) + [investment_id]
    conn.execute(
        f"UPDATE investment SET {set_clause}, updated_at = ? WHERE investment_id = ?;"
        if False else f"UPDATE investment SET {set_clause} WHERE investment_id = ?;",
        params,
    )
    conn.commit()
```

(The dead `if False` branch above is a placeholder reminder to decide `updated_at` handling in
Step 3 during actual implementation — replace with a real decision: append `updated_at =
datetime('now')` to every update, matching `resolve_investment`'s existing `updated_at` population
pattern. Do not leave the `if False` in the merged code; resolve it before committing.)

- [ ] **Step 4: Resolve the `updated_at` handling before running tests**

Fix the implementation to always set `updated_at` on every call (use the same
`datetime.now(timezone.utc).isoformat()` pattern already imported and used by `resolve_investment`
in this same file):

```python
def update_investment_fields(conn: sqlite3.Connection, investment_id: str, **fields) -> None:
    unknown = set(fields) - _UPDATABLE_FIELDS
    if unknown:
        raise ValueError(f"Unknown investment field(s): {sorted(unknown)}")
    if not fields:
        return
    fields = {**fields, "updated_at": datetime.now(timezone.utc).isoformat()}
    set_clause = ", ".join(f"{key} = ?" for key in fields)
    params = list(fields.values()) + [investment_id]
    conn.execute(
        f"UPDATE investment SET {set_clause} WHERE investment_id = ?;", params,
    )
    conn.commit()
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_investment_repository.py -v`
Expected: all pass (3 original + 3 new = 6)

- [ ] **Step 6: Commit**

```bash
git add investment_screener/backend/py_services/domain_model/investment_repository.py \
        investment_screener/backend/tests/py_services/test_investment_repository.py
git commit -m "feat: add update_investment_fields (partial-update, standing-decision-safe)"
```

---

## Task 6: Migration script — dry-run mode (real data, no writes)

**Files:**
- Create: `investment_screener/backend/py_services/domain_model/migrate_target_portfolio_to_sqlite.py`
- Test: `investment_screener/backend/tests/py_services/test_migrate_target_portfolio_to_sqlite.py`

**Interfaces:**
- Consumes: `resolve_investment`/`update_investment_fields` (Task 5), `resolve_pillar`/
  `resolve_sub_strategy` (Task 1), `replace_price_levels` (Task 2), `add_note` (Task 3),
  `upsert_alert` (Task 4).
- Produces:
  - `build_dry_run_report(target_portfolio_path: str, watchlist_path: str, alerts_path: str, breaker_state_path: str) -> dict` — parses all four real source files, returns a structured report (counts per table, any holdings with unexpected/missing fields, any parse warnings) without touching SQLite at all.
  - CLI: `python3 migrate_target_portfolio_to_sqlite.py --dry-run` (default) prints the report; `--write` (requires `--dry-run` to have been run and the report reviewed — see Task 7) performs the real migration.

- [ ] **Step 1: Read the real current `target-portfolio.json` and `watchlist.json` structure fully before writing the parser**

Run: `python3 -c "import json; d = json.load(open('investment_screener/backend/data/theses/target-portfolio.json')); print(list(d.keys())); print(json.dumps(d['holdings'][0], indent=2))"`
Run: `python3 -c "import json; d = json.load(open('investment_screener/backend/data/watchlist.json')); print(type(d)); print(json.dumps(d[:2] if isinstance(d, list) else d, indent=2))"`

Confirm the exact real top-level shape (holdings array, pillars structure, globalSettings) and
watchlist.json's real shape before writing `build_dry_run_report` — do not assume the shape from
this plan's earlier field-shape notes without this direct re-check, since those notes came from a
subagent's summary, not a first-hand read in this task's context.

- [ ] **Step 2: Write the failing test using tmp_path fixture files (not real data yet)**

```python
# investment_screener/backend/tests/py_services/test_migrate_target_portfolio_to_sqlite.py
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from domain_model.migrate_target_portfolio_to_sqlite import (  # noqa: E402
    build_dry_run_report,
)


def _write_fixture(tmp_path):
    target = {
        "holdings": [
            {
                "ticker": "AAPL", "role": "active", "targetWeight": 0.05,
                "action": "ACCUMULATE", "pillar": "AI_INFRA",
                "subStrategy": "AI_COMPUTE",
                "standingDecision": {
                    "type": "HOLD", "reason": "DCF delta <15%",
                    "source": "daily_brief.py", "lastReviewed": "2026-07-01",
                },
                "agentRationale": "DCF: INITIATE | FV $285 vs $421 price.",
                "priceLevels": {
                    "schemaVersion": "1.0", "lastUpdated": "2026-07-01",
                    "lastUpdatedBy": "update_price_levels.py", "note": None,
                    "buyTiers": [{"tier": 1, "price": 150.0, "action": "BUY"}],
                    "sellTiers": [], "stopLoss": None,
                },
                "targetEntryPrice": None,
                "thesisBreakerStatus": None,
            },
        ],
        "pillars": [{"id": "AI_INFRA", "name": "AI Infrastructure", "targetWeight": 0.35}],
    }
    watchlist = [{"ticker": "DRAM", "addedAt": "2026-06-01"}]
    target_path = tmp_path / "target-portfolio.json"
    watchlist_path = tmp_path / "watchlist.json"
    alerts_path = tmp_path / "tradingview_alerts_actual.json"
    breaker_path = tmp_path / "thesis_breaker_state.json"
    target_path.write_text(json.dumps(target))
    watchlist_path.write_text(json.dumps(watchlist))
    alerts_path.write_text(json.dumps([]))
    breaker_path.write_text(json.dumps({}))
    return str(target_path), str(watchlist_path), str(alerts_path), str(breaker_path)


def test_build_dry_run_report_counts_holdings_and_pillars(tmp_path):
    paths = _write_fixture(tmp_path)
    report = build_dry_run_report(*paths)
    assert report["holdings_count"] == 1
    assert report["pillars_count"] == 1
    assert report["watchlist_count"] == 1
    assert report["holdings_with_price_levels"] == 1
    assert report["holdings_with_agent_rationale"] == 1
    assert report["warnings"] == []


def test_build_dry_run_report_flags_missing_ticker_as_warning(tmp_path):
    target_path = tmp_path / "target-portfolio.json"
    target_path.write_text(json.dumps({"holdings": [{"role": "active"}], "pillars": []}))
    watchlist_path = tmp_path / "watchlist.json"
    watchlist_path.write_text(json.dumps([]))
    alerts_path = tmp_path / "tradingview_alerts_actual.json"
    alerts_path.write_text(json.dumps([]))
    breaker_path = tmp_path / "thesis_breaker_state.json"
    breaker_path.write_text(json.dumps({}))
    report = build_dry_run_report(
        str(target_path), str(watchlist_path), str(alerts_path), str(breaker_path)
    )
    assert len(report["warnings"]) == 1
    assert "missing ticker" in report["warnings"][0].lower()


def test_build_dry_run_report_does_not_touch_any_sqlite_file(tmp_path):
    """A dry run must be pure -- no domain_model.sqlite file created as a side effect."""
    paths = _write_fixture(tmp_path)
    build_dry_run_report(*paths)
    assert not (tmp_path / "domain_model.sqlite").exists()
    assert not any(tmp_path.glob("*.sqlite"))
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_migrate_target_portfolio_to_sqlite.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 4: Write minimal implementation (dry-run portion only)**

```python
# investment_screener/backend/py_services/domain_model/migrate_target_portfolio_to_sqlite.py
"""Dry-run + real migration of target-portfolio.json/watchlist.json/
tradingview_alerts_actual.json/thesis_breaker_state.json into the v3.2 domain model.

Non-negotiable per this migration's global constraints: --write must never run
without a --dry-run report first being reviewed and explicitly approved by the
user (tied to a real data-loss incident from before this corrective effort began).
"""

import argparse
import json


def _load(path: str):
    with open(path) as f:
        return json.load(f)


def build_dry_run_report(
    target_portfolio_path: str,
    watchlist_path: str,
    alerts_path: str,
    breaker_state_path: str,
) -> dict:
    target = _load(target_portfolio_path)
    watchlist = _load(watchlist_path)
    alerts = _load(alerts_path)
    breaker_state = _load(breaker_state_path)

    holdings = target.get("holdings", [])
    pillars = target.get("pillars", [])
    warnings = []
    holdings_with_price_levels = 0
    holdings_with_agent_rationale = 0
    holdings_with_target_entry = 0

    for i, holding in enumerate(holdings):
        ticker = holding.get("ticker")
        if not ticker:
            warnings.append(f"holdings[{i}]: missing ticker field")
            continue
        if holding.get("priceLevels"):
            holdings_with_price_levels += 1
        if holding.get("agentRationale"):
            holdings_with_agent_rationale += 1
        if holding.get("targetEntryPrice") is not None:
            holdings_with_target_entry += 1

    return {
        "holdings_count": len(holdings),
        "pillars_count": len(pillars),
        "watchlist_count": len(watchlist) if isinstance(watchlist, list) else 0,
        "alerts_count": len(alerts) if isinstance(alerts, list) else 0,
        "holdings_with_price_levels": holdings_with_price_levels,
        "holdings_with_agent_rationale": holdings_with_agent_rationale,
        "holdings_with_target_entry": holdings_with_target_entry,
        "thesis_breaker_state_keys": list(breaker_state.keys()),
        "warnings": warnings,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-portfolio",
                         default="investment_screener/backend/data/theses/target-portfolio.json")
    parser.add_argument("--watchlist",
                         default="investment_screener/backend/data/watchlist.json")
    parser.add_argument("--alerts",
                         default="investment_screener/backend/data/tradingview_alerts_actual.json")
    parser.add_argument("--breaker-state",
                         default="investment_screener/backend/data/thesis_breaker_state.json")
    parser.add_argument("--db-path",
                         default="investment_screener/backend/data/domain_model.sqlite")
    parser.add_argument("--write", action="store_true",
                         help="Perform the real migration. Requires reviewing a --dry-run "
                              "report first -- never run this without explicit user sign-off.")
    args = parser.parse_args()

    report = build_dry_run_report(
        args.target_portfolio, args.watchlist, args.alerts, args.breaker_state
    )
    print(json.dumps(report, indent=2))

    if args.write:
        raise NotImplementedError(
            "Real --write migration is implemented in Task 7 of the Wave 2 plan -- "
            "not yet wired here. This stub exists so --dry-run (the safe default) "
            "works standalone without a half-built --write path being reachable."
        )


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_migrate_target_portfolio_to_sqlite.py -v`
Expected: `3 passed`

- [ ] **Step 6: Run the dry-run CLI against the real data files (read-only, safe)**

Run: `cd investment_screener/backend && python3 py_services/domain_model/migrate_target_portfolio_to_sqlite.py --dry-run`
Expected: a real JSON report printed to stdout, no `.sqlite` file created or modified. Read the
output — if `warnings` is non-empty, investigate each one before proceeding to Task 7 (a warning
here means the real file has a shape this parser didn't anticipate, which is exactly the kind of
gap Wave 1 found late; better to find it now).

- [ ] **Step 7: Commit**

```bash
git add investment_screener/backend/py_services/domain_model/migrate_target_portfolio_to_sqlite.py \
        investment_screener/backend/tests/py_services/test_migrate_target_portfolio_to_sqlite.py
git commit -m "feat: add Wave 2 migration script (dry-run mode only, real --write gated to Task 7)"
```

---

## Task 7: Migration script — real `--write` mode + hard approval gate

**Files:**
- Modify: `investment_screener/backend/py_services/domain_model/migrate_target_portfolio_to_sqlite.py`
- Test: `investment_screener/backend/tests/py_services/test_migrate_target_portfolio_to_sqlite.py` (add write-mode tests)

**Interfaces:**
- Consumes: everything from Tasks 1-6.
- Produces: `execute_migration(conn, target_portfolio_path, watchlist_path, alerts_path, breaker_state_path) -> dict` — performs the real writes, returns a summary dict (rows written per table) for the caller to log/verify.

- [ ] **Step 1: Write the failing test (tmp_path fixtures + tmp_path SQLite — still not real data)**

```python
# append to investment_screener/backend/tests/py_services/test_migrate_target_portfolio_to_sqlite.py
from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.investment_repository import get_investment  # noqa: E402
from domain_model.price_level_repository import get_price_levels  # noqa: E402
from domain_model.investment_note_repository import list_notes  # noqa: E402
from domain_model.migrate_target_portfolio_to_sqlite import execute_migration  # noqa: E402


def test_execute_migration_writes_full_investment_row(tmp_path):
    paths = _write_fixture(tmp_path)
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    summary = execute_migration(conn, *paths)
    assert summary["investments_updated"] == 1

    row = get_investment(conn, "AAPL")
    assert row is not None
    assert row["target_weight"] == 0.05
    assert row["target_action"] == "ACCUMULATE"
    assert row["standing_decision_type"] == "HOLD"
    assert row["pillar_id"] == "AI_INFRA"

    levels = get_price_levels(conn, "AAPL")
    assert levels is not None
    assert len(levels["buy_tiers"]) == 1

    notes = list_notes(conn, "AAPL")
    assert len(notes) == 1
    assert notes[0]["note_type"] == "MIGRATED_LEGACY_RATIONALE"


def test_execute_migration_sets_watchlist_flag_independent_of_role(tmp_path):
    """watchlist.json's population and role='watchlist' are two different questions
    (spec s2.1 -- DRAM disagrees on role vs. action in real data, only ~20 of ~80/33
    overlap). This test locks in that watchlist membership is driven by watchlist.json
    membership, not inferred from role/action.
    """
    paths = _write_fixture(tmp_path)
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    execute_migration(conn, *paths)
    dram_row = get_investment(conn, "DRAM")
    assert dram_row is not None
    assert dram_row["is_watchlisted"] == 1


def test_execute_migration_is_idempotent_on_rerun(tmp_path):
    paths = _write_fixture(tmp_path)
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    execute_migration(conn, *paths)
    execute_migration(conn, *paths)  # must not duplicate notes/price levels
    notes = list_notes(conn, "AAPL")
    assert len(notes) == 1  # re-running does not append a second identical note
    levels = get_price_levels(conn, "AAPL")
    assert len(levels["buy_tiers"]) == 1  # full-replace, not duplicated
```

Note on the idempotent-notes requirement: since `add_note` is append-only by design (Task 3), the
migration script itself must guard against re-inserting an identical migrated note on rerun — add
a check inside `execute_migration` (not inside `investment_note_repository.py`, which must stay a
dumb append-only primitive) that skips inserting a `MIGRATED_LEGACY_RATIONALE` note if one with the
exact same `body` already exists for that investment.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_migrate_target_portfolio_to_sqlite.py -v`
Expected: FAIL with `ImportError: cannot import name 'execute_migration'`

- [ ] **Step 3: Write minimal implementation (append to the migration script)**

```python
# append to investment_screener/backend/py_services/domain_model/migrate_target_portfolio_to_sqlite.py
from investment_repository import resolve_investment, update_investment_fields
from pillar_repository import resolve_pillar, resolve_sub_strategy
from price_level_repository import replace_price_levels
from investment_note_repository import add_note, list_notes


def execute_migration(
    conn,
    target_portfolio_path: str,
    watchlist_path: str,
    alerts_path: str,
    breaker_state_path: str,
) -> dict:
    target = _load(target_portfolio_path)
    watchlist = _load(watchlist_path)
    alerts = _load(alerts_path)
    breaker_state = _load(breaker_state_path)

    for pillar in target.get("pillars", []):
        resolve_pillar(conn, pillar["id"], pillar["name"], pillar.get("targetWeight"))

    watchlist_tickers = {
        item["ticker"] for item in watchlist if isinstance(item, dict) and item.get("ticker")
    }
    watchlist_added_at = {
        item["ticker"]: item.get("addedAt")
        for item in watchlist if isinstance(item, dict) and item.get("ticker")
    }

    investments_updated = 0
    for holding in target.get("holdings", []):
        ticker = holding.get("ticker")
        if not ticker:
            continue
        investment_id = resolve_investment(conn, ticker, asset_class="EQUITY", currency="USD")

        standing = holding.get("standingDecision") or {}
        fields = {
            "lifecycle_status": holding.get("role"),
            "target_weight": holding.get("targetWeight"),
            "target_action": holding.get("action"),
            "standing_decision_type": standing.get("type"),
            "standing_decision_reason": standing.get("reason"),
            "standing_decision_source": standing.get("source"),
            "standing_decision_review": standing.get("lastReviewed"),
            "pillar_id": holding.get("pillar"),
            "sub_strategy_id": holding.get("subStrategy"),
            "thesis_for_inclusion": holding.get("thesisForInclusion"),
            "agent_rationale": holding.get("agentRationale"),
            "is_watchlisted": ticker in watchlist_tickers,
            "watchlist_added_at": watchlist_added_at.get(ticker),
            "thesis_breaker_status": holding.get("thesisBreakerStatus"),
        }
        fields = {k: v for k, v in fields.items() if v is not None}
        update_investment_fields(conn, investment_id, **fields)
        investments_updated += 1

        price_levels = holding.get("priceLevels")
        target_entry = holding.get("targetEntryPrice")
        if price_levels or target_entry is not None:
            pl = price_levels or {}
            replace_price_levels(
                conn, investment_id,
                schema_version=pl.get("schemaVersion"), last_updated=pl.get("lastUpdated"),
                last_updated_by=pl.get("lastUpdatedBy"), note=pl.get("note"),
                buy_tiers=pl.get("buyTiers", []), sell_tiers=pl.get("sellTiers", []),
                stop_loss=pl.get("stopLoss"), target_entry_price=target_entry,
            )

        rationale = holding.get("agentRationale")
        if rationale:
            existing_notes = list_notes(conn, investment_id)
            already_migrated = any(
                n["body"] == rationale and n["note_type"] == "MIGRATED_LEGACY_RATIONALE"
                for n in existing_notes
            )
            if not already_migrated:
                add_note(
                    conn, investment_id,
                    note_date=holding.get("lastUpdated") or "2026-07-19T00:00:00Z",
                    body=rationale, note_type="MIGRATED_LEGACY_RATIONALE",
                    source="target-portfolio.json migration (Wave 2)",
                )

    # Tickers that are watchlist-only (no holdings entry at all) still need a
    # resolvable investment row so is_watchlisted can be set on them too.
    holdings_tickers = {h.get("ticker") for h in target.get("holdings", []) if h.get("ticker")}
    for ticker in watchlist_tickers - holdings_tickers:
        investment_id = resolve_investment(conn, ticker, asset_class="EQUITY", currency="USD")
        update_investment_fields(
            conn, investment_id, is_watchlisted=True,
            watchlist_added_at=watchlist_added_at.get(ticker),
        )

    return {
        "investments_updated": investments_updated,
        "pillars_updated": len(target.get("pillars", [])),
        "watchlist_only_tickers_added": len(watchlist_tickers - holdings_tickers),
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_migrate_target_portfolio_to_sqlite.py -v`
Expected: all pass (3 dry-run + 3 write-mode = 6)

- [ ] **Step 5: Wire `--write` in `main()` to call `execute_migration` against the real DB**

Replace the `raise NotImplementedError(...)` block in `main()` (Task 6, Step 4) with:

```python
    if args.write:
        conn = initialize_db(args.db_path)
        summary = execute_migration(
            conn, args.target_portfolio, args.watchlist, args.alerts, args.breaker_state
        )
        print("--- WRITE SUMMARY ---")
        print(json.dumps(summary, indent=2))
```

Add `from db_client import initialize_db` to the top-level imports.

- [ ] **Step 6: STOP — hard approval gate before running `--write` against real data**

Do not run `--write` yet. Run `--dry-run` one more time against the real current files (same
command as Task 6 Step 6) and present the report to the user, alongside this summary of what
`--write` will do:

- Update all real `investment` rows (currently 82, identity-only from Wave 0) with full fields
  from `target-portfolio.json`.
- Create `price_level_set`/`price_level_tier` rows for holdings with `priceLevels`/
  `targetEntryPrice` populated (~8-10 real holdings per the investigation).
- Create one `investment_note` row per holding with `agentRationale` populated (~73 real holdings).
- Set `is_watchlisted`/`watchlist_added_at` for all real `watchlist.json` tickers (~80 real
  tickers), creating new minimal `investment` rows for any watchlist-only ticker not already an
  active holding.
- **This does not touch `target-portfolio.json`/`watchlist.json`/`tradingview_alerts_actual.json`/
  `thesis_breaker_state.json` at all** — read-only against the source files, write-only against
  `domain_model.sqlite`. No data loss is possible at this step; the risk is a wrong/incomplete
  SQLite write, not JSON corruption.

**Explicit user sign-off is required before proceeding to Step 7.** This mirrors Wave 1's Task 3/4
gate exactly.

- [ ] **Step 7: Run `--write` against real data (only after Step 6's sign-off)**

Run: `cd investment_screener/backend && python3 py_services/domain_model/migrate_target_portfolio_to_sqlite.py --write`
Expected: real write summary printed; verify row counts directly afterward:

Run: `python3 -c "
import sqlite3
conn = sqlite3.connect('investment_screener/backend/data/domain_model.sqlite')
for table in ['investment', 'price_level_set', 'price_level_tier', 'investment_note']:
    print(table, conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0])
"`

Confirm the counts are plausible against the dry-run report's numbers (not just nonzero) before
proceeding — a mismatch here is a Hard-Stop Condition per the spec (row-count delta unexplained).

- [ ] **Step 8: Commit**

```bash
git add investment_screener/backend/py_services/domain_model/migrate_target_portfolio_to_sqlite.py \
        investment_screener/backend/tests/py_services/test_migrate_target_portfolio_to_sqlite.py
git commit -m "feat: execute real Wave 2 migration (target-portfolio.json + watchlist.json -> SQLite)"
```

---

## Task 8: TradingView alerts + thesis breaker state migration (rides with the same script)

**Files:**
- Modify: `investment_screener/backend/py_services/domain_model/migrate_target_portfolio_to_sqlite.py`
- Test: `investment_screener/backend/tests/py_services/test_migrate_target_portfolio_to_sqlite.py` (add)

**Interfaces:**
- Consumes: `upsert_alert` (Task 4), `update_investment_fields` (Task 5).
- Produces: extends `execute_migration` to also migrate `alerts` (already loaded in Task 7's
  implementation but not yet written to the `alert` table) and `breaker_state` (already loaded but
  not yet written to `investment.thesis_breaker_status`).

**Before writing this task's code:** read the real current `tradingview_alerts_actual.json` (203
entries) and `thesis_breaker_state.json` (4 lines/68 bytes) structure directly —

Run: `python3 -c "import json; d = json.load(open('investment_screener/backend/data/tradingview_alerts_actual.json')); print(len(d)); print(json.dumps(d[0], indent=2))"`
Run: `cat investment_screener/backend/data/thesis_breaker_state.json`

— do not assume the shape; write the parsing code in Step 3 below against the real confirmed shape
(the field names in the sample code below are placeholders inferred from the `alert` table schema
and must be corrected to match whatever the real JSON keys turn out to be).

- [ ] **Step 1: Write the failing test using representative fixture data matching the real shape confirmed above**

(Concrete test code to be written at execution time, using the real field names confirmed by the
Step 0 read above — this is intentionally not pre-scripted with guessed field names, per this
plan's own discipline about not inventing shapes it hasn't verified. Follow the exact test
structure/naming convention used in Task 7's tests: one test for "creates the row," one for
"idempotent on rerun," one for a real-data edge case found during the read.)

- [ ] **Step 2: Run test to verify it fails**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_migrate_target_portfolio_to_sqlite.py -v`
Expected: FAIL (new test references not-yet-added alert/breaker migration logic)

- [ ] **Step 3: Extend `execute_migration` to write alerts and thesis breaker status**

Add to `execute_migration` (after the holdings loop, using the real confirmed field names from
Step 0's direct read, not the placeholder names below):

```python
    alerts_migrated = 0
    for alert_entry in alerts:
        ticker = alert_entry.get("ticker") or alert_entry.get("symbol")
        investment_id = resolve_investment(conn, ticker, asset_class="EQUITY", currency="USD") \
            if ticker else None
        upsert_alert(
            conn,
            alert_id=alert_entry.get("id") or f"tv-{alerts_migrated}",
            investment_id=investment_id,
            alert_type=alert_entry.get("type"),
            message=alert_entry.get("message"),
            price=alert_entry.get("price"),
            condition_json=json.dumps(alert_entry.get("condition")) if alert_entry.get("condition") else None,
            active=alert_entry.get("active", True),
            resolution=alert_entry.get("resolution"),
            created_at=alert_entry.get("createdAt"),
            last_fired_at=alert_entry.get("lastFiredAt"),
            expiration_at=alert_entry.get("expirationAt"),
            synced_at="2026-07-19T00:00:00Z",  # replace with real migration-run timestamp
        )
        alerts_migrated += 1

    breaker_updates = 0
    for ticker, status in breaker_state.items():
        existing = get_investment(conn, ticker)
        if existing:
            update_investment_fields(conn, ticker, thesis_breaker_status=status)
            breaker_updates += 1
```

(This is a starting shape, not final code — Step 0's real-data read may reveal the alerts file is
keyed differently, e.g. an object keyed by ticker rather than a flat list; adjust the loop
structure to match reality, and add an import for `upsert_alert`/`get_investment` at the top of the
file.)

- [ ] **Step 4: Run test to verify it passes**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_migrate_target_portfolio_to_sqlite.py -v`
Expected: all pass

- [ ] **Step 5: Re-run `--dry-run`, present updated report, get sign-off, then re-run `--write` against real data**

Same gate discipline as Task 7 Step 6-7 — alerts (203 real entries) and breaker state are real data
too, even though small.

- [ ] **Step 6: Commit**

```bash
git add investment_screener/backend/py_services/domain_model/migrate_target_portfolio_to_sqlite.py \
        investment_screener/backend/tests/py_services/test_migrate_target_portfolio_to_sqlite.py
git commit -m "feat: extend Wave 2 migration to alerts + thesis breaker state"
```

---

## Tasks 9-13: Producer/Consumer Cutover (structural pattern, not pre-scripted line-by-line)

**Why these are not pre-scripted with exact diffs:** per this migration's established discipline
(Wave 1's Task 7, and this document's own kickoff-prompt template), consumer/producer rewiring
requires reading each file's real current code at execution time — writing exact code now would
mean guessing at current function signatures and control flow not yet freshly re-read line-by-line
in this planning pass. What follows is the real file list (confirmed by investigation, not
estimated), the available repository functions each file should call, and the required sub-task
structure — mirroring Wave 1's 7A/7B/7C split.

**Common instruction for every sub-task below:** before editing each file, read its current real
code in full. Confirm the exact current read (`json.load`) or write (`locked_write_json`-equivalent)
call site, its exact variable names, and how the surrounding function uses the parsed data — then
replace the JSON read/write with the equivalent domain-model repository call(s) listed in the
"Available repository functions" block, preserving all existing behavior/semantics exactly unless a
bug is found (in which case, fix it with evidence, same as Wave 1's 6 real bugs, and note it in the
Wave 2 exit report rather than silently smoothing it over). Each sub-task ends with: run that file's
existing tests (or add one if none exist covering this behavior), confirm no regression, commit.

### Task 9 (sub-wave 2A): Producer cutover — 11 real producers

**Files (confirmed real, from investigation):**
1. `investment_screener/backend/src/services/BrokerSyncService.ts` — writes `target-portfolio.json` holdings sync fields.
2. `investment_screener/backend/py_services/market_regime.py`
3. `investment_screener/backend/py_services/risk_engine.py`
4. `investment_screener/backend/py_services/rebalancer.py`
5. `investment_screener/backend/py_services/backtest_harness.py` (already touched in Task 0 for the stale-path bug — re-verify its normal, non-historical write path here too)
6. `investment_screener/backend/py_services/thesis_breakers.py` — also the sole producer of `thesis_breaker_state.json`, folds into `update_investment_fields(thesis_breaker_status=...)`.
7. `plugins/tradingview/scripts/ta_sweep_batch.py`
8. `plugins/portfolio-advisor/scripts/daily_brief.py`
9. `plugins/portfolio-advisor/scripts/update_thesis.py` — also the source of new `agentRationale` entries; must call `add_note(...)` (Task 3) for each new entry going forward, not `update_investment_fields(agent_rationale=...)` alone, so future rationale updates are queryable history from this point on, not just the one-time migrated blob.
10. `investment_screener/backend/py_services/validate_weights.py`
11. `plugins/portfolio-advisor/scripts/update_price_levels.py` — must call `replace_price_levels(...)` (Task 2), preserving its existing full-object-rewrite semantics exactly.
12. `investment_screener/backend/src/services/WatchlistService.ts` (write side) — must call the TS equivalent of `update_investment_fields(is_watchlisted=True, watchlist_added_at=...)` — confirm whether a TS-side repository wrapper is needed (mirroring `ProjectionRepository.ts`'s Wave 1 pattern) or whether Python-side-only repositories suffice with TS calling through a thin API; read `ProjectionRepository.ts` first to decide, don't invent a new pattern.

**Available repository functions:** `investment_repository.resolve_investment`/
`update_investment_fields`, `pillar_repository.resolve_pillar`/`resolve_sub_strategy`,
`price_level_repository.replace_price_levels`, `investment_note_repository.add_note`,
`alert_repository.upsert_alert`.

- [ ] Sub-task 9.1: rewire the 5 Python producers with no TS dependency (`market_regime.py`,
  `risk_engine.py`, `rebalancer.py`, `validate_weights.py`, `backtest_harness.py`'s live-write path).
- [ ] Sub-task 9.2: rewire `thesis_breakers.py`, `ta_sweep_batch.py`, `daily_brief.py`.
- [ ] Sub-task 9.3: rewire `update_thesis.py` (agentRationale → `add_note`) and
  `update_price_levels.py` (→ `replace_price_levels`) — highest data-shape risk in this sub-wave,
  test against real holdings with existing `priceLevels`/`agentRationale` populated.
- [ ] Sub-task 9.4: rewire `BrokerSyncService.ts` and `WatchlistService.ts` (write side) — TS-side,
  read `ProjectionRepository.ts` first for the established Wave 1 pattern.
- [ ] After each sub-task: run that domain's affected test suite, commit.

### Task 10 (sub-wave 2B): Core consumer cutover — 19 real consumers (18 original + `portfolio_action.py`)

**Files (confirmed real, from investigation):** `docs.ts`, `stock.ts`, `screener.ts`, `theses.ts`
(via `ThesisService.ts`), `compute_conviction_scores.py`, `order_risk_gates.py` (also fixed for the
stale-path bug in Task 0 — verify its normal read path here too), `lock_and_normalize_targets.py`,
`earnings_expectations.py`, `verify_thesis_sync.py`, `harvest_predictions.py`, `tv_create_alerts.py`,
`generate_review.py`, `verify_refresh.py`, `generate_portfolio_blueprint.py`, `generate_reports.py`,
`scan_opportunities.py`, `weekly_review.py`, `portfolio_action.py` (canonical source only — 6
symlinked skill copies must resolve correctly afterward, do not edit the symlink targets
themselves).

**Available repository functions:** `investment_repository.get_investment`, plus read helpers to
add if missing (e.g. `list_investments(conn, lifecycle_status=None, pillar_id=None) -> list[dict]`
for bulk-read consumers like `scan_opportunities.py`/`weekly_review.py` — add this function to
`investment_repository.py` as a small preliminary step within this task if no existing function
covers a given consumer's real query pattern; do not force every consumer through single-row
`get_investment` if it currently iterates the whole holdings array).

- [ ] Sub-task 10.1: add any missing bulk-read repository function(s) discovered while reading the
  first few consumers (e.g. `list_investments`), with its own test, before rewiring consumers that
  need it.
- [ ] Sub-task 10.2: rewire the 5 Python "simple single-ticker or full-scan read" consumers
  (`compute_conviction_scores.py`, `order_risk_gates.py`, `lock_and_normalize_targets.py`,
  `earnings_expectations.py`, `verify_thesis_sync.py`).
- [ ] Sub-task 10.3: rewire `harvest_predictions.py`, `tv_create_alerts.py`, `generate_review.py`,
  `verify_refresh.py`, `generate_portfolio_blueprint.py` (this one has history — Wave 1 found it
  missing from the original inventory and it had a pre-existing latent bug; read it especially
  carefully).
- [ ] Sub-task 10.4: rewire `generate_reports.py`, `scan_opportunities.py`, `weekly_review.py`,
  `portfolio_action.py` (canonical source; after editing, verify all 6 symlinked skill copies still
  resolve by running `ls -la` on each symlink target and confirming they point at the now-updated
  canonical file, plus running each skill's own test suite if one exists).
- [ ] Sub-task 10.5: rewire `docs.ts`, `stock.ts`, `screener.ts`, `theses.ts`/`ThesisService.ts` —
  TS-side, confirm the `standingDecision` read path specifically (highest-risk item in this wave)
  with a dedicated test asserting the API response's standing-decision fields match what
  `get_investment` returns, byte-for-byte against a known real ticker.
- [ ] After each sub-task: run affected tests, commit.

### Task 11 (sub-wave 2C): Watchlist-specific consumer cutover — 6 files

**Files:** `overnight_gaps.py`, `WatchlistService.ts` (read side), `paths.ts` (remove the
`WATCHLIST_FILE` constant once nothing references it — confirm via grep before removing),
`weekly_review.py` (already touched in Task 10.4 for its target-portfolio read — confirm its
separate watchlist read here too), `watchlist_manager.py`, `tradingview-cdp/cli.js`.

**Available repository functions:** `investment_repository.list_investments(conn,
is_watchlisted=True)` (extend the bulk-read function from Task 10.1 to support this filter, or add
a dedicated `list_watchlisted_investments(conn) -> list[dict]` if the query shape differs enough
to warrant its own function — decide based on the real usage pattern in these 6 files, read them
first).

- [ ] Sub-task 11.1: rewire `overnight_gaps.py`, `watchlist_manager.py`.
- [ ] Sub-task 11.2: rewire `WatchlistService.ts` (read side), `paths.ts`.
- [ ] Sub-task 11.3: rewire `weekly_review.py`'s watchlist-specific read, `tradingview-cdp/cli.js`.
- [ ] After each sub-task: run affected tests, commit.

### Task 12 (sub-wave 2D): Alerts + thesis breaker consumer cutover

**Files:** `plugins/tradingview/scripts/tv_list_alerts.py` (both copies — canonical +
`plugins/tradingview/skills/alert-list/scripts/` copy; confirm symlink vs. real duplicate before
deciding whether to edit one canonical source or both — per investigation this needs direct
confirmation, do not assume symlinked without checking), thesis breaker consumers:
`order_risk_gates.py` (already touched Task 10.2 for target-portfolio read — confirm its separate
`thesis_breaker_state.json` read here too), `rebalancer.py` (already touched Task 9.1 — confirm its
consumer-side read here too), `harvest_predictions.py` (already touched Task 10.3), `risk_officer.py`.

**Available repository functions:** `alert_repository.list_alerts`,
`investment_repository.get_investment` (for `thesis_breaker_status`).

- [ ] Sub-task 12.1: confirm whether the two `tv_list_alerts.py` copies are a real symlink or a
  real duplicate (`ls -la` both paths, compare inode/`readlink`); rewire the canonical one only if
  symlinked, both if genuinely duplicated (flag this as a separate finding if duplicated — that
  itself may be undocumented drift worth a note in the exit report).
- [ ] Sub-task 12.2: rewire `risk_officer.py`'s thesis-breaker read; confirm the other 3
  consumers' thesis-breaker-specific read paths (separate from their target-portfolio read already
  handled in earlier sub-tasks).
- [ ] After each sub-task: run affected tests, commit.

### Task 13: Plugin/skill/agent reference updates

Per spec §4's plugin/skill reference table, update every `SKILL.md`/agent markdown file that names
`target-portfolio.json`, `watchlist.json`, `tradingview_alerts_actual.json`, or
`thesis_breaker_state.json` by filename to instead reference the new repository/query method (mirror
Wave 1's approach — doc-text updates, not runtime code). Confirmed referencing files from spec §4:
`etf_analysis`, `daily-loop-agent.md`, `portfolio-advisor-orchestrator.md`, `single-stock-advisor.md`,
`thesis-review-agent.md`, `13f-analyze`, `adversarial-review`, `calibrate-targets`, `daily-brief`,
`rebalance-portfolio`, `set-thesis-breakers`, `strategic-review`, `thesis-challenge-bundler`,
`thesis-review`, `update-portfolio-targets`, `x-news-sweep`, `stock_valuation`,
`toolkit-onboarding-guide.md`, `place-order`, `price-refresh`, `ta-daily-sweep`,
`tradingview-onboarding.md`, `tv-manage-watchlists`, `tv-portfolio-sync`, `alert-list`,
`rebalance-portfolio` (thesis breaker reference). Re-grep this list against real current files before
editing (this plan's list is from the spec, which itself should be re-verified per this whole
migration's standing discipline) — do not trust it as final without a fresh grep.

- [ ] Re-grep: `grep -rl "target-portfolio.json\|watchlist.json\|tradingview_alerts_actual.json\|thesis_breaker_state.json" .agents plugins --include="*.md" --include="*.json"`
- [ ] Update each real match's prose to reference the domain-model repository/query method instead
  of the filename, recording the file-count/size reduction this produces for a representative
  bundle (Context Bundle Completion Bar, per spec requirement).
- [ ] Commit.

---

## Task 14: Archive-readiness verification + `git mv` archive

**Only after every gate below is independently confirmed true** (not assumed) — mirrors Wave 1's
Task 8 exactly:

- [ ] All 11 producers confirmed cut over (Task 9).
- [ ] All 19 core consumers + 6 watchlist + alerts + thesis-breaker consumers confirmed cut over
  (Tasks 10-12).
- [ ] Archive-readiness grep clean: `grep -rn "target-portfolio.json\|theses/target-portfolio\|watchlist.json\|tradingview_alerts_actual.json\|thesis_breaker_state.json" investment_screener plugins --include="*.py" --include="*.ts" --include="*.tsx" --include="*.js"` returns zero real-I/O matches (doc/comment mentions individually verified as non-runtime).
- [ ] Repository-path (anti-bypass) grep clean: no script outside `domain_model/*_repository.py`
  (Python) or the TS repository-equivalent opens its own SQLite connection against `investment`,
  `strategy_pillar`, `sub_strategy`, `price_level_set`, `price_level_tier`, `investment_note`,
  `alert`.
- [ ] Full backend Python + TS test suites pass at the documented pre-existing baseline (compare
  against Wave 1's documented `1267 passed, 24 failed (pre-existing)` / `65 passing, 1 failing
  (pre-existing)` baseline — investigate any new failure beyond that baseline before proceeding).
- [ ] Rollback still possible: `target-portfolio.json`/`watchlist.json` git history intact,
  `tradingview_alerts_actual.json`/`thesis_breaker_state.json` git history intact (all 4 are
  git-tracked, not gitignored, per spec §2.1/§2.7/§2.15 — none require the LOCAL_PRIVATE_ARCHIVE
  treatment §2.19 reserves for gitignored files).

- [ ] **Archive step:**

```bash
git mv investment_screener/backend/data/theses/target-portfolio.json \
       ARCHIVE/investment_screener/backend/data/theses/target-portfolio.json
git mv investment_screener/backend/data/watchlist.json \
       ARCHIVE/investment_screener/backend/data/watchlist.json
git mv investment_screener/backend/data/tradingview_alerts_actual.json \
       ARCHIVE/investment_screener/backend/data/tradingview_alerts_actual.json
git mv investment_screener/backend/data/thesis_breaker_state.json \
       ARCHIVE/investment_screener/backend/data/thesis_breaker_state.json
git commit -m "refactor: archive target-portfolio/watchlist/alerts/breaker-state JSON after Wave 2 SQLite cutover"
```

- [ ] Re-run both test suites immediately after the archive commit, confirm identical results to
  the pre-archive run (no hidden dependency on the old paths).

---

## Task 15: Wave 2 exit report + handoff (match Wave 1's depth exactly)

**Files:**
- Create: `docs/superpowers/status/wave2-target-portfolio-report.md`
- Create: `docs/superpowers/status/wave2-handoff.md`

- [ ] Fill in the Wave KPI table with real numbers: JSON files before (4: target-portfolio.json,
  watchlist.json, tradingview_alerts_actual.json, thesis_breaker_state.json) / after (0 active, 4
  archived), reads/writes removed, producers migrated (n/11), consumers migrated (n/19+6+4+4),
  plugin/skill/agent references updated (from Task 13), context-bundle files removed.
- [ ] Producer/consumer cutover table — one row per real file from Tasks 9-12, each ending in
  `Cutover status: DONE`.
- [ ] Real bugs found and fixed section — include the two stale-path bugs from Task 0 (with
  before/after evidence), plus anything found during Tasks 9-13 (do not smooth over, per this
  migration's standing discipline).
- [ ] Validation results: migration parity (holdings count, price-level-set count, note count,
  alert count — real numbers, full check not a sample, matching Wave 1's "82/82 tickers matched
  exactly" rigor).
- [ ] `standingDecision` anchor rule (CLAUDE.md #8) re-verification result — explicit pass/fail
  statement with evidence, since this is the wave's highest-risk item.
- [ ] Archive evidence, rollback instructions (mirroring Wave 1's exact structure).
- [ ] Commit list.
- [ ] Definition of Done — all 9 items verified explicitly, same as Wave 1's report.
- [ ] Handoff doc: accomplishments, remaining waves (3, 4, 5A-5E), open issues, exact branch/commit
  references, instructions for the next fresh session (gated on this wave's PR review/merge, same
  as Wave 1 → Wave 2 transition).

- [ ] Push wave commits to the remote branch; open a PR to `main` (do not merge unless explicitly
  told to). Verify remote branch matches local HEAD exactly before reporting the PR as ready.

- [ ] **Stop. Do not start Wave 3.** Wait for user review/merge, per standing instruction.

---

## Self-Review

**1. Spec coverage:** Every domain in spec §2.1 (investment/target/watchlist), §2.2 (price levels),
§2.3 (investment notes), §2.7 (alerts), §2.15 (thesis breaker state) has a corresponding task above.
The confirmed investigation findings (stale paths, `portfolio_action.py`, real field shapes) are
incorporated as required inputs, not optional notes, per the user's explicit instruction. The
`standingDecision` anchor rule is called out as the highest-risk item in Tasks 5, 7, 10, and 15
(four separate checkpoints, not one).

**2. Placeholder scan:** Tasks 0-8 (repositories + migration script) contain complete, real,
TDD-ready code. Tasks 9-13 (producer/consumer rewiring across 30+ files) are deliberately NOT
pre-scripted with exact diffs — per this migration's own established discipline (Wave 1's Task 7,
and the kickoff prompt's explicit instruction that this is "honesty, not corner-cutting" for
consumer-rewiring work spanning many files not yet freshly read). Each of those tasks states the
real file list, the available repository functions, and the instruction to read fresh before
editing — this is the sanctioned pattern, not an under-specification gap.

**3. Type consistency:** `resolve_investment(conn, symbol, asset_class, currency, name)` (Wave 0)
is called identically in Task 6/7's migration script. `update_investment_fields(conn,
investment_id, **fields)` (Task 5) matches its usage in Task 7. `replace_price_levels`'s
`target_entry_price` parameter (Task 2) matches the migration script's `holding.get
("targetEntryPrice")` usage (Task 7). `add_note`'s `note_type="MIGRATED_LEGACY_RATIONALE"` string
(Task 3) matches its usage in Task 7's migration script and Task 3's own test.
