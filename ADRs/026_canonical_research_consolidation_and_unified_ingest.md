# ADR-026: Hybrid SQLite Ledger and Materialized Markdown Views for Investment Intelligence

## Status
Proposed (Revised after Adversarial Review)

## Context
Our initial proposal in ADR-025 and early drafts of ADR-026 aimed to replace fragmented date-padded files (e.g. `SNDK_2026-05-19.md`) with a single mutable Markdown profile `research/{TICKER}.md` per stock containing a YAML frontmatter block for metrics.

An adversarial review by GPT-5.6 revealed critical systemic flaws in this design:
1. **Concurrency and Lock Races:** Concurrent reads and writes by multiple agents, CLI tools, and background tasks on a single flat Markdown file introduce read-modify-write data loss patterns.
2. **Double Source of Truth:** Duplicating values like `fairValue` and `action` in both the Markdown frontmatter and the primary projection JSON files creates drift and version incoherency.
3. **Audit Trail Degradation:** Appending text segments to a single file degrades git-rename tracing and provenance information compared to immutable, content-addressed events.

## Decision
We reject flat Markdown profiles as our primary write target. Instead, we implement a **Hybrid SQLite Ledger and Generated View** architecture:

1. **Authoritative Event Sourcing Ledger:** The primary source of truth for qualitative updates is the append-only, chronologically ordered event ledger `history/events/observations.jsonl`.
2. **Derived Database Index (`intelligence.sqlite`):** We use a SQLite database configured in WAL mode as a query index. SQLite table states are derived and rebuilt by replaying the JSONL event stream.
3. **Monotonic Ledger Checkpoints:** Replay states are tracked via a `ledger_checkpoint` table storing sequence offsets and schema versions to prevent replay duplicate anomalies and support migrations.
4. **Synchronized FTS5 Search Index:** Search matching is supported via an `intelligence_event_fts` virtual table, with database triggers (`AFTER INSERT`, `AFTER DELETE`, `AFTER UPDATE`) maintaining sync with the main events table.
5. **Instrument Alias Mapping:** Tickers are mapped through an `instrument_alias` table to ensure historical data does not break when company symbols change or merge (e.g. `FB` -> `META`).
6. **Decoupled Financial Logic & Enums:** Valuation signals (`fairValue`) are strictly version-linked in the valuation history and separated from execution actions (`BUY|HOLD|SELL`), using strict event taxonomy enums and status lifecycles (`ACTIVE`, `SUPERSEDED`, `RETRACTED`, `INVALIDATED`, `DRAFT`).
7. **Generated Markdown Views:** Generated Markdown summaries (`research/{TICKER}.summary.md`) and timelines (`research/{TICKER}.timeline.md`) are compiled programmatically from the ledger to prevent file size bloat. They are read-only, contain source ID snapshots, and are never edited manually.
8. **Multi-Phase Non-Destructive Migration:** Legacy files are imported using a deterministic gate pipeline (`scan -> classify -> manifest -> stage -> validate -> publish -> archive`). Legacy files are moved to a git-committed archive directory, not deleted immediately.
9. **Relocate Cluttered Caches:** Loose raw JSON outputs (`*_raw.json`) in the root of `temp/` are redirected to a structured, gitignored backend cache directory (`backend/data/cache/yfinance/`).

## Consequences
* **Greatly Reduced Contention:** Concurrent reads are permitted during write transactions via WAL mode, protecting Node.js and Python concurrent accesses.
* **Deterministic Provenance:** Every analysis update can be traced directly back to its source event ID and raw model prompt/response files.
* **Separation of Concerns:** Markdown remains the ideal presentation layer for humans and LLMs without serving as a fragile storage engine.
* **Schema Integrity:** YAML headers in generated files are verified against strict schema constraints during generation.
