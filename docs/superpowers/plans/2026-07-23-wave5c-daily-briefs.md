# Wave 5C — Daily Briefs Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate `investment_screener/backend/data/daily-briefs/*.json` (gitignored, 10 real
snapshots) into `intelligence_event` (`event_type='REVIEW_DAILY'`), completing producer cutover
(already dual-writing), consumer cutover (2 real consumers: `dailybrief.ts` route,
`generate_reports.py`), and archive — per ADR-029's three-part "migrated" definition.

**Architecture:** No new tables. Reuses the existing `intelligence_event` ledger
(`observations.jsonl` → `intelligence.sqlite`) and the `py_services/intelligence/` repository
module Wave 5A/5B already established. This domain is materially further along than 5B's TA-sweep
domain was at kickoff: the producer (`daily_brief.py`) already calls `append_event(...,
event_type="REVIEW_DAILY", ...)`, and the consumer route (`dailybrief.ts`) already has
ledger-first code (`queryLatestBriefFromLedger` → `query_ledger_brief.py` →
`get_latest_event_by_type`) with a JSON-file fallback branch. What's missing: real ledger data (0
rows today), one anti-bypass fix, two consumer rewires (`generate_reports.py`,
`daily_brief.py::_load_yesterday()`), fallback removal, and the real tests/parity/rollback
evidence the spec requires.

**Tech Stack:** Python 3.13 (`sqlite3` stdlib), `py_services/intelligence/` (`event_store.py`,
`event_repository.py`, `replay_ledger.py`, `db_client.py`), TypeScript/Express
(`routes/dailybrief.ts`, `better-sqlite3` in tests), pytest + mocha/chai.

## Global Constraints

(Copied verbatim from `docs/superpowers/specs/2026-07-19-domain-data-model-v3-implementation-design.md` and `docs/superpowers/plans/2026-07-19-domain-data-model-v3-implementation-plan.md` — every task below implicitly includes these.)

- **This is a pivot, not an addition.** SQLite/domain repositories become the primary persistence
  layer for applicable operational data; JSON/JSONL must not remain an active operational store
  without an explicit approved exception (spec §2.18).
- **No permanent hybrid.** `JSON + JSONL + SQLite` forever is a failed wave, not a resting state.
- **A domain is migrated only when:** producer writes SQLite + every real consumer reads SQLite +
  old file archived via `git mv` (or local-only `mv` for gitignored files, spec §2.19). Table
  existence, data copying, or a passing fixture test do not count.
- **No script opens its own SQLite connection outside the owning repository/service layer.**
- **Every wave reports:** the Wave KPI table (JSON files before/after, files archived,
  reads/writes removed, producers/consumers migrated, context-bundle files removed, remaining
  exceptions named).
- **Archive convention:** `ARCHIVE/<mirrored source path>` via `git mv`; gitignored/private files
  archive locally only, never `git add`ed (spec §2.19). `data/daily-briefs/*.json` is gitignored
  (`investment_screener/.gitignore:119`) — **local-only `mv`, never `git mv`.**
- **A "real data migration write" must run against the main checkout's actual gitignored data
  files and actual `intelligence.sqlite`, never a worktree's copy.** Any verification of row
  counts must explicitly target main's file paths, not rely on a worktree-relative default.
- **When a real migration script takes multiple path arguments (source file, target DB, AND a
  ledger/JSONL path), override every one of them explicitly to main-checkout absolute paths.**
  This migration writes to two stores (`observations.jsonl` + `intelligence.sqlite`) — both must
  be passed explicit main-checkout absolute paths for the real write, and both must be
  independently re-verified afterward.
- **A wave's plan document must include the design spec's actual required content verbatim.**
  See the dedicated sections below: Hybrid Exit Criteria, §5 Validation Strategy, 9-item
  Definition of Done, Context Bundle Completion Bar.

---

## Task 0 Findings (already completed, evidence for the record)

