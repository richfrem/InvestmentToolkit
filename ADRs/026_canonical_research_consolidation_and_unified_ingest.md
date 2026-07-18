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

1. **Transactional SQLite Index:** We establish `investment_screener/backend/data/intelligence.sqlite` as the authoritative write path and query engine for qualitative updates, valuations, and portfolio decisions.
2. **Immutable Event Capture:** Observations from sweeps (e.g. Grok news sweeps) are stored as immutable, content-addressed event records in the database with clear separation of timestamps (`effective_at`, `observed_at`, `ingested_at`).
3. **Reproducible Materialized Views:** Markdown profiles in `research/{TICKER}.md` are downgraded to read-only, generated views compiled programmatically from SQLite and the projections JSON. They carry generation timestamps and content hashes, and are never edited manually.
4. **Decoupled Financial Logic:** Valuation signals (`fairValue`) are strictly version-linked in the valuation history and separated from execution actions (`BUY|HOLD|SELL`), preventing misleading data alignments.
5. **Multi-Phase Non-Destructive Migration:** Legacy files are imported using a deterministic gate pipeline (`scan -> classify -> manifest -> stage -> validate -> publish -> archive`). Legacy files are moved to a git-committed archive directory, not deleted immediately.
6. **Relocate Cluttered Caches:** Loose raw JSON outputs (`*_raw.json`) in the root of `temp/` are redirected to a structured, gitignored backend cache directory (`backend/data/cache/yfinance/`).

## Consequences
* **No Write Contention:** Writes are transactional via SQLite WAL mode, eliminating read-modify-write file corruption.
* **Deterministic Provenance:** Every analysis update can be traced directly back to its source event ID and raw model prompt/response files.
* **Separation of Concerns:** Markdown remains the ideal presentation layer for humans and LLMs without serving as a fragile storage engine.
* **Schema Integrity:** YAML headers in generated files are verified against strict schema constraints during generation.
