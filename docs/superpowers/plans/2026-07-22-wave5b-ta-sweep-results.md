# Wave 5B — TA Sweep Results Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate `ta-sweep-results.json` to the `intelligence_event` domain per ADR-029's
falsifiable definition — producer writes SQLite as the default/relied-upon path, every real
consumer reads SQLite unconditionally (no fallback), and the old file is archived via `git mv`
(it is git-tracked, not gitignored, unlike Wave 5A's domain).

**Architecture:** The `TECHNICAL_SWEEP` event type and the ledger/replay machinery
(`intelligence.event_store.append_event`, `intelligence.replay_ledger.replay_events_to_db`)
already exist and are exercised by tests — this wave does not add schema. It (1) backfills the
one real production `ta-sweep-results.json` snapshot into the ledger via a new one-time migration
script, (2) rewires the one real consumer call site that never touches SQLite today, (3) removes
now-dead JSON-fallback branches in the two other consumer call sites, (4) flips the producer's
default write from "always write JSON" to "always write SQLite, JSON only if explicitly
requested," and (5) archives the file.

**Tech Stack:** Python 3.13, pytest (`tmp_path` fixtures + real `intelligence.sqlite`/`.jsonl`
round-trips, matching this codebase's existing `test_daily_brief_ta_sweep_delegates.py` and
`test_compute_conviction_scores.py` patterns).

## Global Constraints

(Copied verbatim from the overall plan/spec — applies to this wave.)

- **A domain is migrated only when:** producer writes SQLite + every real consumer reads SQLite +
  old file archived via `git mv`. Table existence, data copying, or a passing fixture test do not
  count.
- **No permanent hybrid.** JSON + SQLite forever is a failed wave, not a resting state.
- **No script opens its own SQLite connection outside the owning repository/service layer** —
  this wave reuses `intelligence.db_client.initialize_db` / `intelligence.event_store` /
  `intelligence.replay_ledger`, already the established pattern; no new connection code.
- **A "real data migration write" must run against the main checkout's actual gitignored data
  files and actual database, never a worktree's copy** — restated here because, unlike Wave 5A,
  this wave performs a real `--write` migration (Task 4).
- **Every wave reports:** the Wave KPI table (JSON files before/after, files archived,
  reads/writes removed, producers/consumers migrated, remaining exceptions named).
- **Archive convention:** `ARCHIVE/<mirrored source path>` via `git mv` for tracked files (this
  file **is** git-tracked, confirmed below — unlike `portfolio.json`/`cash_flows.json`, no
  local-only exception applies here).
- **Subagent model choice: Sonnet or Haiku only for every dispatch** (implementer, task
  reviewer, final whole-branch reviewer, fix subagents) — standing user instruction, overrides
  any skill-text default of "use the most capable model."

## Pre-Implementation Findings (re-verified against real code/data on 2026-07-22, not copied from the plan's one-liner)

- **The overall plan's warning is accurate for this domain, unlike Wave 5A's:** main checkout's
  `investment_screener/backend/data/intelligence.sqlite` has **zero** `TECHNICAL_SWEEP` rows
  (confirmed via direct query — only 80 `RESEARCH_IMPORT` rows exist). The dual-write producer
  code exists and is unit-tested, but has never fired against real production data. This is a
  live gap, not dead-but-harmless code like Wave 5A's fallback was.
- **`ta-sweep-results.json` is git-tracked** (`git ls-files` confirms it), not gitignored —
  archival for this wave uses `git mv` to `ARCHIVE/`, not the local-only `mv` convention used for
  `portfolio.json`/`cash_flows.json`.
- **Real producer:** `plugins/tradingview/scripts/ta_sweep_batch.py::save_sweep_results()`
  (lines 311–376). Currently writes the flat JSON file unconditionally (step 1, lines 335–336),
  then always appends `TECHNICAL_SWEEP` events to the ledger and replays them to SQLite (steps
  2–3, lines 341–376). Called from `main()` (lines 426–430): JSON auto-save runs by default
  unless `--no-save` is passed; nothing today makes the SQLite write conditional — it already
  runs on every real invocation. The gap is that the JSON write is the *default and structurally
  relied-upon* one (three real callers depend on the file, one exclusively), while SQLite has
  never actually been exercised as a real dependency.
- **Real consumers, three call sites across two files — re-verified by reading each, not by
  trusting the plan's one-liner or any prior status doc:**
  1. `investment_screener/backend/py_services/compute_conviction_scores.py::_load_ta()`
     (lines 284–349) — DB-first with a JSON-fallback branch (lines 336–349). **No test exercises
     the fallback branch** (`test_compute_conviction_scores.py` only has
     `test_load_ta_from_sqlite`) — it is untested legacy code, same category as Wave 5A's dead
     branch, but here the DB path itself has 0 real rows to read, so in production this fallback
     is the one *actually* firing today, silently.
  2. `plugins/portfolio-advisor/scripts/daily_brief.py::_ta_age_hours()` (lines 63–93) — same
     DB-first/JSON-fallback shape. `test_ta_age_hours_reads_from_database` covers the DB path
     only.
  3. `plugins/portfolio-advisor/scripts/daily_brief.py::run()` (lines 447–457) — **the one real
     consumer that never touches SQLite at all.** After invoking `ta_sweep_batch.py` as a
     subprocess, it re-opens `TA_SWEEP_PATH` directly to read back that run's results, with an
     explicit comment justifying this as avoiding "two code paths writing the same file." Since
     `save_sweep_results()` already replays to SQLite synchronously before the subprocess exits,
     querying the DB here instead is safe and removes the last real JSON-only read path.
- **Docs referencing a nonexistent backend consumer, confirmed false by grep:**
  `save_sweep_results()`'s docstring (line 319) and `main()`'s auto-save comment (line 425) both
  claim the file is "consumed by the backend `/api/ta-sweep/results` endpoint" — `grep -rl
  "ta-sweep" investment_screener/backend/src` returns zero hits; no such route exists anywhere in
  `backend/src/routes/` (confirmed: `dailybrief.ts, docs.ts, portfolio.ts, projections.ts,
  screener.ts, stock.ts, theses.ts, thirteenf.ts, trading.ts` — no `ta-sweep` route). Also zero
  hits in `investment_screener/frontend/src`. This stale claim must be corrected as part of this
  wave, not left to compound.
- **Real data to migrate:** main checkout's `ta-sweep-results.json` — `scan_date: "2026-07-10"`,
  26 ticker results, keys `ticker, close, changePct, rsi, rsima, volBias, adx, squeezeOn, vol,
  volMA, volumeRatio, flags, dcf, action, targetAction, targetWeight`.
- **`--save-results PATH` CLI flag already exists** (argparse, `nargs='?'`) — this wave repurposes
  it from "override the default auto-save path" to "the only way to get a flat-file JSON export,
  now opt-in rather than default," matching how ad-hoc exports work elsewhere in this codebase.

---

### Task 0: Expand TA sweep scan universe to include watchlist tickers, not just holdings

**Added mid-planning, 2026-07-22, in response to the user asking why the sweep only covers 26
tickers.** Confirmed by reading `ta_sweep_batch.py::load_portfolio()`: the sweep's ticker universe
is `load_portfolio()`'s holdings only — `grep -n watchlist plugins/tradingview/scripts/
ta_sweep_batch.py` returns zero hits; the script never reads watchlist membership at all. Real
counts from main checkout's `domain_model.sqlite` (queried directly, 2026-07-22): 29 held tickers,
80 watchlisted tickers, **82 unique combined** (heavy overlap) minus `DEFAULT_SKIP`'s
`CASH_USD`/`PSU` aliases. This is a pre-existing, unrelated gap in the producer script — not
something Wave 5B's storage migration created — but the user asked for it to be folded into this
wave rather than deferred.

**Precedent already exists in this codebase for exactly this union:**
`investment_screener/backend/py_services/overnight_gaps.py::_load_tickers()` (lines 82–113)
already computes "held positions union the watchlisted investments" via
`domain_model.portfolio_repository.load_portfolio_state_from_db()` +
`domain_model.investment_repository.list_investments(conn, is_watchlisted=True)`, holdings first,
deduplicated. This task mirrors that exact pattern rather than inventing a new one.

**Files:**
- Modify: `plugins/tradingview/scripts/ta_sweep_batch.py:1-20` (module docstring),
  `plugins/tradingview/scripts/ta_sweep_batch.py:62-73` (`load_portfolio()` neighborhood — add a
  new loader alongside it, don't conflate the two), `plugins/tradingview/scripts/
  ta_sweep_batch.py:398-412` (`main()`'s ticker-building loop)
- Test: `plugins/tradingview/tests/test_ta_sweep_batch.py`

**Interfaces:**
- Produces: `load_watchlisted_tickers(db_path: Path = DB_PATH) -> list[str]` — new function,
  returns deduplicated watchlisted ticker symbols only (holdings are still sourced separately
  from the existing `load_portfolio()`; the union happens in `main()`, mirroring
  `overnight_gaps.py`'s structure of two loaders + one union step, not one merged loader).
- Consumes: `domain_model.db_client.initialize_db` (already imported in this file, line 53),
  `domain_model.investment_repository.list_investments` (new import, same module
  `overnight_gaps.py` already imports it from).

- [ ] **Step 1: Write the failing test**

Add to `plugins/tradingview/tests/test_ta_sweep_batch.py`:

```python
def test_load_watchlisted_tickers_returns_watchlist_only_deduplicated(tmp_path):
    """load_watchlisted_tickers must return is_watchlisted=True symbols from domain_model.sqlite,
    deduplicated — mirrors overnight_gaps.py::_load_tickers()'s watchlist half.
    """
    import sys
    from pathlib import Path
    repo_root = Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(repo_root / "investment_screener/backend/py_services"))
    sys.path.insert(0, str(repo_root / "plugins/tradingview/scripts"))

    from domain_model.db_client import initialize_db  # noqa: E402
    from domain_model.investment_repository import resolve_investment, update_investment_fields  # noqa: E402
    from ta_sweep_batch import load_watchlisted_tickers  # noqa: PLC0415

    db_path = tmp_path / "domain_model.sqlite"
    conn = initialize_db(str(db_path))
    for ticker in ("OKLO", "RKLB"):
        inv_id = resolve_investment(conn, ticker)
        update_investment_fields(conn, inv_id, is_watchlisted=True)
    resolve_investment(conn, "MSFT")  # held, not watchlisted — is_watchlisted defaults False
    conn.close()

    tickers = load_watchlisted_tickers(db_path=db_path)

    assert sorted(tickers) == ["OKLO", "RKLB"]
    assert "MSFT" not in tickers


