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

1. **Transactional SQLite Index with WAL Mode:** We establish `investment_screener/backend/data/intelligence.sqlite` as the authoritative index and query engine for qualitative updates, valuations, and portfolio decisions.
2. **Immutable Event Sourcing Ledger:** Observations from sweeps (e.g. Grok news sweeps) are stored as append-only, chronologically ordered logs in `history/events/observations.jsonl`. SQLite acts as a queryable read model rebuilt by replaying this ledger.
3. **FTS5 Search Indexing:** We integrate a dedicated `intelligence_event_fts` virtual table using SQLite FTS5 to enable fast prefix and relevance-based keyword matching over historical prose updates.
4. **Instrument Alias Mapping:** Tickers are mapped through an `instrument_alias` table to ensure historical data does not break when company symbols change or merge (e.g. `FB` -> `META`).
5. **Decoupled Financial Logic & Enums:** Valuation signals (`fairValue`) are strictly version-linked in the valuation history and separated from execution actions (`BUY|HOLD|SELL`), using strict event taxonomy (`RESEARCH_IMPORT`, `NEWS_SWEEP`, `EARNINGS`, etc.) and status enums (`ACTIVE`, `SUPERSEDED`, `RETRACTED`, `INVALIDATED`, `DRAFT`).
6. **Reproducible Materialized Views:** Generated Markdown views in `research/{TICKER}.summary.md` and `research/{TICKER}.timeline.md` are compiled programmatically from the ledger to prevent file size bloat. They are read-only and never edited manually.
7. **Multi-Phase Non-Destructive Migration:** Legacy files are imported using a deterministic gate pipeline (`scan -> classify -> manifest -> stage -> validate -> publish -> archive`). Legacy files are moved to a git-committed archive directory, not deleted immediately.
8. **Relocate Cluttered Caches:** Loose raw JSON outputs (`*_raw.json`) in the root of `temp/` are redirected to a structured, gitignored backend cache directory (`backend/data/cache/yfinance/`).

## Consequences
* **No Write Contention:** Writes are transactional via SQLite WAL mode, eliminating read-modify-write file corruption.
* **Deterministic Provenance:** Every analysis update can be traced directly back to its source event ID and raw model prompt/response files.
* **Separation of Concerns:** Markdown remains the ideal presentation layer for humans and LLMs without serving as a fragile storage engine.
* **Schema Integrity:** YAML headers in generated files are verified against strict schema constraints during generation.
