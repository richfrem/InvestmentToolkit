# ADR-029: Persistence Domain Rationalization and Retirement-Gated Migration

## Status
Accepted

## Context

An implementation pass following ADR-026/027/028 built the JSONL ledger, the SQLite read model,
and migrated one narrow domain's data (80 research reports) into it. That work was reported as
"migration complete" and "certified." It was not: the live application never queried SQLite at
runtime for that data. `docs.ts` read statically-generated Markdown files produced by a
one-time manual export, and the Wave 1 workflow scripts (`ta_sweep_batch.py`,
`compute_conviction_scores.py`, `daily_brief.py`) had dual-write code that had never actually
fired against production data. A parallel SQLite database existed, populated, verified
byte-for-byte — and nothing in the running app depended on it. Meanwhile the domains carrying
the actual majority of this codebase's JSON coupling — `portfolio.json`, `target-portfolio.json`,
`projections/*.json` (146 of 212 total JSON/JSONL files repo-wide; 82 of 151 JSON-referencing
code files) — were never addressed at all.

This ADR is the corrective architectural decision: it defines what "migrated" means going
forward, in a way that cannot be satisfied by data copying alone, and it commits every future
persistence-domain decision to explicit classification rather than defaulting to "leave it as
JSON."

## Decision

### 1. A domain is not migrated until three things are true

```
producer writes SQLite
+ every real consumer reads SQLite
+ the old JSON/JSONL file is moved to ARCHIVE/ via git mv
= migrated
```

A table existing, a repository existing, or data being copied satisfies none of these on its
own. This replaces the implicit and incorrect prior standard ("data copied = complete") with an
explicit one. Applies retroactively: `observations.jsonl`/`intelligence.sqlite` (the research
domain) is **not yet migrated** under this rule — `docs.ts` still reads generated static files,
not SQLite, at request time. That gap is tracked as open work, not re-certified as done.

### 2. Every persistence domain is classified, not defaulted

No file is `RETAIN_AS_*` by default. Each domain gets one of eight classifications
(`MIGRATE_TO_SQLITE_EVENT_MODEL`, `MIGRATE_TO_SQLITE_DOMAIN_TABLE`, `GENERATED_FROM_SQLITE`,
`RETAIN_AS_CONFIGURATION_JSON`, `RETAIN_AS_EXTERNAL_CACHE`, `RETAIN_AS_SEPARATE_APPROVED_LEDGER`,
`ARCHIVE_AFTER_VERIFIED_MIGRATION`, `UNKNOWN_BLOCKER`), with justification answering: what
domain does it belong to, is it authoritative or derived, what reads it, what writes it, why is
JSON/SQLite the right choice, what breaks if it's removed. The full classification for every
domain identified so far lives in
`docs/superpowers/plans/corrected-persistence-domain-migration-plan.md`.

### 3. Two bounded contexts, not one table per event type and not one table for everything

- **Intelligence Ledger** (`intelligence_event`, existing, ADR-026/027/028): narrative/analytical
  observations — research, technical sweeps, reviews, and (newly activated per the ADR-028
  amendment) prediction claims. Shape: `title` + `body_markdown` + `payload_json`, FTS5-searched.
- **Portfolio Operations** (new, this ADR): fully-typed transactional records — trades, cash
  flows, order executions, holdings, target allocations, valuation versions. Shape: real typed
  columns, because the entire point of migrating them is aggregate SQL queries a JSON blob
  can't give you. Owned by a new package, `py_services/portfolio_ledger/`, under the same
  anti-duplication rule as `py_services/intelligence/` (ADR-028 §1, amended).

Mixing these was considered and rejected: forcing `BUY 10 AAPL @ $200` into the same row shape as
a research write-up would require either bloating `intelligence_event`'s CHECK constraint with
transactional types it wasn't designed for, or burying real, queryable fields
(`shares`/`price`/`account`) inside `payload_json`, defeating the reason to migrate at all.

### 4. Full data model and migration design

Column-level schemas, indexes, migration strategy, producer/consumer inventories (gathered by
direct code inspection, not estimated), archive criteria, and rollback strategy for every
in-scope domain live in:
- **`docs/architecture/domain-data-model.md`** (current, Version 3.2 as of this ADR) —
  the `account`/`investment`/`account_investment` model replacing `portfolio.json` +
  `target-portfolio.json` + `watchlist.json`, plus `projection_version`/`projection_scenario`
  (`projections/*.json`, activates ADR-028's pre-approved `valuation_version`), price levels,
  alerts, and investment notes. Supersedes the original `holdings`+`target_portfolio_entry`
  split below for these domains — see its own Revision History for the full v1→v3.2 reasoning
  trail.
- `docs/architecture/supplementary-domain-schemas.md` (formerly
  `persistence-domain-data-model.md`) — `predictions.jsonl` (maps into `intelligence_event` via
  new `PREDICTION_CLAIM`/`PREDICTION_GRADED` event types, not a separate table) and the
  Portfolio Operations schema (`trade_log_entry`, `order_execution`, `cash_flow`,
  `cash_flow_baseline`) — not superseded, still current.
- `docs/architecture/migration-inventory-and-strategy.md` (formerly
  `big-domain-migration-design.md`) — retains its real producer/consumer inventories and
  migration-strategy detail; its `holdings`/`target_portfolio_entry` table designs are
  superseded by `domain-data-model.md` above, kept here only as historical record of how the
  model evolved.

Both documents carry a **Domain Retirement Plan** table (current state → future table → explicit
retirement trigger) for every domain they cover, including ones deferred to future phases —
"not scheduled yet" is stated explicitly with a named destination, never left blank.

### 5. Implementation order

`projection_version` first (approved next step, as of this ADR): one real producer at the time
of design vs. 11–20 for the other two big domains, ties directly to the `research_report_pointer`
field responsible for the bug that triggered this whole correction, and the largest single
file-count reduction (144 of the 146 files these three domains represent). `target_portfolio_entry`
and `holdings` follow only after the producer/consumer/archive discipline is proven end-to-end on
projections — not in parallel, and not before.

### 6. `research_report_pointer` → `research_event_id`

The specific field that broke: a free-text filename string, resolved by regex-matching its shape
against a route's filename validator. Redesigned as `research_event_id`, a real foreign key into
`intelligence_event.event_id`. There is no filename shape left to get wrong, because there is no
filename in the data model. Any future pointer-like reference between domains follows this
pattern — a real FK, never a string with an implicit, unenforced shape contract.

## Consequences

* **"Migrated" now has a falsifiable definition.** Any future status report claiming a domain is
  migrated must show producer, consumer, and archive evidence, not a byte-parity check on the
  data alone (which, as this session proved, can be true while the migration is otherwise
  meaningless).
* **The big three domains have a stated destination.** `portfolio.json`,
  `target-portfolio.json`, and `projections/*.json` are no longer indefinitely deferred without a
  target shape — they have column-level designs now, even though implementation hasn't started.
* **Two data-access packages, not one.** `py_services/intelligence/` and
  `py_services/portfolio_ledger/` both exist under the same anti-duplication discipline; no
  script anywhere opens its own SQLite connection to either domain's tables.
* **ADR-028's pre-approved table names are being activated**, not superseded — `projection_version`
  fulfills its `valuation_version` slot, `target_portfolio_entry` fulfills its `portfolio_decision`
  slot, using the codebase's existing vocabulary rather than introducing new names for the same
  concepts. `research_thesis`, the third pre-approved name, remains unactivated.