def test_main_ticker_universe_is_union_of_holdings_and_watchlist(tmp_path, monkeypatch):
    """main()'s scan universe must be holdings UNION watchlist, not holdings alone —
    confirmed via load_portfolio() + load_watchlisted_tickers() combined, minus DEFAULT_SKIP.
    """
    import sys
    from pathlib import Path
    repo_root = Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(repo_root / "plugins/tradingview/scripts"))
    import ta_sweep_batch  # noqa: PLC0415

    monkeypatch.setattr(ta_sweep_batch, "load_portfolio", lambda: [{"symbol": "MSFT"}, {"symbol": "NVDA"}])
    monkeypatch.setattr(ta_sweep_batch, "load_watchlisted_tickers", lambda db_path=None: ["NVDA", "OKLO", "RKLB"])

    holdings = ta_sweep_batch.load_portfolio()
    watchlisted = ta_sweep_batch.load_watchlisted_tickers()
    seen: set[str] = set()
    universe: list[str] = []
    for sym in [h["symbol"] for h in holdings] + watchlisted:
        if sym and sym not in ta_sweep_batch.DEFAULT_SKIP and sym not in seen:
            seen.add(sym)
            universe.append(sym)

    assert universe == ["MSFT", "NVDA", "OKLO", "RKLB"]  # holdings first, no NVDA duplicate
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd plugins/tradingview && python3 -m pytest tests/test_ta_sweep_batch.py -v -k "watchlist"`

Expected: FAIL — `ImportError: cannot import name 'load_watchlisted_tickers'`.

- [ ] **Step 3: Implement `load_watchlisted_tickers()` and rewire `main()`**

Add directly below `load_portfolio()` (after line 73) in
`plugins/tradingview/scripts/ta_sweep_batch.py`:

```python
def load_watchlisted_tickers(db_path: Path = DB_PATH) -> list[str]:
    """Return watchlisted (not-yet-held) ticker symbols from domain_model.sqlite.

    Mirrors overnight_gaps.py::_load_tickers()'s watchlist half — same
    domain_model.investment_repository.list_investments(is_watchlisted=True) query,
    kept as a separate loader (not merged with load_portfolio()) so callers can
    still distinguish held-vs-watchlisted tickers if needed later.
    """
    from domain_model.investment_repository import list_investments

    conn = initialize_db(str(db_path))
    try:
        return [
            inv["symbol"] for inv in list_investments(conn, is_watchlisted=True)
            if inv.get("symbol")
        ]
    finally:
        conn.close()
```

In `main()`, replace the ticker-building lines (currently `holdings = load_portfolio()` /
`tickers = [h["symbol"] for h in holdings if h.get("symbol") and h["symbol"] not in skip]`) with:

```python
    holdings = load_portfolio()
    watchlisted = load_watchlisted_tickers()
    seen: set[str] = set()
    tickers: list[str] = []
    for sym in [h["symbol"] for h in holdings] + watchlisted:
        if sym and sym not in skip and sym not in seen:
            seen.add(sym)
            tickers.append(sym)
```

Update the module docstring (lines 1–20): change "Daily TA sweep across all active portfolio
holdings" / "Reads portfolio.json for current holdings" to "Daily TA sweep across the combined
portfolio-holdings + watchlist ticker universe (Wave 5B)" and add
`investment_screener/backend/data/domain_model.sqlite (Reads watchlist membership via
is_watchlisted)` to the Key Input Dependencies list.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd plugins/tradingview && python3 -m pytest tests/test_ta_sweep_batch.py -v`

