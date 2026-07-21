# Domain Data Model v3.2 — Wave 3 (Account Holdings) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate `investment_screener/backend/data/portfolio.json` (gitignored, real broker/account
holdings for TFSA + RRSP) into the v3.2 SQLite domain model (`account`, `account_investment`,
`investment_price`), cutting over every real producer and consumer, then archiving the JSON file
locally (never `git add`ed, per its privacy classification).

**Architecture:** Extend the existing `py_services/domain_model/` package (Wave 0's
`account_repository.py`/`account_investment_repository.py`/`investment_repository.py`, already
built and tested) with a new `investment_price_repository.py` and a `portfolio_repository.py`
higher-level module exposing a `load_portfolio_state()`-compatible interface, so the existing
shared I/O module `portfolio_io.py` (discovered this session — the real "single source of truth for
portfolio data I/O" per its own docstring, already used by 7 of the real consumers) can be rewired
in one place rather than rewiring each of its callers individually. Direct producers/consumers that
bypass `portfolio_io.py` (routes/portfolio.ts, BrokerSyncService.ts, apply_portfolio_updates.py,
fetch_broker_data.py, update_price_levels.py, and ~20 direct-read consumers) are rewired
individually, same pattern as Waves 1–2.

**Tech Stack:** Python 3.13 (`sqlite3` stdlib), pytest (`tmp_path` fixtures + real-repo integration
tests), TypeScript/Express (`better-sqlite3`-equivalent already used by `InvestmentRepository.ts`/
`WatchlistService.ts` from Wave 2 — mirror that pattern for TS-side account/account_investment
reads).

## SQLite-First Design Principles (binding on every remaining task, added after Task 2's review)

Task 2's first draft looped over rows fetched one at a time via repository helper calls, reconstructing
the old JSON-tree shape in Python rather than expressing the calculation against the relational schema.
Task 0 separately found the root cause of the RRSP/TFSA bug was the same failure mode one level up:
reasoning about "a portfolio's flat list of holdings" instead of "accounts, each with their own
holdings." Both are instances of one mistake — carrying JSON-shaped thinking into SQLite-shaped code.
Every remaining task in this plan (Tasks 3 onward) must follow these principles, not just Task 2:

1. **The database is the source of truth for the business model.** Do not mentally start from
   `portfolio → accounts → holdings`. Start from `account` / `account_investment` / `investment` /
   `investment_price` — the schema already defines the entities and relationships; don't re-derive a
   document shape on top of it.
2. **Think in entities and relationships, not loops over a document.** `account` 1→many
   `account_investment`; `investment` 1→many `account_investment`; `investment` 1→many
   `investment_price`. A calculation is a query over these relationships, not a `for account in
   portfolio: for holding in account["holdings"]:` walk.
3. **Push set operations into SQL** (`JOIN`, `GROUP BY`, `SUM`, `COUNT`, `AVG`) — let SQLite do
   relational work. A Python loop calling a repository getter once per row, one row at a time, to
   assemble a total is the anti-pattern this principle exists to catch (this is exactly what Task 2's
   first draft did).
4. **Store facts, calculate aggregates.** Store shares, price, cash, account metadata. Calculate
   market value, account value, portfolio value, allocations — never store a calculated aggregate in
   its own column or table (ADR-030's rule, restated here as the general principle behind it).
5. **Calculate upward from the lowest grain.** `account_investment` is the lowest-grain financial fact
   in this schema. A portfolio total is derived from `account_investment` rows directly (via
   per-account rollups), never from "portfolio total ← account total ← holding total" chains that
   could each drift independently.
6. **Preserve account boundaries structurally, not just correctly-in-this-instance.** The direct fix
   for the RRSP/TFSA bug: `GROUP BY account_id` is a first-class step in any aggregation, and a
   portfolio-level total must always be expressible as `SUM(account-level totals)`, never a query that
   flattens across accounts before an account-level number was ever computed (Task 2's
   `get_portfolio_total_value() = sum(get_account_market_values().values())` is the reference
   implementation of this principle — later tasks introducing new aggregations should follow the same
   shape).
7. **Repositories expose business queries, not just row accessors.** Prefer `get_account_market_value()`
   / `get_portfolio_total_value()` / (a future) `get_account_allocations()` over forcing every caller to
   assemble the world from `get_account()`/`get_holding()`/`get_price()` primitives one at a time. SQL
   does the heavy lifting inside the repository function; callers get an answer, not assembly parts.
8. **Stop preserving JSON thinking — this is the root-cause principle behind the other seven.** The
   failure mode to actively watch for in every remaining task: *take the JSON structure → recreate it
   in memory → calculate exactly as the old JSON-based code did → store the result in SQLite.* That is
   not a migration, it's a translation that keeps the old bugs' shape. Instead: start from the business
   question, ask which tables and relationships answer it, express that as SQL, return the result. The
   SQLite schema should drive the implementation of every remaining task, not the retired JSON model
   `portfolio_io.py` or the flat `holdings[]` array used to represent.

## Global Constraints

(Copied verbatim from the spec and CLAUDE.md — every task below implicitly includes these.)

- **TDW/TDD (`.agent/rules/test-driven-development.md`):** no implementation code before a failing
  test exists; critical runtime paths (file/DB I/O) are tested with real `tmp_path` SQLite files and
  real file reads, never mocked. Every task below already follows this; Task 2 in particular carries
  a dedicated hand-computed-expected-value test for the account/portfolio total calculation itself
  (not just structural dict-shape checks), since that computation is exactly the logic ADR-030
  settled and the highest-scrutiny piece of arithmetic in this wave.
- **ADR-030 (`ADRs/030_portfolio_totals_computed_not_stored.md`):** portfolio/account totals are
  always computed live from `account_investment`/`investment_price` (CLAUDE.md rule 27's formula),
  never stored as a separate broker-snapshot table. No new schema is added for this domain beyond
  what Wave 0 already created. Read this ADR before Tasks 2–3.
- **This is a pivot, not an addition.** SQLite becomes the primary persistence layer; JSON must not
  remain an active operational store without an approved exception.
- **No permanent hybrid.** A producer/consumer writing or reading both JSON and SQLite forever,
  with no removal trigger, is a failed wave.
- **A domain is migrated only when:** producer writes SQLite + every real consumer reads SQLite +
  old file archived (local-only `mv` for this gitignored domain, never `git mv`/`git add`).
- **No script opens its own SQLite connection outside `py_services/domain_model/`** (Python) or the
  TS service-class layer (TypeScript established in Wave 2 — `InvestmentRepository.ts` pattern).
- **`portfolio.json` is gitignored, private broker/account data (CLAUDE.md critical rules).** Never
  overwrite/delete/modify without explicit user approval. The archive step is **local-only `mv`**,
  never `git mv`, never `git add`ed — the privacy boundary that exists today (never committed) must
  be identical after migration (spec §2.19, §3 resolved decision 3).
- **CLAUDE.md pitfall #27 / portfolio total validation rule:** NEVER compute portfolio totals from
  shares×price. Always use the broker-reported `totals.totalUSD`. `portfolio_io.py`'s
  `load_portfolio_state()` already implements this correctly (falls back to shares×price only when
  `totals` key is absent) — the SQLite-backed replacement must preserve this exact fallback
  behavior, not regress to a naive computation.
- **Validation requirement (spec, Wave 3-specific):** parity must be proven across at least one full
  real broker-sync cycle before archiving — not a one-off snapshot diff, since this is live,
  syncing data (TFSA/RRSP positions and cash change with every trade and price refresh).
- **Wave-level conditional autonomy** (established Wave 2, binding here): execute end-to-end without
  per-task pause; exactly two review points — the dry-run gate before any real write, and the exit
  report before the PR. Hard-stop conditions (spec §6) apply in full throughout.
- **CLAUDE.md rule 14 (worktree-first):** this entire wave happens in a git worktree
  (`worktree-domain-model-v3-wave3`), never directly on `main`.
- **CLAUDE.md rule 15 (worktree lifecycle):** merge is never self-approved; after user merge, sync
  local `main`, remove the worktree, delete local+remote branch, confirm clean state — tracked as
  part of this wave's own completion, not deferred.

---

## Fresh Verification Findings (this session, supersedes the spec §2.4 claim — read before starting any task)

The spec's original inventory (20 producers, ~32 consumers) was re-verified against real current
code, per this migration's standing discipline (every prior wave found the original inventory
wrong). Findings:

### Confirmed REAL producers (5, not 20)

| # | File | Evidence |
|---|---|---|
| 1 | `investment_screener/backend/src/services/BrokerSyncService.ts` | `fs.writeFileSync(PORTFOLIO_FILE, ...)` at line 241 — the primary TV-sync writer |
| 2 | `investment_screener/backend/src/routes/portfolio.ts` | `fs.writeFileSync(PORTFOLIO_FILE, ...)` at lines 262 and 287 (two write paths in one route file) |
| 3 | `investment_screener/backend/py_services/apply_portfolio_updates.py` | `open(PORTFOLIO_PATH, "w")` at line 134 |
| 4 | `investment_screener/backend/py_services/fetch_broker_data.py` | writes `tvSnapshot` block into `portfolio.json` |
| 5 | `plugins/portfolio-advisor/scripts/update_price_levels.py` | writes `portfolio.json`'s denormalized `priceLevelSnapshot` block (separate from its already-migrated Wave 2 `target-portfolio.json` write) |

**Pre-existing drift risk, named but not this wave's job to fix:** `fetch_broker_data.py` exists as
3 separate, non-symlinked, identical-content files (`investment_screener/backend/py_services/`,
`plugins/tradingview/scripts/`, `plugins/tradingview/skills/tv-portfolio-sync/scripts/`) — this
violates the symlink-only rule (CLAUDE.md rule 5) but predates this migration. Rewire the canonical
`py_services/` copy; flag the other two as a symlink-manager cleanup candidate in the exit report,
do not silently fix within this wave's scope.

### Confirmed FALSE POSITIVES (from the spec's 20 claimed producers)

| File | Real finding |
|---|---|
| `market_regime.py` | Already reads `domain_model.sqlite`'s `investment` table directly (Wave 2); explicitly does NOT call `portfolio_io.load_portfolio_state()` (confirmed via its own docstring). Zero portfolio.json touch, read or write. |
| `risk_engine.py` | Real **consumer** (via `portfolio_io.py`), no write path — producer claim false |
| `backtest_harness.py` | Only ever touches `target-portfolio.json` (Wave 2's domain) |
| `thesis_breakers.py` | Only ever touches `target-portfolio.json` |
| `update_thesis.py` | Only ever touches `target-portfolio.json`; the `portfolio.json` mention is a stale boilerplate docstring line |
| `rebalancer.py` | Real **consumer** (via `portfolio_io.py`, confirmed `import portfolio_io`), no write found |
| `ta_sweep_batch.py` | Real **consumer** (reads holdings), no write |
| `extract_portfolio_symbols.py` | Reads `temp/stocks.xlsx` (an Excel file) — never touches `portfolio.json` at all, docstring is stale |
| `validate_weights.py` | Real **consumer** (`--mode current`), writes only `target-portfolio.json` via `--write` |
| `place_order.py` | Real **consumer** (via `portfolio_io.py` + a freshness check); triggers a sync via API/CDP afterward rather than writing the file itself — indirect at most |
| `fetch_financials.py`, `dcf_sensitivity.py`, `standardize_metrics.py`, `comps_valuation.py`, `dcf_scenarios.py` | Single boilerplate docstring line only (`"...portfolio.json (Internal state database)"`, copy-pasted across many `py_services` scripts' auto-generated headers) — zero real usage anywhere else in the file. Same "docstring ≠ evidence" false-positive pattern Waves 1–2 both hit. |

### Newly discovered real touchpoints NOT in the spec's original inventory at all

- **`investment_screener/backend/py_services/portfolio_io.py`** — a shared I/O module whose own
  docstring states: *"Single source of truth for portfolio data I/O. Safe primitives shared by ALL
  portfolio scripts."* Exposes `load_portfolio_state(portfolio_path: Path) -> dict` (returns
  `shares`, `prices`, `total_usd`, `exchange_rate`, `_totals_from_broker`) and `compute_weights(...)`.
  Real confirmed callers (`import portfolio_io` / `from portfolio_io import`): `order_risk_gates.py`,
  `risk_engine.py`, `rebalancer.py`, `plugins/tradingview/scripts/place_order.py`,
  `plugins/portfolio-advisor/scripts/generate_sub_strategy_blocks.py`,
  `plugins/portfolio-advisor/scripts/sync_portfolio_roles.py`,
  `plugins/portfolio-advisor/scripts/generate_portfolio_blueprint.py`. **This is the highest-leverage
  rewiring point in this wave**: rewiring `load_portfolio_state()` itself to read
  `account_investment`/`investment_price` (preserving the exact same return dict shape and the
  broker-total-first fallback rule) cuts over 7 real consumers in one change, instead of 7 separate
  rewires.
- **A real duplication, not a symlink**: `plugins/portfolio-advisor/scripts/generate_portfolio_blueprint.py`
  (goes through `portfolio_io.py`) and `investment_screener/backend/py_services/generate_portfolio_blueprint.py`
  (has its own independent `PORTFOLIO_JSON` constant and direct-read logic) are **two different
  implementations**, not one file symlinked twice. Task 0 below resolves which is canonical before
  any rewiring — do not rewire both independently and risk diverging behavior further.
- **`generate_sub_strategy_blocks.py`, `sync_portfolio_roles.py`** (`plugins/portfolio-advisor/scripts/`)
  — real consumers via `portfolio_io.py`, absent from the spec's original ~32-consumer list entirely.

### Consumers spot-verified real this session (not exhaustive — Task 0 runs the final sweep)

`helpers.ts`, `docs.ts`, `stock.ts`, `screener.ts`, `theses.ts`, `compute_conviction_scores.py`,
`overnight_gaps.py`, `order_risk_gates.py`, `earnings_calendar.py`, `earnings_expectations.py`,
`verify_portfolio_total.py`, `verify_thesis_sync.py`, `portfolio_performance.py`,
`harvest_predictions.py`, `Sidebar.tsx`, `PortfolioModal.tsx`, `Settings.tsx`, `PortfolioTable.tsx`,
`tv_create_alerts.py`, `generate_reports.py`, `watchlist_manager.py`, `generate_review.py`,
`scan_opportunities.py`, `weekly_review.py`, `verify_refresh.py`, both
`generate_portfolio_blueprint.py` copies (duplication noted above), `risk_engine.py`, `rebalancer.py`,
`ta_sweep_batch.py`, `validate_weights.py`, `place_order.py`, `relabel_actions.py`, `daily_brief.py`,
`ThesisService.ts` (reads `portfolio.json` for a display value; it is a *producer* of
`target-portfolio.json`, Wave 2's retained exception, not of `portfolio.json`).

### Confirmed FALSE-POSITIVE consumers (claimed, verified NOT real for `portfolio.json` specifically)

`fetch_financials.py`, `dcf_sensitivity.py`, `standardize_metrics.py`, `comps_valuation.py`,
`dcf_scenarios.py`, `extract_portfolio_symbols.py`, `lock_and_normalize_targets.py` (only ever
touches `target-portfolio.json`).

---

## Wave KPI Table (filled where known; TBD rows resolve in Task 0)

| KPI | Value |
|---|---|
| Wave | 3 |
| Active JSON/JSONL files before | 1 (`portfolio.json`) |
| Active JSON/JSONL files after | 0 active, 1 archived local-only (never committed) |
| Files archived | 1, local-only `mv` (never `git mv`/`git add`) |
| Producers migrated | 5 real / 5 confirmed real (15 of the spec's original 20 claimed producers are confirmed false positives) |
| Consumers migrated | 33 real files spot-confirmed this session (31 spec-claimed minus 7 false positives, plus 2 newly discovered, plus 7 covered transitively via the `portfolio_io.py` rewire) — **TBD exact final count, Task 0 runs the archive-readiness-grep sweep before this number is finalized** |
| Plugin/skill/agent references updated | Per spec §4 table: `tradingview-onboarding.md`, `tv-manage-watchlists`, `tv-portfolio-sync`, plus the full set shared with `target-portfolio.json` (etf_analysis, daily-loop-agent.md, portfolio-advisor-orchestrator.md, etc.) — TBD exact scope, deferred same as Waves 1–2 unless a runtime dependency is found |
| Context-bundle files removed | 1 fewer file (`portfolio.json`) for any skill/agent bundling `investment_screener/backend/data/` — the largest single file in that directory by producer/consumer count |
| Remaining JSON exceptions (with rationale) | 0 expected — `portfolio.json` is fully in scope for this wave, no partial-retention boundary identified so far (unlike Wave 2's `target-portfolio.json`/`thesis_breaker_state.json`); if Task 0 or later tasks find one, it gets a completed Retained-JSON Rationale Bar before being accepted |

## Context Bundle Completion Bar

Per spec §4's plugin/skill reference table, `portfolio.json` is referenced by the same skill set as
`target-portfolio.json` plus `tradingview-onboarding.md`, `tv-manage-watchlists`, `tv-portfolio-sync`.
After this wave's cutover, any of these skills/agents that currently instruct bundling
`investment_screener/backend/data/portfolio.json` directly should instead reference the
`account_investment`/`investment_price` repository query methods. Full doc-text sweep is **deferred**
(same category Waves 1–2 left open) unless a runtime dependency is found during Task 0 or the
consumer rewiring tasks — tracked as an open item in the exit report either way, not silently
dropped.

## Archive/Retention Decision

`portfolio.json` archives via **local-only `mv`** to
`ARCHIVE/investment_screener/backend/data/portfolio.json` — never `git mv`, never `git add`ed (spec
§2.19, CLAUDE.md critical rules). No Retained-JSON Rationale Bar is expected to be needed (unlike
Wave 2's two retained exceptions) — full-document CRUD equivalents (`routes/portfolio.ts`'s reads
and writes) map cleanly onto `account`/`account_investment`/`investment_price` with no field losing
a home, per Wave 0's already-approved schema. If Task 0 or a later task discovers a field with no
column destination (mirroring Wave 2's `globalSettings`/`bandConfig` discovery), stop and present it
to the user before proceeding, exactly as Wave 2 did — do not silently drop data or expand schema
without approval.

## Stop Conditions (spec §6, restated, binding throughout)

Stop and escalate to the user if any of: live app still reads old JSON after being claimed migrated;
a plugin/skill/agent still writes JSON as source of truth after cutover; SQLite tables exist but
runtime still reads JSON; a producer writes both JSON and SQLite indefinitely with no removal
trigger; a parity mismatch appears during the dual-write window; a consumer is discovered mid-wave
not in this document's (corrected) inventory — amend the inventory, don't silently work around it; a
cleanup/archive step would remove data needed for rollback; the real broker-sync parity proof
(required for this domain specifically) has not been run before any archive step.

---

## Task 0: Final pre-implementation verification sweep

**Files:** none created — this is a read-only investigation task, output is a decision log appended
to this plan's tracking (or a short `docs/superpowers/status/wave3-task0-findings.md` if findings are
substantial enough to warrant their own file, at the implementer's discretion).

**Why this task exists:** every prior wave found its own inventory wrong even after a first
investigation pass (Wave 1: 144→82 files; Wave 2: 7 of 11 producers were false positives, 2 real
consumers missing entirely). This session's fresh-verification pass above is more thorough than any
wave's starting point, but it is not exhaustive — it did not run a full archive-readiness-style
repo-wide grep, only targeted checks against the spec's claimed file list. Task 0 closes that gap
before any rewiring begins.

- [ ] **Step 1: Repo-wide grep for every real `portfolio.json` touchpoint, not just claimed files**

Run:
```bash
grep -rln "portfolio\.json\|PORTFOLIO_FILE\|PORTFOLIO_PATH\|PORTFOLIO_JSON" \
  investment_screener plugins .agents \
  --include="*.ts" --include="*.tsx" --include="*.py" --include="*.js" \
  2>/dev/null | grep -v "/tests/\|test_\|\.test\.\|ARCHIVE/\|node_modules\|__pycache__"
```
Expected: a superset list. Cross-reference every hit against the "Confirmed REAL"/"Confirmed FALSE
POSITIVE" tables above. Any file not already classified must be read and classified now — real
producer, real consumer, or false positive (docstring-only/stale) — with the same evidence standard
used above (an actual `open(...)`/`fs.writeFileSync`/`fs.readFileSync`/`json.load` call, not a
comment or docstring line).

- [ ] **Step 2: Resolve the two `generate_portfolio_blueprint.py` implementations**

Read both `investment_screener/backend/py_services/generate_portfolio_blueprint.py` and
`plugins/portfolio-advisor/scripts/generate_portfolio_blueprint.py` in full. Determine: are they
functionally equivalent (candidates to collapse into one canonical file + symlinks per
`symlink_manager.py`, a `dev-utils:symlink-manager` skill task, not silently done here), or do they
serve genuinely different purposes (in which case both are real, independent consumers requiring
independent rewiring)? Record the decision and rationale before Task 8 (below) touches either file.
If they should be collapsed, that collapse is **out of this wave's scope** — name it as a tracked
follow-up in the exit report, do not expand scope mid-wave to fix unrelated duplication.

- [ ] **Step 3: Confirm no other shared I/O module exists besides `portfolio_io.py`**

Run: `grep -rln "def load_portfolio\|Single source of truth for portfolio" investment_screener plugins --include="*.py" 2>/dev/null | grep -v ARCHIVE`
Expected: only `portfolio_io.py` and its test file match. If a second shared loader is found, add it
to the producer/consumer table before Task 4.

- [ ] **Step 4: Confirm real TFSA/RRSP account shape in `portfolio.json`**

Run: `python3 -c "import json; d = json.load(open('investment_screener/backend/data/portfolio.json')); print(list(d.keys())); print(type(d.get('holdings')))"`
from the repo root. Confirm the real top-level shape (holdings array + totals + tvSnapshot, per
`portfolio_io.py`'s own parsing logic) matches what Tasks 2–3 below assume. If the real shape differs
(e.g. a nested per-account structure not yet accounted for), stop and revise Tasks 2–3 before
proceeding — do not guess at the account/holding mapping.

- [ ] **Step 5: Record findings and get explicit go/no-go before Task 1**

If Task 0 finds the inventory materially different from this plan's tables above (a new real
producer, a false positive presented here as real, a blocking schema mismatch), stop and present the
finding to the user before continuing — same discipline as Wave 2's Task 0. If findings match this
plan's tables (expected outcome, since this session's pass was already thorough), proceed directly to
Task 1 without a pause.

---

## Task 1: Seed real TFSA/RRSP account rows + `investment_price_repository.py`

**Files:**
- Create: `investment_screener/backend/py_services/domain_model/investment_price_repository.py`
- Create: `investment_screener/backend/py_services/domain_model/seed_real_accounts.py`
- Test: `investment_screener/backend/tests/py_services/test_investment_price_repository.py`
- Test: `investment_screener/backend/tests/py_services/test_seed_real_accounts.py`

**Interfaces:**
- Consumes: `domain_model.db_client.initialize_db` (Wave 0), `domain_model.account_repository.upsert_account` (Wave 0, already tested).
- Produces:
  - `upsert_investment_price(conn, investment_id: str, price: float, currency: str, fetched_at: str) -> None`
  - `get_investment_price(conn, investment_id: str) -> dict | None`
  - `seed_real_accounts(conn) -> None` — idempotently seeds `TFSA` and `RRSP` account rows per CLAUDE.md's documented account structure (TFSA primary/larger, RRSP mirrors at ~1/3 share count).

- [ ] **Step 1: Write the failing tests**

```python
# investment_screener/backend/tests/py_services/test_investment_price_repository.py
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.investment_repository import resolve_investment  # noqa: E402
from domain_model.investment_price_repository import (  # noqa: E402
    upsert_investment_price,
    get_investment_price,
)


def test_upsert_investment_price_creates_and_is_idempotent(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    aapl_id = resolve_investment(conn, "AAPL", asset_class="EQUITY", currency="USD")
    upsert_investment_price(conn, aapl_id, price=150.0, currency="USD", fetched_at="2026-07-20T00:00:00Z")
    upsert_investment_price(conn, aapl_id, price=155.5, currency="USD", fetched_at="2026-07-20T01:00:00Z")
    row = get_investment_price(conn, aapl_id)
    assert row["price"] == 155.5  # last write wins, not a duplicate row
    cursor = conn.execute("SELECT COUNT(*) FROM investment_price WHERE investment_id = ?;", (aapl_id,))
    assert cursor.fetchone()[0] == 1


def test_get_investment_price_returns_none_for_unknown(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    assert get_investment_price(conn, "does-not-exist") is None
```

```python
# investment_screener/backend/tests/py_services/test_seed_real_accounts.py
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.account_repository import list_accounts  # noqa: E402
from domain_model.seed_real_accounts import seed_real_accounts  # noqa: E402


def test_seed_creates_tfsa_and_rrsp(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    seed_real_accounts(conn)
    accounts = {a["account_id"] for a in list_accounts(conn)}
    assert accounts == {"TFSA", "RRSP"}


def test_seed_is_idempotent(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    seed_real_accounts(conn)
    seed_real_accounts(conn)
    assert len(list_accounts(conn)) == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_investment_price_repository.py tests/py_services/test_seed_real_accounts.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

```python
# investment_screener/backend/py_services/domain_model/investment_price_repository.py
"""All ``investment_price`` table reads and writes live here (ADR-029 anti-duplication rule)."""

import sqlite3


def upsert_investment_price(
    conn: sqlite3.Connection,
    investment_id: str,
    price: float,
    currency: str,
    fetched_at: str,
) -> None:
    conn.execute(
        "INSERT INTO investment_price (investment_id, price, currency, fetched_at) "
        "VALUES (?, ?, ?, ?) "
        "ON CONFLICT(investment_id) DO UPDATE SET "
        "price=excluded.price, currency=excluded.currency, fetched_at=excluded.fetched_at;",
        (investment_id, price, currency, fetched_at),
    )
    conn.commit()


def get_investment_price(conn: sqlite3.Connection, investment_id: str) -> dict | None:
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(
        "SELECT * FROM investment_price WHERE investment_id = ?;", (investment_id,)
    )
    row = cursor.fetchone()
    return dict(row) if row else None
```

```python
# investment_screener/backend/py_services/domain_model/seed_real_accounts.py
"""One-time-per-wave seed: the two real accounts (CLAUDE.md account structure).

TFSA is primary (larger); RRSP mirrors at ~1/3 share count. Both are real,
named accounts — not free-text strings — so Wave 3's producers/consumers can
resolve against a stable account_id instead of parsing account names out of
portfolio.json's structure ad hoc.
"""

import sqlite3

from account_repository import upsert_account


def seed_real_accounts(conn: sqlite3.Connection) -> None:
    upsert_account(conn, "TFSA", "TFSA", "TFSA", base_currency="CAD")
    upsert_account(conn, "RRSP", "RRSP", "RRSP", base_currency="CAD")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_investment_price_repository.py tests/py_services/test_seed_real_accounts.py -v`
Expected: `4 passed`.

- [ ] **Step 5: Commit**

```bash
git add investment_screener/backend/py_services/domain_model/investment_price_repository.py \
        investment_screener/backend/py_services/domain_model/seed_real_accounts.py \
        investment_screener/backend/tests/py_services/test_investment_price_repository.py \
        investment_screener/backend/tests/py_services/test_seed_real_accounts.py
git commit -m "feat: add investment_price_repository + real TFSA/RRSP account seed (Wave 3 Task 1)"
```

---

## Task 2: `portfolio_repository.py` — SQL aggregation expressed against the relational model

**Files:**
- Create: `investment_screener/backend/py_services/domain_model/portfolio_repository.py`
- Test: `investment_screener/backend/tests/py_services/test_portfolio_repository.py`

**Interfaces:**
- Consumes: `account_investment`/`investment`/`investment_price` tables directly via SQL (Wave 0 +
  Task 1's schema) — this module queries the tables itself rather than looping over rows fetched
  through `list_account_investments()`/`get_investment_price()` one at a time (see design note
  below for why).
- Produces:
  - `get_account_market_values(conn) -> dict[str, float]` — `{account_id: market_value_usd}`, one
    row per real account, via a single `GROUP BY account_id` SQL query.
  - `get_portfolio_total_value(conn) -> float` — the portfolio-wide total, computed by summing
    `get_account_market_values()`'s own per-account results (account boundaries are rolled up into
    the portfolio total, never computed as a separate flat query that could silently cross account
    lines — see design note below).
  - `load_portfolio_state_from_db(conn) -> dict` — same return shape as
    `portfolio_io.py::load_portfolio_state()` (`shares`, `prices`, `total_usd`, `exchange_rate`,
    `_totals_from_broker`), a thin compatibility shim over the two functions above, so
    `portfolio_io.py` can delegate here without changing its own public signature (Task 4 does that
    rewire) and its 7+ real callers keep working unchanged.

**Design note — align the calculation with the SQLite relational model, not a reconstructed JSON
tree.** The old JSON model was a nested tree (`portfolio → accounts → holdings`), and the original
draft of this task's code walked it the same way in Python (`for ai in account_investments: ...`,
fetching one row at a time via repository helper calls and summing in application code). That is
the wrong shape for the new model. The SQLite schema is relational
(`account` / `account_investment` / `investment` / `investment_price`), and the calculations belong
expressed as SQL against those relations — `JOIN account_investment TO investment_price, GROUP BY`
— not as nested Python loops reconstructing the old tree. This is not a performance optimization;
it is matching the calculation's shape to the data's actual shape.

**Design note — preserve account boundaries before rolling up to a portfolio total.** This is the
direct lesson from Task 0's real finding: the original plan's bug was treating all holdings as one
flat, unscoped collection and only discovering afterward that real per-account attribution mattered
(every RRSP holding would have silently landed in TFSA). To make that class of bug structurally
harder to reintroduce, `get_portfolio_total_value()` is **not** its own independent flat
`SUM(quantity × price)` query across every row regardless of account — it is explicitly the sum of
`get_account_market_values()`'s per-account results. Every portfolio-level number in this module
must be derivable by summing account-level numbers this module already computed, never by a
separate query that skips the account grouping step.

**Design note — no persistence for totals (ADR-030, unchanged, restated for this task
specifically).** `ADRs/030_portfolio_totals_computed_not_stored.md` settled: store accounts,
holdings, quantities, prices, and cash facts; compute account market value, portfolio total value,
and allocation percentages live; do not store account totals, portfolio totals, or other calculated
aggregates in any table. This task's two new functions are pure read-time SQL queries — neither
writes anything. Reconciling the computed total against the broker's own reported figure
(`totals.totalUSD` from the live sync payload) remains `verify_portfolio_total.py`'s job (Task 7),
not this module's.

- [ ] **Step 1: Write the failing test**

```python
# investment_screener/backend/tests/py_services/test_portfolio_repository.py
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.account_repository import upsert_account  # noqa: E402
from domain_model.investment_repository import resolve_investment  # noqa: E402
from domain_model.investment_price_repository import upsert_investment_price  # noqa: E402
from domain_model.account_investment_repository import upsert_account_investment  # noqa: E402
from domain_model.portfolio_repository import (  # noqa: E402
    get_account_market_values,
    get_portfolio_total_value,
    load_portfolio_state_from_db,
)


def _seed_two_accounts(conn):
    """AAPL held in both TFSA (10 sh @ $150) and RRSP (3 sh @ $150) -- deliberately
    the exact shape Task 0 found real data has (same symbol, different accounts,
    different quantities), to guard against the RRSP-collapses-into-TFSA bug class.
    """
    upsert_account(conn, "TFSA", "TFSA", "TFSA")
    upsert_account(conn, "RRSP", "RRSP", "RRSP")
    aapl_id = resolve_investment(conn, "AAPL", asset_class="EQUITY", currency="USD")
    upsert_investment_price(conn, aapl_id, price=150.0, currency="USD", fetched_at="2026-07-20T00:00:00Z")
    upsert_account_investment(
        conn, "TFSA", aapl_id, quantity=10, average_cost=140.0,
        book_value=1400.0, currency="USD", last_synced_at="2026-07-20T00:00:00Z",
    )
    upsert_account_investment(
        conn, "RRSP", aapl_id, quantity=3, average_cost=140.0,
        book_value=420.0, currency="USD", last_synced_at="2026-07-20T00:00:00Z",
    )
    return aapl_id


def test_get_account_market_values_keeps_accounts_separate(tmp_path):
    """The direct regression guard for Task 0's real finding: TFSA and RRSP must
    never be collapsed into a single figure before the account-level query returns.
    """
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    _seed_two_accounts(conn)
    values = get_account_market_values(conn)
    assert values == {"TFSA": 1500.0, "RRSP": 450.0}  # 10*150, 3*150 -- never summed together here


def test_get_portfolio_total_value_is_the_sum_of_account_values(tmp_path):
    """The portfolio total must be traceable as SUM(per-account values), not an
    independent flat query -- this is what "preserve account boundaries before
    rolling up" means concretely.
    """
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    _seed_two_accounts(conn)
    account_values = get_account_market_values(conn)
    total = get_portfolio_total_value(conn)
    assert total == sum(account_values.values()) == 1950.0


def test_get_portfolio_total_value_includes_cash_investment_rows(tmp_path):
    """Cash is a real INVESTMENT row (asset_class='CASH', Wave 0 resolved decision 5),
    held via account_investment like any other position -- it must count toward the
    account and portfolio totals the same way a stock position does.
    """
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    _seed_two_accounts(conn)
    cash_id = resolve_investment(conn, "CASH_USD", asset_class="CASH", currency="USD")
    upsert_investment_price(conn, cash_id, price=1.0, currency="USD", fetched_at="2026-07-20T00:00:00Z")
    upsert_account_investment(
        conn, "TFSA", cash_id, quantity=250.0, average_cost=1.0,
        book_value=250.0, currency="USD", last_synced_at="2026-07-20T00:00:00Z",
    )
    account_values = get_account_market_values(conn)
    assert account_values["TFSA"] == 1750.0  # 1500 (AAPL) + 250 (cash)
    assert get_portfolio_total_value(conn) == 2200.0  # 1750 (TFSA) + 450 (RRSP)


def test_load_portfolio_state_from_db_returns_shares_prices_and_total(tmp_path):
    """The portfolio_io.py-compatible shape -- shares/prices aggregated across
    accounts by symbol (portfolio_io.py's own existing aggregation contract),
    total_usd delegated to get_portfolio_total_value() (single source of truth
    for the total, not a second independent computation)."""
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    _seed_two_accounts(conn)
    state = load_portfolio_state_from_db(conn)
    assert state["shares"]["AAPL"] == 13  # 10 (TFSA) + 3 (RRSP), aggregated by symbol across accounts
    assert state["prices"]["AAPL"] == 150.0
    assert state["total_usd"] == get_portfolio_total_value(conn) == 1950.0
    assert state["_totals_from_broker"] is False  # per ADR-030: always computed, never a stored broker column
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_portfolio_repository.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

```python
# investment_screener/backend/py_services/domain_model/portfolio_repository.py
"""Portfolio/account value calculations expressed against the relational model
(account_investment JOIN investment_price, GROUP BY account_id), not as Python
loops reconstructing the old JSON tree shape.

Per ADR-030: these are read-time-only queries. No table stores an account or
portfolio total -- every number here is computed fresh from account_investment/
investment_price on each call. Account boundaries are preserved first
(get_account_market_values' GROUP BY), and the portfolio total is always the
sum of those per-account results (get_portfolio_total_value), never an
independent flat query -- this is the direct fix for the bug class Task 0
found (RRSP holdings silently collapsing into TFSA).
"""

import sqlite3


def get_account_market_values(conn: sqlite3.Connection) -> dict[str, float]:
    """Market value per real account: SUM(quantity * price), grouped by account_id.

    Includes cash rows (asset_class='CASH' investments held via account_investment
    like any other position, per Wave 0's resolved decision 5) -- no special-casing,
    the JOIN treats them identically to equity positions.
    """
    cursor = conn.execute(
        """
        SELECT ai.account_id AS account_id, SUM(ai.quantity * ip.price) AS market_value
        FROM account_investment ai
        JOIN investment_price ip ON ip.investment_id = ai.investment_id
        GROUP BY ai.account_id;
        """
    )
    return {row[0]: row[1] for row in cursor.fetchall()}


def get_portfolio_total_value(conn: sqlite3.Connection) -> float:
    """Portfolio-wide total: the sum of get_account_market_values()'s own results.

    Deliberately not a separate flat SUM(quantity * price) query with no
    GROUP BY -- the portfolio total must always be traceable as a rollup of
    account-level totals, never a query that can silently ignore account
    boundaries.
    """
    return sum(get_account_market_values(conn).values())


def load_portfolio_state_from_db(conn: sqlite3.Connection) -> dict:
    """portfolio_io.py::load_portfolio_state()-compatible shape.

    shares/prices are aggregated across accounts by symbol (matching
    portfolio_io.py's own existing aggregation contract for its 7+ real
    callers); total_usd delegates to get_portfolio_total_value() so there is
    exactly one computation of the total in this codebase, not two.
    """
    cursor = conn.execute(
        """
        SELECT i.symbol AS symbol, SUM(ai.quantity) AS total_shares, MAX(ip.price) AS price
        FROM account_investment ai
        JOIN investment i ON i.investment_id = ai.investment_id
        LEFT JOIN investment_price ip ON ip.investment_id = ai.investment_id
        GROUP BY i.symbol;
        """
    )
    shares: dict[str, float] = {}
    prices: dict[str, float] = {}
    for symbol, total_shares, price in cursor.fetchall():
        if total_shares and total_shares > 0:
            shares[symbol] = total_shares
        if price and price > 0:
            prices[symbol] = price

    return {
        "shares": shares,
        "prices": prices,
        "total_usd": get_portfolio_total_value(conn),
        "exchange_rate": 1.38,
        "_totals_from_broker": False,  # per ADR-030: always computed, never stored/read from a broker column
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_portfolio_repository.py -v`
Expected: `4 passed`.

- [ ] **Step 5: Commit**

```bash
git add investment_screener/backend/py_services/domain_model/portfolio_repository.py \
        investment_screener/backend/tests/py_services/test_portfolio_repository.py
git commit -m "feat: add portfolio_repository — SQL aggregation against the relational model, account boundaries preserved before rollup (Wave 3 Task 2)"
```

---

## Task 3: Migration script (dry-run mode + gated `--write`)

**Files:**
- Create: `investment_screener/backend/py_services/domain_model/migrate_portfolio_to_sqlite.py`
- Test: `investment_screener/backend/tests/py_services/test_migrate_portfolio_to_sqlite.py`

**Interfaces:**
- Consumes: `seed_real_accounts` (Task 1), `upsert_account_investment` (Wave 0),
  `upsert_investment_price` (Task 1), `resolve_investment` (Wave 0).
- Produces: `run_dry_run_migration(portfolio_path) -> dict` (report only, no DB writes),
  `run_real_migration(portfolio_path, db_path) -> dict` (real writes, gated on `--write`), mirroring
  `migrate_target_portfolio_to_sqlite.py`'s dry-run/write-gate pattern exactly.

- [ ] **Step 1: Write the failing test**

```python
# investment_screener/backend/tests/py_services/test_migrate_portfolio_to_sqlite.py
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.account_repository import list_accounts  # noqa: E402
from domain_model.account_investment_repository import list_account_investments  # noqa: E402
from domain_model.migrate_portfolio_to_sqlite import (  # noqa: E402
    run_dry_run_migration,
    run_real_migration,
)

FIXTURE_PORTFOLIO = {
    "holdings": [
        {"symbol": "AAPL", "shares": 13, "price": 150.0},
    ],
    "totals": {"totalUSD": 1950.0, "totalCAD": 2691.0, "exchangeRate": 1.38, "totalSource": "tv_authoritative"},
    "tvSnapshot": {
        "accounts": [
            {"accountType": "TFSA", "accountId": "acct-tfsa-1", "displayText": "TFSA - acct-tfsa-1"},
            {"accountType": "RRSP", "accountId": "acct-rrsp-1", "displayText": "RRSP - acct-rrsp-1"},
        ],
        "snapshots": [
            {
                "accountType": "TFSA", "accountId": "acct-tfsa-1",
                "balances": {"cashUSD": 100.0, "cashCAD": 0.0},
                "positions": [
                    {"symbol": "AAPL", "direction": "Long", "quantity": 10, "avgFillPrice": 140.0, "positionId": "p1"},
                ],
            },
            {
                "accountType": "RRSP", "accountId": "acct-rrsp-1",
                "balances": {"cashUSD": 50.0, "cashCAD": 0.0},
                "positions": [
                    {"symbol": "AAPL", "direction": "Long", "quantity": 3, "avgFillPrice": 140.0, "positionId": "p2"},
                ],
            },
        ],
    },
}


def test_dry_run_does_not_touch_any_db(tmp_path):
    portfolio_path = tmp_path / "portfolio.json"
    portfolio_path.write_text(json.dumps(FIXTURE_PORTFOLIO))
    report = run_dry_run_migration(str(portfolio_path))
    assert report["positions_count"] == 2  # one position row per (account, symbol), not per aggregated holding
    assert report["accounts_found"] == {"TFSA", "RRSP"}
    # No db_path was ever passed -- dry run cannot have written anything.


def test_real_migration_writes_account_investments_per_real_account(tmp_path):
    """Per ADR-030 / Task 0's finding: real per-account attribution comes from
    tvSnapshot.snapshots[].positions[], never from an invented "account" field
    on the flat holdings[] array (which has no such field in real data)."""
    portfolio_path = tmp_path / "portfolio.json"
    portfolio_path.write_text(json.dumps(FIXTURE_PORTFOLIO))
    db_path = str(tmp_path / "test.sqlite")
    report = run_real_migration(str(portfolio_path), db_path)
    assert report["account_investments_written"] == 2  # TFSA:AAPL, RRSP:AAPL

    conn = initialize_db(db_path)
    accounts = {a["account_id"] for a in list_accounts(conn)}
    assert accounts == {"TFSA", "RRSP"}
    rows = {r["account_id"]: r for r in list_account_investments(conn)}
    assert rows["TFSA"]["quantity"] == 10
    assert rows["TFSA"]["average_cost"] == 140.0
    assert rows["RRSP"]["quantity"] == 3


def test_real_migration_writes_cash_as_investment_rows(tmp_path):
    """Wave 0 resolved decision 5: cash is a real INVESTMENT row (asset_class='CASH'),
    held via account_investment like any other position -- not a separate table."""
    portfolio_path = tmp_path / "portfolio.json"
    portfolio_path.write_text(json.dumps(FIXTURE_PORTFOLIO))
    db_path = str(tmp_path / "test.sqlite")
    run_real_migration(str(portfolio_path), db_path)

    conn = initialize_db(db_path)
    rows = list_account_investments(conn, account_id="TFSA")
    cash_investment_ids = [r["investment_id"] for r in rows if r["investment_id"] == "CASH_USD"]
    assert cash_investment_ids  # TFSA's $100 cash balance became a CASH_USD account_investment row


def test_real_migration_is_idempotent(tmp_path):
    portfolio_path = tmp_path / "portfolio.json"
    portfolio_path.write_text(json.dumps(FIXTURE_PORTFOLIO))
    db_path = str(tmp_path / "test.sqlite")
    run_real_migration(str(portfolio_path), db_path)
    run_real_migration(str(portfolio_path), db_path)
    conn = initialize_db(db_path)
    rows = list_account_investments(conn)
    assert len(rows) == 4  # TFSA:AAPL, TFSA:CASH_USD, RRSP:AAPL, RRSP:CASH_USD -- re-run does not duplicate
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_migrate_portfolio_to_sqlite.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

```python
# investment_screener/backend/py_services/domain_model/migrate_portfolio_to_sqlite.py
"""Migrate portfolio.json (gitignored, real broker/account holdings) into
account_investment/investment_price. Dry-run by default; --write is gated,
same discipline as migrate_target_portfolio_to_sqlite.py (Wave 2).

Per ADR-030 and Task 0's real-shape finding: per-account attribution comes
from tvSnapshot.snapshots[].positions[] (real accountType/accountId, real
quantity/avgFillPrice) -- NOT from the flat, cross-account-aggregated
holdings[] array, which carries no per-account field in real data. Cash
(balances.cashUSD/cashCAD per account) becomes CASH_USD/CASH_CAD
account_investment rows per Wave 0's resolved decision 5, not a separate
table. The current market price for each symbol still comes from the flat
holdings[] array (the only place a live per-symbol price appears), joined
by symbol.
"""

import argparse
import json
from datetime import datetime, timezone

from account_repository import upsert_account
from account_investment_repository import upsert_account_investment
from investment_price_repository import upsert_investment_price
from investment_repository import resolve_investment
from db_client import initialize_db
from seed_real_accounts import seed_real_accounts


def _load_snapshots(portfolio_path: str) -> list[dict]:
    with open(portfolio_path) as f:
        data = json.load(f)
    return data.get("tvSnapshot", {}).get("snapshots", [])


def _load_prices_by_symbol(portfolio_path: str) -> dict[str, float]:
    with open(portfolio_path) as f:
        data = json.load(f)
    prices = {}
    for h in data.get("holdings", []):
        symbol = h.get("symbol") or h.get("ticker")
        price = float(h.get("price") or h.get("book_price") or 0)
        if symbol and price > 0:
            prices[symbol] = price
    return prices


def run_dry_run_migration(portfolio_path: str) -> dict:
    snapshots = _load_snapshots(portfolio_path)
    accounts_found = {s["accountType"] for s in snapshots}
    positions_count = sum(len(s.get("positions", [])) for s in snapshots)
    return {
        "positions_count": positions_count,
        "accounts_found": accounts_found,
    }


def run_real_migration(portfolio_path: str, db_path: str) -> dict:
    snapshots = _load_snapshots(portfolio_path)
    prices_by_symbol = _load_prices_by_symbol(portfolio_path)
    conn = initialize_db(db_path)
    seed_real_accounts(conn)

    now = datetime.now(timezone.utc).isoformat()
    written = 0
    for snap in snapshots:
        account_id = snap["accountType"]
        if account_id not in ("TFSA", "RRSP"):
            continue  # CASH account (a real broker sub-account, not TFSA/RRSP) is out of this
            # wave's seeded-account scope; named in the exit report, not silently dropped.
        upsert_account(conn, account_id, account_id, account_id)

        for pos in snap.get("positions", []):
            symbol = pos["symbol"]
            investment_id = resolve_investment(conn, symbol, asset_class="EQUITY", currency="USD")
            price = prices_by_symbol.get(symbol, 0)
            if price > 0:
                upsert_investment_price(conn, investment_id, price=price, currency="USD", fetched_at=now)
            upsert_account_investment(
                conn,
                account_id,
                investment_id,
                quantity=float(pos.get("quantity") or 0),
                average_cost=pos.get("avgFillPrice"),
                book_value=None,
                currency="USD",
                last_synced_at=now,
            )
            written += 1

        cash_usd = float(snap.get("balances", {}).get("cashUSD") or 0)
        if cash_usd > 0:
            cash_id = resolve_investment(conn, "CASH_USD", asset_class="CASH", currency="USD")
            upsert_account_investment(
                conn, account_id, cash_id, quantity=cash_usd, average_cost=1.0,
                book_value=cash_usd, currency="USD", last_synced_at=now,
            )
            written += 1

    return {"account_investments_written": written}


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate portfolio.json into account_investment/investment_price.")
    parser.add_argument("--portfolio-path", default="investment_screener/backend/data/portfolio.json")
    parser.add_argument("--db-path", default="investment_screener/backend/data/domain_model.sqlite")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    if args.write:
        report = run_real_migration(args.portfolio_path, args.db_path)
        print("[WRITE MODE]", json.dumps(report, indent=2, default=list))
    else:
        report = run_dry_run_migration(args.portfolio_path)
        print("[DRY RUN]", json.dumps(report, indent=2, default=list))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_migrate_portfolio_to_sqlite.py -v`
Expected: `5 passed`.

- [ ] **Step 5: Commit**

```bash
git add investment_screener/backend/py_services/domain_model/migrate_portfolio_to_sqlite.py \
        investment_screener/backend/tests/py_services/test_migrate_portfolio_to_sqlite.py
git commit -m "feat: add portfolio.json migration script, dry-run + gated --write (Wave 3 Task 3)"
```

- [ ] **Step 6: Run the real dry-run against the real, private `portfolio.json` and review with the user**

Run:
```bash
cd investment_screener/backend/py_services
python3 -m domain_model.migrate_portfolio_to_sqlite \
  --portfolio-path ../data/portfolio.json \
  --db-path ../data/domain_model.sqlite
```
**This is the mandatory dry-run gate.** Present the real holding/account counts to the user for
explicit review before any `--write` run. Per this wave's validation requirement, do not proceed to
`--write` until the user has seen and approved the real numbers — this is real, private financial
data, higher stakes than Wave 2's target-weight data.

---

## Task 4: Rewire `portfolio_io.py` (the highest-leverage cutover point)

**Files:**
- Modify: `investment_screener/backend/py_services/portfolio_io.py`
- Test: `investment_screener/backend/tests/py_services/test_portfolio_io.py` (already exists — extend it)

**Interfaces:**
- Consumes: `domain_model.portfolio_repository.load_portfolio_state_from_db` (Task 2).
- Produces: `load_portfolio_state(portfolio_path: Path | None = None) -> dict` — same public name,
  same return shape, but now backed by SQLite. `portfolio_path` becomes optional/unused-but-accepted
  (kept for call-site compatibility with the 7 real callers found this session — none of their call
  sites need to change if the parameter is still accepted, even if ignored).

**Why this task is the highest-priority rewire:** per this session's findings, `portfolio_io.py` is
already the shared abstraction point for 7 real consumers (`order_risk_gates.py`, `risk_engine.py`,
`rebalancer.py`, `place_order.py`, `generate_sub_strategy_blocks.py`, `sync_portfolio_roles.py`, and
one of the two `generate_portfolio_blueprint.py` implementations). Rewiring this one file cuts over
all 7 in a single change, rather than editing each call site.

- [ ] **Step 1: Read the existing test file to see current coverage**

Run: `cat investment_screener/backend/tests/py_services/test_portfolio_io.py`

- [ ] **Step 2: Write the new failing test for the SQLite-backed path**

Add to `test_portfolio_io.py`:

```python
def test_load_portfolio_state_reads_from_sqlite_not_json(tmp_path, monkeypatch):
    """After Wave 3's cutover, load_portfolio_state() must read domain_model.sqlite,
    not portfolio.json -- even if a stale portfolio.json still exists on disk.
    """
    from domain_model.db_client import initialize_db
    from domain_model.account_repository import upsert_account
    from domain_model.investment_repository import resolve_investment
    from domain_model.investment_price_repository import upsert_investment_price
    from domain_model.account_investment_repository import upsert_account_investment

    db_path = str(tmp_path / "test.sqlite")
    conn = initialize_db(db_path)
    upsert_account(conn, "TFSA", "TFSA", "TFSA")
    aapl_id = resolve_investment(conn, "AAPL", asset_class="EQUITY", currency="USD")
    upsert_investment_price(conn, aapl_id, price=200.0, currency="USD", fetched_at="2026-07-20T00:00:00Z")
    upsert_account_investment(
        conn, "TFSA", aapl_id, quantity=5, average_cost=180.0,
        book_value=900.0, currency="USD", last_synced_at="2026-07-20T00:00:00Z",
    )

    monkeypatch.setattr("portfolio_io._DB_PATH", db_path)

    # A stale portfolio.json exists but must NOT be read.
    stale_json = tmp_path / "portfolio.json"
    stale_json.write_text('{"holdings": [{"symbol": "MSFT", "shares": 999, "price": 1.0}]}')

    state = load_portfolio_state(stale_json)
    assert state["shares"] == {"AAPL": 5}
    assert "MSFT" not in state["shares"]
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_portfolio_io.py::test_load_portfolio_state_reads_from_sqlite_not_json -v`
Expected: FAIL (current implementation reads the JSON file, so `MSFT` would appear).

- [ ] **Step 4: Rewire the implementation**

Replace `portfolio_io.py`'s `load_portfolio_state` function body:

```python
# investment_screener/backend/py_services/portfolio_io.py
# (imports section gains:)
from pathlib import Path as _Path
_HERE = _Path(__file__).resolve().parent
_DB_PATH = str(_HERE / ".." / "data" / "domain_model.sqlite")


def load_portfolio_state(portfolio_path: Path) -> dict[str, Any]:
    """Read the portfolio state from domain_model.sqlite (Wave 3 cutover).

    ``portfolio_path`` is accepted for call-site compatibility with existing
    callers but is no longer read -- SQLite is the sole source of truth for
    this domain after Wave 3. See docs/superpowers/status/wave3-*-report.md
    for the migration record.
    """
    import sys as _sys
    sys.path.insert(0, str(_HERE.parent / "domain_model")) if False else None  # placeholder removed below
    from domain_model.db_client import initialize_db
    from domain_model.portfolio_repository import load_portfolio_state_from_db

    conn = initialize_db(_DB_PATH)
    try:
        return load_portfolio_state_from_db(conn)
    finally:
        conn.close()
```

(The implementer must clean up the placeholder `sys.path` line above during actual implementation —
it is left visibly wrong here only to flag that the real import path must be verified against how
`portfolio_io.py`'s existing imports resolve `domain_model` today; do not ship the placeholder line
as-is. Confirm the working import pattern via `python3 -c "from domain_model.db_client import initialize_db"`
run from `py_services/` before finalizing.)

- [ ] **Step 5: Run test to verify it passes**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_portfolio_io.py -v`
Expected: all tests pass, including the new one.

- [ ] **Step 6: Run every real caller's own test suite to catch regressions**

Run:
```bash
cd investment_screener/backend
python3 -m pytest tests/py_services/ -k "order_risk_gates or risk_engine or rebalancer or place_order or generate_sub_strategy_blocks or sync_portfolio_roles or generate_portfolio_blueprint" -v
```
Expected: all pass. Any failure here means one of the 7 real callers depends on a `portfolio_io.py`
behavior this rewire changed unintentionally — fix before proceeding, do not silence the test.

- [ ] **Step 7: Commit**

```bash
git add investment_screener/backend/py_services/portfolio_io.py \
        investment_screener/backend/tests/py_services/test_portfolio_io.py
git commit -m "feat: rewire portfolio_io.load_portfolio_state onto domain_model.sqlite (Wave 3 Task 4, cuts over 7 real consumers)"
```

---

## Task 5: Rewire the 5 confirmed real producers

**Files:**
- Modify: `investment_screener/backend/src/services/BrokerSyncService.ts`
- Modify: `investment_screener/backend/src/routes/portfolio.ts`
- Modify: `investment_screener/backend/py_services/apply_portfolio_updates.py`
- Modify: `investment_screener/backend/py_services/fetch_broker_data.py`
- Modify: `plugins/portfolio-advisor/scripts/update_price_levels.py`

**Interfaces:**
- Consumes (Python side): `domain_model.migrate_portfolio_to_sqlite`'s per-holding write logic
  (Task 3), refactored into a small reusable `upsert_holding(conn, account_id, symbol, shares, price, ...)`
  helper if 2+ of these scripts need the same per-holding write shape (avoid duplicating the
  same 6-line upsert block 3 times — extract it into `portfolio_repository.py` from Task 2 as
  `write_holding()` if this task finds real duplication, following this codebase's DRY convention).
- Consumes (TS side): a new `PortfolioRepository.ts` (mirroring `InvestmentRepository.ts`'s
  Wave 2 pattern) exposing `upsertAccountInvestment(accountId, investmentId, quantity, ...)`.

**This task's steps are written per-file below since each has a different real write shape found
during this session's investigation — do not treat them as identical mechanical edits.**

- [ ] **Step 1: Create `PortfolioRepository.ts` (TS-side repository, mirrors Wave 2's `InvestmentRepository.ts`)**

First read `investment_screener/backend/src/services/InvestmentRepository.ts` in full (the Wave 2
precedent) to match its exact connection-handling and error-handling conventions before writing
this file — do not invent a different pattern for the TS side of this domain.

- [ ] **Step 2: Write a failing test for `PortfolioRepository.ts.upsertAccountInvestment`**

Follow the exact test structure of `InvestmentRepository.spec.ts` (Wave 2) — read that file first,
then write `PortfolioRepository.spec.ts` with the same `tmp`-database-per-test setup, asserting a
round-trip write+read for a fixture account/investment/quantity, and an idempotency test (same
shape as this plan's Python tests above).

- [ ] **Step 3: Implement `PortfolioRepository.ts` minimally, run the test, confirm pass, commit.**

```bash
git add investment_screener/backend/src/services/PortfolioRepository.ts \
        investment_screener/backend/tests/api/PortfolioRepository.spec.ts
git commit -m "feat: add PortfolioRepository.ts (TS-side account_investment writer, Wave 3 Task 5.1)"
```

- [ ] **Step 4: Rewire `BrokerSyncService.ts`'s write path (line 241) to call `PortfolioRepository.upsertAccountInvestment` instead of `fs.writeFileSync(PORTFOLIO_FILE, ...)`**

Read the full 30 lines around line 241 first (the sync write logic) before editing — this is the
primary TV-sync writer for real, live account data; do not simplify its existing merge/dedup logic
while rewiring the storage target. Write a test asserting a sync call results in real
`account_investment` rows (using the same `tmp`-database pattern), run it, confirm it fails against
the pre-rewire code, implement, confirm it passes, run the full `BrokerSyncService.spec.ts` suite to
check for regressions, then commit.

- [ ] **Step 5: Rewire `routes/portfolio.ts`'s two write paths (lines 262, 287)**

Same process: read the full route handlers around both lines first (these handle explicit
user-triggered portfolio edits, not just sync), write a failing test per handler, implement, verify,
run the full `portfolio.spec.ts`/`routes` test suite, commit.

- [ ] **Step 6: Rewire `apply_portfolio_updates.py`'s write (line 134)**

Read the full script first — it's a smaller, more contained CLI tool. Write a failing test using the
same `tmp_path` SQLite pattern established in this plan's earlier tasks, implement using
`account_investment_repository.upsert_account_investment` directly (no need for the full
`portfolio_repository.py` abstraction for a single-holding CLI tool), verify, commit.

- [ ] **Step 7: Rewire `fetch_broker_data.py`'s `tvSnapshot` write**

Read the full write_snapshot()/promote flow first (lines ~28-193 per this session's grep). This is
the canonical file (`investment_screener/backend/py_services/fetch_broker_data.py`) — the other 2
duplicate copies (`plugins/tradingview/scripts/`, `plugins/tradingview/skills/tv-portfolio-sync/scripts/`)
are NOT rewired in this task (named as a symlink-manager follow-up in Task 0's findings) unless Task
0's Step 1 sweep found they are independently invoked at runtime (if so, escalate — that would mean
3 independent live write paths for the same file, a real correctness risk beyond this wave's
original scope). Write a failing test, implement, verify, commit.

- [ ] **Step 8: Rewire `update_price_levels.py`'s `portfolio.json` snapshot write (separate from its already-migrated `target-portfolio.json` write)**

Read the "2. Update portfolio.json snapshot" section (around line 284 per this session's grep) in
full. Write a failing test, implement using `account_investment_repository`/a
`priceLevelSnapshot`-equivalent write (confirm with Task 0 whether `price_level_tier`, already
migrated in Wave 2, already covers this denormalized snapshot need, or whether a genuinely new
column/table is required — do not duplicate schema that already exists), verify, commit.

---

## Task 6: Rewire remaining direct-read consumers not covered by the `portfolio_io.py` cutover

**Added after Task 5's review: `routes/portfolio.ts`'s own remaining read endpoints are now this
task's highest-priority item, not an afterthought.** Task 5 (producer rewire) found that 4 of 5
producers had to become dual-writers (JSON write kept, SQLite write added) rather than full
replacements, specifically because `routes/portfolio.ts`'s `/summary`, `/weights`,
`/strategy-allocation`, `/position/:ticker`, and `/holdings/:ticker` endpoints still read
`portfolio.json` directly (`totals`, per-account `tvSnapshot.positions[]`) and were never part of
`portfolio_io.py`'s Task 4 cutover. **This is the specific, named removal trigger for those 4
producers' dual-writes** (per this plan's Global Constraints: "No permanent hybrid... a producer
writing both JSON and SQLite forever, with no removal trigger, is a failed wave") — once these
endpoints are rewired here, Task 8 can safely stop treating `portfolio.json` as load-bearing and the
dual-writes from Task 5 can be reduced to SQLite-only in the same pass (or a fast, explicit follow-up
inside this task — do not leave the dual-write in place past this task's completion).

**For `/summary`'s `totals` specifically**: per ADR-030, this is NOT a new-schema question — the
portfolio-wide total is computed live via `portfolio_repository.get_portfolio_total_value()`
(Python) / the TS equivalent on `PortfolioRepository.ts`, never read from a stored `totals` JSON
block or a new table. Wire `/summary` to call that function, matching CLAUDE.md rule 27's formula
exactly (the same computation `portfolio_io.py` already delegates to since Task 4) — this closes the
"totals has no SQLite equivalent" gap Task 5's report flagged, without any schema change.

**Files:** (each read individually before editing, per this plan's established discipline — do not
batch-edit without reading first)
`routes/portfolio.ts` (`/summary`, `/weights`, `/strategy-allocation`, `/position/:ticker`,
`/holdings/:ticker` — the 4 dual-write producers' removal trigger, see above), `helpers.ts`,
`docs.ts`, `stock.ts`, `screener.ts`, `theses.ts`, `compute_conviction_scores.py`,
`overnight_gaps.py`, `earnings_calendar.py`, `earnings_expectations.py`, `verify_portfolio_total.py`,
`verify_thesis_sync.py`, `portfolio_performance.py`, `harvest_predictions.py`, `Sidebar.tsx`,
`PortfolioModal.tsx`, `Settings.tsx`, `PortfolioTable.tsx`, `tv_create_alerts.py`,
`generate_reports.py`, `watchlist_manager.py`, `generate_review.py`, `scan_opportunities.py`,
`weekly_review.py`, `verify_refresh.py`, `ThesisService.ts`, and whichever of the two
`generate_portfolio_blueprint.py` files Task 0 determined does NOT go through `portfolio_io.py`
(Task 0 corrected this: it's one real file reachable via a symlink, not two implementations —
`portfolio_io.py`'s Task 4 cutover already covers its one real read path, so no separate action is
needed here beyond confirming that).

**`POST /` on `routes/portfolio.ts`** (the flat manual-edit path, `items` array with no per-account
attribution) is confirmed out of scope for SQLite dual-write per Task 5's own finding — writing a
fabricated single-account split for a flat aggregate would corrupt real `account_investment` data.
Leave it JSON-only with the inline comment Task 5 already added; do not force a rewire here.

**Process for each file (same as Wave 2's Task 10/11 pattern):**
1. Read the file's real current portfolio.json read logic in full.
2. Write a failing test asserting the function reads from `domain_model.sqlite` (via
   `portfolio_repository.load_portfolio_state_from_db` for Python, `PortfolioRepository.ts` for TS)
   instead of the JSON file — same `tmp_path`/`tmp`-database pattern as every prior task.
3. Implement the minimal rewire.
4. Run the test, confirm pass.
5. Run that file's own existing test suite (not just the new test) to catch regressions — this
   migration's standing discipline (Wave 2 caught a real test-leak regression exactly this way).
6. Commit with a message following the pattern `feat: rewire <file> onto domain_model.sqlite (Wave 3 Task 6)`.

**When reducing Task 5's 4 dual-write producers to SQLite-only**: also update
`test_fetch_broker_data_persist.py::test_write_snapshot_also_persists_to_domain_model_sqlite`, which
currently asserts the JSON `tvSnapshot` write is unchanged (`written_json["tvSnapshot"] == SNAPSHOT`)
— a one-line assertion that will need updating once the JSON write is actually dropped for this
producer, flagged by Task 5's review so it doesn't silently block the removal.

**Batch these commits by natural grouping** (TS route/component files together, Python
portfolio-advisor scripts together, tradingview scripts together) rather than one commit per file,
mirroring Wave 2's `26056cba`/`6658883f`-style grouped commits — but each file still gets its own
failing-test-first cycle, grouping is only for the commit boundary, not the TDD cycle.

**If dispatching sub-batches of this task to background agents:** per the Wave 2 handoff's explicit
lesson (a background agent hit an API session limit mid-file, leaving a broken orphaned worktree),
instruct every dispatched batch to commit after each single file, not batches, and independently
verify via direct test runs and grep before folding any orphaned worktree's work back in.

---

## Task 7: Real broker-sync parity proof (this domain's specific validation requirement)

**Files:** none created — this is a live validation task, output is evidence recorded in the exit
report.

**Why this task is required and unique to Wave 3:** the spec's Validation Strategy requires parity
proven across at least one full real broker-sync cycle before archiving, specifically because
`portfolio.json` is live, syncing data (unlike Waves 1–2's more static domains) — a one-off snapshot
diff is not sufficient evidence.

- [ ] **Step 1: Trigger one real broker sync** (via the already-rewired `BrokerSyncService.ts`/
  `fetch_broker_data.py` from Task 5) against the real TradingView CDP connection, per this repo's
  documented `tv-portfolio-sync` flow.

- [ ] **Step 2: Diff the resulting `account_investment`/`investment_price` rows against the
  pre-cutover `portfolio.json`'s holdings** for the same sync cycle — every ticker's `quantity`,
  `average_cost` (if present), and `price` must match exactly, not approximately.

- [ ] **Step 3: Confirm `load_portfolio_state()` (Task 4's rewired version) returns the same
  `shares`/`prices` dict the pre-rewire JSON-backed version would have returned** for
  this same real sync snapshot — a direct before/after comparison, not a fixture test.

- [ ] **Step 4: Reconcile the computed `total_usd` against the broker's own reported total —
  this is the account-value calculation's real-data test, not a fixture.** Per ADR-030,
  `load_portfolio_state_from_db()`'s `total_usd` is always computed (`SUM(quantity × price)` across
  every `account_investment` row including cash); it is never read from a stored broker figure.
  Compare it against the same real sync cycle's `totals.totalUSD` (the raw broker-reported figure
  from the sync payload, captured before archiving in Task 8). Record both numbers and the variance
  in the exit report. A small variance (price movement/refresh lag — expect low single-digit dollars
  to tens of dollars depending on position count) is expected and not a defect. A large variance
  (on the order of hundreds to thousands of dollars, matching the ~$1,277 gap Task 0 originally found
  between the file's own `totals.totalUSD` and the sum of its three accounts' `totalEquityUSDCombined`
  figures) is a real signal — investigate before proceeding to Task 8's archive step, do not average
  it away or treat it as acceptable noise. If `verify_portfolio_total.py` already has a variance
  threshold/test for this, run it against this real cycle's numbers and report its verdict directly
  rather than eyeballing the two figures.

- [ ] **Step 5: Record the parity evidence in the exit report** (Task 9) — real ticker-by-ticker
  counts and the Step 4 reconciliation numbers, not "looks correct."

---

## Task 8: Archive `portfolio.json` (local-only, never committed)

**Files:**
- Move (local-only, never `git mv`/`git add`): `investment_screener/backend/data/portfolio.json` →
  `ARCHIVE/investment_screener/backend/data/portfolio.json`

- [ ] **Step 1: Archive-readiness grep** — confirm zero real I/O matches remain outside the confirmed
  producer/consumer list:
```bash
grep -rn "portfolio\.json" investment_screener plugins .agents \
  --include="*.ts" --include="*.tsx" --include="*.py" --include="*.js" \
  2>/dev/null | grep -v "/tests/\|test_\|\.test\.\|ARCHIVE/\|node_modules\|__pycache__\|^.*#.*docs\|SKILL\.md\|\.md:"
```
Expected: zero real-I/O matches (doc/comment/SKILL.md mentions excluded per this migration's
established convention, verified individually if any appear ambiguous).

- [ ] **Step 2: Repository-path (anti-bypass) grep** — confirm no script opens its own SQLite
  connection against `account_investment`/`investment_price` outside `domain_model/` (Python) or
  `PortfolioRepository.ts`/`InvestmentRepository.ts` (TypeScript):
```bash
grep -rn "sqlite3.connect\|better-sqlite3" investment_screener plugins --include="*.py" --include="*.ts" 2>/dev/null | grep -v "domain_model/\|/tests/\|Repository\.ts"
```
Expected: only the pre-existing `intelligence.sqlite`-domain hits already documented in Wave 1/2's
own reports (a different database file, Wave 5 territory) — no new bypass.

- [ ] **Step 3: Run the full backend test suite one more time, immediately before archiving**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/ -v 2>&1 | tail -30` and
the TS equivalent. Compare against the documented pre-existing baseline (per Wave 2's report: 24
failed/1282 passed Python, 72 passed/1 failed TS) — any *new* failure blocks archiving.

- [ ] **Step 4: Archive, local-only**

```bash
mkdir -p ARCHIVE/investment_screener/backend/data
mv investment_screener/backend/data/portfolio.json ARCHIVE/investment_screener/backend/data/portfolio.json
```
**Do not `git add` this move.** Confirm with `git status` that neither the old nor new path appears
as a tracked change (both are gitignored) — this preserves the privacy boundary exactly as it
existed before migration, per spec §2.19.

- [ ] **Step 5: Re-run the full test suite immediately after the archive, confirm identical results
  to Step 3.**

---

## Task 9: Wave 3 exit report + handoff + fresh-session Wave 4 kickoff prompt

**Files:**
- Create: `docs/superpowers/status/wave3-account-holdings-report.md`
- Create: `docs/superpowers/status/wave3-handoff.md`
- Create: `docs/superpowers/status/wave4-kickoff-prompt.md`

- [ ] **Step 1: Fill in the Wave KPI table with real, final numbers** (not the TBD placeholders in
  this plan's own table above) — real producer count, real consumer count after Task 0's sweep and
  Task 6's rewiring, real bugs found and fixed, real broker-sync parity evidence from Task 7.

- [ ] **Step 2: Write the Producer/Consumer Cutover Table** with one row per real file, each ending
  in `Cutover status: DONE`, following Wave 2's exit report table format exactly.

- [ ] **Step 3: Record any real bugs found and fixed during this wave** (same section format as
  Wave 1's 6 and Wave 2's 7 — do not omit this section even if fewer bugs were found; state that
  explicitly if so).

- [ ] **Step 4: Write the Definition of Done — Verified section**, checking off all 9 items from the
  spec, with real evidence for each (not a status label).

- [ ] **Step 5: Write the handoff doc** following `wave2-handoff.md`'s exact structure: what Wave 3
  accomplished, inventory-correction summary (this plan's own findings above, updated with Task 0's
  final results), open issues, exact branch/commit references, instructions for the next fresh
  session (confirm Wave 3's PR merged before starting Wave 4, re-verify Wave 4's own claimed
  producer/consumer list fresh — same standing instruction every wave has carried forward).

- [ ] **Step 6: Write the Wave 4 kickoff prompt**, self-contained, following this same
  `wave3-kickoff-prompt.md`'s structure, so a fresh session with zero context can start Wave 4
  (Portfolio Operations — trade log, order executions, cash flows) without re-deriving anything
  from this conversation.

- [ ] **Step 7: Commit and open the PR** (do not merge it yourself).

```bash
git add docs/superpowers/status/wave3-account-holdings-report.md \
        docs/superpowers/status/wave3-handoff.md \
        docs/superpowers/status/wave4-kickoff-prompt.md
git commit -m "docs: Wave 3 (account holdings) exit report + handoff + Wave 4 kickoff prompt"
gh pr create --title "Wave 3: Account holdings (portfolio.json) migration to SQLite domain model" \
  --body "See docs/superpowers/status/wave3-account-holdings-report.md and wave3-handoff.md for full detail."
```

### Hard Checkpoint — Do Not Start Wave 4 Until This Is Reviewed

Same standing instruction as every prior wave: stop here. Present the exit report to the user. Do
not merge the PR yourself unless explicitly told to. Do not start Wave 4's own detailed task-level
planning until the user has reviewed this wave's outcome, per CLAUDE.md rule 15's full worktree
lifecycle (PR review → user merge → your post-merge sync/cleanup → only then may the next wave's
planning begin).

---

## Self-Review

**1. Spec coverage:** This plan implements spec §2.4's account-holdings domain in full: both target
tables (`account_investment`, `investment_price`), the local-only archive rule (§2.19), the
broker-sync-cycle validation requirement specific to this domain, and the corrected (not assumed)
producer/consumer inventory. Task 0 explicitly closes the gap between this session's targeted
verification and a true archive-readiness-grade sweep before any schema/rewiring decision is
finalized.

**2. Placeholder scan:** One placeholder was deliberately left visible in Task 4 Step 4 (the
`sys.path` line) with an explicit flag telling the implementer to resolve it against
`portfolio_io.py`'s real existing import pattern rather than guessing — this is intentional
signposting of a real open question (how `portfolio_io.py` currently resolves the `domain_model`
package import, which was not directly observed this session), not an unresolved "TBD" left by
oversight. Every other task has complete, concrete code. Task 2's `total_usd` scalar-column question
is explicitly gated on Task 0's Step 4 finding, not silently assumed — this is intentional
sequencing (Task 0 runs first), not a placeholder.

**3. Type consistency:** `load_portfolio_state_from_db(conn) -> dict` (Task 2) returns exactly the
same key set (`shares`, `prices`, `total_usd`, `exchange_rate`, `_totals_from_broker`) that
`portfolio_io.py`'s existing `load_portfolio_state()` returns (confirmed by reading the real file
this session), and Task 4's rewire preserves that exact shape. `upsert_account_investment`'s
generated ID format and parameter order matches Wave 0's already-tested signature throughout.
