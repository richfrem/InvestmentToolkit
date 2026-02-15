# ADR 020: Robust Valuation Persistence Strategy

## Status
Proposed (2026-02-14)

## Context
The Investment Toolkit needs to move valuation projections from browser `LocalStorage` to backend JSON storage for permanence and cross-device potential. Initial designs only considered a monolithic JSON file and simple dual-write sync. 

Red Team review (Opus 4.6) identified several critical risks:
1. **Monolithic Data File**: A single large JSON file for all users/tickers increases the impact of corruption and slows down as data grows.
2. **Sync Race Conditions**: Dual-writing to LocalStorage and API simultaneously can lead to silent data loss if one write fails.
3. **Write Atomicity**: Standard `fs.writeFileSync` can truncate data if the process crashes during writing.
4. **Validation**: Lack of schema enforcement at the API layer allows malformed or malicious data.

## Decision
We will implement a hardened persistence layer with the following characteristics:

1. **Per-Ticker Sharding**: Each ticker's projections are stored in a separate file (e.g., `backend/data/projections/AAPL.json`).
2. **Atomic Writes**: Implement a "Write-Rename" pattern using `.tmp` files and `fs.renameSync()` to ensure file integrity.
3. **Strict API-First Sync**: The backend is the source of truth. The frontend only updates its `LocalStorage` cache *after* a successful server response.
4. **Version-Based Conflict Detection**: Each projection includes a `version` number. The backend rejects POSTs with stale versions (HTTP 409) to handle concurrent multi-tab editing.
5. **Zod Schema Validation**: All incoming data is strictly validated for types, numeric ranges, and business logic (e.g., scenario weights must sum to 1.0).
6. **Enhanced Snapshots**: Capture fiscal periods and analyst estimates at save-time to ensure historical valuations are contextually complete.
7. **Architecture Reference**: Detailed design is located in `docs/architecture/stock-valuation/valuation-persistence.md`.

## Consequences
- **Pros**:
    - Significantly reduced data loss and corruption risk.
    - Improved scalability as the user's ticker list grows.
    - Clearer audit trail for historical valuations.
    - Easier manual backup/inspection of individual stock data.
- **Cons**:
    - Slightly higher complexity in backend file management.
    - Requires robust migration logic for existing V1 (flat) LocalStorage data.