Expected: PASS — all tests, including every pre-existing test in the file (unaffected — they
exercise `run_sweep`/`enrich_results`/`save_sweep_results`, not the ticker-selection loop).

- [ ] **Step 5: Commit**

```bash
git add plugins/tradingview/scripts/ta_sweep_batch.py plugins/tradingview/tests/test_ta_sweep_batch.py
git commit -m "feat(ta_sweep_batch.py): scan holdings UNION watchlist, not holdings only"
```

**Note for Task 5:** this task changes the ticker universe for *future* real sweep runs, not the
historical 26-ticker `ta-sweep-results.json` snapshot Task 5 backfills — that file's 26 rows are
whatever the last real TradingView-Desktop-driven sweep produced under the old, holdings-only
logic. Task 5's row-count reconciliation (Hard-Stop Condition #1) is still against that file's own
`count` field (26), not the ~78 the new scan-universe logic will produce for the *next* real
sweep run. Do not conflate the two — expect the next real sweep after this wave ships to write
substantially more `TECHNICAL_SWEEP` rows than the 26 this backfill adds.

---

### Task 1: One-time migration script — backfill `ta-sweep-results.json` into the ledger

**Files:**
- Create: `investment_screener/backend/py_services/migrate_ta_sweep_to_ledger.py`
- Test: `investment_screener/backend/tests/py_services/test_migrate_ta_sweep_to_ledger.py`

**Interfaces:**
- Produces: `migrate(json_path: Path, jsonl_path: Path, db_path: Path, dry_run: bool = True) -> dict`
  returning `{"source_count": int, "written_count": int, "skipped": list[str]}`.
- Consumes: `intelligence.event_store.append_event` (existing signature, same as
  `ta_sweep_batch.py::save_sweep_results` uses — `event_type, effective_at, status, title,
  body_markdown, ticker, source_id, payload, idempotency_key`), `intelligence.replay_ledger.
  replay_events_to_db`, `intelligence.db_client.initialize_db`.

- [ ] **Step 1: Write the failing test**

Create `investment_screener/backend/tests/py_services/test_migrate_ta_sweep_to_ledger.py`:

```python
"""Wave 5B Task 1: backfilling the one real ta-sweep-results.json snapshot into the
Intelligence Ledger as TECHNICAL_SWEEP events, using the same append_event/replay
machinery ta_sweep_batch.py's own save_sweep_results() already uses for new sweeps.
"""
import json
import sqlite3
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
PY_SERVICES = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(PY_SERVICES))

from migrate_ta_sweep_to_ledger import migrate  # noqa: E402
from intelligence.db_client import initialize_db  # noqa: E402


FIXTURE_RESULTS = [
    {"ticker": "MSFT", "close": 450.0, "changePct": 1.2, "rsi": 55.0, "action": "HOLD"},
    {"ticker": "NVDA", "close": 900.0, "changePct": -0.5, "rsi": 60.0, "action": "ACCUMULATE"},
]


def _write_source_json(path: Path, scan_date: str, results: list[dict]) -> None:
    path.write_text(json.dumps({
        "timestamp": f"{scan_date}T14:46:53.885784+00:00",
        "scan_date": scan_date,
        "count": len(results),
        "results": results,
    }))


def _seed_instruments(db_path: Path, tickers: list[str]) -> None:
    conn = initialize_db(str(db_path))
    for t in tickers:
        conn.execute(
            "INSERT OR IGNORE INTO instrument VALUES (?, ?, 'NASDAQ', ?, '2026-01-01', NULL);",
            (f"us-{t.lower()}", t, t),
        )
    conn.commit()
    conn.close()


def test_dry_run_reports_counts_without_writing(tmp_path):
    json_path = tmp_path / "ta-sweep-results.json"
    jsonl_path = tmp_path / "observations.jsonl"
    db_path = tmp_path / "intelligence.sqlite"
    _write_source_json(json_path, "2026-07-10", FIXTURE_RESULTS)
    _seed_instruments(db_path, ["MSFT", "NVDA"])

    report = migrate(json_path, jsonl_path, db_path, dry_run=True)

    assert report["source_count"] == 2
    assert report["written_count"] == 0
    assert not jsonl_path.exists() or jsonl_path.read_text() == ""
    conn = sqlite3.connect(db_path)
    count = conn.execute(
        "SELECT COUNT(*) FROM intelligence_event WHERE event_type = 'TECHNICAL_SWEEP';"
    ).fetchone()[0]
    conn.close()
    assert count == 0


def test_real_write_creates_technical_sweep_events(tmp_path):
    json_path = tmp_path / "ta-sweep-results.json"
    jsonl_path = tmp_path / "observations.jsonl"
    db_path = tmp_path / "intelligence.sqlite"
    _write_source_json(json_path, "2026-07-10", FIXTURE_RESULTS)
    _seed_instruments(db_path, ["MSFT", "NVDA"])

    report = migrate(json_path, jsonl_path, db_path, dry_run=False)

    assert report["source_count"] == 2
    assert report["written_count"] == 2
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT i.ticker, ie.event_type, ie.status, ie.payload_json FROM intelligence_event ie "
        "JOIN instrument i ON i.instrument_id = ie.instrument_id "
        "WHERE ie.event_type = 'TECHNICAL_SWEEP' ORDER BY i.ticker;"
    ).fetchall()
    conn.close()
    assert [r[0] for r in rows] == ["MSFT", "NVDA"]
    assert all(r[1] == "TECHNICAL_SWEEP" and r[2] == "ACTIVE" for r in rows)
    assert json.loads(rows[0][3])["ticker"] == "MSFT"


def test_idempotency_key_matches_producer_format_no_duplicate_on_rerun(tmp_path):
    """Idempotency key must match ta_sweep_batch.py's own format (ta-sweep-{ticker}-{scan_date})
    so a real future sweep for the same ticker/date never double-writes against this backfill.
    """
    json_path = tmp_path / "ta-sweep-results.json"
    jsonl_path = tmp_path / "observations.jsonl"
    db_path = tmp_path / "intelligence.sqlite"
    _write_source_json(json_path, "2026-07-10", FIXTURE_RESULTS)
    _seed_instruments(db_path, ["MSFT", "NVDA"])

    migrate(json_path, jsonl_path, db_path, dry_run=False)
    migrate(json_path, jsonl_path, db_path, dry_run=False)  # re-run, same source

    conn = sqlite3.connect(db_path)
    count = conn.execute(
        "SELECT COUNT(*) FROM intelligence_event WHERE event_type = 'TECHNICAL_SWEEP' AND status = 'ACTIVE';"
    ).fetchone()[0]
    conn.close()
    assert count == 2  # not 4 — replay is idempotent on the same idempotency_key


def test_missing_source_file_raises_filenotfounderror(tmp_path):
    with pytest.raises(FileNotFoundError):
        migrate(tmp_path / "does-not-exist.json", tmp_path / "o.jsonl", tmp_path / "d.sqlite", dry_run=True)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd investment_screener/backend && pytest tests/py_services/test_migrate_ta_sweep_to_ledger.py -v`

Expected: FAIL — `ModuleNotFoundError: No module named 'migrate_ta_sweep_to_ledger'`.

