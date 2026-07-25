# Persistence Domain Data Model — Proposed SQLite Schema

Design document, produced before any migration code is written, per the corrected scope in
`docs/superpowers/plans/corrected-persistence-domain-migration-plan.md`. Covers every domain
classified `MIGRATE_TO_SQLITE_EVENT_MODEL` in that plan, plus how they relate to the existing
`intelligence_event` schema (ADRs 026/027/028), so a reviewer can see the whole target shape
before implementation starts. Nothing in this document has been built yet.

---

## Two Bounded Contexts, Not One Table

The existing `intelligence_event` table (already live, holds 80 `RESEARCH_IMPORT` rows) was
designed for **narrative, analytical observations** — its schema is `title` +
`body_markdown` + a loosely-typed `payload_json`, with an FTS5 index over the text. That shape
fits research write-ups, technical-sweep summaries, and daily reviews well.

`trade-log.json`, `orders_executed.jsonl`, and `cash_flows.json` are a **different kind of
data**: small, fully-typed, transactional records (ticker, shares, price, account, amount, date)
where the entire point of migrating them is to run real aggregate queries — "sum cash flows by
account," "total shares traded per ticker this year." Burying those fields inside
`payload_json` would defeat that purpose; they need real columns. Forcing them into
`intelligence_event`'s narrative shape would also be a CHECK-constraint schema migration on a
table that's already live and tested, mixing two unrelated domains under one taxonomy.

**Decision:** keep `intelligence_event` as-is for narrative/analytical events (adding one new
`event_type` value for predictions — see below), and introduce a **separate "Portfolio
Operations" schema** for the transactional records. Both share the existing `instrument` table
for ticker identity, so there is one consistent way to look up "everything about AAPL" across
both domains.

---

## Domain 1: `predictions.jsonl` → `intelligence_event` (existing table, one new `event_type`)

**Current shape:** JSONL, one line per dated prediction claim —
`{v, id, date, ticker, type, claim: {consensus_eps, consensus_revenue, earnings_date, ...}}`.

**Why it fits the existing table rather than a new one:** a prediction claim is an analytical
observation ("as of this date, this is what we expect") — the same shape as a research event,
just shorter and more structured. It also has a real lifecycle (`predictions_graded.jsonl`
elsewhere in the codebase grades a claim against actuals later) that maps naturally onto the
existing `status`/`supersedes_event_id` columns: a graded prediction can supersede its raw
claim, exactly the pattern already built for research supersession.

**Mapping:**
- `event_type` = new value `PREDICTION_CLAIM` (requires widening the existing CHECK constraint —
  a real, scoped schema migration on the live table, done carefully with the existing 80 rows
  intact).
- `instrument_id` = resolved from `ticker` via the existing `instrument` table.
- `effective_at` = `date`.
- `payload_json` = the `claim` object as-is.
- `title` = `"{ticker} {type} prediction for {date}"`.
- `body_markdown` = unused (NULL) — this domain has no narrative prose.

**Grading follow-up events** (from the existing `predictions_graded.jsonl` concept) would use the
same table with a new `PREDICTION_GRADED` event_type, `supersedes_event_id` pointing at the
original `PREDICTION_CLAIM` row.

---

## Domain 2, 3, 4: New "Portfolio Operations" Schema

### `trade_log_entry` (from `trade-log.json`, 52 rows today)

**Wave 6 correction:** the columns below were updated to match the real, shipped
`domain_model/db_client.py` DDL rather than this document's original pre-implementation sketch.
Two real changes since this table was first drafted: (1) the FK column is named `investment_id`
and points at `investment(investment_id)`, not `instrument_id`/`instrument` — this table now
lives in the `domain_model.sqlite` file alongside `investment`, per `domain-data-model.md`'s v3
model, not the separate `instrument` table originally sketched in this document; (2) a
`tv_order_id` column was added post-hoc (Wave 4 Task 11) so `trading.ts`'s `/modify`, `/cancel`,
and `/log/sync-from-tv` routes can reconcile a logged entry against its live TradingView order.

