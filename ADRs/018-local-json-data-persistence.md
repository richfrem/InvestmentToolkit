# ADR 018: Local JSON Data Persistence

## Status
Proposed (Inferred from existing codebase)

## Context
The application needs to store portfolio holdings and user settings locally. To maintain portability and simplicity, we want to avoid requiring a full database engine (PostgreSQL/MongoDB) for the initial MVP.

## Decision
Use **Local JSON Files** for data persistence:
1. `portfolio.json`: Stores all ticker symbols, share counts, and basic metadata.
2. The file is stored in a shared location (`backend/data/`) accessible to both backend (for updates) and frontend (via API).

## Consequences
- **Pros**:
    - Zero configuration; no database setup required.
    - Human-readable and easy to debug/edit manually.
    - Version-controllable (if desired by user).
- **Cons**:
    - Not suitable for high-concurrency writes (race conditions).
    - Lacks structural validation or indexing found in SQL databases.