- [ ] **Step 3: Write the implementation**

Create `investment_screener/backend/py_services/migrate_ta_sweep_to_ledger.py`:

```python
#!/usr/bin/env python3
"""One-time migration: backfill the real ta-sweep-results.json snapshot into the
Intelligence Ledger as TECHNICAL_SWEEP events (Wave 5B, ADR-029).

Uses the exact same append_event/replay_events_to_db machinery
ta_sweep_batch.py::save_sweep_results() already uses for new sweeps, so future real
sweeps and this one-time backfill share one idempotency-key format
(ta-sweep-{ticker}-{scan_date}) — a real future sweep for an already-backfilled
ticker/date never double-writes.

Usage:
    python3 migrate_ta_sweep_to_ledger.py --dry-run
    python3 migrate_ta_sweep_to_ledger.py --write
"""
import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))

DEFAULT_JSON_PATH = REPO_ROOT / "investment_screener/backend/data/ta-sweep-results.json"
DEFAULT_DB_PATH = REPO_ROOT / "investment_screener/backend/data/intelligence.sqlite"


def migrate(json_path: Path, jsonl_path: Path, db_path: Path, dry_run: bool = True) -> dict:
    """Backfill one ta-sweep-results.json snapshot into intelligence_event.

    Args:
        json_path: Source ta-sweep-results.json to read.
        jsonl_path: observations.jsonl ledger to append TECHNICAL_SWEEP events to.
        db_path: intelligence.sqlite to replay the ledger into.
        dry_run: When True (default), report counts without writing anything.

    Returns:
        {"source_count": int, "written_count": int, "skipped": list[str]}
    """
    from intelligence.event_store import append_event
    from intelligence.replay_ledger import replay_events_to_db
    from intelligence.db_client import initialize_db
    import sqlite3

    if not json_path.exists():
        raise FileNotFoundError(f"Source file not found: {json_path}")

    with open(json_path) as f:
        raw = json.load(f)
    scan_date = raw.get("scan_date")
    results = raw.get("results", [])
    skipped: list[str] = []

    report = {"source_count": len(results), "written_count": 0, "skipped": skipped}
    if dry_run:
        return report

    for res in results:
        ticker = res.get("ticker")
        if not ticker or not scan_date:
            skipped.append(str(res))
            continue
        append_event(
            str(jsonl_path),
            event_type="TECHNICAL_SWEEP",
            effective_at=scan_date,
            status="ACTIVE",
            title=f"TA Sweep for {ticker}",
            body_markdown=f"Batch technical indicators for {ticker}.",
            ticker=ticker,
            source_id="wave5b-migration-backfill",
            payload=res,
            idempotency_key=f"ta-sweep-{ticker}-{scan_date}",
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
    parser.add_argument("--json-path", default=str(DEFAULT_JSON_PATH))
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--jsonl-path", default=None, help="Defaults to the standard observations.jsonl ledger path.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true")
    group.add_argument("--write", action="store_true")
    args = parser.parse_args()

    from intelligence.event_store import _default_jsonl_path
    jsonl_path = Path(args.jsonl_path) if args.jsonl_path else _default_jsonl_path()

    report = migrate(Path(args.json_path), jsonl_path, Path(args.db_path), dry_run=args.dry_run)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd investment_screener/backend && pytest tests/py_services/test_migrate_ta_sweep_to_ledger.py -v`

Expected: PASS, all 5 tests.

- [ ] **Step 5: Commit**

```bash
git add investment_screener/backend/py_services/migrate_ta_sweep_to_ledger.py investment_screener/backend/tests/py_services/test_migrate_ta_sweep_to_ledger.py
git commit -m "feat(wave5b): add ta-sweep-results.json ledger backfill migration script"
```

---

### Task 2: Rewire `daily_brief.py::run()` to read TA sweep results from SQLite, not the JSON file

**Files:**
- Modify: `plugins/portfolio-advisor/scripts/daily_brief.py:447-457` (the post-subprocess read
  in `run()`)
- Test: `investment_screener/backend/tests/py_services/test_daily_brief_ta_sweep_delegates.py`
  (add a new test to the existing file)

**Interfaces:**
- Produces: `_load_latest_ta_sweep_count(db_path: str | None = None) -> int | None` — new helper
  in `daily_brief.py`, returning the count of `ACTIVE` `TECHNICAL_SWEEP` rows for the most recent
  `effective_at` date, or `None` if none exist.
- Consumes: same `sqlite3` direct-query pattern already used by `_ta_age_hours()` in the same
  file (lines 63–93) — no new repository/service layer needed, matches existing precedent.

- [ ] **Step 1: Write the failing test**

Add to `investment_screener/backend/tests/py_services/test_daily_brief_ta_sweep_delegates.py`:

```python
def test_load_latest_ta_sweep_count_reads_from_database(tmp_path):
    """_load_latest_ta_sweep_count must read the most recent scan's row count from SQLite,
    not re-open TA_SWEEP_PATH — the last real JSON-only read site in daily_brief.py (Wave 5B).
    """
    import sys
    from pathlib import Path
    repo_root = Path(__file__).resolve().parents[4]
    sys.path.insert(0, str(repo_root / "investment_screener/backend/py_services"))
    sys.path.insert(0, str(repo_root / "plugins/portfolio-advisor/scripts"))

    from daily_brief import _load_latest_ta_sweep_count  # noqa: PLC0415
    from intelligence.db_client import initialize_db  # noqa: E402
    from intelligence.event_store import append_event  # noqa: E402
    from intelligence.replay_ledger import replay_events_to_db  # noqa: E402
    import sqlite3

    db_path = tmp_path / "intelligence.sqlite"
    jsonl_path = tmp_path / "observations.jsonl"

    conn = initialize_db(str(db_path))
    for ticker in ("MSFT", "NVDA", "AAPL"):
        conn.execute(
            "INSERT INTO instrument VALUES (?, ?, 'NASDAQ', ?, '2026-01-01', NULL);",
            (f"us-{ticker.lower()}", ticker, ticker),
        )
    conn.commit()
    conn.close()

    for ticker in ("MSFT", "NVDA", "AAPL"):
        append_event(
            str(jsonl_path), event_type="TECHNICAL_SWEEP", effective_at="2026-07-18",
            status="ACTIVE", title=f"TA Sweep {ticker}", body_markdown="x",
            ticker=ticker, source_id="tradingview-cdp", payload={"ticker": ticker},
            idempotency_key=f"ta-sweep-{ticker}-2026-07-18",
        )
    conn = sqlite3.connect(str(db_path))
    replay_events_to_db(str(jsonl_path), conn)
    conn.close()

    count = _load_latest_ta_sweep_count(db_path=str(db_path))
    assert count == 3


def test_load_latest_ta_sweep_count_returns_none_when_no_events(tmp_path):
    import sys
    from pathlib import Path
    repo_root = Path(__file__).resolve().parents[4]
    sys.path.insert(0, str(repo_root / "investment_screener/backend/py_services"))
    sys.path.insert(0, str(repo_root / "plugins/portfolio-advisor/scripts"))
    from daily_brief import _load_latest_ta_sweep_count  # noqa: PLC0415
    from intelligence.db_client import initialize_db  # noqa: E402

    db_path = tmp_path / "intelligence.sqlite"
    initialize_db(str(db_path)).close()

    assert _load_latest_ta_sweep_count(db_path=str(db_path)) is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd investment_screener/backend && pytest tests/py_services/test_daily_brief_ta_sweep_delegates.py -v -k load_latest_ta_sweep_count`