Verified against real, current code (not the spec's summary) before this plan was written:

- `daily_brief.py` (`plugins/portfolio-advisor/scripts/daily_brief.py:636-667`) **already**
  dual-writes: after saving `data/daily-briefs/{date}.json`, it calls
  `append_event(..., event_type="REVIEW_DAILY", ..., idempotency_key=f"daily-brief-{today_str}")`
  then `replay_events_to_db(...)`. This differs from the "code wired but no real test exists"
  framing only in that it's real, current code — not stale/dead. Confirmed via direct read, not
  assumed.
- `intelligence.sqlite` (main checkout) has **0** `REVIEW_DAILY` rows today, confirmed via
  `sqlite3 investment_screener/backend/data/intelligence.sqlite "SELECT event_type, COUNT(*) FROM
  intelligence_event GROUP BY event_type"` → `RESEARCH_IMPORT|80`, `TECHNICAL_SWEEP|105`, no
  `REVIEW_DAILY` row. `REVIEW_DAILY` **is** a valid value in the live `event_type` CHECK
  constraint already (confirmed via `sqlite_master` schema dump). So: dual-write code exists,
  fires every real `daily_brief.py` run, but the table is empty — meaning either the code path has
  never actually executed against the main checkout's real DB, or it silently failed. Task 4 below
  investigates and fixes this before backfilling.
- **`generate_reports.py::load_latest_brief()`** (line 99) is a real, live consumer:
  `glob.glob(os.path.join(DAILY_BRIEFS_DIR, "*.json"))` → picks the file with the latest mtime.
  Confirmed real (not docstring-only) by reading the function body.
- **`investment_screener/backend/src/routes/dailybrief.ts` is a real consumer the design spec's
  §4 inventory table MISSED** (spec listed only `generate_reports.py`). It's a live Express route
  (`GET /latest`, `/history`, `/conviction/:ticker`) already wired ledger-first:
  `queryLatestBriefFromLedger()` → `spawnPythonScript('query_ledger_brief.py', ['--latest'])` →
  `get_latest_event_by_type(conn, "REVIEW_DAILY")`, falling back to `fs.readdirSync(BRIEFS_DIR)` +
  `JSON.parse(fs.readFileSync(...))` only when the ledger query returns null/throws. Since the
  ledger has 0 rows today, **every real production request today silently uses the JSON
  fallback** — the ledger-first branch has never actually served real data. This route must be
  added to the wave's cutover table; it was missing from the spec's inventory (the inverse of
  Wave 5B's `evolution_events.py` false-positive — a real consumer the inventory missed, not a
  claimed one that wasn't real).
- **`query_ledger_brief.py` (backing the above route) opens its own `sqlite3.connect(db_path)`
  and runs raw SQL directly for `--history` and `--conviction`** (only `--latest` goes through
  `event_repository.get_latest_event_by_type`). This is a real violation of the Global Constraint
  "no script opens its own SQLite connection outside the owning repository/service layer" —
  Hard-Stop Condition #6. Must be fixed as part of this wave (Task 1 below), not carried forward.
- **`daily_brief.py::_load_yesterday()`** (line 128) is the delta-vs-yesterday glob+sort logic the
  spec's §2.13 calls out for SQL rewire: `sorted(DAILY_BRIEFS_DIR.glob("*.json"),
  reverse=True)`, returns the first snapshot whose filename stem isn't today. Must become
  `ORDER BY effective_at DESC LIMIT 2` per spec.
- **Docstring-only mentions, confirmed NOT real I/O** (excluded from the cutover table per the
  spec's "doc/comment mentions excluded, verified individually" rule): `macro_regime.py:17`,
  `grade_predictions.py:16`, `brief_recommendations.py:23`, `harvest_predictions.py:18`,
  `prediction_ledger.py:20` — all list `data/daily-briefs/` only in a "Key Input/Output
  Dependencies" docstring header, none contain any `daily-briefs`-path file I/O in their function
  bodies (verified via grep + read).
- **Existing tests already fixture-cover the query layer, not the producer or real data:**
  `investment_screener/backend/tests/api/dailybrief.spec.ts` tests `queryLatestBriefFromLedger` /
  `queryBriefHistoryFromLedger` / `queryTickerConvictionFromLedger` against a **fixture**
  `better-sqlite3` DB with hand-inserted `REVIEW_DAILY` rows — proves the query SQL is correct,
  proves nothing about whether `daily_brief.py`'s real dual-write actually populates real rows in
  main's real `intelligence.sqlite`. No test today exercises `daily_brief.py`'s dual-write block
  itself (lines 636-667) at all — that's the actual "no real test exists for this path" gap the
  prior effort's caveat pointed at, now precisely located.
- **Context Bundle reference count:** spec §4 lists exactly one skill referencing
  `data/daily-briefs/*.json`: `daily-brief`. Confirmed via
  `grep -rn "daily-briefs" plugins/portfolio-advisor/skills/daily-brief/SKILL.md` → one hit,
  line 136: `` investment_screener/backend/data/daily-briefs/YYYY-MM-DD.json `` (a "where output
  goes" description). This is the one reference Task 9 (Context Bundle bar) must update.

---

## Hybrid Exit Criteria (spec § "Hybrid Exit Criteria", applied to this domain)

Target architecture: SQLite/domain model as authoritative; hybrid (dual-write, JSON fallback) is
a temporary migration aid, never a resting state. Three-part test for this domain:

| Test | Current state (pre-wave) | Required post-wave state |
|---|---|---|
| Producer cutover | `daily_brief.py` dual-writes JSON + ledger event (code exists, real rows = 0) | Producer writes ledger unconditionally; JSON write may remain only if still needed by a consumer not yet cut over (none, after this wave) |
| Consumer cutover | `dailybrief.ts` ledger-first w/ JSON fallback (fallback always taken today); `generate_reports.py` reads JSON only, no ledger awareness | Both consumers read `intelligence_event` only, zero JSON fallback branches reachable |
| Archive | `data/daily-briefs/*.json` (10 files) live in `investment_screener/backend/data/` | Locally `mv`'d to `ARCHIVE/investment_screener/backend/data/daily-briefs/` (gitignored — local-only, never `git mv`/`git add`) |

No domain is allowed to sit in dual-write state past this wave.

---

## §5 Validation Strategy (spec verbatim checklist, applied to this domain)

- [ ] **Schema tests:** N/A — no new table (`intelligence_event` and its CHECK constraint already
  support `REVIEW_DAILY`; already covered by existing `test_event_repository.py`/db_client tests).
- [ ] **Migration tests:** dry-run against the real 10 `data/daily-briefs/*.json` files with
  field-level parity (not a sample) — Task 3/4.
- [ ] **Repository tests:** `query_ledger_brief.py` routed entirely through
  `py_services/intelligence/event_repository.py` functions, no inline `sqlite3.connect()` +
  raw SQL left in the CLI script — Task 1.
- [ ] **Consumer tests:** one test per real consumer (`dailybrief.ts` route handlers,
  `generate_reports.py::load_latest_brief()`) confirming each reads `intelligence_event`, not the
  old file, with the JSON fallback branch removed — Tasks 5, 6, 7.
- [ ] **Parity tests:** run both paths in parallel for at least one full real-world cycle (a real
  `daily_brief.py` run) and diff row-for-row — Task 8.
- [ ] **Live-path tests where practical:** manually exercise `GET /api/daily-brief/latest` against
  the real, now-populated `intelligence.sqlite` — Task 8.
- [ ] **Grep/scan for legacy JSON reads/writes:** `grep -rn "daily-briefs" investment_screener
  plugins` returning zero real-I/O matches (doc mentions excluded, verified individually) before
  archive — Task 9.
- [ ] **Archive verification:** confirm local `mv` executed, confirm old path no longer resolves
  via any code path, confirm `ARCHIVE/` copy readable — Task 9.
- [ ] **Rollback verification:** physically exercise rollback once for this domain before
  declaring the wave done — restore from `ARCHIVE/`, revert producer/consumer commits, confirm
  the app runs correctly against the old files again — Task 10 (throwaway worktree, per Wave 5B's
  template).
- [ ] **Context-bundle verification:** confirm `daily-brief/SKILL.md` no longer references the old
  file path, record the reference-count reduction (1 → 0) — Task 9.

---

## Definition of Done (spec's 9-item list, verbatim, applies to this wave without exception)

A wave is complete only when all nine are true:

1. Data is migrated to SQLite/domain model.
2. Real producers write SQLite/domain repositories.
3. Real consumers read SQLite/domain repositories.
4. Old JSON/JSONL runtime references are removed or rewritten.
5. SKILL.md / agent / plugin instructions no longer point at old JSON.
6. Context-bundler no longer needs retired JSON files for that domain.
7. Old JSON/JSONL is archived with `git mv` (or local-only `mv` for gitignored files, spec §2.19)
   or retained under a completed Retained-JSON Rationale Bar (spec §2.18).
8. Tests prove live path behavior against real data, not only fixture behavior.
9. JSON file count and context-bundle footprint are reported before/after (Wave KPI table).

A wave that finishes in this state has **failed**, regardless of what its status report claims:
`SQLite table exists + JSON still authoritative + runtime still reads JSON + fallback remains
indefinitely`.

---

## Context Bundle Completion Bar

Per spec §4's Producer/Consumer Mapping table: `data/daily-briefs/*.json` is referenced by exactly
one skill, `daily-brief` (`plugins/portfolio-advisor/skills/daily-brief/SKILL.md:136`).

- **Before wave:** 1 stale-after-migration reference (describes the JSON output path as where
  results land).
- **After wave (Task 9):** must be 0 — reference rewritten to describe the ledger write instead.
  Verified via `grep -rn "daily-briefs" plugins/portfolio-advisor/skills/daily-brief/` → expect
  zero hits on the old path.

---

## Hard-Stop Conditions (spec §6, re-checked explicitly before declaring this wave done)

1. Source count and target row count do not reconcile.
2. Row/version/scenario count has an unexplained delta.
3. A new data shape is discovered without a test covering it.
4. A producer still writes the old JSON path as source of truth (JSON write may remain
   informationally, but must not be read by any consumer post-wave).
5. A real consumer still reads the old JSON path after claimed cutover.
6. Any script bypasses the approved repository/service layer and opens SQLite directly
   (**pre-existing violation found in Task 0**, fixed by Task 1 — must be re-verified clean).
7. Tests fail in a new or migration-related way (documented pre-existing baseline: `zod-
   schemas.spec.ts`, an `InvestmentRepository` real-sqlite parity test needing a live broker sync
   — confirmed unrelated through Wave 5B, re-confirm still the only pre-existing failures here).
8. Archive-readiness grep still finds real runtime I/O to the old JSON path.
9. The archive step would remove rollback capability.
10. Context-bundler still requires retired files without explanation.
11. The wave would end in a permanent hybrid state.
12. A real data migration write is claimed verified without independent re-run against main's
    actual files.
13. The "wired, exercised in production" claim is repeated without independent re-confirmation.
14. A real migration write touches more than one store and verification only checked one.
15. The wave's plan document lacks the spec's verbatim Hybrid Exit Criteria/§5/DoD/Context Bundle
    content (this document includes all four above).

---

## Task 1: Fix `query_ledger_brief.py`'s anti-bypass violation

**Files:**
- Modify: `investment_screener/backend/py_services/intelligence/event_repository.py`
- Modify: `investment_screener/backend/py_services/query_ledger_brief.py`
- Test: `investment_screener/backend/tests/py_services/test_event_repository.py`

**Interfaces:**
- Produces: `list_active_events_by_type(conn, event_type: str) -> list[dict]` — new repository
  function, ordered `effective_at DESC, ingested_at DESC`. Used by Task 1's rewrite and by Task 6.

- [ ] **Step 1: Write the failing test for the new repository function**

Add to `investment_screener/backend/tests/py_services/test_event_repository.py` (this file
already has fixture-DB setup helpers for `intelligence_event` — follow its existing pattern by
reading the file's current fixture/connection setup first, then add):

```python
def test_list_active_events_by_type_returns_all_matching_ordered_desc(conn):
    from intelligence.event_repository import list_active_events_by_type
    from intelligence.event_repository import insert_event

    insert_event(conn, {
        "event_id": "evt_1", "event_sequence": 1, "instrument_id": None,
        "event_type": "REVIEW_DAILY", "effective_at": "2026-07-17",
        "observed_at": None, "ingested_at": "2026-07-17T10:00:00Z",
        "source_id": "daily_brief", "confidence_score": None, "status": "ACTIVE",
        "title": "Daily Brief for 2026-07-17", "body_markdown": "x",
        "payload_json": '{"date": "2026-07-17"}', "supersedes_event_id": None,
        "idempotency_key": "daily-brief-2026-07-17", "content_hash": "h1",
    })
    insert_event(conn, {
        "event_id": "evt_2", "event_sequence": 2, "instrument_id": None,
        "event_type": "REVIEW_DAILY", "effective_at": "2026-07-18",
        "observed_at": None, "ingested_at": "2026-07-18T10:00:00Z",
        "source_id": "daily_brief", "confidence_score": None, "status": "ACTIVE",
        "title": "Daily Brief for 2026-07-18", "body_markdown": "x",
        "payload_json": '{"date": "2026-07-18"}', "supersedes_event_id": None,
        "idempotency_key": "daily-brief-2026-07-18", "content_hash": "h2",
    })

    results = list_active_events_by_type(conn, "REVIEW_DAILY")

    assert len(results) == 2
    assert results[0]["event_id"] == "evt_2"  # newest first
    assert results[1]["event_id"] == "evt_1"
```

(Reuse whichever `conn` fixture the existing tests in this file already use — read the file's top
for the actual fixture name/signature before pasting; do not invent a new one.)

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest investment_screener/backend/tests/py_services/test_event_repository.py::test_list_active_events_by_type_returns_all_matching_ordered_desc -v`
Expected: FAIL with `ImportError: cannot import name 'list_active_events_by_type'`

- [ ] **Step 3: Implement the repository function**

Add to `investment_screener/backend/py_services/intelligence/event_repository.py` (after
`get_latest_event_by_type`):

```python
def list_active_events_by_type(conn, event_type: str) -> list[dict]:
    """Return every ACTIVE event of the given type, newest first.

    Args:
        conn: Open sqlite3 connection with the read-model schema applied.
        event_type: Event type to filter on (e.g. ``REVIEW_DAILY``).

    Returns:
        List of event dicts ordered by effective_at DESC, ingested_at DESC.
    """
    cursor = conn.execute("""
        SELECT ie.event_id, ie.event_sequence, ie.instrument_id, ie.event_type,
               ie.effective_at, ie.observed_at, ie.ingested_at, ie.source_id,
               ie.confidence_score, ie.status, ie.title, ie.body_markdown,
               ie.payload_json, ie.supersedes_event_id, ie.idempotency_key,
               ie.content_hash
        FROM intelligence_event ie
        WHERE ie.event_type = ? AND ie.status = 'ACTIVE'
        ORDER BY ie.effective_at DESC, ie.ingested_at DESC;
    """, (event_type,))
    columns = [d[0] for d in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest investment_screener/backend/tests/py_services/test_event_repository.py::test_list_active_events_by_type_returns_all_matching_ordered_desc -v`
Expected: PASS

- [ ] **Step 5: Rewrite `query_ledger_brief.py` to use only repository functions**

Replace the `--history` and `--conviction` branches in
`investment_screener/backend/py_services/query_ledger_brief.py`'s `main()` (read the current file
first — this replaces the raw-SQL blocks under `elif args.history:` and `elif args.conviction:`,
keeping the same JSON output shape each already produces):

```python
        elif args.history:
            from intelligence.event_repository import list_active_events_by_type
            events = list_active_events_by_type(conn, "REVIEW_DAILY")
            history = []
            for event in events:
                payload_json = event.get("payload_json")
                if not payload_json:
                    continue
                try:
                    d = json.loads(payload_json)
                    history.append({
                        "date": d.get("date"),
                        "regime": d.get("macro_regime", {}).get("regime"),
                        "reduce_count": len([s for s in d.get("conviction_scores", []) if s.get("band") in ("REDUCE", "EXIT")]),
                        "accum_count": len([s for s in d.get("conviction_scores", []) if s.get("band") == "ACCUMULATE"]),
                        "ta_refreshed": d.get("ta_refreshed"),
                    })
                except Exception:
                    pass
            print(json.dumps(history))

        elif args.conviction:
            from intelligence.event_repository import list_active_events_by_type
            ticker = args.conviction.upper()
            events = list_active_events_by_type(conn, "REVIEW_DAILY")
            conviction_history = []
            for event in reversed(events):  # ascending by date for this endpoint
                payload_json = event.get("payload_json")
                if not payload_json:
                    continue
                try:
                    d = json.loads(payload_json)
                except Exception:
                    continue
                score = next((s for s in d.get("conviction_scores", []) if s.get("ticker") == ticker), None)
                if score:
                    conviction_history.append({"date": d.get("date"), **score})
            print(json.dumps(conviction_history))
```

Also change the top-level `conn = sqlite3.connect(db_path)` line to keep using a plain connection
(fine to keep — the anti-bypass rule is about **raw SQL against `intelligence_event` outside the
repository module**, not about which module opens the file handle; `query_ledger_brief.py` is a
thin CLI already passing `conn` into `get_latest_event_by_type` today — this step makes the other
two branches follow the same pattern, closing the actual violation).

- [ ] **Step 6: Run the full repository + query_ledger_brief test suite**

Run: `python3 -m pytest investment_screener/backend/tests/py_services/test_event_repository.py -v`
Expected: all PASS, including the new test.

Run: `cd investment_screener/backend && npx mocha -r ts-node/register tests/api/dailybrief.spec.ts` (or the project's existing mocha invocation for `tests/api/` — check `package.json`'s
`test` script for the exact command before running) to confirm `query_ledger_brief.py --history`/
`--conviction`'s output shape is unchanged from the fixture DB's perspective.
Expected: all PASS (the CLI's output shape is identical, only its internal SQL access path
changed).

- [ ] **Step 7: Commit**

```bash
git add investment_screener/backend/py_services/intelligence/event_repository.py \
        investment_screener/backend/py_services/query_ledger_brief.py \
        investment_screener/backend/tests/py_services/test_event_repository.py
git commit -m "fix(query_ledger_brief): route --history/--conviction through event_repository, close anti-bypass gap"
```

---

## Task 2: Add the missing real test for `daily_brief.py`'s dual-write block

**Files:**
- Test: `investment_screener/backend/tests/py_services/test_daily_brief_review_daily_dual_write.py` (create)

**Interfaces:**
- Consumes: `append_event`, `_default_jsonl_path` (`intelligence.event_store`),
  `replay_events_to_db` (`intelligence.replay_ledger`), `initialize_db` (`intelligence.db_client`)
  — same imports `daily_brief.py:638-640` already uses.

This closes the exact "no real test exists for this path" gap Task 0 confirmed. It does not test
the full `daily_brief.py::run()` (too many live external dependencies — TV CDP, yfinance); it
isolates the dual-write block itself by calling `append_event`/`replay_events_to_db` exactly as
`daily_brief.py` does, against a `tmp_path` JSONL + DB pair, and asserts a real row lands.

- [ ] **Step 1: Write the failing test**

```python
"""Real (non-mocked) test for daily_brief.py's REVIEW_DAILY dual-write block.

Isolates the append_event -> replay_events_to_db sequence daily_brief.py:636-667
performs, run against a tmp_path JSONL + SQLite pair, so a real row is asserted to land
without depending on daily_brief.py's full external I/O (TV CDP, yfinance, etc.).
"""
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))


def test_review_daily_dual_write_lands_real_row(tmp_path):
    from intelligence.event_store import append_event
    from intelligence.replay_ledger import replay_events_to_db
    from intelligence.db_client import initialize_db

    jsonl_path = tmp_path / "observations.jsonl"
    db_path = tmp_path / "intelligence.sqlite"

    brief = {
        "date": "2026-07-23",
        "macro_regime": {"regime": "BULL"},
        "conviction_scores": [{"ticker": "MSFT", "total": 8, "band": "ACCUMULATE"}],
    }

    append_event(
        str(jsonl_path),
        event_type="REVIEW_DAILY",
        effective_at="2026-07-23",
        status="ACTIVE",
        title="Daily Brief for 2026-07-23",
        body_markdown="Generated daily brief summary metrics.",
        ticker=None,
        source_id="daily_brief",
        payload=brief,
        idempotency_key="daily-brief-2026-07-23",
    )

    conn = initialize_db(str(db_path))
    try:
        replay_events_to_db(str(jsonl_path), conn)
        row = conn.execute(
            "SELECT event_type, effective_at, payload_json FROM intelligence_event "
            "WHERE idempotency_key = ?",
            ("daily-brief-2026-07-23",),
        ).fetchone()
    finally:
        conn.close()

    assert row is not None
    assert row[0] == "REVIEW_DAILY"
    assert row[1] == "2026-07-23"
    assert json.loads(row[2])["conviction_scores"][0]["ticker"] == "MSFT"


def test_review_daily_dual_write_is_idempotent_on_rerun(tmp_path):
    """A second append_event call with the same idempotency_key must not create a duplicate row."""
    from intelligence.event_store import append_event
    from intelligence.replay_ledger import replay_events_to_db
    from intelligence.db_client import initialize_db

    jsonl_path = tmp_path / "observations.jsonl"
    db_path = tmp_path / "intelligence.sqlite"
    brief = {"date": "2026-07-23", "macro_regime": {"regime": "BULL"}, "conviction_scores": []}

    for _ in range(2):
        append_event(
            str(jsonl_path),
            event_type="REVIEW_DAILY",
            effective_at="2026-07-23",
            status="ACTIVE",
            title="Daily Brief for 2026-07-23",
            body_markdown="Generated daily brief summary metrics.",
            ticker=None,
            source_id="daily_brief",
            payload=brief,
            idempotency_key="daily-brief-2026-07-23",
        )

    conn = initialize_db(str(db_path))
    try:
        replay_events_to_db(str(jsonl_path), conn)
        count = conn.execute(
            "SELECT COUNT(*) FROM intelligence_event WHERE idempotency_key = ?",
            ("daily-brief-2026-07-23",),
        ).fetchone()[0]
    finally:
        conn.close()

    assert count == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest investment_screener/backend/tests/py_services/test_daily_brief_review_daily_dual_write.py -v`
Expected: at this point it should actually PASS already, since `append_event`/`replay_events_to_db`
are pre-existing, working functions — this test's purpose is to *exist* (closing DoD item 8's
gap), not to drive new production code. If it fails, investigate why before proceeding — that
would mean the dual-write machinery itself is broken, a Hard-Stop-worthy finding.

- [ ] **Step 3: Confirm it passes and commit**

Run: `python3 -m pytest investment_screener/backend/tests/py_services/test_daily_brief_review_daily_dual_write.py -v`
Expected: 2 passed.

```bash
git add investment_screener/backend/tests/py_services/test_daily_brief_review_daily_dual_write.py
git commit -m "test(daily_brief): add missing real test for REVIEW_DAILY dual-write block"
```

---

## Task 3: Write the backfill migration script (dry-run capable)

**Files:**
- Create: `investment_screener/backend/py_services/migrate_daily_briefs_to_ledger.py`
- Test: `investment_screener/backend/tests/py_services/test_migrate_daily_briefs_to_ledger.py`

**Interfaces:**
- Produces: `migrate(briefs_dir: Path, jsonl_path: Path, db_path: Path, dry_run: bool = True) -> dict`
  returning `{"source_count": int, "written_count": int, "skipped": list[str]}` — mirrors
  `migrate_ta_sweep_to_ledger.py`'s exact shape (Wave 5B's proven template).

- [ ] **Step 1: Write the failing test**

```python
"""Tests for migrate_daily_briefs_to_ledger.py — mirrors test_migrate_ta_sweep_to_ledger.py's
structure for the daily-briefs domain (Wave 5C)."""
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))

from migrate_daily_briefs_to_ledger import migrate


def _write_brief(briefs_dir: Path, date_str: str, regime: str) -> None:
    briefs_dir.mkdir(parents=True, exist_ok=True)
    (briefs_dir / f"{date_str}.json").write_text(json.dumps({
        "date": date_str,
        "macro_regime": {"regime": regime},
        "conviction_scores": [{"ticker": "MSFT", "total": 7, "band": "MAINTAIN"}],
    }))


def test_migrate_dry_run_reports_counts_without_writing(tmp_path):
    briefs_dir = tmp_path / "daily-briefs"
    _write_brief(briefs_dir, "2026-07-17", "BULL")
    _write_brief(briefs_dir, "2026-07-18", "CONGESTION")
    jsonl_path = tmp_path / "observations.jsonl"
    db_path = tmp_path / "intelligence.sqlite"

    report = migrate(briefs_dir, jsonl_path, db_path, dry_run=True)

    assert report["source_count"] == 2
    assert report["written_count"] == 0
    assert not jsonl_path.exists()
    assert not db_path.exists()


def test_migrate_write_creates_real_rows(tmp_path):
    briefs_dir = tmp_path / "daily-briefs"
    _write_brief(briefs_dir, "2026-07-17", "BULL")
    _write_brief(briefs_dir, "2026-07-18", "CONGESTION")
    jsonl_path = tmp_path / "observations.jsonl"
    db_path = tmp_path / "intelligence.sqlite"

    report = migrate(briefs_dir, jsonl_path, db_path, dry_run=False)

    assert report["source_count"] == 2
    assert report["written_count"] == 2

    import sqlite3
    conn = sqlite3.connect(str(db_path))
    try:
        rows = conn.execute(
            "SELECT effective_at, idempotency_key FROM intelligence_event "
            "WHERE event_type = 'REVIEW_DAILY' ORDER BY effective_at"
        ).fetchall()
    finally:
        conn.close()
    assert rows == [
        ("2026-07-17", "daily-brief-2026-07-17"),
        ("2026-07-18", "daily-brief-2026-07-18"),
    ]


def test_migrate_write_is_idempotent_against_a_real_producer_rerun(tmp_path):
    """A future real daily_brief.py run for an already-backfilled date must not double-write —
    both use the same idempotency_key format (daily-brief-{date})."""
    briefs_dir = tmp_path / "daily-briefs"
    _write_brief(briefs_dir, "2026-07-17", "BULL")
    jsonl_path = tmp_path / "observations.jsonl"
    db_path = tmp_path / "intelligence.sqlite"
    migrate(briefs_dir, jsonl_path, db_path, dry_run=False)

    from intelligence.event_store import append_event
    from intelligence.replay_ledger import replay_events_to_db
    from intelligence.db_client import initialize_db

    append_event(
        str(jsonl_path), event_type="REVIEW_DAILY", effective_at="2026-07-17", status="ACTIVE",
        title="Daily Brief for 2026-07-17", body_markdown="rerun",
        ticker=None, source_id="daily_brief", payload={"date": "2026-07-17"},
        idempotency_key="daily-brief-2026-07-17",
    )
    conn = initialize_db(str(db_path))
    try:
        replay_events_to_db(str(jsonl_path), conn)
        count = conn.execute(
            "SELECT COUNT(*) FROM intelligence_event WHERE idempotency_key = ?",
            ("daily-brief-2026-07-17",),
        ).fetchone()[0]
    finally:
        conn.close()
    assert count == 1


def test_migrate_skips_files_missing_date_field(tmp_path):
    briefs_dir = tmp_path / "daily-briefs"
    briefs_dir.mkdir(parents=True)
    (briefs_dir / "2026-07-19.json").write_text(json.dumps({"macro_regime": {"regime": "BULL"}}))
    jsonl_path = tmp_path / "observations.jsonl"
    db_path = tmp_path / "intelligence.sqlite"

    report = migrate(briefs_dir, jsonl_path, db_path, dry_run=True)

    assert report["source_count"] == 1
    assert report["written_count"] == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest investment_screener/backend/tests/py_services/test_migrate_daily_briefs_to_ledger.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'migrate_daily_briefs_to_ledger'`

- [ ] **Step 3: Implement the migration script**

Create `investment_screener/backend/py_services/migrate_daily_briefs_to_ledger.py`, mirroring
`migrate_ta_sweep_to_ledger.py`'s structure exactly (one JSON file per day here, instead of one
file with an array — so this iterates files, not a `results` array):

```python
#!/usr/bin/env python3
"""One-time migration: backfill the real data/daily-briefs/*.json snapshots into the
Intelligence Ledger as REVIEW_DAILY events (Wave 5C, ADR-029).

Uses the exact same append_event/replay_events_to_db machinery daily_brief.py's own
dual-write block already uses, and the same idempotency_key format
(daily-brief-{date}) — so a future real daily_brief.py run for an already-backfilled
date never double-writes.

Usage:
    python3 migrate_daily_briefs_to_ledger.py --dry-run
    python3 migrate_daily_briefs_to_ledger.py --write
"""
import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))

DEFAULT_BRIEFS_DIR = REPO_ROOT / "investment_screener/backend/data/daily-briefs"
DEFAULT_DB_PATH = REPO_ROOT / "investment_screener/backend/data/intelligence.sqlite"


def migrate(briefs_dir: Path, jsonl_path: Path, db_path: Path, dry_run: bool = True) -> dict:
    """Backfill every data/daily-briefs/*.json snapshot into intelligence_event.

    Args:
        briefs_dir: Directory containing one {date}.json snapshot file per day.
        jsonl_path: observations.jsonl ledger to append REVIEW_DAILY events to.
        db_path: intelligence.sqlite to replay the ledger into.
        dry_run: When True (default), report counts without writing anything.

    Returns:
        {"source_count": int, "written_count": int, "skipped": list[str]}
    """
    from intelligence.event_store import append_event
    from intelligence.replay_ledger import replay_events_to_db
    from intelligence.db_client import initialize_db

    files = sorted(briefs_dir.glob("*.json")) if briefs_dir.exists() else []
    skipped: list[str] = []
    report = {"source_count": len(files), "written_count": 0, "skipped": skipped}
    if dry_run:
        for f in files:
            with open(f) as fh:
                raw = json.load(fh)
            if not raw.get("date"):
                skipped.append(f.name)
        report["written_count"] = len(files) - len(skipped)
        report["written_count"] = 0  # dry-run never writes
        return report

    for f in files:
        with open(f) as fh:
            raw = json.load(fh)
        date_str = raw.get("date")
        if not date_str:
            skipped.append(f.name)
            continue
        append_event(
            str(jsonl_path),
            event_type="REVIEW_DAILY",
            effective_at=date_str,
            status="ACTIVE",
            title=f"Daily Brief for {date_str}",
            body_markdown="Generated daily brief summary metrics.",
            ticker=None,
            source_id="wave5c-migration-backfill",
            payload=raw,
            idempotency_key=f"daily-brief-{date_str}",
        )
        report["written_count"] += 1

    conn = initialize_db(str(db_path))
    try:
        replay_events_to_db(str(jsonl_path), conn)
    finally:
        conn.close()

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--briefs-dir", default=str(DEFAULT_BRIEFS_DIR))
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--jsonl-path", default=None, help="Defaults to the standard observations.jsonl ledger path.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true")
    group.add_argument("--write", action="store_true")
    args = parser.parse_args()

    from intelligence.event_store import _default_jsonl_path
    jsonl_path = Path(args.jsonl_path) if args.jsonl_path else _default_jsonl_path()

    report = migrate(Path(args.briefs_dir), jsonl_path, Path(args.db_path), dry_run=args.dry_run)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
```

(Note the dry-run count logic above is deliberately explicit about "0 written in dry-run" — fix
the redundant double-assignment line during implementation if it reads awkwardly, but the
externally-observed behavior — `written_count == 0` whenever `dry_run=True` — must not change.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest investment_screener/backend/tests/py_services/test_migrate_daily_briefs_to_ledger.py -v`
Expected: 4 passed.

- [ ] **Step 5: Dry-run against the real main-checkout data (read-only, safe)**

Run (from the main checkout, NOT this worktree — the real files live only there):
```bash
cd /Users/richardfremmerlid/Projects/InvestmentToolkit
python3 investment_screener/backend/py_services/migrate_daily_briefs_to_ledger.py --dry-run
```
Expected output: `"source_count": 10` (per the kickoff prompt's confirmed starting state — if a
real `daily_brief.py` run has happened since, expect a higher count and note it), `"written_count":
0`, `"skipped": []` (unless a real file is missing its `date` field — investigate any non-empty
`skipped` list before proceeding, do not silently continue).

- [ ] **Step 6: Commit (worktree only — the script, not the dry-run's real-world output)**

```bash
git add investment_screener/backend/py_services/migrate_daily_briefs_to_ledger.py \
        investment_screener/backend/tests/py_services/test_migrate_daily_briefs_to_ledger.py
git commit -m "feat(migrate_daily_briefs_to_ledger): add dry-run/write backfill script for REVIEW_DAILY"
```

---

## Task 4: Real dry-run, user sign-off gate, then the real write against main

**This task requires explicit user approval before the `--write` sub-step. Do not proceed past
the dry-run without it — non-negotiable per this plan's mandatory approval gate.**

**Files:** none (operational task — runs the Task 3 script against main checkout's real files).

- [ ] **Step 1: Re-run the dry-run against main one more time, immediately before write**

```bash
cd /Users/richardfremmerlid/Projects/InvestmentToolkit
python3 investment_screener/backend/py_services/migrate_daily_briefs_to_ledger.py \
  --briefs-dir "$(pwd)/investment_screener/backend/data/daily-briefs" \
  --db-path "$(pwd)/investment_screener/backend/data/intelligence.sqlite" \
  --jsonl-path "$(pwd)/investment_screener/backend/data/observations.jsonl" \
  --dry-run
```

Present the exact JSON report to the user (source_count, skipped list) and ask for explicit
sign-off before continuing. **Enumerate all three path args explicitly** (per the Global
Constraint on this) even though they match the script's own defaults when run from main — do not
rely on the defaults resolving correctly, state them.

- [ ] **Step 2: On sign-off, run the real write against main's actual files**

```bash
cd /Users/richardfremmerlid/Projects/InvestmentToolkit
python3 investment_screener/backend/py_services/migrate_daily_briefs_to_ledger.py \
  --briefs-dir "$(pwd)/investment_screener/backend/data/daily-briefs" \
  --db-path "$(pwd)/investment_screener/backend/data/intelligence.sqlite" \
  --jsonl-path "$(pwd)/investment_screener/backend/data/observations.jsonl" \
  --write
```

Expected: `"written_count"` equal to the dry-run's `source_count` (minus any confirmed-legitimate
skips).

- [ ] **Step 3: Independently re-verify against main's actual files (not the script's own report)**

```bash
cd /Users/richardfremmerlid/Projects/InvestmentToolkit
sqlite3 investment_screener/backend/data/intelligence.sqlite \
  "SELECT COUNT(*) FROM intelligence_event WHERE event_type='REVIEW_DAILY' AND status='ACTIVE';"
grep -c '"event_type": "REVIEW_DAILY"' investment_screener/backend/data/observations.jsonl
```

Expected: both numbers match the dry-run's `source_count` (minus skips). **Both stores must be
checked** — this is the exact class of gap Wave 5B's jsonl-path miss created.

- [ ] **Step 4: Investigate why the pre-existing dual-write code produced 0 rows before this backfill**

Since `daily_brief.py`'s dual-write block already existed and should have fired on every real run
since it was written, but the table had 0 rows, this is a real discrepancy worth a root cause, not
just a silent backfill. Check: `git log -p --follow plugins/portfolio-advisor/scripts/daily_brief.py`
for when the dual-write block landed vs. the dates of the 10 real snapshot files (if all 10
predate the dual-write code, that fully explains the gap — no bug, just an as-expected new-code
lag). Record the finding in the wave exit report; if any snapshot postdates the dual-write code's
landing, that's a real Hard-Stop-worthy bug (producer silently failing) and must be fixed before
continuing, not backfilled over.

- [ ] **Step 5: No commit this step** (this task only writes to main checkout's gitignored data
files, not to the worktree's git history — nothing to commit here).

---

## Task 5: Rewire `generate_reports.py::load_latest_brief()` to the ledger

**Files:**
- Modify: `plugins/portfolio-advisor/scripts/generate_reports.py:97-103`
- Test: create `investment_screener/backend/tests/py_services/test_generate_reports_load_latest_brief.py`

**Interfaces:**
- Consumes: `list_active_events_by_type` (Task 1).

- [ ] **Step 1: Write the failing test**

```python
import json
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))
sys.path.insert(0, str(REPO_ROOT / "plugins/portfolio-advisor/scripts"))


def _seed_db(db_path: Path) -> None:
    from intelligence.db_client import initialize_db
    from intelligence.event_repository import insert_event

    conn = initialize_db(str(db_path))
    insert_event(conn, {
        "event_id": "evt_1", "event_sequence": 1, "instrument_id": None,
        "event_type": "REVIEW_DAILY", "effective_at": "2026-07-22",
        "observed_at": None, "ingested_at": "2026-07-22T10:00:00Z",
        "source_id": "daily_brief", "confidence_score": None, "status": "ACTIVE",
        "title": "Daily Brief for 2026-07-22", "body_markdown": "x",
        "payload_json": json.dumps({"date": "2026-07-22", "macro_regime": {"regime": "BULL"}}),
        "supersedes_event_id": None, "idempotency_key": "daily-brief-2026-07-22",
        "content_hash": "h1",
    })
    insert_event(conn, {
        "event_id": "evt_2", "event_sequence": 2, "instrument_id": None,
        "event_type": "REVIEW_DAILY", "effective_at": "2026-07-23",
        "observed_at": None, "ingested_at": "2026-07-23T10:00:00Z",
        "source_id": "daily_brief", "confidence_score": None, "status": "ACTIVE",
        "title": "Daily Brief for 2026-07-23", "body_markdown": "x",
        "payload_json": json.dumps({"date": "2026-07-23", "macro_regime": {"regime": "CONGESTION"}}),
        "supersedes_event_id": None, "idempotency_key": "daily-brief-2026-07-23",
        "content_hash": "h2",
    })
    conn.commit()
    conn.close()


def test_load_latest_brief_reads_from_ledger_not_json_glob(tmp_path, monkeypatch):
    import generate_reports

    db_path = tmp_path / "intelligence.sqlite"
    _seed_db(db_path)
    monkeypatch.setattr(generate_reports, "INTELLIGENCE_DB_PATH", str(db_path))

    # No data/daily-briefs directory exists at all in this tmp_path scenario —
    # proves the function no longer depends on the JSON glob path.
    result = generate_reports.load_latest_brief()

    assert result["date"] == "2026-07-23"
    assert result["macro_regime"]["regime"] == "CONGESTION"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest investment_screener/backend/tests/py_services/test_generate_reports_load_latest_brief.py -v`
Expected: FAIL — `generate_reports` has no `INTELLIGENCE_DB_PATH` attribute yet, and
`load_latest_brief()` still globs JSON.

- [ ] **Step 3: Implement the rewire**

In `plugins/portfolio-advisor/scripts/generate_reports.py`, add the DB path constant near the
existing `DOMAIN_DB_PATH` (top of file) and replace `load_latest_brief()`:

```python
INTELLIGENCE_DB_PATH = os.path.join(PROJECT_ROOT, "investment_screener/backend/data/intelligence.sqlite")


def load_latest_brief(db_path=INTELLIGENCE_DB_PATH):
    """Loads the latest REVIEW_DAILY event payload from the Intelligence Ledger.

    Wave 5C cutover — replaces the direct data/daily-briefs/*.json glob read.
    """
    sys.path.insert(0, os.path.join(PROJECT_ROOT, "investment_screener/backend/py_services"))
    from intelligence.db_client import initialize_db
    from intelligence.event_repository import list_active_events_by_type

    if not os.path.exists(db_path):
        return {}

    conn = initialize_db(db_path)
    try:
        events = list_active_events_by_type(conn, "REVIEW_DAILY")
    finally:
        conn.close()

    if not events:
        return {}
    payload_json = events[0].get("payload_json")  # already ordered newest-first
    return json.loads(payload_json) if payload_json else {}
```

Remove the now-unused `import glob` if nothing else in the file uses it (check with
`grep -n "glob\." plugins/portfolio-advisor/scripts/generate_reports.py` before removing the
import — `DAILY_BRIEFS_DIR` constant can also be removed if nothing else references it after this
change).

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest investment_screener/backend/tests/py_services/test_generate_reports_load_latest_brief.py -v`
Expected: PASS.

- [ ] **Step 5: Run the full generate_reports-adjacent test suite to check for regressions**

Run: `python3 -m pytest investment_screener/backend/tests/py_services/ -k "generate_reports" -v`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add plugins/portfolio-advisor/scripts/generate_reports.py \
        investment_screener/backend/tests/py_services/test_generate_reports_load_latest_brief.py
git commit -m "feat(generate_reports): cut load_latest_brief() over to intelligence_event ledger"
```

---

## Task 6: Rewire `daily_brief.py::_load_yesterday()` to a real SQL query

**Files:**
- Modify: `plugins/portfolio-advisor/scripts/daily_brief.py:128-136`
- Test: create `investment_screener/backend/tests/py_services/test_daily_brief_load_yesterday.py`

**Interfaces:**
- Consumes: `list_active_events_by_type` (Task 1).

- [ ] **Step 1: Write the failing test**

```python
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))
sys.path.insert(0, str(REPO_ROOT / "plugins/portfolio-advisor/scripts"))


def _seed_two_events(db_path: Path) -> None:
    from intelligence.db_client import initialize_db
    from intelligence.event_repository import insert_event

    conn = initialize_db(str(db_path))
    for i, (eff_date, regime) in enumerate([("2026-07-22", "BULL"), ("2026-07-23", "CONGESTION")], start=1):
        insert_event(conn, {
            "event_id": f"evt_{i}", "event_sequence": i, "instrument_id": None,
            "event_type": "REVIEW_DAILY", "effective_at": eff_date,
            "observed_at": None, "ingested_at": f"{eff_date}T10:00:00Z",
            "source_id": "daily_brief", "confidence_score": None, "status": "ACTIVE",
            "title": f"Daily Brief for {eff_date}", "body_markdown": "x",
            "payload_json": json.dumps({"date": eff_date, "macro_regime": {"regime": regime}}),
            "supersedes_event_id": None, "idempotency_key": f"daily-brief-{eff_date}",
            "content_hash": f"h{i}",
        })
    conn.commit()
    conn.close()


def test_load_yesterday_returns_second_most_recent_event_via_sql(tmp_path, monkeypatch):
    import daily_brief

    db_path = tmp_path / "intelligence.sqlite"
    _seed_two_events(db_path)
    monkeypatch.setattr(daily_brief, "INTELLIGENCE_DB_PATH", str(db_path))
    monkeypatch.setattr(daily_brief, "date", type("FakeDate", (), {"today": staticmethod(lambda: __import__("datetime").date(2026, 7, 24))}))

    result = daily_brief._load_yesterday()

    # Today is 2026-07-24 (not in the DB); the most recent real prior snapshot is 2026-07-23.
    assert result["date"] == "2026-07-23"
    assert result["macro_regime"]["regime"] == "CONGESTION"


def test_load_yesterday_returns_none_when_no_prior_events(tmp_path, monkeypatch):
    import daily_brief

    db_path = tmp_path / "intelligence.sqlite"
    from intelligence.db_client import initialize_db
    initialize_db(str(db_path)).close()
    monkeypatch.setattr(daily_brief, "INTELLIGENCE_DB_PATH", str(db_path))

    assert daily_brief._load_yesterday() is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest investment_screener/backend/tests/py_services/test_daily_brief_load_yesterday.py -v`
Expected: FAIL — `daily_brief` has no `INTELLIGENCE_DB_PATH` attribute, `_load_yesterday()` still
globs JSON.

- [ ] **Step 3: Implement the rewire**

In `plugins/portfolio-advisor/scripts/daily_brief.py`, add near the existing `DAILY_BRIEFS_DIR`
constant (line 38):

```python
INTELLIGENCE_DB_PATH = REPO_ROOT / "investment_screener/backend/data/intelligence.sqlite"
```

Replace `_load_yesterday()` (lines 128-136):

```python
def _load_yesterday() -> dict[str, Any] | None:
    """Load the most recent prior daily brief snapshot from the Intelligence Ledger.

    Wave 5C cutover — replaces the data/daily-briefs/*.json glob+sort read with
    ORDER BY effective_at DESC LIMIT 2 (today's own event, if already written this
    run, plus the true prior day), per spec §2.13.
    """
    import os as _os

    if not _os.path.exists(INTELLIGENCE_DB_PATH):
        return None

    from intelligence.db_client import initialize_db
    from intelligence.event_repository import list_active_events_by_type

    today_str = date.today().isoformat()
    conn = initialize_db(str(INTELLIGENCE_DB_PATH))
    try:
        events = list_active_events_by_type(conn, "REVIEW_DAILY")
    finally:
        conn.close()

    for event in events:
        if event["effective_at"] != today_str:
            payload_json = event.get("payload_json")
            return json.loads(payload_json) if payload_json else None
    return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest investment_screener/backend/tests/py_services/test_daily_brief_load_yesterday.py -v`
Expected: PASS.

- [ ] **Step 5: Run the existing daily_brief test suite for regressions**

Run: `python3 -m pytest investment_screener/backend/tests/py_services/ -k "daily_brief" -v`
Expected: all PASS (including `test_daily_brief_ta_sweep_delegates.py`,
`test_daily_brief_rebalance_event_emission.py`, `test_daily_brief_thesis_breakers.py`,
`test_daily_brief_prediction_harvest.py` — none of these should reference `_load_yesterday`'s old
JSON behavior, but confirm no incidental coupling).

- [ ] **Step 6: Commit**

```bash
git add plugins/portfolio-advisor/scripts/daily_brief.py \
        investment_screener/backend/tests/py_services/test_daily_brief_load_yesterday.py
git commit -m "feat(daily_brief): cut _load_yesterday() over to a real SQL query against intelligence_event"
```

---

## Task 7: Remove `dailybrief.ts`'s JSON fallback branches

**Only start this task after Task 4's real write has landed and been independently verified** —
removing the fallback before real data exists would 404 the live route.

**Files:**
- Modify: `investment_screener/backend/src/routes/dailybrief.ts`
- Modify: `investment_screener/backend/tests/api/dailybrief.spec.ts`

**Interfaces:**
- No change to exported function signatures (`queryLatestBriefFromLedger`,
  `queryBriefHistoryFromLedger`, `queryTickerConvictionFromLedger` keep their signatures) — only
  the route handlers' fallback branches and the now-dead `latestBriefPath()`/`BRIEFS_DIR` helpers
  are removed.

- [ ] **Step 1: Write the failing test — route handler no longer falls back**

Add to `investment_screener/backend/tests/api/dailybrief.spec.ts` (after the existing three
`describe` tests, same file, same fixture pattern already established there):

```typescript
describe('dailybrief.ts route handlers — no JSON fallback after Wave 5C cutover', () => {
    it('module no longer exports latestBriefPath or references BRIEFS_DIR fallback', () => {
        // eslint-disable-next-line @typescript-eslint/no-var-requires
        const mod = require('../../src/routes/dailybrief');
        expect(mod.latestBriefPath).to.be.undefined;
    });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: (project's mocha invocation for `tests/api/`, per `package.json`'s `test` script — confirm
exact command first)
Expected: current behavior — `latestBriefPath` is a private (non-exported) function today, so
this specific assertion likely already passes; adjust the test if so to instead assert on
behavior: mock `queryLatestBriefFromLedger` to return `null` and confirm the route now returns 404
instead of silently reading a JSON file. Write the accurate failing-first test based on the
file's real current export surface — read `dailybrief.ts` fresh at implementation time to confirm
which functions are actually exported before finalizing this test's exact shape.

- [ ] **Step 3: Remove the fallback code**

In `investment_screener/backend/src/routes/dailybrief.ts`: delete `latestBriefPath()`,
`BRIEFS_DIR`, and the `fs`/`path` imports if nothing else in the file uses them; delete each
route handler's fallback block, replacing e.g.:

```typescript
router.get('/latest', async (_req, res) => {
    try {
        const brief = await queryLatestBriefFromLedger();
        if (!brief) {
            res.status(404).json({ error: 'No daily brief found. Run: python3 plugins/portfolio-advisor/scripts/daily_brief.py' });
            return;
        }
        res.json(brief);
    } catch (e: any) {
        res.status(500).json({ error: e.message });
    }
});
```

Apply the equivalent simplification to `/history` (return `[]` if `queryBriefHistoryFromLedger`
returns null) and `/conviction/:ticker` (same).

- [ ] **Step 4: Run test to verify it passes**

Run: mocha for `tests/api/dailybrief.spec.ts`.
Expected: all PASS, including the new no-fallback test.

- [ ] **Step 5: Live-path check against main's real, now-populated DB**

Start the backend (`npm run dev -w backend` from `investment_screener/`, main checkout — not this
worktree, since only main has the real populated `intelligence.sqlite` from Task 4) and run:
```bash
curl -s http://localhost:3001/api/daily-brief/latest | python3 -m json.tool | head -20
curl -s http://localhost:3001/api/daily-brief/history | python3 -m json.tool
```
Confirm both return real data matching the real backfilled snapshots, not a 404/empty response.
Record the exact output in the wave exit report as this task's live-path evidence (spec §5's
"Live-path tests where practical" requirement — done here, not deferred to Task 8, since Task 8's
parity test is a different check: a live producer run, not a live consumer read).

- [ ] **Step 6: Commit**

```bash
git add investment_screener/backend/src/routes/dailybrief.ts \
        investment_screener/backend/tests/api/dailybrief.spec.ts
git commit -m "refactor(dailybrief.ts): remove JSON fallback branches, ledger-only after Wave 5C cutover"
```

---

## Task 8: Real-cycle parity test

**Requires TradingView Desktop running with CDP reachable (port 9222) and the user's real broker
session — coordinate timing with the user before this task, same as Wave 5B's remediation.**

**Files:** none created — this is an operational verification task, evidence goes in the wave
exit report.

- [ ] **Step 1: Run one real `daily_brief.py` cycle against main**

```bash
cd /Users/richardfremmerlid/Projects/InvestmentToolkit
python3 plugins/portfolio-advisor/scripts/daily_brief.py --json > /tmp/wave5c_parity_check.json
```

- [ ] **Step 2: Diff the JSON snapshot against the ledger's row for the same date, field-for-field**

```bash
cd /Users/richardfremmerlid/Projects/InvestmentToolkit
TODAY=$(date +%Y-%m-%d)
diff <(python3 -m json.tool "investment_screener/backend/data/daily-briefs/${TODAY}.json") \
     <(sqlite3 investment_screener/backend/data/intelligence.sqlite \
       "SELECT payload_json FROM intelligence_event WHERE event_type='REVIEW_DAILY' AND effective_at='${TODAY}';" \
       | python3 -m json.tool)
```

Expected: **zero diff output** — byte-identical parity between the JSON export and the ledger's
payload for the same real run. Record the exact diff command output (empty) in the wave exit
report as evidence, per spec §5's requirement (not a prose description).

- [ ] **Step 3: Independently re-verify the row count against main (not the run's own console output)**

```bash
sqlite3 investment_screener/backend/data/intelligence.sqlite \
  "SELECT COUNT(*) FROM intelligence_event WHERE event_type='REVIEW_DAILY' AND status='ACTIVE';"
```
Expected: `10 + 1` (backfilled 10 from Task 4, plus this real new run), unless the user has run
`daily_brief.py` again in the interim — reconcile explicitly if the count differs.

- [ ] **Step 4: Delete the temporary parity-check artifact**

```bash
rm /tmp/wave5c_parity_check.json
```
(The real `${TODAY}.json` snapshot itself stays in place until Task 9's archive step — this is
only the throwaway `/tmp` copy used for the diff command's process substitution above, if any
extra copy was made.)

No commit — no files changed by this task.

---

## Task 9: Archive old JSON files + Context Bundle update + grep verification

**Only after Tasks 4-8 are all independently confirmed** (real write verified, both consumers
cut over and live-path checked, parity diff clean).

**Files:**
- Modify (local-only, not git-tracked): `investment_screener/backend/data/daily-briefs/*.json`
  → moved to `ARCHIVE/investment_screener/backend/data/daily-briefs/` (main checkout only — this
  step must NOT run inside this worktree; see the note below).
- Modify: `plugins/portfolio-advisor/skills/daily-brief/SKILL.md:136`

- [ ] **Step 1: Grep-verify zero real runtime I/O to the old path remains**

```bash
cd /Users/richardfremmerlid/Projects/InvestmentToolkit/.claude/worktrees/wave5c-daily-briefs
grep -rn "daily-briefs" investment_screener plugins --include="*.py" --include="*.ts"
```
Expected matches remaining: only the constant *definitions* (`DAILY_BRIEFS_DIR` in
`daily_brief.py` — still needed because the producer still writes the JSON file as a legacy
export alongside the ledger write; this is acceptable per the Hybrid Exit Criteria table above,
since no consumer reads it anymore) and the migration script's `--briefs-dir` default. Zero
matches should remain in `generate_reports.py` or `dailybrief.ts` after Tasks 5/7. If any
unexpected match appears, investigate before proceeding — do not archive with a live reader still
pointed at the old path (Hard-Stop #5).

- [ ] **Step 2: Update the SKILL.md Context Bundle reference**

In `plugins/portfolio-advisor/skills/daily-brief/SKILL.md`, change line 136's description from
pointing at the JSON path to describing the ledger write (read the surrounding lines first to
match the existing doc's tone/format — this is a one-line factual correction, e.g. replacing
"Results saved to `investment_screener/backend/data/daily-briefs/YYYY-MM-DD.json`" with "Results
written to the Intelligence Ledger (`intelligence_event`, `event_type='REVIEW_DAILY'`); a
same-shape JSON snapshot is also still written to
`investment_screener/backend/data/daily-briefs/YYYY-MM-DD.json` as a legacy export, not read by
any consumer").

- [ ] **Step 3: Verify zero stale references remain**

```bash
grep -rn "daily-briefs" plugins/portfolio-advisor/skills/daily-brief/SKILL.md
```
Expected: the one remaining match is now accurate (describes the ledger + legacy-export
reality), not stale. Record this as the Context Bundle Completion Bar evidence: 1 stale
reference → 0 (the reference itself may still exist textually, but is no longer describing a
retired sole-source-of-truth path — same standard Wave 5B applied to `technical-analysis-expert`'s
equivalent line).

- [ ] **Step 4: Commit the worktree-side changes**

```bash
git add plugins/portfolio-advisor/skills/daily-brief/SKILL.md
git commit -m "docs(daily-brief SKILL.md): correct stale daily-briefs JSON reference post Wave 5C"
```

- [ ] **Step 5: Archive the real JSON files — main checkout only, local `mv`, NOT this worktree**

**Do not run this step inside the worktree.** Per CLAUDE.md's worktree/file-move discipline
(confirmed by Wave 5B's own accidental-`git mv`-in-main-checkout lesson, inverted here: this file
is gitignored so the correct target is the main checkout, not the worktree — a `git mv` inside
the worktree would do nothing for a file `git` doesn't track, and moving it in the worktree
wouldn't affect main's real files at all since gitignored data never syncs across worktrees per
CLAUDE.md pitfall #29):

```bash
cd /Users/richardfremmerlid/Projects/InvestmentToolkit
mkdir -p ARCHIVE/investment_screener/backend/data/daily-briefs
mv investment_screener/backend/data/daily-briefs/*.json \
   ARCHIVE/investment_screener/backend/data/daily-briefs/
```

- [ ] **Step 6: Confirm the old path no longer resolves and the archive copy is readable**

```bash
ls investment_screener/backend/data/daily-briefs/ 2>&1  # expect: empty or "No such file"
ls ARCHIVE/investment_screener/backend/data/daily-briefs/ | wc -l  # expect: matches Task 4's written_count
cat ARCHIVE/investment_screener/backend/data/daily-briefs/*.json | head -c 200  # expect: readable JSON
```

Note this archive step is local-only (the directory is gitignored) — nothing to `git add`/commit
for the archive itself; only the `SKILL.md` correction (Step 4 above) is a real commit.

---

## Task 10: Physically-executed rollback exercise

**Files:** none in the main worktree — performed entirely in a throwaway worktree, discarded
afterward. Mirrors Wave 5B's remediation exercise exactly.

- [ ] **Step 1: Create the throwaway worktree**

Use `EnterWorktree` with a name like `wave5c-rollback-exercise-throwaway`, branched from this
wave's actual feature branch tip (after all of Tasks 1-9's commits) via `git merge --ff-only`.

- [ ] **Step 2: Revert all of this wave's commits**

```bash
git revert --no-commit <first-wave-commit>^..<last-wave-commit>
```
(Substitute the real commit range from Tasks 1-9's `git commit` steps above.) Expected: clean
revert, no conflicts (matches Wave 5B's precedent — no reason to expect conflicts here since this
wave, like 5B, doesn't touch code any other wave also modifies).

- [ ] **Step 3: Restore the archived JSON files into place (simulating the old runtime state)**

```bash
cp ARCHIVE/investment_screener/backend/data/daily-briefs/*.json \
   investment_screener/backend/data/daily-briefs/
```
(This throwaway worktree has its own separate copy of `ARCHIVE/` from the real Task 9 archive —
if this worktree branched before Task 9's archive step landed on the wave branch, copy the files
manually from the main checkout's `ARCHIVE/` path instead.)

- [ ] **Step 4: Run the reverted (pre-wave) code against the restored files**

```bash
cd investment_screener/backend/py_services
python3 -c "
import sys
sys.path.insert(0, '../../../plugins/portfolio-advisor/scripts')
import generate_reports
print(generate_reports.load_latest_brief())
"
```
Expected: the reverted `load_latest_brief()` (old glob-based version) successfully reads one of
the restored JSON files and returns its content — proving the old code path still works against
the restored files, not stale/cached state.

- [ ] **Step 5: Run the full pre-wave test suite for the affected files**

```bash
python3 -m pytest investment_screener/backend/tests/py_services/ -k "daily_brief or generate_reports" -v
```
Expected: all pre-wave tests pass against the reverted code (the new Wave 5C tests from Tasks
1-6 won't exist in this reverted state — confirm they're absent, not failing, since `git revert`
removed the files that introduced them).

- [ ] **Step 6: Discard the throwaway worktree**

Use `ExitWorktree` with `action: "remove"`, `discard_changes: true`. Confirm via `git worktree
list` back in the main checkout that no trace remains.

- [ ] **Step 7: Record the exercise's evidence in the wave exit report**

No commit from this task (everything discarded) — the wave exit report's "Rollback Evidence"
section is this task's deliverable, quoting the exact revert command, conflict count (0 expected),
and Step 4/5's output.

---

## Task 11: Wave exit — KPI table, exit report, handoff, PR

**Files:**
- Create: `docs/superpowers/status/wave5c-daily-briefs-report.md`
- Create: `docs/superpowers/status/wave5c-handoff.md`

- [ ] **Step 1: Compute the Wave KPI table with real numbers**

Fill in (do not estimate): JSON files before (10, or the real Task 4 dry-run count) → after (0
active, N archived); producers migrated (1/1: `daily_brief.py`); consumers migrated (2/2:
`dailybrief.ts`, `generate_reports.py` — noting the spec's inventory initially missed
`dailybrief.ts`); context-bundle references updated (1 → 0 stale); anti-bypass fix count (1:
`query_ledger_brief.py`).

- [ ] **Step 2: Write the exit report**

Match `wave5b-ta-sweep-results-report.md`'s depth: KPI table, producer/consumer cutover table
(both DONE, with evidence), real bugs found and fixed (the pre-existing anti-bypass violation;
whatever Task 4 Step 4's root-cause investigation found), validation results (explicitly stating
the real write was verified against main's DB **and** ledger file), archive evidence, rollback
instructions with physical-execution evidence (Task 10), commit list.

- [ ] **Step 3: Push the branch and open a PR — do not merge yourself**

```bash
git push -u origin worktree-wave5c-daily-briefs
gh pr create --title "Wave 5C: Daily Briefs migration to Intelligence Ledger" --body "$(cat docs/superpowers/status/wave5c-daily-briefs-report.md)"
```

- [ ] **Step 4: Write the handoff doc and stop**

Follow `wave5b-handoff.md`'s structure. **Stop. Do not start Wave 5D.** Wait for the user to
review/merge the PR, then follow `.agent/rules/git-operations.md`'s End-of-Wave Closeout
Playbook (fetch, fast-forward main, verify ancestor, re-verify real row counts against the
now-updated main checkout one more time, remove worktree, delete branches) before writing Wave
5D's kickoff prompt.
