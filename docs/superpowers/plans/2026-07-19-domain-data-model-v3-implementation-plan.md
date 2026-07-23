# Domain Data Model v3.2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate InvestmentToolkit's fragmented JSON/JSONL persistence into the v3.2 SQLite
domain model, wave by wave, with each wave provably reducing JSON dependency rather than adding
SQLite alongside it.

**Architecture:** `ACCOUNT`/`INVESTMENT`/`ACCOUNT_INVESTMENT` core (new
`py_services/domain_model/` package, mirroring the existing `py_services/intelligence/` package's
repository-per-table pattern) plus the existing `intelligence_event` ledger for narrative/event
domains. No script outside these two owning packages ever opens its own SQLite connection.

**Tech Stack:** Python 3.13 (`sqlite3` stdlib, WAL mode), pytest (`tmp_path` fixtures + real-repo
integration tests), TypeScript/Express (Node's `better-sqlite3` or equivalent — confirm against
`ProjectionService.ts`'s existing dependencies before Wave 1), existing `py_services/intelligence/`
package as the established pattern to mirror.

## Global Constraints

(Copied verbatim from `docs/superpowers/specs/2026-07-19-domain-data-model-v3-implementation-design.md` — every task below implicitly includes these.)

- **This is a pivot, not an addition.** SQLite/domain repositories become the primary persistence
  layer for applicable operational data; JSON/JSONL must not remain an active operational store
  without an explicit approved exception (spec §2.18).
- **No permanent hybrid.** `JSON + JSONL + SQLite` forever is a failed wave, not a resting state.
- **A domain is migrated only when:** producer writes SQLite + every real consumer reads SQLite +
  old file archived via `git mv` (or local-only `mv` for gitignored files, spec §2.19). Table
  existence, data copying, or a passing fixture test do not count.
- **No script opens its own SQLite connection outside the owning repository/service layer** — this
  applies identically to Python (`py_services/intelligence/`, `py_services/domain_model/`) and
  TypeScript (service classes are the sole DB callers for their tables).
- **Every wave reports:** the Wave KPI table (JSON files before/after, files archived, reads/writes
  removed, producers/consumers migrated, context-bundle files removed, remaining exceptions named).
- **Archive convention:** `ARCHIVE/<mirrored source path>` via `git mv`; gitignored/private files
  archive locally only, never `git add`ed (spec §2.19).
- **Wave order:** 0 (schema/repo foundation) → 1 (projections) → 2 (investment/target/watchlist +
  price levels + notes + alerts + thesis breaker state) → 3 (account holdings) → 4 (trade
  log/orders/cash flows) → 5A–5E (generated research views → TA sweep → daily briefs → predictions
  → account policy).
- **A "real data migration write" must run against the main checkout's actual gitignored data
  files and actual `domain_model.sqlite`, never a worktree's copy.** Added 2026-07-22 after Wave
  4's real `--write` migration ran successfully inside the wave worktree, was independently
  verified there, and the wave was reported/merged as complete — but the worktree has its own
  separate, gitignored `domain_model.sqlite` and source JSON files that git never syncs back to
  the main checkout (the same gitignored-private-data distinction this plan already applies to
  `portfolio.json`/`cash_flows.json` archiving, just not carried through to where the migration
  *write* itself runs). Post-merge, `main`'s own live database still had zero rows in the new
  tables while the newly-cut-over code was already reading exclusively from SQLite — caught only
  because the user asked for worktree cleanup, not by the wave's own verification steps. **Fix:**
  any task that performs the real `--write` step, and any verification of its row counts, must
  explicitly target the main checkout's file paths (not rely on a worktree-relative default), and
  the wave's exit report must state which `domain_model.sqlite` (main vs. worktree) was verified.

---

## Wave 0: Schema and Repository Foundation

**Scope:** Create the full v3.2 schema and the `investment`/`account`/`account_investment`
repository layer. No JSON file is touched, read, or archived in this wave — it exists solely so
Wave 1 (`projection_version` needs a resolvable `investment_id`) has something to reference.
This wave's "Wave KPI table" is trivially all-zero (no JSON files are affected yet) — that is the
correct, honest report for a foundation wave, not a gap.

### Task 1: `py_services/domain_model` package + `db_client.py` schema

**Files:**
- Create: `investment_screener/backend/py_services/domain_model/__init__.py` (empty)
- Create: `investment_screener/backend/py_services/domain_model/db_client.py`
- Test: `investment_screener/backend/tests/py_services/test_domain_model_db_client.py`

**Interfaces:**
- Produces: `initialize_db(db_path: str) -> sqlite3.Connection` — opens (creating if absent) the
  domain-model SQLite file, applies `PRAGMA journal_mode=WAL`/`PRAGMA foreign_keys=ON`, and
  `CREATE TABLE IF NOT EXISTS` for every v3.2 table. Mirrors
  `py_services/intelligence/db_client.py::initialize_db`'s signature exactly so later
  repositories/tests use the same calling convention.

- [ ] **Step 1: Write the failing test**

```python
# investment_screener/backend/tests/py_services/test_domain_model_db_client.py
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from domain_model.db_client import initialize_db  # noqa: E402

EXPECTED_TABLES = {
    "account",
    "investment",
    "account_investment",
    "investment_price",
    "strategy_pillar",
    "sub_strategy",
    "price_level_set",
    "price_level_tier",
    "alert",
    "investment_note",
    "projection_version",
    "projection_scenario",
    "trade_log_entry",
    "order_execution",
    "cash_flow",
    "cash_flow_baseline",
    "portfolio_policy",
}


def test_initialize_db_creates_every_v32_table(tmp_path):
    conn = initialize_db(str(tmp_path / "domain_model_test.sqlite"))
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
    )
    actual_tables = {row[0] for row in cursor.fetchall()}
    missing = EXPECTED_TABLES - actual_tables
    assert not missing, f"Missing tables: {missing}"


def test_initialize_db_enforces_foreign_keys(tmp_path):
    conn = initialize_db(str(tmp_path / "domain_model_test.sqlite"))
    cursor = conn.execute("PRAGMA foreign_keys;")
    assert cursor.fetchone()[0] == 1


def test_initialize_db_is_idempotent(tmp_path):
    db_path = str(tmp_path / "domain_model_test.sqlite")
    conn1 = initialize_db(db_path)
    conn1.close()
    conn2 = initialize_db(db_path)  # must not raise on re-open of existing file
    cursor = conn2.execute("SELECT COUNT(*) FROM investment;")
    assert cursor.fetchone()[0] == 0


def test_investment_symbol_unique_constraint_enforced(tmp_path):
    conn = initialize_db(str(tmp_path / "domain_model_test.sqlite"))
    conn.execute(
        "INSERT INTO investment (investment_id, symbol, asset_class, currency, updated_at) "
        "VALUES ('aapl-1', 'AAPL', 'EQUITY', 'USD', '2026-07-19T00:00:00Z');"
    )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO investment (investment_id, symbol, asset_class, currency, updated_at) "
            "VALUES ('aapl-2', 'AAPL', 'EQUITY', 'USD', '2026-07-19T00:00:00Z');"
        )


def test_account_investment_unique_account_plus_investment_enforced(tmp_path):
    conn = initialize_db(str(tmp_path / "domain_model_test.sqlite"))
    conn.execute(
        "INSERT INTO account (account_id, account_name, account_type) VALUES ('TFSA', 'TFSA', 'TFSA');"
    )
    conn.execute(
        "INSERT INTO investment (investment_id, symbol, asset_class, currency, updated_at) "
        "VALUES ('aapl-1', 'AAPL', 'EQUITY', 'USD', '2026-07-19T00:00:00Z');"
    )
    conn.execute(
        "INSERT INTO account_investment "
        "(account_investment_id, account_id, investment_id, quantity, last_synced_at) "
        "VALUES ('TFSA:aapl-1', 'TFSA', 'aapl-1', 10, '2026-07-19T00:00:00Z');"
    )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO account_investment "
            "(account_investment_id, account_id, investment_id, quantity, last_synced_at) "
            "VALUES ('TFSA:aapl-1-dup', 'TFSA', 'aapl-1', 5, '2026-07-19T01:00:00Z');"
        )


def test_projection_version_unique_investment_plus_version_enforced(tmp_path):
    conn = initialize_db(str(tmp_path / "domain_model_test.sqlite"))
    conn.execute(
        "INSERT INTO investment (investment_id, symbol, asset_class, currency, updated_at) "
        "VALUES ('aapl-1', 'AAPL', 'EQUITY', 'USD', '2026-07-19T00:00:00Z');"
    )
    conn.execute(
        "INSERT INTO projection_version (projection_id, investment_id, version, saved_at) "
        "VALUES ('p1', 'aapl-1', 1, '2026-07-19T00:00:00Z');"
    )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO projection_version (projection_id, investment_id, version, saved_at) "
            "VALUES ('p2', 'aapl-1', 1, '2026-07-19T01:00:00Z');"
        )


def test_projection_scenario_unique_projection_plus_scenario_name_enforced(tmp_path):
    conn = initialize_db(str(tmp_path / "domain_model_test.sqlite"))
    conn.execute(
        "INSERT INTO investment (investment_id, symbol, asset_class, currency, updated_at) "
        "VALUES ('aapl-1', 'AAPL', 'EQUITY', 'USD', '2026-07-19T00:00:00Z');"
    )
    conn.execute(
        "INSERT INTO projection_version (projection_id, investment_id, version, saved_at) "
        "VALUES ('p1', 'aapl-1', 1, '2026-07-19T00:00:00Z');"
    )
    conn.execute(
        "INSERT INTO projection_scenario (scenario_id, projection_id, scenario_name) "
        "VALUES ('s1', 'p1', 'base');"
    )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO projection_scenario (scenario_id, projection_id, scenario_name) "
            "VALUES ('s2', 'p1', 'base');"
        )


def test_expected_indexes_exist(tmp_path):
    conn = initialize_db(str(tmp_path / "domain_model_test.sqlite"))
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='index';")
    actual_indexes = {row[0] for row in cursor.fetchall()}
    expected_indexes = {
        "idx_investment_pillar",
        "idx_investment_lifecycle",
        "idx_account_investment_account",
        "idx_account_investment_investment",
        "idx_projection_investment",
        "idx_projection_scenario_projection",
        "idx_alert_investment",
        "idx_investment_note_investment",
    }
    missing = expected_indexes - actual_indexes
    assert not missing, f"Missing indexes: {missing}"
```

Add `import sqlite3` and `import pytest` to the top of this test file alongside the existing
imports (both are needed for the `IntegrityError`/`raises` assertions above).

- [ ] **Step 2: Run test to verify it fails**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_domain_model_db_client.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'domain_model'`

- [ ] **Step 3: Write minimal implementation**

Copy the column-level DDL for every table from
`docs/architecture/domain-data-model.md` (§ "v3 Column-Level Schema", plus the `alert` and
`projection_version`/`projection_scenario` blocks in the same file) and
`docs/architecture/supplementary-domain-schemas.md` (§ "Domain 2, 3, 4" —
`trade_log_entry`/`order_execution`/`cash_flow`/`cash_flow_baseline`) and
`docs/architecture/domain-data-model.md` (§ "Missing top-level PORTFOLIO/config entity" —
`portfolio_policy`). Every `CREATE TABLE` statement already exists verbatim in those two files —
this task transcribes them into executable DDL, it does not invent new columns.

```python
# investment_screener/backend/py_services/domain_model/db_client.py
import sqlite3


def initialize_db(db_path: str) -> sqlite3.Connection:
    """Open (creating if absent) the v3.2 domain-model SQLite database.

    Mirrors ``py_services/intelligence/db_client.py::initialize_db``'s calling
    convention: WAL mode, foreign keys on, idempotent schema creation.
    """
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")

    conn.execute("""
    CREATE TABLE IF NOT EXISTS account (
        account_id      TEXT PRIMARY KEY,
        account_name    TEXT NOT NULL,
        account_type    TEXT,
        base_currency   TEXT NOT NULL DEFAULT 'CAD'
    );
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS strategy_pillar (
        pillar_id       TEXT PRIMARY KEY,
        name            TEXT NOT NULL,
        target_weight   REAL
    );
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS sub_strategy (
        sub_strategy_id TEXT PRIMARY KEY,
        pillar_id       TEXT REFERENCES strategy_pillar(pillar_id),
        name            TEXT NOT NULL
    );
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS investment (
        investment_id              TEXT PRIMARY KEY,
        symbol                      TEXT NOT NULL,
        name                        TEXT,
        asset_class                 TEXT NOT NULL,
        currency                    TEXT NOT NULL DEFAULT 'USD',
        lifecycle_status            TEXT,
        target_weight               REAL,
        target_action               TEXT,
        standing_decision_type      TEXT,
        standing_decision_reason    TEXT,
        standing_decision_source    TEXT,
        standing_decision_review    TEXT,
        pillar_id                   TEXT REFERENCES strategy_pillar(pillar_id),
        sub_strategy_id             TEXT REFERENCES sub_strategy(sub_strategy_id),
        thesis_for_inclusion        TEXT,
        agent_rationale             TEXT,
        is_watchlisted              INTEGER NOT NULL DEFAULT 0,
        watchlist_added_at          TEXT,
        latest_projection_id        TEXT REFERENCES projection_version(projection_id),
        latest_research_event_id    TEXT,
        thesis_breaker_status       TEXT,
        updated_at                  TEXT NOT NULL,
        UNIQUE(symbol)
    );
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS investment_price (
        investment_id   TEXT PRIMARY KEY REFERENCES investment(investment_id),
        price           REAL NOT NULL,
        currency        TEXT NOT NULL DEFAULT 'USD',
        fetched_at      TEXT NOT NULL
    );
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS account_investment (
        account_investment_id   TEXT PRIMARY KEY,
        account_id              TEXT NOT NULL REFERENCES account(account_id),
        investment_id           TEXT NOT NULL REFERENCES investment(investment_id),
        quantity                REAL NOT NULL DEFAULT 0,
        average_cost            REAL,
        book_value              REAL,
        currency                TEXT NOT NULL DEFAULT 'USD',
        last_synced_at          TEXT NOT NULL,
        UNIQUE(account_id, investment_id)
    );
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS price_level_set (
        price_level_set_id  TEXT PRIMARY KEY,
        investment_id       TEXT NOT NULL REFERENCES investment(investment_id),
        schema_version      TEXT,
        last_updated        TEXT,
        last_updated_by     TEXT,
        note                TEXT
    );
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS price_level_tier (
        tier_id              TEXT PRIMARY KEY,
        price_level_set_id   TEXT NOT NULL REFERENCES price_level_set(price_level_set_id),
        tier_kind            TEXT NOT NULL DEFAULT 'BUY_TIER',
        tier_number          INTEGER NOT NULL,
        price                REAL,
        action               TEXT,
        trim_pct             REAL,
        order_type           TEXT,
        basis                TEXT,
        source               TEXT,
        source_date          TEXT,
        condition            TEXT,
        status               TEXT
    );
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS alert (
        alert_id        TEXT PRIMARY KEY,
        investment_id   TEXT REFERENCES investment(investment_id),
        alert_type      TEXT,
        message         TEXT,
        price           REAL,
        condition_json  TEXT,
        active          INTEGER NOT NULL DEFAULT 1,
        resolution      TEXT,
        created_at      TEXT,
        last_fired_at   TEXT,
        expiration_at   TEXT,
        synced_at       TEXT NOT NULL
    );
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_alert_investment ON alert(investment_id);")

    conn.execute("""
    CREATE TABLE IF NOT EXISTS investment_note (
        note_id         TEXT PRIMARY KEY,
        investment_id   TEXT NOT NULL REFERENCES investment(investment_id),
        note_date       TEXT NOT NULL,
        note_type       TEXT,
        body            TEXT NOT NULL,
        source          TEXT
    );
    """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_investment_note_investment "
        "ON investment_note(investment_id, note_date);"
    )

    conn.execute("""
    CREATE TABLE IF NOT EXISTS projection_version (
        projection_id         TEXT PRIMARY KEY,
        investment_id         TEXT NOT NULL REFERENCES investment(investment_id),
        version               INTEGER NOT NULL,
        saved_at              TEXT NOT NULL,
        analyzed_at           TEXT,
        model                 TEXT,
        fair_value            REAL,
        action                TEXT,
        rationale             TEXT,
        research_event_id     TEXT,
        snapshot_json         TEXT,
        analytics_log_json    TEXT,
        UNIQUE(investment_id, version)
    );
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS projection_scenario (
        scenario_id         TEXT PRIMARY KEY,
        projection_id       TEXT NOT NULL REFERENCES projection_version(projection_id),
        scenario_name       TEXT NOT NULL,
        weight              REAL,
        growth_rate         REAL,
        net_margin          REAL,
        exit_pe             REAL,
        quality_multiplier  REAL,
        share_change        REAL,
        rationale           TEXT,
        moat_score          INTEGER,
        management_score    INTEGER,
        year5_revenue       REAL,
        year5_net_income    REAL,
        year5_eps           REAL,
        scenario_price      REAL,
        risks_json          TEXT,
        UNIQUE(projection_id, scenario_name)
    );
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS trade_log_entry (
        entry_id        TEXT PRIMARY KEY,
        investment_id   TEXT NOT NULL REFERENCES investment(investment_id),
        account_id      TEXT REFERENCES account(account_id),
        action          TEXT,
        shares          REAL,
        price           REAL,
        total_cost      REAL,
        order_type      TEXT,
        limit_price     REAL,
        trade_date      TEXT,
        notes           TEXT,
        status          TEXT,
        source          TEXT,
        priority        TEXT,
        logged_at       TEXT
    );
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS order_execution (
        execution_id      TEXT PRIMARY KEY,
        executed_at       TEXT NOT NULL,
        investment_id     TEXT NOT NULL REFERENCES investment(investment_id),
        side              TEXT,
        shares            REAL,
        price             REAL,
        decision          TEXT,
        gate_result_json  TEXT
    );
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS cash_flow (
        flow_id                             TEXT PRIMARY KEY,
        flow_date                           TEXT,
        flow_type                           TEXT,
        amount_cad                          REAL,
        portfolio_value_before_flow_cad      REAL,
        account                              TEXT
    );
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS cash_flow_baseline (
        account                TEXT PRIMARY KEY,
        starting_balance_cad   REAL,
        starting_date          TEXT
    );
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS portfolio_policy (
        policy_id                                TEXT PRIMARY KEY,
        rebalance_frequency                      TEXT,
        portfolio_value_usd_target               REAL,
        max_marginal_risk_contribution_pct        REAL,
        max_cluster_variance_contribution_pct      REAL,
        rebalance_band_relative_pct                REAL,
        rebalance_band_absolute_pct                REAL,
        rebalance_band_critical_multiplier          REAL,
        account_preference_rules_json                TEXT,
        psu_funding_rule_json                          TEXT,
        updated_at                                      TEXT NOT NULL
    );
    """)

    conn.execute("CREATE INDEX IF NOT EXISTS idx_investment_pillar ON investment(pillar_id);")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_investment_lifecycle ON investment(lifecycle_status);"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_account_investment_account "
        "ON account_investment(account_id);"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_account_investment_investment "
        "ON account_investment(investment_id);"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_projection_investment "
        "ON projection_version(investment_id);"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_projection_scenario_projection "
        "ON projection_scenario(projection_id);"
    )

    conn.commit()
    return conn
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_domain_model_db_client.py -v`
Expected: `9 passed`

- [ ] **Step 5: DDL drift check against the approved schema documents**

The DDL in `db_client.py` was hand-transcribed from `docs/architecture/domain-data-model.md` and
`docs/architecture/supplementary-domain-schemas.md`. Hand-transcription is a real risk (a dropped
column, a renamed constraint) — do not skip this step. For every table, diff the column list,
types, and constraints in `db_client.py` against the source document column-for-column. Record
the result as a comment block at the top of `db_client.py`:

```python
# DDL drift check (performed at authoring time, re-run whenever this file changes):
# Source: docs/architecture/domain-data-model.md (account, strategy_pillar, sub_strategy,
#   investment, investment_price, account_investment, price_level_set, price_level_tier,
#   alert, investment_note, projection_version, projection_scenario, portfolio_policy)
#   + docs/architecture/supplementary-domain-schemas.md (trade_log_entry, order_execution,
#   cash_flow, cash_flow_baseline).
# Deviations from source documents (must be empty, or each entry must be justified):
#   - projection_version.research_event_id: source docs show this as
#     "REFERENCES intelligence_event(event_id)" but that table lives in a different SQLite
#     file (intelligence.sqlite) than this one (domain_model's own .sqlite) — SQLite cannot
#     enforce a cross-database FK, so this column is declared without a REFERENCES clause here.
#     Referential integrity for this link is enforced at the repository layer (Wave 1's
#     projection repository must validate the event_id exists before insert), not by SQLite.
#     Same reasoning applies to investment.latest_research_event_id.
#   - (no other deviations found as of this transcription)
```

If a second reviewer (or a future re-read of this file) finds any other deviation from the two
source documents, it must be added to this list with the same justify-or-fix treatment — silently
differing from the approved schema is exactly the kind of unverified claim ADR-029 warns against.

- [ ] **Step 6: Commit**

```bash
git add investment_screener/backend/py_services/domain_model/__init__.py \
        investment_screener/backend/py_services/domain_model/db_client.py \
        investment_screener/backend/tests/py_services/test_domain_model_db_client.py
git commit -m "feat: add v3.2 domain-model SQLite schema (Wave 0, foundation only)"
```

---

### Task 2: `investment_repository.py`

**Files:**
- Create: `investment_screener/backend/py_services/domain_model/investment_repository.py`
- Test: `investment_screener/backend/tests/py_services/test_investment_repository.py`

**Interfaces:**
- Consumes: `domain_model.db_client.initialize_db(db_path) -> sqlite3.Connection` (Task 1).
- Produces:
  - `resolve_investment(conn, symbol: str, asset_class: str = "EQUITY", currency: str = "USD", name: str | None = None) -> str` — idempotent, mirrors `instrument_repository.py::resolve_instrument`'s shape exactly (same idempotency contract, same "insert if missing, return existing id if present" behavior).
  - `get_investment(conn, investment_id: str) -> dict | None`

- [ ] **Step 1: Write the failing test**

```python
# investment_screener/backend/tests/py_services/test_investment_repository.py
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.investment_repository import (  # noqa: E402
    resolve_investment,
    get_investment,
)


def test_resolve_investment_creates_new_and_is_idempotent(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    id_1 = resolve_investment(conn, "AAPL", asset_class="EQUITY", currency="USD", name="Apple Inc.")
    id_2 = resolve_investment(conn, "AAPL", asset_class="EQUITY", currency="USD", name="Apple Inc.")
    assert id_1 == id_2
    cursor = conn.execute("SELECT COUNT(*) FROM investment WHERE symbol = 'AAPL';")
    assert cursor.fetchone()[0] == 1


def test_resolve_investment_supports_cash_concepts(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    investment_id = resolve_investment(conn, "CASH_USD", asset_class="CASH", currency="USD")
    row = get_investment(conn, investment_id)
    assert row["asset_class"] == "CASH"
    assert row["symbol"] == "CASH_USD"


def test_get_investment_returns_none_for_unknown_id(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    assert get_investment(conn, "does-not-exist") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_investment_repository.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'domain_model.investment_repository'`

- [ ] **Step 3: Write minimal implementation**

```python
# investment_screener/backend/py_services/domain_model/investment_repository.py
"""All ``investment`` table reads and writes live here, mirroring
``py_services/intelligence/instrument_repository.py``'s anti-duplication rule (ADR-028,
extended to the domain-model package by ADR-029).
"""

import sqlite3
from datetime import datetime, timezone


def resolve_investment(
    conn: sqlite3.Connection,
    symbol: str,
    asset_class: str = "EQUITY",
    currency: str = "USD",
    name: str | None = None,
) -> str:
    """Return the ``investment_id`` for a symbol, inserting it if new.

    Idempotent: calling this twice for the same symbol returns the same
    ``investment_id`` and does not insert a duplicate row.
    """
    cursor = conn.execute("SELECT investment_id FROM investment WHERE symbol = ?;", (symbol,))
    row = cursor.fetchone()
    if row:
        return row[0]
    investment_id = symbol.upper()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO investment (investment_id, symbol, name, asset_class, currency, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?);",
        (investment_id, symbol, name or symbol, asset_class, currency, now),
    )
    conn.commit()
    return investment_id


def get_investment(conn: sqlite3.Connection, investment_id: str) -> dict | None:
    """Return the investment row as a dict, or ``None`` if it doesn't exist."""
    conn.row_factory = sqlite3.Row
    cursor = conn.execute("SELECT * FROM investment WHERE investment_id = ?;", (investment_id,))
    row = cursor.fetchone()
    return dict(row) if row else None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_investment_repository.py -v`
Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add investment_screener/backend/py_services/domain_model/investment_repository.py \
        investment_screener/backend/tests/py_services/test_investment_repository.py
git commit -m "feat: add investment_repository (resolve_investment, get_investment)"
```

---

### Task 3: `account_repository.py` + seed the two real accounts

**Files:**
- Create: `investment_screener/backend/py_services/domain_model/account_repository.py`
- Test: `investment_screener/backend/tests/py_services/test_account_repository.py`

**Interfaces:**
- Consumes: `domain_model.db_client.initialize_db` (Task 1).
- Produces:
  - `upsert_account(conn, account_id: str, account_name: str, account_type: str, base_currency: str = "CAD") -> None`
  - `get_account(conn, account_id: str) -> dict | None`
  - `list_accounts(conn) -> list[dict]`

**Context:** Per CLAUDE.md, the two real accounts are TFSA (primary, larger) and RRSP (mirrors at
~1/3 share count). This task seeds both as real rows — later waves' broker-sync producers
(`BrokerSyncService.ts`, `fetch_broker_data.py`) will resolve against these `account_id`s rather
than free-text account-name strings.

- [ ] **Step 1: Write the failing test**

```python
# investment_screener/backend/tests/py_services/test_account_repository.py
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.account_repository import (  # noqa: E402
    upsert_account,
    get_account,
    list_accounts,
)


def test_upsert_account_creates_and_is_idempotent(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    upsert_account(conn, "TFSA", "TFSA", "TFSA", base_currency="CAD")
    upsert_account(conn, "TFSA", "TFSA", "TFSA", base_currency="CAD")
    cursor = conn.execute("SELECT COUNT(*) FROM account WHERE account_id = 'TFSA';")
    assert cursor.fetchone()[0] == 1


def test_get_account_returns_row(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    upsert_account(conn, "RRSP", "RRSP", "RRSP", base_currency="CAD")
    row = get_account(conn, "RRSP")
    assert row["account_name"] == "RRSP"


def test_list_accounts_returns_all(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    upsert_account(conn, "TFSA", "TFSA", "TFSA")
    upsert_account(conn, "RRSP", "RRSP", "RRSP")
    accounts = list_accounts(conn)
    assert {a["account_id"] for a in accounts} == {"TFSA", "RRSP"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_account_repository.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'domain_model.account_repository'`

- [ ] **Step 3: Write minimal implementation**

```python
# investment_screener/backend/py_services/domain_model/account_repository.py
"""All ``account`` table reads and writes live here (ADR-029 anti-duplication rule)."""

import sqlite3


def upsert_account(
    conn: sqlite3.Connection,
    account_id: str,
    account_name: str,
    account_type: str,
    base_currency: str = "CAD",
) -> None:
    conn.execute(
        "INSERT INTO account (account_id, account_name, account_type, base_currency) "
        "VALUES (?, ?, ?, ?) "
        "ON CONFLICT(account_id) DO UPDATE SET "
        "account_name=excluded.account_name, account_type=excluded.account_type, "
        "base_currency=excluded.base_currency;",
        (account_id, account_name, account_type, base_currency),
    )
    conn.commit()


def get_account(conn: sqlite3.Connection, account_id: str) -> dict | None:
    conn.row_factory = sqlite3.Row
    cursor = conn.execute("SELECT * FROM account WHERE account_id = ?;", (account_id,))
    row = cursor.fetchone()
    return dict(row) if row else None


def list_accounts(conn: sqlite3.Connection) -> list[dict]:
    conn.row_factory = sqlite3.Row
    cursor = conn.execute("SELECT * FROM account;")
    return [dict(row) for row in cursor.fetchall()]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_account_repository.py -v`
Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add investment_screener/backend/py_services/domain_model/account_repository.py \
        investment_screener/backend/tests/py_services/test_account_repository.py
git commit -m "feat: add account_repository (upsert_account, get_account, list_accounts)"
```

---

### Task 4: `account_investment_repository.py`

**Files:**
- Create: `investment_screener/backend/py_services/domain_model/account_investment_repository.py`
- Test: `investment_screener/backend/tests/py_services/test_account_investment_repository.py`

**Interfaces:**
- Consumes: `resolve_investment`/`get_investment` (Task 2), `upsert_account`/`get_account`
  (Task 3).
- Produces:
  - `upsert_account_investment(conn, account_id: str, investment_id: str, quantity: float, average_cost: float | None, book_value: float | None, currency: str, last_synced_at: str) -> str` — returns the generated `account_investment_id` (`f"{account_id}:{investment_id}"`).
  - `list_account_investments(conn, account_id: str | None = None, investment_id: str | None = None) -> list[dict]`

- [ ] **Step 1: Write the failing test**

```python
# investment_screener/backend/tests/py_services/test_account_investment_repository.py
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.account_repository import upsert_account  # noqa: E402
from domain_model.investment_repository import resolve_investment  # noqa: E402
from domain_model.account_investment_repository import (  # noqa: E402
    upsert_account_investment,
    list_account_investments,
)


def _seed(conn):
    upsert_account(conn, "TFSA", "TFSA", "TFSA")
    upsert_account(conn, "RRSP", "RRSP", "RRSP")
    aapl_id = resolve_investment(conn, "AAPL", asset_class="EQUITY", currency="USD")
    return aapl_id


def test_upsert_account_investment_creates_and_is_idempotent(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    aapl_id = _seed(conn)
    ai_id_1 = upsert_account_investment(
        conn, "TFSA", aapl_id, quantity=10, average_cost=150.0,
        book_value=1500.0, currency="USD", last_synced_at="2026-07-19T00:00:00Z",
    )
    ai_id_2 = upsert_account_investment(
        conn, "TFSA", aapl_id, quantity=12, average_cost=150.0,
        book_value=1800.0, currency="USD", last_synced_at="2026-07-19T01:00:00Z",
    )
    assert ai_id_1 == ai_id_2 == "TFSA:AAPL"
    rows = list_account_investments(conn, account_id="TFSA")
    assert len(rows) == 1
    assert rows[0]["quantity"] == 12  # last write wins, not a duplicate row


def test_same_investment_across_two_accounts(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    aapl_id = _seed(conn)
    upsert_account_investment(
        conn, "TFSA", aapl_id, quantity=10, average_cost=150.0,
        book_value=1500.0, currency="USD", last_synced_at="2026-07-19T00:00:00Z",
    )
    upsert_account_investment(
        conn, "RRSP", aapl_id, quantity=3, average_cost=150.0,
        book_value=450.0, currency="USD", last_synced_at="2026-07-19T00:00:00Z",
    )
    rows = list_account_investments(conn, investment_id=aapl_id)
    assert {r["account_id"] for r in rows} == {"TFSA", "RRSP"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_account_investment_repository.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# investment_screener/backend/py_services/domain_model/account_investment_repository.py
"""All ``account_investment`` table reads and writes live here (ADR-029 anti-duplication rule)."""

import sqlite3


def upsert_account_investment(
    conn: sqlite3.Connection,
    account_id: str,
    investment_id: str,
    quantity: float,
    average_cost: float | None,
    book_value: float | None,
    currency: str,
    last_synced_at: str,
) -> str:
    account_investment_id = f"{account_id}:{investment_id}"
    conn.execute(
        "INSERT INTO account_investment "
        "(account_investment_id, account_id, investment_id, quantity, average_cost, "
        "book_value, currency, last_synced_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(account_id, investment_id) DO UPDATE SET "
        "quantity=excluded.quantity, average_cost=excluded.average_cost, "
        "book_value=excluded.book_value, currency=excluded.currency, "
        "last_synced_at=excluded.last_synced_at;",
        (
            account_investment_id, account_id, investment_id, quantity,
            average_cost, book_value, currency, last_synced_at,
        ),
    )
    conn.commit()
    return account_investment_id


def list_account_investments(
    conn: sqlite3.Connection,
    account_id: str | None = None,
    investment_id: str | None = None,
) -> list[dict]:
    conn.row_factory = sqlite3.Row
    query = "SELECT * FROM account_investment WHERE 1=1"
    params: list[str] = []
    if account_id:
        query += " AND account_id = ?"
        params.append(account_id)
    if investment_id:
        query += " AND investment_id = ?"
        params.append(investment_id)
    cursor = conn.execute(query, params)
    return [dict(row) for row in cursor.fetchall()]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_account_investment_repository.py -v`
Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
git add investment_screener/backend/py_services/domain_model/account_investment_repository.py \
        investment_screener/backend/tests/py_services/test_account_investment_repository.py
git commit -m "feat: add account_investment_repository (upsert, list, dedupe by account+investment)"
```

---

### Task 5: Backfill the real ticker universe (minimal `investment` identity rows)

**Files:**
- Create: `investment_screener/backend/py_services/domain_model/backfill_investment_universe.py`
- Test: `investment_screener/backend/tests/py_services/test_backfill_investment_universe.py`

**Interfaces:**
- Consumes: `resolve_investment` (Task 2).
- Produces: `backfill_from_ticker_lists(conn, tickers: list[str], asset_class: str = "EQUITY", currency: str = "USD") -> int` — returns count of newly-created rows (idempotent on re-run).

**Why this task exists:** Wave 1's `projection_version.investment_id` is a required FK. Every
ticker with a `projections/*.json` file must have a resolvable `investment_id` before Wave 1's
migration script runs. This task creates minimal identity-only rows (symbol, asset_class,
currency) — full field population (lifecycle_status, target_weight, standing_decision, etc.)
happens in Wave 2 when `target-portfolio.json` itself migrates. This is intentionally a thin
seed, not a preview of Wave 2's work.

- [ ] **Step 1: Write the failing test**

```python
# investment_screener/backend/tests/py_services/test_backfill_investment_universe.py
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.investment_repository import get_investment  # noqa: E402
from domain_model.backfill_investment_universe import (  # noqa: E402
    backfill_from_ticker_lists,
)


def test_backfill_creates_one_row_per_new_ticker(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    created = backfill_from_ticker_lists(conn, ["AAPL", "MSFT"])
    assert created == 2
    assert get_investment(conn, "AAPL") is not None
    assert get_investment(conn, "AAPL")["asset_class"] == "EQUITY"


def test_backfill_cash_concepts_use_asset_class_cash(tmp_path):
    """CASH_USD/CASH_CAD are real INVESTMENT rows per the v3.2 model (spec §3, resolved
    decision 5) — they must never silently default to EQUITY. The caller is responsible for
    passing asset_class="CASH" explicitly; this test guards against that contract being
    dropped, since a default-to-EQUITY cash row would be a real data-modeling bug, not a
    cosmetic one (it would corrupt asset_class-based portfolio composition queries).
    """
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    backfill_from_ticker_lists(conn, ["CASH_USD", "CASH_CAD"], asset_class="CASH")
    assert get_investment(conn, "CASH_USD")["asset_class"] == "CASH"
    assert get_investment(conn, "CASH_CAD")["asset_class"] == "CASH"


def test_backfill_is_idempotent_on_rerun(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    backfill_from_ticker_lists(conn, ["AAPL", "MSFT"])
    created_second_run = backfill_from_ticker_lists(conn, ["AAPL", "MSFT", "GOOGL"])
    assert created_second_run == 1  # only GOOGL is new
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_backfill_investment_universe.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# investment_screener/backend/py_services/domain_model/backfill_investment_universe.py
"""One-time-per-wave backfill: minimal INVESTMENT identity rows for the real ticker universe.

Full field population (lifecycle_status, target_weight, standing_decision, etc.) is Wave 2's
job when target-portfolio.json itself migrates. This script only guarantees every known ticker
has a resolvable investment_id before Wave 1 (projection_version) needs one.
"""

import sqlite3

from investment_repository import get_investment, resolve_investment


def backfill_from_ticker_lists(
    conn: sqlite3.Connection,
    tickers: list[str],
    asset_class: str = "EQUITY",
    currency: str = "USD",
) -> int:
    created = 0
    for ticker in tickers:
        existing = get_investment(conn, ticker.upper())
        resolve_investment(conn, ticker, asset_class=asset_class, currency=currency)
        if existing is None:
            created += 1
    return created
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_backfill_investment_universe.py -v`
Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add investment_screener/backend/py_services/domain_model/backfill_investment_universe.py \
        investment_screener/backend/tests/py_services/test_backfill_investment_universe.py
git commit -m "feat: add investment-universe backfill (minimal identity rows for Wave 1 FK)"
```

---

### Task 6: Wave 0 exit report + full test suite gate

**Files:**
- Create: `docs/superpowers/status/wave0-schema-foundation-report.md`

- [ ] **Step 1: Run the full backend Python test suite to confirm no regression**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/ -v 2>&1 | tail -30`
Expected: all `domain_model`-prefixed tests pass; pre-existing unrelated failures (network/yfinance
tests, per `cleanup-execution-report.md`'s documented baseline) are the only failures, if any.

- [ ] **Step 2: Run this project's T0/T0.5 gate**

Run: `python3 run_tests.py`
Expected: all gates pass, including the map-debt audit.

- [ ] **Step 3: Write the Wave 0 KPI report**

Fill in the Wave KPI table template from the spec (§ Required Success Metric) with real numbers —
Wave 0 is a foundation wave, so this is legitimately all-zero on the JSON side:

```markdown
# Wave 0 — Schema and Repository Foundation — Report

| KPI | Value |
|---|---|
| Wave | 0 |
| Active JSON/JSONL files before | 212 (repo-wide baseline, unchanged) |
| Active JSON/JSONL files after | 212 (unchanged — no JSON domain touched this wave) |
| Files archived | 0 |
| JSON reads removed | 0 |
| JSON writes removed | 0 |
| Producers migrated (n / total) | 0 / 0 (no producer targeted this wave) |
| Consumers migrated (n / total) | 0 / 0 (no consumer targeted this wave) |
| Plugin/skill/agent references updated | 0 (none reference domain_model tables yet) |
| Context-bundle files removed | 0 |
| Remaining JSON exceptions (with rationale) | N/A — this wave is schema-only, not a domain cutover |

## Definition of Done — verified

1. Data migrated — N/A (foundation wave, no JSON data migrated yet).
2. Producers write domain repositories — N/A this wave.
3. Consumers read domain repositories — N/A this wave.
4. Old JSON references removed/rewritten — N/A this wave.
5. SKILL.md/agent/plugin instructions updated — N/A this wave.
6. Context-bundler no longer needs retired files — N/A this wave.
7. Old JSON archived or retained under exception — N/A this wave.
8. Tests prove live path, not fixtures only — schema/repository tests run against real
   `tmp_path`-backed SQLite files (real `sqlite3`, not mocked), per the project's mocking
   prohibition on critical runtime paths.
9. JSON file count before/after reported — yes, unchanged (correctly — see row above).

## Why this wave is honestly "complete" despite all-zero JSON KPIs

Wave 0 exists only to make Wave 1 possible (`projection_version.investment_id` needs a resolvable
FK target). It touches no JSON file, migrates no consumer, and archives nothing — reporting
anything other than zero here would be fabricating progress the spec's Anti-Regression Lessons
explicitly warn against ("data copied to SQLite is not adoption"). The real KPI movement starts
in Wave 1.
```

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/status/wave0-schema-foundation-report.md
git commit -m "docs: Wave 0 schema/repository foundation exit report"
```

### Hard Checkpoint — Do Not Start Wave 1 Until This Is Reviewed

**Wave 1 does not begin automatically after Task 6's commit.** The Wave 0 exit report above must
be presented to the user for explicit review and sign-off before any Wave 1 work (including
writing Wave 1's own detailed task plan) starts. This is not a formality: Wave 0 introduces a new
package, a new schema, and a new anti-duplication rule that every later wave depends on — a
mistake here (a missing index, a wrong constraint, a repository function signature later waves
build against) is far cheaper to catch before Wave 1 starts consuming it than after. Treat the end
of Task 6 as a full stop, not a soft pause.

---

## Waves 1 Through 5E — Roadmap (detailed task breakdown written immediately before each wave starts)

**Why these waves are not broken into bite-sized code steps here:** Wave 0 above is genuinely
plannable now because it creates new files from an already-fully-specified schema. Waves 1–5E
each **rewrite existing consumer code** (2–32 files per domain) — writing exact TDD steps for
that now would mean guessing at current function signatures, import structures, and test
conventions in files not yet freshly re-read line-by-line. That is exactly the failure mode ADR-029
documents: the prior effort's plan asserted `projections/{TICKER}.json` had a top-level
`researchReport` field when the real field was nested at `aiThesis.researchReport`, and a
migration script built against that wrong assumption would have silently corrupted data. **Each
wave below gets its own `superpowers:writing-plans` pass, immediately before that wave begins,**
using this same skill and the same Definition of Done — not a generic follow-up, a mandatory gate.

Every wave plan, when written, must include:

- **Hybrid Exit Criteria** (spec § "Hybrid Exit Criteria" + §2.0 Source-of-Truth Transition Table
  row for that domain).
- **Wave KPI table** (spec § "Wave KPI Table Template"), filled with real numbers, not estimates.
- **Context Bundle Completion Bar**: which SKILL.md/agent files (spec §4 table) get updated, and
  the resulting bundle file-count/size reduction for a representative plugin invocation.
- **Producer/Consumer cutover table**: one row per real file (spec §2's per-domain lists), each
  ending in `Cutover status: DONE`, not "planned."
- **Archive/retention decision**: `git mv` target under `ARCHIVE/<mirrored path>`, or a completed
  Retained-JSON Rationale Bar (spec §2.18) if anything is kept.
- **Stop conditions** (spec §6), re-checked explicitly before the wave is declared done.

### Definition of Done (applies to every wave, 1 through 5E, without exception)

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

```
SQLite table exists
+
JSON still authoritative
+
runtime still reads JSON
+
fallback remains indefinitely
```

### Wave 1 — Projections (`projections/*.json`, 144 files)

- **Scope:** 2 producers (`ProjectionService.ts`, `apply_catalyst.py`), 18 consumers (spec §2.5).
- **Depends on:** Wave 0's `investment`/`projection_version`/`projection_scenario` tables and
  `resolve_investment`.
- **Key fix carried in:** `research_report_pointer` → `research_event_id` (real FK, no filename
  string) — this is the root-cause bug this whole correction traces to; do not defer it.
- **Expected KPI shape:** 144 files → 0 active, 144 archived; 2/2 producers, 18/18 consumers.
- **Before writing this wave's detailed plan:** re-read `ProjectionService.ts`,
  `routes/projections.ts`, and `apply_catalyst.py` fresh (do not trust this document's producer
  description as gospel — it summarizes `migration-inventory-and-strategy.md`, which itself
  should be re-verified against current code before task-level steps are written).
- **Repeated, because this is the first real test of it:** every one of Wave 1's 2 producers and
  18 consumers must call into a `projection_repository.py`/`ProjectionRepository.ts`-equivalent
  module — no script or route gets its own `sqlite3.connect()`/DB driver call against
  `projection_version`/`projection_scenario`. This is the same anti-duplication rule Wave 0
  established for `investment`/`account`/`account_investment` (Global Constraints, above); Wave 1
  is where it gets tested against real, messy, 18-consumer rewiring pressure for the first time,
  so it is restated here explicitly rather than assumed to carry over silently.

### Wave 2 — Investment / Target / Watchlist / Price Levels / Notes / Alerts / Thesis Breaker State

- **Scope:** `target-portfolio.json`, `watchlist.json` (11 + 6 producers, 18 + 6 consumers),
  embedded price levels and `agentRationale`, `tradingview_alerts_actual.json`,
  `thesis_breaker_state.json` (spec §2.1–§2.3, §2.7, §2.15).
- **Depends on:** Wave 0's `investment` table already has minimal rows from the backfill (Task 5)
  — this wave populates every remaining field (lifecycle_status, target_weight,
  standing_decision_*, thesis_for_inclusion, is_watchlisted, thesis_breaker_status) on those same
  rows, not new rows.
- **Highest-risk item:** the `standingDecision` anchor rule (CLAUDE.md #8 — never flip BUY→SELL on
  <15% variance) must be re-verified against the new read path specifically before this wave is
  declared done — this is the single most safety-critical piece of logic touching this file.
- **Expected KPI shape:** 2 files → 0 active (both archived), plus 5 embedded sub-domains folded
  into the same cutover (no separate file count for those, since they were never separate files).

### Wave 3 — Account Holdings (`portfolio.json`, gitignored)

- **Scope:** 20 producers, ~32 consumers (spec §2.4) — the largest domain in this migration by
  producer/consumer count, deliberately not attempted before Waves 1–2 prove the pattern.
- **Archive rule:** local-only, never committed (spec §2.19) — the privacy boundary that exists
  today must be identical after migration.
- **Validation requirement:** parity proven across at least one full real broker-sync cycle before
  archiving, per the spec's Validation Strategy — not a one-off snapshot diff.

### Wave 4 — Portfolio Operations (Trade Log, Order Executions, Cash Flows)

- **Scope:** `trade-log.json` (1 TS route, both producer+consumer), `orders_executed.jsonl`
  (1 producer, 1 consumer), `cash_flows.json` (**0 code producers — new write path required**,
  spec §2.10).
- **Note:** `cash_flows.json`'s migration is not a swap — it requires building a write path
  (small CLI or UI action) that doesn't exist today, since the file is currently hand-edited.
  This wave's plan must design that write path explicitly, not assume one already exists to
  redirect.

### Wave 5A — Generated Research Views (closes root-cause debt from the prior effort)

- **Scope:** `docs.ts`'s `GET /api/research/:filename` route — remove the filename-shape
  fallback branch entirely, query `intelligence_event` unconditionally.
- **This is not new scope** — it is unresolved debt from ADR-029, carried into this plan because
  leaving it open repeats the exact failure this whole spec corrects. Must complete before 5B–5D,
  since they reuse the same query pattern this sub-wave establishes.

### Wave 5B — TA Sweep Results

- **Scope:** `ta-sweep-results.json` → `intelligence_event` (`TECHNICAL_SWEEP`).
- **Explicit instruction:** the prior effort's status docs describe this as "code wired, never
  exercised." **Do not trust that claim.** Re-verify producer/consumer/archive from scratch
  against the Definition of Done above.

### Wave 5C — Daily Briefs

- **Scope:** `data/daily-briefs/*.json` → `intelligence_event` (`REVIEW_DAILY`).
- **Explicit instruction:** same re-verification requirement as 5B — "code wired but no real test
  exists for this path" per the prior effort's own status doc. Write the missing real test before
  claiming this wave done.

### Wave 5D — Predictions

- **Scope:** `predictions.jsonl`, `predictions_graded.jsonl` → `intelligence_event`
  (`PREDICTION_CLAIM`/`PREDICTION_GRADED`), widening the existing live CHECK constraint with the
  existing 80 rows intact.

### Wave 5E — Account/Portfolio Policy

- **Scope:** `account_policy.json` → `portfolio_policy` (4 numeric columns + 2 JSON rule-blob
  columns, per spec §2.14 — the JSON columns are the approved exception, already justified, not a
  new decision needed at implementation time).

### Wave 6 — Program Closure & Architecture Reconciliation

- **Scope:** runs only after every functional wave (0 through 5E) is complete and merged — this is
  not a code-migration wave, it is the program's closing audit and documentation/agent-ecosystem
  reconciliation pass. Added as a terminal phase during Wave 3 kickoff planning (2026-07-20) so it
  is not forgotten once the functional waves stop generating their own forcing function.
- **1. Architecture documentation reconciliation:** export the complete final SQLite DDL, refresh
  the Mermaid ERD, regenerate physical schema docs and data dictionary, and verify all of it
  matches the actual shipped schema (not the original spec's pre-migration draft).
- **2. Agent & onboarding reconciliation:** review and update `toolkit-onboarding-guide`; validate
  startup/bootstrap instructions, coordinator-agent routing logic, and the TradingView onboarding
  path; update agent-ecosystem docs for the SQLite-first architecture; remove references to
  retired JSON/JSONL stores anywhere they still linger in skills/agents/plugins.
- **3. Retained-JSON reassessment:** revisit every exemption approved along the way (at minimum
  `target-portfolio.json` and `thesis_breaker_state.json` from Wave 2, plus any later-approved
  exceptions) and for each: confirm the exemption is still justified, evaluate whether a schema
  change would now eliminate it, and decide migrate / redesign / formally retain with documented
  rationale.
- **4. Final migration audit:** JSON/JSONL file counts before vs. after across the whole program;
  remaining runtime JSON producers/consumers (should be zero outside approved exceptions); full
  SQLite table/repository/service inventory; a program-level Wave KPI rollup.
- **5. Architecture simplification review:** remove temporary compatibility layers, migration-only
  code, dead adapters, now-unused helper functions, and duplicate access paths left behind by
  incremental wave-by-wave cutover; confirm the final architecture actually matches the SQLite-
  pivot objective stated at the top of this plan, not a permanent hybrid.
- **Also binding on Wave 3 and later wave exits (per Wave 2's own lesson, restated here so it
  isn't lost before Wave 6):** a wave is not finished at "PR created." The full protocol is
  post-merge local `main` sync to `origin/main`, worktree removal, local **and remote** feature
  branch deletion, and verification (`git worktree list` / `git branch --list` clean) — before the
  next wave starts. This is CLAUDE.md's worktree-lifecycle rule; it is repeated here because Wave 6
  is exactly the kind of terminal phase this discipline is meant to protect.

---

## Self-Review

**1. Spec coverage:** Wave 0 fully implements the spec's schema (§3, all tables) and repository
anti-duplication rule (Live Code Requirement). Waves 1–5E map 1:1 to spec §2.1–§2.15 with no
domain omitted, and carry forward the spec's Hybrid Exit Criteria, Wave KPI template, Retained-
JSON Rationale Bar, and Definition of Done verbatim. The spec's Recommended First Implementation
Wave (§7) is honored: Wave 0 → Wave 1.

**2. Placeholder scan:** Wave 0's six tasks contain complete, real code (schema DDL transcribed
from the already-approved column-level schema in `domain-data-model.md`/
`supplementary-domain-schemas.md`, not invented). Waves 1–5E are explicitly a roadmap, not
under-specified tasks masquerading as complete ones — each states plainly why its detailed plan
is deferred and exactly when it must be written (immediately before that wave, same skill).

**3. Type consistency:** `resolve_investment(conn, symbol, asset_class, currency, name)` (Task 2)
is called identically in Task 5's backfill script and in every test. `upsert_account_investment`'s
generated ID format (`f"{account_id}:{investment_id}"`) matches the schema's documented
`account_investment_id` generation rule from `domain-data-model.md`.
