# ADR-027: SQLite Database Selection for Structured Observations and Indexing

## Status
Proposed

## Context
With the decision in ADR-026 to transition to a Hybrid Event Sourcing architecture (with JSONLines logs as the master ledger and a queryable SQL database as the derived read model index), we must select a suitable SQL database engine.

We require a storage engine that satisfies several workstation requirements:
1. **Low Operational Overhead:** The workstation runs locally on a retail investor's machine. Installing, configuring, and maintaining a separate server process (e.g. PostgreSQL, MySQL) is unacceptable for a desktop toolkit.
2. **Dual-Runtime Compatibility:** The index must be readable and writable from both Node.js (Vite/Express backend) and Python (py_services analytical bridges).
3. **FTS5 Search Capabilities:** We require robust, native full-text search (FTS) indexing over markdown prose research events to replace slow string scanning.
4. **Concurrency Support:** Multiple agent scripts, CLI tools, and the backend server must be able to query the index concurrently without write locking blocking the main process loop.

## Decision
We select **SQLite (v3.x)** as our structured storage and indexing engine.

We configure SQLite under the following parameters:
* **Write-Ahead Logging (WAL) Mode:** Enabled (`PRAGMA journal_mode=WAL;`). This permits concurrent reads while a write transaction is executing, preventing backend locks.
* **FTS5 Extension:** Enabled. We utilize the virtual table FTS5 extension for search.
* **Foreign Key Constraints:** Enabled (`PRAGMA foreign_keys=ON;`) to enforce referential integrity across instruments and events.

### Alternatives Evaluated

| Alternative | Pros | Cons | Reason for Rejection |
|---|---|---|---|
| **PostgreSQL** | Rich relational features, out-of-the-box concurrency, strong type checks. | Requires running a local database service daemon; complex setup. | Overkill for a local workstation; adds installation friction. |
| **Flat JSON File Collections** | Simple, Git-diffable, readable. | No transactions; prone to concurrent write corruption; slow scanning. | Fails concurrency and transactional constraints. |
| **NoSQL (CouchDB / MongoDB)** | Flexible schema fits qualitative data. | Requires running service daemons; complex dual-runtime client setup. | Operational complexity and installation friction. |

## Consequences
* **Impact on `investment_screener` backend:** We must add `sqlite3` or `better-sqlite3` Node module dependencies to the Express backend packages, and standard `sqlite3` libraries in Python.
* **Zero Configuration:** The database is self-contained in a single file (`intelligence.sqlite`), requiring no installation steps for new toolkit setups.
* **Local Read/Write Performance:** Query times are sub-millisecond, and the index can be fully rebuilt from the JSONL master log in seconds if corrupted.