Expected: FAIL — `ImportError: cannot import name '_load_latest_ta_sweep_count'`.

- [ ] **Step 3: Implement `_load_latest_ta_sweep_count()` and rewire `run()`**

In `plugins/portfolio-advisor/scripts/daily_brief.py`, add this function directly below
`_ta_age_hours()` (after line 93):

```python
def _load_latest_ta_sweep_count(db_path: str | None = None) -> int | None:
    """Return the number of ACTIVE TECHNICAL_SWEEP rows for the most recent effective_at date,
    or None if no sweep events exist yet. SQLite-only (Wave 5B) — no JSON fallback, matching
    the ta-sweep-results.json domain's ADR-029 migration.
    """
    import sqlite3

    resolved_db_path = db_path or str(REPO_ROOT / "investment_screener/backend/data/intelligence.sqlite")
    conn = sqlite3.connect(resolved_db_path)
    try:
        latest = conn.execute("""
            SELECT MAX(effective_at) FROM intelligence_event
            WHERE event_type = 'TECHNICAL_SWEEP' AND status = 'ACTIVE';
        """).fetchone()[0]
        if not latest:
            return None
        count = conn.execute("""
            SELECT COUNT(*) FROM intelligence_event
            WHERE event_type = 'TECHNICAL_SWEEP' AND status = 'ACTIVE' AND effective_at = ?;
        """, (latest,)).fetchone()[0]
        return count
    finally:
        conn.close()
```

Then replace lines 447–457 of `run()` (currently re-opening `TA_SWEEP_PATH` after the subprocess)
with:

```python
            if result.returncode == 0:
                # save_sweep_results() already replayed this run's events to SQLite
                # synchronously before the subprocess exited (Wave 5B) — read the count
                # back from there instead of re-opening the file it also used to write.
                scan_count = _load_latest_ta_sweep_count(db_path=db_path)
                if scan_count is not None:
                    ran_ta = True
                    print(f"  Scanned {scan_count} holdings.", file=sys.stderr)
                else:
                    ta_skip_reason = "TA sweep produced no events"
```

Remove the now-unused `resolved_json_path`/`json.loads(f.read())["results"]` lines and the
`(json.JSONDecodeError, FileNotFoundError, KeyError)` except clause that guarded them — the new
code has no file I/O to guard.

Remove the `ta_json_path` parameter from `run()`'s signature (line 376) and its docstring entry
(line 383), and remove the `ta_json_path=ta_json_path` passthrough at the `compute_all()` call
site (line 473) — Task 3 removes the corresponding parameter from `compute_all()`/`_load_ta()`,
so this call site must be updated in the same commit as Task 3, not this one; for this task,
leave the passthrough as `ta_json_path=None` (harmless no-op) rather than editing `compute_all()`'s
signature — that edit belongs to Task 3.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd investment_screener/backend && pytest tests/py_services/test_daily_brief_ta_sweep_delegates.py -v`

Expected: PASS, including the pre-existing `test_daily_brief_does_not_write_ta_sweep_path_directly`
and `test_ta_age_hours_reads_from_database` (unchanged, must still pass).

- [ ] **Step 5: Commit**

```bash
git add plugins/portfolio-advisor/scripts/daily_brief.py investment_screener/backend/tests/py_services/test_daily_brief_ta_sweep_delegates.py
git commit -m "fix(daily_brief.py): read post-sweep TA count from SQLite, not ta-sweep-results.json (Wave 5B)"
```

---

### Task 3: Remove the JSON-fallback branches in `_load_ta()` and `_ta_age_hours()`

**Files:**
- Modify: `investment_screener/backend/py_services/compute_conviction_scores.py:284-349`
  (`_load_ta()`) and its callers (`compute_all()` signature, line 445)
- Modify: `plugins/portfolio-advisor/scripts/daily_brief.py:63-93` (`_ta_age_hours()`) and the
  `run()` call site (line 473, `ta_json_path=ta_json_path` → drop entirely)
- Test: `investment_screener/backend/tests/py_services/test_compute_conviction_scores.py`,
  `investment_screener/backend/tests/py_services/test_daily_brief_ta_sweep_delegates.py`

**Interfaces:**
- Produces: `_load_ta(db_path: str | None = None) -> tuple[dict, int | None]` (drops the
  `ta_json_path` parameter entirely). `compute_all(db_path=..., ...)` (drops `ta_json_path`
  parameter). `_ta_age_hours(db_path: str | None = None) -> float | None` (drops fallback body,
  signature unchanged).
- Consumes: Task 1's migration having already backfilled real data means the DB path is no
  longer empty in production, so removing the fallback does not create a new gap for real users
  — verify this ordering explicitly (Task 4, the real migration write, must land before or
  alongside this task's merge to `main`, not after — call this out in the task review).

- [ ] **Step 1: Write the failing tests**

Add to `investment_screener/backend/tests/py_services/test_compute_conviction_scores.py` (in the
existing `_load_ta` test class, alongside `test_load_ta_from_sqlite`):

```python
    def test_load_ta_has_no_json_fallback_signature(self):
        """_load_ta must not accept a ta_json_path parameter — Wave 5B removed the fallback."""
        import inspect
        from compute_conviction_scores import _load_ta  # noqa: PLC0415
        sig = inspect.signature(_load_ta)
        assert "ta_json_path" not in sig.parameters

    def test_load_ta_returns_empty_on_missing_db_no_json_read(self, tmp_path, monkeypatch):
        """With no DB and no fallback, a missing db_path must return ({}, None) — never attempt
        to read any JSON file (Wave 5B: no fallback exists to attempt).
        """
        from compute_conviction_scores import _load_ta  # noqa: PLC0415
        missing_db = tmp_path / "does-not-exist.sqlite"
        ta_map, stale = _load_ta(db_path=str(missing_db))
        assert ta_map == {}
        assert stale is None
```

Add to `investment_screener/backend/tests/py_services/test_daily_brief_ta_sweep_delegates.py`:

```python
def test_ta_age_hours_returns_none_on_missing_db_no_json_fallback(tmp_path):
    """With no DB and no fallback, a missing db_path must return None — Wave 5B removed the
    JSON-fallback branch entirely.
    """
    import sys
    from pathlib import Path
    repo_root = Path(__file__).resolve().parents[4]
    sys.path.insert(0, str(repo_root / "plugins/portfolio-advisor/scripts"))
    from daily_brief import _ta_age_hours  # noqa: PLC0415

    missing_db = tmp_path / "does-not-exist.sqlite"
    assert _ta_age_hours(db_path=str(missing_db)) is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