| Column | Type | Notes |
|---|---|---|
| `entry_id` | TEXT PK | from source `id` field |
| `investment_id` | TEXT FK → `investment(investment_id)` | resolved from `ticker`; renamed from `instrument_id`/`instrument` per Wave 0's `investment` consolidation |
| `account_id` | TEXT FK → `account(account_id)` | **OPEN DESIGN QUESTION, not resolved here:** the real DDL types this as a proper FK (matching `domain-data-model.md`'s v3 Mermaid ERD, `ACCOUNT ||--o{ TRADE_LOG_ENTRY`), but this table's own `cash_flow` sibling below keeps the equivalent field as a plain `account TEXT` with no FK for the same "which account" concept. Flagged for a follow-up decision, not picked here — see `db_client.py`'s top-of-file comment for the full trail. |
| `action` | TEXT | BUY/SELL/etc. |
| `shares` | REAL | |
| `price` | REAL | |
| `total_cost` | REAL | |
| `order_type` | TEXT | |
| `limit_price` | REAL NULL | |
| `trade_date` | TEXT | source `date` |
| `notes` | TEXT NULL | |
| `status` | TEXT | |
| `source` | TEXT | |
| `priority` | TEXT NULL | |
| `logged_at` | TEXT | source `loggedAt` |
| `tv_order_id` | TEXT NULL | post-hoc, Wave 4 Task 11 — matches a logged entry against its live TradingView order id; added via `SCHEMA_EVOLUTIONS` self-heal rather than the original `CREATE TABLE`, so pre-existing real rows self-heal to have this column on next `initialize_db()` |

Immutable once written (a trade, once logged, is a historical fact) — insert-only table, no
update path needed.

### `order_execution` (from `orders_executed.jsonl`)

**Wave 6 correction:** FK column renamed `investment_id` → `investment(investment_id)`, same
reasoning as `trade_log_entry` above — not present in this table's original pre-implementation
sketch, which predates the v3 `investment` consolidation.

| Column | Type | Notes |
|---|---|---|
| `execution_id` | TEXT PK | generated: hash of `timestamp` + ticker + side |
| `executed_at` | TEXT | source `timestamp` |
| `investment_id` | TEXT FK → `investment(investment_id)` | resolved from `order.ticker`; renamed from `instrument_id`/`instrument` |
| `side` | TEXT | BUY/SELL |
| `shares` | REAL | |
| `price` | REAL NULL | market orders may have no price |
| `decision` | TEXT | BLOCKED / EXECUTED / etc. |
| `gate_result_json` | TEXT | the full `gate_result` object — kept as JSON deliberately: it's a variable-shape audit detail (which risk gates fired, why), not something queried column-by-column the way `shares`/`price`/`decision` are |

Insert-only — an execution attempt, once recorded, doesn't change.

### `cash_flow` (from `cash_flows.json`'s `cash_flows` array, 3 rows today)

| Column | Type | Notes |
|---|---|---|
| `flow_id` | TEXT PK | generated: hash of date + account + type |
| `flow_date` | TEXT | |
| `flow_type` | TEXT | deposit / withdrawal |
| `amount_cad` | REAL | |
| `portfolio_value_before_flow_cad` | REAL | |
| `account` | TEXT | |

### `cash_flow_baseline` (from `cash_flows.json`'s `starting_balance_cad`/`starting_date`)

Not event-shaped — a single current config value per account, not a log. Modeled as its own
tiny table rather than crammed into `cash_flow` as a fake "flow":

| Column | Type | Notes |
|---|---|---|
| `account` | TEXT PK | |
| `starting_balance_cad` | REAL | |
| `starting_date` | TEXT | |

---

## Entity-Relationship Diagram

**Wave 6 correction:** this diagram originally showed a standalone `INSTRUMENT` entity as the FK
anchor for `TRADE_LOG_ENTRY`/`ORDER_EXECUTION`. That was this document's pre-implementation
sketch; the real, shipped schema (`domain_model/db_client.py`) instead points both tables at
`INVESTMENT` (`domain-data-model.md`'s v3 model absorbed `INSTRUMENT` into `INVESTMENT` — see
that document's "The Core Question, Answered Honestly"). `INTELLIGENCE_EVENT` genuinely does
still reference its own `instrument(instrument_id)` table — that table lives in a *different*
SQLite file (`intelligence.sqlite`) than `investment` (`domain_model.sqlite`), is real, current,
and un-migrated; it is NOT the same table `TRADE_LOG_ENTRY`/`ORDER_EXECUTION` now point at. Also
added below (Wave 6): the real `ledger_checkpoint` table, the full `intelligence_event` column
list (including `observed_at`/`ingested_at`/`source_id`/`confidence_score`/`content_hash`, absent
from the original abbreviated entity block), and the `intelligence_event_fts` FTS5 virtual table
+ its 3 sync triggers — all four exist in `intelligence/db_client.py` today but were previously
undocumented in either architecture file.

```mermaid
erDiagram
    INSTRUMENT ||--o{ INTELLIGENCE_EVENT : "has events about"
    INTELLIGENCE_EVENT ||--o{ INTELLIGENCE_EVENT_FTS : "indexed by (via rowid triggers)"
    INVESTMENT ||--o{ TRADE_LOG_ENTRY : "has trades of"
    INVESTMENT ||--o{ ORDER_EXECUTION : "has orders for"

    INSTRUMENT {
        TEXT instrument_id PK
        TEXT ticker
        TEXT exchange
        TEXT name
        TEXT active_from
        TEXT active_to
    }

    LEDGER_CHECKPOINT {
        TEXT checkpoint_id PK
        INTEGER last_event_sequence
        TEXT last_event_id
        INTEGER schema_version
        TEXT processed_at
        TEXT ledger_file_hash
    }

    INTELLIGENCE_EVENT {
        TEXT event_id PK
        INTEGER event_sequence "UNIQUE"
        TEXT instrument_id FK
        TEXT event_type "RESEARCH_IMPORT|NEWS_SWEEP|EARNINGS|VALUATION_UPDATE|TECHNICAL_SWEEP|PORTFOLIO_DECISION|THESIS_UPDATE|MACRO_EVENT|REVIEW_DAILY|REVIEW_WEEKLY|PREDICTION_CLAIM|PREDICTION_GRADED"
        TEXT effective_at
        TEXT observed_at
        TEXT ingested_at
        TEXT source_id
        REAL confidence_score "CHECK 0.0-1.0"
        TEXT status "ACTIVE|SUPERSEDED|RETRACTED|INVALIDATED|DRAFT"
        TEXT title
        TEXT body_markdown
        TEXT payload_json
        TEXT supersedes_event_id FK
        TEXT idempotency_key "UNIQUE"
        TEXT content_hash
    }

    INTELLIGENCE_EVENT_FTS {
        TEXT title "fts5, content=intelligence_event, content_rowid=rowid"
        TEXT body_markdown
    }

    TRADE_LOG_ENTRY {
        TEXT entry_id PK
        TEXT investment_id FK
        TEXT account_id FK "OPEN QUESTION — see column table above"
        TEXT action
        REAL shares
        REAL price
        REAL total_cost
        TEXT order_type
        REAL limit_price
        TEXT trade_date
        TEXT status
        TEXT logged_at
        TEXT tv_order_id "post-hoc, Wave 4 Task 11"
    }

    ORDER_EXECUTION {
        TEXT execution_id PK
        TEXT executed_at
        TEXT investment_id FK
        TEXT side
        REAL shares
        REAL price
        TEXT decision
        TEXT gate_result_json
    }

    CASH_FLOW {
        TEXT flow_id PK
        TEXT flow_date
        TEXT flow_type
        REAL amount_cad
        REAL portfolio_value_before_flow_cad
        TEXT account
    }

    CASH_FLOW_BASELINE {
        TEXT account PK
        REAL starting_balance_cad
        TEXT starting_date
    }
```

`CASH_FLOW` and `CASH_FLOW_BASELINE` are account-scoped, not ticker-scoped, so they don't have a
foreign key into `INSTRUMENT`/`INVESTMENT` — shown without a relationship line for that reason.
`LEDGER_CHECKPOINT` has no FK to any other table (it tracks replay progress against the event
ledger as a whole, one row per checkpoint run) — also shown without a relationship line.
`INTELLIGENCE_EVENT_FTS` is a virtual table populated only via the 3 triggers documented below,
never written to directly — its relationship line reflects that trigger-driven sync, not a real
FK.

**`intelligence_event_fts` (FTS5 virtual table) + sync triggers** — real schema in
`intelligence/db_client.py`, previously undocumented in either architecture file:

```sql
CREATE VIRTUAL TABLE intelligence_event_fts USING fts5(
    title,
    body_markdown,
    content='intelligence_event',
    content_rowid='rowid'
);

-- 3 triggers keep the FTS index in sync with intelligence_event, standard FTS5 external-content
-- pattern (INSERT mirrors in; DELETE issues an FTS 'delete' command; UPDATE does both):
--   trg_intelligence_event_ai  AFTER INSERT ON intelligence_event
--   trg_intelligence_event_ad  AFTER DELETE ON intelligence_event
--   trg_intelligence_event_au  AFTER UPDATE ON intelligence_event
```

---

## Repository Layer (per ADR-028's anti-duplication rule)

The existing rule — only `py_services/intelligence/event_repository.py` may run SQL against
`intelligence_event` — extends the same way to the new tables: a new module,
`py_services/portfolio_ledger/` (mirroring the existing `intelligence/` package structure:
`db_client.py`, `trade_log_repository.py`, `order_execution_repository.py`,
`cash_flow_repository.py`), becomes the sole owner of SQL against these three new tables. No
producer or consumer script gets its own `sqlite3.connect()` call against them, same discipline
as the intelligence ledger.

## Domain Retirement Plan

The rule going forward, stated explicitly so it can't quietly slide back into another
accidental hybrid: **no domain is "migrated" because a table exists, a repository exists, or
data was copied. It is migrated only when the producer writes SQLite, every real consumer reads
SQLite, and the old JSON/JSONL file is moved to `ARCHIVE/` via `git mv`.** A domain stays at
"Current: JSON" in the table below until all three of those are true — not until the SQLite
side merely exists alongside it.

| Domain | Current | Future | Retirement Trigger |
|---|---|---|---|
| `predictions.jsonl` | JSONL | `intelligence_event` (`PREDICTION_CLAIM`/`PREDICTION_GRADED`) | producer + all 7 real consumers query SQLite; file archived |
| `orders_executed.jsonl` | JSONL | `order_execution` table | producer + both real consumers query SQLite; file archived |
| `trade-log.json` | JSON list | `trade_log_entry` table | producer + all 4 real consumers query SQLite; file archived |
| `cash_flows.json` | JSON | `cash_flow` + `cash_flow_baseline` tables | producer + all 3 real consumers query SQLite; file archived |
| `observations.jsonl` / `research/archive/*.md` | JSONL + MD | `intelligence_event` (`RESEARCH_IMPORT`) — **data already migrated, retirement NOT yet met** | `docs.ts` and every real consumer must query SQLite live at request time — today they read static files generated from it once; that gap is the exact failure this whole correction is about |
| `ta-sweep-results.json` | JSON snapshot | `intelligence_event` (`TECHNICAL_SWEEP`) — code wired, never exercised | real backfill of history, a real non-mocked test, then consumers query SQLite live |
| `data/daily-briefs/*.json` | JSON per date | `intelligence_event` (`REVIEW_DAILY`) — code wired but **no real test exists** for this path | write the missing test, backfill the 10 historical files, consumers query SQLite live |
| `portfolio.json` | **MIGRATED (Wave 3, 2026-07-22)** | `account`/`investment`/`account_investment`/`investment_price` tables (not the `holdings` shape originally sketched here — see `docs/architecture/domain-data-model.md` for the real schema) | done — real producers rewired (`BrokerSyncService.ts`, `fetch_broker_data.py`, `/refresh-prices`), `portfolio_io.load_portfolio_state()` delegates to SQLite |
| `target-portfolio.json` | **MIGRATED (Wave 2)** | `price_level_set`/`price_level_tier`/`strategy_pillar`/`sub_strategy` tables (not the flat `target_portfolio_entry` shape originally sketched here) | done — see `docs/superpowers/status/wave2-target-portfolio-report.md`; the `standingDecision` anchor rule (CLAUDE.md #8) verified unchanged |
| `projections/*.json` | **MIGRATED (Wave 1)** | `projection_version`/`projection_scenario` tables | done — see `docs/superpowers/status/wave1-projections-report.md` |
| `watchlist.json` | JSON dict | `watchlist_entry` table: one row per `instrument_id` with `added_at`, `notes` | full design pass + rewiring 6 real consumers; small enough to fold into the `portfolio`/`target_portfolio` consolidation you raised earlier rather than build standalone |
| `thesis_breaker_state.json` | JSON snapshot | `thesis_breaker_state` table: one row per `instrument_id` with breaker status, `generated_at` | low priority, 6 consumers, not scheduled |
| `tradingview_alerts_actual.json` | JSON list (TV mirror) | stays JSON — `RETAIN_AS_EXTERNAL_CACHE` | none — TradingView is authoritative, this is a synced mirror, same reasoning as `portfolio.json`'s cache role even after `portfolio.json` itself migrates |
| `account_policy.json` | JSON config | stays JSON — `RETAIN_AS_CONFIGURATION_JSON` | none — static config, never was operational data |

None of the "Future" targets above with real column shapes are placeholders picked to look
complete — they follow directly from each file's actual on-disk structure, checked this session
(§ domain-by-domain sections above and the corrected persistence-domain migration plan). The
ones still marked "not scheduled" are genuinely not designed in column-level detail yet — that
would be a real design pass, not a one-line guess — but their target table shape is stated
here so this document can't be used to quietly defer them forever without a stated destination.

## What This Document Does Not Fully Cover

Column-by-column design for `holdings`, `target_portfolio_entry`, `projection_version`, and
`watchlist_entry` is sketched above at the level needed to prove a destination exists, not built
out to migration-ready detail (index strategy, exact FK cascade behavior, how `pillars` /
`globalSettings` / scenario-level DCF detail decompose). That detail is the next design pass for
those four domains specifically, once the smaller ones in this document are proven out
end-to-end.

## Next Step

This is a design for review, not a build. Confirm the table shapes and the two-schema split
above before any implementation starts. When implementation does start, the Domain Retirement
Plan table above is the acceptance checklist — a domain doesn't move to "done" until producer,
consumer, and archival are all true, not when SQLite merely has the data.
