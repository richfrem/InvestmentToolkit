# Design Spec: SQLite-Driven Intelligence Ledger & Generated Research Views

## 1. Context & Architecture Goal
Based on the adversarial feedback from GPT-5.6, we reject the model where mutable Markdown files are the primary write targets. Doing so introduces concurrent read-write races, double sources of truth for financial variables, and breaks transaction boundaries.

Our target architecture transitions to a **Hybrid Structured Intelligence Ledger**:
1. **Authoritative Write Store:** SQLite is the transactional ledger for structural observations, instrument metadata, and valuation versions.
2. **Event Ledger (Event Sourcing Lite):** Immutable, chronologically ordered JSONLines logs act as the master log. SQLite is a projection/index built by replaying this ledger.
3. **FTS5 Search Index:** A virtual SQLite search table enables prefix/relevance matching, resolving query issues over thousands of prose observations.
4. **Generated Views (Markdown):** Markdown files in `research/{TICKER}.md` are **reproducible, materialized views** generated from the SQLite ledger and projections DB. They are split into `.summary.md`, `.timeline.md`, and `.metrics.json` to control agent token limits.
5. **Clutter-Free Caching:** Loose JSON dumps in `temp/` are swept into structured, gitignored subdirectories.

---

## 2. Directory Layout & Storage Mapping

We organize directories under a strict separation of raw data, structured db, and generated views:

```
investment_screener/backend/data/
├── intelligence.sqlite        ← Authoritative transactional index & query store
├── projections/               ← Canonical JSON DCF version logs (unchanged)
├── research/                  ← Generated human-readable views (re-created on demand)
│   ├── PLTR.summary.md        ← Generated from DB (core thesis, catalysts, risks)
│   ├── PLTR.timeline.md       ← Generated from DB (chronological audit history)
│   └── PLTR.metrics.json      ← Machine-readable generated snapshot data
├── history/                   ← Git-committed historical records
│   ├── events/                ← Append-only JSONL event logs (Authoritative recovery source)
│   │   └── observations.jsonl
│   ├── reviews/               ← Daily/Weekly confluence reviews (generated)
│   │   ├── daily/
│   │   └── weekly/
│   └── sweeps/                ← Archive of raw sweep prompt/response inputs (provenance)
└── cache/                     ← Gitignored raw API cache files
    ├── yfinance/              ← yfinance fetches (*_raw.json)
    └── tv_snapshots/          ← Technical analysis temporary snapshots
```

---

## 3. SQLite Database Schema

We define a relational schema in `intelligence.sqlite` to track instruments, events, source provenance, and valuations:

```sql
-- Core instrument mapping
CREATE TABLE IF NOT EXISTS instrument (
    instrument_id TEXT PRIMARY KEY,
    ticker TEXT NOT NULL,
    exchange TEXT,
    name TEXT NOT NULL,
    active_from TEXT,
    active_to TEXT,
    UNIQUE(ticker, exchange, active_from)
);

-- Ticker aliases for symbols that change over time (e.g. FB -> META)
CREATE TABLE IF NOT EXISTS instrument_alias (
    alias_id TEXT PRIMARY KEY,
    instrument_id TEXT NOT NULL,
    alias_ticker TEXT NOT NULL,
    exchange TEXT,
    effective_from TEXT NOT NULL,
    effective_to TEXT,
    FOREIGN KEY(instrument_id) REFERENCES instrument(instrument_id),
    UNIQUE(alias_ticker, exchange, effective_from)
);

-- Provenance tracking
CREATE TABLE IF NOT EXISTS source (
    source_id TEXT PRIMARY KEY,
    source_type TEXT NOT NULL,
    provider TEXT,
    original_path TEXT,
    original_uri TEXT,
    git_commit TEXT,
    retrieved_at TEXT,
    content_hash TEXT NOT NULL
);

-- Core event stream data with corrections logic
CREATE TABLE IF NOT EXISTS intelligence_event (
    event_id TEXT PRIMARY KEY,
    instrument_id TEXT,
    event_type TEXT NOT NULL CHECK (
        event_type IN (
            'RESEARCH_IMPORT', 'NEWS_SWEEP', 'EARNINGS', 
            'VALUATION_UPDATE', 'TECHNICAL_SWEEP', 'PORTFOLIO_DECISION', 
            'THESIS_UPDATE', 'MACRO_EVENT', 'REVIEW_DAILY', 'REVIEW_WEEKLY'
        )
    ),
    effective_at TEXT NOT NULL,
    observed_at TEXT,
    ingested_at TEXT NOT NULL,
    source_id TEXT,
    confidence REAL,
    status TEXT NOT NULL CHECK (
        status IN ('ACTIVE', 'SUPERSEDED', 'RETRACTED', 'INVALIDATED', 'DRAFT')
    ),
    title TEXT,
    body_markdown TEXT,
    payload_json TEXT,
    supersedes_event_id TEXT,
    idempotency_key TEXT UNIQUE,
    content_hash TEXT NOT NULL,
    FOREIGN KEY(instrument_id) REFERENCES instrument(instrument_id),
    FOREIGN KEY(source_id) REFERENCES source(source_id),
    FOREIGN KEY(supersedes_event_id) REFERENCES intelligence_event(event_id),
    UNIQUE(content_hash, source_id)
);

-- FTS5 search index table
CREATE VIRTUAL TABLE IF NOT EXISTS intelligence_event_fts USING fts5(
    title,
    body_markdown,
    content='intelligence_event',
    content_rowid='rowid'
);

-- Current synthesized thesis (avoids rebuilding from history on every run)
CREATE TABLE IF NOT EXISTS research_thesis (
    thesis_id TEXT PRIMARY KEY,
    instrument_id TEXT NOT NULL,
    core_thesis TEXT NOT NULL,
    key_risks TEXT NOT NULL,
    key_catalysts TEXT NOT NULL,
    validation_breakers TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(instrument_id) REFERENCES instrument(instrument_id)
);

CREATE TABLE IF NOT EXISTS valuation_version (
    valuation_id TEXT PRIMARY KEY,
    instrument_id TEXT NOT NULL,
    model_version TEXT NOT NULL,
    effective_at TEXT NOT NULL,
    fair_value_minor_units INTEGER NOT NULL,
    currency TEXT NOT NULL,
    assumptions_json TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    FOREIGN KEY(instrument_id) REFERENCES instrument(instrument_id)
);

CREATE TABLE IF NOT EXISTS portfolio_decision (
    decision_id TEXT PRIMARY KEY,
    instrument_id TEXT NOT NULL,
    valuation_id TEXT,
    action TEXT NOT NULL CHECK (
        action IN ('BUY', 'ADD', 'HOLD', 'TRIM', 'EXIT', 'WATCH')
    ),
    reason_code TEXT NOT NULL,
    policy_version TEXT NOT NULL,
    effective_at TEXT NOT NULL,
    FOREIGN KEY(instrument_id) REFERENCES instrument(instrument_id),
    FOREIGN KEY(valuation_id) REFERENCES valuation_version(valuation_id)
);
```

---

## 4. Generated Profile Metadata Envelope (`research/{TICKER}.summary.md`)

```yaml
---
schemaVersion: 1
documentType: generated-research-summary
instrumentId: us-xnas-pltr
ticker: "PLTR"
generatedAt: "2026-07-18T09:30:00Z"
revision: 42
valuationSnapshot:
  projectionVersion: 17
  valuationAsOf: "2026-07-18T09:30:00Z"
  fairValue: 147.06
  action: HOLD
---

# PLTR Canonical Research Summary

*This file is a generated view. Do not edit directly. Authoritative observations are stored in `intelligence.sqlite`.*

## Current Thesis Summary
...
```

---

## 5. Non-Destructive Migration Protocol

To transition from dated files safely, we enforce a strict 6-phase migration pipeline:

```
[Scan] ➔ [Classify] ➔ [Manifest] ➔ [Stage] ➔ [Validate] ➔ [Publish & Archive]
```

1. **Scan:** Parse all `{TICKER}_{DATE}.md` files in `backend/data/research/`.
2. **Classify:** Identify ticker, effective date, and parse content structures.
3. **Manifest:** Write a migration manifest tracking hashes, sizes, and destination IDs.
4. **Stage:** Populate `intelligence.sqlite` tables and event records in memory or test db.
5. **Validate:** Confirm no byte count mismatches, verify projection schemas, and check referential integrity.
6. **Publish & Archive:** Commit to `intelligence.sqlite`. Move legacy source files to `history/archive/` (no immediate deletion).