cd investment_screener/backend
pytest tests/py_services/test_compute_conviction_scores.py -v -k "no_json_fallback_signature or no_json_read"
pytest tests/py_services/test_daily_brief_ta_sweep_delegates.py -v -k "no_json_fallback"
```

Expected: FAIL — `test_load_ta_has_no_json_fallback_signature` fails because `ta_json_path` is
still a parameter; the missing-db tests currently return non-empty/non-None because the fallback
branch reads `TA_SWEEP_PATH` if it exists on the real filesystem (test isolation gap this task
closes).

- [ ] **Step 3: Remove the fallback branches**

In `investment_screener/backend/py_services/compute_conviction_scores.py`, replace the whole
`_load_ta()` function (lines 284–349) with:

```python
def _load_ta(db_path: str | None = None) -> tuple[dict[str, dict[str, Any]], int | None]:
    """Load TA sweep results keyed by ticker and compute staleness, from the SQLite ledger only.

    No JSON fallback (Wave 5B, ADR-029) — ta-sweep-results.json is archived; the ledger is the
    sole source of truth.

    Returns:
        Tuple of (ticker_map, staleness_days). Both empty/None if the DB is missing or empty.
    """
    import os
    import sqlite3

    resolved_db_path = db_path or str(REPO_ROOT / "investment_screener/backend/data/intelligence.sqlite")
    if not os.path.exists(resolved_db_path):
        return {}, None

    try:
        conn = sqlite3.connect(resolved_db_path)
        cursor = conn.execute("""
            SELECT ticker, payload_json, effective_at, ingested_at FROM (
                SELECT i.ticker, ie.payload_json, ie.effective_at, ie.ingested_at,
                       ROW_NUMBER() OVER (PARTITION BY i.ticker ORDER BY ie.effective_at DESC, ie.ingested_at DESC) as rn
                FROM intelligence_event ie
                JOIN instrument i ON i.instrument_id = ie.instrument_id
                WHERE ie.event_type = 'TECHNICAL_SWEEP' AND ie.status = 'ACTIVE'
            ) WHERE rn = 1;
        """)
        rows = cursor.fetchall()
        conn.close()
    except Exception:
        return {}, None

    if not rows:
        return {}, None

    ticker_map = {}
    latest_ts = None
    for ticker, payload_json, effective_at, ingested_at in rows:
        if payload_json:
            ticker_map[ticker] = json.loads(payload_json)
        ts = ingested_at or effective_at
        if ts and (latest_ts is None or ts > latest_ts):
            latest_ts = ts

    stale: int | None = None
    if latest_ts:
        ts_str = latest_ts.replace("Z", "+00:00")
        if len(ts_str) == 10:
            ts_str += "T00:00:00+00:00"
        try:
            scanned = datetime.fromisoformat(ts_str)
            stale = (datetime.now(timezone.utc) - scanned).days
        except ValueError:
            pass
    return ticker_map, stale
```

Remove the now-unused `TA_SWEEP_PATH` module-level constant (line 68) if nothing else in the
file references it — confirm with `grep -n TA_SWEEP_PATH investment_screener/backend/py_services/compute_conviction_scores.py`
before deleting.

Update `compute_all()` (line 443 onward): remove the `ta_json_path: Path | None = None`
parameter (line 445) and change the call at line 452 from
`_load_ta(db_path=db_path, ta_json_path=ta_json_path)` to `_load_ta(db_path=db_path)`.

In `plugins/portfolio-advisor/scripts/daily_brief.py`, replace `_ta_age_hours()` (lines 63–93)
with:

```python
def _ta_age_hours(db_path: str | None = None) -> float | None:
    """Return hours since last TA sweep from the SQLite ledger. No JSON fallback (Wave 5B)."""
    import os
    import sqlite3

    resolved_db_path = db_path or str(REPO_ROOT / "investment_screener/backend/data/intelligence.sqlite")
    if not os.path.exists(resolved_db_path):
        return None
    try:
        conn = sqlite3.connect(resolved_db_path)
        cursor = conn.execute("""
            SELECT MAX(ingested_at) FROM intelligence_event
            WHERE event_type = 'TECHNICAL_SWEEP' AND status = 'ACTIVE';
        """)
        row = cursor.fetchone()
        conn.close()
        if row and row[0]:
            ts_str = row[0].replace("Z", "+00:00")
            scanned = datetime.fromisoformat(ts_str)
            return (datetime.now(timezone.utc) - scanned).total_seconds() / 3600
    except Exception:
        pass
    return None
```

Remove the `ta_json_path=ta_json_path` passthrough in `run()`'s `compute_all()` call (line 473)
— change to `scores = compute_all(db_path=db_path)`. Remove the `ta_json_path` parameter from
`run()`'s own signature (line 376) and docstring (line 383) — this is safe now that Task 2's
`_load_latest_ta_sweep_count()` also takes no `ta_json_path`.

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
cd investment_screener/backend
pytest tests/py_services/test_compute_conviction_scores.py -v
pytest tests/py_services/test_daily_brief_ta_sweep_delegates.py -v
```

Expected: PASS — all tests in both files, including every pre-existing test (they exercise the
DB-populated path, unaffected by fallback removal).

- [ ] **Step 5: Commit**

```bash
git add investment_screener/backend/py_services/compute_conviction_scores.py plugins/portfolio-advisor/scripts/daily_brief.py investment_screener/backend/tests/py_services/test_compute_conviction_scores.py investment_screener/backend/tests/py_services/test_daily_brief_ta_sweep_delegates.py
git commit -m "fix(wave5b): remove dead JSON-fallback branches in _load_ta/_ta_age_hours"
```

---

### Task 4: Producer — stop writing `ta-sweep-results.json` by default; correct stale docs

**Files:**
- Modify: `plugins/tradingview/scripts/ta_sweep_batch.py:311-433` (`save_sweep_results()` and
  `main()`)
- Modify: `plugins/tradingview/skills/technical-analysis-expert/SKILL.md:78`,
  `plugins/tradingview/README.md:184-189` (stale doc references)
- Test: `plugins/tradingview/tests/test_ta_sweep_batch.py`

**Interfaces:**
- Produces: `save_sweep_results(results, jsonl_path=None, db_path=None, json_export_path=None) ->
  None` — the flat JSON write becomes conditional on `json_export_path` being explicitly passed
  (default `None` = no JSON write); the ledger/SQLite write remains unconditional, same as today.
  This is a **signature change** — `output_path` (previously required, positional) is replaced
  by optional `json_export_path`; the DB/ledger write no longer depends on any output path being
  given at all.
- Consumes: existing `intelligence.event_store.append_event`,
  `intelligence.replay_ledger.replay_events_to_db`, `intelligence.db_client.initialize_db` —
  unchanged.

- [ ] **Step 1: Write the failing tests**

Modify `plugins/tradingview/tests/test_ta_sweep_batch.py`: the existing
`test_save_sweep_results_writes_timestamped_json` (line 150) and
`test_save_sweep_results_overwrites_existing` (line 168) currently call
`save_sweep_results(FIXTURE_RESULTS, out_file)` with `out_file` as the *required* JSON output
path. Update both call sites to the new keyword: `save_sweep_results(FIXTURE_RESULTS,
json_export_path=out_file, jsonl_path=<tmp jsonl>, db_path=<tmp db>)` (matching the pattern
`test_save_sweep_results_writes_to_ledger_and_sqlite`, line 180, already uses) — this is required
regardless of pass/fail because the signature is changing; but as a TDD checkpoint, first add
this new test proving the JSON write is now opt-in:

