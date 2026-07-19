# ADR-028: Shared Intelligence Data Access Layer (Repository Pattern)

## Status
Accepted

## Amendment (see ADR-029)
This ADR's Decision §1.2 pre-approved three future domain-object tables — `valuation_version`,
`portfolio_decision`, `research_thesis` — "not yet created because no task in the current plan
produces the data they'd hold." Two of those tasks now exist: the `projection_version` table
designed in `docs/architecture/big-domain-migration-design.md` **is** the pre-approved
`valuation_version` table (kept the codebase's existing "projection" vocabulary —
`ProjectionService.ts`, `data/projections/` — rather than diverging to a new name), and
`target_portfolio_entry` in `docs/architecture/persistence-domain-data-model.md` **is** the
pre-approved `portfolio_decision` table. `research_thesis` remains unactivated — no task yet
produces synthesized-thesis data distinct from raw `RESEARCH_IMPORT` events.

The anti-duplication rule in Decision §1 is extended, not replaced: it applies per bounded
context, not only to `intelligence_event`. A second package,
`py_services/portfolio_ledger/`, is the sole owner of SQL against the new transactional tables
(`trade_log_entry`, `order_execution`, `cash_flow`) — these are not `intelligence_event` rows
(see ADR-029 for why) and do not belong under `EventRepository`. The rule "no producer or
consumer script opens its own connection" holds for both packages independently.

## Context
ADR-026 established the hybrid JSONL-ledger + SQLite-read-model + generated-views
architecture; ADR-027 selected SQLite as the storage engine. Neither addresses a second,
independent failure mode raised during plan review (by both a manual audit and adversarial
review from GPT-5.6): **duplicated JSONL/SQLite access code scattered across Python scripts,
Node routes, plugin scripts, skill instructions, and sub-agent workflows.** Without an explicit
boundary, every future consumer (`stock_valuation` skill, `daily_brief.py`, a future search
API route, etc.) would grow its own ad hoc SQLite connection or hand-rolled JSONL append —
recreating, inside the new architecture, the exact file-sprawl problem ADR-026 exists to fix.

A second, related risk surfaced: over-normalizing `intelligence_event`'s `event_type` values
(`NEWS_SWEEP`, `EARNINGS`, `TECHNICAL_SWEEP`, ...) into separate per-type tables and
repositories, which would defeat the point of a single append-only event ledger.

## Decision

1. **One shared Python package**, `investment_screener/backend/py_services/intelligence/`,
   is the only code allowed to open a SQLite connection to `intelligence.sqlite` or append a
   line to `observations.jsonl`. Modules, by responsibility:
   - `db_client.py` — connection/schema only (WAL, foreign keys, table/trigger definitions).
   - `event_store.py` — JSONL append: sequence assignment, content hashing, idempotency-key
     dedup.
   - `replay_ledger.py` — JSONL → SQLite projection, checkpoint tracking, full/incremental
     rebuild.
   - `event_repository.py` — all `intelligence_event` reads/writes and FTS5 search; the only
     place raw SQL against that table is allowed to exist.
   - `instrument_repository.py` — ticker → `instrument_id` resolution (aliases, exchange
     disambiguation).
   - `view_generator.py` — renders `research/{TICKER}.summary.md` / `.timeline.md` from the
     SQLite projection; generated files are read-only, never hand-edited.
   - `models.py` — typed dataclasses (`IntelligenceEvent`, `Instrument`) so callers pass
     structured objects, not unvalidated raw dicts.

   **Anti-duplication rule:** no plugin, skill, sub-agent, backend route, or script opens its
   own SQLite connection or writes its own JSONL line for intelligence data. It calls this
   package. Any exception must be explicitly documented at the call site, not silent.

2. **`event_type` is classification metadata, not a table-selection mechanism.** All event
   categories in the current taxonomy (`NEWS_SWEEP`, `EARNINGS`, `TECHNICAL_SWEEP`,
   `MACRO_EVENT`, `THESIS_UPDATE`, `RESEARCH_IMPORT`, `REVIEW_DAILY`, `REVIEW_WEEKLY`) are rows
   in the single `intelligence_event` table — never a `news_sweep`/`earnings`/etc. table per
   type. A new table is only justified for a domain object with a materially different shape or
   lifecycle than "something happened at a point in time" — e.g. `research_thesis` (current
   synthesized state, not event history), `valuation_version`, or `portfolio_decision`. These
   three are **named here as the recognized, pre-approved set of future domain-object tables**
   (see the design spec's full schema) — they are not yet created because no task in the
   current plan produces the data they'd hold, not because they're architecturally
   questionable. Creating one of these three when its data actually exists is expected, ordinary
   plan work; creating any *other* new table (i.e. anything outside this pre-approved set, most
   importantly anything that looks like a per-`event_type` table) is what requires its own
   documented ADR. Target repository count stays small — `EventRepository`,
   `InstrumentRepository`, and (when their tables exist) `ValuationRepository`,
   `ThesisRepository`: four to six total, not one per `event_type`. Repository ownership follows
   the *domain object* the table represents, never the `event_type` value.

3. **Deferred, explicitly scoped, not built in this pass:**
   - A symmetric Node/Express service layer (`src/services/intelligence/`). Nothing in the
     current implementation plan has Node querying `intelligence.sqlite` directly — the
     Express backend only reads generated Markdown files off disk. Build this layer when a
     route actually needs direct SQLite/FTS5 access (e.g. a future search API), not
     speculatively ahead of a caller.
   - Full `architecture.md`, `AGENTS.md`, `GEMINI.md`, `.github/copilot-instructions.md`
     rewrites reflecting the new source-of-truth hierarchy (JSONL ledger → SQLite projection →
     generated views → legacy archive). `architecture.md`'s ADR index table points here in the
     interim; the broader ecosystem doc sweep is follow-up work once the read model has real
     writers wired end-to-end.
   - A `generated_research_view` provenance table tracking which event-sequence/valuation/
     decision snapshot a generated file was rendered from — a legitimate future addition, not
     required for the first working version.

## Consequences
* **One data layer, many consumers.** Plugins/skills/reports call `event_store.append_event()`
  or `event_repository.search_fts()`; none of them know SQL, JSONL serialization, sequence
  logic, content hashing, or FTS trigger mechanics.
* **Retrofit cost paid once, early.** `db_client.py` and `replay_ledger.py` (built flat in
  `py_services/` before this ADR) move into the package immediately rather than after more
  work is built on the flat structure.
* **No premature Node/doc work.** Deferred items are documented here as the durable record,
  satisfying the "don't silently skip it" requirement without building unused scaffolding.