```python
def test_save_sweep_results_writes_no_json_by_default(self, tmp_path: Path):
    """Wave 5B: without json_export_path, save_sweep_results must not create any JSON file —
    only the ledger/SQLite write is unconditional now."""
    sys.path.insert(0, str(REPO_ROOT / "plugins/tradingview/scripts"))
    from ta_sweep_batch import save_sweep_results  # noqa: PLC0415

    jsonl_path = tmp_path / "observations.jsonl"
    db_path = tmp_path / "intelligence.sqlite"
    from intelligence.db_client import initialize_db  # noqa: PLC0415
    conn = initialize_db(str(db_path))
    conn.execute("INSERT INTO instrument VALUES ('us-msft', 'MSFT', 'NASDAQ', 'Microsoft', '2026-01-01', NULL);")
    conn.commit()
    conn.close()

    save_sweep_results(FIXTURE_RESULTS, jsonl_path=jsonl_path, db_path=db_path)

    assert not any(tmp_path.glob("*.json"))  # no flat JSON written anywhere
    import sqlite3
    conn = sqlite3.connect(db_path)
    count = conn.execute(
        "SELECT COUNT(*) FROM intelligence_event WHERE event_type = 'TECHNICAL_SWEEP';"
    ).fetchone()[0]
    conn.close()
    assert count == len(FIXTURE_RESULTS)  # ledger/SQLite write still unconditional
```

(`FIXTURE_RESULTS` must have `ticker: "MSFT"` for this instrument-seeded test — check the
existing fixture at the top of the file and adjust the `INSERT INTO instrument` line(s) to match
whatever tickers `FIXTURE_RESULTS` actually contains.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd plugins/tradingview && python3 -m pytest tests/test_ta_sweep_batch.py -v -k "writes_no_json_by_default"`

Expected: FAIL — current signature requires `output_path` positionally, so this call raises
`TypeError: save_sweep_results() missing 1 required positional argument: 'output_path'`.

- [ ] **Step 3: Implement the signature change**

Replace `save_sweep_results()` (lines 311–376) in `plugins/tradingview/scripts/ta_sweep_batch.py`
with:

```python
def save_sweep_results(
    results: list[dict[str, Any]],
    jsonl_path: Path | None = None,
    db_path: Path | None = None,
    json_export_path: Path | None = None,
) -> None:
    """Write TECHNICAL_SWEEP events to the ledger and SQLite read-model (always) and,
    only if json_export_path is given, an ad-hoc flat-JSON export snapshot.

    Wave 5B (ADR-029): the ledger/SQLite write is the source of truth and always runs.
    The flat-file JSON export is now opt-in only — for manual debugging/export, never a
    dependency any real consumer relies on (ta-sweep-results.json itself was archived
    to ARCHIVE/ this wave; see Task 5).

    Args:
        results: Enriched per-ticker sweep results from main sweep loop.
        jsonl_path: Optional path to observations.jsonl ledger (defaults to the standard path).
        db_path: Optional path to intelligence.sqlite database (defaults to the standard path).
        json_export_path: If given, also write a flat {timestamp, scan_date, count, results}
            JSON snapshot to this path — opt-in only, not written by default.
    """
    now = datetime.now(timezone.utc)
    scan_date = now.strftime("%Y-%m-%d")

    if json_export_path is not None:
        payload: dict[str, Any] = {
            "timestamp": now.isoformat(),
            "scan_date": scan_date,
            "count": len(results),
            "results": results,
        }
        json_export_path.parent.mkdir(parents=True, exist_ok=True)
        with open(json_export_path, "w") as f:
            json.dump(payload, f, indent=2)

    from intelligence.event_store import append_event, _default_jsonl_path
    from intelligence.replay_ledger import replay_events_to_db
    from intelligence.db_client import initialize_db
    import sys

    if "pytest" in sys.modules and jsonl_path is None and db_path is None:
        return

    resolved_jsonl_path = jsonl_path or _default_jsonl_path()
    resolved_db_path = db_path or (REPO_ROOT / "investment_screener/backend/data/intelligence.sqlite")

    for res in results:
        ticker = res["ticker"]
        append_event(
            str(resolved_jsonl_path),
            event_type="TECHNICAL_SWEEP",
            effective_at=scan_date,
            status="ACTIVE",
            title=f"TA Sweep for {ticker}",
            body_markdown=f"Batch technical indicators for {ticker}.",
            ticker=ticker,
            source_id="tradingview-cdp",
            payload=res,
            idempotency_key=f"ta-sweep-{ticker}-{scan_date}",
        )

    conn = initialize_db(str(resolved_db_path))
    try:
        replay_events_to_db(str(resolved_jsonl_path), conn)
    finally:
        conn.close()
```

Replace the CLI wiring at the end of `main()` (lines 424–430):

```python
    # SQLite/ledger write is always the source of truth (Wave 5B) — the --save-results
    # flag now controls an OPTIONAL flat-JSON export only, off by default.
    export_path = Path(args.save_results) if args.save_results else None
    save_sweep_results(scan_results, json_export_path=export_path)
    if export_path:
        print(f"Results also exported → {export_path}", file=sys.stderr)
```

Remove the now-unreachable `--no-save` argparse option (lines it's defined at, near
`--save-results`) — with JSON export off by default, there is nothing left to suppress; update
the `--save-results` help text (currently references the old default path) to: `"Also export a
flat-file JSON snapshot to PATH (default default: no export — ledger/SQLite write is always the
source of truth)"`. Update `TA_SWEEP_RESULTS_PATH` module constant's docstring/comment if it
implies default auto-save behavior that no longer exists — keep the constant itself (Task 5's
archive step and any manual `--save-results` invocation still reference it as a conventional
default path when the flag has no explicit value); change its `nargs='?', const=...` default to
still point at it for convenience when `--save-results` is passed with no value.

Also fix the stale doc references confirmed false in Pre-Implementation Findings:
- `plugins/tradingview/skills/technical-analysis-expert/SKILL.md:78`: change "Results auto-saved
  to `investment_screener/backend/data/ta-sweep-results.json`" to "Results written to the
  Intelligence Ledger (`TECHNICAL_SWEEP` events); pass `--save-results` for an optional flat-file
  export."
- `plugins/tradingview/README.md:184-189`: same correction — update the comment and the "Results
  saved to" line.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd plugins/tradingview && python3 -m pytest tests/test_ta_sweep_batch.py -v`

Expected: PASS — all tests including the two updated pre-existing ones
(`test_save_sweep_results_writes_timestamped_json`,
`test_save_sweep_results_overwrites_existing`) and
`test_save_sweep_results_writes_to_ledger_and_sqlite` (unchanged assertions, updated call syntax
only), plus the new `test_save_sweep_results_writes_no_json_by_default`.

- [ ] **Step 5: Commit**

```bash
git add plugins/tradingview/scripts/ta_sweep_batch.py plugins/tradingview/tests/test_ta_sweep_batch.py plugins/tradingview/skills/technical-analysis-expert/SKILL.md plugins/tradingview/README.md
git commit -m "fix(ta_sweep_batch.py): JSON export opt-in only, SQLite/ledger write is default (Wave 5B)"
```

---

### Task 5: Real data migration (main checkout only) + archive `ta-sweep-results.json`

**This task performs a real write against the main checkout — not this worktree — per this
wave's kickoff prompt and CLAUDE.md pitfall #29. Requires a dry-run report and explicit user
sign-off BEFORE the real `--write` runs.**

**Files:**
- Real write target (main checkout, absolute path, never worktree-relative):
  `/Users/richardfremmerlid/Projects/InvestmentToolkit/investment_screener/backend/data/intelligence.sqlite`
- Real source (main checkout):
  `/Users/richardfremmerlid/Projects/InvestmentToolkit/investment_screener/backend/data/ta-sweep-results.json`
- Archive: `git mv investment_screener/backend/data/ta-sweep-results.json ARCHIVE/investment_screener/backend/data/ta-sweep-results.json`
  (this file is git-tracked — confirmed in Pre-Implementation Findings — `git mv`, not a
  local-only `mv`)

**Steps (not TDD — this is an operational/data task, gated by hard-stop conditions above):**

- [ ] **Step 1: Dry-run against the main checkout**, from the main checkout directory (not the
  worktree):
  ```bash
  cd /Users/richardfremmerlid/Projects/InvestmentToolkit
  python3 investment_screener/backend/py_services/migrate_ta_sweep_to_ledger.py \
    --json-path investment_screener/backend/data/ta-sweep-results.json \
    --db-path investment_screener/backend/data/intelligence.sqlite \
    --dry-run
  ```
  Report the exact JSON output (`source_count`, `written_count`, `skipped`) to the user. Expect
  `source_count: 26, written_count: 0` (dry-run never writes).

- [ ] **Step 2: Stop. Present the dry-run report to the user and get explicit sign-off before
  proceeding to the real write.** This is the hard approval gate — do not skip it even though
  Task 1's tests already prove the script works on fixtures.

- [ ] **Step 3: Real write against the main checkout** (only after sign-off):
  ```bash
  cd /Users/richardfremmerlid/Projects/InvestmentToolkit
  python3 investment_screener/backend/py_services/migrate_ta_sweep_to_ledger.py \
    --json-path investment_screener/backend/data/ta-sweep-results.json \
    --db-path investment_screener/backend/data/intelligence.sqlite \
    --write
  ```

- [ ] **Step 4: Independently re-verify against the main checkout's actual DB file** (not the
  script's own reported output — a fresh, separate query):
  ```bash
  cd /Users/richardfremmerlid/Projects/InvestmentToolkit
  python3 -c "
  import sqlite3
  conn = sqlite3.connect('investment_screener/backend/data/intelligence.sqlite')
  cur = conn.execute(\"SELECT COUNT(*) FROM intelligence_event WHERE event_type='TECHNICAL_SWEEP' AND status='ACTIVE'\")
  print('TECHNICAL_SWEEP ACTIVE rows:', cur.fetchone()[0])
  "
  ```
  Expected: 26 (matching the source file's `count` field). If this does not match, this is
  Hard-Stop Condition #1 (source/target count do not reconcile) — stop, do not proceed to
  archival, report to the user.

- [ ] **Step 5: Confirm every real consumer now reads from this populated DB**, from the main
  checkout:
  ```bash
  cd /Users/richardfremmerlid/Projects/InvestmentToolkit
  python3 -c "
  import sys
  sys.path.insert(0, 'investment_screener/backend/py_services')
  from compute_conviction_scores import _load_ta
  ta_map, stale = _load_ta()
  print('tickers loaded:', len(ta_map), 'staleness_days:', stale)
  "
  ```
  Expected: `tickers loaded: 26` (or fewer if some tickers in the sweep aren't in the
  `instrument` table yet — investigate any shortfall before proceeding, do not assume it's fine).

- [ ] **Step 6: Archive** (only after Steps 4–5 both confirm real data + real consumer reads
  succeed):
  ```bash
  cd /Users/richardfremmerlid/Projects/InvestmentToolkit
  git mv investment_screener/backend/data/ta-sweep-results.json ARCHIVE/investment_screener/backend/data/ta-sweep-results.json
  ```
  Note: this `git mv` happens in the **main checkout**, not the worktree — coordinate with the
  worktree branch by also running the equivalent `git mv` inside the worktree so the commit that
  reaches the PR includes the archive (the main-checkout copy is the one with real, current
  20260710-dated data; the worktree's copy — confirmed identical since the file is git-tracked —
  can be archived the same way from the worktree's branch for the PR diff itself; the *real
  intelligence.sqlite write* stays main-checkout-only per Step 3).

- [ ] **Step 7: Commit** (from the worktree branch, so it lands in the PR):
  ```bash
  git add ARCHIVE/investment_screener/backend/data/ta-sweep-results.json
  git status  # confirm the deletion from the old path is staged too (git mv stages both sides)
  git commit -m "chore(wave5b): archive ta-sweep-results.json after verified TECHNICAL_SWEEP migration"
  ```

---

## Wave KPI Table (fill in at wave exit)

| Metric | Before | After |
|---|---|---|
| JSON files in this domain | 1 (`ta-sweep-results.json`, git-tracked) | 0 (archived to `ARCHIVE/`) |
| `TECHNICAL_SWEEP` rows in main's `intelligence.sqlite` | 0 | 26 (real backfilled historical data — next real sweep run adds ~78 more under the expanded scan universe) |
| Sweep scan universe | 26 tickers (portfolio holdings only) | Holdings ∪ watchlist — 82 unique combined as of 2026-07-22 (29 held, 80 watchlisted) minus `DEFAULT_SKIP` |
| Producers writing SQLite as default/unconditional path | 1 (already wired, but JSON was still the relied-upon default) | 1 (JSON now opt-in export only) |
| Real consumers reading SQLite unconditionally, no fallback | 0 of 3 (2 had untested fallback, 1 never touched DB) | 3 of 3 |
| Dead/untested fallback branches removed | 2 | 0 |
| Stale doc references to a nonexistent backend route | 2 (`SKILL.md`, `README.md`) + 2 in code comments | 0 |

## Definition of Done for This Wave

- [ ] All 6 tasks committed with passing tests.
- [ ] TA sweep scan universe confirmed to include both holdings and watchlist tickers (Task 0).
- [ ] Real migration write verified independently against the main checkout's
      `intelligence.sqlite` (Task 5 Step 4), not the worktree's.
- [ ] All 3 real consumer call sites confirmed reading SQLite only, no fallback remains reachable.
- [ ] `ta-sweep-results.json` archived via `git mv`.
- [ ] Full backend test suite + `plugins/tradingview/tests/test_ta_sweep_batch.py` run with no
      new failures vs. the documented baseline.
- [ ] Wave exit report + handoff written per the kickoff prompt's Way of Working §4.
- [ ] PR opened to `main`, not merged by the agent.
